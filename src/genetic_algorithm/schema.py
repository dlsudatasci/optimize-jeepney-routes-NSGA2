import random
from collections.abc import Sequence
from dataclasses import dataclass, field

import networkx as nx
import numpy as np

from config.config import (
  CATCHMENT_RADIUS_M,
  MAX_BUDGET,
  MAX_DEGREE,
  STOP_COST,
  STOP_SIZES,
)


class Stop:
  def __init__(self, lat: float, long: float, isTranspo: bool, stop_id: int, area):
    self.lat = lat
    self.long = long
    self.isTranspo = isTranspo  # if it is an existing transpo amenity
    self.enabled = False
    self.stop_id = stop_id
    self.area = area
    self.degree = 0

  def enable(self):
    self.enabled = True

  def disable(self):
    self.enabled = False


class Route:
  def __init__(
    self, route: list, route_id: str, length: float, line_id: int, direction: str
  ):
    self.route = route
    self.route_id = route_id
    self.length = length
    self.line_id = line_id
    self.direction = direction  # could only be "forward" or "reverse"

  def __str__(self):
    return f"[Route ID:{self.route_id} Line ID:{self.line_id}]: {len(self.route)} stops {self.length:<4} km"


class Network:
  def __init__(self, routes: list[Route], graph: nx.MultiDiGraph):
    self.routes = routes
    self.graph = graph
    self.fitness_score: np.array | None = None
    self.constraint_violation: float | None = None
@dataclass(frozen=True, slots=True)
class HyperParameters:
  fitness_weights: dict
  walk_distance: int
  selection_rate: float = 0.10

  # Mutation
  mutation_probability: float = 0.2
  mutations_per_child: Sequence[float] = (0.1, 0.1, 0.4, 0.2, 0.2)
  mutations_per_child_identical: Sequence[float] = (0.0, 0.1, 0.4, 0.3, 0.2)

  # User Cost
  catchment_m: float = CATCHMENT_RADIUS_M

  # CapEx score
  stop_cost: float = STOP_COST
  stop_sizes: tuple[float, float, float] = STOP_SIZES
  max_degree: tuple[int, int, int] = MAX_DEGREE
  max_budget: float = MAX_BUDGET

  # Stop Criterion
  plateau_threshold: float = 1e-11
  plateau_count_limit: int = 10_000
  max_generations: int = 50_000

  checkpoint_every: int = 10

  @classmethod
  def from_dict(cls, raw: dict[str, any]) -> HyperParameters:
    return cls(**raw)


@dataclass
class RunState:
  network_population: list[Network]
  generation_num: int = 1
  best_population: list | None = None
  plateau_counter: int = 0
  elapsed_before: float = 0.0
  hv_anchor: tuple[np.ndarray, np.ndarray] | None = None
  best_hv: float = -np.inf
  hv_history: list = field(default_factory=list)
  best_hv_list: list = field(default_factory=list)

  def to_checkpoint(self, elapsed_total: float) -> dict:
    return {
      "network_population": self.network_population,
      "generation_num": self.generation_num,
      "most_optimal_gen": self.best_population,
      "plateau_counter": self.plateau_counter,
      "elapsed_seconds": elapsed_total,
      "python_random_state": random.getstate(),
      "numpy_random_state": np.random.get_state(),
      "hv_anchor": self.hv_anchor,
      "best_hv": self.best_hv,
      "hv_history": self.hv_history,
      "best_hv_list": self.best_hv_list,
    }

  @classmethod
  def from_checkpoint(cls, checkpoint: dict) -> RunState:
    if "python_random_state" in checkpoint:
      random.setstate(checkpoint["python_random_state"])
    if "numpy_random_state" in checkpoint:
      np.random.set_state(checkpoint["numpy_random_state"])
    return cls(
      network_population=checkpoint["network_population"],
      generation_num=checkpoint.get("generation_num", 1),
      best_population=checkpoint["most_optimal_gen"],
      plateau_counter=checkpoint["plateau_counter"],
      elapsed_before=checkpoint.get("elapsed_seconds", 0.0),
      hv_anchor=checkpoint.get("hv_anchor", None),
      best_hv=checkpoint.get("best_hv", -np.inf),
      hv_history=checkpoint.get("hv_history", []),
      best_hv_list=checkpoint.get("best_hv_list", [])
    )
