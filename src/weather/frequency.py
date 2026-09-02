"""Count pooled and year-specific weather observations by station and season."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

DEFAULT_INPUT = Path("data/processed/weather/weather.parquet")
DEFAULT_OUTPUT = Path("data/processed/weather/frequency.csv")
DEFAULT_TRAFFIC_OUTPUT = Path("data/processed/weather/traffic_frequency.csv")
FIRST_YEAR = 2007
LAST_YEAR = 2025
SEASONS = np.array(["Winter", "Spring", "Summer", "Fall"])
F_UPPER_BOUNDS = np.array([5, 10, 15, 20, 25], dtype=float)
F_FIVE_MS_UPPER_BOUNDS = F_UPPER_BOUNDS
FG_UPPER_BOUNDS = np.array([5, 10, 15, 20, 25, 30, 35], dtype=float)
TEMPERATURE_UPPER_BOUNDS = np.array([-5, -3, -1, 1, 3, 5], dtype=float)
TEMPERATURE_THRESHOLDS = TEMPERATURE_UPPER_BOUNDS
TEMPERATURE_LABELS = ["<-5", "-5--3", "-3--1", "-1-1", "1-3", "3-5", ">=5"]


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
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    years_count = LAST_YEAR - FIRST_YEAR + 1
    group_count = len(stations) * years_count * len(SEASONS)
    wind_totals = np.zeros(group_count, dtype=np.int64)
    f_counts = np.zeros((group_count, len(F_UPPER_BOUNDS) + 1), dtype=np.int64)
    fg_counts = np.zeros((group_count, len(FG_UPPER_BOUNDS) + 1), dtype=np.int64)
    temperature_totals = np.zeros(group_count, dtype=np.int64)
    temperature_counts = np.zeros(
        (group_count, len(TEMPERATURE_UPPER_BOUNDS) + 1), dtype=np.int64
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
        year = timestamp.astype("datetime64[Y]").astype(np.int64) + 1970
        month = timestamp.astype("datetime64[M]").astype(np.int64) % 12 + 1
        if year.min() < FIRST_YEAR or year.max() > LAST_YEAR:
            raise ValueError(f"Unexpected year range {year.min()}-{year.max()}")
        station_index = np.searchsorted(stations, station)
        group = (
            (station_index * years_count + year - FIRST_YEAR) * len(SEASONS)
            + season_index(month)
        )
        wind_totals += np.bincount(group, minlength=group_count)
        f_bin = np.searchsorted(F_UPPER_BOUNDS, f, side="right")
        f_counts += np.bincount(
            group * f_counts.shape[1] + f_bin, minlength=f_counts.size
        ).reshape(f_counts.shape)
        fg_bin = np.searchsorted(FG_UPPER_BOUNDS, fg, side="right")
        fg_counts += np.bincount(
            group * fg_counts.shape[1] + fg_bin, minlength=fg_counts.size
        ).reshape(fg_counts.shape)
        valid = np.isfinite(temperature)
        temp_group = group[valid]
        temperature_totals += np.bincount(temp_group, minlength=group_count)
        temp_bin = np.searchsorted(
            TEMPERATURE_UPPER_BOUNDS, temperature[valid], side="right"
        )
        temperature_counts += np.bincount(
            temp_group * temperature_counts.shape[1] + temp_bin,
            minlength=temperature_counts.size,
        ).reshape(temperature_counts.shape)
        input_rows += len(table)
        if (row_group + 1) % 25 == 0 or row_group + 1 == row_groups:
            print(
                f"row_groups={row_group + 1}/{row_groups} rows={input_rows:,}",
                flush=True,
            )
    return (
        wind_totals, f_counts, fg_counts, temperature_totals,
        temperature_counts, input_rows,
    )


def make_yearly_table(
    stations: np.ndarray,
    wind_totals: np.ndarray,
    f_counts: np.ndarray,
    fg_counts: np.ndarray,
    temperature_totals: np.ndarray,
    temperature_counts: np.ndarray,
) -> pd.DataFrame:
    years_count = LAST_YEAR - FIRST_YEAR + 1
    frames = []
    definitions = (
        (
            "f", f_counts, labels(F_UPPER_BOUNDS),
            np.concatenate(([0.0], F_UPPER_BOUNDS)), wind_totals,
        ),
        (
            "fg", fg_counts, labels(FG_UPPER_BOUNDS),
            np.concatenate(([0.0], FG_UPPER_BOUNDS)), wind_totals,
        ),
        (
            "temperature", temperature_counts, TEMPERATURE_LABELS,
            np.concatenate(([-np.inf], TEMPERATURE_UPPER_BOUNDS)),
            temperature_totals,
        ),
    )
    for variable, counts, bin_labels, lower_bounds, totals in definitions:
        group, bin_index = np.nonzero(counts)
        station_index = group // (years_count * len(SEASONS))
        remainder = group % (years_count * len(SEASONS))
        frame = pd.DataFrame(
            {
                "station": stations[station_index],
                "year": FIRST_YEAR + remainder // len(SEASONS),
                "season": SEASONS[remainder % len(SEASONS)],
                "variable": variable,
                "bin_label": np.asarray(bin_labels)[bin_index],
                "bin_lower_value": lower_bounds[bin_index],
                "measurement_count": counts[group, bin_index],
                "total_measurements_in_period": totals[group],
            }
        )
        frame["frequency_pct"] = (
            100 * frame["measurement_count"] / frame["total_measurements_in_period"]
        )
        frames.append(frame)
    return pd.concat(frames, ignore_index=True).sort_values(
        ["station", "year", "season", "variable", "bin_lower_value"]
    )


def make_pooled_table(yearly: pd.DataFrame) -> pd.DataFrame:
    pooled = yearly.groupby(
        ["station", "season", "variable", "bin_label"],
        as_index=False,
        observed=True,
    ).agg(
        bin_lower_value=("bin_lower_value", "first"),
        measurement_count=("measurement_count", "sum"),
    )
    totals = yearly.groupby(
        ["station", "year", "season", "variable"], as_index=False, observed=True
    )["total_measurements_in_period"].first()
    totals = totals.groupby(
        ["station", "season", "variable"], as_index=False, observed=True
    )["total_measurements_in_period"].sum()
    pooled = pooled.merge(
        totals, on=["station", "season", "variable"],
        how="left", validate="many_to_one",
    )
    pooled["frequency_pct"] = (
        100 * pooled["measurement_count"] / pooled["total_measurements_in_period"]
    )
    return pooled.sort_values(["station", "season", "variable", "bin_lower_value"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "-t", "--traffic-output", type=Path, default=DEFAULT_TRAFFIC_OUTPUT
    )
    parser.add_argument("-m", "--max-row-groups", type=int)
    args = parser.parse_args()
    started = time.perf_counter()
    parquet_file = pq.ParquetFile(args.input)
    row_groups = parquet_file.metadata.num_row_groups
    if args.max_row_groups is not None:
        row_groups = min(row_groups, args.max_row_groups)
    stations = station_ids(parquet_file, row_groups)
    arrays = accumulate(parquet_file, row_groups, stations)
    yearly = make_yearly_table(stations, *arrays[:-1])
    pooled = make_pooled_table(yearly)
    for path in [args.output, args.traffic_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    pooled.to_csv(args.output, index=False)
    traffic = yearly[yearly["variable"].eq("f")]
    traffic.to_csv(args.traffic_output, index=False)
    print(
        f"wrote={args.output} rows={len(pooled):,}; "
        f"traffic_rows={len(traffic):,}; input_rows={arrays[-1]:,}; "
        f"elapsed={time.perf_counter() - started:.1f}s"
    )


if __name__ == "__main__":
    main()
