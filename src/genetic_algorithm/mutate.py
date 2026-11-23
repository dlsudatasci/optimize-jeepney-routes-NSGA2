import random

import networkx as nx

from config.config import MAX_DISTANCE
from genetic_algorithm.schema import Network
from utils.route_utils import haversine

# V2 - Mutation

# Modify the stop connections of a random route in the network
# Randomly select a route and randomly select a stop in that route
# Then randomly select another stop that is a not too far from the selected stop based on threshold
# Swap connections with that stop
def mutate(network: Network, graph_of_stops: nx.MultiDiGraph, walk_dist: int):
  valid_routes = [r for r in network.routes if len(r.route) >= 2]
  if not valid_routes:
    return False

  # Randomly select a route
  route_obj = random.choice(valid_routes)
  route = route_obj.route
  route_id = route_obj.route_id
  graph = network.graph

  # Randomly select a stop in the route from start to dest
  stops = [c[0] for c in route] + [route[-1][-1]]
  stop_idx = random.randint(0, len(stops) - 1)
  old_stop = stops[stop_idx]

  is_start = (stop_idx == 0)
  is_end = (stop_idx == len(stops) - 1)

  prev_node = None if is_start else stops[stop_idx - 1]
  next_node = None if is_end else stops[stop_idx + 1]

  used_stops = set(stops)
  old_pos = (graph_of_stops.nodes[old_stop]["y"], graph_of_stops.nodes[old_stop]["x"]) # (y, x)
  nearby_stops = [
    n
    for n, d in graph_of_stops.nodes(data=True)
    if n not in used_stops and haversine(old_pos, (d["y"], d["x"])) <= walk_dist / 1000
  ]

  random.shuffle(nearby_stops)

  # Calculate route length without the edges attached to old_stop
  removed_dist = 0.0
  if not is_start:
    removed_dist += graph.get_edge_data(prev_node, old_stop, route_id)["distance"]
  if not is_end:
    removed_dist += graph.get_edge_data(old_stop, next_node, route_id)["distance"]

  subset_distance = route_obj.length - removed_dist
  min_distance = min(7.0, 0.35 * MAX_DISTANCE)

  # Search for a new connection
  for new_stop in nearby_stops:
    if (not is_start and graph.has_edge(prev_node, new_stop, route_id)) or (not is_end and graph.has_edge(new_stop, next_node, route_id)):
      continue

    try:
      path1 = nx.shortest_path(graph_of_stops, prev_node, new_stop, weight="length") if not is_start else None
      path2 = nx.shortest_path(graph_of_stops, new_stop, next_node, weight="length") if not is_end else None
    except nx.NetworkXNoPath:
      continue

    dist1 = get_distance_path(path1, graph_of_stops) if path1 else 0.0
    dist2 = get_distance_path(path2, graph_of_stops) if path2 else 0.0
    new_length = subset_distance + dist1 + dist2

    if min_distance <= new_length <= MAX_DISTANCE:
      graph.add_node(new_stop, **graph_of_stops.nodes[new_stop])

      if not is_start:
        graph.remove_edge(prev_node, old_stop, route_id)
        graph.add_edge(prev_node, new_stop, key=route_id, road_path=path1, distance=dist1)
        route[stop_idx - 1] = path1

      if not is_end:
        graph.remove_edge(old_stop, next_node, route_id)
        graph.add_edge(new_stop, next_node, key=route_id, road_path=path2, distance=dist2)
        route[stop_idx] = path2

      if graph.degree(old_stop) == 0:
        graph.remove_node(old_stop)

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