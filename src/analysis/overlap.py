"""Route overlap and stop-cost profiles for a route network.

Methodology 3.2.2 asks how much of the network is shared by several routes, and
3.2.3 asks what the stops would cost to build. ``compute_redundancy`` and
``fitness_capex_cost`` each collapse one of those to a single number; these
functions break the same quantities down, which is what the write-up needs in
order to say *where* the duplication and the cost sit.

Both read the same inputs as their objective-function counterparts, so the
totals here reconcile with the scores in the baseline table.
"""
from config.config import MAX_DEGREE, STOP_COST, STOP_SIZES


def routes_per_arc(network, edge_len):
    """Map each serviced directed arc to the set of routes running over it.

    Arcs are directed, matching ``compute_redundancy``: a line's forward and
    return legs run over opposite arcs, so a line never overlaps itself. Arcs
    missing from ``edge_len`` are road classes jeepneys are not placed on and
    are skipped, again as the objective function does.
    """
    arcs = {}
    for _, _, route_id, data in network.graph.edges(keys=True, data=True):
        previous = None
        for stop in data["road_path"]:
            if previous is None:
                previous = stop
                continue
            arc = (previous, stop)
            if edge_len.get(arc) is not None:
                arcs.setdefault(arc, set()).add(route_id)
            previous = stop
    return arcs


def overlap_profile(network, edge_len, buckets=(1, 2, 3)):
    """How much serviced road length carries 1, 2, 3, ... routes.

    Returns shares of total serviced length, so the values sum to 1, plus the
    serviced length itself in km and the busiest arc found. The last bucket is
    open-ended, i.e. ``3`` becomes "3 or more".
    """
    arcs = routes_per_arc(network, edge_len)
    serviced = sum(edge_len[arc] for arc in arcs)

    profile = {"Serviced Road Length (km)": serviced / 1000}
    if serviced <= 0:
        return profile

    for count in buckets:
        last = count == buckets[-1]
        label = f"{count}+ Routes" if last else f"Exactly {count} Route" + \
            ("" if count == 1 else "s")
        length = sum(
            edge_len[arc] for arc, routes in arcs.items()
            if (len(routes) >= count if last else len(routes) == count))
        profile[f"{label} (share)"] = length / serviced

    profile["Max Routes On One Arc"] = max(
        (len(routes) for routes in arcs.values()), default=0)
    profile["Mean Routes Per Arc"] = sum(
        len(routes) for routes in arcs.values()) / len(arcs)
    return profile


def stop_class_profile(network, stop_cost=STOP_COST, stop_sizes=STOP_SIZES,
                       max_degree=MAX_DEGREE):
    """Count and cost the stops in each CapEx class.

    Stop class is set by degree, the same mapping ``get_stop_area`` uses, so
    the costs here add up to ``fitness_capex_cost``. Isolated stops are skipped
    for the same reason it skips them: nothing stops there.
    """
    counts = [0] * len(stop_sizes)
    for stop in network.graph.nodes():
        degree = network.graph.degree(stop)
        if degree < 1:
            continue
        for stop_class, upper in enumerate(max_degree):
            if degree <= upper:
                counts[stop_class] += 1
                break
        else:
            counts[-1] += 1

    profile = {}
    for stop_class, count in enumerate(counts):
        area = count * stop_sizes[stop_class]
        profile[f"Type {stop_class + 1} Stops"] = count
        profile[f"Type {stop_class + 1} Cost (PHP)"] = area * stop_cost
    profile["Costed Stops"] = sum(counts)
    return profile
