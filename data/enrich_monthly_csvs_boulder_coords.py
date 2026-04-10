#!/usr/bin/env python3
"""
Collect every unique Station ID from colorado_air_quality_*.csv and/or all_air_quality_data_*.csv under a directory,
assign each a (latitude, longitude) on a disk around Boulder with ~uniform spacing
(Vogel / golden-angle layout), then rewrite those CSVs with new columns latitude, longitude.

Run from repo root:

  python data/enrich_monthly_csvs_boulder_coords.py --monthly-dir data/monthly_csv

Large files are processed in chunks (safe replace via .tmp then rename).
"""
from __future__ import annotations

import argparse
import math
import shutil
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Default: near CU Boulder campus
DEFAULT_CENTER_LAT = 40.0150
DEFAULT_CENTER_LON = -105.2705


def _monthly_air_csv_paths(monthly_dir: Path) -> list[Path]:
    by_resolved: dict[str, Path] = {}
    for pattern in ("colorado_air_quality_*.csv", "all_air_quality_data_*.csv"):
        for p in monthly_dir.glob(pattern):
            by_resolved[str(p.resolve())] = p
    return sorted(by_resolved.values(), key=lambda p: p.name)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Add latitude/longitude per Station ID (spread on a disk around Boulder)."
    )
    p.add_argument(
        "--monthly-dir",
        type=Path,
        default=_REPO_ROOT / "data" / "monthly_csv",
        help="Directory with colorado_air_quality_*.csv and/or all_air_quality_data_*.csv",
    )
    p.add_argument("--chunk-size", type=int, default=100_000)
    p.add_argument(
        "--center-lat",
        type=float,
        default=DEFAULT_CENTER_LAT,
        help="Disk center latitude (default: Boulder / CU area)",
    )
    p.add_argument(
        "--center-lon",
        type=float,
        default=DEFAULT_CENTER_LON,
        help="Disk center longitude",
    )
    p.add_argument(
        "--radius-km",
        type=float,
        default=8.0,
        help="Max radius (km) from center for the outermost station (default: 8)",
    )
    return p.parse_args()


def positions_on_disk(
    n: int, center_lat: float, center_lon: float, radius_km: float
) -> list[tuple[float, float]]:
    """
    Vogel / golden-angle layout on a disk: good uniform area coverage; neighbor distances
    are similar (not perfectly equal for all pairs, but evenly spread across Boulder).
    """
    if n <= 0:
        return []
    if n == 1:
        return [(center_lat, center_lon)]
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    cos_lat = math.cos(math.radians(center_lat))
    out: list[tuple[float, float]] = []
    for k in range(n):
        r_norm = math.sqrt((k + 0.5) / n)
        r_km = r_norm * radius_km
        theta = k * golden_angle
        d_north_km = r_km * math.cos(theta)
        d_east_km = r_km * math.sin(theta)
        dlat = d_north_km / 111.0
        dlon = d_east_km / (111.0 * cos_lat)
        out.append((center_lat + dlat, center_lon + dlon))
    return out


def collect_unique_station_ids(paths: list[Path], chunk_size: int) -> list[str]:
    seen: set[str] = set()
    for path in paths:
        print(f"Scanning IDs: {path.name}")
        reader = pd.read_csv(
            path,
            usecols=["Station ID"],
            chunksize=chunk_size,
            dtype=str,
        )
        for chunk in reader:
            seen.update(chunk["Station ID"].str.strip().dropna().unique())
    return sorted(seen)


def build_station_to_latlon(
    station_ids: list[str], center_lat: float, center_lon: float, radius_km: float
) -> dict[str, tuple[float, float]]:
    pts = positions_on_disk(len(station_ids), center_lat, center_lon, radius_km)
    return {sid: (lat, lon) for sid, (lat, lon) in zip(station_ids, pts, strict=True)}


def enrich_file(path: Path, mapping: dict[str, tuple[float, float]], chunk_size: int) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()

    lat_col = pd.Series({k: v[0] for k, v in mapping.items()})
    lon_col = pd.Series({k: v[1] for k, v in mapping.items()})

    reader = pd.read_csv(path, chunksize=chunk_size, dtype=str, low_memory=False)
    first_chunk = True
    for chunk in reader:
        drop = [c for c in ("latitude", "longitude") if c in chunk.columns]
        if drop:
            chunk = chunk.drop(columns=drop)
        chunk["Station ID"] = chunk["Station ID"].str.strip()
        if not chunk["Station ID"].isin(lat_col.index).all():
            bad = chunk.loc[~chunk["Station ID"].isin(lat_col.index), "Station ID"].iloc[0]
            raise SystemExit(f"Station ID {bad!r} in {path.name} missing from mapping.")
        chunk["latitude"] = chunk["Station ID"].map(lat_col).astype(float)
        chunk["longitude"] = chunk["Station ID"].map(lon_col).astype(float)
        chunk.to_csv(tmp, mode="a", header=first_chunk, index=False)
        first_chunk = False

    path.unlink(missing_ok=False)
    shutil.move(str(tmp), str(path))
    print(f"Rewrote {path.name} with latitude, longitude")


def main() -> int:
    args = parse_args()
    monthly_dir = args.monthly_dir
    paths = _monthly_air_csv_paths(monthly_dir)
    if not paths:
        print(f"No colorado_air_quality_*.csv or all_air_quality_data_*.csv in {monthly_dir}")
        return 1

    station_ids = collect_unique_station_ids(paths, args.chunk_size)
    print(f"Unique Station IDs: {len(station_ids):,}")

    mapping = build_station_to_latlon(
        station_ids, args.center_lat, args.center_lon, args.radius_km
    )

    for path in paths:
        enrich_file(path, mapping, args.chunk_size)

    print("Done. Re-ingest with: python data/ingest_monthly_csv_to_postgres.py --monthly-dir ...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
