"""
Metro Manila rail trunk network for use in City Zone Creation / NSGA-II.

Operational lines as of 2026 only.
Station coordinates are read from ``data/rail_layer/rail_stations.json``
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from utils.route_utils import haversine

RAIL_STATIONS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "rail_layer" / "rail_stations.json"
)

# Average commercial speed (km/h) including station dwell. Published end-to-end
# journey times / line length give roughly these values.
LINE_SPEED_KPH = {
    "MRT-3": 35.0,
    "LRT-1": 30.0,
    "LRT-2": 32.0,
}

# Operator-published line lengths (km).
# line_segments scales by published_length / measured_length per line.
LINE_LENGTH_KM = {
    "MRT-3": 16.9,
    "LRT-1": 26.0,
    "LRT-2": 17.6,
}

# Station sequence per line. Order defines direction and inter-station distance.
STATION_ORDER = {
    "MRT-3": [
        "North Avenue", "Quezon Avenue", "GMA Kamuning", "Araneta Center Cubao",
        "Santolan-Annapolis", "Ortigas", "Shaw Boulevard", "Boni", "Guadalupe",
        "Buendia", "Ayala", "Magallanes", "Taft Avenue",
    ],
    "LRT-1": [
        "Fernando Poe Jr.", "Balintawak", "Monumento", "5th Avenue", "R. Papa",
        "Abad Santos", "Blumentritt", "Tayuman", "Bambang", "Doroteo Jose",
        "Carriedo", "Central Terminal", "United Nations", "Pedro Gil", "Quirino",
        "Vito Cruz", "Gil Puyat", "Libertad", "EDSA", "Baclaran",
        "Redemptorist", "MIA Road", "PITX", "Ninoy Aquino Avenue", "Dr Santos",
    ],
    "LRT-2": [
        "Recto", "Legarda", "Pureza", "V. Mapa", "J. Ruiz", "Gilmore",
        "Betty Go-Belmonte", "Araneta Center Cubao", "Anonas", "Katipunan",
        "Santolan", "Marikina-Pasig", "Antipolo",
    ],
}

# fixed transfers
RAIL_INTERCHANGES = [
    (("LRT-1", "Doroteo Jose"), ("LRT-2", "Recto")),
    (("MRT-3", "Araneta Center Cubao"), ("LRT-2", "Araneta Center Cubao")),
    (("LRT-1", "EDSA"), ("MRT-3", "Taft Avenue")),
]

# stations within city bounds as of 2026
CITY_RAIL_STATIONS = {
    "Makati": [
        ("MRT-3", "Guadalupe"),
        ("MRT-3", "Buendia"),
        ("MRT-3", "Ayala"),
        ("MRT-3", "Magallanes"),
    ],
    "Manila": [
        ("LRT-1", "R. Papa"),
        ("LRT-1", "Abad Santos"),
        ("LRT-1", "Blumentritt"),
        ("LRT-1", "Tayuman"),
        ("LRT-1", "Bambang"),
        ("LRT-1", "Doroteo Jose"),
        ("LRT-1", "Carriedo"),
        ("LRT-1", "Central Terminal"),
        ("LRT-1", "United Nations"),
        ("LRT-1", "Pedro Gil"),
        ("LRT-1", "Quirino"),
        ("LRT-1", "Vito Cruz"),
        ("LRT-2", "Recto"),
        ("LRT-2", "Legarda"),
        ("LRT-2", "Pureza"),
        ("LRT-2", "V. Mapa"),
    ],
    "Taguig": [],
}


def rail_stations_for(city: str) -> list[tuple[str, str]]:
    """(line, station) pairs that count as OD points in ``city``."""
    return CITY_RAIL_STATIONS.get(city, [])


def _load_stations(path: Path | None = None) -> dict[str, list[tuple[str, float, float]]]:
    """Read the OSM-derived station file and return ``{line: [(name, lat, lon)]}``."""
    p = Path(path) if path is not None else RAIL_STATIONS_PATH
    with open(p, encoding="utf-8") as f:
        raw = json.load(f)

    out: dict[str, list[tuple[str, float, float]]] = {}
    for line, order in STATION_ORDER.items():
        rows = {r["name"]: r for r in raw["lines"][line]}
        missing = [n for n in order if n not in rows]
        if missing:
            raise KeyError(
                f"{p} is missing {line} stations: {missing}. "
                f"Regenerate with: python scripts/fetch_rail_stations.py"
            )
        out[line] = [(n, rows[n]["lat"], rows[n]["lon"]) for n in order]
    return out


STATIONS = _load_stations()

LINES = {
    line: {"speed_kph": LINE_SPEED_KPH[line], "stations": STATIONS[line]}
    for line in STATION_ORDER
}


def measured_length_km(line: str) -> float:
    """Straight-line total along the line, before curvature correction."""
    st = LINES[line]["stations"]
    return sum(
        haversine(la, loa, lb, lob)
        for (_, la, loa), (_, lb, lob) in itertools.pairwise(st)
    )


def route_factor(line: str) -> float:
    """published length / measured straight-line length."""
    m = measured_length_km(line)
    return LINE_LENGTH_KM[line] / m if m > 0 else 1.0


def line_segments(line: str):
    """Yield (station_a, station_b, distance_km) along ``line``.

    Distances are curvature-corrected so the line totals match the published
    operator length.
    """
    st = LINES[line]["stations"]
    factor = route_factor(line)
    for (na, la, loa), (nb, lb, lob) in itertools.pairwise(st):
        yield na, nb, haversine(la, loa, lb, lob) * factor


def total_length_km(line: str) -> float:
    return sum(d for _, _, d in line_segments(line))


if __name__ == "__main__":
    tot = 0.0
    print(f"{'line':7}{'stations':>9}{'measured':>10}{'published':>11}{'factor':>8}{'speed':>7}{'e2e':>8}")
    for name in STATION_ORDER:
        km = total_length_km(name)
        tot += km
        med = measured_length_km(name)
        fac = route_factor(name)
        speed = LINE_SPEED_KPH[name]
        print(f"{name:7}{len(LINES[name]['stations']):>9}{med:>10.2f}"
              f"{km:>11.2f}{fac:>8.3f}{speed:>7.0f}{km/speed*60:>7.0f}m")
    print(f"\ntotal trunk length: {tot:.2f} km")

    manual = []
    with open(RAIL_STATIONS_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    n_osm = sum(1 for rows in raw["lines"].values()
                for r in rows if r.get("source") == "osm")
    for line, rows in raw["lines"].items():
        for r in rows:
            if r.get("source") == "manual":
                manual.append(f"{line}: {r['name']}")
    if manual:
        print(f"{n_osm} stations from OSM; "
              f"{len(manual)} on published coordinates (no usable OSM match):")
        for m in manual:
            print("  " + m)
