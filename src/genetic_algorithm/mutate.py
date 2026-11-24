import random

import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from config.config import MAX_DISTANCE, MUTATE_WEIGHTS
from genetic_algorithm.schema import Network

_ROUTING_TABLE: StopRoutingTable = None
_ROUTING_GRAPH_ID = None

def _get_routing_table(graph_of_stops: nx.MultiDiGraph) -> StopRoutingTable:
  """Lazily build and cache the all-pairs StopRoutingTable once per graph."""
  global _ROUTING_TABLE, _ROUTING_GRAPH_ID
  if _ROUTING_TABLE is None or _ROUTING_GRAPH_ID != id(graph_of_stops):
    _ROUTING_TABLE = StopRoutingTable(graph_of_stops)
    _ROUTING_GRAPH_ID = id(graph_of_stops)
  return _ROUTING_TABLE

# V3 - Mutation w/ multi-operators (Add, Remove, Extend, Shorten)
def mutate(network: Network, graph_of_stops: nx.MultiDiGraph, walk_dist: int) -> bool:
  valid_routes = [r for r in network.routes if len(r.route) >= 2]
  if not valid_routes:
    return False

  table = _get_routing_table(graph_of_stops)

  # Randomly select a route
  route_obj = random.choice(valid_routes)

  feats = [
    insert_stop,
    remove_stop,
    add_terminal_stop,
    remove_terminal_stop,
    # Just add another mutate feature here
  ]

  chosen = random.choices(feats, weights=MUTATE_WEIGHTS, k=1)[0]

  return chosen(route_obj, network, graph_of_stops, walk_dist, table)

def insert_stop(route_obj, network: Network, graph_of_stops: nx.MultiDiGraph, walk_dist: int, table: StopRoutingTable) -> bool:
  """Split an existing segment (u -> v) into (u -> w -> v) using a nearby stop w."""
  route = route_obj.route
  route_id = route_obj.route_id
  graph = network.graph

  seg_idx = random.randint(0, len(route) - 1)
  u, v = route[seg_idx][0], route[seg_idx][-1]

  old_edge = graph.get_edge_data(u, v, route_id)
  if old_edge is None:
    return False

  subset_distance = route_obj.length - old_edge["distance"]
  remaining_budget = MAX_DISTANCE - subset_distance
  if remaining_budget <= 0:
    return False

  search_km = min(max(walk_dist / 1000.0, 1.5), remaining_budget)
  used_stops = set(_get_stops(route))

  # Query road-reachable stops from u within search_km directly from dist_km
  candidates = [n for n in table.get_outbound_neighbors(u, search_km) if n not in used_stops]
  random.shuffle(candidates)

  min_dist = _min_distance()

  for new_stop in candidates:
    if graph.has_edge(u, new_stop, route_id) or graph.has_edge(new_stop, v, route_id):
      continue

    dist1 = table.get_distance(u, new_stop)
    if subset_distance + dist1 > MAX_DISTANCE:
      continue

    dist2 = table.get_distance(new_stop, v)
    new_length = subset_distance + dist1 + dist2

    if min_dist <= new_length <= MAX_DISTANCE:
      path1 = table.get_path(u, new_stop)
      path2 = table.get_path(new_stop, v)
      if path1 is None or path2 is None:
        continue

      graph.add_node(new_stop, **graph_of_stops.nodes[new_stop])
      graph.remove_edge(u, v, route_id)
      graph.add_edge(u, new_stop, key=route_id, road_path=path1, distance=dist1)
      graph.add_edge(new_stop, v, key=route_id, road_path=path2, distance=dist2)

      route[seg_idx : seg_idx + 1] = [path1, path2]
      route_obj.length = new_length
      return True

  return False

def remove_stop(route_obj, network: Network, graph_of_stops: nx.MultiDiGraph, walk_dist: int, table: StopRoutingTable) -> bool:
  """Shortcut an intermediate stop (u -> v -> w) directly into (u -> w)."""
  route = route_obj.route
  if len(route) < 3:
    return False  # Keep at least 2 segments (3 stops)

  route_id = route_obj.route_id
  graph = network.graph
  stops = _get_stops(route)

  stop_idx = random.randint(1, len(stops) - 2)
  u, old_stop, w = stops[stop_idx - 1], stops[stop_idx], stops[stop_idx + 1]

  if graph.has_edge(u, w, route_id):
    return False

  edge1 = graph.get_edge_data(u, old_stop, route_id)
  edge2 = graph.get_edge_data(old_stop, w, route_id)
  if edge1 is None or edge2 is None:
    return False

  shortcut_dist = table.get_distance(u, w)
  if np.isinf(shortcut_dist):
    return False

  new_length = route_obj.length - edge1["distance"] - edge2["distance"] + shortcut_dist

  if _min_distance() <= new_length <= MAX_DISTANCE:
    shortcut_path = table.get_path(u, w)
    if shortcut_path is None:
      return False

    graph.remove_edge(u, old_stop, route_id)
    graph.remove_edge(old_stop, w, route_id)
    graph.add_edge(u, w, key=route_id, road_path=shortcut_path, distance=shortcut_dist)

    if graph.degree(old_stop) == 0:
      graph.remove_node(old_stop)

    route[stop_idx - 1 : stop_idx + 1] = [shortcut_path]
    route_obj.length = new_length
    return True

  return False

def add_terminal_stop(route_obj, network: Network, graph_of_stops: nx.MultiDiGraph, walk_dist: int, table: StopRoutingTable) -> bool:
  """Extend the route past its start (new -> start) or end (end -> new)."""
  route = route_obj.route
  route_id = route_obj.route_id
  graph = network.graph
  stops = _get_stops(route)
  used_stops = set(stops)

  remaining_budget = MAX_DISTANCE - route_obj.length
  if remaining_budget <= 0.2:
    return False

  at_start = random.choice([True, False])
  anchor = stops[0] if at_start else stops[-1]
  search_km = min(max(walk_dist / 1000.0, 2.0), remaining_budget)
  if search_km < 0.2:
    return False

  # Inbound road neighbors if prepending to start; outbound if appending to end
  raw_neighbors = (
    table.get_inbound_neighbors(anchor, search_km, min_km=0.2)
    if at_start
    else table.get_outbound_neighbors(anchor, search_km, min_km=0.2)
  )
  candidates = [n for n in raw_neighbors if n not in used_stops]
  random.shuffle(candidates)

  min_dist = _min_distance()

  for new_stop in candidates:
    u, v = (new_stop, anchor) if at_start else (anchor, new_stop)
    if graph.has_edge(u, v, route_id):
      continue

    ext_dist = table.get_distance(u, v)
    new_length = route_obj.length + ext_dist

    if min_dist <= new_length <= MAX_DISTANCE:
      ext_path = table.get_path(u, v)
      if ext_path is None:
        continue

      graph.add_node(new_stop, **graph_of_stops.nodes[new_stop])
      graph.add_edge(u, v, key=route_id, road_path=ext_path, distance=ext_dist)

      if at_start:
        route.insert(0, ext_path)
      else:
        route.append(ext_path)

      route_obj.length = new_length
      return True

  return False

def remove_terminal_stop(route_obj, network: Network, graph_of_stops: nx.MultiDiGraph, walk_dist: int, table: StopRoutingTable) -> bool:
  """Trim the first or last segment of the route."""
  route = route_obj.route
  if len(route) < 3:
    return False  # Keep at least 2 segments (3 stops)

  route_id = route_obj.route_id
  graph = network.graph

  sides = [True, False]
  random.shuffle(sides)

  for at_start in sides:
    seg = route[0] if at_start else route[-1]
    u, v = seg[0], seg[-1]
    removed_stop = u if at_start else v

    edge = graph.get_edge_data(u, v, route_id)
    if edge is None:
      continue

    new_length = route_obj.length - edge["distance"]
    if _min_distance() <= new_length <= MAX_DISTANCE:
      graph.remove_edge(u, v, route_id)
      if graph.degree(removed_stop) == 0:
        graph.remove_node(removed_stop)

      if at_start:
        route.pop(0)
      else:
        route.pop()

      route_obj.length = new_length
      return True

  return False

def get_distance_path(path: list, graph_of_stops: nx.MultiDiGraph):
  total = 0.0
  for i in range(len(path) - 1):
    edge_dict = graph_of_stops.get_edge_data(path[i], path[i + 1])
    edge_data = min(edge_dict.values(), key=lambda d: d.get("length", float("inf")))
    total += edge_data["length"] / 1000.0
  return total

def _min_distance() -> float:
  return min(7.0, 0.35 * MAX_DISTANCE)

def _get_stops(route: list[list]) -> list:
  return [c[0] for c in route] + [route[-1][-1]]

class StopRoutingTable:
  def __init__(self, graph_of_stops: nx.MultiDiGraph):
    self.nodes = list(graph_of_stops.nodes())
    self.node_to_idx = {n: i for i, n in enumerate(self.nodes)}
    n = len(self.nodes)

    edges = {}
    for u, v, data in graph_of_stops.edges(data=True):
      length_km = data.get("length", float("inf")) / 1000.0
      pair = (self.node_to_idx[u], self.node_to_idx[v])
      if pair not in edges or length_km < edges[pair]:
        edges[pair] = length_km

    rows = np.fromiter((u for u, _ in edges), dtype=np.int32, count=len(edges))
    cols = np.fromiter((v for _, v in edges), dtype=np.int32, count=len(edges))
    weights = np.fromiter(edges.values(), dtype=np.float64, count=len(edges))

    adj = csr_matrix((weights, (rows, cols)), shape=(n, n))
    self.dist_km, self.predecessors = dijkstra(adj, directed=True, return_predecessors=True)

  def get_distance(self, u, v) -> float:
    """O(1) road distance in km (inf if unreachable)."""
    return float(self.dist_km[self.node_to_idx[u], self.node_to_idx[v]])

  def get_outbound_neighbors(self, u, max_km: float, min_km: float = 0.0):
    i = self.node_to_idx[u]
    row = self.dist_km[i]
    idxs = np.flatnonzero((row >= min_km) & (row <= max_km))
    return [self.nodes[j] for j in idxs if j != i]

  def get_inbound_neighbors(self, v, max_km: float, min_km: float = 0.0):
    j = self.node_to_idx[v]
    col = self.dist_km[:, j]
    idxs = np.flatnonzero((col >= min_km) & (col <= max_km))
    return [self.nodes[i] for i in idxs if i != j]

  def get_path(self, u, v):
    """Reconstruct shortest node path from u to v, None if unreachable."""
    i, j = self.node_to_idx[u], self.node_to_idx[v]
    if np.isinf(self.dist_km[i, j]):
      return None

    preds = self.predecessors[i]
    nodes = self.nodes

    path = [v]
    curr = j
    while curr != i:
      curr = preds[curr]
      if curr < 0:
        return None
      path.append(nodes[curr])
    path.reverse()
    return path