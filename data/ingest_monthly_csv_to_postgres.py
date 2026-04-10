#!/usr/bin/env python3
"""
Load monthly air-quality CSVs into PostGIS.

Files discovered (non-overlapping union): ``colorado_air_quality_*.csv``, ``all_air_quality_data_*.csv``.

Station coordinates:
  • If columns latitude + longitude exist (from enrich_monthly_csvs_boulder_coords.py), those are used.
  • Otherwise coordinates are loaded from AirNow Monitoring_Site_Locations_V2.dat (AQSID = Station ID).

From repo root (DATABASE_URL set, migrations applied):

  python data/enrich_monthly_csvs_boulder_coords.py --monthly-dir data/monthly_csv
  python data/ingest_monthly_csv_to_postgres.py --monthly-dir data/monthly_csv

Optional: --clear-ingested-sites removes sites/observations that have external_station_id (keeps any rows without it).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd
from geoalchemy2.elements import WKTElement
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from packages.airtrail_core.models import MonitoringSite, PollutionObservation

DEFAULT_LOCATIONS_URL = (
    "https://s3-us-west-1.amazonaws.com/files.airnowtech.org/airnow/today/Monitoring_Site_Locations_V2.dat"
)

ALLOWED_POLLUTANTS = frozenset({"PM2.5", "PM10", "SO2", "NO", "NO2", "OZONE", "CO"})


def _monthly_air_csv_paths(monthly_dir: Path) -> list[Path]:
    """Colorado sample exports and AirNow monthly files share the same column layout."""
    by_resolved: dict[str, Path] = {}
    for pattern in ("colorado_air_quality_*.csv", "all_air_quality_data_*.csv"):
        for p in monthly_dir.glob(pattern):
            by_resolved[str(p.resolve())] = p
    return sorted(by_resolved.values(), key=lambda p: p.name)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest monthly CSVs into pollution_observations.")
    p.add_argument(
        "--monthly-dir",
        type=Path,
        default=_REPO_ROOT / "data" / "monthly_csv",
        help="Directory containing colorado_air_quality_*.csv and/or all_air_quality_data_*.csv",
    )
    p.add_argument(
        "--locations",
        type=Path,
        default=None,
        help="Local Monitoring_Site_Locations_V2.dat (only if CSVs lack latitude/longitude).",
    )
    p.add_argument("--locations-url", default=DEFAULT_LOCATIONS_URL)
    p.add_argument(
        "--cache-locations",
        type=Path,
        default=_REPO_ROOT / "data" / "cache" / "Monitoring_Site_Locations_V2.dat",
        help="Cache path when downloading AirNow locations.",
    )
    p.add_argument("--chunk-size", type=int, default=50_000)
    p.add_argument(
        "--clear-ingested-sites",
        action="store_true",
        help="Delete observations and sites that have external_station_id.",
    )
    return p.parse_args()


def ensure_locations(path: Path | None, url: str, cache: Path) -> Path:
    if path is not None and path.is_file():
        return path
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.is_file():
        print(f"Downloading station locations → {cache}")
        urlretrieve(url, str(cache))
    return cache


def load_station_coords_airnow(locations_path: Path) -> dict[str, tuple[float, float, str]]:
    df = pd.read_csv(locations_path, sep="|", dtype=str)
    df["AQSID"] = df["AQSID"].str.strip()
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    out: dict[str, tuple[float, float, str]] = {}
    for _, row in df.iterrows():
        sid = row["AQSID"]
        if sid in out:
            continue
        lat, lon = row["Latitude"], row["Longitude"]
        if pd.isna(lat) or pd.isna(lon):
            continue
        if lat == 0 and lon == 0:
            continue
        name = str(row.get("SiteName", "") or "")
        out[sid] = (float(lat), float(lon), name)
    print(f"Loaded {len(out):,} station coordinates from AirNow")
    return out


def csv_sample_has_lat_lon(csv_path: Path, nrows: int = 5) -> bool:
    df = pd.read_csv(csv_path, nrows=nrows)
    return "latitude" in df.columns and "longitude" in df.columns


def merge_coords_from_chunk(
    coord_map: dict[str, tuple[float, float, str]],
    chunk: pd.DataFrame,
) -> None:
    """Fill coord_map from CSV latitude/longitude + Location (first row per Station ID)."""
    cols = ["Station ID", "latitude", "longitude"]
    if not all(c in chunk.columns for c in cols):
        return
    sub = chunk[cols + (["Location"] if "Location" in chunk.columns else [])].copy()
    sub["Station ID"] = sub["Station ID"].str.strip()
    sub = sub.drop_duplicates(subset=["Station ID"], keep="first")
    for _, row in sub.iterrows():
        sid = row["Station ID"]
        if sid in coord_map:
            continue
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
        except (TypeError, ValueError):
            continue
        name = ""
        if "Location" in row.index and pd.notna(row["Location"]):
            name = str(row["Location"]).strip()
        coord_map[sid] = (lat, lon, name)


def attach_utc_timestamps(chunk: pd.DataFrame) -> pd.DataFrame:
    local = pd.to_datetime(
        chunk["Date"].str.strip() + " " + chunk["Hour"].str.strip(),
        format="%m/%d/%y %H:%M",
        errors="coerce",
    )
    off = pd.to_numeric(chunk["Offset"], errors="coerce").fillna(0.0)
    return chunk.assign(_ts=local - pd.to_timedelta(off, unit="h"))


def main() -> int:
    args = parse_args()
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql://airtrail:password@localhost:5433/airtrail"
    )
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    monthly_files = _monthly_air_csv_paths(args.monthly_dir)
    if not monthly_files:
        print(
            f"No files matching colorado_air_quality_*.csv or all_air_quality_data_*.csv under {args.monthly_dir}"
        )
        session.close()
        return 1

    coord_map: dict[str, tuple[float, float, str]] = {}
    use_csv_coords = csv_sample_has_lat_lon(monthly_files[0])
    if use_csv_coords:
        print("Using latitude/longitude from monthly CSVs (enriched).")
    else:
        lpath = ensure_locations(args.locations, args.locations_url, args.cache_locations)
        coord_map = load_station_coords_airnow(lpath)

    if args.clear_ingested_sites:
        print("Clearing ingested sites + their observations...")
        session.execute(
            text(
                "UPDATE exposure_points SET matched_site_id = NULL WHERE matched_site_id IN "
                "(SELECT id FROM monitoring_sites WHERE external_station_id IS NOT NULL)"
            )
        )
        session.execute(
            text(
                "DELETE FROM pollution_observations WHERE site_id IN "
                "(SELECT id FROM monitoring_sites WHERE external_station_id IS NOT NULL)"
            )
        )
        session.execute(text("DELETE FROM monitoring_sites WHERE external_station_id IS NOT NULL"))
        session.commit()

    site_by_external: dict[str, int] = {
        str(r[0]).strip(): r[1]
        for r in session.execute(
            text("SELECT external_station_id, id FROM monitoring_sites WHERE external_station_id IS NOT NULL")
        ).fetchall()
    }

    obs_table = PollutionObservation.__table__
    attempted = 0

    dtype_base = {
        "Station ID": str,
        "Date": str,
        "Hour": str,
        "Pollutant": str,
        "Unit": str,
        "Measurement": str,
        "Offset": str,
    }

    for csv_path in monthly_files:
        print(f"Ingesting {csv_path.name} ...")
        reader = pd.read_csv(csv_path, chunksize=args.chunk_size, dtype=dtype_base, low_memory=False)
        for chunk in reader:
            chunk["Station ID"] = chunk["Station ID"].str.strip()
            chunk = chunk[chunk["Pollutant"].isin(ALLOWED_POLLUTANTS)]

            if use_csv_coords:
                merge_coords_from_chunk(coord_map, chunk)

            chunk = chunk[chunk["Station ID"].isin(coord_map.keys())]
            if chunk.empty:
                continue

            stids = set(chunk["Station ID"].unique())
            missing = sorted(stids - site_by_external.keys())
            for sid in missing:
                lat, lon, name = coord_map[sid]
                session.add(
                    MonitoringSite(
                        name=name or sid,
                        external_station_id=sid,
                        location=WKTElement(f"POINT ({lon} {lat})", srid=4326),
                    )
                )
            if missing:
                session.flush()
                for sid in missing:
                    nid = session.execute(
                        select(MonitoringSite.id).where(MonitoringSite.external_station_id == sid)
                    ).scalar_one()
                    site_by_external[sid] = nid

            chunk = attach_utc_timestamps(chunk)
            chunk = chunk[chunk["_ts"].notna()]
            chunk["_val"] = pd.to_numeric(chunk["Measurement"], errors="coerce")
            chunk = chunk[chunk["_val"].notna()]
            chunk["_site_id"] = chunk["Station ID"].map(site_by_external)
            chunk = chunk[chunk["_site_id"].notna()]

            if chunk.empty:
                continue

            units = chunk["Unit"].fillna("unknown").astype(str).str.strip().str.lower()
            batch = []
            for sid, ts, pol, val, unit in zip(
                chunk["_site_id"],
                chunk["_ts"],
                chunk["Pollutant"],
                chunk["_val"],
                units,
                strict=True,
            ):
                ts_py = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                batch.append(
                    {
                        "site_id": int(sid),
                        "timestamp": ts_py,
                        "pollutant": pol,
                        "value": float(val),
                        "unit": unit or "unknown",
                    }
                )

            insert_stmt = insert(obs_table).values(batch)
            # Replace values when the same site/timestamp/pollutant is ingested again (e.g. regenerated CSVs).
            stmt = insert_stmt.on_conflict_do_update(
                constraint="uq_pollution_obs_site_time_pollutant",
                set_={
                    "value": insert_stmt.excluded.value,
                    "unit": insert_stmt.excluded.unit,
                },
            )
            session.execute(stmt)
            attempted += len(batch)
            session.commit()

    session.close()
    print(f"Finished. Rows upserted (insert or update on conflict): {attempted:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
