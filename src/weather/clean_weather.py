"""Clean 10-minute weather observations and report exclusions by year."""

from __future__ import annotations

import argparse
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


DEFAULT_INPUT = Path("data/raw/weather/weather_10min_raw.parquet")
DEFAULT_OUTPUT = Path("data/processed/weather/weather_10min_clean.parquet")
DEFAULT_SUMMARY = Path("archive/generated_diagnostics/weather_cleaning_by_year.csv")
DEFAULT_NOTES = Path("archive/generated_diagnostics/weather_cleaning_notes.txt")

MAX_MEAN_WIND_MS = 40.0
MAX_GUST_MS = 75.0
GUST_BELOW_MEAN_TOLERANCE_MS = 0.5
MIN_TEMPERATURE_C = -60.0
MAX_TEMPERATURE_C = 50.0
ZERO_RUN_MIN_ELAPSED = np.timedelta64(2, "h")
TEN_MINUTES = np.timedelta64(10, "m")


def empty_stats() -> dict[str, int]:
    return defaultdict(int)


def find_frozen_zero_intervals(
    parquet_file: pq.ParquetFile, row_groups: int
) -> pd.DataFrame:
    """Find continuous, all-zero wind/gust episodes longer than two hours.

    The raw file is ordered by station and then timestamp. A frozen sensor is
    conservatively defined as uninterrupted 10-minute records with both
    ``f == 0`` and ``fg == 0``. A run must have elapsed time strictly greater
    than two hours; ordinary calm weather and isolated zeroes are retained.
    """
    intervals: list[dict[str, object]] = []
    pending: dict[str, object] | None = None

    def finish(run: dict[str, object]) -> None:
        elapsed = run["end"] - run["start"]
        if elapsed > ZERO_RUN_MIN_ELAPSED:
            intervals.append(
                {
                    "station": int(run["station"]),
                    "start": run["start"],
                    "end": run["end"],
                    "zero_rows": int(run["zero_rows"]),
                    "elapsed_minutes": int(elapsed / np.timedelta64(1, "m")),
                }
            )

    for row_group in range(row_groups):
        batch = parquet_file.read_row_group(
            row_group, columns=["station", "time", "f", "fg"]
        ).to_batches()[0]
        station = batch.column(0).to_numpy(zero_copy_only=False)
        timestamp = batch.column(1).to_numpy(zero_copy_only=False)
        f = batch.column(2).to_numpy(zero_copy_only=False)
        fg = batch.column(3).to_numpy(zero_copy_only=False)
        zero = np.isfinite(f) & np.isfinite(fg) & (f == 0) & (fg == 0)
        if not zero.any():
            if pending is not None:
                finish(pending)
                pending = None
            continue

        continuous_previous = np.zeros(len(zero), dtype=bool)
        continuous_previous[1:] = (
            zero[:-1]
            & zero[1:]
            & (station[:-1] == station[1:])
            & ((timestamp[1:] - timestamp[:-1]) == TEN_MINUTES)
        )
        starts = np.flatnonzero(zero & ~continuous_previous)
        continuous_next = np.zeros(len(zero), dtype=bool)
        continuous_next[:-1] = continuous_previous[1:]
        ends = np.flatnonzero(zero & ~continuous_next)

        for start_index, end_index in zip(starts, ends, strict=True):
            run = {
                "station": int(station[start_index]),
                "start": timestamp[start_index],
                "end": timestamp[end_index],
                "zero_rows": int(end_index - start_index + 1),
            }
            joins_pending = (
                pending is not None
                and start_index == 0
                and pending["station"] == run["station"]
                and (run["start"] - pending["end"] == TEN_MINUTES)
            )
            if joins_pending:
                run["start"] = pending["start"]
                run["zero_rows"] += pending["zero_rows"]
                pending = None
            elif pending is not None:
                finish(pending)
                pending = None

            if end_index == len(zero) - 1:
                pending = run
            else:
                finish(run)

    if pending is not None:
        finish(pending)
    return pd.DataFrame(
        intervals,
        columns=["station", "start", "end", "zero_rows", "elapsed_minutes"],
    )


def frozen_zero_mask(
    station: np.ndarray, timestamp: np.ndarray, intervals: pd.DataFrame
) -> np.ndarray:
    """Return rows falling in a verified frozen all-zero interval."""
    result = np.zeros(len(station), dtype=bool)
    if intervals.empty:
        return result
    for station_id, indices in pd.Series(station).groupby(station, sort=False).groups.items():
        rows = intervals[intervals["station"].eq(int(station_id))]
        if rows.empty:
            continue
        starts = rows["start"].to_numpy(dtype="datetime64[us]")
        ends = rows["end"].to_numpy(dtype="datetime64[us]")
        times = timestamp[np.asarray(indices)]
        match = np.searchsorted(starts, times, side="right") - 1
        valid = match >= 0
        matched = np.zeros(len(times), dtype=bool)
        matched[valid] = times[valid] <= ends[match[valid]]
        result[np.asarray(indices)] = matched
    return result


def add_stats(
    stats: dict[int, dict[str, int]],
    years: np.ndarray,
    valid_f: np.ndarray,
    valid_fg: np.ndarray,
    valid_t: np.ndarray,
    f: np.ndarray,
    fg: np.ndarray,
    frozen_zero: np.ndarray,
    keep_wind: np.ndarray,
    keep_full: np.ndarray,
) -> None:
    """Accumulate both overlapping rule counts and a partition of all rows.

    The existing rule-specific counts are intentionally overlapping: for
    example, one record may have both a missing gust and an invalid mean wind.
    The ``excluded_*`` counts below are mutually exclusive and therefore sum
    exactly to ``input_rows``.  They make the annual audit interpretable.
    """
    missing_both = ~valid_f & ~valid_fg
    missing_f_only = ~valid_f & valid_fg
    missing_fg_only = valid_f & ~valid_fg
    invalid_f = valid_f & ((f < 0) | (f > MAX_MEAN_WIND_MS))
    invalid_fg = valid_fg & ((fg < 0) | (fg > MAX_GUST_MS))
    invalid_pair = (
        valid_f
        & valid_fg
        & ~invalid_f
        & ~invalid_fg
        & (fg + GUST_BELOW_MEAN_TOLERANCE_MS < f)
    )
    excluded_missing = missing_both | missing_f_only | missing_fg_only
    excluded_invalid_f = ~excluded_missing & invalid_f
    excluded_invalid_fg = ~excluded_missing & ~excluded_invalid_f & invalid_fg
    excluded_invalid_pair = (
        ~excluded_missing & ~excluded_invalid_f & ~excluded_invalid_fg & invalid_pair
    )
    excluded_frozen = (
        ~excluded_missing
        & ~excluded_invalid_f
        & ~excluded_invalid_fg
        & ~excluded_invalid_pair
        & frozen_zero
    )
    for year in np.unique(years):
        mask = years == year
        out = stats[int(year)]
        out["input_rows"] += int(mask.sum())
        out["missing_f"] += int((mask & ~valid_f).sum())
        out["f_outside_0_40"] += int(
            (mask & valid_f & ((f < 0) | (f > MAX_MEAN_WIND_MS))).sum()
        )
        out["f_above_40"] += int((mask & valid_f & (f > MAX_MEAN_WIND_MS)).sum())
        out["missing_fg"] += int((mask & ~valid_fg).sum())
        out["fg_outside_0_75"] += int(
            (mask & valid_fg & ((fg < 0) | (fg > MAX_GUST_MS))).sum()
        )
        out["fg_above_75"] += int((mask & valid_fg & (fg > MAX_GUST_MS)).sum())
        valid_pair_values = (
            mask
            & valid_f
            & valid_fg
            & (f >= 0)
            & (f <= MAX_MEAN_WIND_MS)
            & (fg >= 0)
            & (fg <= MAX_GUST_MS)
        )
        out["fg_below_f_beyond_tolerance"] += int(
            (valid_pair_values & (fg + GUST_BELOW_MEAN_TOLERANCE_MS < f)).sum()
        )
        out["frozen_zero_rows"] += int((mask & frozen_zero).sum())
        out["nail_rows"] += int(
            (mask & valid_f & valid_fg & ((f > MAX_MEAN_WIND_MS) | (fg > MAX_GUST_MS))).sum()
        )
        out["dropped_any_wind_rule"] += int((mask & ~keep_wind).sum())
        out["clean_wind_rows"] += int((mask & keep_wind).sum())
        out["clean_full_f_fg_t_rows"] += int((mask & keep_full).sum())
        out["clean_wind_rows_missing_t"] += int((mask & keep_wind & ~valid_t).sum())
        out["excluded_missing_both_f_fg"] += int((mask & missing_both).sum())
        out["excluded_missing_f_only"] += int((mask & missing_f_only).sum())
        out["excluded_missing_fg_only"] += int((mask & missing_fg_only).sum())
        out["excluded_invalid_f"] += int((mask & excluded_invalid_f).sum())
        out["excluded_invalid_fg"] += int((mask & excluded_invalid_fg).sum())
        out["excluded_fg_below_f"] += int((mask & excluded_invalid_pair).sum())
        out["excluded_frozen_zero"] += int((mask & excluded_frozen).sum())
        out["retained_clean_wind"] += int((mask & keep_wind).sum())


def clean_batch(
    batch: pa.RecordBatch,
    frozen_zero: np.ndarray,
) -> tuple[
    pa.Table,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    station = batch.column(0).to_numpy(zero_copy_only=False)
    timestamp = batch.column(1).to_numpy(zero_copy_only=False)
    f = batch.column(2).to_numpy(zero_copy_only=False)
    fg = batch.column(3).to_numpy(zero_copy_only=False)
    temperature = batch.column(4).to_numpy(zero_copy_only=False)

    valid_f = ~np.isnan(f)
    valid_fg = ~np.isnan(fg)
    valid_t = (
        ~np.isnan(temperature)
        & (temperature >= MIN_TEMPERATURE_C)
        & (temperature <= MAX_TEMPERATURE_C)
    )
    keep_wind = (
        valid_f
        & valid_fg
        & (f >= 0)
        & (f <= MAX_MEAN_WIND_MS)
        & (fg >= 0)
        & (fg <= MAX_GUST_MS)
        & (fg + GUST_BELOW_MEAN_TOLERANCE_MS >= f)
        & ~frozen_zero
    )
    keep_full = keep_wind & valid_t

    kept_t = temperature[keep_wind]
    kept_t_valid = valid_t[keep_wind]
    table = pa.table(
        {
            "station": pa.array(station[keep_wind], type=pa.int32()),
            "time": pa.array(timestamp[keep_wind], type=pa.timestamp("us")),
            "f": pa.array(f[keep_wind], type=pa.float32()),
            "fg": pa.array(fg[keep_wind], type=pa.float32()),
            "t": pa.array(kept_t, mask=~kept_t_valid, type=pa.float32()),
        }
    )
    return table, timestamp, valid_f, valid_fg, valid_t, f, fg, keep_wind, keep_full


def write_notes(
    path: Path,
    input_path: Path,
    output_path: Path,
    summary: pd.DataFrame,
    output_bytes: int,
    elapsed_seconds: float,
    max_row_groups: int | None,
    frozen_intervals: pd.DataFrame,
) -> None:
    totals = summary.select_dtypes(include="number").sum()
    input_rows = int(totals["input_rows"])
    wind_rows = int(totals["clean_wind_rows"])
    full_rows = int(totals["clean_full_f_fg_t_rows"])
    notes = f"""10-minute weather cleaning notes
================================

Input: {input_path}
Output: {output_path}
Scope: {'pilot, first ' + str(max_row_groups) + ' row groups' if max_row_groups else 'full file'}

Rules
-----
- Keep mean wind when 0 <= f <= {MAX_MEAN_WIND_MS:g} m/s.
- Keep gust when 0 <= fg <= {MAX_GUST_MS:g} m/s.
- Require fg + {GUST_BELOW_MEAN_TOLERANCE_MS:g} >= f.
- Exclude a run only when both f and fg are exactly zero at uninterrupted
  10-minute intervals for more than two hours.
- Keep temperature only when {MIN_TEMPERATURE_C:g} <= t <= {MAX_TEMPERATURE_C:g} deg. C.
- Output rows always have valid f and fg. Temperature is nullable so otherwise valid
  wind observations are retained for the wind-only analysis.

Interpretation of the upper limits
----------------------------------
The limits f <= 40 m/s and fg <= 75 m/s are the operational thesis quality rules
specified by the supervisor. Rows above either limit are reported as excluded; the
script does not claim that every naturally high observation is a measurement error.

Counts
------
- Input rows: {input_rows:,}
- Clean f/fg rows: {wind_rows:,} ({100 * wind_rows / input_rows:.3f}%)
- Clean f/fg/t rows: {full_rows:,} ({100 * full_rows / input_rows:.3f}%)
- Clean wind rows with missing/invalid t retained: {wind_rows - full_rows:,}
- Rows excluded by at least one wind rule: {int(totals['dropped_any_wind_rule']):,}
  ({100 * totals['dropped_any_wind_rule'] / input_rows:.4f}%)
- Unique high-value nail rows (f > 40 or fg > 75): {int(totals['nail_rows']):,}
  ({100 * totals['nail_rows'] / input_rows:.4f}%)
- Frozen all-zero intervals >2 h: {len(frozen_intervals):,}
- Rows excluded in frozen all-zero intervals: {int(totals['frozen_zero_rows']):,}
- Output size: {output_bytes:,} bytes
- Elapsed time: {elapsed_seconds:.1f} seconds

Exclusive exclusion categories
------------------------------
The annual CSV also contains ``excluded_*`` categories.  These are evaluated
in a fixed order (missing wind fields, invalid mean wind, invalid gust,
gust/mean inconsistency, frozen zero run) and form a partition with
``retained_clean_wind``.  Unlike the ordinary rule counts, they can be added
without double counting.

Deduplication
-------------
The input was already grouped to one row per station/time by the upstream dedup builder.
This script preserves that key and does not resolve upstream conflicting duplicates again.
"""
    path.write_text(notes, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean 10-minute wind data in streaming batches.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument(
        "--frozen-zero-intervals",
        type=Path,
        default=Path("archive/generated_diagnostics/weather_frozen_zero_intervals.csv"),
    )
    parser.add_argument("--max-row-groups", type=int)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.notes.parent.mkdir(parents=True, exist_ok=True)
    args.frozen_zero_intervals.parent.mkdir(parents=True, exist_ok=True)
    tmp_output = args.output.with_suffix(args.output.suffix + ".tmp")
    tmp_output.unlink(missing_ok=True)

    parquet_file = pq.ParquetFile(args.input)
    row_groups = parquet_file.metadata.num_row_groups
    if args.max_row_groups is not None:
        row_groups = min(row_groups, args.max_row_groups)

    frozen_intervals = find_frozen_zero_intervals(parquet_file, row_groups)
    frozen_intervals.to_csv(args.frozen_zero_intervals, index=False)

    stats: dict[int, dict[str, int]] = defaultdict(empty_stats)
    writer: pq.ParquetWriter | None = None
    started = time.time()
    input_rows = 0
    output_rows = 0

    try:
        for row_group in range(row_groups):
            batch = parquet_file.read_row_group(
                row_group, columns=["station", "time", "f", "fg", "t"]
            ).to_batches()[0]
            station_values = batch.column(0).to_numpy(zero_copy_only=False)
            timestamp_values = batch.column(1).to_numpy(zero_copy_only=False)
            frozen = frozen_zero_mask(station_values, timestamp_values, frozen_intervals)
            (
                clean,
                timestamp,
                valid_f,
                valid_fg,
                valid_t,
                f,
                fg,
                keep_wind,
                keep_full,
            ) = clean_batch(batch, frozen)

            years = timestamp.astype("datetime64[Y]").astype(np.int64) + 1970
            add_stats(
                stats, years, valid_f, valid_fg, valid_t, f, fg, frozen, keep_wind, keep_full
            )
            input_rows += len(timestamp)
            output_rows += len(clean)

            if writer is None:
                writer = pq.ParquetWriter(
                    tmp_output,
                    clean.schema,
                    compression="zstd",
                    compression_level=6,
                    # Wind and gust values repeat heavily on the 10-minute grid.
                    # Dictionary encoding therefore makes the cleaned file
                    # materially smaller without changing a single value.
                    use_dictionary=["station", "f", "fg", "t"],
                )
            if len(clean):
                writer.write_table(clean, row_group_size=1_000_000)

            if (row_group + 1) % 25 == 0 or row_group + 1 == row_groups:
                print(
                    f"row_groups={row_group + 1}/{row_groups} "
                    f"input_rows={input_rows:,} output_rows={output_rows:,} "
                    f"elapsed={time.time() - started:.1f}s",
                    flush=True,
                )
    finally:
        if writer is not None:
            writer.close()

    tmp_output.replace(args.output)
    summary = pd.DataFrame.from_dict(stats, orient="index").fillna(0).astype(int)
    summary.index.name = "year"
    summary = summary.reset_index().sort_values("year")
    summary["clean_wind_pct"] = 100 * summary["clean_wind_rows"] / summary["input_rows"]
    summary["clean_full_f_fg_t_pct"] = 100 * summary["clean_full_f_fg_t_rows"] / summary["input_rows"]
    summary.to_csv(args.summary, index=False)
    write_notes(
        args.notes,
        args.input,
        args.output,
        summary,
        args.output.stat().st_size,
        time.time() - started,
        args.max_row_groups,
        frozen_intervals,
    )
    print(f"wrote={args.output} rows={output_rows:,} bytes={args.output.stat().st_size:,}")


if __name__ == "__main__":
    main()
