"""Calculate seasonal wind frequencies by station using the final thesis bins."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


DEFAULT_INPUT = Path("data/processed/weather/weather.parquet")
DEFAULT_STATIONS = Path("data/raw/weather/stations.csv")
DEFAULT_OUTPUT = Path("data/processed/weather/frequency.csv")

OUTPUT_COLUMNS = [
    "station", "year", "season", "variable", "bin_label", "bin_lower_value",
    "measurement_count", "total_measurements_in_period",
]
DEFAULT_WIDE = Path("archive/generated_diagnostics/wind_frequency_readable.csv")
DEFAULT_NOTES = Path(
    "archive/generated_diagnostics/wind_frequency_notes.txt"
)

FIRST_YEAR = 2007
LAST_YEAR = 2025
SEASONS = np.array(["Winter", "Spring", "Summer", "Fall"])
F_UPPER_BOUNDS = np.array([5, 10, 15, 20, 25], dtype=float)
# The annual-traffic preparation retains this internal label to distinguish its
# five-metre mean-wind rows from a legacy three-metre column. Its public
# output is always described as mean wind speed, `f`.
F_FIVE_MS_UPPER_BOUNDS = F_UPPER_BOUNDS
FG_UPPER_BOUNDS = np.array([5, 10, 15, 20, 25, 30, 35], dtype=float)
GUST_FACTOR_MIN_MEAN_WIND = 3.0
GUST_FACTOR_UPPER_BOUNDS = np.array([1.2, 1.4, 1.6, 1.8, 2.0], dtype=float)
TEMPERATURE_THRESHOLDS = np.array([-9, -6, -3, 0, 3, 6, 9, 12, 15, 18], dtype=float)
TEMPERATURE_LABELS = [
    "<-9", "-9--6", "-6--3", "-3-0", "0-3", "3-6",
    "6-9", "9-12", "12-15", "15-18", ">=18",
]


def season_index(month: np.ndarray) -> np.ndarray:
    result = np.empty(len(month), dtype=np.int8)
    result[np.isin(month, [12, 1, 2, 3])] = 0
    result[np.isin(month, [4, 5])] = 1
    result[np.isin(month, [6, 7, 8, 9])] = 2
    result[np.isin(month, [10, 11])] = 3
    return result


def labels(upper_bounds: np.ndarray) -> list[str]:
    lower = np.concatenate(([0.0], upper_bounds[:-1]))
    return [f"{lo:g}-{hi:g}" for lo, hi in zip(lower, upper_bounds, strict=True)] + [
        f">={upper_bounds[-1]:g}"
    ]


def station_ids(parquet_file: pq.ParquetFile, row_groups: int) -> np.ndarray:
    values: set[int] = set()
    for row_group in range(row_groups):
        column = parquet_file.read_row_group(row_group, columns=["station"]).column(0)
        values.update(map(int, np.unique(column.to_numpy())))
    return np.array(sorted(values), dtype=np.int32)


def accumulate(
    parquet_file: pq.ParquetFile, row_groups: int, stations: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    years_count = LAST_YEAR - FIRST_YEAR + 1
    group_count = len(stations) * years_count * len(SEASONS)
    totals = np.zeros(group_count, dtype=np.int64)
    f_counts = np.zeros((group_count, len(F_UPPER_BOUNDS) + 1), dtype=np.int64)
    fg_counts = np.zeros((group_count, len(FG_UPPER_BOUNDS) + 1), dtype=np.int64)
    gust_factor_totals = np.zeros(group_count, dtype=np.int64)
    gust_factor_counts = np.zeros(
        (group_count, len(GUST_FACTOR_UPPER_BOUNDS) + 1), dtype=np.int64
    )
    temperature_totals = np.zeros(group_count, dtype=np.int64)
    temperature_counts = np.zeros(
        (group_count, len(TEMPERATURE_THRESHOLDS) + 1), dtype=np.int64
    )
    input_rows = 0

    for row_group in range(row_groups):
        table = parquet_file.read_row_group(
            row_group, columns=["station", "time", "f", "fg", "t"]
        )
        station = table.column("station").to_numpy()
        timestamp = table.column("time").to_numpy().astype("datetime64[us]")
        f = table.column("f").to_numpy()
        fg = table.column("fg").to_numpy()
        temperature = table.column("t").to_numpy()

        month_value = timestamp.astype("datetime64[M]").astype(np.int64)
        year = timestamp.astype("datetime64[Y]").astype(np.int64) + 1970
        month = month_value % 12 + 1
        if year.min() < FIRST_YEAR or year.max() > LAST_YEAR:
            raise ValueError(f"Unexpected year range {year.min()}-{year.max()}")

        station_index = np.searchsorted(stations, station)
        group = (
            (station_index * years_count + (year - FIRST_YEAR)) * len(SEASONS)
            + season_index(month)
        )
        totals += np.bincount(group, minlength=group_count)
        f_bin = np.searchsorted(F_UPPER_BOUNDS, f, side="right")
        fg_bin = np.searchsorted(FG_UPPER_BOUNDS, fg, side="right")
        f_counts += np.bincount(
            group * f_counts.shape[1] + f_bin,
            minlength=f_counts.size,
        ).reshape(f_counts.shape)
        fg_counts += np.bincount(
            group * fg_counts.shape[1] + fg_bin,
            minlength=fg_counts.size,
        ).reshape(fg_counts.shape)
        factor_valid = f >= GUST_FACTOR_MIN_MEAN_WIND
        factor_group = group[factor_valid]
        factor = fg[factor_valid] / f[factor_valid]
        gust_factor_totals += np.bincount(factor_group, minlength=group_count)
        factor_bin = np.searchsorted(GUST_FACTOR_UPPER_BOUNDS, factor, side="right")
        gust_factor_counts += np.bincount(
            factor_group * gust_factor_counts.shape[1] + factor_bin,
            minlength=gust_factor_counts.size,
        ).reshape(gust_factor_counts.shape)
        temperature_valid = (
            np.isfinite(temperature)
            & (temperature >= -30.0)
            & (temperature <= 30.0)
        )
        temperature_group = group[temperature_valid]
        temperature_totals += np.bincount(
            temperature_group, minlength=group_count
        )
        temperature_bin = np.searchsorted(
            TEMPERATURE_THRESHOLDS, temperature[temperature_valid], side="right"
        )
        temperature_counts += np.bincount(
            temperature_group * temperature_counts.shape[1] + temperature_bin,
            minlength=temperature_counts.size,
        ).reshape(temperature_counts.shape)
        input_rows += len(table)
        if (row_group + 1) % 25 == 0 or row_group + 1 == row_groups:
            print(
                f"row_groups={row_group + 1}/{row_groups} rows={input_rows:,}",
                flush=True,
            )
    return (
        totals,
        f_counts,
        fg_counts,
        gust_factor_totals,
        gust_factor_counts,
        temperature_totals,
        temperature_counts,
        input_rows,
    )


def make_long_table(
    stations: np.ndarray,
    station_names: pd.DataFrame,
    totals: np.ndarray,
    f_counts: np.ndarray,
    fg_counts: np.ndarray,
    gust_factor_totals: np.ndarray,
    gust_factor_counts: np.ndarray,
    temperature_totals: np.ndarray,
    temperature_counts: np.ndarray,
) -> pd.DataFrame:
    years_count = LAST_YEAR - FIRST_YEAR + 1
    frames: list[pd.DataFrame] = []
    for variable, counts, bin_labels, lower_bounds, upper_bounds, variable_totals in (
        ("f", f_counts, labels(F_UPPER_BOUNDS), np.concatenate(([0.0], F_UPPER_BOUNDS)), np.concatenate((F_UPPER_BOUNDS, [np.inf])), totals),
        ("fg", fg_counts, labels(FG_UPPER_BOUNDS), np.concatenate(([0.0], FG_UPPER_BOUNDS)), np.concatenate((FG_UPPER_BOUNDS, [np.inf])), totals),
        ("gust_factor", gust_factor_counts, labels(GUST_FACTOR_UPPER_BOUNDS), np.concatenate(([0.0], GUST_FACTOR_UPPER_BOUNDS)), np.concatenate((GUST_FACTOR_UPPER_BOUNDS, [np.inf])), gust_factor_totals),
        ("temperature", temperature_counts, TEMPERATURE_LABELS, np.concatenate(([-np.inf], TEMPERATURE_THRESHOLDS)), np.concatenate((TEMPERATURE_THRESHOLDS, [np.inf])), temperature_totals),
    ):
        group, bin_index = np.nonzero(counts)
        station_index = group // (years_count * len(SEASONS))
        remainder = group % (years_count * len(SEASONS))
        year = FIRST_YEAR + remainder // len(SEASONS)
        season = SEASONS[remainder % len(SEASONS)]
        bin_labels = np.array(bin_labels)
        frame = pd.DataFrame(
            {
                "station": stations[station_index],
                "year": year,
                "season": season,
                "period": np.char.add(np.char.add(season.astype(str), " "), year.astype(str)),
                "variable": variable,
                "bin_label": bin_labels[bin_index],
                "bin_lower_value": lower_bounds[bin_index],
                "bin_upper_value": upper_bounds[bin_index],
                "measurement_count": counts[group, bin_index],
                "total_measurements_in_period": variable_totals[group],
            }
        )
        frame["frequency_pct"] = (
            100 * frame["measurement_count"] / frame["total_measurements_in_period"]
        )
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    result = result.merge(station_names, on="station", how="left", validate="many_to_one")
    return result[
        [
            "station",
            "name",
            "year",
            "season",
            "period",
            "variable",
            "bin_label",
            "bin_lower_value",
            "bin_upper_value",
            "measurement_count",
            "total_measurements_in_period",
            "frequency_pct",
        ]
    ].sort_values(["station", "year", "season", "variable", "bin_lower_value"])


def make_wide_table(long: pd.DataFrame) -> pd.DataFrame:
    wide_source = long.copy()
    wide_source["column"] = (
        wide_source["variable"]
        + "_"
        + wide_source["bin_label"].str.replace(">=", "ge_", regex=False).str.replace(
            "-", "_", regex=False
        )
        + "_pct"
    )
    index = ["station", "name", "year", "season", "period"]
    wide = wide_source.pivot(index=index, columns="column", values="frequency_pct")
    wide = wide.fillna(0).reset_index().rename_axis(columns=None)
    totals = (
        long.groupby(index, as_index=False)["total_measurements_in_period"]
        .first()
    )
    result = totals.merge(wide, on=index, how="left", validate="one_to_one")
    ordered_bins = [
        f"{variable}_{label.replace('>=', 'ge_').replace('-', '_')}_pct"
        for variable, bounds in (
            ("f", F_UPPER_BOUNDS),
            ("fg", FG_UPPER_BOUNDS),
            ("gust_factor", GUST_FACTOR_UPPER_BOUNDS),
            ("temperature", TEMPERATURE_THRESHOLDS),
        )
        for label in (TEMPERATURE_LABELS if variable == "temperature" else labels(bounds))
    ]
    for column in ordered_bins:
        if column not in result:
            result[column] = 0.0
    return result[[*index, "total_measurements_in_period", *ordered_bins]]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build seasonal f/fg frequency tables for each weather station."
    )
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-s", "--stations", type=Path, default=DEFAULT_STATIONS)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-w", "--wide", type=Path, default=DEFAULT_WIDE)
    parser.add_argument("-n", "--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("-m", "--max-row-groups", type=int)
    args = parser.parse_args()

    started = time.perf_counter()
    parquet_file = pq.ParquetFile(args.input)
    row_groups = parquet_file.metadata.num_row_groups
    if args.max_row_groups is not None:
        row_groups = min(row_groups, args.max_row_groups)
    stations = station_ids(parquet_file, row_groups)
    metadata = pd.read_csv(args.stations, usecols=["station", "name"]).drop_duplicates(
        "station"
    )
    (
        totals,
        f_counts,
        fg_counts,
        gust_factor_totals,
        gust_factor_counts,
        temperature_totals,
        temperature_counts,
        input_rows,
    ) = accumulate(parquet_file, row_groups, stations)
    long = make_long_table(
        stations, metadata, totals, f_counts, fg_counts,
        gust_factor_totals, gust_factor_counts, temperature_totals,
        temperature_counts,
    )
    wide = make_wide_table(long)

    for path in (args.output, args.wide, args.notes):
        path.parent.mkdir(parents=True, exist_ok=True)
    missing = set(OUTPUT_COLUMNS) - set(long.columns)
    if missing:
        raise ValueError(f"Frequency output is missing columns: {sorted(missing)}")
    long[OUTPUT_COLUMNS].to_csv(args.output, index=False)
    wide.to_csv(args.wide, index=False)
    elapsed = time.perf_counter() - started
    notes = f"""Wind frequency by station and season
====================================

Input: {args.input}
Scope: {'pilot' if args.max_row_groups else 'full cleaned weather file'}
Input rows aggregated: {input_rows:,}
Stations represented: {len(stations):,}
Station-season-year periods represented: {len(wide):,}

Seasons use the traffic-period-compatible calendar definition:
- Winter: December-March
- Spring: April-May
- Summer: June-September
- Fall: October-November

Bins are left-closed and right-open. For example, 2-4 means 2 <= value < 4.
The final bins are f >= 25 m/s, fg >= 35 m/s and gust factor >= 2.0.
Frequencies use all clean f/fg observations at the same station in that season
and calendar year.

The long Parquet table contains counts and percentages and is intended for analysis.
The wide CSV mirrors the example layout in todo.md and is intended for inspection.

Elapsed seconds: {elapsed:.1f}
"""
    args.notes.write_text(notes, encoding="utf-8")
    print(
        f"wrote={args.output} rows={len(long):,}; wide_rows={len(wide):,}; "
        f"elapsed={elapsed:.1f}s"
    )


if __name__ == "__main__":
    main()
