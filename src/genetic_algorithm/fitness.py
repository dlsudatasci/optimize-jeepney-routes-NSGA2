import networkx as nx
import random
from genetic_algorithm.schema import Route, Network

from config.config import TARGET_NODE_RATIO, MIN_INTERSECTIONS_PER_ROUTE, MIN_TRANSPO_STOPS_PER_ROUTE, STOP_COST, STOP_SIZES, MAX_BUDGET, MAX_DEGREE

def fitness_network_efficiency(network, weights, total_potential_transport_nodes, total_network_distance, allowed_edge, edge_len):
    internal_connectivity, internal_details = compute_internal_connectivity(
        network,
        target_node_ratio=TARGET_NODE_RATIO,
        min_intersections_per_route=MIN_INTERSECTIONS_PER_ROUTE
    )

    external_connectivity, external_details = compute_external_connectivity(
        network,
        total_potential_transport_nodes=total_potential_transport_nodes,
        min_transpo_stops_per_route=MIN_TRANSPO_STOPS_PER_ROUTE
    )

    weighted_internal_connectivity = weights["w_int"] * internal_connectivity
    weighted_external_connectivity = weights["w_ext"] * external_connectivity

    network_coverage = get_network_coverage(network.graph, total_network_distance, allowed_edge, edge_len)
    weighted_network_coverage = weights["w_cov"] * network_coverage

    vul, q_c_vul = compute_vulnerability(network.graph)
    vulnerability = normalize_vul_rob(vul, q_c_vul)
    weighted_vulnerability = weights["w_vul"] * vulnerability

    rob, q_c_rob = compute_robustness(network.graph)
    robustness = normalize_vul_rob(rob, q_c_rob)
    weighted_robustness = weights["w_rob"] * robustness

    redundancy = compute_redundancy(network)
    weighted_redundancy = weights["w_rob"] * redundancy

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

        "Total Network Nodes": len(network.graph.nodes()),
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

    fitness_score = 0.0 if total_weight <= 0 else weighted_sum / total_weight

    return fitness_score, data

# stop costs based off singapore minimum size (9m x 3m) with length multiplied by factor of 1x, 1.5x, 2x
# price is computed based off dotr figures (28k per sqm)
def fitness_capex_cost(
    network: Network,
    stop_cost: int = STOP_COST,
    stop_sizes: list[float] = STOP_SIZES,
    max_degree: list[int] = MAX_DEGREE,
    max_budget: int = MAX_BUDGET
):
    area = 0.0
    for stop in network.graph.nodes():
        if network.graph.degree(stop) < 1:
            continue
        area += get_stop_area(network.graph, stop, stop_sizes, max_degree)

    capex_cost = area * stop_cost

    violation = max(0, capex_cost - max_budget)
    return capex_cost, violation

def fitness_user_cost(
        network: Network
):
    return

# map stop size by number of degrees, return size of stop based on its stop class
def get_stop_area(network, stop, stop_sizes, max_degree):
    degree = network.degree(stop)
    for stop_class in range(0, 3):
        upper = max_degree[stop_class]
        if degree <= upper:
            return stop_sizes[stop_class]
    return stop_sizes[2]

def compute_internal_connectivity(
    network: Network,
    target_node_ratio=TARGET_NODE_RATIO,
    min_intersections_per_route=MIN_INTERSECTIONS_PER_ROUTE
):
    """
        n_i = the number of intersection nodes, aka when 2+ routes stop there in the same direction
        N_i = nodes * target node ratio, decimals truncated and floor set at 1
        r_i = the number of routes containing intersection nodes >= intersection threshold
            passed to this function
        R_i = the number of routes
        internal connectivity = 0.5 * [MIN(n_i / N_i, 1.0) + (r_i / R_i IF R_i > 0 ELSE 0.0)]
    """

    total_nodes = len(network.graph.nodes())
    if total_nodes == 0:
        return 0.0, {
            "n_i": 0,
            "N_i": 0,
            "r_i": 0,
            "R_i": 0,
            "min_intersections_per_route": min_intersections_per_route,
        }

    if not network.routes:
        return 0.0, {
            "n_i": 0,
            "N_i": max(1, int(total_nodes * target_node_ratio)),
            "r_i": 0,
            "R_i": 0,
            "min_intersections_per_route": min_intersections_per_route,
        }

    routes_by_direction = {}
    route_stops = {}

    for route in network.routes:
        stops = set()
        for connection in route.route:
            stops.add(connection[0])
            stops.add(connection[-1])
        route_stops[route.route_id] = stops

        per_stop = routes_by_direction.setdefault(route.direction, {})
        for stop in stops:
            per_stop.setdefault(stop, set()).add(route.route_id)

    intersection_nodes = set()
    for per_stop in routes_by_direction.values():
        for stop, route_ids in per_stop.items():
            if len(route_ids) >= 2:
                intersection_nodes.add(stop)

    n_i = len(intersection_nodes)
    N_i = max(1, int(total_nodes * target_node_ratio))
    r_i = 0

    for route in network.routes:
        per_stop = routes_by_direction[route.direction]
        interchange_stops = {
            stop for stop in route_stops[route.route_id]
            if len(per_stop.get(stop, ())) >= 2
        }
        if len(interchange_stops) >= min_intersections_per_route:
            r_i += 1

    R_i = len(network.routes)

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
    total_nodes = len(network.graph.nodes())
    if total_nodes == 0:
        return 0.0, {
            "total_nodes": 0,
            "n_e": 0,
            "N_e": max(1, total_potential_transport_nodes),
            "r_e": 0,
            "R_e": 0,
            "min_transpo_stops_per_route": min_transpo_stops_per_route,
        }

    # route_family_stops = get_route_family_stop_map(network)
    # total_route_families = len(route_family_stops)

    stop_list = {}
    for u, v, route in network.graph.edges(keys=True):
        if route not in stop_list:
            stop_list[route] = set()

        stop_list[route].add(u)
        stop_list[route].add(v)

    total_routes = len(stop_list)

    transpo_nodes = {
        node for node, node_data in network.graph.nodes(data=True)
        if node_data.get("isTranspo", False)
    }

    n_e = len(transpo_nodes)
    N_e = max(1, total_potential_transport_nodes)

    if total_routes == 0:
        return 0.0, {
            "total_nodes": total_nodes,
            "n_e": n_e,
            "N_e": N_e,
            "r_e": 0,
            "R_e": 0,
            "min_transpo_stops_per_route": min_transpo_stops_per_route,
        }

    r_e = 0
    for _, stops in stop_list.items():
        transpo_count = sum(1 for stop in stops if stop in transpo_nodes)
        if transpo_count >= min_transpo_stops_per_route:
            r_e += 1

    R_e = total_routes

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

# Red(R) = sum of L(a) for a in A_multi / sum of L(a) for a in A_serviced
# NOTE: test if working
def compute_redundancy(network: Network, edge_len) -> float:
    arcs = {} # length
    routes_on = {} # route ids

    for (_, _, key, data) in network.graph.edges(keys=True, data=True):
        prev = None
        for stop in data['road_path']:
            if prev is None:
                prev = stop
                continue
            arc = (prev, stop)
            length = edge_len.get(arc)
            if length is not None:
                arcs[arc] = length
                routes_on.setdefault(arc, set()).add(key)
            prev = stop

    serviced = sum(arcs.values())
    if serviced <= 0:
        return 0.0
    multi = sum(length for arc, length in arcs.items() if len(routes_on[arc]) >= 2)
    return multi / serviced

# NOTE: check if types are correct
def get_network_coverage(network_graph, total_network_distance: int, allowed_edge: dict[tuple[int, int], bool], edge_len:  dict[tuple[int, int], float]):
    # This will contain all the edges travelled

    if (total_network_distance == 0):
            return 0.0

    serviced = {}
    for _, _, edge_data in network_graph.edges(data=True):
        prev_stop = None
        for stop in edge_data['road_path']:
            if prev_stop is None:
                prev_stop = stop
                continue

            segment = frozenset((prev_stop, stop))
            if segment not in serviced and segment in allowed_edge:
                serviced[segment] = edge_len.get(segment, 0.0)

            prev_stop = stop

    return sum(serviced.values()) / total_network_distance
    # edge_seen = set()
    # path_seen = set()
    # travelled_distance = 0
    # for node1, node2, edge_data in network_graph.edges(data=True):
    #     if (node1, node2) not in edge_seen and (node2, node1) not in edge_seen:
    #         edge_seen.add((node1, node2))
    #         edge_seen.add((node2, node1))
    #         path_travelled = edge_data['road_path']
    #
    #         prev_stop = None
    #         for stop in path_travelled:
    #             if prev_stop == None:
    #                 prev_stop = stop
    #                 continue
    #
    #             if (prev_stop, stop) not in path_seen:
    #                 if allowed_edge.get((prev_stop, stop), False):
    #                     travelled_distance += edge_len[(prev_stop, stop)]
    #                 path_seen.add((prev_stop, stop))
    #
    #             prev_stop = stop
    #
    # print(travelled_distance, '/', total_network_distance, '=', travelled_distance / total_network_distance)
    # return travelled_distance / total_network_distance

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

def normalize_vul_rob(vul_rob, q_c):
    # With fixed q_c = 10% removals, max possible R' is q_c
    # because R' = (1/N) * sum s(q), and each s(q) <= 1.
    return 0.0 if q_c <= 0 else vul_rob / q_c

def fitness_score(network, weights, total_potential_transport_nodes, total_network_distance, allowed_edge, edge_len):
    internal_connectivity, internal_details = compute_internal_connectivity(
        network,
        target_node_ratio=TARGET_NODE_RATIO,
        min_intersections_per_route=MIN_INTERSECTIONS_PER_ROUTE
    )

    external_connectivity, external_details = compute_external_connectivity(
        network,
        total_potential_transport_nodes=total_potential_transport_nodes,
        min_transpo_stops_per_route=MIN_TRANSPO_STOPS_PER_ROUTE
    )

    weighted_internal_connectivity = weights["w_int"] * internal_connectivity
    weighted_external_connectivity = weights["w_ext"] * external_connectivity

    network_coverage = get_network_coverage(network.graph, total_network_distance, allowed_edge, edge_len)
    weighted_network_coverage = weights["w_cov"] * network_coverage

    vul, q_c_vul = compute_vulnerability(network.graph)
    vulnerability = normalize_vul_rob(vul, q_c_vul)
    weighted_vulnerability = weights["w_vul"] * vulnerability

    rob, q_c_rob = compute_robustness(network.graph)
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

        "Total Network Nodes": len(network.graph.nodes()),
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

# def get_route_family_stop_map(network):
#     """
#     Returns:
#         dict[route_family] = set of stop nodes touched by that route family
#     Counts A/B as one route family.
#     """
#     route_family_stops = {}

#     for u, v, key in network.edges(keys=True):
#         if not (isinstance(key, str) and '-' in key):
#             continue

#         route_family = key.split('-')[0]
#         if route_family not in route_family_stops:
#             route_family_stops[route_family] = set()

#         route_family_stops[route_family].add(u)
#         route_family_stops[route_family].add(v)

#     return route_family_stops


def _pct_tag(w):
    """
    Convert weight (0.6) -> '60', (0.02) -> '02', (1.0) -> '100'
    Assumes weights are in [0,1].
    """
    return f"{int(round(w * 100)):02d}"  # 0.1->10, 0.05->05

def make_run_tag(weights):
    return (
        f"cov{_pct_tag(weights["w_cov"])}"
        f"_int{_pct_tag(weights["w_int"])}"
        f"_ext{_pct_tag(weights["w_ext"])}"
        f"_vul{_pct_tag(weights["w_vul"])}"
        f"_rob{_pct_tag(weights["w_rob"])}"
    )
