import networkx as nx
from geopy.distance import geodesic

from schema import Route

# Iterate through each node in reverse and get the shortest path

def get_reverse_route(route, graph_of_stops, overall_graph, max_walking_distance):
    paths = route.route
    reverse_paths = paths[::-1]
    reverse_route_list = []
    reverse_route_id = route.route_id[:-1] + 'B' # Reverse Route ID
    totalDistance = 0

    used_stops = []
    stop_list = []
    for connection in reverse_paths:
        reverse_route_path = connection[::-1]
        end_node = reverse_route_path[-1]

        # Getting the edges of the start node only for the first connection
        if reverse_paths.index(connection) == 0:
            start_node = reverse_route_path[0] # Start node is critical as it should be the same as the last stop previous connection (If this is not the first connection)
            new_start_node = get_opposite_side_stop(start_node, graph_of_stops)
            if new_start_node is not None:
                start_node = new_start_node
            used_stops.append(start_node)

        # Getting the edges of the end node
        new_end_node = get_opposite_side_stop(end_node, graph_of_stops)
        if new_end_node is not None:
            end_node = new_end_node

        if not nx.has_path(graph_of_stops, start_node, end_node):
            if not nx.has_path(graph_of_stops, start_node, reverse_route_path[-1]):
                return None
            else:
                end_node = reverse_route_path[-1]

        if end_node not in used_stops:
            used_stops.append(end_node)
        else:
            return None

        stop_list.append([start_node, end_node])
        start_node = end_node # Next connection start node is the end node of the previous connection

    for connection in stop_list:
        start_node = connection[0]
        end_node = connection[-1]

        reverse_route = nx.shortest_path(graph_of_stops, start_node, end_node, weight='length')
        reverse_route_list.append(reverse_route)

        distance_travelled = 0
        # Get the total distance from point A to point B
        for i in range(len(reverse_route)-1):
            node_data = graph_of_stops.nodes[reverse_route[i]]
            next_node_data = graph_of_stops.nodes[reverse_route[i+1]]
            distance_travelled += geodesic(
                (node_data['y'], node_data['x']),
                (next_node_data['y'], next_node_data['x'])
            ).kilometers

        # Finally, Add the edge
        if reverse_route[0] not in overall_graph:
            overall_graph.add_node(reverse_route[0], **graph_of_stops.nodes[reverse_route[0]])
        if reverse_route[-1] not in overall_graph:
            overall_graph.add_node(reverse_route[-1], **graph_of_stops.nodes[reverse_route[-1]])

        overall_graph.add_edge(reverse_route[0], reverse_route[-1], key=reverse_route_id, road_path = reverse_route, distance = distance_travelled) # Add edge
        totalDistance += distance_travelled

    # print("REVERSE ROUTE DISTANCE: ", totalDistance)
    return Route(reverse_route_list, reverse_route_id, totalDistance)

# Checking the edges -> This is to see if the stop is in a one-way route
def get_opposite_side_stop(node, graph_of_stops, partner_edges=None):
    # TODO: partner_edges comes from the notebook right now, graph_of_stops contains it
    if partner_edges is None:
        partner_edges = graph_of_stops.graph.get('partner_edges', {})

    out_edges = list(graph_of_stops.out_edges(node, keys=True, data=True))
    if not out_edges:
        return None
    n1,n2,key,data = out_edges[0]
    opposite_node = None

    eid = data.get('edge_id')
    if eid is None:
        return None
    if eid in partner_edges:
        partner_edge_id = partner_edges[eid]
        for u, v, k, road in graph_of_stops.edges(keys=True, data=True):
            if road['edge_id'] == partner_edge_id:
                if u < 100000:
                    opposite_node = u
                    break
                if v < 100000:
                    opposite_node = v
                    break

    return opposite_node
