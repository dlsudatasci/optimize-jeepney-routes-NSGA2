# run: python -m utils.make_population_csv <city_name> (only "Taguig" works)

from __future__ import annotations
import argparse
import os
import sys
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

# this file is <repo>/src/utils/make_population_csv.py
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"

HRSL_PATH = REPO_ROOT / "phl_general_2020.csv"
OUTPUT_DIR = DATA_DIR / "population_distribution"
AMENITY_MAPS_DIR = REPO_ROOT / "data" / "amenity_maps"

BOUNDARIES = {
    "Taguig": AMENITY_MAPS_DIR / "Taguig" / "taguig_boundary_tmp.gpkg",
}
VALUE_COL = "phl_general_2020"
REQUIRED_COLS = ("longitude", "latitude", VALUE_COL)

# Padding used when shrinking the boundary to a bbox for the prefilter.
BBOX_PAD = 0.25
CHUNK_ROWS = 2_000_000

# for sanity check 
CENSUS_2020 = {
    "Taguig": 1_366_659,
    "Makati": 629_616,
    "Manila": 1_846_513,
    "Mandaluyong": 425_758,
}

def load_boundary(path: str) -> tuple[gpd.GeoDataFrame, shapely.Geometry]:
    # Load a boundary file and union it into a single containment geometry.
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")

    geom = shapely.union_all(gdf.geometry.values)
    if not geom.is_valid:
        geom = shapely.make_valid(geom)
    return gdf, geom


def scan_hrsl(hrsl_path: str, bounds: tuple[float, ...]) -> pd.DataFrame:
    # Chunk-scan the HRSL CSV and return only rows inside ``bounds``.
    lon_min, lat_min, lon_max, lat_max = bounds
    keep: list[pd.DataFrame] = []
    total = 0

    reader = pd.read_csv(hrsl_path, usecols=list(REQUIRED_COLS), chunksize=CHUNK_ROWS)
    for idx, chunk in enumerate(reader):
        total += len(chunk)
        mask = chunk["longitude"].between(lon_min, lon_max) & chunk[
            "latitude"
        ].between(lat_min, lat_max)
        sub = chunk[mask]
        if len(sub):
            keep.append(sub)
        print(f"  chunk {idx}: {len(chunk):>9,} rows scanned, {len(sub):>7,} kept")

    print(f"  scanned {total:,} rows total")
    if not keep:
        raise SystemExit(
            "no rows fell inside the boundary bbox; check that the boundary and the HRSL CSV refer to the same country"
        )
    return pd.concat(keep, ignore_index=True)


def clip_to_boundary(df: pd.DataFrame, geom: shapely.Geometry) -> pd.DataFrame:
    # Keep only points strictly inside the boundary, dropping duplicates.
    df = df.drop_duplicates(subset=["longitude", "latitude"])
    pts = shapely.points(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    return df[shapely.contains(geom, pts)].reset_index(drop=True)


def add_reference_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Add the ``geometry`` and ``index_right`` columns to match sibling files.
    out = df.copy()
    out["geometry"] = shapely.to_wkt(
        shapely.points(out["longitude"].to_numpy(), out["latitude"].to_numpy()),
        rounding_precision=-1,
    )
    out["index_right"] = 0 # index_right is just 0 so idk what they were cooking here
    return out


def report(city: str, df: pd.DataFrame, boundary: shapely.Geometry) -> float:
    # Print diagnostics for a clipped frame; return the population total.
    total = float(df[VALUE_COL].sum())
    expected = CENSUS_2020.get(city)
    ratio = total / expected if expected else float("nan")

    print(f"\nboundary area:           {boundary.area:.6f} deg^2")
    print(f"points inside boundary:  {len(df):,}")
    print(f"population sum:          {total:,.0f}")
    if expected:
        print(f"2020 census ({city}): {expected:,}  -> ratio {ratio:.3f}")
    print(
        f"lon range {df['longitude'].min():.5f} - {df['longitude'].max():.5f} | "
        f"lat range {df['latitude'].min():.5f} - {df['latitude'].max():.5f}"
    )
    print(
        f"value min {df[VALUE_COL].min():.4f} max {df[VALUE_COL].max():.4f} | "
        f"zero cells {(df[VALUE_COL] == 0).sum():,}"
    )

    if expected and not 0.5 <= ratio <= 1.0:
        print(
            f"WARNING: ratio {ratio:.3f} is outside the expected 0.5-1.0 band. "
            "The boundary may cover the wrong area, or may be a pre-2023 "
            "boundary that excludes barangays since transferred to this city.",
            file=sys.stderr,
        )
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build population CSV for CZC from Meta highres pop. data."
    )
    parser.add_argument("city", help="City name, e.g. Taguig")
    parser.add_argument(
        "--dry-run", action="store_true", help="print diagnostics without writing"
    )
    args = parser.parse_args(argv)

    city = args.city
    if city not in BOUNDARIES:
        raise SystemExit(
            f"no boundary registered for {city!r}; known cities: "
            f"{', '.join(sorted(BOUNDARIES))} (add one to BOUNDARIES)"
        )

    started = time.time()
    boundary_path = BOUNDARIES[city]
    out_path = OUTPUT_DIR / f"{city.lower()}-population-polygon.csv"

    _, boundary = load_boundary(boundary_path)
    lon_min, lat_min, lon_max, lat_max = boundary.bounds
    print(f"city:     {city}")
    print(f"boundary: {boundary_path}")
    print(
        f"  bounds lon {lon_min:.4f}-{lon_max:.4f} lat {lat_min:.4f}-{lat_max:.4f}"
    )

    padded = (
        lon_min - BBOX_PAD,
        lat_min - BBOX_PAD,
        lon_max + BBOX_PAD,
        lat_max + BBOX_PAD,
    )
    print(f"\nscanning {HRSL_PATH}")
    candidates = scan_hrsl(HRSL_PATH, padded)

    df = clip_to_boundary(candidates, boundary)
    report(city, df, boundary)

    out = add_reference_columns(df)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"\nwrote {out_path} ({len(out):,} rows) in {time.time() - started:.1f}s")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
