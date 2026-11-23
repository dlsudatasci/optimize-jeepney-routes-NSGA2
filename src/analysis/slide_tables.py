"""Slide tables, written as CSVs you paste straight into a Canva table.

The deck is built in Canva, and its two faces -- League Spartan for headings,
Lato for body -- are Canva fonts. Neither is installed locally, so a table
rendered to PNG here comes out in Arial and does not match the deck. A native
Canva table does match, stays editable, and scales without going fuzzy.

So this module does not draw anything. It emits one small CSV per slide table,
with every value already formatted the way it should appear on the slide --
``62%``, ``PHP 697 M``, ``+0.11`` -- so pasting is what-you-see-is-what-you-get
and nobody is rounding by hand at one in the morning.

The point of it being a module rather than a notebook cell is that the numbers
move. ``residential`` entering the allowed-road set changed six of these tables
at once, and the version in the deck was stale for a week. Re-run this after
any change to the pipeline and re-paste.

Usage::

    uv run python -m analysis.slide_tables            # all tables
    uv run python -m analysis.slide_tables --fast     # skip the slow ones

``--fast`` writes only the tables that come straight out of the saved CSVs.
The others re-derive their numbers (a catchment sweep over three radii, and
the stop-basis comparison), which takes a few minutes.
"""
import argparse
import csv
import sys

import pandas as pd

from config.config import (CATCHMENT_RADIUS_M, MAX_BUDGET, WALKING_DISTANCES,
                           WD_TO_USE)

from analysis.original_network import ROOT

EDA_DIR = ROOT / "data" / "eda"
OUT_DIR = ROOT / "docs" / "slide_tables"

#: The deck's column order. Fixed here so every table reads the same way
#: left to right, which is the thing a reader notices when it is wrong.
CITIES = ("Makati", "Manila", "Taguig")


# --------------------------------------------------------------------------
# formatting
#
# Everything is formatted to a string at the point it is written, not left as
# a float for Canva to render. A spreadsheet that holds 0.217968 will paste
# 0.217968 into a slide, and the one thing this module exists to prevent is
# somebody tidying numbers by hand on the way in.
# --------------------------------------------------------------------------

def pct(value, dp=0):
    """A share in 0..1 as a percentage string."""
    return f"{value * 100:.{dp}f}%"


def php_m(pesos, dp=0):
    """Pesos as millions, the unit every cost on the slides uses."""
    return f"PHP {pesos / 1e6:,.{dp}f} M"


def signed(value, dp=2):
    """A correlation, with its sign always shown."""
    return f"{value:+.{dp}f}"


def km(value, dp=1):
    return f"{value:,.{dp}f} km"


# --------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------

def _baseline():
    return pd.read_csv(EDA_DIR / "original_network_baseline.csv").set_index("City")


def _design_inputs():
    return pd.read_csv(EDA_DIR / "eda_design_inputs.csv").set_index("City")


def _row(label, frame, column, fmt):
    """One table row: a label, then the same column read per city."""
    return [label] + [fmt(frame.loc[city, column]) for city in CITIES]


# --------------------------------------------------------------------------
# the tables
#
# Each returns ``(filename, header_row, data_rows)``. Keeping them separate
# means a slide that changes shape only touches its own function.
# --------------------------------------------------------------------------

def route_overlaps():
    """Slide 13."""
    b = _baseline()
    header = ["", *CITIES]
    rows = [
        _row("Carrying 3+ routes", b, "3+ Routes (share)", pct),
        _row("Mean routes per arc", b, "Mean Routes Per Arc", lambda v: f"{v:.1f}"),
        _row("Most routes on an arc", b, "Max Routes On One Arc",
             lambda v: f"{int(v)}"),
        ["Road served / available"] + [
            pct(b.loc[c, "Serviced Road Length (km)"]
                / b.loc[c, "Allowed Road Length (km)"]) for c in CITIES],
    ]
    return "13_route_overlaps.csv", header, rows


def connectivity():
    """Slide 15."""
    b = _baseline()
    header = ["", *CITIES]
    rows = [
        _row("Connected components", b, "Weakly Connected Components",
             lambda v: f"{int(v)}"),
        _row("Stops in the largest", b, "Largest Component Share", pct),
        _row("Stop pairs reachable", b, "Reachable Stop Pairs", pct),
    ]
    return "15_connectivity.csv", header, rows


def budget():
    """Slide 17. The three sizing rules, against the one configured cap."""
    d = _design_inputs()
    header = ["Sizing rule", *CITIES]
    rules = [
        ("01 Degree, config", "sized by degree, config thresholds"),
        ("02 Degree, terciles", "sized by degree, per-city terciles"),
        ("03 Catchment, 5%", "sized to catchment, 5% board in peak hour"),
    ]
    rows = [_row(label, d, column, php_m) for label, column in rules]
    rows.append(["MAX_BUDGET"] + [php_m(MAX_BUDGET)] * len(CITIES))
    return "17_budget.csv", header, rows


def stop_sizing():
    """Slide 18. Whether stop degree stands in for how many people it serves."""
    d = _design_inputs()
    header = ["Degree vs residents", *CITIES]
    rows = [
        _row("Apportioned catchment", d,
             "Degree vs Apportioned Catchment Correlation", signed),
        _row("Raw catchment", d, "Degree vs Raw Catchment Correlation", signed),
    ]
    return "18_stop_sizing.csv", header, rows


def baseline_fitness():
    """Slide 21. The column Objective 3 compares optimised networks against.

    Three columns here are not the obvious one, and all three are deliberate.

    ``Robustness`` rather than ``Robustness Mean``: the first is what feeds
    ``Z_efficiency``, the second is the average of the 30 draws, and they do
    not agree. Showing the mean beside a weighted score computed from the
    other value would be showing a number that does not add up on the slide.

    ``Z_CapEx`` is read from the costing in ``eda_design_inputs``, not from
    the baseline's own ``Z_CapEx (PHP)``. The fitness function folds a
    100 M penalty into what it returns when a city is over budget, which is
    why the baseline reads 797 M for Manila against a 697 M build cost. The
    slide is about what the stops would cost to build, so it shows the build
    cost -- and this keeps it equal to the figure on slide 17.

    ``Z_user`` is an absolute aggregate -- population times generalised
    minutes, summed over every origin-destination pair -- so it is not
    comparable between cities, and Manila's being fifty times Makati's says
    only that Manila is bigger. The three rows under it are the per-trip
    figures that are comparable, which is why they are on the slide at all.
    Its unit is billions of person-minutes and the row label does not carry
    it, because the labels here match the deck's: put the unit in the slide
    caption, or the 4.6 against the 233.7 means nothing on its own.
    """
    b = _baseline()
    d = _design_inputs()
    header = ["", *CITIES]
    three = lambda v: f"{v:.3f}"
    rows = [
        _row("Z_efficiency", b, "Z_efficiency", three),
        _row("Coverage", b, "Coverage", three),
        _row("Internal connectivity", b, "Internal Connectivity", three),
        _row("External connectivity", b, "External Connectivity", three),
        _row("Vulnerability", b, "Vulnerability", three),
        _row("Robustness", b, "Robustness", three),
        _row("Redundancy", b, "Redundancy", three),
        _row("Z_CapEx", d, "sized by degree, config thresholds", php_m),
        _row("Z_user", b, "Z_user", lambda v: f"{v / 1e9:,.1f}"),
        _row("Mean trip", b, "Z_user Mean Generalised Min",
             lambda v: f"{v:.1f} min"),
        _row("Changes per trip", b, "Z_user Mean Changes",
             lambda v: f"{v:.2f}"),
        _row("Pairs reachable", b, "Z_user Reach", pct),
    ]
    return "21_baseline_fitness.csv", header, rows


def commuter_flows():
    """Slide 14. Reach and double counting at each configured walking radius.

    Slow: it rebuilds every stop's catchment over the 30 m population grid,
    once per city per radius.
    """
    from analysis.catchment import summarize
    from analysis.original_network import load_original_network

    header = ["Radius", "Makati", "Manila", "Taguig", "Counted"]
    reach, overlap = {}, {}
    for city in CITIES:
        network, _ = load_original_network(city)
        for radius in WALKING_DISTANCES:
            s = summarize(network, city, float(radius))
            reach[(city, radius)] = s["Population Reached (share)"]
            overlap[(city, radius)] = s["Catchment Overlap Factor"]

    rows = []
    for radius in WALKING_DISTANCES:
        factors = [overlap[(c, radius)] for c in CITIES]
        rows.append([f"{radius} m",
                     *(pct(reach[(c, radius)]) for c in CITIES),
                     f"{min(factors):.1f}-{max(factors):.1f}x"])
    return "14_commuter_flows.csv", header, rows


def stop_spacing():
    """Slide 19. Real gaps between consecutive stops, against the generator's floor.

    Slow: it walks every route in every city.
    """
    import numpy as np

    from analysis.original_network import load_original_network
    from analysis.stop_basis import route_stop_spacing

    # The generator spaces consecutive stops by one walking distance, so the
    # floor follows WD_TO_USE rather than being a number written down here.
    floor = float(WALKING_DISTANCES[WD_TO_USE])

    header = ["", "Median gap", "Below the floor"]
    rows = []
    for city in ("Makati", "Taguig", "Manila"):
        network, _ = load_original_network(city)
        gaps = np.asarray(route_stop_spacing(network), dtype=float)
        gaps = gaps[gaps > 0]
        rows.append([city, f"{np.median(gaps):,.0f} m",
                     pct(float((gaps < floor).mean()), 1)])
    return "19_stop_spacing.csv", header, rows


TABLES_FAST = (route_overlaps, connectivity, budget, stop_sizing,
               baseline_fitness)
TABLES_SLOW = (commuter_flows, stop_spacing)


def write_tables(fast=False, out_dir=OUT_DIR):
    """Write every table to ``out_dir`` and echo it as tab-separated text.

    The echo is there because a tab-separated block copied out of a terminal
    pastes into a Canva table just as well as one copied out of Excel, and
    saves opening a file for a table you only need once.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    builders = TABLES_FAST if fast else TABLES_FAST + TABLES_SLOW

    for build in builders:
        try:
            name, header, rows = build()
        except Exception as error:                      # noqa: BLE001
            print(f"!! {build.__name__}: {type(error).__name__}: {error}",
                  file=sys.stderr)
            continue

        path = out_dir / name
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)

        print(f"\n--- {name}")
        for line in (header, *rows):
            print("\t".join(str(cell) for cell in line))

    print(f"\nWritten to {out_dir}")
    print(f"Catchment radius {CATCHMENT_RADIUS_M:.0f} m, "
          f"MAX_BUDGET {php_m(MAX_BUDGET)}.")


# --------------------------------------------------------------------------
# PNG rendering
#
# Most of these tables are rebuilt by hand in Canva, where they stay editable
# and in the deck's own face. Slide 21's is the exception: at twelve rows it
# is too much to retype every time the numbers move, so it goes on the slide
# as a picture instead.
#
# Arial, because it is the only face on this machine that is close to the
# deck's. Roboto, Lato and League Spartan are Canva fonts and are not
# installed, so asking matplotlib for them silently gives DejaVu Sans, which
# looks nothing like the deck. If anyone installs Roboto locally, change
# TABLE_FONT and the tables will match the hand-built ones exactly.
# --------------------------------------------------------------------------

PNG_DIR = ROOT / "plots" / "slides"

TABLE_FONT = "Arial"

#: Geometry, in the same arbitrary units the first of these images used, at
#: 118 units to the inch and 300 dpi. Measured off
#: ``slide8_baseline_table.png`` so a regenerated table drops into the same
#: hole on the slide: 1,019 units wide is 2,590 px.
COL_WIDTHS = (420, 200, 200, 199)
HEADER_FILL = "#F2F2F3"
RULE = "#C9CACC"
CORNER = 15
UNITS_PER_INCH = 118.0


def render_png(header, rows, path, col_widths=COL_WIDTHS, row_h=70,
               bold=(), dpi=300):
    """Draw one table as a standalone image and return the path.

    ``row_h`` is what holds the footprint steady as rows come and go. The
    eight-row version of this table used 110 and came out 2,237 px tall;
    thirteen rows at 70 come out 2,313, so the picture still occupies the
    same part of the slide and nothing has to be nudged.

    ``bold`` is the set of row labels to set in bold -- the objectives, so a
    reader can see which rows are totals and which are the components
    underneath them.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle

    matplotlib.rcParams["font.family"] = TABLE_FONT

    width = sum(col_widths)
    height = row_h * (len(rows) + 1)

    figure = plt.figure(figsize=(width / UNITS_PER_INCH,
                                 height / UNITS_PER_INCH), dpi=dpi)
    axes = figure.add_axes([0, 0, 1, 1])
    axes.set_xlim(0, width)
    axes.set_ylim(0, height)
    axes.set_axis_off()
    figure.patch.set_facecolor("white")

    edges = [0]
    for column in col_widths:
        edges.append(edges[-1] + column)
    header_y = height - row_h

    # The header fill is a rounded box for the top two corners, with a plain
    # rectangle over its lower half to square off the bottom two.
    axes.add_patch(FancyBboxPatch(
        (0, header_y), width, row_h,
        boxstyle=f"round,pad=0,rounding_size={CORNER}",
        linewidth=0, facecolor=HEADER_FILL, zorder=1))
    axes.add_patch(Rectangle((0, header_y), width, row_h * 0.55,
                             facecolor=HEADER_FILL, edgecolor="none", zorder=1))

    for x in edges[1:-1]:
        axes.plot([x, x], [0, height], color=RULE, linewidth=1.1, zorder=2)
    for i in range(len(rows) + 1):
        y = header_y - row_h * i
        axes.plot([0, width], [y, y], color=RULE, linewidth=1.1, zorder=2)

    def write(values, y, weight, size):
        for column, value in enumerate(values):
            if not value:
                continue
            axes.text((edges[column] + edges[column + 1]) / 2, y, value,
                      ha="center", va="center", color="black",
                      fontsize=size, fontweight=weight, zorder=4)

    write(header, header_y + row_h / 2, "bold", 12.5)
    for i, row in enumerate(rows):
        weight = "bold" if row[0] in bold else "normal"
        write(row, header_y - row_h * i - row_h / 2, weight, 12)

    axes.add_patch(FancyBboxPatch(
        (0.6, 0.6), width - 1.2, height - 1.2,
        boxstyle=f"round,pad=0,rounding_size={CORNER}",
        linewidth=1.2, edgecolor=RULE, facecolor="none", zorder=5))

    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=dpi, facecolor="white")
    plt.close(figure)
    return path


def baseline_fitness_png(path=None):
    """Slide 21's table as an image, bold on the three objectives."""
    _, header, rows = baseline_fitness()
    # PHP reads as PHP in a CSV because the peso sign does not survive every
    # spreadsheet round trip. On a slide it should be the sign.
    rows = [[cell.replace("PHP ", "₱") for cell in row] for row in rows]
    return render_png(header, rows,
                      path or PNG_DIR / "slide21_baseline_table.png",
                      bold={"Z_efficiency", "Z_CapEx", "Z_user"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast", action="store_true",
                        help="skip the tables that re-derive their numbers")
    parser.add_argument("--png", action="store_true",
                        help="also render slide 21's table as an image")
    arguments = parser.parse_args()
    write_tables(fast=arguments.fast)
    if arguments.png:
        print("rendered", baseline_fitness_png())


if __name__ == "__main__":
    main()
