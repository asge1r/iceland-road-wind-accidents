"""Clean 10-minute wind data using the fixed thesis quality rules.

No wind value is clipped or imputed. The processed file contains only retained
records; the two CSV audit files explain every excluded record.
"""

from __future__ import annotations

import argparse
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


RAW_COLUMNS = ("station", "time", "f", "fg", "t")
WIND_COLUMNS = RAW_COLUMNS[:-1]
DEFAULT_INPUT = Path("data/raw/weather/weather_10min_raw.parquet")
DEFAULT_OUTPUT = Path("data/processed/weather/weather.parquet")
DEFAULT_SUMMARY = Path("archive/generated_diagnostics/weather_cleaning_by_year.csv")
DEFAULT_COVERAGE = Path("archive/generated_diagnostics/weather_station_year_coverage.csv")
DEFAULT_FROZEN = Path("archive/generated_diagnostics/weather_frozen_zero_intervals.csv")

MAX_F = 45.0
MAX_FG = 65.0
GUST_TOLERANCE = 0.5
MIN_TEMPERATURE = -60.0
MAX_TEMPERATURE = 50.0
TEN_MINUTES = np.timedelta64(10, "m")
FROZEN_DURATION = np.timedelta64(2, "h")


def arrays(file: pq.ParquetFile, row_group: int, columns: tuple[str, ...]) -> tuple[np.ndarray, ...]:
    batch = file.read_row_group(row_group, columns=columns).to_batches()[0]
    return tuple(batch.column(name).to_numpy(zero_copy_only=False) for name in columns)


def years(timestamp: np.ndarray) -> np.ndarray:
    return timestamp.astype("datetime64[Y]").astype(np.int64) + 1970


def output_path(path: Path, year: int | None) -> Path:
    return path if year is None else path.with_name(f"{path.stem}_{year}{path.suffix}")


def add_run(run: dict | None, frozen: dict[int, list[tuple[np.datetime64, np.datetime64]]]) -> None:
    if run is not None and run["end"] - run["start"] >= FROZEN_DURATION:
        frozen[int(run["station"])].append((run["start"], run["end"]))


def scan_frozen_runs(file: pq.ParquetFile) -> dict[int, list[tuple[np.datetime64, np.datetime64]]]:
    """Find only continuous runs with f=fg=0 lasting at least two hours."""
    frozen: dict[int, list[tuple[np.datetime64, np.datetime64]]] = defaultdict(list)
    pending: dict | None = None
    for row_group in range(file.metadata.num_row_groups):
        station, timestamp, f, fg = arrays(file, row_group, WIND_COLUMNS)
        zero = np.isfinite(f) & np.isfinite(fg) & (f == 0) & (fg == 0)
        if not zero.any():
            add_run(pending, frozen)
            pending = None
            continue
        continues = np.zeros(len(zero), dtype=bool)
        continues[1:] = (
            zero[:-1] & zero[1:] & (station[:-1] == station[1:])
            & (timestamp[1:] - timestamp[:-1] == TEN_MINUTES)
        )
        starts = np.flatnonzero(zero & ~continues)
        ends = np.flatnonzero(zero & ~np.r_[continues[1:], False])
        for first, last in zip(starts, ends, strict=True):
            run = {"station": int(station[first]), "start": timestamp[first], "end": timestamp[last]}
            joins = (
                pending is not None and first == 0
                and pending["station"] == run["station"]
                and run["start"] - pending["end"] == TEN_MINUTES
            )
            if joins:
                run["start"] = pending["start"]
                pending = None
            elif pending is not None:
                add_run(pending, frozen)
                pending = None
            if last == len(zero) - 1:
                pending = run
            else:
                add_run(run, frozen)
    add_run(pending, frozen)
    return frozen


def frozen_mask(station: np.ndarray, timestamp: np.ndarray, frozen: dict) -> np.ndarray:
    result = np.zeros(len(station), dtype=bool)
    for station_id in np.unique(station):
        rows = np.flatnonzero(station == station_id)
        for start, end in frozen.get(int(station_id), []):
            result[rows] |= (timestamp[rows] >= start) & (timestamp[rows] <= end)
    return result


def wind_capable_station_years(file: pq.ParquetFile) -> set[tuple[int, int]]:
    """Return station-years with at least one finite f or fg value."""
    result: set[tuple[int, int]] = set()
    for row_group in range(file.metadata.num_row_groups):
        station, timestamp, f, fg = arrays(file, row_group, WIND_COLUMNS)
        present = np.isfinite(f) | np.isfinite(fg)
        result.update((int(s), int(y)) for s, y in zip(station[present], years(timestamp)[present]))
    return result


def classify(
    station: np.ndarray, timestamp: np.ndarray, f: np.ndarray, fg: np.ndarray,
    temperature: np.ndarray, frozen: np.ndarray, capable: set[tuple[int, int]],
) -> tuple[pa.Table, dict[str, np.ndarray]]:
    """Classify records in a fixed order so exclusion categories do not overlap."""
    year = years(timestamp)
    wind_capable = np.fromiter(((int(s), int(y)) in capable for s, y in zip(station, year)), bool, len(station))
    f_present, fg_present = np.isfinite(f), np.isfinite(fg)
    no_wind_station_year = ~wind_capable
    missing_wind = wind_capable & (~f_present | ~fg_present)
    negative = wind_capable & ~missing_wind & ((f < 0) | (fg < 0))
    upper_threshold = wind_capable & ~missing_wind & ~negative & ((f >= MAX_F) | (fg >= MAX_FG))
    inconsistent_zero_gust = wind_capable & ~missing_wind & ~negative & ~upper_threshold & (fg == 0) & (f > 0)
    gust_below_mean = wind_capable & ~missing_wind & ~negative & ~upper_threshold & ~inconsistent_zero_gust & (fg + GUST_TOLERANCE < f)
    frozen_zero = wind_capable & ~missing_wind & ~negative & ~upper_threshold & ~inconsistent_zero_gust & ~gust_below_mean & frozen
    excluded = no_wind_station_year | missing_wind | negative | upper_threshold | inconsistent_zero_gust | gust_below_mean | frozen_zero
    retained = ~excluded
    valid_t = np.isfinite(temperature) & (temperature >= MIN_TEMPERATURE) & (temperature <= MAX_TEMPERATURE)
    clean = pa.table({
        "station": pa.array(station[retained], type=pa.int32()),
        "time": pa.array(timestamp[retained], type=pa.timestamp("us")),
        "f": pa.array(f[retained], type=pa.float32()),
        "fg": pa.array(fg[retained], type=pa.float32()),
        "t": pa.array(temperature[retained], mask=~valid_t[retained], type=pa.float32()),
    })
    return clean, {
        "no_wind_station_year": no_wind_station_year,
        "missing_wind": missing_wind,
        "negative": negative,
        "upper_threshold": upper_threshold,
        "inconsistent_zero_gust": inconsistent_zero_gust,
        "gust_below_mean": gust_below_mean,
        "frozen_zero": frozen_zero,
        "retained_wind_rows": retained,
        "negative_f": f_present & (f < 0),
        "negative_fg": fg_present & (fg < 0),
        "f_at_or_above_45": f_present & (f >= MAX_F),
        "fg_at_or_above_65": fg_present & (fg >= MAX_FG),
        "fg_zero_rows": fg_present & (fg == 0),
        "fg_zero_with_positive_f": f_present & fg_present & (fg == 0) & (f > 0),
    }


def add_counts(totals: dict, station: np.ndarray, year: np.ndarray, masks: dict[str, np.ndarray]) -> None:
    for station_id, value in set(zip(station.tolist(), year.tolist(), strict=True)):
        rows = (station == station_id) & (year == value)
        out = totals[(int(station_id), int(value))]
        out["raw_rows"] += int(rows.sum())
        for name, mask in masks.items():
            out[name] += int((rows & mask).sum())


def write_audits(summary_path: Path, coverage_path: Path, totals: dict) -> None:
    records = [{"station": station, "year": year, **values} for (station, year), values in totals.items()]
    coverage = pd.DataFrame(records).fillna(0)
    columns = [
        "raw_rows", "no_wind_station_year", "missing_wind", "negative",
        "upper_threshold", "inconsistent_zero_gust", "gust_below_mean",
        "frozen_zero", "retained_wind_rows", "negative_f", "negative_fg",
        "f_at_or_above_45", "fg_at_or_above_65", "fg_zero_rows",
        "fg_zero_with_positive_f",
    ]
    coverage[columns] = coverage[columns].astype(int)
    coverage["excluded_rows"] = coverage[[
        "no_wind_station_year", "missing_wind", "negative", "upper_threshold",
        "inconsistent_zero_gust", "gust_below_mean", "frozen_zero",
    ]].sum(axis=1)
    coverage["retained_pct_of_raw"] = 100 * coverage["retained_wind_rows"] / coverage["raw_rows"]
    coverage.sort_values(["year", "station"]).to_csv(coverage_path, index=False)
    annual = coverage.groupby("year", as_index=False)[columns + ["excluded_rows"]].sum()
    annual["clean_wind_rows"] = annual["retained_wind_rows"]
    annual["dropped_any_wind_rule"] = annual["excluded_rows"]
    annual["clean_wind_pct"] = 100 * annual["clean_wind_rows"] / annual["raw_rows"]
    annual["input_rows"] = annual["raw_rows"]
    annual["excluded_categories_sum_to_raw"] = annual["excluded_rows"] + annual["retained_wind_rows"] == annual["raw_rows"]
    total = annual.drop(columns="year").sum(numeric_only=True).to_dict()
    total["year"] = "total"
    total["clean_wind_pct"] = 100 * total["clean_wind_rows"] / total["input_rows"]
    total["excluded_categories_sum_to_raw"] = total["excluded_rows"] + total["retained_wind_rows"] == total["raw_rows"]
    pd.concat([annual, pd.DataFrame([total])], ignore_index=True).to_csv(summary_path, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean 10-minute wind data in streaming batches.")
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("-s", "--summary", type=Path)
    parser.add_argument("--coverage", type=Path)
    parser.add_argument("--frozen-intervals", type=Path)
    parser.add_argument("-y", "--year", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or output_path(DEFAULT_OUTPUT, args.year)
    summary = args.summary or output_path(DEFAULT_SUMMARY, args.year)
    coverage = args.coverage or output_path(DEFAULT_COVERAGE, args.year)
    frozen_path = args.frozen_intervals or output_path(DEFAULT_FROZEN, args.year)
    for path in (output, summary, coverage, frozen_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    source = pq.ParquetFile(args.input)
    frozen = scan_frozen_runs(source)
    capable = wind_capable_station_years(source)
    pd.DataFrame([
        {"station": station, "start": start, "end": end, "elapsed_minutes": int((end - start) / np.timedelta64(1, "m"))}
        for station, runs in frozen.items() for start, end in runs
    ]).to_csv(frozen_path, index=False)

    totals: dict = defaultdict(lambda: defaultdict(int))
    writer: pq.ParquetWriter | None = None
    input_rows = output_rows = 0
    started = time.time()
    try:
        for row_group in range(source.metadata.num_row_groups):
            station, timestamp, f, fg, temperature = arrays(source, row_group, RAW_COLUMNS)
            year = years(timestamp)
            selected = np.ones(len(timestamp), dtype=bool) if args.year is None else year == args.year
            if not selected.any():
                continue
            station, timestamp, f, fg, temperature, year = (
                value[selected] for value in (station, timestamp, f, fg, temperature, year)
            )
            clean, masks = classify(station, timestamp, f, fg, temperature, frozen_mask(station, timestamp, frozen), capable)
            add_counts(totals, station, year, masks)
            input_rows += len(timestamp)
            output_rows += len(clean)
            if writer is None:
                writer = pq.ParquetWriter(temporary, clean.schema, compression="zstd", compression_level=6, use_dictionary=["station", "f", "fg", "t"])
            if len(clean):
                writer.write_table(clean, row_group_size=1_000_000)
            if (row_group + 1) % 25 == 0 or row_group + 1 == source.metadata.num_row_groups:
                print(f"row_groups={row_group + 1}/{source.metadata.num_row_groups} input_rows={input_rows:,} output_rows={output_rows:,} elapsed={time.time() - started:.1f}s", flush=True)
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        raise ValueError(f"No weather observations found for year {args.year}.")
    temporary.replace(output)
    write_audits(summary, coverage, totals)
    print(f"wrote={output} rows={output_rows:,} bytes={output.stat().st_size:,}")
    print(f"wrote={summary}")
    print(f"wrote={coverage}")


if __name__ == "__main__":
    main()
