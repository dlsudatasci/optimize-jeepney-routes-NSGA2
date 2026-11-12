import copy
import random

import networkx as nx

from genetic_algorithm.schema import Network, Route


def calc_jaccard_sim(route1: Route, route2: Route) -> float:
  edges1 = set(standardize_route(route1.route))
  edges2 = set(standardize_route(route2.route))

  if not edges1 or not edges2:
    return 0.0

  intersection = edges1.intersection(edges2)
  union = edges1.union(edges2)
  return len(intersection) / len(union)


def group_into_lines(routes: list[Route]):
  lines = {}
  for route in routes:
    if route.line_id not in lines:
      lines[route.line_id] = []
    lines[route.line_id].append(route)
  return list(lines.values())


# sim threshold determines how much of the edges have to be the same to determine if it is to be repaired
def repair_chromosome(
  child_lines: list[tuple[int, list[Route]]],
  spare_pool: list[tuple[int, list[Route]]],
  similarity_threshold: float = 1.0,
):
  repaired_lines = []
  seen_standardized = []

  random.shuffle(spare_pool)  # Shuffle to ensure stochasticity

  for parent_idx, line in child_lines:
    fwd_route = next((r for r in line if r.direction.lower() == "forward"), line[0])
    std_route = standardize_route(fwd_route.route)

    # Check against already accepted routes for exact matches
    is_invalid = std_route in seen_standardized

    if not is_invalid:
      for accepted_std in seen_standardized:
        # Reconstruct dummy routes for the similarity function
        dummy_r1, dummy_r2 = (
          Route(list(std_route), "", 0, 0, ""),
          Route(list(accepted_std), "", 0, 0, ""),
        )

        if calc_jaccard_sim(dummy_r1, dummy_r2) >= similarity_threshold:
          is_invalid = True
          break

    if is_invalid:
      # If route is invalid (aka similar to another) it is to be repaired.
      while spare_pool:
        spare_parent_idx, spare_line = spare_pool.pop(0)
        spare_fwd = next(
          (r for r in spare_line if r.direction.lower() == "forward"), spare_line[0]
        )
        spare_std = standardize_route(spare_fwd.route)

        if spare_std not in seen_standardized:
          repaired_lines.append((spare_parent_idx, copy.deepcopy(spare_line)))
          seen_standardized.append(spare_std)
          break
      # Note: If spare_pool runs out, the duplicate is simply dropped,

    else:
      repaired_lines.append((parent_idx, copy.deepcopy(line)))
      seen_standardized.append(std_route)

  return repaired_lines


# V3 - Crossover with post-op repair
def crossover(network1: Network, network2: Network):
  lines1 = [(0, line) for line in group_into_lines(network1.routes)]
  lines2 = [(1, line) for line in group_into_lines(network2.routes)]

  min_length = min(len(lines1), len(lines2))

  if min_length <= 1:
    return copy.deepcopy(network1), copy.deepcopy(network2), False

  split_idx = random.randint(1, min_length - 1)

  child1_raw = lines1[:split_idx] + lines2[split_idx:]
  child2_raw = lines2[:split_idx] + lines1[split_idx:]

  child1_spare = lines1[split_idx:] + lines2[:split_idx]
  child2_spare = lines2[split_idx:] + lines1[:split_idx]

  child1_repaired = repair_chromosome(child1_raw, child1_spare)
  child2_repaired = repair_chromosome(child2_raw, child2_spare)

  def build_network_from_routes(
    lines: list[tuple[int, list[Route]]],
    parent_graphs: tuple[nx.MultiDiGraph, nx.MultiDiGraph],
  ):
    child_graph = nx.MultiDiGraph()
    final_routes = []

    for line_id, (parent_idx, line) in enumerate(lines):
      src_graph = parent_graphs[parent_idx]

      for route in line:
        old_route_id = route.route_id
        new_route_id = f"{line_id}-{route.direction[:1].upper()}"

        new_route = Route(
          route=[copy.deepcopy(r) for r in route.route],
          route_id=new_route_id,
          length=route.length,
          line_id=line_id,
          direction=route.direction,
        )

        for connection in route.route:
          u = connection[0]
          v = connection[-1]
          child_graph.add_node(u, **src_graph.nodes[u])
          child_graph.add_node(v, **src_graph.nodes[v])

          edge_data = src_graph.get_edge_data(u, v, key=old_route_id)
          if edge_data:
            child_graph.add_edge(u, v, key=new_route_id, **edge_data)

        final_routes.append(new_route)

    return Network(final_routes, child_graph)

  child1 = build_network_from_routes(child1_repaired, (network1.graph, network2.graph))
  child2 = build_network_from_routes(child2_repaired, (network1.graph, network2.graph))

  return child1, child2, True


# Standardizes the route for more efficiency in comparing routes
def standardize_route(route):
  return tuple(tuple(sorted(connection)) for connection in route)
