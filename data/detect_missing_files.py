import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path


FILENAME_PATTERN = re.compile(r"^(?:HourlyData|HourlyAQObs)_(\d{8})(\d{2})\.dat$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect missing hourly .dat files by date from file names."
    )
    parser.add_argument(
        "--dir",
        default="downloads",
        help="Directory containing downloaded .dat files (default: downloads)",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Optional start date in YYYYMMDD format",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Optional end date in YYYYMMDD format",
    )
    return parser.parse_args()


def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y%m%d")


def daterange(start_date: datetime, end_date: datetime):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def collect_hours_by_date(download_dir: Path) -> dict[str, set[int]]:
    hours_by_date: dict[str, set[int]] = {}

    for file in download_dir.glob("*.dat"):
        match = FILENAME_PATTERN.match(file.name)
        if not match:
            continue

        date_part, hour_part = match.groups()
        hour = int(hour_part)
        hours_by_date.setdefault(date_part, set()).add(hour)

    return hours_by_date


def main() -> None:
    args = parse_args()
    download_dir = Path(args.dir)

    if not download_dir.exists():
        print(f"Directory not found: {download_dir}")
        return

    hours_by_date = collect_hours_by_date(download_dir)
    if not hours_by_date:
        print("No matching .dat files found.")
        return

    detected_dates = sorted(hours_by_date.keys())
    default_start = parse_date(detected_dates[0])
    default_end = parse_date(detected_dates[-1])

    start_date = parse_date(args.start_date) if args.start_date else default_start
    end_date = parse_date(args.end_date) if args.end_date else default_end

    if end_date < start_date:
        print("Invalid range: end date is before start date.")
        return

    total_missing_files = 0
    missing_date_count = 0
    partial_date_count = 0

    print(f"Checking range: {start_date.strftime('%Y%m%d')} -> {end_date.strftime('%Y%m%d')}")
    print(f"Source directory: {download_dir.resolve()}")
    print("-" * 60)

    for day in daterange(start_date, end_date):
        day_str = day.strftime("%Y%m%d")
        found_hours = hours_by_date.get(day_str, set())
        missing_hours = [h for h in range(24) if h not in found_hours]

        if len(found_hours) == 0:
            missing_date_count += 1
            total_missing_files += 24
            print(f"{day_str}: MISSING DAY (24/24 files missing)")
        elif missing_hours:
            partial_date_count += 1
            total_missing_files += len(missing_hours)
            hours_text = ", ".join(f"{h:02d}" for h in missing_hours)
            print(
                f"{day_str}: PARTIAL ({len(found_hours)}/24 present) | Missing hours: {hours_text}"
            )

    print("-" * 60)
    print(f"Dates with no files: {missing_date_count}")
    print(f"Dates with partial files: {partial_date_count}")
    print(f"Total missing hourly files: {total_missing_files}")


if __name__ == "__main__":
    main()
