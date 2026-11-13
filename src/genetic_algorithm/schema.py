import random
from collections.abc import Sequence
from dataclasses import dataclass, field

import networkx as nx
import numpy as np


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
    self.fitness_score = None
    self.fitness_score_components = {}  # individual components for fitness


@dataclass(frozen=True, slots=True)
class HyperParameters:
  fitness_weights: dict
  walk_distance: int
  n_transport_nodes: int
  mutation_probability: float = 0.2
  mutations_per_child: Sequence[float] = (0.1, 0.1, 0.4, 0.2, 0.2)
  mutations_per_child_identical: Sequence[float] = (0.0, 0.1, 0.4, 0.3, 0.2)
  plateau_threshold: float = 1e-11
  plateau_count_limit: int = 10_000
  max_generations: int = 50_000
  selection_fraction: float = 0.10
  checkpoint_every: int = 10

  @classmethod
  def from_dict(cls, raw: dict[str, any]) -> HyperParameters:
    return cls(**raw)


@dataclass
class RunState:
  network_population: list[Network]
  generation_num: int = 1
  max_score_list: list = field(default_factory=list)
  best_population: list | None = None
  prev_max_score: float | None = None
  plateau_counter: int = 0
  best_max_score: float = 0.0
  best_avg_score: float = 0.0
  elapsed_before: float = 0.0

  def to_checkpoint(self, elapsed_total: float) -> dict:
    return {
      "generation_num": self.generation_num,
      "network_population": self.network_population,
      "max_score_list": self.max_score_list,
      "most_optimal_gen": self.best_population,
      "prev_max_fitness_score": self.prev_max_score,
      "plateau_counter": self.plateau_counter,
      "current_highest_max_score": self.best_max_score,
      "current_highest_avg_score": self.best_avg_score,
      "elapsed_seconds": elapsed_total,
      "python_random_state": random.getstate(),
      "numpy_random_state": np.random.get_state(),
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
      max_score_list=checkpoint["max_score_list"],
      best_population=checkpoint["most_optimal_gen"],
      prev_max_score=checkpoint["prev_max_fitness_score"],
      plateau_counter=checkpoint["plateau_counter"],
      best_max_score=checkpoint["current_highest_max_score"],
      best_avg_score=checkpoint["current_highest_avg_score"],
      elapsed_before=checkpoint.get("elapsed_seconds", 0.0),
    )
