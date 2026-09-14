"""Pool daytime weather by station and calendar month across 2007–2025.

Each valid ten-minute observation has equal weight; years are pooled, not
averaged separately. Missing values have separate denominators per variable.
The four existing seasonal frequency files are not modified.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.weather.eligibility import valid_temperature
from src.weather.frequency import (
    DEFAULT_INPUT, FIRST_YEAR, LAST_YEAR, OE_F_UPPER_BOUNDS,
    OE_FG_UPPER_BOUNDS, OE_TEMPERATURE_UPPER_BOUNDS,
    OE_TEMPERATURE_LABELS, labels, station_ids,
)

OUTPUT = Path("data/processed/weather/monthly_frequency.csv")
VARIABLES = {
    "f": (OE_F_UPPER_BOUNDS, labels(OE_F_UPPER_BOUNDS)),
    "fg": (OE_FG_UPPER_BOUNDS, labels(OE_FG_UPPER_BOUNDS)),
    "temperature": (OE_TEMPERATURE_UPPER_BOUNDS, OE_TEMPERATURE_LABELS),
}


def build(path: Path) -> pd.DataFrame:
    source = pq.ParquetFile(path)
    stations = station_ids(source, source.num_row_groups)
    counts = {
        variable: np.zeros((len(stations) * 12, len(names)), dtype=np.int64)
        for variable, (_, names) in VARIABLES.items()
    }
    off_grid = 0
    for batch in source.iter_batches(columns=["station", "time", "f", "fg", "t"]):
        stamp = batch.column("time").to_numpy(zero_copy_only=False).astype("datetime64[us]")
        years = stamp.astype("datetime64[Y]").astype(int) + 1970
        months = stamp.astype("datetime64[M]").astype(int) % 12
        hours = stamp.astype("datetime64[h]").astype(int) % 24
        on_grid = stamp.astype(np.int64) % (600 * 1_000_000) == 0
        daytime = (years >= FIRST_YEAR) & (years <= LAST_YEAR) & (hours >= 7)
        off_grid += int((daytime & ~on_grid).sum())
        eligible = daytime & on_grid
        station = batch.column("station").to_numpy(zero_copy_only=False)
        groups = np.searchsorted(stations, station) * 12 + months
        for variable, (bounds, _) in VARIABLES.items():
            values = batch.column("t" if variable == "temperature" else variable).to_numpy(zero_copy_only=False)
            valid = (valid_temperature(values) if variable == "temperature"
                     else np.isfinite(values) & (values >= 0))
            use = eligible & valid
            bins = np.searchsorted(bounds, values[use], side="right")
            target = counts[variable]
            target += np.bincount(
                groups[use] * target.shape[1] + bins, minlength=target.size,
            ).reshape(target.shape)
    frames = []
    for variable, (_, names) in VARIABLES.items():
        totals = counts[variable].sum(axis=1)
        for order, name in enumerate(names):
            observed = counts[variable][:, order]
            frames.append(pd.DataFrame({
                "weather_station_id": np.repeat(stations, 12),
                "month": np.tile(np.arange(1, 13), len(stations)),
                "variable": variable, "bin_label": name, "bin_order": order,
                "measurement_count": observed,
                "total_measurements_in_period": totals,
                "frequency": np.divide(observed, totals, out=np.full(len(totals), np.nan), where=totals > 0),
                "first_year": FIRST_YEAR, "last_year": LAST_YEAR,
                "start_hour": 7, "end_hour": 24,
            }))
    print(f"off_grid_daytime_observations_excluded={off_grid:,}", flush=True)
    return pd.concat(frames, ignore_index=True).sort_values(
        ["weather_station_id", "month", "variable", "bin_order"]
    ).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"wrote={args.output} rows={len(result):,}")


if __name__ == "__main__":
    main()
