import networkx as nx
from geopy.distance import geodesic
import copy, random

from genetic_algorithm.schema import Network, Route
from config.config import MAX_DISTANCE
from genetic_algorithm.reverse_routes import get_reverse_route
from utils.route_utils import add_stops_to_list

# V2 - Crossover routes should not have the same routes
# CROSSOVER SPLIT INDEX FUNCTION

def crossover(network1, network2):
    # Split both networks based on which routes do not have the same connections
    # network.routes is a list of routes or list of lists of shortest_path
    routes_same1 = []
    routes_not_same1 = []
    routes_same2 = []
    routes_not_same2 = []

    # Standardize and store the routes of network2 for comparison
    network1_routes_standardized = {standardize_route(route.route): route for route in network1.routes}
    network2_routes_standardized = {standardize_route(route.route): route for route in network2.routes}

    # Compare each route in network1 with routes in network2
    for route in network1.routes:
        standardized_route1 = standardize_route(route.route)
        if standardized_route1 in network2_routes_standardized:
            routes_same1.append(route)
        else:
            routes_not_same1.append(route)

    for route in network2.routes:
        standardized_route2 = standardize_route(route.route)
        if standardized_route2 in network1_routes_standardized:
            routes_same2.append(route)
        else:
            routes_not_same2.append(route)

    # Create new graphs for the left and right sides
    route_graph1 = nx.MultiDiGraph()
    route_graph2 = nx.MultiDiGraph()

    route_network1 = []
    route_network2 = []

    reversed_route_network1 = []
    reversed_route_network2 = []

    used_stops1 = []
    used_stops2 = []

    reversed_used_stops1 = []
    reversed_used_stops2 = []

    conn_type1 = network1.conn_type
    conn_type2 = network2.conn_type

    walk_type1 = network1.walk_distance
    walk_type2 = network2.walk_distance

    # If all have similar connections, then do not split
    if len(routes_not_same1) == 0:
        test_graph_net1 = network1.graph.copy()
        test_routes_net1 = [copy.deepcopy(r) for r in network1.routes]
        test_reversed_routes_net1 = [copy.deepcopy(r) for r in network1.reversed_routes]
        test_stops_net1 = [copy.deepcopy(s) for s in network1.stops]
        test_reversed_stops_net1 = [copy.deepcopy(s) for s in network1.reversed_stops]
        child1 = Network(test_routes_net1, test_reversed_routes_net1, test_stops_net1, test_reversed_stops_net1, test_graph_net1, network1.conn_type, network1.walk_distance)

        test_graph_net2 = network2.graph.copy()
        test_routes_net2 = [copy.deepcopy(r) for r in network2.routes]
        test_reversed_routes_net2 = [copy.deepcopy(r) for r in network2.reversed_routes]
        test_stops_net2 = [copy.deepcopy(s) for s in network2.stops]
        test_reversed_stops_net2 = [copy.deepcopy(s) for s in network2.reversed_stops]
        child2 = Network(test_routes_net2, test_reversed_routes_net2, test_stops_net2, test_reversed_stops_net2, test_graph_net2, network2.conn_type, network2.walk_distance)

        #print("THERE ARE NO DIFFERENT ROUTES")
        is_different = False

    # If all routes of both networks are different, then split at a random index
    elif len(routes_same1) == 0:
        # Split both networks at a random index
        # network.routes is a list of routes or list of lists of shortest_path
        if len(network1.routes) < len(network2.routes):
            split_index = random.randint(0, len(network2.routes)-1)
        else:
            split_index = random.randint(0, len(network1.routes)-1)

        count = 0 # This is the index count, this will also serve as the new route ID
        for route in network1.routes:
            index = network1.routes.index(route)
            new_route_id = f"{count}-A"
            new_route = Route([copy.deepcopy(r) for r in route.route],new_route_id, route.length)

            reversed_route = network1.reversed_routes[index]
            if reversed_route is not None:
                new_reversed_route_id = f"{count}-B"
                new_reversed_route = Route([copy.deepcopy(r) for r in reversed_route.route],new_reversed_route_id, reversed_route.length)

            if count < split_index: # if 0-split_index -> child1 graph
                for connection in route.route:
                    route_graph1.add_node(connection[0], **network1.graph.nodes[connection[0]])
                    if connection[0] not in used_stops1:
                        used_stops1.append(connection[0])

                    route_graph1.add_node(connection[-1], **network1.graph.nodes[connection[-1]])
                    if connection[-1] not in used_stops1:
                        used_stops1.append(connection[-1])
                    route_graph1.add_edge(connection[0], connection[-1], key=new_route_id, **network1.graph.get_edge_data(connection[0], connection[-1], route.route_id))
                route_network1.append(new_route)

                # Reversed
                if reversed_route is not None:
                    for connection in reversed_route.route:
                        route_graph1.add_node(connection[0], **network1.graph.nodes[connection[0]])
                        if connection[0] not in reversed_used_stops1:
                            reversed_used_stops1.append(connection[0])

                        route_graph1.add_node(connection[-1], **network1.graph.nodes[connection[-1]])
                        if connection[-1] not in reversed_used_stops1:
                            reversed_used_stops1.append(connection[-1])

                        route_graph1.add_edge(connection[0], connection[-1], key=new_reversed_route_id, **network1.graph.get_edge_data(connection[0], connection[-1],  reversed_route.route_id))
                    reversed_route_network1.append(new_reversed_route)
                else:
                    reversed_route_network1.append(None)


            else: # else its for child2 graph
                for connection in route.route:
                    route_graph2.add_node(connection[0], **network1.graph.nodes[connection[0]])
                    if connection[0] not in used_stops2:
                        used_stops2.append(connection[0])

                    route_graph2.add_node(connection[-1], **network1.graph.nodes[connection[-1]])
                    if connection[-1] not in used_stops2:
                        used_stops2.append(connection[-1])

                    route_graph2.add_edge(connection[0], connection[-1], key=new_route_id, **network1.graph.get_edge_data(connection[0], connection[-1], route.route_id))
                route_network2.append(new_route)
                # Reversed
                if reversed_route is not None:
                    for connection in reversed_route.route:
                        route_graph2.add_node(connection[0], **network1.graph.nodes[connection[0]])
                        if connection[0] not in reversed_used_stops2:
                            reversed_used_stops2.append(connection[0])

                        route_graph2.add_node(connection[-1], **network1.graph.nodes[connection[-1]])
                        if connection[-1] not in reversed_used_stops2:
                            reversed_used_stops2.append(connection[-1])

                        route_graph2.add_edge(connection[0], connection[-1], key=new_reversed_route_id, **network1.graph.get_edge_data(connection[0], connection[-1], reversed_route.route_id))
                    reversed_route_network2.append(new_reversed_route)
                else:
                    reversed_route_network2.append(None)
            count += 1

        # Network 2
        count = 0
        for route in network2.routes:
            index = network2.routes.index(route)
            new_route_id = f"{count}-A"
            new_route = Route([copy.deepcopy(r) for r in route.route],new_route_id, route.length)

            reversed_route = network2.reversed_routes[index]
            if reversed_route is not None:
                new_reversed_route_id = f"{count}-B"
                new_reversed_route = Route([copy.deepcopy(r) for r in reversed_route.route], new_reversed_route_id, reversed_route.length)

            if count >= split_index: # if split_index-end -> child1 graph
                for connection in route.route:
                    route_graph1.add_node(connection[0], **network2.graph.nodes[connection[0]])
                    if connection[0] not in used_stops1:
                        used_stops1.append(connection[0])

                    route_graph1.add_node(connection[-1], **network2.graph.nodes[connection[-1]])
                    if connection[-1] not in used_stops1:
                        used_stops1.append(connection[-1])
                    route_graph1.add_edge(connection[0], connection[-1], key=new_route_id, **network2.graph.get_edge_data(connection[0], connection[-1], route.route_id))
                route_network1.append(new_route)

                # Reverse
                if reversed_route is not None:
                    for connection in reversed_route.route:
                        route_graph1.add_node(connection[0], **network2.graph.nodes[connection[0]])
                        if connection[0] not in reversed_used_stops1:
                            reversed_used_stops1.append(connection[0])

                        route_graph1.add_node(connection[-1], **network2.graph.nodes[connection[-1]])
                        if connection[-1] not in reversed_used_stops1:
                            reversed_used_stops1.append(connection[-1])
                        route_graph1.add_edge(connection[0], connection[-1], key=new_reversed_route_id, **network2.graph.get_edge_data(connection[0], connection[-1], reversed_route.route_id))
                    reversed_route_network1.append(new_reversed_route)
                else:
                    reversed_route_network1.append(None)

            else: # else its for child2 graph
                for connection in route.route:
                    route_graph2.add_node(connection[0], **network2.graph.nodes[connection[0]])
                    if connection[0] not in used_stops2:
                        used_stops2.append(connection[0])

                    route_graph2.add_node(connection[-1], **network2.graph.nodes[connection[-1]])
                    if connection[-1] not in used_stops2:
                        used_stops2.append(connection[-1])
                    route_graph2.add_edge(connection[0], connection[-1], key=new_route_id, **network2.graph.get_edge_data(connection[0], connection[-1], route.route_id))
                route_network2.append(new_route)

                # Reversed
                if reversed_route is not None:
                    for connection in reversed_route.route:
                        route_graph2.add_node(connection[0], **network2.graph.nodes[connection[0]])
                        if connection[0] not in reversed_used_stops2:
                            reversed_used_stops2.append(connection[0])

                        route_graph2.add_node(connection[-1], **network2.graph.nodes[connection[-1]])
                        if connection[-1] not in reversed_used_stops2:
                            reversed_used_stops2.append(connection[-1])

                        route_graph2.add_edge(connection[0], connection[-1], key=new_reversed_route_id, **network2.graph.get_edge_data(connection[0], connection[-1], reversed_route.route_id))
                    reversed_route_network2.append(new_reversed_route)
                else:
                    reversed_route_network2.append(None)

            count += 1

        child1 = Network(route_network1, reversed_route_network1, used_stops1, reversed_used_stops1, route_graph1, conn_type1, walk_type1)
        child2 = Network(route_network2, reversed_route_network2, used_stops2, reversed_used_stops2, route_graph2, conn_type2, walk_type2)

        #print("ALL ROUTES ARE DIFFERENT")
        is_different = True

    # If there are some different routes, then split according to the number of different routes
    else:
        # CHILD 1
        # All same routes from parent 1 will go to child 1

        count = 0
        for route in routes_same1:
            index = network1.routes.index(route)
            new_route_id = f"{count}-A"
            new_route = Route([copy.deepcopy(r) for r in route.route],new_route_id, route.length)

            reversed_route = network1.reversed_routes[index]
            if reversed_route is not None:
                new_reversed_route_id = f"{count}-B"
                new_reversed_route = Route([copy.deepcopy(r) for r in reversed_route.route],new_reversed_route_id, reversed_route.length)

            for connection in route.route:
                route_graph1.add_node(connection[0], **network1.graph.nodes[connection[0]])
                if connection[0] not in used_stops1:
                    used_stops1.append(connection[0])

                route_graph1.add_node(connection[-1], **network1.graph.nodes[connection[-1]])
                if connection[-1] not in used_stops1:
                    used_stops1.append(connection[-1])

                route_graph1.add_edge(connection[0], connection[-1], key=new_route_id, **network1.graph.get_edge_data(connection[0], connection[-1], route.route_id))
            route_network1.append(new_route)

            # Reversed
            if reversed_route is not None:
                for connection in reversed_route.route:
                    route_graph1.add_node(connection[0], **network1.graph.nodes[connection[0]])
                    if connection[0] not in reversed_used_stops1:
                        reversed_used_stops1.append(connection[0])

                    route_graph1.add_node(connection[-1], **network1.graph.nodes[connection[-1]])
                    if connection[-1] not in reversed_used_stops1:
                        reversed_used_stops1.append(connection[-1])

                    route_graph1.add_edge(connection[0], connection[-1], key=new_reversed_route_id, **network1.graph.get_edge_data(connection[0], connection[-1], reversed_route.route_id))
                reversed_route_network1.append(new_reversed_route)
            else:
                reversed_route_network1.append(None)

            count += 1

        # All not same routes from parent 2 will go to child 1
        for route in routes_not_same2:
            index = network2.routes.index(route)
            new_route_id = f"{count}-A"
            new_route = Route([copy.deepcopy(r) for r in route.route],new_route_id, route.length)

            reversed_route = network2.reversed_routes[index]
            if reversed_route is not None:
                new_reversed_route_id = f"{count}-B"
                new_reversed_route = Route([copy.deepcopy(r) for r in reversed_route.route],new_reversed_route_id, reversed_route.length)

            for connection in route.route:
                route_graph1.add_node(connection[0], **network2.graph.nodes[connection[0]])
                if connection[0] not in used_stops1:
                    used_stops1.append(connection[0])

                route_graph1.add_node(connection[-1], **network2.graph.nodes[connection[-1]])
                if connection[-1] not in used_stops1:
                    used_stops1.append(connection[-1])

                route_graph1.add_edge(connection[0], connection[-1], key=new_route_id, **network2.graph.get_edge_data(connection[0], connection[-1], route.route_id))
            route_network1.append(new_route)

            # Reverse
            if reversed_route is not None:
                for connection in reversed_route.route:
                    route_graph1.add_node(connection[0], **network2.graph.nodes[connection[0]])
                    if connection[0] not in reversed_used_stops1:
                        reversed_used_stops1.append(connection[0])

                    route_graph1.add_node(connection[-1], **network2.graph.nodes[connection[-1]])
                    if connection[-1] not in reversed_used_stops1:
                        reversed_used_stops1.append(connection[-1])

                    route_graph1.add_edge(connection[0], connection[-1], key=new_reversed_route_id, **network2.graph.get_edge_data(connection[0], connection[-1], reversed_route.route_id))
                reversed_route_network1.append(new_reversed_route)
            else:
                reversed_route_network1.append(None)
            count += 1

        #CHILD2
        # All not same routes from parent 1 will go to child 2

        count = 0
        for route in routes_not_same1:
            index = network1.routes.index(route)
            new_route_id = f"{count}-A"
            new_route = Route([copy.deepcopy(r) for r in route.route],new_route_id, route.length)

            reversed_route = network1.reversed_routes[index]
            if reversed_route is not None:
                new_reversed_route_id = f"{count}-B"
                new_reversed_route = Route([copy.deepcopy(r) for r in reversed_route.route],new_reversed_route_id, reversed_route.length)

            for connection in route.route:
                route_graph2.add_node(connection[0], **network1.graph.nodes[connection[0]])
                if connection[0] not in used_stops2:
                    used_stops2.append(connection[0])

                route_graph2.add_node(connection[-1], **network1.graph.nodes[connection[-1]])
                if connection[-1] not in used_stops2:
                    used_stops2.append(connection[-1])

                route_graph2.add_edge(connection[0], connection[-1], key=new_route_id, **network1.graph.get_edge_data(connection[0], connection[-1], route.route_id))
            route_network2.append(new_route)

            #Reverse
            if reversed_route is not None:
                for connection in reversed_route.route:
                    route_graph2.add_node(connection[0], **network1.graph.nodes[connection[0]])
                    if connection[0] not in reversed_used_stops2:
                        reversed_used_stops2.append(connection[0])

                    route_graph2.add_node(connection[-1], **network1.graph.nodes[connection[-1]])
                    if connection[-1] not in reversed_used_stops2:
                        reversed_used_stops2.append(connection[-1])

                    route_graph2.add_edge(connection[0], connection[-1], key=new_reversed_route_id, **network1.graph.get_edge_data(connection[0], connection[-1], reversed_route.route_id))
                reversed_route_network2.append(new_reversed_route)
            else:
                reversed_route_network2.append(None)
            count += 1

        # All same routes from parent 2 will go to child 2
        for route in routes_same2:
            index = network2.routes.index(route)
            new_route_id = f"{count}-A"
            new_route = Route([copy.deepcopy(r) for r in route.route],new_route_id, route.length)

            reversed_route = network2.reversed_routes[index]
            if reversed_route is not None:
                new_reversed_route_id = f"{count}-B"
                new_reversed_route = Route([copy.deepcopy(r) for r in reversed_route.route],new_reversed_route_id, reversed_route.length)

            for connection in route.route:
                route_graph2.add_node(connection[0], **network2.graph.nodes[connection[0]])
                if connection[0] not in used_stops2:
                    used_stops2.append(connection[0])

                route_graph2.add_node(connection[-1], **network2.graph.nodes[connection[-1]])
                if connection[-1] not in used_stops2:
                    used_stops2.append(connection[-1])

                route_graph2.add_edge(connection[0], connection[-1], key=new_route_id, **network2.graph.get_edge_data(connection[0], connection[-1], route.route_id))
            route_network2.append(new_route)

            # Reversed
            if reversed_route is not None:
                for connection in reversed_route.route:
                    route_graph2.add_node(connection[0], **network2.graph.nodes[connection[0]])
                    if connection[0] not in reversed_used_stops2:
                        reversed_used_stops2.append(connection[0])

                    route_graph2.add_node(connection[-1], **network2.graph.nodes[connection[-1]])
                    if connection[-1] not in reversed_used_stops2:
                        reversed_used_stops2.append(connection[-1])

                    route_graph2.add_edge(connection[0], connection[-1], key=new_reversed_route_id, **network2.graph.get_edge_data(connection[0], connection[-1], reversed_route.route_id))
                reversed_route_network2.append(new_reversed_route)
            else:
                reversed_route_network2.append(None)
            count += 1

        child1 = Network(route_network1, reversed_route_network1, used_stops1, reversed_used_stops1, route_graph1, conn_type1, walk_type1)
        child2 = Network(route_network2, reversed_route_network2, used_stops2, reversed_used_stops2, route_graph2, conn_type2, walk_type2)

        #print("SOME ROUTES ARE DIFFERENT")
        is_different = True


    # # ----------- ERROR CHECKING ---------------------
    # print("* Checking Child 1 for errors:", flush=True)
    # # TODO: DELETE FOR TESTING IF GRAPH IS CONSISTENT WITH ITS LIST OF ROUTES
    # print("Checking for graph and route consistency...", flush=True)
    # check_graph_with_route(child1)
    # print("Checking for graph and list of stops consistency...", flush=True)
    # check_graph_with_stops(child1)
    # print("Checking if order of routes is correct...", flush=True)
    # check_order_route(child1)
    # print("Checking for list of stops and route consistency...", flush=True)
    # check_stops_routes(child1)
    # print("Checking for duplicates in routes...")
    # check_duplicate_routes(child1)
    # print("Checking for duplicate stops and connections...")
    # check_duplicate_stops_routes(child1)
    # print()

    # print("* Checking Child 2 for errors:", flush=True)
    # # # TODO: DELETE FOR TESTING IF GRAPH IS CONSISTENT WITH ITS LIST OF ROUTES
    # print("Checking for graph and route consistency...", flush=True)
    # check_graph_with_route(child2)
    # print("Checking for graph and list of stops consistency...", flush=True)
    # check_graph_with_stops(child2)
    # print("Checking if order of routes is correct...", flush=True)
    # check_order_route(child2)
    # print("Checking for list of stops and route consistency...", flush=True)
    # check_stops_routes(child2)
    # print("Checking for duplicates in routes...")
    # check_duplicate_routes(child2)
    # print("Checking for duplicate stops and connections...")
    # check_duplicate_stops_routes(child2)
    # print()

    return child1, child2, is_different

# Standardizes the route for more efficiency in comparing routes
def standardize_route(route):
    return tuple(tuple(sorted(connection)) for connection in route)

# MUTATION FUNCTION

# Modify the stop connections of a random route in the network
# Randomly select a route and randomly select a stop in that route
# Then randomly select another stop that is a not too far from the selected stop based on threshold
# Swap connections with that stop
def mutate(network_to_mutate, graph_of_stops, list_of_stops):
    # Randomly select a route
    random_route_obj = random.choice(network_to_mutate.routes)
    random_route_obj_index = network_to_mutate.routes.index(random_route_obj)

    random_route = random_route_obj.route
    random_route_id = random_route_obj.route_id

    # Randomly select a stop in the route
    index_array = list(range(1, len(random_route)-1))
    connection_index = random.choice(index_array)
    random_node_connection = random_route[connection_index]

    # Walking Distance
    set_walk_distance = network_to_mutate.walk_distance

    connection_stop_index = random.choice([0, -1]) # Choose whether the origin or destination node
    random_stop = random_node_connection[connection_stop_index] # The random stop to be swapped

    # Get the old total distance
    old_total_distance = 0
    for connection in random_route:
        edge_data = network_to_mutate.graph.get_edge_data(connection[0], connection[-1], random_route_id)
        old_total_distance += edge_data['distance']


    # This is to get the subset distance (Distance without the connection with chosen random stop)
    if connection_stop_index == 0: # If it is the origin node in that connection (A, B, C and B is the chosen. Get B-C and A-B)
        prev_connection = random_route[connection_index-1] # Get the previous connection
        prev_node = prev_connection[0] # Get the origin node for that connection
        distance1 = network_to_mutate.graph.get_edge_data(prev_node, random_stop, random_route_id)['distance'] # Get the distance of the previous connection
        distance2 = network_to_mutate.graph.get_edge_data(random_stop, random_node_connection[-1], random_route_id)['distance'] # Get the distance of the current connection
        distance_to_subtract = distance1 + distance2

        # Previous connection: node1 - random_node
        # Current connection: random_node - node2
        node1 = prev_node # Setting the partner nodes
        node2 = random_node_connection[-1]

    else: #If it is the dest node in that connection
        distance1 = network_to_mutate.graph.get_edge_data(random_node_connection[0], random_stop, random_route_id)['distance'] # Get the distance of the current connection
        next_connection = random_route[connection_index+1] # Get the next route
        next_node = next_connection[-1] # Get the destination node for the next connection
        distance2 = network_to_mutate.graph.get_edge_data(random_stop, next_node, random_route_id)['distance']
        distance_to_subtract = distance1 + distance2

        # Previous connection: node1 - random_node
        # Current connection: random_node - node2
        node2 = next_node
        node1 = random_node_connection[0]

    # Get the subset different -> This will be used to make sure that the distance of the connections to the new node will be less than or equal to MAX_DISTANCE (15km)
    subset_distance = old_total_distance - distance_to_subtract

    # Will try searching for a random stop
    for i in range(100):
        # Get a random stop
        new_random_stop = random.choice(list_of_stops).id
        new_random_stop_data = graph_of_stops.nodes[new_random_stop]

        # Check if the new random stop is not within walking distance with the other stop in the route
        # Walking distance between node1 in route and stop to be swapped with
        source = (new_random_stop_data['y'], new_random_stop_data['x'])
        point = (graph_of_stops.nodes[node1]['y'], graph_of_stops.nodes[node1]['x'])
        walking_distance1 = geodesic(source, point).meters

        # Walking distance between node2 in route and stop to be swapped with
        source = (new_random_stop_data['y'], new_random_stop_data['x'])
        point = (graph_of_stops.nodes[node2]['y'], graph_of_stops.nodes[node2]['x'])
        walking_distance2 = geodesic(source, point).meters

        # Check if it already has been used in the route
        isCandidate = True
        for connection in random_route:
            if new_random_stop == connection[0] or new_random_stop == connection[-1]:
                isCandidate = False
                continue

        # Check if the edge has already been used
        has_edge1 = network_to_mutate.graph.has_edge(node1, new_random_stop, random_route_id)
        has_edge2 = network_to_mutate.graph.has_edge(new_random_stop, node1, random_route_id)
        has_edge3 = network_to_mutate.graph.has_edge(new_random_stop, node2, random_route_id)
        has_edge4 = network_to_mutate.graph.has_edge(node2, new_random_stop, random_route_id)

        # If it is not within walking distances, has not been used in the same route, has a path, has no existing edge
        if walking_distance1 >= set_walk_distance and walking_distance2 >= set_walk_distance and isCandidate and nx.has_path(graph_of_stops, node1, new_random_stop) and nx.has_path(graph_of_stops, new_random_stop, node2) and not has_edge1 and not has_edge2 and not has_edge3 and not has_edge4:
            # DISTANCE 1: Get the total distance from point A to point B
            shortest_route1 = nx.shortest_path(graph_of_stops, node1, new_random_stop, weight='length')
            distance_travelled1 = 0
            for i in range(len(shortest_route1)-1):
                node_data = graph_of_stops.nodes[shortest_route1[i]]
                next_node_data = graph_of_stops.nodes[shortest_route1[i+1]]
                distance_travelled1 += geodesic(node_data['y'], node_data['x'], next_node_data['y'], next_node_data['x']) # TODO: Double check this was not double checked yet since baka mali yung type

            # DISTANCE 2: Get the total distance from point A to point B
            shortest_route2 = nx.shortest_path(graph_of_stops, new_random_stop, node2, weight='length')
            distance_travelled2 = 0
            for i in range(len(shortest_route2)-1):
                node_data = graph_of_stops.nodes[shortest_route2[i]]
                next_node_data = graph_of_stops.nodes[shortest_route2[i+1]]
                distance_travelled2 += geodesic(node_data['y'], node_data['x'], next_node_data['y'], next_node_data['x']) # TODO: Double check this was not double checked yet since baka mali yung type

            newDistance = subset_distance + distance_travelled1 + distance_travelled2
            # If its within the 15km distance, then this new stop can be used
            if newDistance <= MAX_DISTANCE:
                # Add the new stop to the used stops
                if new_random_stop not in network_to_mutate.stops:
                    network_to_mutate.stops.append(new_random_stop)

                # Modify the graph by adding the new node
                network_to_mutate.graph.add_node(new_random_stop, **graph_of_stops.nodes[new_random_stop])

                # Connect the new stop to the edges
                network_to_mutate.graph.add_edge(shortest_route1[0], shortest_route1[-1], key=random_route_id, road_path = shortest_route1, distance = distance_travelled1) # Add edge
                network_to_mutate.graph.add_edge(shortest_route2[0], shortest_route2[-1], key=random_route_id, road_path = shortest_route2, distance = distance_travelled2) # Add edge

                # Remove the old connections and node if it has no other connections
                network_to_mutate.graph.remove_edge(node1, random_stop, random_route_id)
                network_to_mutate.graph.remove_edge(random_stop, node2, random_route_id)
                if (network_to_mutate.graph.degree(random_stop) == 0):
                    network_to_mutate.graph.remove_node(random_stop)
                    network_to_mutate.stops.remove(random_stop)


                # Modify the route
                if connection_stop_index == 0: #If its the origin node
                    random_route[connection_index-1] = shortest_route1 # Change the previous connection
                    random_route[connection_index] = shortest_route2 # Change the current connection

                else: #else If its the dest node
                    random_route[connection_index] = shortest_route1 # Change the current connection
                    random_route[connection_index+1] = shortest_route2 # Change the next connection

                # Modify the distance of the modified route
                random_route_obj.length = newDistance


                # REVERSE
                original_reverse_route = network_to_mutate.reversed_routes[random_route_obj_index]
                if original_reverse_route is not None:
                    original_reverse_route_id = original_reverse_route.route_id
                    # print(f"Reverse Key: {original_reverse_route_id}")
                    # print(f"Key: {random_route_id}")

                    for connection in original_reverse_route.route:
                        # print(f"{connection[0]} - {connection[-1]}")
                        if not network_to_mutate.graph.has_edge(connection[0], connection[-1], original_reverse_route_id):
                            print("EDGE MISSING")
                            # if not network_to_mutate.graph.has_node(connection[0]):
                            #     print(f"{connection[0]} missing")

                            # if not network_to_mutate.graph.has_node(connection[-1]):
                            #     print(f"{connection[-1]} missing")

                        network_to_mutate.graph.remove_edge(connection[0], connection[-1], original_reverse_route_id)
                        if (network_to_mutate.graph.degree(connection[0]) == 0):
                            network_to_mutate.graph.remove_node(connection[0])
                            if connection[0] in network_to_mutate.stops:
                                network_to_mutate.stops.remove(connection[0])

                        if (network_to_mutate.graph.degree(connection[-1]) == 0):
                            network_to_mutate.graph.remove_node(connection[-1])
                            if connection[-1] in network_to_mutate.stops:
                                network_to_mutate.stops.remove(connection[-1])

                    reverse_route = get_reverse_route(random_route_obj, graph_of_stops, network_to_mutate.graph, network_to_mutate.walk_distance)
                    network_to_mutate.reversed_routes[random_route_obj_index] = reverse_route
                    new_reversed_used_stops = add_stops_to_list(network_to_mutate.reversed_routes)
                    network_to_mutate.reversed_stops = new_reversed_used_stops

                # ----------- FOR ERROR CHECKING -------------------
                # print("Checking for graph and route consistency...")
                # check_graph_with_route(network_to_mutate)
                # print("Checking for graph and list of stops consistency...")
                # check_graph_with_stops(network_to_mutate)
                # print("Checking if order of routes is correct...")
                # check_order_route(network_to_mutate)
                # print("Checking for list of stops and route consistency...")
                # check_stops_routes(network_to_mutate)
                # print("Checking for duplicates in routes...")
                # check_duplicate_routes(network_to_mutate)
                # print("Checking for duplicate stops and connections...")
                # check_duplicate_stops_routes(network_to_mutate)
                # print()
                # print("MUTATION DONE", flush=True)

                # Break the loop once we swap
                #print()
                break
