import osmnx as ox

def generate_graph(location, mode, graph_dir):
    print(f"Generating road network for {location}")
    graph = ox.graph_from_place(location, network_type=mode)
    ox.save_graphml(graph, graph_dir) # Save it as a file

    print(f"Graph saved to {graph_dir}")
    return graph

def load_graph(graph_dir):
    graph = ox.load_graphml(graph_dir)

    print("Graph loaded successfully")
    # print("NUMBER OF EDGES: ", graph.number_of_edges())
    # print("NUMBER OF NODES: ", graph.number_of_nodes())
    # print('\n')
    return graph