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
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap

from analysis.original_network import ROOT
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


#: Tile sources for :func:`plot_overlap_map`, by the name callers pass.
#:
#: ``osm`` is the standard openstreetmap.org render, the one the rest of the
#: deck's maps use. CartoDB is absent because its tiles have needed an API key
#: since 2024; the others are Esri's.
BASEMAPS = {
    "osm": ("OpenStreetMap", "Mapnik"),
    "street": ("Esri", "WorldStreetMap"),
    "topo": ("Esri", "WorldTopoMap"),
    "grey": ("Esri", "WorldGrayCanvas"),
    "satellite": ("Esri", "WorldImagery"),
}

#: How this project identifies itself to a tile server.
#:
#: openstreetmap.org serves its tiles from volunteer-run machines, and its
#: usage policy requires a User-Agent that identifies the application making
#: the request. contextily sends ``contextily-<random hex>``, which identifies
#: nothing, and OSM answers that with a 403 image reading "App is not
#: following the tile usage policy". Naming the project is what the policy
#: asks for, so that is what this does.
#:
#: The rest of the policy still binds and is satisfied by how this is used:
#: a handful of tiles for three city maps at one zoom level, cached on disk
#: between runs so a re-run refetches nothing. It is not a licence to loop
#: over cities or zoom levels. If this ever needs bulk tiles, the answer is a
#: provider that sells them, not a heavier hand here.
#:
#: Deliberately carries no contact details. The policy accepts an application
#: name, and a thesis repository should not ship anyone's address.
TILE_USER_AGENT = ("optimize-jeepney-routes-NSGA2/0.1 "
                   "(undergraduate thesis; non-commercial research)")

#: Where fetched tiles are kept, so a re-run does not hit the server again.
TILE_CACHE = ROOT / "cache" / "tiles"

#: The projection tile servers use. Drawing in degrees over it would misplace
#: every arc, so the arcs are converted into it rather than the other way.
WEB_MERCATOR = "EPSG:3857"

#: Colour ramp for the arcs: a quiet slate at one route, the deck's coral in
#: the middle, a near-black crimson at the top.
#:
#: This replaces a cyan-to-magenta ramp. That one was chosen to stay clear of
#: the yellows and oranges the street basemap paints its own roads in, which
#: was the right worry and the wrong fix. Single-route arcs are most of the
#: network, so a bright cyan at the bottom of the ramp made the *least*
#: important value the loudest thing on the map, and the corridors the figure
#: exists to show had to compete with it.
#:
#: This ramp is ordered by lightness rather than hue, so "more routes" reads
#: as "darker and heavier" without consulting the key -- and it still works
#: for a reader who cannot separate the hues. It is only safe because the
#: basemap is desaturated first (see :func:`_fade_tiles`): over full-colour
#: tiles no reddish ramp is, since OSM draws motorways and trunk roads in
#: pinks and reds.
OVERLAY_STOPS = ("#8295A6", "#DD6B6C", "#5C0A14")
OVERLAY_CMAP = LinearSegmentedColormap.from_list("jeepney_overlap",
                                                 OVERLAY_STOPS)


def _to_web_mercator(points):
    """``(lon, lat)`` degrees to web mercator metres."""
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:4326", WEB_MERCATOR, always_xy=True)
    longs, lats = zip(*points)
    return list(zip(*transformer.transform(longs, lats)))


def _fade_tiles(image, keep=0.58):
    """Drain the colour out of a rendered basemap, in place.

    The street map is the only basemap that labels the avenues, which is what
    lets a reader say "that is Taft". Its own roads are drawn in the same
    oranges as the overlay, though, so left alone it competes with the thing
    the figure is about. Converting it to grey and washing it towards white
    keeps the labels and the coastline and gives the overlay the only colour
    on the figure. ``keep`` is how much of the grey survives; lower is paler.
    """
    original = np.asarray(image.get_array())
    tiles = original.astype(float)
    if tiles.ndim != 3 or tiles.shape[2] < 3:
        return

    # Rec. 601 luma, the weighting that matches perceived brightness.
    grey = tiles[..., :3] @ np.array([0.299, 0.587, 0.114])
    white = 255.0 if tiles.max() > 1.0 else 1.0
    faded = white - (white - grey) * keep

    channels = [faded, faded, faded]
    if tiles.shape[2] == 4:
        channels.append(tiles[..., 3])
    image.set_array(np.dstack(channels).astype(original.dtype))


def _add_basemap(ax, basemap, fade):
    """Draw tiles under the axes. Returns whether it worked.

    Tiles are fetched over the network the first time and read from
    :data:`TILE_CACHE` after that, so this is the one figure that needs the
    network on a cold run. It fails soft on purpose: a map with no basemap is
    still the figure, and a re-run of the whole notebook should not stop
    because a tile server is unreachable.
    """
    try:
        import contextily as ctx
    except ImportError:
        return False

    TILE_CACHE.mkdir(parents=True, exist_ok=True)
    ctx.set_cache_dir(str(TILE_CACHE))

    group, name = BASEMAPS[basemap]
    try:
        ctx.add_basemap(ax, source=getattr(ctx.providers, group)[name],
                        headers={"user-agent": TILE_USER_AGENT},
                        attribution_size=6, zorder=0)
    except Exception:
        return False

    if fade and ax.images:
        _fade_tiles(ax.images[0])
    return True


def plot_overlap_map(network, stop_graph, edge_len, city, path=None,
                     basemap="osm", fade=True, cmap=OVERLAY_CMAP):
    """Serviced road arcs drawn in place, coloured by how many routes use them.

    Shows *where* duplication sits rather than how much of it there is, which
    is the part a reader cannot get from the redundancy score.

    ``basemap`` is a key of :data:`BASEMAPS`, or ``None`` for no tiles. The
    default is the openstreetmap.org render, the same source the rest of the
    deck's maps use, desaturated before the arcs go on top.

    ``fade`` is on by default, and the two defaults depend on each other. The
    tiles keep their streets, labels and coastline but lose their colour, so
    the overlay is the only coloured thing on the figure; that is what lets
    :data:`OVERLAY_CMAP` run through reds at all, and what lets a one-route
    arc read as a quiet line rather than disappearing into the road beneath
    it. Pass ``fade=False`` to get the tiles as the server draws them, but
    then also pass a ``cmap`` that avoids yellow, orange and red.

    The arcs keep a white casing underneath. It is what separates a thin arc
    from whatever it crosses, and it is the reason the low end of the ramp
    can be a muted slate instead of something loud.
    """
    arcs = routes_per_arc(network, edge_len)

    segments, counts = [], []
    for (u, v), routes in arcs.items():
        if u not in stop_graph.nodes or v not in stop_graph.nodes:
            continue
        a, b = stop_graph.nodes[u], stop_graph.nodes[v]
        segments.append([(a["x"], a["y"]), (b["x"], b["y"])])
        counts.append(len(routes))

    if basemap is not None:
        segments = [_to_web_mercator(segment) for segment in segments]

    counts = np.array(counts)
    fig, ax = plt.subplots(figsize=(7, 7))

    # Thin and pale for single-route road, thick and dark for shared
    # corridors. Width carries the same message as colour on purpose: the
    # corridors have to be findable at a glance from the back of a room.
    widths = 1.3 + 4.2 * (counts - counts.min()) / max(np.ptp(counts), 1)
    collection = LineCollection(segments, array=counts, cmap=cmap,
                                linewidths=widths, zorder=2)

    # A white casing, the cartographic trick for a line over a busy basemap:
    # it separates the arc from whatever it crosses, so the pale end of the
    # ramp stays visible against the basemap's own yellow roads.
    collection.set_path_effects([
        path_effects.Stroke(linewidth=2.8, foreground="white", alpha=0.9),
        path_effects.Normal()])
    ax.add_collection(collection)
    ax.autoscale()
    ax.set_aspect("equal")

    # A margin so arcs on the city edge are not drawn against the frame, and
    # so the tiles extend past the network rather than stopping at it.
    ax.margins(0.03)
    ax.set_axis_off()

    drawn = basemap is not None and _add_basemap(ax, basemap, fade)
    ax.set_title(f"{city}: routes per road arc in the existing jeepney network")

    bar = fig.colorbar(collection, ax=ax, shrink=0.7)
    bar.set_label("routes using the arc")
    if basemap is not None and not drawn:
        print(f"{city}: basemap tiles unavailable, drawing arcs alone")
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

    fig.suptitle("Stop degree does not track the residents around a stop")
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


def plot_capex_options(options, budget=None, path=None):
    """Cost of the existing stops under each candidate sizing rule.

    ``budget`` draws a reference line. It defaults to off: the only figure
    available to draw was ``MAX_BUDGET``, an inherited placeholder that was
    never derived from anything, and a dashed line across a chart reads as a
    standard whatever the legend says. The bars are the finding on their own.
    """
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

    if budget is not None:
        ax.axhline(budget / 1e6, linestyle="--", color="black", linewidth=1.2,
                   label=f"budget ceiling ({budget / 1e6:.0f}M)")
    ax.set_xticks(positions, cities)
    ax.set_ylabel("cost of existing stops (PHP million)")
    ax.set_title("Stop infrastructure cost under each sizing rule")
    ax.legend(fontsize=8)
    return _save(fig, path)


def plot_stop_spacing(spacings, walking_distances, path=None):
    """Real distance between consecutive stops, against the walking distances.

    The generator spaces the stops of a route by one of ``WALKING_DISTANCES``,
    so if the real gaps sit well below the smallest of them, no generated
    network can look like jeepney service whatever the optimiser does.
    """
    cities = list(spacings)
    fig, ax = plt.subplots(figsize=FIGSIZE)

    # Tick labels are set separately rather than passed in: the boxplot keyword
    # for them was renamed between matplotlib versions.
    ax.boxplot([spacings[city] for city in cities], showfliers=False, widths=0.5)
    ax.set_xticks(range(1, len(cities) + 1), cities)

    colours = ("tab:red", "tab:orange", "tab:brown")
    for distance, colour in zip(walking_distances, colours):
        ax.axhline(distance, linestyle="--", linewidth=1.2, color=colour,
                   label=f"walking distance {distance} m")

    for index, city in enumerate(cities, start=1):
        median = np.median(spacings[city])
        ax.text(index, median, f" {median:.0f} m", va="center", fontsize=9)

    ax.set_ylabel("metres between consecutive stops on a route")
    ax.set_ylim(0, max(walking_distances) * 1.25)
    ax.set_title("Real stop spacing against the spacing the generator imposes")
    ax.legend(fontsize=8)
    return _save(fig, path)


def plot_stop_basis(rows, path=None):
    """Stop count and population reached, for each candidate stop basis."""
    cities = [row["City"] for row in rows]
    positions = np.arange(len(cities))
    width = 0.38

    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.5))

    for offset, key, label in ((-width / 2, "Sakay Stops", "Sakay stops"),
                               (width / 2, "Derived Candidates", "derived candidates")):
        bars = left.bar(positions + offset, [row[key] for row in rows], width,
                        label=label)
        left.bar_label(bars, fmt="%d", fontsize=8, padding=2)
    left.set_yscale("log")
    left.set_xticks(positions, cities)
    left.set_ylabel("stops the optimiser may choose from (log)")
    left.set_title("How many stops")
    left.legend(fontsize=8)

    for offset, key, label in ((-width / 2, "Sakay Reach", "Sakay stops"),
                               (width / 2, "Derived Reach", "derived candidates")):
        bars = right.bar(positions + offset, [row[key] for row in rows], width,
                         label=label)
        right.bar_label(bars, fmt="%.0f%%",
                        labels=[f"{row[key]:.0%}" for row in rows], fontsize=8,
                        padding=2)
    right.set_xticks(positions, cities)
    right.set_ylim(0, 1.12)
    right.set_ylabel("share of city population within reach")
    right.set_title("What that buys in reach")
    right.legend(fontsize=8)

    fig.suptitle("A dense candidate pool costs an order of magnitude for a few points of reach")
    return _save(fig, path)
