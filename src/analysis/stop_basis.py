"""Which stops the algorithm should be allowed to choose from.

The route generator does not start from the stops jeepneys actually use. It
starts from every node of the city road graph that City Zone Creation tagged
(1778 of Makati's 4072), and thins them while a route is built: at each step ``generate_route`` re-enables the pool and disables
whatever lies within one of ``WALKING_DISTANCES`` of the stop it is standing on,
so the next stop is always at least that far from the current one. The walking
distance is therefore the spacing between *consecutive* stops on a route, and
the candidate pool is road nodes rather than stops.

This module measures the alternative -- taking Sakay.ph's stops as the basis --
against that, on the two questions it turns on:

* :func:`route_stop_spacing` -- how far apart real jeepney stops actually are,
  which says whether the walking distances produce realistic service at all.
* :func:`basis_comparison` -- what the derived pool buys over the real stops in
  population reached, what it costs, and whether it even contains them. If a
  real stop has no candidate near it, the optimiser cannot reproduce the
  network in service, and the Pareto front cannot contain the status quo that
  methodology 3.6 compares it against.
"""
import pickle

import numpy as np
from geopy.distance import geodesic
from scipy.spatial import cKDTree

from config.config import (N_NETWORKS, N_ROUTES, STOP_COST, STOP_MIN,
                           STOP_SIZES, WALKING_DISTANCES, WD_TO_USE)
from utils.route_utils import make_run_tag

from analysis.catchment import _project
from analysis.original_network import ROOT

ROUTE_SET_DIR = ROOT / "data" / "initial_route_sets"


def route_stop_spacing(network):
    """Straight-line metres between consecutive stops, over every route.

    Straight line rather than along the road on purpose: the walking distance
    it is compared against is a radius, not a path length.
    """
    gaps = []
    for route in network.routes:
        for connection in route.route:
            start, end = connection[0], connection[-1]
            a, b = network.graph.nodes[start], network.graph.nodes[end]
            gaps.append(
                geodesic((a["lat"], a["lon"]), (b["lat"], b["lon"])).m)
    return np.array(gaps)


def sakay_stop_coords(network):
    """``(lat, lon)`` of every stop in the network in service."""
    return [(data["lat"], data["lon"])
            for _, data in network.graph.nodes(data=True)]


def derived_stop_paths(city):
    """Candidate stop-graph files for a city, best first.

    The run-tagged name comes first. IRSG writes one file per parameter set
    and leaves older ones in place, so the untagged ``{city}_stops.pkl`` is
    whatever happened to be written last -- for Manila that is a 4,132-node
    pool while the current settings produce 4,140. Reading the untagged name
    means quoting a pool nobody is generating against any more, silently.

    The tag is rebuilt from config rather than discovered, so this follows
    ``WD_TO_USE`` and ``N_ROUTES`` automatically when the group re-runs IRSG.
    """
    tag = make_run_tag(WALKING_DISTANCES[WD_TO_USE], STOP_MIN,
                       N_ROUTES[city], N_NETWORKS)
    return (ROUTE_SET_DIR / city / f"{city}_stops{tag}.pkl",
            ROUTE_SET_DIR / city / f"{city}_stops.pkl")


def derived_stop_graph(city):
    """The saved stop graph IRSG generated for a city, and where it came from.

    Returns ``(graph, path)``. The path is returned so a caller can say which
    run a figure was drawn from, which matters while several parameter sets
    are on disk at once.
    """
    tried = derived_stop_paths(city)
    for path in tried:
        if not path.exists():
            continue
        with open(path, "rb") as f:
            payload = pickle.load(f)

        # IRSG's notebook writes the network population and the stop graph
        # from the same ``file_path`` variable, so running those cells out of
        # order saves a list of Networks under the stops name. Checking the
        # type here turns that into a sentence instead of an AttributeError
        # several frames deep.
        if not hasattr(payload, "nodes"):
            raise TypeError(
                f"{path} holds {type(payload).__name__}"
                f"{f' of {len(payload)}' if hasattr(payload, '__len__') else ''}"
                f", not a stop graph. IRSG saved the wrong object here;"
                f" re-run its stop-graph cell for {city}.")
        return payload, path

    listed = ", ".join(str(p) for p in tried)
    raise FileNotFoundError(
        f"no generated stop set for {city}; tried {listed}. Run IRSG for it first")


def derived_stop_coords(city):
    """``(lat, lon)`` of every candidate stop the route generator may pick.

    These are the nodes of the saved stop graph carrying ``isTranspo``, which
    is what ``generate_route_network`` is handed as ``stop_nodes``.
    """
    graph, _ = derived_stop_graph(city)
    return [(data["y"], data["x"])
            for _, data in graph.nodes(data=True) if "isTranspo" in data]


def _reach(grid, stops, radius):
    """Share of city population within ``radius`` of any of these stops."""
    cells = set()
    for group in grid.cells_near([a for a, _ in stops],
                                 [b for _, b in stops], radius):
        cells.update(group)
    return grid.population_of(cells) / grid.total


def _nearest_spacing(grid, stops):
    """Median distance from a stop to its nearest neighbour, in metres."""
    points = _project([a for a, _ in stops], [b for _, b in stops],
                      grid.lat0, grid.lon0)
    distance, _ = cKDTree(points).query(points, k=2)
    return float(np.median(distance[:, 1]))


def distance_to_nearest(grid, source, target):
    """Metres from each ``source`` stop to the closest ``target`` stop."""
    a = _project([lat for lat, _ in source], [lon for _, lon in source],
                 grid.lat0, grid.lon0)
    b = _project([lat for lat, _ in target], [lon for _, lon in target],
                 grid.lat0, grid.lon0)
    distance, _ = cKDTree(b).query(a, k=1)
    return distance


def cheapest_possible_cost(count):
    """What ``count`` stops cost if every one is built at the smallest size.

    A floor, not an estimate: ``get_stop_area`` can only ever charge more. It
    is the useful number against ``MAX_BUDGET``, because a basis whose floor is
    already over budget cannot be used whatever the optimiser does.
    """
    return count * min(STOP_SIZES) * STOP_COST


def basis_comparison(city, network, grid, radius):
    """The two stop bases side by side, as a flat dict."""
    sakay = sakay_stop_coords(network)
    derived = derived_stop_coords(city)
    gap = distance_to_nearest(grid, sakay, derived)

    return {
        "City": city,
        "Sakay Stops": len(sakay),
        "Derived Candidates": len(derived),
        "Sakay Reach": _reach(grid, sakay, radius),
        "Derived Reach": _reach(grid, derived, radius),
        "Sakay Median Spacing (m)": _nearest_spacing(grid, sakay),
        "Derived Median Spacing (m)": _nearest_spacing(grid, derived),
        "Sakay Cost Floor (PHP)": cheapest_possible_cost(len(sakay)),
        "Derived Cost Floor (PHP)": cheapest_possible_cost(len(derived)),

        # Whether the derived pool can even express the network in service.
        "Real Stop To Nearest Candidate, median (m)": float(np.median(gap)),
        "Real Stop To Nearest Candidate, max (m)": float(gap.max()),
        "Real Stops With A Candidate Within 20m": float((gap <= 20).mean()),
        "Real Stops With A Candidate Within 100m": float((gap <= 100).mean()),
    }


def thinning_curve(grid, stops, radius, spacings):
    """Reach against stop count as the candidate pool is thinned by spacing.

    Greedy thinning: walk the stops and keep one only if nothing already kept
    lies within ``spacing`` of it.

    This is *not* what the generator does. ``generate_route`` calls
    ``enable_nodes`` before each step and then disables only what sits within
    the walking distance of the stop it is standing on, and
    ``generate_route_network`` resets the pool for every line, so the
    constraint is between *consecutive* stops rather than across the network.
    What this curve answers is the narrower question of how much of a city a
    stop network can reach if every stop is at least ``spacing`` from every
    other -- an upper bound on sparse coverage, which is why reach falls away
    so fast.
    """
    points = _project([a for a, _ in stops], [b for _, b in stops],
                      grid.lat0, grid.lon0)
    rows = []
    for spacing in spacings:
        tree = cKDTree(points)
        kept = []
        blocked = set()
        for index in range(len(points)):
            if index in blocked:
                continue
            kept.append(index)
            blocked.update(tree.query_ball_point(points[index], spacing))
        thinned = [stops[index] for index in kept]
        rows.append({"Spacing (m)": spacing,
                     "Stops": len(thinned),
                     "Reach": _reach(grid, thinned, radius)})
    return rows
