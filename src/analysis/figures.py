"""Figures for the exploratory analysis.

Each function answers one of the questions the EDA is meant to settle before
the algorithm's parameters are fixed, and saves a single figure:

* :func:`plot_overlap_map` and :func:`plot_overlap_profile` -- where routes
  duplicate each other, and how much of the network that accounts for.
* :func:`plot_degree_vs_catchment` -- whether stop degree stands in for how
  many people a stop serves, which is what the CapEx model assumes.
* :func:`plot_catchment_overlap` -- how the walking radius trades reach against
  double-counting.
* :func:`plot_capex_options` -- what the existing stops cost under each
  candidate sizing rule, against the configured budget.

Figures are written as PNG at a size that survives being dropped into the
manuscript at full text width.
"""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection

from analysis.overlap import routes_per_arc

FIGSIZE = (8, 5)
DPI = 200


def _save(fig, path=None):
    """Save the figure if asked, and hand it back so a notebook displays it.

    Returning the figure rather than closing it is what makes these show up
    inline: Jupyter renders a figure returned as a cell's value. Passing no
    path skips the file entirely, for when only the inline version is wanted.
    """
    fig.tight_layout()
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=DPI)
    return fig


def plot_overlap_map(network, stop_graph, edge_len, city, path=None):
    """Serviced road arcs drawn in place, coloured by how many routes use them.

    Shows *where* duplication sits rather than how much of it there is, which
    is the part a reader cannot get from the redundancy score.
    """
    arcs = routes_per_arc(network, edge_len)

    segments, counts = [], []
    for (u, v), routes in arcs.items():
        if u not in stop_graph.nodes or v not in stop_graph.nodes:
            continue
        a, b = stop_graph.nodes[u], stop_graph.nodes[v]
        segments.append([(a["x"], a["y"]), (b["x"], b["y"])])
        counts.append(len(routes))

    counts = np.array(counts)
    fig, ax = plt.subplots(figsize=(7, 7))

    # Thin and pale for single-route road, thick and hot for shared corridors.
    widths = 0.6 + 2.4 * (counts - counts.min()) / max(np.ptp(counts), 1)
    collection = LineCollection(segments, array=counts, cmap="YlOrRd",
                                linewidths=widths)
    ax.add_collection(collection)
    ax.autoscale()
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(f"{city}: routes per road arc in the existing jeepney network")

    bar = fig.colorbar(collection, ax=ax, shrink=0.7)
    bar.set_label("routes using the arc")
    return _save(fig, path)


def plot_overlap_profile(profiles, path=None):
    """Share of serviced road length carried by 1, 2 and 3+ routes, per city."""
    cities = list(profiles)
    labels = ("Exactly 1 Route (share)", "Exactly 2 Routes (share)",
              "3+ Routes (share)")
    legend = ("1 route", "2 routes", "3 or more routes")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    bottom = np.zeros(len(cities))
    for label, name in zip(labels, legend):
        values = np.array([profiles[city][label] for city in cities])
        ax.bar(cities, values, bottom=bottom, label=name)
        for x, (value, base) in enumerate(zip(values, bottom)):
            if value > 0.04:
                ax.text(x, base + value / 2, f"{value:.0%}",
                        ha="center", va="center", color="white", fontsize=9)
        bottom += values

    ax.set_ylabel("share of serviced road length")
    ax.set_ylim(0, 1)
    ax.set_title("How much of the road network carries more than one route")
    ax.legend(loc="lower right")
    return _save(fig, path)


def plot_degree_vs_catchment(samples, path=None):
    """Stop degree against the population apportioned to that stop.

    The CapEx model sizes a stop from its degree, which only makes sense if the
    two move together. One panel per city, with the correlation stated.
    """
    fig, axes = plt.subplots(1, len(samples), figsize=(5.5 * len(samples), 4.5),
                             squeeze=False)
    for ax, (city, (degrees, population)) in zip(axes[0], samples.items()):
        degrees = np.asarray(degrees)
        population = np.asarray(population)
        ax.scatter(degrees, population, s=14, alpha=0.55)

        if degrees.std() > 0:
            slope, intercept = np.polyfit(degrees, population, 1)
            grid = np.linspace(degrees.min(), degrees.max(), 2)
            ax.plot(grid, slope * grid + intercept, linewidth=1.5, color="crimson")
            r = np.corrcoef(degrees, population)[0, 1]
            ax.set_title(f"{city}  (r = {r:+.2f})")
        else:
            ax.set_title(city)

        ax.set_xlabel("stop degree")
        ax.set_ylabel("residents apportioned to the stop")

    fig.suptitle("Stop degree is not a proxy for how many people a stop serves")
    return _save(fig, path)


def plot_catchment_overlap(rows, path=None):
    """Reach and double-counting as the walking radius grows."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.5))

    for city, city_rows in rows.items():
        radii = [row["Radius (m)"] for row in city_rows]
        left.plot(radii, [row["Population Reached (share)"] for row in city_rows],
                  marker="o", label=city)
        right.plot(radii, [row["Catchment Overlap Factor"] for row in city_rows],
                   marker="o", label=city)

    left.set_xlabel("walking radius (m)")
    left.set_ylabel("share of city population within reach")
    left.set_ylim(0, 1)
    left.set_title("Reach")
    left.legend()

    right.set_xlabel("walking radius (m)")
    right.set_ylabel("sum of stop catchments / population reached")
    right.set_title("How many times the same resident is counted")
    right.legend()

    fig.suptitle("Choosing the catchment radius")
    return _save(fig, path)


def plot_capex_options(options, budget, path=None):
    """Cost of the existing stops under each candidate sizing rule."""
    cities = list(options)
    rules = list(next(iter(options.values())))

    fig, ax = plt.subplots(figsize=FIGSIZE)
    width = 0.8 / len(rules)
    positions = np.arange(len(cities))

    for index, rule in enumerate(rules):
        values = [options[city][rule] / 1e6 for city in cities]
        offset = (index - (len(rules) - 1) / 2) * width
        bars = ax.bar(positions + offset, values, width, label=rule)
        ax.bar_label(bars, fmt="%.0f", fontsize=8, padding=2)

    ax.axhline(budget / 1e6, linestyle="--", color="black", linewidth=1.2,
               label=f"configured MAX_BUDGET ({budget / 1e6:.0f}M)")
    ax.set_xticks(positions, cities)
    ax.set_ylabel("cost of existing stops (PHP million)")
    ax.set_title("Stop infrastructure cost under each sizing rule")
    ax.legend(fontsize=8)
    return _save(fig, path)
