import networkx as nx
import random

from config.config import TARGET_NODE_RATIO, MIN_INTERSECTIONS_PER_ROUTE, MIN_TRANSPO_STOPS_PER_ROUTE

def fitness_score(road_snapped_network_graph, weights, total_potential_transport_nodes):
    internal_connectivity, internal_details = compute_internal_connectivity(
        road_snapped_network_graph,
        target_node_ratio=TARGET_NODE_RATIO,
        min_intersections_per_route=MIN_INTERSECTIONS_PER_ROUTE
    )

    external_connectivity, external_details = compute_external_connectivity(
        road_snapped_network_graph,
        total_potential_transport_nodes=total_potential_transport_nodes,
        min_transpo_stops_per_route=MIN_TRANSPO_STOPS_PER_ROUTE
    )

    weighted_internal_connectivity = weights["w_int"] * internal_connectivity
    weighted_external_connectivity = weights["w_ext"] * external_connectivity

    network_coverage = get_network_coverage(road_snapped_network_graph)
    weighted_network_coverage = weights["w_cov"] * network_coverage

    vul, q_c_vul = compute_vulnerability(road_snapped_network_graph)
    vulnerability = normalize_vul_rob(vul, q_c_vul)
    weighted_vulnerability = weights["w_vul"] * vulnerability

    rob, q_c_rob = compute_robustness(road_snapped_network_graph)
    robustness = normalize_vul_rob(rob, q_c_rob)
    weighted_robustness = weights["w_rob"] * robustness

    data = {
        "Coverage": weighted_network_coverage,
        "Internal Connectivity": weighted_internal_connectivity,
        "External Connectivity": weighted_external_connectivity,
        "Vulnerability": weighted_vulnerability,
        "Robustness": weighted_robustness,

        "Coverage Raw": network_coverage,
        "Internal Connectivity Raw": internal_connectivity,
        "External Connectivity Raw": external_connectivity,
        "Vulnerability Raw": vulnerability,
        "Robustness Raw": robustness,

        "Total Network Nodes": len(road_snapped_network_graph.nodes()),
        "Total Potential Transport Nodes": total_potential_transport_nodes,

        "n_i": internal_details["n_i"],
        "N_i": internal_details["N_i"],
        "r_i": internal_details["r_i"],
        "R_i": internal_details["R_i"],
        "Min Intersections Per Route": internal_details["min_intersections_per_route"],

        "n_e": external_details["n_e"],
        "N_e": external_details["N_e"],
        "r_e": external_details["r_e"],
        "R_e": external_details["R_e"],
        "Min Transpo Stops Per Route": external_details["min_transpo_stops_per_route"],

        "Target Node Ratio": TARGET_NODE_RATIO,

        "q_c Vulnerability": q_c_vul,
        "q_c Robustness": q_c_rob,
    }

    total_weight = (
        weights["w_cov"]
        + weights["w_int"]
        + weights["w_ext"]
        + weights["w_vul"]
        + weights["w_rob"]
    )

    weighted_sum = (
        weighted_network_coverage
        + weighted_internal_connectivity
        + weighted_external_connectivity
        + weighted_vulnerability
        + weighted_robustness
    )

    fitness_score = 0.0 if total_weight <= 0 else weighted_sum / total_weight

    return fitness_score, data

def compute_internal_connectivity(
    network,
    target_node_ratio=TARGET_NODE_RATIO,
    min_intersections_per_route=MIN_INTERSECTIONS_PER_ROUTE
):
    total_nodes = len(network.nodes())
    if total_nodes == 0:
        return 0.0, {
            "n_i": 0,
            "N_i": 0,
            "r_i": 0,
            "R_i": 0,
            "min_intersections_per_route": min_intersections_per_route,
        }

    route_family_stops = get_route_family_stop_map(network)
    total_route_families = len(route_family_stops)

    if total_route_families == 0:
        return 0.0, {
            "n_i": 0,
            "N_i": max(1, int(total_nodes * target_node_ratio)),
            "r_i": 0,
            "R_i": 0,
            "min_intersections_per_route": min_intersections_per_route,
        }

    # Identify intersection nodes: nodes touched by >1 unique route family
    node_route_families = {}
    for route_family, stops in route_family_stops.items():
        for stop in stops:
            node_route_families.setdefault(stop, set()).add(route_family)

    intersection_nodes = {
        node for node, families in node_route_families.items()
        if len(families) > 1
    }

    n_i = len(intersection_nodes)
    N_i = max(1, int(total_nodes * target_node_ratio))

    # r_i = routes with at least n intersection nodes
    r_i = 0
    for route_family, stops in route_family_stops.items():
        intersection_count = sum(1 for stop in stops if stop in intersection_nodes)
        if intersection_count >= min_intersections_per_route:
            r_i += 1

    R_i = total_route_families

    internal_connectivity = 0.5 * (
        min(n_i / N_i, 1.0) +
        (r_i / R_i if R_i > 0 else 0.0)
    )

    details = {
        "total_nodes": total_nodes,
        "n_i": n_i,
        "N_i": N_i,
        "r_i": r_i,
        "R_i": R_i,
        "min_intersections_per_route": min_intersections_per_route,
    }

    return internal_connectivity, details

def compute_external_connectivity(
    network,
    total_potential_transport_nodes,
    min_transpo_stops_per_route=MIN_TRANSPO_STOPS_PER_ROUTE
):
    total_nodes = len(network.nodes())
    if total_nodes == 0:
        return 0.0, {
            "total_nodes": 0,
            "n_e": 0,
            "N_e": max(1, total_potential_transport_nodes),
            "r_e": 0,
            "R_e": 0,
            "min_transpo_stops_per_route": min_transpo_stops_per_route,
        }

    route_family_stops = get_route_family_stop_map(network)
    total_route_families = len(route_family_stops)

    transpo_nodes = {
        node for node, node_data in network.nodes(data=True)
        if node_data.get("isTranspo", False) is True
    }

    n_e = len(transpo_nodes)
    N_e = max(1, total_potential_transport_nodes)

    if total_route_families == 0:
        return 0.0, {
            "total_nodes": total_nodes,
            "n_e": n_e,
            "N_e": N_e,
            "r_e": 0,
            "R_e": 0,
            "min_transpo_stops_per_route": min_transpo_stops_per_route,
        }

    r_e = 0
    for route_family, stops in route_family_stops.items():
        transpo_count = sum(1 for stop in stops if stop in transpo_nodes)
        if transpo_count >= min_transpo_stops_per_route:
            r_e += 1

    R_e = total_route_families

    external_connectivity = 0.5 * (
        min(n_e / N_e, 1.0) +
        (r_e / R_e if R_e > 0 else 0.0)
    )

    details = {
        "total_nodes": total_nodes,
        "n_e": n_e,
        "N_e": N_e,
        "r_e": r_e,
        "R_e": R_e,
        "min_transpo_stops_per_route": min_transpo_stops_per_route,
    }

    return external_connectivity, details

def compute_vulnerability(network_graph):
    G = network_graph.copy()
    N = len(G.nodes())
    if N == 0:
        return 0.0, 0.0

    num_removals = max(1, int(N * 0.1))
    s_values = []

    for k in range(1, num_removals + 1):
        if len(G.nodes()) == 0:
            break

        deg_view = G.degree()
        max_node, _ = max_degree_node_first(deg_view)
        G.remove_node(max_node)

        lwcc_size = largest_weakly_connected_component_size(G)
        s_q = lwcc_size / N
        s_values.append(s_q)

    q_c = num_removals / N
    R_prime = sum(s_values) / N
    return R_prime, q_c

def compute_robustness(network_graph):
    G = network_graph.copy()
    N = len(G.nodes())
    if N == 0:
        return 0.0, 0.0

    num_removals = max(1, int(N * 0.1))
    s_values = []

    for k in range(1, num_removals + 1):
        if len(G.nodes()) == 0:
            break

        selected_node = random.choice(list(G.nodes()))
        G.remove_node(selected_node)

        lwcc_size = largest_weakly_connected_component_size(G)
        s_q = lwcc_size / N
        s_values.append(s_q)

    q_c = num_removals / N
    R_prime = sum(s_values) / N
    return R_prime, q_c

def get_network_coverage(network_graph):
    travelled_distance = 0
    # This will contain all the edges travelled
    edge_seen = set()
    path_seen = set()

    for node1, node2, edge_data in network_graph.edges(data=True):
        if (node1, node2) not in edge_seen and (node2, node1) not in edge_seen:
            edge_seen.add((node1, node2))
            edge_seen.add((node2, node1))
            path_travelled = edge_data['road_path']

            prev_stop = None
            for stop in path_travelled:
                if prev_stop == None:
                    prev_stop = stop
                    continue

                if (prev_stop, stop) not in path_seen:
                    if ALLOWED_EDGE.get((prev_stop, stop), False): # FIXME: Havent defined ALLOWED_EDGE, EDGE_LEN, and TOTAL_NETWORK_ROAD_DISTANCE yet.
                        travelled_distance += EDGE_LEN[(prev_stop, stop)]
                    path_seen.add((prev_stop, stop))

                prev_stop = stop

    # print(travelled_distance, '/', TOTAL_NETWORK_ROAD_DISTANCE, '=', travelled_distance / TOTAL_NETWORK_ROAD_DISTANCE)
    return travelled_distance / TOTAL_NETWORK_ROAD_DISTANCE

def largest_weakly_connected_component_size(G):
    if len(G) == 0:
        return 0
    return len(max(nx.weakly_connected_components(G), key=len))

# This function will return the node with the maximum degree and its degree from a DegreeView object
def max_degree_node_first(deg_view):
    max_d = -1
    max_n = None
    for n, d in deg_view:
        if d > max_d:
            max_d = d
            max_n = n
    return max_n, max_d

def get_route_family_stop_map(network):
    """
    Returns:
        dict[route_family] = set of stop nodes touched by that route family
    Counts A/B as one route family.
    """
    route_family_stops = {}

    for u, v, key in network.edges(keys=True):
        if not (isinstance(key, str) and '-' in key):
            continue

        route_family = key.split('-')[0]
        if route_family not in route_family_stops:
            route_family_stops[route_family] = set()

        route_family_stops[route_family].add(u)
        route_family_stops[route_family].add(v)

    return route_family_stops
