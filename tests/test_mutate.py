"""Unit tests for ``mutate`` in ``src/genetic_operators.py``.

Specification under test. ``mutate`` rewires one interior stop of one route of
a network, in place:

* It picks a route, then an interior stop of that route -- never one of the two
  terminal stops, which are fixed.
* It looks for a replacement stop drawn from ``list_of_stops`` that satisfies
  all of:
    - at least ``network.walk_distance`` metres from each of the two stops it
      would sit between, so the new stop does not merely duplicate walkable
      coverage its neighbours already give;
    - not already served by that route;
    - reachable from both neighbours along ``graph_of_stops``;
    - not already joined to either neighbour by an edge of this route;
    - leaving the route's total length no greater than ``MAX_DISTANCE``.
* On success the route, the network graph and the network's stop list are all
  updated together, and the route's length is corrected.
* If no candidate qualifies it leaves the network exactly as it was.

Fixtures are small enough that every expected value is shown as arithmetic in a
comment. Randomness is steered by what is being chosen rather than by the order
in which choices happen, so these tests do not depend on the sequence of draws.
"""
import copy

import networkx as nx
import pytest

import genetic_operators
from config import MAX_DISTANCE
from genetic_operators import mutate
from schema import Network, Route

# Stops on a north-south line about 1.11 km apart, plus candidates off it.
# The distances that decide the gates, by geodesic:
#
#   A-B, B-C, C-D, D-E, E-F  ~= 1113 m   consecutive stops on the line
#   X-A ~= 1959 m, X-C ~= 1959 m         X is a valid replacement anywhere
#   M-A ~=   15 m                        too close to A
#   P-C ~=   15 m                        too close to C
#   E-A ~= 4426 m, E-C ~= 2213 m         far from both, but already on the route
#   W-A ~= 63 km                         reachable, but blows MAX_DISTANCE
#   Z                                    isolated in the road graph
COORDS = {
    "A": (14.540, 121.030),
    "B": (14.550, 121.030),
    "C": (14.560, 121.030),
    "D": (14.570, 121.030),
    "E": (14.580, 121.030),
    "F": (14.590, 121.030),
    "X": (14.550, 121.045),
    "M": (14.5401, 121.0301),
    "P": (14.5601, 121.0301),
    "W": (15.100, 121.030),
    "Z": (14.600, 121.100),
}

ROUTE_ID = "0-A"
WALK_DISTANCE = 550
CONNECTION_KM = 1.113

# Road links. Z is deliberately left out so it is unreachable.
ROAD_LINKS = [
    ("A", "B"), ("B", "C"), ("C", "D"), ("D", "E"), ("E", "F"),
    ("A", "X"), ("X", "C"), ("B", "X"), ("X", "D"),
    ("A", "M"), ("M", "C"), ("B", "M"),
    ("A", "P"), ("P", "C"),
    ("A", "E"), ("E", "C"),
    ("A", "W"), ("W", "C"),
]

FOUR_STOPS = [["A", "B"], ["B", "C"], ["C", "D"]]
THREE_STOPS = [["A", "B"], ["B", "C"]]
SIX_STOPS = [["A", "B"], ["B", "C"], ["C", "D"], ["D", "E"], ["E", "F"]]


class Candidate:
    """A replacement stop. ``mutate`` reads only ``.id``."""

    def __init__(self, stop_id):
        self.id = stop_id

    def __repr__(self):
        return f"Candidate({self.id!r})"


def build_network(connections=FOUR_STOPS, extra_route_edges=()):
    """Return (network, road_graph, route), consistent with each other.

    ``extra_route_edges`` adds edges to the network's own graph under the route
    id without putting them in the route, to set up the duplicate-edge case.
    """
    connections = [list(c) for c in connections]

    road_graph = nx.MultiDiGraph()
    for stop, (lat, lon) in COORDS.items():
        road_graph.add_node(stop, y=lat, x=lon)
    for u, v in ROAD_LINKS:
        road_graph.add_edge(u, v, length=1113.0)
        road_graph.add_edge(v, u, length=1113.0)

    route_graph = nx.MultiDiGraph()
    for stop, (lat, lon) in COORDS.items():
        route_graph.add_node(stop, y=lat, x=lon)
    for conn in connections:
        route_graph.add_edge(conn[0], conn[-1], key=ROUTE_ID,
                             road_path=list(conn), distance=CONNECTION_KM)
    for u, v in extra_route_edges:
        route_graph.add_edge(u, v, key=ROUTE_ID, road_path=[u, v],
                             distance=CONNECTION_KM)

    route = Route(connections, ROUTE_ID, CONNECTION_KM * len(connections))
    stops = sorted({s for conn in connections for s in (conn[0], conn[-1])})

    network = Network([route], [None], stops, [], route_graph)
    network.walk_distance = WALK_DISTANCE
    network.conn_type = "Default"
    return network, road_graph, route


def steer(monkeypatch, connection=1, endpoint=0):
    """Make the random draws deterministic, keyed on what is being chosen.

    ``connection`` is the index of the route connection to rewire and
    ``endpoint`` picks its origin (0) or destination (-1) stop. Candidate stops
    are handed out in order, one per draw, so a search that rejects one goes on
    to the next.

    Keying on the contents of each sequence rather than on the order of the
    draws keeps these tests independent of how mutate sequences its choices.
    """
    real_choice = genetic_operators.random.choice
    drawn = {"candidates": 0}

    def choice(seq):
        options = list(seq)
        if not options:
            # Nothing to steer; let the real implementation raise, so the
            # traceback points at the caller rather than at this stub.
            return real_choice(seq)
        if isinstance(options[0], Route):
            return options[0]
        if options == [0, -1]:
            return endpoint
        if isinstance(options[0], Candidate):
            picked = options[drawn["candidates"] % len(options)]
            drawn["candidates"] += 1
            return picked
        if connection in options:
            return connection
        return options[0]

    monkeypatch.setattr(genetic_operators.random, "choice", choice)


def route_stops(route):
    """The stop sequence the route visits, start to end."""
    stops = [route.route[0][0]]
    for conn in route.route:
        stops.append(conn[-1])
    return stops


def snapshot(network, route):
    return (
        copy.deepcopy(route.route),
        sorted(network.stops),
        sorted(network.graph.edges(keys=True)),
        route.length,
    )


def assert_network_is_consistent(network, route):
    """Checks that must hold of any network mutate hands back."""
    stops = route_stops(route)

    # The route is a chain: each connection starts where the last one ended.
    for earlier, later in zip(route.route, route.route[1:]):
        assert earlier[-1] == later[0], f"break between {earlier} and {later}"

    # No stop is visited twice.
    assert len(stops) == len(set(stops)), f"repeated stop in {stops}"

    # Every connection has a matching graph edge carrying its road path and
    # distance, since the fitness functions read both off the graph.
    for conn in route.route:
        data = network.graph.get_edge_data(conn[0], conn[-1], ROUTE_ID)
        assert data is not None, f"no graph edge for connection {conn}"
        assert data["road_path"][0] == conn[0]
        assert data["road_path"][-1] == conn[-1]
        assert data["distance"] > 0

    # The graph holds exactly the route's connections under this route id.
    edges = {(u, v) for u, v, k in network.graph.edges(keys=True) if k == ROUTE_ID}
    assert edges == {(c[0], c[-1]) for c in route.route}

    # The stop list is exactly the stops the route visits.
    assert sorted(network.stops) == sorted(stops)

    # The recorded length agrees with the edges that make up the route.
    total = sum(network.graph.get_edge_data(c[0], c[-1], ROUTE_ID)["distance"]
                for c in route.route)
    assert route.length == pytest.approx(total, rel=1e-6)

    assert route.length <= MAX_DISTANCE


# --------------------------------------------------------------------------
# A successful swap
# --------------------------------------------------------------------------

def test_swaps_the_chosen_interior_stop_for_the_candidate(monkeypatch):
    # Rewiring connection 1 at its origin end targets B, whose neighbours are
    # A and C, so A-B-C-D becomes A-X-C-D.
    network, road_graph, route = build_network()
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate("X")])

    assert route_stops(route) == ["A", "X", "C", "D"]


def test_swaps_at_the_destination_end_of_a_connection(monkeypatch):
    # Rewiring connection 1 at its destination end targets C, whose neighbours
    # are B and D, so A-B-C-D becomes A-B-X-D.
    network, road_graph, route = build_network()
    steer(monkeypatch, connection=1, endpoint=-1)

    mutate(network, road_graph, [Candidate("X")])

    assert route_stops(route) == ["A", "B", "X", "D"]


def test_swaps_the_only_interior_stop_of_a_three_stop_route(monkeypatch):
    # A-B-C has exactly one interior stop, so the result is forced: A-X-C.
    network, road_graph, route = build_network(THREE_STOPS)
    steer(monkeypatch)

    mutate(network, road_graph, [Candidate("X")])

    assert route_stops(route) == ["A", "X", "C"]


def test_leaves_the_network_self_consistent_after_a_swap(monkeypatch):
    network, road_graph, route = build_network()
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate("X")])

    assert_network_is_consistent(network, route)


def test_drops_the_replaced_stop_from_the_graph_and_stop_list(monkeypatch):
    # B is served by this route alone, so once its two connections are rerouted
    # nothing refers to it and it must not linger in the graph or stop list.
    network, road_graph, route = build_network()
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate("X")])

    assert "B" not in network.stops
    assert not network.graph.has_node("B")


def test_keeps_a_replaced_stop_that_another_route_still_serves(monkeypatch):
    # A second route also calls at B. Dropping B from the graph or the stop
    # list would strand that route, so it has to stay.
    network, road_graph, route = build_network()
    network.graph.add_edge("B", "D", key="1-A", road_path=["B", "D"], distance=2.0)
    other = Route([["B", "D"]], "1-A", 2.0)
    network.routes.append(other)
    network.reversed_routes.append(None)
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate("X")])

    assert network.graph.has_node("B")
    assert "B" in network.stops


def test_corrects_the_route_length_after_a_swap(monkeypatch):
    # Three connections at 1.113 km is 3.339 km. Dropping A-B and B-C leaves
    # 1.113 km, and the new A-X and X-C legs are about 1.959 km each.
    network, road_graph, route = build_network()
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate("X")])

    assert route.length == pytest.approx(1.113 + 1.959 + 1.959, rel=1e-3)


def test_never_replaces_a_terminal_stop(monkeypatch):
    # The first and last stops anchor the route and are not the operator's to
    # move, whichever interior stop it happens to pick.
    swapped = 0
    for connection in (1, 2, 3):
        for endpoint in (0, -1):
            network, road_graph, route = build_network(SIX_STOPS)
            steer(monkeypatch, connection=connection, endpoint=endpoint)

            mutate(network, road_graph, [Candidate("X")])

            stops = route_stops(route)
            assert stops[0] == "A", f"lost the start at {connection}/{endpoint}"
            assert stops[-1] == "F", f"lost the end at {connection}/{endpoint}"
            swapped += "X" in stops

    # Declining every candidate would satisfy the assertions above without
    # testing anything, so at least one of those combinations must have gone
    # through.
    assert swapped, "no combination produced a swap, so the check was vacuous"


def test_regenerates_the_reverse_route_when_one_exists(monkeypatch):
    # The reverse leg has to follow the forward route, otherwise the pair
    # describes two different roads.
    network, road_graph, route = build_network()
    reverse_connections = [["D", "C"], ["C", "B"], ["B", "A"]]
    for conn in reverse_connections:
        network.graph.add_edge(conn[0], conn[-1], key="0-B",
                               road_path=list(conn), distance=CONNECTION_KM)
    network.reversed_routes = [Route(reverse_connections, "0-B", 3.339)]
    network.reversed_stops = ["A", "B", "C", "D"]
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate("X")])

    reverse = network.reversed_routes[0]
    assert reverse is not None
    assert route_stops(reverse) == list(reversed(route_stops(route)))


# --------------------------------------------------------------------------
# Candidates that must be refused
# --------------------------------------------------------------------------

@pytest.mark.parametrize("candidate_id, why", [
    ("M", "15 m from A, one of the two neighbours"),
    ("P", "15 m from C, the other neighbour"),
    ("Z", "not reachable from either neighbour"),
    ("W", "63 km away, so the route would exceed MAX_DISTANCE"),
])
def test_refuses_an_unsuitable_candidate(monkeypatch, candidate_id, why):
    # Rewiring connection 1 at its origin end targets B, between A and C.
    network, road_graph, route = build_network()
    before = snapshot(network, route)
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate(candidate_id)])

    assert snapshot(network, route) == before, f"accepted a stop {why}"


def test_refuses_a_candidate_already_served_by_the_route(monkeypatch):
    # E is further along A-B-C-D-E-F, so reusing it would make the route call
    # at E twice. E is far from both A and C and shares no edge with either,
    # so nothing else disqualifies it.
    network, road_graph, route = build_network(SIX_STOPS)
    before = snapshot(network, route)
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate("E")])

    assert snapshot(network, route) == before


def test_refuses_a_candidate_already_joined_to_a_neighbour(monkeypatch):
    # X clears every other condition, but this route already runs A-X, and
    # taking it would duplicate that edge.
    network, road_graph, route = build_network(extra_route_edges=[("A", "X")])
    before = snapshot(network, route)
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate("X")])

    assert snapshot(network, route) == before


def test_leaves_the_network_untouched_when_nothing_qualifies(monkeypatch):
    network, road_graph, route = build_network()
    before = snapshot(network, route)
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate("M"), Candidate("Z")])

    assert snapshot(network, route) == before


def test_keeps_looking_past_candidates_that_do_not_qualify(monkeypatch):
    # M is too close to A and Z is unreachable, so the search has to carry on
    # and reach X rather than give up or take the first stop offered.
    network, road_graph, route = build_network()
    steer(monkeypatch, connection=1, endpoint=0)

    mutate(network, road_graph, [Candidate("M"), Candidate("Z"), Candidate("X")])

    assert route_stops(route) == ["A", "X", "C", "D"]
