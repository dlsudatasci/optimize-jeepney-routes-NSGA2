from __future__ import annotations

import random
import threading

import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree  # pyright: ignore[reportAttributeAccessIssue]

from config.config import (
    CATCHMENT_RADIUS_M,
    FILTER_OPTIONS,
    INVALID_NETWORK_COST,
    JEEP_TRANSFER_MAX_M,
    MIN_INTERSECTIONS_PER_ROUTE,
    MIN_TRANSPO_STOPS_PER_ROUTE,
    RAIL_TRANSFER_MAX_M,
    TARGET_NODE_RATIO,
    TRANSFER_PENALTY_MIN,
)
from genetic_algorithm.schema import HyperParameters, Network
from utils import route_layer as rl
from utils.rail_layer import LINES as _LINES
from utils.rail_layer import rail_stations_for

_CITY_CACHE: dict[tuple[str, int], tuple[dict[frozenset, bool], dict, float, int]] = {}
_RAIL_CACHE: dict[str, nx.Graph] = {}
_CACHE_LOCK = threading.Lock()

def _get_city_stats(city_name: str, graph_of_stops: nx.MultiDiGraph):
    key = (city_name, id(graph_of_stops))
    if key in _CITY_CACHE:
        return _CITY_CACHE[key]

    with _CACHE_LOCK:
        if key in _CITY_CACHE:
            return _CITY_CACHE[key]

        allowed_edge: dict[frozenset, bool] = {}
        edge_len: dict = {}
        total_network_distance = 0.0

        for u, v, _, data in graph_of_stops.edges(keys=True, data=True):
            if data.get("junction") is not None:
                continue
            hw = data.get("highway")
            allowed = (
                any(h in FILTER_OPTIONS for h in hw)
                if isinstance(hw, list)
                else (hw in FILTER_OPTIONS)
            )

            length = data.get("length", 0.0)
            segment = frozenset((u, v))
            if segment not in allowed_edge:
                allowed_edge[segment] = allowed
                edge_len[segment] = length
                if allowed:
                    total_network_distance += length
            elif allowed and not allowed_edge[segment]:
                allowed_edge[segment] = True
                total_network_distance += length

            edge_len[(u, v)] = length
            edge_len[(v, u)] = length

        n_transport_nodes = sum(1 for _, d in graph_of_stops.nodes(data=True) if d.get("isTranspo"))

        _CITY_CACHE[key] = (
            allowed_edge,
            edge_len,
            total_network_distance,
            n_transport_nodes,
        )
        return _CITY_CACHE[key]


def fitness_score(
    network: Network,
    hp: HyperParameters,
    graph_of_stops: nx.MultiDiGraph,
    population_gdf,
    city_name: str,
) -> tuple[np.ndarray, float]:
    allowed_edge, edge_len, total_network_distance, n_transport_nodes = _get_city_stats(
        city_name, graph_of_stops
    )

    z_efficiency = fitness_network_efficiency(network, hp.fitness_weights, n_transport_nodes, total_network_distance, allowed_edge, edge_len)
    z_user = fitness_user_cost(network, graph_of_stops, population_gdf, hp.catchment_m, city=city_name)
    z_capex = fitness_capex_cost(network, hp.stop_cost, hp.stop_sizes, hp.max_degree)


    violation = 0.0
    if z_capex > hp.max_budget:
        violation += (z_capex - hp.max_budget) / max(hp.max_budget, 1.0) # budget excess
    if z_user >= INVALID_NETWORK_COST:
        violation += 1.0 # unscorable
    return np.array([z_user, z_capex, z_efficiency]), violation # min, min, max


def fitness_network_efficiency(
    network: Network,
    weights: dict[str, float],
    total_potential_transport_nodes: int,
    total_network_distance: float,
    allowed_edge: dict[frozenset, bool],
    edge_len: dict[frozenset, float],
) -> float:
  route_stops = {}
  for route in network.routes:
      stops = route_stops.get(route.route_id)
      if stops is None:
          stops = route_stops[route.route_id] = set()
      for connection in route.route:
          if connection:
              stops.update((connection[0], connection[-1]))

  arcs = {}
  for successors in network.graph.adj.values():
      for edges in successors.values():
          for key, data in edges.items():
              path = data["road_path"]
              for i in range(1, len(path)):
                  arc = (path[i - 1], path[i])
                  if arc in edge_len:
                      routes = arcs.get(arc)
                      if routes is None:
                          arcs[arc] = {key}
                      else:
                          routes.add(key)

  nodes = list(network.graph.adj)
  index = {node: i for i, node in enumerate(nodes)}
  rows, cols = [], []
  for node, successors in network.graph.adj.items():
      i = index[node]
      for successor in successors:
          j = index[successor]
          if i != j:
              rows.append(i)
              cols.append(j)
              rows.append(j)
              cols.append(i)

  adjacency = csr_matrix((np.ones(len(rows), dtype=bool), (rows, cols)), shape=(len(nodes), len(nodes)))

  internal_connectivity = compute_internal_connectivity(
    network,
    target_node_ratio=TARGET_NODE_RATIO,
    min_intersections_per_route=MIN_INTERSECTIONS_PER_ROUTE,
    route_stops=route_stops,
  )

  external_connectivity = compute_external_connectivity(
    network,
    total_potential_transport_nodes=total_potential_transport_nodes,
    min_transpo_stops_per_route=MIN_TRANSPO_STOPS_PER_ROUTE,
    route_stops=route_stops
  )

  weighted_internal_connectivity = weights["w_int"] * internal_connectivity
  weighted_external_connectivity = weights["w_ext"] * external_connectivity

  network_coverage = get_network_coverage(total_network_distance, allowed_edge, edge_len, arcs=arcs)
  weighted_network_coverage = weights["w_cov"] * network_coverage

  vul, q_c_vul = compute_vulnerability(network.graph, adjacency=adjacency)
  vulnerability = normalize_vul_rob(vul, q_c_vul)
  weighted_vulnerability = weights["w_vul"] * vulnerability

  rob, q_c_rob = compute_robustness(network.graph, adjacency=adjacency)
  robustness = normalize_vul_rob(rob, q_c_rob)
  weighted_robustness = weights["w_rob"] * robustness

  redundancy = compute_redundancy(edge_len, arcs=arcs)
  weighted_redundancy = weights["w_red"] * redundancy

  total_weight = (
    weights["w_cov"]
    + weights["w_int"]
    + weights["w_ext"]
    + weights["w_vul"]
    + weights["w_rob"]
    + weights["w_red"]
  )

  weighted_sum = (
    weighted_network_coverage
    + weighted_internal_connectivity
    + weighted_external_connectivity
    + weighted_vulnerability
    + weighted_robustness
    + weighted_redundancy
  )

  return 0.0 if total_weight <= 0 else weighted_sum / total_weight


# stop costs based off singapore minimum size (9m x 3m) with length multiplied by factor of 1x, 1.5x, 2x
# price is computed based off dotr figures (28k per sqm)
def fitness_capex_cost(
    network: Network,
    stop_cost: float,
    stop_sizes: tuple[float, float, float],
    max_degree: tuple[int, int, int],
) -> float:
    area = 0.0
    for _stop, degree in network.graph.degree():
        if degree < 1:
            continue
        if degree <= max_degree[0]:
          area += stop_sizes[0]
        elif degree <= max_degree[1]:
          area += stop_sizes[1]
        else:
          area += stop_sizes[2]

    return area * stop_cost

"""
Z_user(R) = sum_o C_o * sum_d [t_od(R) + theta * m_od(R)]

  C_o - population in the walking catchment of origin stop o
  t_od - in-vehicle travel time from o to d over the multimodal graph (minutes)
  m_od - number of mode/line changes on the least-cost path
  theta - fixed transfer penalty

Notes:
- Walking to and from stops is excluded from t_od
- Rail is a static trunk layer (utils.rail_layer) composed with the candidate jeepney network by utils.route_layer.
- Unreachable pairs are charged the worst observed generalised cost plus theta
Returns user cost (aggregate) or INVALID_NETWORK_COST when the network cannot be scored (e.g. no routes)
"""
def fitness_user_cost(
    network: Network,
    graph_of_stops: nx.MultiDiGraph,
    population_gdf,
    catchment_m: float,
    city: str,
    theta: float = TRANSFER_PENALTY_MIN,
    rail_graph=None,
    jeep_transfer_m: float = JEEP_TRANSFER_MAX_M,
    rail_transfer_m: float = RAIL_TRANSFER_MAX_M,
) -> float:
  rail = rail_graph if rail_graph is not None else get_rail_graph()

  if not network.routes:
    return INVALID_NETWORK_COST

  od = []
  seen = set()
  for route in network.routes:
    for conn in route.route:
      if not conn:
        continue
      for end in (conn[0], conn[-1]):
        if end not in seen:
          seen.add(end)
          od.append(end)

  rail_coords: dict = {}
  if city is not None:
    station_xyz = {}
    for line, info in _LINES.items():
      for name, la, lo in info["stations"]:
        station_xyz[(line, name)] = (la, lo)
    for pair in rail_stations_for(city):
      if pair in station_xyz and pair not in seen:
        seen.add(pair)
        od.append(pair)
        rail_coords[pair] = station_xyz[pair]

  if not od:
    return INVALID_NETWORK_COST

  out = rl.cost_matrix(
    network,
    graph_of_stops,
    rail,
    od,
    theta=theta,
    jeep_transfer_m=jeep_transfer_m,
    rail_transfer_m=rail_transfer_m,
  )
  T, M = out[0], out[1]

  C = origin_population(
    graph_of_stops, od, population_gdf, catchment_m, rail_coords=rail_coords, city=city
  )
  c = np.array([C[n] for n in od], dtype=float)

  if c.sum() <= 0:
    return INVALID_NETWORK_COST

  reachable = np.isfinite(T)

  if not reachable.any():
    return INVALID_NETWORK_COST

  # T excludes theta (route_layer subtracts it per path), so the generalised cost the objective sums is T + theta*M.
  generalised = T + theta * M
  finite_gen = generalised[reachable]

  penalty = float(finite_gen.max()) + theta
  cost = np.where(reachable, generalised, penalty)

  return float((c[:, None] * cost).sum())

def eda_fitness_user_cost(
    network: Network,
    graph_of_stops: nx.MultiDiGraph,
    population_gdf,
    catchment_m: float = CATCHMENT_RADIUS_M,
    theta: float = TRANSFER_PENALTY_MIN,
    rail_graph=None,
    city: str | None = None,
    jeep_transfer_m: float = JEEP_TRANSFER_MAX_M,
    rail_transfer_m: float = RAIL_TRANSFER_MAX_M,
    return_details: bool = False,
):
    def out(cost, **details):
        return (cost, details) if return_details else cost

    rail = rail_graph if rail_graph is not None else get_rail_graph()

    if not network.routes:
        return out(INVALID_NETWORK_COST, n_od=0, reach=0.0)

    od = []
    seen = set()
    for route in network.routes:
        for conn in route.route:
            if not conn:
                continue
            for end in (conn[0], conn[-1]):
                if end not in seen:
                    seen.add(end)
                    od.append(end)

    n_jeep_od = len(od)

    rail_coords: dict = {}
    if city is not None:
        station_xyz = {}
        for line, info in _LINES.items():
            for name, la, lo in info["stations"]:
                station_xyz[(line, name)] = (la, lo)
        for pair in rail_stations_for(city):
            if pair in station_xyz and pair not in seen:
                seen.add(pair)
                od.append(pair)
                rail_coords[pair] = station_xyz[pair]

    if not od:
        return out(INVALID_NETWORK_COST, n_od=0, reach=0.0)

    costs = rl.cost_matrix(
        network,
        graph_of_stops,
        rail,
        od,
        theta=theta,
        jeep_transfer_m=jeep_transfer_m,
        rail_transfer_m=rail_transfer_m,
    )
    T, M = costs[0], costs[1]

    C = origin_population(
        graph_of_stops, od, population_gdf, catchment_m, rail_coords=rail_coords, city=city
    )
    c = np.array([C[n] for n in od], dtype=float)

    if c.sum() <= 0:
        return out(INVALID_NETWORK_COST, n_od=len(od), reach=0.0)

    reachable = np.isfinite(T)

    if not reachable.any():
        return out(
            INVALID_NETWORK_COST,
            n_od=len(od),
            reach=0.0,
            pop_total=float(c.sum()),
        )

    generalised = T + theta * M
    finite_gen = generalised[reachable]

    penalty = float(finite_gen.max()) + theta
    cost = np.where(reachable, generalised, penalty)

    z = float((c[:, None] * cost).sum())

    return out(
        z,
        n_od=len(od),
        n_jeep_od=n_jeep_od,
        n_rail_od=len(od) - n_jeep_od,
        reach=float(reachable.mean()),
        n_unreachable=int((~reachable).sum()),
        mean_min=float(T[reachable].mean()),
        mean_changes=float(M[reachable].mean()),
        mean_generalised_min=float(finite_gen.mean()),
        pop_total=float(c.sum()),
        pop_rail=float(c[n_jeep_od:].sum()),
        penalty_min=penalty,
    )

def compute_internal_connectivity(
  network: Network,
  route_stops: dict,
  target_node_ratio: float = TARGET_NODE_RATIO,
  min_intersections_per_route: int = MIN_INTERSECTIONS_PER_ROUTE,
) -> float:
  """
  n_i = the number of intersection nodes, aka when 2+ routes stop there in the same direction
  N_i = nodes * target node ratio, decimals truncated and floor set at 1
  r_i = the number of routes containing intersection nodes >= intersection threshold
  R_i = the number of routes
  internal connectivity = 0.5 * [MIN(n_i / N_i, 1.0) + (r_i / R_i IF R_i > 0 ELSE 0.0)]
  """
  total_nodes = len(network.graph.nodes())
  if total_nodes == 0 or not network.routes:
    return 0.0

  by_direction: dict = {}  # direction -> {stop: route_id of first route seen}
  intersection_nodes: dict = {}  # direction -> {stop}

  for route in network.routes:
    per_stop = by_direction.get(route.direction)
    if per_stop is None:
      per_stop = by_direction[route.direction] = {}
    interchange = intersection_nodes.get(route.direction)
    if interchange is None:
      interchange = intersection_nodes[route.direction] = set()

    for stop in route_stops[route.route_id]:
      first = per_stop.get(stop)
      if first is None:
        per_stop[stop] = route.route_id
      elif first != route.route_id:
        interchange.add(stop)

  n_i = len({stop for stops in intersection_nodes.values() for stop in stops})
  N_i = max(1, int(total_nodes * target_node_ratio))
  r_i = 0

  for route in network.routes:
    interchange = intersection_nodes.get(route.direction)
    if (
      interchange
      and len(route_stops[route.route_id] & interchange) >= min_intersections_per_route
    ):
      r_i += 1

  R_i = len(network.routes)
  return 0.5 * (min(n_i / N_i, 1.0) + (r_i / R_i if R_i > 0 else 0.0))


def compute_external_connectivity(
  network: Network,
  total_potential_transport_nodes: int,
  route_stops: dict,
  min_transpo_stops_per_route: int = MIN_TRANSPO_STOPS_PER_ROUTE,
) -> float:
  total_nodes = len(network.graph.nodes())
  if total_nodes == 0:
    return 0.0

  total_routes = len(route_stops)

  if total_routes == 0:
    return 0.0

  transpo_nodes = {
    node
    for node, node_data in network.graph.nodes(data=True)
    if node_data.get("isTranspo", False)
  }

  n_e = len(transpo_nodes)
  N_e = max(1, total_potential_transport_nodes)

  r_e = sum(
    1
    for stops in route_stops.values()
    if len(stops & transpo_nodes) >= min_transpo_stops_per_route
  )

  return 0.5 * (min(n_e / N_e, 1.0) + (r_e / total_routes))

def compute_vulnerability(
  network_graph: nx.MultiDiGraph,
  adjacency: csr_matrix | None = None,
) -> tuple[float, float]:
  nodes = list(network_graph.adj)
  N = len(nodes)
  if N == 0:
    return 0.0, 0.0

  index = {node: i for i, node in enumerate(nodes)}
  rows: list[int] = []
  cols: list[int] = []
  counts: list[int] = []
  for node, successors in network_graph.adj.items():
    i = index[node]
    for successor, keys in successors.items():
      rows.append(i)
      cols.append(index[successor])
      counts.append(len(keys))

  out_counts = csr_matrix(
    (np.array(counts, dtype=np.int64), (rows, cols)), shape=(N, N)
  )
  in_counts = out_counts.T.tocsr()
  adjacency_matrix = (out_counts + in_counts) != 0 if adjacency is None else adjacency

  degree = (
    np.asarray(out_counts.sum(axis=1)).ravel()
    + np.asarray(in_counts.sum(axis=1)).ravel()
  ).astype(np.int64)

  num_removals = max(1, int(N * 0.1))
  alive = np.ones(N, dtype=bool)
  s_values = []

  for _ in range(num_removals):
    max_node = int(np.where(alive, degree, -1).argmax())
    alive[max_node] = False

    lo = out_counts.indptr[max_node]
    hi = out_counts.indptr[max_node + 1]
    degree[out_counts.indices[lo:hi]] -= out_counts.data[lo:hi]

    lo = in_counts.indptr[max_node]
    hi = in_counts.indptr[max_node + 1]
    degree[in_counts.indices[lo:hi]] -= in_counts.data[lo:hi]

    keep = np.flatnonzero(alive)
    if keep.size == 0:
      break
    _n_components, labels = connected_components(
      adjacency_matrix[keep][:, keep], directed=False
    )
    s_values.append(int(np.bincount(labels).max()) / N)

  q_c = num_removals / N
  R_prime = sum(s_values) / N
  return R_prime, q_c

def compute_robustness(
  network_graph: nx.MultiDiGraph,
  adjacency: csr_matrix
) -> tuple[float, float]:
  nodes = list(network_graph.adj)
  N = len(nodes)
  if N == 0:
    return 0.0, 0.0

  num_removals = max(1, int(N * 0.1))
  alive = np.ones(N, dtype=bool)
  s_values = []

  for selected_node in random.sample(range(N), num_removals):
    alive[selected_node] = False

    keep = np.flatnonzero(alive)
    if keep.size == 0:
      break
    _n_components, labels = connected_components(
      adjacency[keep][:, keep], directed=False
    )
    s_values.append(int(np.bincount(labels).max()) / N)

  q_c = num_removals / N
  R_prime = sum(s_values) / N
  return R_prime, q_c

# Red(R) = sum of L(a) for a in A_multi / sum of L(a) for a in A_serviced
def compute_redundancy(
    edge_len: dict[frozenset, float],
    arcs: dict[tuple, set],
) -> float:
    serviced = 0.0
    multi = 0.0
    for arc, routes in arcs.items():
        length = edge_len.get(frozenset(arc))
        if length is None:
            continue
        serviced += length
        if len(routes) >= 2:
            multi += length

    return 0.0 if serviced <= 0 else multi / serviced

def get_network_coverage(
    total_network_distance: float,
    allowed_edge: dict[frozenset, bool],
    edge_len: dict[frozenset, float],
    arcs: dict[tuple, set],
) -> float:
    if total_network_distance == 0:
        return 0.0

    serviced: set[frozenset] = set()
    covered = 0.0
    for arc in arcs:
        segment = frozenset(arc)
        if segment in serviced:
            continue
        if not allowed_edge.get(segment, False):
            continue
        serviced.add(segment)
        covered += edge_len.get(segment, 0.0)

    return covered / total_network_distance


def normalize_vul_rob(vul_rob: float, q_c: float) -> float:
    # With fixed q_c = 10% removals, max possible R' is q_c
    # because R' = (1/N) * sum s(q), and each s(q) <= 1.
    return 0.0 if q_c <= 0 else vul_rob / q_c


def get_rail_graph() -> nx.Graph:
    """Build and cache the static rail trunk graph (thread-safe)."""
    if "rail" not in _RAIL_CACHE:
        with _CACHE_LOCK:
            if "rail" not in _RAIL_CACHE:
                from utils.route_layer import build_rail_graph
                _RAIL_CACHE["rail"] = build_rail_graph()
    return _RAIL_CACHE["rail"]

_POP_CACHE: dict = {}

def origin_population(
  graph_of_stops: nx.MultiDiGraph,
  route_nodes,
  population_gdf,
  catchment_m: float,
  rail_coords: dict | None = None,
  city: str | None = None,
) -> dict:
  cached = _POP_CACHE.get(city)
  if cached is None or cached[0] is not population_gdf:
    lon = population_gdf["longitude"].to_numpy()
    lat = population_gdf["latitude"].to_numpy()
    pop = population_gdf["phl_general_2020"].to_numpy()
    coslat = np.cos(np.radians(np.mean(lat)))
    tree = cKDTree(np.column_stack((lon * 111_320.0 * coslat, lat * 111_320.0)))
    cached = (population_gdf, pop, coslat, tree)
    _POP_CACHE[city] = cached

  _cached_gdf, pop, coslat, tree = cached
  rail_coords = rail_coords or {}
  C = {}
  for n in route_nodes:
    if n in rail_coords:
      y, x = rail_coords[n]
    else:
      d = graph_of_stops.nodes.get(n)
      if d is None:
        C[n] = 0.0
        continue
      y, x = d.get("y", d.get("lat")), d.get("x", d.get("lon"))
    if y is None or x is None:
      C[n] = 0.0
      continue

    idx = tree.query_ball_point((x * 111_320.0 * coslat, y * 111_320.0), catchment_m)
    C[n] = float(pop[idx].sum()) if idx else 0.0
  return C

def _pct_tag(w: float) -> str:
    """
    Convert weight (0.6) -> '60', (0.02) -> '02', (1.0) -> '100'
    Assumes weights are in [0,1].
    """
    return f"{round(w * 100):02d}"


def make_run_tag(weights: dict[str, float]) -> str:
    return (
        f"cov{_pct_tag(weights['w_cov'])}"
        f"_int{_pct_tag(weights['w_int'])}"
        f"_ext{_pct_tag(weights['w_ext'])}"
        f"_vul{_pct_tag(weights['w_vul'])}"
        f"_rob{_pct_tag(weights['w_rob'])}"
    )