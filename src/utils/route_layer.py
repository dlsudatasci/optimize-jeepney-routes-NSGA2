"""Line-expanded shortest paths for Z_user.

Nodes and arcs
--------------
    jeep node   : (stop, line)  for connection endpoints only. A connection is
                  one logical hop between two stops; its length is the
                  ``distance`` attribute stored on the network edge, so no
                  interior road nodes are needed.
    jeep arc    : (u, line) -> (v, line), weight = metres / JEEP_SPEED_KPH
    jeep xfer   : (s1, lineA) -> (s2, lineB), weight = theta, when s1 and s2 are
                  within JEEP_TRANSFER_MAX_M. Direction-independent;
    rail arc    : (line, station) -> (line, station), weight from rail_layer
    rail xfer   : fixed pairs from RAIL_INTERCHANGES, weight = theta
    mode xfer   : jeep stop <-> rail station within RAIL_TRANSFER_MAX_M, theta

Max transfer distance radii differ by mode (but rail-rail interchanges are fixed)

A city's rail stations are themselves origin/destination nodes.
"""

from __future__ import annotations

import math
from collections import defaultdict

import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra as sp_dijkstra
from scipy.spatial import cKDTree

from config.config import (
  JEEP_TRANSFER_MAX_M,
  RAIL_TRANSFER_MAX_M,
  TRANSFER_PENALTY_MIN,
)
from utils.rail_layer import LINES, RAIL_INTERCHANGES

JEEP_SPEED_KPH = 9.0
EARTH_R = 6371008.8


def build_rail_graph() -> nx.Graph:
    """Build the static rail trunk graph.

    Nodes are ``(line, station)`` tuples so an interchange is two distinct nodes
    joined by a theta-cost edge. Edges carry ``minutes`` and ``mode``.
    """
    from utils.rail_layer import line_segments

    G = nx.Graph()
    for line, info in LINES.items():
        speed = info["speed_kph"]
        for name, lat, lon in info["stations"]:
            G.add_node((line, name), lat=lat, lon=lon, line=line,
                       mode="rail", name=name)
        for a, b, km in line_segments(line):
            if (line, a) not in G or (line, b) not in G:
                continue
            G.add_edge((line, a), (line, b),
                       minutes=km / speed * 60.0, mode="rail", line=line)

    for a, b in RAIL_INTERCHANGES:
        if a in G and b in G:
            G.add_edge(a, b, minutes=TRANSFER_PENALTY_MIN,
                       mode="transfer", line="interchange")
    return G


def _hav_m(a, b) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(h))


def _coords(graph_of_stops, n):
    d = graph_of_stops.nodes.get(n)
    if d is None:
        return None
    lat = d.get("lat", d.get("y"))
    lon = d.get("lon", d.get("x"))
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def _is_rail(n) -> bool:
    return isinstance(n, tuple) and len(n) == 2 and isinstance(n[0], str) and n[0] in LINES


def _local_xy(pairs, lat0):
    out = np.empty((len(pairs), 2))
    coslat = math.cos(math.radians(lat0))
    for i, (la, lo) in enumerate(pairs):
        out[i, 0] = lo * 111_320.0 * coslat
        out[i, 1] = la * 111_320.0
    return out


def build_layer(network, graph_of_stops, rail: nx.Graph,
                theta: float = TRANSFER_PENALTY_MIN,
                jeep_transfer_m: float = JEEP_TRANSFER_MAX_M,
                rail_transfer_m: float = RAIL_TRANSFER_MAX_M):
    """Return (graph, stop_to_nodes, station_nodes, stats)."""
    G = nx.DiGraph()
    stats = {"jeep_arcs": 0, "jeep_transfers": 0, "rail_arcs": 0,
             "rail_interchanges": 0, "mode_links": 0,
             "boarding_nodes": 0, "missing_distance": 0}

    def add(u, v, w, kind):
        old = G.get_edge_data(u, v)
        if old is None or w < old["minutes"]:
            G.add_edge(u, v, minutes=w, kind=kind)

    g = network.graph
    boarding = set()

    # ---- jeepney riding arcs ----
    for route in network.routes:
        line = route.line_id
        for conn in route.route:
            if not conn:
                continue
            u, v = conn[0], conn[-1]
            boarding.add((u, line))
            if u == v:
                continue

            data = None
            if g.has_edge(u, v):
                data = g.get_edge_data(u, v, route.route_id)
            if data is None and g.has_edge(v, u):
                data = g.get_edge_data(v, u, route.route_id)
            if data is None:
                for key in (g.get_edge_data(u, v) or {}):
                    if key == route.route_id:
                        data = g.get_edge_data(u, v, key)
                        break

            if data is not None and data.get("distance") is not None:
                dd = float(data["distance"])
                metres = dd * 1000.0 if dd < 100 else dd
            else:
                cu = _coords(graph_of_stops, u)
                cv = _coords(graph_of_stops, v)
                if cu is None or cv is None:
                    stats["missing_distance"] += 1
                    continue
                metres = _hav_m(cu, cv)

            add((u, line), (v, line),
                metres / 1000.0 / JEEP_SPEED_KPH * 60.0, "jeep")
            stats["jeep_arcs"] += 1

    for n in boarding:
        G.add_node(n)

    # ---- rail riding arcs ----
    for u, v, d in rail.edges(data=True):
        w = d.get("minutes")
        if not isinstance(w, (int, float)) or math.isnan(w):
            continue
        add(u, v, float(w), "rail")
        stats["rail_arcs"] += 1

    # ---- fixed rail interchanges ----
    for a, b in RAIL_INTERCHANGES:
        if a in G and b in G:
            add(a, b, theta, "transfer")
            add(b, a, theta, "transfer")
            stats["rail_interchanges"] += 2

    # ---- stop -> lines, and coordinates ----
    stop_lines: dict = defaultdict(set)
    for n in G.nodes:
        if isinstance(n, tuple) and len(n) == 2 and not _is_rail(n):
            stop_lines[n[0]].add(n[1])

    stops = [s for s in stop_lines if _coords(graph_of_stops, s) is not None]
    coords = {s: _coords(graph_of_stops, s) for s in stops}

    if stops:
        lat0 = sum(coords[s][0] for s in stops) / len(stops)
        xy = _local_xy([coords[s] for s in stops], lat0)
        tree = cKDTree(xy)
        for i, j in tree.query_pairs(r=jeep_transfer_m, output_type="ndarray"):
            s1, s2 = stops[i], stops[j]
            for a in stop_lines[s1]:
                for b in stop_lines[s2]:
                    if a == b:
                        continue
                    add((s1, a), (s2, b), theta, "transfer")
                    add((s2, b), (s1, a), theta, "transfer")
                    stats["jeep_transfers"] += 2

    # ---- jeep stop <-> rail station ----
    stations = [(n, (d["lat"], d["lon"])) for n, d in rail.nodes(data=True)
                if d.get("mode") == "rail"]
    if stations and stops:
        lat0r = sum(c[0] for _, c in stations) / len(stations)
        stree = cKDTree(_local_xy([c for _, c in stations], lat0r))
        for s in stops:
            sc = _local_xy([coords[s]], lat0r)[0]
            for j in stree.query_ball_point(sc, r=rail_transfer_m):
                station = stations[j][0]
                for line in stop_lines[s]:
                    add((s, line), station, theta, "transfer")
                    add(station, (s, line), theta, "transfer")
                    stats["mode_links"] += 2

    stop_to_nodes: dict = {}
    for n in G.nodes:
        if _is_rail(n):
            continue
        if isinstance(n, tuple) and len(n) == 2:
            stop_to_nodes.setdefault(n[0], []).append(n)

    station_nodes = {n: [n] for n in G.nodes if _is_rail(n)}
    stats["boarding_nodes"] = len(boarding)
    return G, stop_to_nodes, station_nodes, stats


def cost_matrix(network, graph_of_stops, rail: nx.Graph, od_nodes: list,
                theta: float = TRANSFER_PENALTY_MIN, want_stats=False,
                jeep_transfer_m: float = JEEP_TRANSFER_MAX_M,
                rail_transfer_m: float = RAIL_TRANSFER_MAX_M):
    """Return (T_min, M) for ``od_nodes``, which may hold jeep stops and rail
    station ``(line, station)`` tuples.

    ``T`` is pure riding time; ``T + theta*M`` is the quantity Z_user
    minimises. Both are read off the same shortest path, so they cannot
    disagree. Unreachable pairs stay ``inf``.
    """
    G, stop_to_nodes, station_nodes, stats = build_layer(
        network, graph_of_stops, rail, theta,
        jeep_transfer_m=jeep_transfer_m, rail_transfer_m=rail_transfer_m,
    )

    nodes = list(G.nodes)
    index = {n: i for i, n in enumerate(nodes)}
    n_all = len(nodes)

    rows, cols, vals, trows, tcols = [], [], [], [], []
    for u, v, d in G.edges(data=True):
        rows.append(index[u]); cols.append(index[v]); vals.append(d["minutes"])
        if d["kind"] == "transfer":
            trows.append(index[u]); tcols.append(index[v])

    M_cost = csr_matrix((vals, (rows, cols)), shape=(n_all, n_all))
    transfer_set = set(zip(trows, tcols))

    n_od = len(od_nodes)
    T = np.full((n_od, n_od), np.inf)
    Mcnt = np.zeros((n_od, n_od), dtype=np.int16)
    best_gen = np.full((n_od, n_od), np.inf) #  Best generalized cost seen per OD pair.

    def nodes_for(x):
        if _is_rail(x):
            return station_nodes.get(x, []) if x in index else []
        return stop_to_nodes.get(x, [])

    src_rows, src_owner = [], []
    for i, s in enumerate(od_nodes):
        for n in nodes_for(s):
            j = index.get(n)
            if j is not None:
                src_rows.append(j)
                src_owner.append(i)
    if not src_rows:
        return (T, Mcnt, stats) if want_stats else (T, Mcnt)

    D, pred = sp_dijkstra(M_cost, directed=True, indices=np.array(src_rows),
                          return_predecessors=True)

    dst = []
    for j, s in enumerate(od_nodes):
        for n in nodes_for(s):
            k = index.get(n)
            if k is not None:
                dst.append((k, j))

    for row, owner in enumerate(src_owner):
        Drow, Prow = D[row], pred[row]
        for k, dest in dst:
            if owner == dest:
                continue
            cost = Drow[k]
            if not np.isfinite(cost) or cost >= best_gen[owner, dest]:
                continue
            changes = 0
            cur = k
            guard = 0
            while guard < 5000:
                p = Prow[cur]
                if p < 0:
                    break
                if (p, cur) in transfer_set:
                    changes += 1
                cur = p
                guard += 1
            best_gen[owner, dest] = cost
            T[owner, dest] = cost - theta * changes
            Mcnt[owner, dest] = changes

    np.fill_diagonal(T, 0.0)
    np.fill_diagonal(Mcnt, 0)
    T[T < 0] = 0.0
    return (T, Mcnt, stats) if want_stats else (T, Mcnt)
