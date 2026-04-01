import asyncio
import datetime
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

import aiohttp
import pandas as pd
import requests


S3_LIST_URL = "https://s3-us-west-1.amazonaws.com/files.airnowtech.org"
PREFIX_ROOT = "airnow/2026/"
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_LOG_CSV = Path("air_quality_data.csv")
MONTHLY_OUTPUT_DIR = Path("monthly_csv")
DAT_FILENAME_MONTH = re.compile(
    r"^HourlyData_(\d{8})(\d{2})\.dat$", re.IGNORECASE
)

TARGET_DATES = set()


def log_debug(msg: str) -> None:
    print(f"{datetime.datetime.now().isoformat()} DEBUG: {msg}")


def log_error(msg: str) -> None:
    print(f"{datetime.datetime.now().isoformat()} ERROR: {msg}")


def _extract_s3_values(xml_text: str, tag_name: str) -> list[str]:
    try:
        root = ET.fromstring(xml_text)
        values = []
        for node in root.iter():
            if node.tag.endswith(tag_name) and node.text:
                values.append(node.text.strip())
        return values
    except ET.ParseError:
        return []


def _list_s3_prefixes(prefix_root: str) -> list[str]:
    prefixes: list[str] = []
    continuation_token = None
    while True:
        params = {"list-type": "2", "delimiter": "/", "prefix": prefix_root}
        if continuation_token:
            params["continuation-token"] = continuation_token

        response = requests.get(S3_LIST_URL, params=params, timeout=60)
        response.raise_for_status()
        xml_text = response.text
        prefixes.extend(_extract_s3_values(xml_text, "Prefix"))

        next_tokens = _extract_s3_values(xml_text, "NextContinuationToken")
        is_truncated = _extract_s3_values(xml_text, "IsTruncated")
        if not next_tokens or not is_truncated or is_truncated[0].lower() != "true":
            break
        continuation_token = next_tokens[0]

    return sorted(set(prefixes))


def _list_s3_keys(prefix_root: str) -> list[str]:
    keys: list[str] = []
    continuation_token = None
    while True:
        params = {"list-type": "2", "prefix": prefix_root}
        if continuation_token:
            params["continuation-token"] = continuation_token

        response = requests.get(S3_LIST_URL, params=params, timeout=60)
        response.raise_for_status()
        xml_text = response.text
        keys.extend(_extract_s3_values(xml_text, "Key"))

        next_tokens = _extract_s3_values(xml_text, "NextContinuationToken")
        is_truncated = _extract_s3_values(xml_text, "IsTruncated")
        if not next_tokens or not is_truncated or is_truncated[0].lower() != "true":
            break
        continuation_token = next_tokens[0]

    return sorted(set(keys))


def get_day_urls(prefix_root: str | None = None) -> list[str]:
    root = prefix_root if prefix_root is not None else PREFIX_ROOT
    day_pattern = re.compile(r"^airnow/\d{4}/(\d{8})/$")
    day_prefixes = _list_s3_prefixes(root)
    day_urls = []
    for prefix in day_prefixes:
        match = day_pattern.match(prefix)
        if not match:
            continue
        date_part = match.group(1)
        if TARGET_DATES and date_part not in TARGET_DATES:
            continue
        day_urls.append(prefix)

    unique_prefixes = sorted(set(day_urls))
    log_debug(f"Found {len(unique_prefixes)} day directory links")
    return unique_prefixes


def get_dat_file_urls(day_prefix: str) -> list[str]:
    dat_keys = []
    dat_name_pattern = re.compile(r"HourlyData_[^/\s]+\.dat$", re.IGNORECASE)
    for key in _list_s3_keys(day_prefix):
        if dat_name_pattern.search(key):
            dat_keys.append(key)

    unique_urls = sorted(
        {f"https://s3-us-west-1.amazonaws.com/files.airnowtech.org/{unquote(key)}" for key in dat_keys}
    )
    log_debug(f"Found {len(unique_urls)} .dat files on {day_prefix}")
    return unique_urls


async def download_file(session: aiohttp.ClientSession, file_url: str, download_dir: Path) -> dict | None:
    filename = file_url.split("/")[-1]
    file_path = download_dir / filename

    if file_path.exists():
        log_debug(f"Skipping existing file: {filename}")
        return {
            "file_url": file_url,
            "file_name": filename,
            "file_path": str(file_path),
            "status": "skipped_exists",
            "timestamp": datetime.datetime.now().isoformat(),
        }

    try:
        async with session.get(file_url, timeout=120) as response:
            if response.status != 200:
                log_error(f"Failed to download {filename}. Status: {response.status}")
                return None

            content = await response.read()
            file_path.write_bytes(content)
            log_debug(f"Downloaded: {filename}")
            return {
                "file_url": file_url,
                "file_name": filename,
                "file_path": str(file_path),
                "status": "downloaded",
                "timestamp": datetime.datetime.now().isoformat(),
            }
    except Exception as e:
        log_error(f"Error downloading {filename}: {e}")
        return None


async def download_all_files(file_urls: list[str], download_dir: Path) -> list[dict]:
    download_dir.mkdir(parents=True, exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=300)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [download_file(session, file_url, download_dir) for file_url in file_urls]
        results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


def _read_dat_file(file: Path, columns: list[str]) -> pd.DataFrame | None:
    try:
        return pd.read_csv(
            file,
            sep="|",
            header=None,
            names=columns,
            encoding="utf-8",
            on_bad_lines="skip",
        )
    except Exception:
        try:
            return pd.read_csv(
                file,
                sep="|",
                header=None,
                names=columns,
                encoding="latin1",
                on_bad_lines="skip",
            )
        except Exception as e:
            log_error(f"Failed reading {file.name}. Skipping. Error: {e}")
            return None


def _month_key_from_filename(name: str) -> str | None:
    m = DAT_FILENAME_MONTH.match(name)
    if not m:
        return None
    # YYYYMMDD from filename -> YYYYMM
    return m.group(1)[:6]


def build_monthly_csvs_from_dats(download_dir: Path, output_dir: Path) -> None:
    columns = [
        "Date",
        "Hour",
        "Station ID",
        "Location",
        "Offset",
        "Pollutant",
        "Unit",
        "Measurement",
        "Network",
    ]

    dat_files = sorted(download_dir.glob("*.dat"))
    if not dat_files:
        log_debug("No .dat files found to build monthly CSVs.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("all_air_quality_data_*.csv"):
        old.unlink(missing_ok=True)

    months_written: set[str] = set()

    for file in dat_files:
        month_key = _month_key_from_filename(file.name)
        if not month_key:
            log_error(f"Could not parse month from filename: {file.name}")
            continue

        df = _read_dat_file(file, columns)
        if df is None or df.empty:
            continue

        df["source_file"] = file.name
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
        df = df.dropna(how="all")

        year = month_key[:4]
        month_num = month_key[4:6]
        month_path = output_dir / f"all_air_quality_data_{year}_{month_num}.csv"
        write_header = not month_path.exists() or month_path.stat().st_size == 0
        df.to_csv(month_path, mode="a", header=write_header, index=False)
        months_written.add(month_key)

    if months_written:
        log_debug(
            f"Monthly CSVs updated (append): {len(months_written)} month(s) in {output_dir}"
        )
    else:
        log_debug("No readable .dat files produced monthly CSV output.")


def append_monthly_for_dat_files(dat_files: list[Path], output_dir: Path) -> None:
    columns = [
        "Date",
        "Hour",
        "Station ID",
        "Location",
        "Offset",
        "Pollutant",
        "Unit",
        "Measurement",
        "Network",
    ]

    if not dat_files:
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    months_written: set[str] = set()

    for file in sorted(dat_files):
        if not file.exists():
            log_error(f"Missing file for monthly append: {file}")
            continue

        month_key = _month_key_from_filename(file.name)
        if not month_key:
            log_error(f"Could not parse month from filename: {file.name}")
            continue

        df = _read_dat_file(file, columns)
        if df is None or df.empty:
            continue

        df["source_file"] = file.name
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
        df = df.dropna(how="all")

        year = month_key[:4]
        month_num = month_key[4:6]
        month_path = output_dir / \
            f"all_air_quality_data_{year}_{month_num}.csv"
        write_header = not month_path.exists() or month_path.stat().st_size == 0
        df.to_csv(month_path, mode="a", header=write_header, index=False)
        months_written.add(month_key)

    if months_written:
        log_debug(
            f"Monthly CSVs appended for {len(months_written)} month(s) in {output_dir}"
        )


async def main() -> None:
    start_time = time.time()

    try:
        day_urls = get_day_urls()
    except Exception as e:
        log_error(f"Failed to list day URLs from {PREFIX_ROOT}: {e}")
        raise

    all_file_urls: list[str] = []
    for day_url in day_urls:
        try:
            all_file_urls.extend(get_dat_file_urls(day_url))
        except Exception as e:
            log_error(f"Failed to parse day page {day_url}: {e}")

    all_file_urls = sorted(set(all_file_urls))
    log_debug(f"Total unique .dat files to process: {len(all_file_urls)}")

    download_records = await download_all_files(all_file_urls, DOWNLOAD_DIR)
    if download_records:
        import csv

        with open(DOWNLOAD_LOG_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["file_url", "file_name", "file_path", "status", "timestamp"]
            )
            writer.writeheader()
            writer.writerows(download_records)
        log_debug(f"Download log saved as {DOWNLOAD_LOG_CSV}")
    else:
        log_debug("No files downloaded or skipped.")

    build_monthly_csvs_from_dats(DOWNLOAD_DIR, MONTHLY_OUTPUT_DIR)

    end_time = time.time()
    log_debug(f"Script finished in {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())