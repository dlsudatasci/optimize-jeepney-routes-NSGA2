"""Building a city's existing jeepney network from its collected route data.

Makati, Manila and Mandaluyong were turned into route networks by an earlier
version of the project and pickled; Taguig was collected later and only exists
as the stop list in ``Taguig_routes.csv``. This module reproduces that same
pipeline so any city with a route CSV, a road graph and a set of transport
amenities can be brought up to the same form.

The steps mirror ``notebooks/Original Jeepney Routes.ipynb``:

1. read the stops of each route, in order;
2. flag a stop as a transport interchange if a transportation amenity sits
   within ``TRANSPO_DISTANCE`` metres of it;
3. merge stops that are within ``MERGE_DISTANCE`` metres of each other,
   preferring an interchange as the survivor;
4. splice each surviving stop into the road graph, cutting the nearest road
   edge in two so the stop becomes a real node;
5. join consecutive stops by the shortest path along the road, which becomes
   one connection of the route;
6. add the return leg by walking the stops in reverse.

Results are cached next to the pickles of the other cities, because step 4
calls ``nearest_edges`` once per stop and is the slow part.
"""
import pickle
import re

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from geopy.distance import geodesic

from genetic_algorithm.schema import Network, Route

from analysis.original_network import ORIGINAL_DIR, ROOT

#: A stop this close to a transportation amenity is treated as an interchange.
TRANSPO_DISTANCE = 50

#: Stops closer together than this are the same stop collected twice.
MERGE_DISTANCE = 20

#: A route needs more than this many stops to be worth keeping, matching the
#: earlier pipeline, which dropped the stubs left behind by truncation.
MIN_STOPS_PER_ROUTE = 3

STREET_NETWORK_DIR = ROOT / "data" / "street_networks"


#: One stop of the raw Sakay.ph export, as WKT.
_POINT = re.compile(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)")


def read_route_stops(path):
    """``{route id: [(lat, long), ...]}`` in the order the stops were listed.

    Handles both collected formats: the ``lat, long, route id`` export Taguig
    was delivered as, and the raw ``WKT, Route Number`` Sakay.ph download the
    other three cities came from.
    """
    frame = pd.read_csv(path)
    if {"lat", "long", "route id"} <= set(frame.columns):
        return {route_id: list(zip(group["lat"], group["long"]))
                for route_id, group in frame.groupby("route id", sort=True)}
    return _read_wkt_route_stops(frame)


def _read_wkt_route_stops(frame):
    """Read the raw export, where each row is one stop of the current route.

    A route is a *run* of consecutive rows sharing a Route Number, not every
    row carrying that number -- which is what the notebook's ``process_csv``
    did, and it matters: a number is reused for the two directions of a line
    and for unrelated routes elsewhere in the file, so grouping by it would
    join stops kilometres apart into one route.
    """
    routes = {}
    occurrences = {}
    current = None
    stops = []

    def close_route():
        if not stops:
            return
        index = occurrences.get(current, 0)
        occurrences[current] = index + 1
        # Second and later runs of a number get a suffix so they stay apart.
        routes[f"{current}" if index == 0 else f"{current}-{index}"] = list(stops)

    for number, wkt in zip(frame["Route Number"], frame["WKT"]):
        if number != current:
            close_route()
            current, stops = number, []
        match = _POINT.match(str(wkt))
        if match:
            long, lat = (float(value) for value in match.groups())
            stops.append((lat, long))
    close_route()

    return routes


#: A stop farther than this from any road in the city graph is outside the
#: study area. Routes genuinely leave the city -- a third of the Taguig stops
#: are in Pasig, Makati or Parañaque, some 6 km past the edge of the graph --
#: and the methodology disregards stops outside the chosen scope.
BOUNDS_TOLERANCE_M = 100

#: Rough metres per degree at this latitude, used only to turn the projected
#: snap distance back into something interpretable.
METRES_PER_DEGREE = 111_320


def clip_to_city(routes, graph, tolerance_m=BOUNDS_TOLERANCE_M,
                 min_stops=MIN_STOPS_PER_ROUTE):
    """Keep the parts of each route that lie inside the city's road graph.

    Taguig's routes run well past the city -- two thirds of its collected
    stops are outside the Taguig graph, some by several kilometres -- and a
    route often leaves and comes back. Cutting at the first stop outside the
    graph, which is what the earlier pipeline did, would throw away two thirds
    of the network along with it.

    So a route is split into the runs of consecutive in-city stops, and each
    run long enough to be a route in its own right is kept. Nothing is
    invented: the gap where the route was outside the city simply is not
    represented, rather than being bridged by a road the jeepney never takes.

    Note this makes a Taguig "route" an in-city segment, which is not the same
    object as a route in the cities whose collected data was already clipped.

    Returns ``(segments, stops dropped, routes split)``.
    """
    nodes = ox.graph_to_gdfs(graph, edges=False)
    min_x, min_y, max_x, max_y = nodes.total_bounds

    flat = [point for stops in routes.values() for point in stops]
    if not flat:
        return routes, 0

    lats = np.array([lat for lat, _ in flat])
    longs = np.array([long for _, long in flat])
    _, distances = ox.distance.nearest_edges(graph, X=longs, Y=lats,
                                             return_dist=True)
    distances = np.asarray(distances) * METRES_PER_DEGREE

    segments = {}
    position = 0
    dropped = 0
    split = 0

    for route_id, stops in routes.items():
        runs = []
        current = []
        for lat, long in stops:
            index = position
            position += 1
            in_bbox = min_x <= long <= max_x and min_y <= lat <= max_y
            if in_bbox and distances[index] <= tolerance_m:
                current.append((lat, long))
            else:
                dropped += 1
                if current:
                    runs.append(current)
                    current = []
        if current:
            runs.append(current)

        runs = [run for run in runs if len(run) > min_stops]
        if len(runs) > 1:
            split += 1
        for part, run in enumerate(runs):
            label = route_id if len(runs) == 1 else f"{route_id}.{part + 1}"
            segments[label] = run

    return segments, dropped, split


def flag_transport_stops(stops, transport_points):
    """Which stops sit within ``TRANSPO_DISTANCE`` of a transport amenity.

    The amenity set is small -- a handful of stations and terminals per city --
    so comparing every stop against every amenity is cheaper than an index.
    """
    flags = []
    for lat, long in stops:
        flags.append(any(
            geodesic((lat, long), (plat, plong)).meters <= TRANSPO_DISTANCE
            for plat, plong in transport_points))
    return flags


def merge_nearby(stops, is_transport):
    """Collapse stops within ``MERGE_DISTANCE`` of each other.

    Returns ``{index: index of the stop that replaces it}``, covering only the
    stops that get merged away. A transport interchange wins over a plain stop,
    so merging never loses an interchange.
    """
    order = sorted(range(len(stops)), key=lambda i: (stops[i][0], stops[i][1]),
                   reverse=True)

    replacement = {}
    group = [order[0]]
    groups = []
    for index in order[1:]:
        if geodesic(stops[group[-1]], stops[index]).meters <= MERGE_DISTANCE:
            group.append(index)
        else:
            groups.append(group)
            group = [index]
    groups.append(group)

    for group in groups:
        if len(group) == 1:
            continue
        survivor = next((i for i in group if is_transport[i]), group[0])
        for index in group:
            if index != survivor:
                replacement[index] = survivor
    return replacement


def splice_stop(graph, stop_id, lat, long, is_transport):
    """Insert a stop as a node on the road edge nearest to it.

    The edge it lands on is cut in two and the two halves keep the original
    edge's attributes, with ``length`` recomputed, so a path through the stop
    still measures the real distance along the road.

    A two-way road is two directed edges in the graph, and both have to be cut.
    Splitting only one of them leaves the stop reachable going one way and not
    the other, so the shortest path back has to loop around the whole block --
    on Taguig that produced 14 km paths between stops 100 m apart. Genuinely
    one-way roads have no opposite edge and stay one-way.
    """
    node1, node2, key = ox.distance.nearest_edges(graph, X=long, Y=lat)
    data = dict(graph.get_edge_data(node1, node2, key))

    graph.add_node(stop_id, x=long, y=lat, isTranspo=is_transport)

    start = (graph.nodes[node1]["y"], graph.nodes[node1]["x"])
    end = (graph.nodes[node2]["y"], graph.nodes[node2]["x"])
    here = (lat, long)

    to_stop = geodesic(start, here).meters
    from_stop = geodesic(here, end).meters

    first = dict(data, length=to_stop)
    second = dict(data, length=from_stop)
    first.pop("geometry", None)
    second.pop("geometry", None)

    graph.add_edge(node1, stop_id, **first)
    graph.add_edge(stop_id, node2, **second)
    graph.remove_edge(node1, node2, key)

    opposite = graph.get_edge_data(node2, node1)
    if opposite:
        back_key, back_data = next(iter(opposite.items()))
        back = dict(back_data)
        back.pop("geometry", None)
        graph.add_edge(node2, stop_id, **dict(back, length=from_stop))
        graph.add_edge(stop_id, node1, **dict(back, length=to_stop))
        graph.remove_edge(node2, node1, back_key)


def _connections_along(graph, stops):
    """Shortest road path between each consecutive pair of stops.

    Returns ``(connections, kilometres)``, truncated at the first pair the road
    network cannot join -- the same thing the earlier pipeline did, so a single
    unreachable stop shortens a route instead of discarding it.
    """
    connections = []
    total = 0.0
    for start, end in zip(stops, stops[1:]):
        if not nx.has_path(graph, start, end):
            break
        path = nx.shortest_path(graph, start, end, weight="length")
        length = nx.shortest_path_length(graph, start, end, weight="length")
        connections.append(tuple(path))
        total += length / 1000
    return connections, total


def build_from_route_csv(city, routes_csv, graphml=None, transport_points=None):
    """Build ``(network, stop_graph)`` for a city from its route CSV."""
    graphml = graphml or STREET_NETWORK_DIR / f"{city}.graphml"
    stop_graph = ox.load_graphml(graphml)

    raw_routes = read_route_stops(routes_csv)
    collected = len(raw_routes)
    raw_routes, dropped, split = clip_to_city(raw_routes, stop_graph)
    if dropped:
        print(f"{city}: {dropped} stops outside the city road graph dropped; "
              f"{collected} collected routes became {len(raw_routes)} in-city "
              f"segments ({split} routes split)")

    flat = [point for stops in raw_routes.values() for point in stops]
    transport_flags = flag_transport_stops(flat, transport_points or [])
    replacement = merge_nearby(flat, transport_flags)

    # Give every surviving stop a node id, then rewrite each route to use them.
    stop_ids = {}
    position = 0
    routes_as_ids = {}
    for route_id, stops in raw_routes.items():
        ids = []
        for _ in stops:
            index = position
            position += 1
            survivor = replacement.get(index, index)
            if survivor not in stop_ids:
                stop_ids[survivor] = len(stop_ids)
            node = stop_ids[survivor]
            if not ids or ids[-1] != node:
                ids.append(node)
        routes_as_ids[route_id] = ids

    for index, node in sorted(stop_ids.items(), key=lambda pair: pair[1]):
        lat, long = flat[index]
        splice_stop(stop_graph, node, lat, long, transport_flags[index])

    graph = nx.MultiDiGraph()
    routes = []
    line_id = 0

    for stops in routes_as_ids.values():
        forward, forward_km = _connections_along(stop_graph, stops)
        if len(forward) + 1 <= MIN_STOPS_PER_ROUTE:
            continue

        served = [stops[0]] + [connection[-1] for connection in forward]
        reverse, reverse_km = _connections_along(stop_graph, list(reversed(served)))

        for direction, connections, kilometres in (
                ("forward", forward, forward_km), ("reverse", reverse, reverse_km)):
            if not connections:
                continue
            route_id = f"{line_id}-{'A' if direction == 'forward' else 'B'}"
            for connection in connections:
                start, end = connection[0], connection[-1]
                for node in (start, end):
                    data = stop_graph.nodes[node]
                    graph.add_node(node, lat=data["y"], lon=data["x"],
                                   isTranspo=bool(data.get("isTranspo", False)))
                distance = sum(
                    stop_graph.get_edge_data(u, v)[0]["length"]
                    for u, v in zip(connection, connection[1:])) / 1000
                graph.add_edge(start, end, key=route_id,
                               road_path=list(connection), distance=distance)
            routes.append(Route(connections, route_id, kilometres,
                                line_id, direction))
        line_id += 1

    return Network(routes, graph), stop_graph


def build_and_cache(city, routes_csv, transport_points=None, graphml=None):
    """Build a city's network and cache it beside the other cities' pickles."""
    network, stop_graph = build_from_route_csv(
        city, routes_csv, graphml=graphml, transport_points=transport_points)
    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    with open(ORIGINAL_DIR / f"{city}_built.pkl", "wb") as f:
        pickle.dump({"routes": network.routes, "graph": network.graph,
                     "stop_graph": stop_graph}, f)
    return network, stop_graph
