"""Shared pytest configuration and graph fixtures for the src/ modules.

``src/fitness.py`` uses flat imports (``from config import ...``), so ``src/``
itself has to be on ``sys.path`` for the module to import at all.
"""
import sys
from pathlib import Path

import networkx as nx
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def add_route(graph, route_id, nodes):
    """Chain ``nodes`` together as one directed route, keyed ``route_id``.

    Mirrors how the network builder keys edges: ``"<family>-A"`` for the
    forward direction and ``"<family>-B"`` for the reverse.
    """
    for u, v in zip(nodes, nodes[1:]):
        graph.add_edge(u, v, key=route_id, road_path=[u, v], distance=1.0)


@pytest.fixture
def two_crossing_routes():
    """Six stops, two route families that share stops n2 and n3.

    Family "0" runs n1-n2-n3-n4 and back (keys ``0-A`` / ``0-B``), family "1"
    runs n2-n3-n7-n8 (key ``1-A``). Node degrees (in + out, with edge
    multiplicity) are n1:2, n2:5, n3:6, n4:2, n7:2, n8:1, so n3 is the unique
    highest-degree node.
    """
    graph = nx.MultiDiGraph()
    add_route(graph, "0-A", ["n1", "n2", "n3", "n4"])
    add_route(graph, "0-B", ["n4", "n3", "n2", "n1"])
    add_route(graph, "1-A", ["n2", "n3", "n7", "n8"])
    return graph


@pytest.fixture
def transpo_graph(two_crossing_routes):
    """``two_crossing_routes`` with n2, n3 and n8 flagged as transport stops."""
    for node in ("n2", "n3", "n8"):
        two_crossing_routes.nodes[node]["isTranspo"] = True
    return two_crossing_routes


@pytest.fixture
def path_graph_20():
    """A single 20-stop route, p0 .. p19, so ``int(N * 0.1)`` removals is 2."""
    graph = nx.MultiDiGraph()
    add_route(graph, "0-A", [f"p{i}" for i in range(20)])
    return graph
