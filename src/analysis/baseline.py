"""Evaluating the existing jeepney networks with this study's objectives.

Methodology 3.6 compares the Pareto front against the networks that are in
service today, which means the existing networks have to be scored by the same
code that scores GA output. That is what this module does: it imports the
objective functions from :mod:`genetic_algorithm.fitness` rather than keeping a
copy, so a change to an objective moves the baseline with it.

Two of the three objectives can be computed now. ``Z_user`` cannot, because
``fitness_user_cost`` is still a stub and the origin-destination demand matrix
``d_od`` it needs does not exist yet; :data:`MISSING` marks it in the output
instead of being left out silently.
"""
import random
import statistics

from genetic_algorithm.fitness import (
    compute_external_connectivity, compute_internal_connectivity,
    compute_redundancy, compute_robustness, compute_vulnerability,
    fitness_capex_cost, fitness_network_efficiency, fitness_user_cost,
    get_network_coverage, normalize_vul_rob)

from analysis.descriptive import describe_network
from analysis.original_network import (
    build_road_reference, count_transport_amenities, load_original_network)
from analysis.overlap import overlap_profile, stop_class_profile

MISSING = "not implemented"

#: Seeded so the published baseline can be reproduced. ``compute_robustness``
#: removes stops with an unseeded ``random.choice`` and keeps only one such
#: draw, so without this the reported figure moves every run -- on Makati it
#: was seen to swing between 0.74 and 0.88.
SEED = 42

#: How many extra robustness draws to take, purely to report the spread. The
#: real fix is for ``compute_robustness`` to average over repetitions itself;
#: until it does, this at least makes the sensitivity visible.
ROBUSTNESS_REPEATS = 30

#: Component names reported for every network, in the order they are shown.
COMPONENTS = ("Coverage", "Internal Connectivity", "External Connectivity",
              "Vulnerability", "Robustness", "Redundancy")


def robustness_spread(network, repeats=ROBUSTNESS_REPEATS):
    """Robustness over repeated random-failure draws.

    One draw is what the objective function reports, and on a small network one
    draw is noisy, so the baseline also carries the mean and spread.
    """
    draws = []
    for _ in range(repeats):
        value, q_c = compute_robustness(network.graph)
        draws.append(normalize_vul_rob(value, q_c))
    return {
        "Robustness Mean": statistics.mean(draws),
        "Robustness SD": statistics.stdev(draws) if len(draws) > 1 else 0.0,
        "Robustness Min": min(draws),
        "Robustness Max": max(draws),
        "Robustness Draws": repeats,
    }


def evaluate_network(network, weights, total_potential_transport_nodes,
                     total_network_distance, allowed_edge, edge_len,
                     seed=SEED, repeats=ROBUSTNESS_REPEATS):
    """Score one network on every objective that currently has one.

    Returns a flat dict: the efficiency objective and its six raw components,
    the CapEx objective and its budget violation, the spread of the one
    stochastic component, and the user cost objective as :data:`MISSING` while
    it remains unimplemented.
    """
    if seed is not None:
        random.seed(seed)

    # The objective functions no longer hand back the components they combined,
    # so the raw figures are read from the component functions directly. The
    # composite still comes from the objective function itself, never
    # recomputed here, so the two cannot drift apart.
    efficiency = fitness_network_efficiency(
        network, weights, total_potential_transport_nodes,
        total_network_distance, allowed_edge, edge_len)

    vulnerability, q_c_vul = compute_vulnerability(network.graph)
    robustness, q_c_rob = compute_robustness(network.graph)

    result = {
        "Z_efficiency": efficiency,
        "Coverage": get_network_coverage(
            network.graph, total_network_distance, allowed_edge, edge_len),
        "Internal Connectivity": compute_internal_connectivity(network),
        "External Connectivity": compute_external_connectivity(
            network, total_potential_transport_nodes=total_potential_transport_nodes),
        "Vulnerability": normalize_vul_rob(vulnerability, q_c_vul),
        "Robustness": normalize_vul_rob(robustness, q_c_rob),
        "Redundancy": compute_redundancy(network, edge_len),
    }

    user_cost = fitness_user_cost(network)
    result["Z_CapEx (PHP)"] = fitness_capex_cost(network)
    result["Z_user"] = MISSING if user_cost is None else user_cost
    result.update(robustness_spread(network, repeats))

    return result


def evaluate_city(city, weights, descriptive=True):
    """Load a city's existing network and score it.

    ``descriptive`` adds the structural statistics; it is the slow part, since
    it walks every stop pair for the diameter and centrality measures.
    """
    network, stop_graph = load_original_network(city)
    total_network_distance, allowed_edge, edge_len = build_road_reference(stop_graph)
    total_potential_transport_nodes = count_transport_amenities(city)

    row = {"City": city}
    if descriptive:
        row.update(describe_network(network))

    row["Allowed Road Length (km)"] = total_network_distance / 1000
    row.update(evaluate_network(
        network, weights, total_potential_transport_nodes,
        total_network_distance, allowed_edge, edge_len))
    row.update(overlap_profile(network, edge_len))
    row.update(stop_class_profile(network))
    return row


def baseline_table(cities, weights, descriptive=True):
    return [evaluate_city(city, weights, descriptive) for city in cities]
