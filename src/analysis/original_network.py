import pathlib
import pickle
import sys
from pathlib import Path

from genetic_algorithm.schema import Network, Route

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_DIR = ROOT / "data" / "original_jeepney_routes" / "Saved Networks"
SAVED_NETWORKS_DIR = ROOT / "data" / "saved_networks"

CITIES = ("Makati", "Manila", "Taguig", "Mandaluyong")

AMENITY_MAPS_DIR = ROOT / "data" / "amenity_maps"

SUBMODULE_HINT = (
    "data/amenity_maps is empty. It is a git submodule, so populate it with:\n"
    "    git submodule update --init data/amenity_maps")


def amenity_maps_path(*parts):
    path = AMENITY_MAPS_DIR.joinpath(*parts)
    if not path.exists() and not any(AMENITY_MAPS_DIR.iterdir()
                                     if AMENITY_MAPS_DIR.is_dir() else []):
        raise FileNotFoundError(SUBMODULE_HINT)
    return path

POINT_SOURCES = {
    "Taguig": (("Taguig", "taguig_point.geojson"),
               ("Taguig", "taguig_point.geojson.zip")),
}


def point_sources(city):
    """The candidate amenity point files for a city, best first."""
    return POINT_SOURCES.get(
        city, (("Jacob-Group", f"{city} City", f"{city}_point.geojson"),))


def read_city_points(city):
    """A city's amenity points as a ``GeoDataFrame``."""
    import geopandas as gpd

    for parts in point_sources(city):
        path = AMENITY_MAPS_DIR.joinpath(*parts)
        if not path.exists():
            continue
        if path.suffix == ".zip":
            return gpd.read_file(f"zip://{path.as_posix()}")
        return gpd.read_file(path)

    tried = ", ".join(str(pathlib.Path(*parts)) for parts in point_sources(city))
    raise FileNotFoundError(
        f"no amenity points for {city}; tried {tried}. {SUBMODULE_HINT}")


BUILT_FROM_CSV = {
    "Taguig": {
        "routes_csv": ("amenity_maps", "Taguig", "Taguig Jeepney Routes",
                       "Taguig_routes.csv"),
    },
    "Makati": {
        "routes_csv": ("repo", "data", "original_jeepney_routes",
                       "Original Data", "Existing Jeepney Routes (Makati).csv"),
    },
    "Manila": {
        "routes_csv": ("repo", "data", "original_jeepney_routes",
                       "Original Data", "Formatted-Manila-Routes.csv"),
    },
    "Mandaluyong": {
        "routes_csv": ("repo", "data", "original_jeepney_routes", "Original Data",
                       "Existing Jeepney Routes (Mandaluyong).csv"),
    },
}


def route_csv_path(recipe):
    """Resolve a recipe's route CSV, in this repo or in the amenity maps."""
    root, *parts = recipe["routes_csv"]
    if root == "repo":
        return ROOT.joinpath(*parts)
    return amenity_maps_path(*parts)

ALLOWED_HIGHWAY_TYPES = frozenset(
    {"primary", "secondary", "tertiary", "trunk", "unclassified"})

_DIRECTION_BY_SUFFIX = {"A": "forward", "B": "reverse",
                        "F": "forward", "R": "reverse"}


class _LegacyNetworkObj:
    """Stand-in for the retired ``networkObj``."""

    def __init__(self, route_network=None, graph=None):
        self.routes = route_network
        self.graph = graph
        self.fitness_score = 0


class _LegacyRoute:
    """Stand-in for the retired three-argument ``Route``."""

    def __init__(self, route=None, route_id=None, length=None):
        self.route = route
        self.route_id = route_id
        self.length = length


class _LegacyStopCandidate:
    """Stand-in for the retired ``stopCandidate``."""

    def __init__(self, lat=None, long=None, isTranspo=None, id=None):
        self.lat = lat
        self.long = long
        self.isTranspo = isTranspo
        self.id = id


def _install_legacy_classes():
    """Make the retired notebook classes importable from ``__main__``.

    The pickles name their classes as ``__main__.<name>``, so the unpickler
    looks them up there no matter which module is actually running.
    """
    main = sys.modules["__main__"]
    for name, cls in (("networkObj", _LegacyNetworkObj),
                      ("Route", _LegacyRoute),
                      ("stopCandidate", _LegacyStopCandidate)):
        if not hasattr(main, name):
            setattr(main, name, cls)


def _load_pickle(path: Path):
    _install_legacy_classes()
    with open(path, "rb") as f:
        return pickle.load(f)


def _split_route_id(route_id: str):
    """``"12-A"`` -> ``(12, "forward")``.

    Unknown suffixes fall back to a forward leg of their own line, which keeps
    a malformed id from silently merging into another line.
    """
    line_part, _, suffix = str(route_id).rpartition("-")
    try:
        line_id = int(line_part)
    except ValueError:
        line_id = line_part or route_id
    return line_id, _DIRECTION_BY_SUFFIX.get(suffix.upper(), "forward")


def _edges_by_route(graph):
    """Group a route network's edges by the route id they are keyed under."""
    edges = {}
    for u, v, key, data in graph.edges(keys=True, data=True):
        edges.setdefault(key, []).append((u, v, data))
    return edges


def _chain_edges(edges):
    """Order one route's edges from its first stop to its last.

    A route is a simple path through the graph, so the starting edge is the one
    whose source is nobody else's target. Returns ``None`` if the edges do not
    form a single chain, which is the caller's signal to skip the route rather
    than invent an order for it.
    """
    outgoing = {}
    for u, v, data in edges:
        if u in outgoing:
            return None
        outgoing[u] = (v, data)

    targets = {v for _, v, _ in edges}
    starts = [u for u in outgoing if u not in targets]
    if len(starts) != 1:
        return None

    chain = []
    node = starts[0]
    while node in outgoing:
        v, data = outgoing.pop(node)
        chain.append((node, v, data))
        node = v
    return chain if not outgoing else None


def _route_from_edges(route_id, edges):
    """Rebuild a :class:`Route` from the edges stored under its route id.

    The saved networks only pickled the forward legs as ``Route`` objects --
    the old ``networkObj`` had no field for the return legs -- but every return
    leg is still in the graph, so it can be read back from there. Each edge
    carries the ``road_path`` between two consecutive stops, which is exactly
    one connection, and ``distance`` for its length.
    """
    chain = _chain_edges(edges)
    if chain is None:
        return None

    connections = [tuple(data["road_path"]) for _, _, data in chain]
    length = sum(data["distance"] for _, _, data in chain)
    line_id, direction = _split_route_id(route_id)
    return Route(connections, route_id, length, line_id, direction)


def build_city_from_csv(city: str):
    """Build a city's network from its route CSV and cache it.

    Called from the Taguig section of Original Jeepney Routes.ipynb, not during
    analysis -- building walks the road graph once per stop and takes minutes,
    and an analysis run should not silently turn into a pipeline run.
    """
    from analysis.build_original import build_and_cache

    recipe = BUILT_FROM_CSV[city]
    points = read_city_points(city)
    transport = points[points["amenity"] == "transportation"]
    transport_points = [(geometry.y, geometry.x)
                        for geometry in transport.geometry]

    return build_and_cache(city, route_csv_path(recipe),
                           transport_points=transport_points)


def _load_built(city: str):
    """Load a city that was built from a route CSV by the preparation script."""
    cached = ORIGINAL_DIR / f"{city}_built.pkl"
    if cached.exists():
        with open(cached, "rb") as f:
            payload = pickle.load(f)
        return (Network(payload["routes"], payload["graph"]),
                payload["stop_graph"])

    if city in BUILT_FROM_CSV:
        raise FileNotFoundError(
            f"{city} has no saved route network yet. Build it once by"
            f" running the {city} section of"
            f" notebooks/Original Jeepney Routes.ipynb, which caches it here.")

    raise FileNotFoundError(
        f"no saved route network for {city} and no route CSV configured")


def load_original_network(city: str):
    """Return ``(network, stop_graph)`` for a city's existing jeepney network.

    ``network`` is a current-schema :class:`Network` whose graph is the saved
    route network: a ``MultiDiGraph`` keyed by route id, with ``road_path`` and
    ``distance`` on every edge and ``isTranspo`` on every node.

    Both legs of every line end up in ``network.routes``. The pickles store
    only the forward legs, so the return legs are rebuilt from the graph; see
    :func:`_route_from_edges`. Without them the two connectivity metrics
    disagree about how many routes exist, because internal connectivity counts
    ``network.routes`` while external connectivity counts graph edge keys.

    ``stop_graph`` is the city road network the routes were snapped onto, which
    carries the ``length`` and ``highway`` attributes the coverage and
    redundancy metrics need.

    Where a ``{city}_built.pkl`` exists it wins over the legacy pickle, because
    it was produced by the fixed pipeline; delete it to fall back.
    """
    # A rebuilt network supersedes the legacy pickle. The pickles predate the
    # two-way splicing and in-city clipping fixes, so where both exist the
    # rebuilt one is the one whose road paths are right.
    rebuilt = ORIGINAL_DIR / f"{city}_built.pkl"
    legacy_path = ORIGINAL_DIR / f"{city} Route Network.pikl"
    if rebuilt.exists() or not legacy_path.exists():
        return _load_built(city)

    legacy = _load_pickle(legacy_path)
    stop_graph = _load_pickle(ORIGINAL_DIR / f"stop_graph_{city}.pkl")

    graph = legacy.graph
    routes = []
    for old in legacy.routes:
        line_id, direction = _split_route_id(old.route_id)
        routes.append(Route(old.route, old.route_id, old.length,
                            line_id, direction))

    stored = {route.route_id for route in routes}
    for route_id, edges in sorted(_edges_by_route(graph).items()):
        if route_id in stored:
            continue
        rebuilt = _route_from_edges(route_id, edges)
        if rebuilt is not None:
            routes.append(rebuilt)

    return Network(routes, graph), stop_graph


def build_road_reference(stop_graph):
    """Derive the road-network inputs the fitness metrics expect.

    Returns ``(total_network_distance, allowed_edge, edge_len)`` where lengths
    are metres, taken from the OSM ``length`` attribute.

    ``edge_len`` is keyed two ways on purpose, because its two consumers ask
    different questions and a ``frozenset`` key never collides with a tuple:

    * ``get_network_coverage`` looks up ``frozenset((u, v))`` -- a stretch of
      road is covered no matter which way a jeepney drives down it.
    * ``compute_redundancy`` looks up ``(u, v)`` -- the methodology defines
      redundancy over *directed* arcs, so a line's own return leg must not
      count as a second route overlapping the forward leg.

    ``total_network_distance`` counts each stretch of road once, matching the
    undirected numerator that coverage builds. Summing the directed edges
    instead would double every two-way road and roughly halve coverage.
    """
    total_network_distance = 0.0
    allowed_edge = {}
    edge_len = {}

    for u, v, data in stop_graph.edges(data=True):
        highway = data.get("highway")
        types = set(highway) if isinstance(highway, list) else {highway}
        if not types & ALLOWED_HIGHWAY_TYPES:
            continue

        length = data.get("length")
        if length is None:
            continue

        segment = frozenset((u, v))
        if segment not in allowed_edge:
            allowed_edge[segment] = True
            edge_len[segment] = length
            total_network_distance += length

        edge_len[(u, v)] = length

    return total_network_distance, allowed_edge, edge_len


def count_transport_amenities(city: str) -> int:
    """How many transportation amenities the city has in total (``N_e``).

    This is the denominator of external connectivity, so it has to be the
    city-wide count of transport amenities rather than the ones a particular
    network happens to reach.

    Counted from the raw amenity points, not from the city-zone-creation
    output: zone creation merges amenities that sit close together, which for
    Makati collapses 119 transport points into 29 zones. Using the merged
    count made a network's own transport stop count exceed the city total.
    The raw counts line up with the figures Original Jeepney Routes.ipynb
    already uses (Makati 111, Manila 464, Mandaluyong 45), which came from the
    same points filtered to the city bounds.
    """
    frame = read_city_points(city)
    return int((frame["amenity"] == "transportation").sum())
