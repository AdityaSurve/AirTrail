"""
Daily incremental download: list S3 keys for recent day prefixes only, download
only .dat files not already present under downloads/, append monthly CSVs for new files.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import datetime as dt
import re
import sys
from pathlib import Path

# Allow `python data/daily_update.py` from repo root
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from webscrapper import (  # noqa: E402
    append_monthly_for_dat_files,
    download_all_files,
    get_dat_file_urls,
    get_day_urls,
    log_debug,
    log_error,
)

# Defaults relative to this file so cwd does not matter (e.g. `python data/daily_update.py` from repo root).
_DEFAULT_DOWNLOAD_DIR = _SCRIPT_DIR / "downloads"
_DEFAULT_MONTHLY_DIR = _SCRIPT_DIR / "monthly_csv"
_DEFAULT_LOG_CSV = _SCRIPT_DIR / "air_quality_data.csv"


DAY_PREFIX_RE = re.compile(r"^airnow/\d{4}/(\d{8})/$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Download only new AirNow hourly .dat files (not already in downloads/)."
    )
    p.add_argument(
        "--lookback-days",
        type=int,
        default=14,
        help="Only scan S3 day folders with date >= (UTC today - N days). Default: 14.",
    )
    p.add_argument(
        "--year",
        type=int,
        default=None,
        help="Bucket prefix year, e.g. 2026. Default: current UTC year.",
    )
    p.add_argument(
        "--download-dir",
        type=Path,
        default=_DEFAULT_DOWNLOAD_DIR,
        help="Directory for .dat files (default: downloads/ next to this script).",
    )
    p.add_argument(
        "--monthly-dir",
        type=Path,
        default=_DEFAULT_MONTHLY_DIR,
        help="Directory for monthly CSV output.",
    )
    p.add_argument(
        "--log-csv",
        type=Path,
        default=_DEFAULT_LOG_CSV,
        help="Append download log rows to this CSV.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List missing URLs only; do not download or update CSVs.",
    )
    return p.parse_args()


def _utc_today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def filter_day_prefixes_by_lookback(
    prefixes: list[str], lookback_days: int
) -> list[str]:
    if lookback_days <= 0:
        return prefixes

    cutoff = _utc_today() - dt.timedelta(days=lookback_days)
    out: list[str] = []
    for prefix in prefixes:
        m = DAY_PREFIX_RE.match(prefix)
        if not m:
            continue
        day = dt.datetime.strptime(m.group(1), "%Y%m%d").date()
        if day >= cutoff:
            out.append(prefix)
    return sorted(out)


def local_dat_filenames(download_dir: Path) -> set[str]:
    download_dir = Path(download_dir)
    if not download_dir.is_dir():
        return set()
    return {p.name for p in download_dir.glob("*.dat")}


def collect_remote_urls(day_prefixes: list[str]) -> list[str]:
    urls: list[str] = []
    for prefix in day_prefixes:
        try:
            urls.extend(get_dat_file_urls(prefix))
        except Exception as e:
            log_error(f"Failed listing keys for {prefix}: {e}")
    return sorted(set(urls))


def urls_for_missing_files(remote_urls: list[str], local_names: set[str]) -> list[str]:
    missing: list[str] = []
    for url in remote_urls:
        name = url.rstrip("/").split("/")[-1]
        if name not in local_names:
            missing.append(url)
    return missing


def append_download_log(records: list[dict], log_path: Path) -> None:
    if not records:
        return
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["file_url", "file_name", "file_path", "status", "timestamp"]
    write_header = not log_path.exists() or log_path.stat().st_size == 0
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        w.writerows(records)


async def run() -> int:
    args = parse_args()
    year = args.year
    if year is None:
        year = dt.datetime.now(dt.timezone.utc).year

    prefix_root = f"airnow/{year}/"
    log_debug(f"Daily update: prefix={prefix_root} lookback_days={args.lookback_days}")

    try:
        all_day_prefixes = get_day_urls(prefix_root)
    except Exception as e:
        log_error(f"Failed to list day prefixes: {e}")
        return 1

    day_prefixes = filter_day_prefixes_by_lookback(
        all_day_prefixes, args.lookback_days
    )
    log_debug(
        f"Day prefixes after lookback: {len(day_prefixes)} (of {len(all_day_prefixes)} total)"
    )

    download_dir = Path(args.download_dir)
    local_names = local_dat_filenames(download_dir)
    log_debug(f"Local .dat files: {len(local_names)}")

    remote_urls = collect_remote_urls(day_prefixes)
    log_debug(f"Remote .dat URLs in window: {len(remote_urls)}")

    missing_urls = urls_for_missing_files(remote_urls, local_names)
    log_debug(f"Missing (to download): {len(missing_urls)}")

    if args.dry_run:
        for u in missing_urls[:50]:
            print(u)
        if len(missing_urls) > 50:
            print(f"... and {len(missing_urls) - 50} more")
        return 0

    if not missing_urls:
        log_debug("Nothing to download.")
        return 0

    download_records = await download_all_files(missing_urls, download_dir)
    append_download_log(download_records, args.log_csv)
    log_debug(f"Appended download log to {args.log_csv}")

    new_files = [
        Path(r["file_path"])
        for r in download_records
        if r.get("status") == "downloaded" and r.get("file_path")
    ]
    if new_files:
        append_monthly_for_dat_files(new_files, Path(args.monthly_dir))
    else:
        log_debug("No newly downloaded files to append to monthly CSVs.")

    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
