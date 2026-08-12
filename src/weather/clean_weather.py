"""Clean 10-minute wind observations and report exclusion percentages."""

from __future__ import annotations

import argparse
import csv
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


RAW_COLUMNS = ("station", "time", "f", "fg", "t")
WIND_COLUMNS = RAW_COLUMNS[:-1]
DEFAULT_INPUT = Path("data/raw/weather/weather_10min_raw.parquet")
DEFAULT_OUTPUT = Path("data/processed/weather/weather_10min_clean.parquet")
DEFAULT_SUMMARY = Path("archive/generated_diagnostics/weather_cleaning_by_year.csv")

MAX_F = 45.0
MAX_FG = 65.0
GUST_TOLERANCE = 0.5
MIN_TEMPERATURE = -60.0
MAX_TEMPERATURE = 50.0
TEN_MINUTES = np.timedelta64(10, "m")
FROZEN_DURATION = np.timedelta64(2, "h")
ONE_DAY = np.timedelta64(1, "D")

SUMMARY_COLUMNS = {
    "nails": "nails",
    "frozen": "frozen",
    "nan": "NaN",
    "missing": "missing",
    "dropped": "total dropped",
}
DIAGNOSTICS = (
    "f_below_minus_1",
    "f_from_minus_1_to_0",
    "fg_below_minus_1",
    "fg_from_minus_1_to_0",
    "gust_below_mean",
    "f_only_nails",
    "fg_only_nails",
    "both_nails",
)

Interval = tuple[np.datetime64, np.datetime64]
Stats = dict[int, dict[str, int]]


def arrays(file: pq.ParquetFile, row_group: int, columns: tuple[str, ...]) -> tuple[np.ndarray, ...]:
    batch = file.read_row_group(row_group, columns=columns).to_batches()[0]
    return tuple(batch.column(name).to_numpy(zero_copy_only=False) for name in columns)


def output_path(path: Path, year: int | None) -> Path:
    return path if year is None else path.with_name(f"{path.stem}_{year}{path.suffix}")


def days_between(start: object, end: object) -> Interval:
    """Return the complete calendar days containing a station's first and last record."""
    start, end = np.datetime64(start), np.datetime64(end)
    return start.astype("datetime64[D]"), end.astype("datetime64[D]") + ONE_DAY - TEN_MINUTES


def correct_wind(
    f: np.ndarray, fg: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Convert wind sentinels to NaN and small negative values to zero."""
    f_below_minus_1 = np.isfinite(f) & (f < -1)
    f_from_minus_1_to_0 = np.isfinite(f) & (f > -1) & (f < 0)
    fg_below_minus_1 = np.isfinite(fg) & (fg < -1)
    fg_from_minus_1_to_0 = np.isfinite(fg) & (fg > -1) & (fg < 0)
    f, fg = f.copy(), fg.copy()
    f[f_below_minus_1] = np.nan
    fg[fg_below_minus_1] = np.nan
    f[f_from_minus_1_to_0] = 0
    fg[fg_from_minus_1_to_0] = 0
    return f, fg, {
        "f_below_minus_1": f_below_minus_1,
        "f_from_minus_1_to_0": f_from_minus_1_to_0,
        "fg_below_minus_1": fg_below_minus_1,
        "fg_from_minus_1_to_0": fg_from_minus_1_to_0,
    }


def add_frozen(
    run: dict[str, object] | None, frozen: dict[int, list[Interval]]
) -> None:
    if run is None or run["end"] - run["start"] < FROZEN_DURATION:
        return
    frozen[int(run["station"])].append((run["start"], run["end"]))


def scan_metadata(file: pq.ParquetFile) -> tuple[dict[int, list[Interval]], dict[int, Interval]]:
    """Find frozen-zero runs and station operating dates in one streaming pass."""
    frozen: dict[int, list[Interval]] = defaultdict(list)
    operation: dict[int, list[np.datetime64]] = {}
    pending: dict[str, object] | None = None

    for row_group in range(file.metadata.num_row_groups):
        station, timestamp, f, fg = arrays(file, row_group, WIND_COLUMNS)
        f, fg, _ = correct_wind(f, fg)
        recorded = np.isfinite(f) & np.isfinite(fg)
        for station_id in np.unique(station[recorded]):
            records = timestamp[recorded & (station == station_id)]
            start, end = records.min(), records.max()
            bounds = operation.setdefault(int(station_id), [start, end])
            bounds[0], bounds[1] = min(bounds[0], start), max(bounds[1], end)

        zeros = recorded & (f == 0) & (fg == 0)
        if not zeros.any():
            add_frozen(pending, frozen)
            pending = None
            continue

        continues = np.zeros(len(zeros), dtype=bool)
        continues[1:] = (
            zeros[:-1]
            & zeros[1:]
            & (station[:-1] == station[1:])
            & (timestamp[1:] - timestamp[:-1] == TEN_MINUTES)
        )
        starts = np.flatnonzero(zeros & ~continues)
        ends = np.flatnonzero(zeros & ~np.r_[continues[1:], False])
        for first, last in zip(starts, ends, strict=True):
            run = {
                "station": int(station[first]),
                "start": timestamp[first],
                "end": timestamp[last],
            }
            joins_pending = (
                pending is not None
                and first == 0
                and pending["station"] == run["station"]
                and run["start"] - pending["end"] == TEN_MINUTES
            )
            if joins_pending:
                run["start"] = pending["start"]
            else:
                add_frozen(pending, frozen)
            pending = run if last == len(zeros) - 1 else None
            if pending is None:
                add_frozen(run, frozen)

    add_frozen(pending, frozen)
    return frozen, {station: days_between(*bounds) for station, bounds in operation.items()}


def interval_mask(
    station: np.ndarray, timestamp: np.ndarray, intervals: dict[int, list[Interval]]
) -> np.ndarray:
    """Mark rows inside any interval assigned to their station."""
    result = np.zeros(len(station), dtype=bool)
    for station_id in np.unique(station):
        rows = np.flatnonzero(station == station_id)
        for start, end in intervals.get(int(station_id), []):
            result[rows] |= (timestamp[rows] >= start) & (timestamp[rows] <= end)
    return result


def operation_mask(
    station: np.ndarray, timestamp: np.ndarray, operation: dict[int, Interval]
) -> np.ndarray:
    return interval_mask(station, timestamp, {key: [value] for key, value in operation.items()})


def possible_slots(operation: dict[int, Interval], year: int | None) -> dict[int, int]:
    """Count every possible 10-minute slot across station operating dates."""
    totals: dict[int, int] = defaultdict(int)
    for start, end in operation.values():
        first_year = start.astype("datetime64[Y]").astype(int) + 1970
        last_year = end.astype("datetime64[Y]").astype(int) + 1970
        for value in range(first_year, last_year + 1):
            if year is not None and value != year:
                continue
            year_start = np.datetime64(f"{value}-01-01")
            year_end = np.datetime64(f"{value + 1}-01-01") - TEN_MINUTES
            totals[value] += int((min(end, year_end) - max(start, year_start)) / TEN_MINUTES) + 1
    return dict(totals)


def classify(
    station: np.ndarray,
    timestamp: np.ndarray,
    f: np.ndarray,
    fg: np.ndarray,
    temperature: np.ndarray,
    frozen: np.ndarray,
    corrections: dict[str, np.ndarray],
) -> tuple[pa.Table, dict[str, np.ndarray]]:
    """Create clean rows and mutually exclusive exclusion categories."""
    f_present, fg_present = np.isfinite(f), np.isfinite(fg)
    nan = ~f_present | ~fg_present
    negative = (f_present & (f < 0)) | (fg_present & (fg < 0))
    gust_below_mean = f_present & fg_present & (fg + GUST_TOLERANCE < f)
    missing = negative | gust_below_mean
    f_nail, fg_nail = f_present & (f > MAX_F), fg_present & (fg > MAX_FG)
    nails = (f_nail | fg_nail) & ~missing
    f_only_nails = f_nail & ~fg_nail & ~missing
    fg_only_nails = fg_nail & ~f_nail & ~missing
    both_nails = f_nail & fg_nail & ~missing
    dropped = nan | missing | f_nail | fg_nail | frozen
    keep = ~dropped
    valid_temperature = np.isfinite(temperature) & (temperature >= MIN_TEMPERATURE) & (temperature <= MAX_TEMPERATURE)
    clean = pa.table(
        {
            "station": pa.array(station[keep], type=pa.int32()),
            "time": pa.array(timestamp[keep], type=pa.timestamp("us")),
            "f": pa.array(f[keep], type=pa.float32()),
            "fg": pa.array(fg[keep], type=pa.float32()),
            "t": pa.array(temperature[keep], mask=~valid_temperature[keep], type=pa.float32()),
        }
    )
    return clean, {
        "nails": nails,
        "frozen": frozen,
        "nan": nan,
        "missing": missing,
        "dropped": dropped,
        **corrections,
        "gust_below_mean": gust_below_mean,
        "f_only_nails": f_only_nails,
        "fg_only_nails": fg_only_nails,
        "both_nails": both_nails,
    }


def add_stats(stats: Stats, timestamp: np.ndarray, operating: np.ndarray, masks: dict[str, np.ndarray]) -> None:
    years = timestamp.astype("datetime64[Y]").astype(int) + 1970
    for year in np.unique(years):
        eligible = (years == year) & operating
        values = stats.setdefault(int(year), defaultdict(int))
        values["observed"] += int(eligible.sum())
        for name, mask in masks.items():
            values[name] += int((eligible & mask).sum())


def write_summary(path: Path, stats: Stats, slots: dict[int, int]) -> None:
    """Write the compact, percentage-only cleaning summary."""
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["year", *SUMMARY_COLUMNS.values()])
        writer.writeheader()
        totals: dict[str, int] = defaultdict(int)
        for year in sorted(slots):
            values = stats.get(year, {})
            unrecorded = slots[year] - values.get("observed", 0)
            if unrecorded < 0:
                raise ValueError("Observed more rows than the station-operation grid allows.")
            values = {
                **values,
                "missing": values.get("missing", 0) + unrecorded,
                "dropped": values.get("dropped", 0) + unrecorded,
            }
            for name in SUMMARY_COLUMNS:
                totals[name] += values.get(name, 0)
            writer.writerow(
                {
                    "year": year,
                    **{
                        label: f"{100 * values.get(name, 0) / slots[year]:.3f}%"
                        for name, label in SUMMARY_COLUMNS.items()
                    },
                }
            )
        total_slots = sum(slots.values())
        writer.writerow(
            {
                "year": "total",
                **{
                    label: f"{100 * totals[name] / total_slots:.3f}%"
                    for name, label in SUMMARY_COLUMNS.items()
                },
            }
        )


def print_diagnostics(stats: Stats, slots: dict[int, int]) -> None:
    totals = {
        name: sum(values.get(name, 0) for values in stats.values())
        for name in DIAGNOSTICS
    }
    denominator = sum(slots.values())
    percentage = lambda count: 100 * count / denominator if denominator else 0
    print("Wind diagnostics:")
    print(f"  f < -1 converted to NaN: {totals['f_below_minus_1']:,} ({percentage(totals['f_below_minus_1']):.3f}%)")
    print(f"  -1 < f < 0 converted to zero: {totals['f_from_minus_1_to_0']:,} ({percentage(totals['f_from_minus_1_to_0']):.3f}%)")
    print(f"  fg < -1 converted to NaN: {totals['fg_below_minus_1']:,} ({percentage(totals['fg_below_minus_1']):.3f}%)")
    print(f"  -1 < fg < 0 converted to zero: {totals['fg_from_minus_1_to_0']:,} ({percentage(totals['fg_from_minus_1_to_0']):.3f}%)")
    print(f"  f-only nails: {totals['f_only_nails']:,}")
    print(f"  fg-only nails: {totals['fg_only_nails']:,}")
    print(f"  Both-threshold nails: {totals['both_nails']:,}")
    print(f"  Any nail: {sum(totals[name] for name in ('f_only_nails', 'fg_only_nails', 'both_nails')):,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean 10-minute wind data in streaming batches.")
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("-s", "--summary", type=Path)
    parser.add_argument("-y", "--year", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or output_path(DEFAULT_OUTPUT, args.year)
    summary = args.summary or output_path(DEFAULT_SUMMARY, args.year)
    for path in (output, summary):
        path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)

    source = pq.ParquetFile(args.input)
    frozen, operation = scan_metadata(source)
    slots = possible_slots(operation, args.year)
    stats: Stats = {}
    writer: pq.ParquetWriter | None = None
    input_rows = output_rows = 0
    started = time.time()
    try:
        for row_group in range(source.metadata.num_row_groups):
            station, timestamp, f, fg, temperature = arrays(source, row_group, RAW_COLUMNS)
            selected = np.ones(len(timestamp), dtype=bool) if args.year is None else timestamp.astype("datetime64[Y]").astype(int) + 1970 == args.year
            if not selected.any():
                continue
            station, timestamp, f, fg, temperature = (value[selected] for value in (station, timestamp, f, fg, temperature))
            f, fg, corrections = correct_wind(f, fg)
            clean, masks = classify(station, timestamp, f, fg, temperature, interval_mask(station, timestamp, frozen), corrections)
            add_stats(stats, timestamp, operation_mask(station, timestamp, operation), masks)
            input_rows, output_rows = input_rows + len(timestamp), output_rows + len(clean)
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
    write_summary(summary, stats, slots)
    print_diagnostics(stats, slots)
    print(f"wrote={output} rows={output_rows:,} bytes={output.stat().st_size:,}")


if __name__ == "__main__":
    main()
