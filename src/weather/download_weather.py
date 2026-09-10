"""Download and combine the official supplied ten-minute weather files.

The Icelandic Met Office supplied one station catalogue and three observation
file types at ``brunnur.vedur.is/pub/arason/asgeir``. ``f_`` contains recent
IMO observations, ``fj_`` older complementary IMO observations, and ``fv_``
Road Administration station observations. All observation files use the
canonical columns ``timi,stod,t,f,fg``.

All three file types are retained: ``f_`` (recent IMO), ``fj_`` (older
complementary IMO), and ``fv_`` (Road Administration). The raw text files form
a resumable local cache. They are combined without quality filtering into one
Parquet file with the canonical columns expected by :mod:`src.weather.clean`.
The separate cleaning step applies the documented quality rules and records
every exclusion category.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from io import StringIO
from pathlib import Path
import re
from typing import Iterable
from urllib.parse import urljoin

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests


BASE_URL = "http://brunnur.vedur.is/pub/arason/asgeir/"
DEFAULT_RAW_DIR = Path("data/raw/weather/supplied")
DEFAULT_OUTPUT = Path("data/raw/weather/weather_10min_raw.parquet")
DEFAULT_AUDIT = Path("data/raw/weather/weather_10min_raw_audit.csv")
DEFAULT_STATIONS_OUTPUT = Path("data/raw/weather/stations.csv")
FIRST_YEAR = 2007
LAST_YEAR = 2025
MIN_TEMPERATURE_C = -30.0
MAX_TEMPERATURE_C = 30.0
EXPECTED_COLUMNS = ["timi", "stod", "t", "f", "fg"]


def parse_index(html: str) -> pd.DataFrame:
    """Return observation filenames and station IDs from the directory page."""
    records = []
    pattern = re.compile(
        r'href="((?:f|fj|fv)_([0-9]+)\.txt)".*?\s([0-9.]+)([KMG])\s*$',
        re.MULTILINE,
    )
    multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3}
    for filename, station, size, unit in pattern.findall(html):
        records.append(
            {
                "source_file": filename,
                "station": int(station),
                "listed_bytes": int(float(size) * multipliers[unit]),
            }
        )
    if not records:
        raise ValueError("No observation files were found in the official index")
    return pd.DataFrame(records).sort_values(["station", "source_file"])


def select_files(index: pd.DataFrame, station_ids: set[int]) -> pd.DataFrame:
    """Select every supplied file; f and fj for one station are complementary."""
    selected = index[index["station"].isin(station_ids)].copy()
    unavailable = station_ids - set(selected["station"])
    if unavailable:
        raise ValueError(
            "Official extract has no file for target stations: "
            + ", ".join(map(str, sorted(unavailable)))
        )
    return selected.sort_values(["station", "source_file"])


def fetch_text(session: requests.Session, url: str, timeout: int) -> str:
    response = session.get(url, timeout=(20, timeout))
    response.raise_for_status()
    return response.content.decode("latin1")


def download_file(
    base_url: str, filename: str, destination: Path, timeout: int
) -> tuple[Path, str]:
    """Download atomically, or reuse a complete cached file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 20:
        with destination.open("rb") as handle:
            columns = handle.readline().decode("ascii", errors="replace").strip().split(",")
            if columns == EXPECTED_COLUMNS:
                digest = hashlib.sha256()
                handle.seek(0)
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
                return destination, digest.hexdigest()
    temporary = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    with requests.get(
        urljoin(base_url, filename), stream=True, timeout=(20, timeout)
    ) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for block in response.iter_content(1024 * 1024):
                if block:
                    handle.write(block)
                    digest.update(block)
    with temporary.open("rb") as handle:
        columns = handle.readline().decode("ascii", errors="replace").strip().split(",")
    if columns != EXPECTED_COLUMNS:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"Unexpected columns in {filename}: {columns}")
    temporary.replace(destination)
    return destination, digest.hexdigest()


def raw_chunks(path: Path, chunksize: int = 500_000) -> Iterable[tuple[pd.DataFrame, dict]]:
    """Yield typed study-period rows while preserving values for ``clean.py``."""
    for chunk in pd.read_csv(
        path, usecols=EXPECTED_COLUMNS, chunksize=chunksize, low_memory=False
    ):
        raw_rows = len(chunk)
        chunk["time"] = pd.to_datetime(
            chunk.pop("timi"), format="%Y-%m-%d %H:%M:%S", errors="coerce"
        )
        chunk["station"] = pd.to_numeric(chunk.pop("stod"), errors="coerce")
        for column in ("t", "f", "fg"):
            chunk[column] = pd.to_numeric(chunk[column], errors="coerce")
        valid_time = chunk["time"].notna()
        valid_station = chunk["station"].notna()
        in_period = valid_time & chunk["time"].dt.year.between(FIRST_YEAR, LAST_YEAR)
        keep = valid_station & in_period
        raw = chunk.loc[keep, ["station", "time", "f", "fg", "t"]].copy()
        raw["station"] = raw["station"].astype("int32")
        raw[["f", "fg", "t"]] = raw[["f", "fg", "t"]].astype("float32")
        yield raw, {
            "source_rows": raw_rows,
            "invalid_timestamp_rows": int((~valid_time).sum()),
            "missing_f_rows": int(chunk["f"].isna().sum()),
            "missing_fg_rows": int(chunk["fg"].isna().sum()),
            "missing_t_rows": int(chunk["t"].isna().sum()),
            "outside_study_period_rows": int((valid_time & ~in_period).sum()),
            "study_period_rows": int(keep.sum()),
            "first_time": chunk.loc[valid_time, "time"].min(),
            "last_time": chunk.loc[valid_time, "time"].max(),
        }


def build_raw_parquet(
    files: pd.DataFrame, raw_dir: Path, output: Path, audit_path: Path,
    digests: dict[str, str],
) -> None:
    """Combine source files into an unfiltered raw parquet and source audit."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    schema = pa.schema(
        [
            ("station", pa.int32()),
            ("time", pa.timestamp("us")),
            ("f", pa.float32()),
            ("fg", pa.float32()),
            ("t", pa.float32()),
        ]
    )
    writer = pq.ParquetWriter(temporary, schema, compression="zstd")
    audit_rows = []
    try:
        for row in files.itertuples(index=False):
            totals: dict[str, object] = {
                "source_file": row.source_file,
                "station": int(row.station),
                "listed_bytes": int(row.listed_bytes),
                "downloaded_bytes": (raw_dir / row.source_file).stat().st_size,
                "sha256": digests[row.source_file],
                "source_rows": 0,
                "invalid_timestamp_rows": 0,
                "missing_f_rows": 0,
                "missing_fg_rows": 0,
                "missing_t_rows": 0,
                "outside_study_period_rows": 0,
                "study_period_rows": 0,
                "first_time": pd.NaT,
                "last_time": pd.NaT,
            }
            for raw, counts in raw_chunks(raw_dir / row.source_file):
                for column in (
                    "source_rows", "invalid_timestamp_rows",
                    "missing_f_rows", "missing_fg_rows", "missing_t_rows",
                    "outside_study_period_rows", "study_period_rows",
                ):
                    totals[column] = int(totals[column]) + int(counts[column])
                if pd.notna(counts["first_time"]):
                    totals["first_time"] = (
                        counts["first_time"] if pd.isna(totals["first_time"])
                        else min(totals["first_time"], counts["first_time"])
                    )
                    totals["last_time"] = (
                        counts["last_time"] if pd.isna(totals["last_time"])
                        else max(totals["last_time"], counts["last_time"])
                    )
                if len(raw):
                    table = pa.Table.from_pandas(raw, schema=schema, preserve_index=False)
                    writer.write_table(table, row_group_size=1_000_000)
            audit_rows.append(totals)
            print(
                f"processed={row.source_file} rows={int(totals['study_period_rows']):,}",
                flush=True,
            )
    finally:
        writer.close()
    temporary.replace(output)
    pd.DataFrame(audit_rows).to_csv(audit_path, index=False)
    print(f"wrote={output} rows={pq.ParquetFile(output).metadata.num_rows:,}")
    print(f"wrote={audit_path} files={len(audit_rows)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument(
        "--stations-output", type=Path, default=DEFAULT_STATIONS_OUTPUT
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    with requests.Session() as session:
        index_text = fetch_text(session, args.base_url, args.timeout_seconds)
        station_text = fetch_text(
            session, urljoin(args.base_url, "stod.txt"), args.timeout_seconds
        )
    (args.raw_dir / "index.html").write_text(index_text, encoding="latin1")
    (args.raw_dir / "stations.csv").write_text(station_text, encoding="latin1")
    stations = pd.read_csv(StringIO(station_text))
    stations = stations.rename(
        columns={
            "stod": "station", "skst": "abbr", "breidd": "lat",
            "lengd": "lon", "h_stod": "ele", "nafn": "name",
        }
    )
    stations["lon"] = -pd.to_numeric(stations["lon"], errors="coerce").abs()
    stations = stations[["station", "name", "abbr", "lat", "lon", "ele"]]
    args.stations_output.parent.mkdir(parents=True, exist_ok=True)
    stations.to_csv(args.stations_output, index=False)
    index = parse_index(index_text)
    files = index
    print(
        f"stations={files['station'].nunique()} files={len(files)} "
        f"listed_gib={files['listed_bytes'].sum() / 1024**3:.2f}",
        flush=True,
    )
    digests: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                download_file,
                args.base_url,
                row.source_file,
                args.raw_dir / row.source_file,
                args.timeout_seconds,
            ): row.source_file
            for row in files.itertuples(index=False)
        }
        for number, future in enumerate(as_completed(futures), start=1):
            path, digest = future.result()
            digests[path.name] = digest
            print(f"downloaded={number}/{len(futures)} file={path.name}", flush=True)
    build_raw_parquet(files, args.raw_dir, args.output, args.audit, digests)


if __name__ == "__main__":
    main()
