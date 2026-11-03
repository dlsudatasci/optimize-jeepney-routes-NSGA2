from geopy.distance import geodesic
import numpy as np
import math
from scipy.spatial.distance import euclidean

from genetic_algorithm.schema import Stop

def add_stops_to_list(routes):
    used_stops = []
    for route in routes:
        if route is None:
            continue

        for conn in route.route:
            if conn[0] not in used_stops:
                used_stops.append(conn[0])
            if conn[-1] not in used_stops:
                used_stops.append(conn[-1])
    return used_stops

def add_points_to_graph(graph, graph_to_add):
    for node_key, node_data in graph.nodes.items():
        if 'geometry' in node_data and node_data['geometry'].geom_type in ['Point']:
            graph_to_add.add_node(node_key, geometry=node_data['geometry'], name=node_data['name'], y=node_data['lat'], amenity=node_data['amenity'],
                                x=node_data['lon'])

def get_enabled_node_with_highest_edge_probability(source_node: Stop, enabled_nodes: list[Stop],  city_area_sum: float, network_graph):
    prob_list = []
    for n in enabled_nodes:
        edge_prob = get_edge_probability(source_node, n, len(enabled_nodes), city_area_sum, network_graph)
        prob_list.append(edge_prob)

    min_score = min(prob_list)
    if min_score < 0: # Shift the scores to ensure all are positive
        prob_list = [score - min_score for score in prob_list]
    total = sum(prob_list)
    selection_p = [score / total for score in prob_list]

    chosen_node = np.random.choice(enabled_nodes, 1, p=selection_p)[0]

    return chosen_node

# Probabilities of candidate nodes based on distance, area, node degree, and if transpo stop
def get_edge_probability(source: Stop, destination: Stop, normalization_factor, city_area_sum: float, network_graph):
    source_coord = [source.lat, source.long]
    dest_coord = [destination.lat, destination.long]

    base_prob = math.exp(-(euclidean(source_coord, dest_coord))) / float(normalization_factor)

    # If there is already an existing edge between source and destination, decrease the probability
    if network_graph.has_edge(source.stop_id, destination.stop_id):
        base_prob *= 0.5 # The penalty

    if destination.isTranspo:
        return base_prob * 1.5

    area_mult = 1 + (destination.area / city_area_sum)
    degree_mult = 1 + (destination.degree / 10)

    return base_prob * area_mult * degree_mult

# Disables the surrounding nodes within the distance of source
def disable_surrounding_nodes(nodes: list[Stop], source_node: Stop, max_distance: int):
    max_radius = 2000 # This is max radius in which all nodes outside will be disabled
    s_lat = source_node.lat
    s_lon = source_node.long

    for node in nodes:
        n_lat = node.lat
        n_lon = node.long
        distance_to_source = geodesic((s_lat, s_lon), (n_lat, n_lon)).meters
        if distance_to_source <= max_distance or distance_to_source > max_radius:
            node.disable()

def enable_nodes(nodes: list[Stop]):
    for node in nodes:
        node.enable()

# 6371000 * math.pi / 180 = ~111194.92664455873 meters per degree
METERS_PER_DEGREE = 111194.92664455873

# For units conversions
def degrees_to_meters(angle_degrees):
    return angle_degrees * METERS_PER_DEGREE

def meters_to_degrees(distance_meters):
    return distance_meters / METERS_PER_DEGREE
