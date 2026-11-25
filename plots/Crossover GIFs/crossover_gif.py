from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw


def _get_xy(graph_of_stops):
  pos = {}
  for n, d in graph_of_stops.nodes(data=True):
    x = d.get("x", d.get("lon"))
    y = d.get("y", d.get("lat"))
    if x is not None and y is not None:
      pos[n] = (float(x), float(y))
  return pos


def _route_signature(route_obj):
  return tuple(tuple(seg) for seg in route_obj.route)


def _route_edges(route_obj, pos):
  edges = []
  for seg in route_obj.route:
    if len(seg) < 2:
      continue
    if all(n in pos for n in seg):
      edges.extend((seg[i], seg[i + 1]) for i in range(len(seg) - 1))
    elif seg[0] in pos and seg[-1] in pos:
      edges.append((seg[0], seg[-1]))
  return edges


def _offset_segment(p1, p2, offset_dist):
  x1, y1 = p1
  x2, y2 = p2
  dx, dy = x2 - x1, y2 - y1
  length = np.hypot(dx, dy)
  if length == 0 or offset_dist == 0:
    return (x1, x2), (y1, y2)
  nx_, ny_ = -dy / length, dx / length
  return (
    (x1 + nx_ * offset_dist, x2 + nx_ * offset_dist),
    (y1 + ny_ * offset_dist, y2 + ny_ * offset_dist),
  )


def _draw_network(
  ax,
  pos,
  base_edges,
  routes,
  route_colors,
  swapped_sigs,
  route_labels,
  lane_step,
  xlim,
  ylim,
  title,
):
  # 1. Base graph
  for u, v in base_edges:
    if u in pos and v in pos:
      ax.plot(
        [pos[u][0], pos[v][0]],
        [pos[u][1], pos[v][1]],
        color="#ececec",
        lw=0.5,
        zorder=1,
      )

  # 2. Parallel lane slots per undirected edge
  edge_routes = defaultdict(list)
  for idx, r in enumerate(routes):
    seen = set()
    for u, v in _route_edges(r, pos):
      key = tuple(sorted((u, v)))
      if key not in seen:
        seen.add(key)
        edge_routes[key].append(idx)

  # 3. Draw kept routes first, swapped routes on top
  draw_order = sorted(
    range(len(routes)),
    key=lambda idx: 1 if _route_signature(routes[idx]) in swapped_sigs else 0,
  )

  for idx in draw_order:
    r = routes[idx]
    sig = _route_signature(r)
    color = route_colors[sig]
    is_swapped = sig in swapped_sigs

    lw = 3.0 if is_swapped else 1.8
    alpha = 0.95 if is_swapped else 0.55
    z = 4 if is_swapped else 2

    edges = _route_edges(r, pos)
    mid_idx = len(edges) // 2
    label_xy = None

    for e_i, (u, v) in enumerate(edges):
      key = tuple(sorted((u, v)))
      sharers = edge_routes[key]
      slot = sharers.index(idx) - (len(sharers) - 1) / 2.0
      a, b = key
      xs, ys = _offset_segment(pos[a], pos[b], slot * lane_step)

      if e_i == mid_idx:
        label_xy = ((xs[0] + xs[1]) / 2, (ys[0] + ys[1]) / 2)

      if is_swapped:
        ax.plot(
          xs,
          ys,
          color="white",
          lw=lw + 2.0,
          alpha=0.9,
          solid_capstyle="round",
          zorder=z - 0.5,
        )
      ax.plot(
        xs,
        ys,
        color=color,
        lw=lw,
        alpha=alpha,
        solid_capstyle="round",
        zorder=z,
      )

    # Terminal dots on swapped routes
    if is_swapped and edges:
      for node in (edges[0][0], edges[-1][1]):
        if node in pos:
          ax.scatter(
            pos[node][0],
            pos[node][1],
            s=42,
            color=color,
            edgecolors="white",
            linewidths=1.0,
            zorder=5,
          )

    # Origin + route number badge on ALL routes
    if label_xy is not None and sig in route_labels:
      ax.text(
        label_xy[0],
        label_xy[1],
        route_labels[sig],
        fontsize=8.5 if is_swapped else 7.0,
        fontweight="bold",
        color="white",
        ha="center",
        va="center",
        zorder=6 if is_swapped else 5,
        bbox={
          "boxstyle": "round,pad=0.22" if is_swapped else "round,pad=0.18",
          "facecolor": color,
          "edgecolor": "white",
          "lw": 1.0 if is_swapped else 0.7,
          "alpha": 1.0 if is_swapped else 0.8,
        },
      )

  ax.set_xlim(xlim)
  ax.set_ylim(ylim)
  ax.set_aspect("equal")
  ax.axis("off")
  ax.set_title(title, fontsize=13, fontweight="bold", pad=8)


def make_crossover_gif(
  parent1,
  parent2,
  child1,
  child2,
  graph_of_stops,
  out_dir: str | Path,
  name: str = "crossover",
  mode: str = "wipe",
  n_steps: int = 24,
  step_ms: int = 60,
  hold_ms: int = 1600,
  ping_pong: bool = True,
):
  out_dir = Path(out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)

  pos = _get_xy(graph_of_stops)
  xs = [p[0] for p in pos.values()]
  ys = [p[1] for p in pos.values()]
  span = max(max(xs) - min(xs), max(ys) - min(ys))
  pad_x = (max(xs) - min(xs)) * 0.03
  pad_y = (max(ys) - min(ys)) * 0.03
  xlim = (min(xs) - pad_x, max(xs) + pad_x)
  ylim = (min(ys) - pad_y, max(ys) + pad_y)
  lane_step = span * 0.0045
  base_edges = list(graph_of_stops.edges())

  # Persistent color per unique route
  cmap = plt.get_cmap("tab20")
  route_colors = {}
  for net in (parent1, parent2, child1, child2):
    for r in net.routes:
      sig = _route_signature(r)
      if sig not in route_colors:
        route_colors[sig] = cmap(len(route_colors) % 20)

  # Identify swapped routes
  p1_sigs = {_route_signature(r) for r in parent1.routes}
  p2_sigs = {_route_signature(r) for r in parent2.routes}
  c1_sigs = {_route_signature(r) for r in child1.routes}
  c2_sigs = {_route_signature(r) for r in child2.routes}
  swapped_sigs = (p1_sigs - c1_sigs) | (p2_sigs - c2_sigs)

  # Label EVERY route with its parent origin and route number
  route_labels = {}
  for i, r in enumerate(parent1.routes, 1):
    sig = _route_signature(r)
    route_labels[sig] = f"P1-{i}"

  for i, r in enumerate(parent2.routes, 1):
    sig = _route_signature(r)
    if sig in route_labels:
      route_labels[sig] += f"/P2-{i}"
    else:
      route_labels[sig] = f"P2-{i}"

  # Fallback for any brand-new routes created in children
  new_idx = 1
  for net in (child1, child2):
    for r in net.routes:
      sig = _route_signature(r)
      if sig not in route_labels:
        route_labels[sig] = f"New-{new_idx}"
        new_idx += 1

  before_png = out_dir / f"{name}_before.png"
  after_png = out_dir / f"{name}_after.png"
  gif_path = out_dir / f"{name}.gif"

  # BEFORE (Parents)
  fig, axes = plt.subplots(1, 2, figsize=(14, 7), dpi=150)
  _draw_network(
    axes[0],
    pos,
    base_edges,
    parent1.routes,
    route_colors,
    swapped_sigs,
    route_labels,
    lane_step,
    xlim,
    ylim,
    "Parent 1 (bold = swapped)",
  )
  _draw_network(
    axes[1],
    pos,
    base_edges,
    parent2.routes,
    route_colors,
    swapped_sigs,
    route_labels,
    lane_step,
    xlim,
    ylim,
    "Parent 2 (bold = swapped)",
  )
  fig.suptitle("Crossover — BEFORE (Parents)", fontsize=15, fontweight="bold", y=0.98)
  fig.tight_layout(rect=[0, 0, 1, 0.94])
  fig.savefig(before_png, bbox_inches="tight", facecolor="white")
  plt.close(fig)

  # AFTER (Children)
  fig, axes = plt.subplots(1, 2, figsize=(14, 7), dpi=150)
  _draw_network(
    axes[0],
    pos,
    base_edges,
    child1.routes,
    route_colors,
    swapped_sigs,
    route_labels,
    lane_step,
    xlim,
    ylim,
    "Child 1 (received P2 routes)",
  )
  _draw_network(
    axes[1],
    pos,
    base_edges,
    child2.routes,
    route_colors,
    swapped_sigs,
    route_labels,
    lane_step,
    xlim,
    ylim,
    "Child 2 (received P1 routes)",
  )
  fig.suptitle("Crossover — AFTER (Children)", fontsize=15, fontweight="bold", y=0.98)
  fig.tight_layout(rect=[0, 0, 1, 0.94])
  fig.savefig(after_png, bbox_inches="tight", facecolor="white")
  plt.close(fig)

  # Build GIF
  before_img = Image.open(before_png).convert("RGBA")
  after_img = Image.open(after_png).convert("RGBA")
  if after_img.size != before_img.size:
    after_img = after_img.resize(before_img.size, Image.Resampling.LANCZOS)

  w, h = before_img.size
  frames, durations = [], []

  def _transition(t: float) -> Image.Image:
    if mode == "fade":
      return Image.blend(before_img, after_img, t)
    split_x = round(w * t)
    frame = before_img.copy()
    if split_x > 0:
      frame.paste(after_img.crop((0, 0, split_x, h)), (0, 0))
    if 0 < split_x < w:
      ImageDraw.Draw(frame).line(
        [(split_x, 0), (split_x, h)], fill=(40, 40, 40, 200), width=3
      )
    return frame

  frames.append(before_img.copy())
  durations.append(hold_ms)
  for i in range(1, n_steps):
    frames.append(_transition(i / n_steps))
    durations.append(step_ms)
  frames.append(after_img.copy())
  durations.append(hold_ms)
  if ping_pong:
    for i in range(n_steps - 1, 0, -1):
      frames.append(_transition(i / n_steps))
      durations.append(step_ms)

  rgb_frames = [f.convert("RGB") for f in frames]
  rgb_frames[0].save(
    gif_path,
    save_all=True,
    append_images=rgb_frames[1:],
    duration=durations,
    loop=0,
    optimize=True,
  )
  return before_png, after_png, gif_path


# --- Usage ---
# child1, child2, is_different = crossover(
#   deepcopy(parent1), deepcopy(parent2), graph_of_stops
# )

# if is_different:
#   before_png, after_png, gif_path = make_crossover_gif(
#     parent1, parent2, child1, child2, graph_of_stops, out_dir, mode="wipe"
#   )
