"""Count pooled weather observations by station, season, variable, and interval."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


DEFAULT_INPUT = Path("data/processed/weather/weather.parquet")
DEFAULT_OUTPUT = Path("data/processed/weather/frequency.csv")

OUTPUT_COLUMNS = [
    "station",
    "season",
    "variable",
    "bin_label",
    "bin_lower_value",
    "measurement_count",
    "total_measurements_in_period",
    "frequency_pct",
]

SEASONS = np.array(["Winter", "Spring", "Summer", "Fall"])
F_UPPER_BOUNDS = np.array([5, 10, 15, 20, 25], dtype=float)
FG_UPPER_BOUNDS = np.array([5, 10, 15, 20, 25, 30, 35], dtype=float)
TEMPERATURE_UPPER_BOUNDS = np.array([-5, -3, -1, 1, 3, 5], dtype=float)
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


def station_ids(parquet_file: pq.ParquetFile) -> np.ndarray:
    values: set[int] = set()
    for row_group in range(parquet_file.metadata.num_row_groups):
        column = parquet_file.read_row_group(row_group, columns=["station"]).column(0)
        values.update(map(int, np.unique(column.to_numpy())))
    return np.array(sorted(values), dtype=np.int32)


def accumulate(
    parquet_file: pq.ParquetFile, stations: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    group_count = len(stations) * len(SEASONS)
    wind_totals = np.zeros(group_count, dtype=np.int64)
    f_counts = np.zeros((group_count, len(F_UPPER_BOUNDS) + 1), dtype=np.int64)
    fg_counts = np.zeros((group_count, len(FG_UPPER_BOUNDS) + 1), dtype=np.int64)
    temperature_totals = np.zeros(group_count, dtype=np.int64)
    temperature_counts = np.zeros(
        (group_count, len(TEMPERATURE_UPPER_BOUNDS) + 1), dtype=np.int64
    )
    input_rows = 0

    for row_group in range(parquet_file.metadata.num_row_groups):
        table = parquet_file.read_row_group(
            row_group, columns=["station", "time", "f", "fg", "t"]
        )
        station = table.column("station").to_numpy()
        timestamp = table.column("time").to_numpy().astype("datetime64[us]")
        f = table.column("f").to_numpy()
        fg = table.column("fg").to_numpy()
        temperature = table.column("t").to_numpy()

        month = timestamp.astype("datetime64[M]").astype(np.int64) % 12 + 1
        station_index = np.searchsorted(stations, station)
        group = station_index * len(SEASONS) + season_index(month)
        wind_totals += np.bincount(group, minlength=group_count)

        f_bin = np.searchsorted(F_UPPER_BOUNDS, f, side="right")
        f_counts += np.bincount(
            group * f_counts.shape[1] + f_bin,
            minlength=f_counts.size,
        ).reshape(f_counts.shape)

        fg_bin = np.searchsorted(FG_UPPER_BOUNDS, fg, side="right")
        fg_counts += np.bincount(
            group * fg_counts.shape[1] + fg_bin,
            minlength=fg_counts.size,
        ).reshape(fg_counts.shape)

        temperature_valid = np.isfinite(temperature)
        temperature_group = group[temperature_valid]
        temperature_totals += np.bincount(temperature_group, minlength=group_count)
        temperature_bin = np.searchsorted(
            TEMPERATURE_UPPER_BOUNDS,
            temperature[temperature_valid],
            side="right",
        )
        temperature_counts += np.bincount(
            temperature_group * temperature_counts.shape[1] + temperature_bin,
            minlength=temperature_counts.size,
        ).reshape(temperature_counts.shape)

        input_rows += len(table)
        if (row_group + 1) % 25 == 0 or row_group + 1 == parquet_file.metadata.num_row_groups:
            print(
                f"row_groups={row_group + 1}/{parquet_file.metadata.num_row_groups} "
                f"rows={input_rows:,}",
                flush=True,
            )

    return wind_totals, f_counts, fg_counts, temperature_totals, temperature_counts, input_rows


def make_table(
    stations: np.ndarray,
    wind_totals: np.ndarray,
    f_counts: np.ndarray,
    fg_counts: np.ndarray,
    temperature_totals: np.ndarray,
    temperature_counts: np.ndarray,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    definitions = (
        ("f", f_counts, labels(F_UPPER_BOUNDS), np.concatenate(([0.0], F_UPPER_BOUNDS)), wind_totals),
        ("fg", fg_counts, labels(FG_UPPER_BOUNDS), np.concatenate(([0.0], FG_UPPER_BOUNDS)), wind_totals),
        ("temperature", temperature_counts, TEMPERATURE_LABELS, np.concatenate(([-np.inf], TEMPERATURE_UPPER_BOUNDS)), temperature_totals),
    )
    for variable, counts, bin_labels, lower_bounds, totals in definitions:
        group, bin_index = np.nonzero(counts)
        frame = pd.DataFrame(
            {
                "station": stations[group // len(SEASONS)],
                "season": SEASONS[group % len(SEASONS)],
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
        ["station", "season", "variable", "bin_lower_value"]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    started = time.perf_counter()
    parquet_file = pq.ParquetFile(args.input)
    stations = station_ids(parquet_file)
    wind_totals, f_counts, fg_counts, temperature_totals, temperature_counts, input_rows = accumulate(
        parquet_file, stations
    )
    frequency = make_table(
        stations,
        wind_totals,
        f_counts,
        fg_counts,
        temperature_totals,
        temperature_counts,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frequency[OUTPUT_COLUMNS].to_csv(args.output, index=False)
    print(
        f"wrote={args.output} rows={len(frequency):,}; "
        f"input_rows={input_rows:,}; elapsed={time.perf_counter() - started:.1f}s"
    )


if __name__ == "__main__":
    main()
