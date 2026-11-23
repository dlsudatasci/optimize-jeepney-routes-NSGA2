"""Shared pytest configuration for the tests.

The modules under ``src/`` import each other by package name
(``from config.config import ...``, ``from genetic_algorithm.schema import ...``),
so ``src/`` itself has to be on ``sys.path``.
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
