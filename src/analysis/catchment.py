"""Stop and route catchments over the high-resolution population grid.

Rather than estimate an origin-destination demand matrix, which the project has
no ridership data to ground, a stop's demand is approximated by the population
living within walking distance of it. The walking radii come from
``WALKING_DISTANCES`` in the config, the same tolerances the route generator
uses, and the literature's recommended ceiling is 800 m.

Population comes from Meta's High Resolution Population Density grid, already
clipped per city under ``data/population_distribution/``. Each row is a 30 m
cell with a centroid and a 2020 population estimate.

Catchments overlap, so the population a route or a network reaches is computed
as the union of the cells its stops cover, never the sum of per-stop figures.
The ratio between the two is reported, because it says how much of a network's
apparent reach is the same people counted twice -- which is a question about
stop placement, not about demand.
"""
import math

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from config.config import WALKING_DISTANCES

from analysis.original_network import ROOT

POPULATION_DIR = ROOT / "data" / "population_distribution"
POPULATION_COLUMN = "phl_general_2020"

EARTH_RADIUS_M = 6_371_000.0


def _project(lats, lons, lat0, lon0):
    """Local equirectangular projection to metres.

    Over a single city the distortion is far below the 30 m resolution of the
    population grid, and keeping the projection explicit means stops and cells
    are guaranteed to land in the same plane.
    """
    lat = np.radians(np.asarray(lats, dtype=float))
    lon = np.radians(np.asarray(lons, dtype=float))
    x = EARTH_RADIUS_M * (lon - math.radians(lon0)) * math.cos(math.radians(lat0))
    y = EARTH_RADIUS_M * (lat - math.radians(lat0))
    return np.column_stack((x, y))


class PopulationGrid:
    """The population cells of one city, indexed for radius queries."""

    def __init__(self, city):
        frame = pd.read_csv(POPULATION_DIR / f"{city.lower()}-population-polygon.csv")
        self.city = city
        self.population = frame[POPULATION_COLUMN].to_numpy(dtype=float)
        self.total = float(self.population.sum())
        self.lat0 = float(frame["latitude"].mean())
        self.lon0 = float(frame["longitude"].mean())
        self._tree = cKDTree(
            _project(frame["latitude"], frame["longitude"], self.lat0, self.lon0))

    def cells_near(self, lats, lons, radius):
        """Cell indices within ``radius`` metres of each given point."""
        points = _project(lats, lons, self.lat0, self.lon0)
        return self._tree.query_ball_point(points, radius)

    def population_of(self, cells):
        if not cells:
            return 0.0
        return float(self.population[list(cells)].sum())


def stop_catchments(network, grid, radius):
    """``{stop: (population, frozenset of cell indices)}`` for every stop.

    The cell sets are kept so route and network catchments can be unioned
    without visiting the grid again.
    """
    stops = [(node, data) for node, data in network.graph.nodes(data=True)]
    lats = [data["lat"] for _, data in stops]
    lons = [data["lon"] for _, data in stops]

    catchments = {}
    for (node, _), cells in zip(stops, grid.cells_near(lats, lons, radius)):
        cells = frozenset(cells)
        catchments[node] = (grid.population_of(cells), cells)
    return catchments


def apportioned_catchments(network, grid, radius):
    """Split every population cell among the stops that can serve it.

    A raw catchment counts a resident once for every stop they could walk to,
    which at 550 m means counting the same people roughly nine times over. That
    is fine for asking "can these people reach a jeepney at all" and useless for
    asking "how busy is this stop", because the per-stop figures then add up to
    many times the city's population.

    Here each cell's population is divided equally among the stops within
    ``radius`` of it, so the per-stop figures sum to exactly the population the
    network reaches. Equal division assumes a resident is as likely to use any
    stop in walking range; weighting by distance would sharpen the split but
    needs a decay parameter the project has no data to fit.

    Returns ``{stop: apportioned population}``.
    """
    stops = [(node, data) for node, data in network.graph.nodes(data=True)]
    lats = [data["lat"] for _, data in stops]
    lons = [data["lon"] for _, data in stops]

    cells_per_stop = grid.cells_near(lats, lons, radius)

    # How many stops compete for each cell.
    servers = np.zeros(len(grid.population), dtype=float)
    for cells in cells_per_stop:
        if cells:
            servers[list(cells)] += 1

    shares = np.zeros(len(grid.population), dtype=float)
    reachable = servers > 0
    shares[reachable] = grid.population[reachable] / servers[reachable]

    return {node: float(shares[list(cells)].sum()) if cells else 0.0
            for (node, _), cells in zip(stops, cells_per_stop)}


def route_stops(route):
    """The stops a route calls at; intermediate road junctions are not stops."""
    return {stop for connection in route.route
            for stop in (connection[0], connection[-1])}


def route_catchments(network, catchments, grid):
    """Population reached by each route, as the union over its own stops.

    A line's forward and return legs serve the same stops, so they report the
    same catchment; that is intended, since the question is which corridors
    reach people, not how many vehicles run along them.
    """
    served = {}
    for route in network.routes:
        cells = frozenset().union(
            *(catchments[stop][1] for stop in route_stops(route)
              if stop in catchments)) if route.route else frozenset()
        served[route.route_id] = (grid.population_of(cells), route.length)
    return served


def summarize(network, city, radius):
    """Catchment figures for one network at one walking radius."""
    grid = PopulationGrid(city)
    catchments = stop_catchments(network, grid, radius)
    routes = route_catchments(network, catchments, grid)

    stop_populations = np.array([pop for pop, _ in catchments.values()])
    union_cells = frozenset().union(*(cells for _, cells in catchments.values()))
    reached = grid.population_of(union_cells)
    naive = float(stop_populations.sum())

    route_populations = np.array([pop for pop, _ in routes.values()])
    per_km = np.array([pop / length for pop, length in routes.values() if length > 0])

    degrees = np.array([network.graph.degree(stop) for stop in catchments])

    return {
        "Radius (m)": radius,
        "City Population": grid.total,
        "Population Reached": reached,
        "Population Reached (share)": reached / grid.total if grid.total else 0.0,
        "Sum Of Stop Catchments": naive,
        "Catchment Overlap Factor": naive / reached if reached else 0.0,

        "Stop Catchment Mean": float(stop_populations.mean()),
        "Stop Catchment Median": float(np.median(stop_populations)),
        "Stop Catchment Min": float(stop_populations.min()),
        "Stop Catchment Max": float(stop_populations.max()),
        "Stops Reaching Nobody": int((stop_populations == 0).sum()),

        "Route Catchment Mean": float(route_populations.mean()),
        "Route Catchment Median": float(np.median(route_populations)),
        "Route Catchment Min": float(route_populations.min()),
        "Route Catchment Max": float(route_populations.max()),
        "Route Catchment Per Km Mean": float(per_km.mean()) if per_km.size else 0.0,

        # Whether stop degree is a usable stand-in for how busy a stop is,
        # which is the assumption get_stop_area makes when it sizes stops.
        "Degree vs Raw Catchment Correlation": float(
            np.corrcoef(degrees, stop_populations)[0, 1])
        if degrees.size > 1 and stop_populations.std() > 0 else float("nan"),
    }


def summarize_all_radii(network, city, radii=WALKING_DISTANCES):
    return [summarize(network, city, radius) for radius in radii]
