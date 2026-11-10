"""Setting the stop-infrastructure capacity constraint per city.

Two parameters in the config are placeholders: ``MAX_DEGREE``, which decides
how large a stop is built, and ``MAX_BUDGET``, which caps what the whole
network's stops may cost. This module derives both from data instead.

**Stop sizing.** Singapore's LTA sizes a bus shelter by boarding passengers per
peak hour (Architectural Design Criteria section 4.2), on a ladder that steps
the shelter length by 3 m at a time. :data:`LTA_SHELTER_LADDER` is that table.
``get_stop_area`` currently picks a size from a stop's *degree*, which assumes
degree tracks how busy a stop is -- an assumption
:func:`analysis.catchment.apportioned_catchments` can test directly, and which
the existing networks do not support.

**Budget.** The defensible anchor for ``MAX_BUDGET`` is what the stops of the
network already in service would cost under the same cost model, so the
constraint reads "no more stop infrastructure than the city has today" rather
than resting on a round number.
"""
import numpy as np

from config.config import MAX_DEGREE, STOP_COST, STOP_SIZES

#: LTA Architectural Design Criteria s4.2, "Sizing of Bus Shelter".
#: ``(upper bound on boarding passengers per peak hour, length m, width m)``.
#: The final band is open-ended, written here with an infinite upper bound.
LTA_SHELTER_LADDER = (
    (150, 6, 3),
    (200, 9, 3),
    (300, 12, 3),
    (400, 15, 3),
    (500, 18, 3),
    (600, 21, 3),
    (700, 24, 3),
    (800, 27, 3),
    (900, 30, 3),
    (1000, 33, 3),
    (float("inf"), 36, 3),
)


def lta_areas():
    """Shelter floor areas on the LTA ladder, in square metres."""
    return [length * width for _, length, width in LTA_SHELTER_LADDER]


def lta_area_for(boardings_per_peak_hour):
    """Shelter area the LTA ladder prescribes for a boarding volume."""
    for upper, length, width in LTA_SHELTER_LADDER:
        if boardings_per_peak_hour <= upper:
            return length * width
    return LTA_SHELTER_LADDER[-1][1] * LTA_SHELTER_LADDER[-1][2]


def degree_thresholds(network, quantiles=(1 / 3, 2 / 3)):
    """Degree cut-points that split this city's stops into equal-sized classes.

    If stop size has to stay keyed to degree, the thresholds should at least
    come from the city's own degree distribution rather than from round
    numbers, because a threshold of 3 and 5 puts over 40% of stops in the most
    expensive class in both cities studied here.

    Returns a ``MAX_DEGREE``-shaped list, the last entry open-ended.
    """
    degrees = np.array([degree for _, degree in network.graph.degree()])
    cuts = [int(np.quantile(degrees, q)) for q in quantiles]
    return cuts + [999999]


def capex_under(network, max_degree=MAX_DEGREE, stop_sizes=STOP_SIZES,
                stop_cost=STOP_COST):
    """Total stop cost for a network under a given degree classing.

    Mirrors ``fitness_capex_cost`` so the figures are comparable, but takes the
    thresholds and sizes as arguments so alternatives can be priced.
    """
    total_area = 0.0
    counts = [0] * len(stop_sizes)
    for stop in network.graph.nodes():
        degree = network.graph.degree(stop)
        if degree < 1:
            continue
        for stop_class, upper in enumerate(max_degree):
            if degree <= upper:
                break
        else:
            stop_class = len(stop_sizes) - 1
        stop_class = min(stop_class, len(stop_sizes) - 1)
        counts[stop_class] += 1
        total_area += stop_sizes[stop_class]
    return total_area * stop_cost, counts


def capex_from_catchment(apportioned, peak_boarding_rate, stop_cost=STOP_COST):
    """Total stop cost when size follows catchment population, not degree.

    ``peak_boarding_rate`` is the share of a stop's catchment residents who
    board there during the peak hour, which is what turns a population into the
    boarding volume the LTA ladder is indexed by: 0.05 means 5 of every 100
    residents in the catchment board in that hour.

    The project has no ridership survey to fit that share, so it stays an
    explicit argument: report the value used, or sweep it, rather than hiding a
    guess inside the cost model.
    """
    total_area = 0.0
    areas = []
    for residents in apportioned.values():
        area = lta_area_for(residents * peak_boarding_rate)
        areas.append(area)
        total_area += area
    return total_area * stop_cost, areas


def budget_candidates(network, apportioned=None, peak_boarding_rate=None):
    """Candidate ``MAX_BUDGET`` values for one city, with how each is derived.

    Every entry is the cost of building this city's existing stops under one
    sizing rule, which is the quantity the constraint should be anchored to.
    """
    current, current_counts = capex_under(network)
    tuned_thresholds = degree_thresholds(network)
    tuned, tuned_counts = capex_under(network, max_degree=tuned_thresholds)

    candidates = {
        "Existing stops, config thresholds (PHP)": current,
        "Existing stops, per-city degree terciles (PHP)": tuned,
        "Per-city degree terciles": tuned_thresholds,
        "Stops per class, config thresholds": current_counts,
        "Stops per class, terciles": tuned_counts,
    }

    if apportioned is not None and peak_boarding_rate is not None:
        catchment_cost, _ = capex_from_catchment(
            apportioned, peak_boarding_rate)
        candidates["Existing stops, sized to catchment (PHP)"] = catchment_cost
        candidates["Peak-hour boarding rate assumed"] = peak_boarding_rate

    return candidates
