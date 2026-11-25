from pathlib import Path

import matplotlib.pyplot as plt
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


def _route_stops(route_obj):
  stops = set()
  for seg in route_obj.route:
    if seg:
      stops.add(seg[0])
      stops.add(seg[-1])
  return stops


def _draw_mutated_network(
  ax,
  pos,
  base_edges,
  mutated_routes,
  route_colors,
  route_labels,
  diff_segs,
  diff_stops,
  diff_color: str,
  xlim,
  ylim,
  title: str,
):
  # 1. Faint base road network
  for u, v in base_edges:
    if u in pos and v in pos:
      ax.plot(
        [pos[u][0], pos[v][0]],
        [pos[u][1], pos[v][1]],
        color="#ececec",
        lw=0.5,
        zorder=1,
      )

  # 2. Only the modified route(s), single centered line per edge + white halo
  for r in mutated_routes:
    sig = _route_signature(r)
    color = route_colors.get(sig, "#1f77b4")
    label = route_labels.get(sig, "R")

    edges = _route_edges(r, pos)
    mid_idx = len(edges) // 2
    label_xy = None

    for e_i, (u, v) in enumerate(edges):
      xs = [pos[u][0], pos[v][0]]
      ys = [pos[u][1], pos[v][1]]

      if e_i == mid_idx:
        label_xy = ((xs[0] + xs[1]) / 2, (ys[0] + ys[1]) / 2)

      # White halo + bold route line (matching crossover highlight styling)
      ax.plot(
        xs,
        ys,
        color="white",
        lw=5.0,
        alpha=0.9,
        solid_capstyle="round",
        zorder=2.5,
      )
      ax.plot(
        xs,
        ys,
        color=color,
        lw=3.0,
        alpha=0.95,
        solid_capstyle="round",
        zorder=3,
      )

      # Highlighted diff segment directly on the same single path
      key = tuple(sorted((u, v)))
      if key in diff_segs:
        ax.plot(
          xs,
          ys,
          color="white",
          lw=6.0,
          alpha=0.9,
          solid_capstyle="round",
          zorder=4.5,
        )
        ax.plot(
          xs,
          ys,
          color=diff_color,
          lw=4.0,
          alpha=1.0,
          solid_capstyle="round",
          zorder=5,
        )

    # Terminal dots
    if edges:
      for node in (edges[0][0], edges[-1][1]):
        if node in pos:
          ax.scatter(
            pos[node][0],
            pos[node][1],
            s=42,
            color=color,
            edgecolors="white",
            linewidths=1.0,
            zorder=6,
          )

    # Route number badge (matching crossover badge style)
    if label_xy is not None:
      ax.text(
        label_xy[0],
        label_xy[1],
        label,
        fontsize=8.5,
        fontweight="bold",
        color="white",
        ha="center",
        va="center",
        zorder=7,
        bbox={
          "boxstyle": "round,pad=0.22",
          "facecolor": color,
          "edgecolor": "white",
          "lw": 1.0,
          "alpha": 1.0,
        },
      )

  # 3. Added/removed stop nodes
  if diff_stops:
    sx = [pos[n][0] for n in diff_stops if n in pos]
    sy = [pos[n][1] for n in diff_stops if n in pos]
    ax.scatter(
      sx,
      sy,
      s=65,
      color=diff_color,
      edgecolors="white",
      linewidths=1.2,
      zorder=8,
    )

  ax.set_xlim(xlim)
  ax.set_ylim(ylim)
  ax.set_aspect("equal")
  ax.axis("off")
  ax.set_title(title, fontsize=13, fontweight="bold", pad=8)


def make_mutation_gif(
  before_net,
  after_net,
  graph_of_stops,
  operator_name: str,
  out_dir: str | Path,
  mode: str = "wipe",
  n_steps: int = 24,
  step_ms: int = 60,
  hold_ms: int = 1200,
  ping_pong: bool = True,
):
  out_dir = Path(out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)

  pos = _get_xy(graph_of_stops)
  xs = [p[0] for p in pos.values()]
  ys = [p[1] for p in pos.values()]
  pad_x = (max(xs) - min(xs)) * 0.03
  pad_y = (max(ys) - min(ys)) * 0.03
  xlim = (min(xs) - pad_x, max(xs) + pad_x)
  ylim = (min(ys) - pad_y, max(ys) + pad_y)
  base_edges = list(graph_of_stops.edges())

  before_sigs = {_route_signature(r) for r in before_net.routes}
  after_sigs = {_route_signature(r) for r in after_net.routes}

  before_mutated = [
    r for r in before_net.routes if _route_signature(r) not in after_sigs
  ]
  after_mutated = [
    r for r in after_net.routes if _route_signature(r) not in before_sigs
  ]

  # Assign persistent route numbers & colors across BEFORE and AFTER
  cmap = plt.get_cmap("tab20")
  palette = [cmap(i) for i in range(20) if i not in (4, 5, 6, 7)]

  route_colors = {}
  route_labels = {}
  unmatched_before = []

  for i, r in enumerate(before_net.routes, 1):
    sig = _route_signature(r)
    color = palette[(i - 1) % len(palette)]
    label = f"R{i}"
    route_colors[sig] = color
    route_labels[sig] = label
    if sig not in after_sigs:
      unmatched_before.append((label, color))

  extra_idx = len(before_net.routes) + 1
  for r in after_net.routes:
    sig = _route_signature(r)
    if sig not in route_colors:
      if unmatched_before:
        label, color = unmatched_before.pop(0)
      else:
        label = f"R{extra_idx}"
        color = palette[(extra_idx - 1) % len(palette)]
        extra_idx += 1
      route_colors[sig] = color
      route_labels[sig] = label

  # Diff segments & stops strictly within the modified route(s)
  b_mut_segs = {tuple(sorted(e)) for r in before_mutated for e in _route_edges(r, pos)}
  a_mut_segs = {tuple(sorted(e)) for r in after_mutated for e in _route_edges(r, pos)}
  removed_segs = b_mut_segs - a_mut_segs
  added_segs = a_mut_segs - b_mut_segs

  b_mut_stops = (
    set().union(*(_route_stops(r) for r in before_mutated)) if before_mutated else set()
  )
  a_mut_stops = (
    set().union(*(_route_stops(r) for r in after_mutated)) if after_mutated else set()
  )
  removed_stops = b_mut_stops - a_mut_stops
  added_stops = a_mut_stops - b_mut_stops

  print(
    f"[{operator_name}] mutated routes: {len(before_mutated)} -> {len(after_mutated)} | "
    f"segs: -{len(removed_segs)} / +{len(added_segs)} | "
    f"stops: -{len(removed_stops)} / +{len(added_stops)}"
  )

  before_has_diff = bool(removed_segs or removed_stops)
  after_has_diff = bool(added_segs or added_stops)
  before_title = f"{operator_name} — BEFORE" + (
    " (red = removed)" if before_has_diff else ""
  )
  after_title = f"{operator_name} — AFTER" + (
    " (green = added)" if after_has_diff else ""
  )

  before_png = out_dir / f"{operator_name}_before.png"
  after_png = out_dir / f"{operator_name}_after.png"
  gif_path = out_dir / f"{operator_name}.gif"

  fig, axes = plt.subplots(1, 2, figsize=(14, 7), dpi=150)
  _draw_mutated_network(
    axes[0],
    pos,
    base_edges,
    before_mutated,
    route_colors,
    route_labels,
    removed_segs,
    removed_stops,
    "#d62728",
    xlim,
    ylim,
    before_title,
  )
  _draw_mutated_network(
    axes[1],
    pos,
    base_edges,
    after_mutated,
    route_colors,
    route_labels,
    added_segs,
    added_stops,
    "#2ca02c",
    xlim,
    ylim,
    after_title,
  )
  fig.suptitle(f"Mutation — {operator_name}", fontsize=15, fontweight="bold", y=0.98)
  fig.tight_layout(rect=[0, 0, 1, 0.94])
  fig.savefig(before_png, bbox_inches="tight", facecolor="white")
  plt.close(fig)

  # Separate single-panel renders for smooth wipe/fade GIF transitions
  for out_f, mut_routes, segs, stops, diff_col, panel_title in [
    (
      before_png,
      before_mutated,
      removed_segs,
      removed_stops,
      "#d62728",
      before_title,
    ),
    (
      after_png,
      after_mutated,
      added_segs,
      added_stops,
      "#2ca02c",
      after_title,
    ),
  ]:
    fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
    _draw_mutated_network(
      ax,
      pos,
      base_edges,
      mut_routes,
      route_colors,
      route_labels,
      segs,
      stops,
      diff_col,
      xlim,
      ylim,
      panel_title,
    )
    fig.tight_layout()
    fig.savefig(out_f, bbox_inches="tight", facecolor="white")
    plt.close(fig)

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
