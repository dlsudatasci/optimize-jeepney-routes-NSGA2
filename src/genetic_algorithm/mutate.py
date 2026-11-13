import random

import networkx as nx
from geopy.distance import geodesic

from config.config import MAX_DISTANCE
from genetic_algorithm.schema import Network

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
    n for n, d in graph_of_stops.nodes(data=True)
    if n not in used_stops
    and geodesic(old_pos, (d["y"], d["x"])).meters <= walk_dist
  ]

  random.shuffle(nearby_stops)

  # Calculate route length without the edges attached to old_stop
  removed_dist = 0.0
  if not is_start:
    removed_dist += graph.get_edge_data(prev_node, old_stop, route_id)["distance"]
  if not is_end:
    removed_dist += graph.get_edge_data(old_stop, next_node, route_id)["distance"]
  subset_distance = route_obj.length - removed_dist

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

  if new_length <= MAX_DISTANCE:
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
  return sum(
    geodesic(
      (graph_of_stops.nodes[path[i]]["y"], graph_of_stops.nodes[path[i]]["x"]),
      (graph_of_stops.nodes[path[i + 1]]["y"], graph_of_stops.nodes[path[i + 1]]["x"]),
    ).kilometers
    for i in range(len(path) - 1)
  )