"""Descriptive statistics for a route network.

These are the structural figures the baseline comparison reports alongside the
objective functions: how many routes and stops there are, how long the routes
run, how well connected the stops are, and the centrality and diameter
measures named in methodology 3.6.

The functions take a current-schema :class:`~genetic_algorithm.schema.Network`
and do not touch the fitness weights, so they work on the existing networks and
on GA output alike.
"""
import statistics

import networkx as nx

from genetic_algorithm.crossover import group_into_lines


def route_stops(route):
    """The stops a route calls at, in order, without repeats.

    A connection is the road path between two stops, so only its first and last
    node are stops; everything between them is a road junction.
    """
    stops = []
    for connection in route.route:
        for stop in (connection[0], connection[-1]):
            if stop not in stops:
                stops.append(stop)
    return stops


def route_length_stats(routes):
    lengths = [r.length for r in routes]
    return {
        "Total Route Length (km)": sum(lengths),
        "Mean Route Length (km)": statistics.mean(lengths),
        "Median Route Length (km)": statistics.median(lengths),
        "Shortest Route (km)": min(lengths),
        "Longest Route (km)": max(lengths),
    }


def stops_per_route_stats(routes):
    counts = [len(route_stops(r)) for r in routes]
    return {
        "Mean Stops Per Route": statistics.mean(counts),
        "Fewest Stops On A Route": min(counts),
        "Most Stops On A Route": max(counts),
    }


def degree_stats(graph):
    degrees = [d for _, d in graph.degree()]
    return {
        "Mean Degree": statistics.mean(degrees),
        "Max Degree": max(degrees),
    }


def connectivity_stats(graph):
    weak = list(nx.weakly_connected_components(graph))
    strong = list(nx.strongly_connected_components(graph))
    largest_weak = max((len(c) for c in weak), default=0)
    return {
        "Weakly Connected Components": len(weak),
        "Strongly Connected Components": len(strong),
        "Largest Component Share": largest_weak / graph.number_of_nodes(),
    }


def distance_stats(graph, weight="distance"):
    """Network diameter and mean shortest path over reachable stop pairs.

    Unreachable pairs are left out rather than penalized, so on a fragmented
    network these describe the parts that are actually usable. The share of
    pairs that are reachable at all is reported next to them.
    """
    longest = 0.0
    total = 0.0
    pairs = 0
    for node in graph.nodes():
        lengths = nx.single_source_dijkstra_path_length(graph, node, weight=weight)
        for target, length in lengths.items():
            if target == node:
                continue
            total += length
            pairs += 1
            longest = max(longest, length)

    possible = graph.number_of_nodes() * (graph.number_of_nodes() - 1)
    return {
        "Network Diameter (km)": longest,
        "Mean Shortest Path (km)": total / pairs if pairs else 0.0,
        "Reachable Stop Pairs": pairs / possible if possible else 0.0,
    }


def centrality_stats(graph):
    betweenness = nx.betweenness_centrality(graph)
    closeness = nx.closeness_centrality(graph)
    return {
        "Mean Betweenness": statistics.mean(betweenness.values()),
        "Max Betweenness": max(betweenness.values()),
        "Mean Closeness": statistics.mean(closeness.values()),
        "Max Closeness": max(closeness.values()),
    }


def describe_network(network):
    """Every descriptive figure for one network, as a flat dict."""
    graph = network.graph
    transpo = sum(1 for _, data in graph.nodes(data=True)
                  if data.get("isTranspo", False))

    stats = {
        "Routes": len(network.routes),
        "Lines": len(group_into_lines(network.routes)),
        "Stops": graph.number_of_nodes(),
        "Route Edges": graph.number_of_edges(),
        "Transport Stops": transpo,
        "Transport Stop Share": transpo / graph.number_of_nodes(),
    }
    stats.update(route_length_stats(network.routes))
    stats.update(stops_per_route_stats(network.routes))
    stats.update(degree_stats(graph))
    stats.update(connectivity_stats(graph))
    stats.update(distance_stats(graph))
    stats.update(centrality_stats(graph))
    return stats
