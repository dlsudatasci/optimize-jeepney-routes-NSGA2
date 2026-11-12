import os
import random
from itertools import groupby

import folium
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

def improved_route_plot(graph, route, color, map_obj, route_id, dash_array=None):
    for idx, connection in enumerate(route.route):
        route_coords = [(graph.nodes[node]['y'], graph.nodes[node]['x']) for node in connection]

        # Draw start node circle marker on first connection
        if idx == 0:
            lat = graph.nodes[connection[0]]['y']
            long = graph.nodes[connection[0]]['x']
            isTranspo = graph.nodes[connection[0]]['isTranspo']

            folium.CircleMarker(
                location=[lat, long],
                radius=7.5,
                popup=f"Transportation: {isTranspo}\n{lat},{long}",
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7
            ).add_to(map_obj)

        # Draw end node circle marker
        lat = graph.nodes[connection[-1]]['y']
        long = graph.nodes[connection[-1]]['x']
        isTranspo = graph.nodes[connection[-1]]['isTranspo']

        folium.CircleMarker(
            location=[lat, long],
            radius=7.5,
            popup=f"Transportation: {isTranspo}\n{lat},{long}",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7
        ).add_to(map_obj)

        # Draw route polyline with directional styling (solid vs dashed)
        folium.PolyLine(
            route_coords,
            popup=f"{route_id}",
            color=color,
            weight=4,
            opacity=0.8,
            dash_array=dash_array
        ).add_to(map_obj)

    return map_obj

def save_route_graph_to_plot(graph_of_stops, route_network, file_name, file_path):
    colors = [
        "red", "blue", "green", "purple", "orange", "darkred", "lightred",
        "darkblue", "darkgreen", "cadetblue", "darkpurple", "pink", "lightblue",
        "lightgreen", "gray", "black"
    ]

    # Auto-center map using average lat/long from graph nodes
    lats = [data['y'] for _, data in graph_of_stops.nodes(data=True)]
    longs = [data['x'] for _, data in graph_of_stops.nodes(data=True)]
    map_center = (sum(lats) / len(lats), sum(longs) / len(longs))

    # Initialize a single combined map
    m_combined = folium.Map(location=map_center, zoom_start=12, tiles='OpenStreetMap')

    # Sort and group by line_id so paired directions share the exact same color
    sorted_routes = sorted(route_network, key=lambda r: r.line_id)

    for line_id, line_group in groupby(sorted_routes, key=lambda r: r.line_id):
        line_color = random.choice(colors)

        for route in line_group:
            # Solid for forward, dashed for reverse
            is_reverse = (route.direction == "reverse")
            dash_style = '5, 10' if is_reverse else None

            improved_route_plot(
                graph_of_stops,
                route,
                line_color,
                m_combined,
                route.route_id,
                dash_array=dash_style
            )

    os.makedirs(file_path, exist_ok=True)

    # Save single combined map HTML
    output_path = os.path.join(file_path, file_name)
    m_combined.save(output_path)

    print(f"Saved {file_name} to: {output_path}")
