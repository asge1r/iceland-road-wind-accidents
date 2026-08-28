"""Build time-stratified case-crossover weather samples for each accident."""

from __future__ import annotations

import argparse
import calendar
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


DEFAULT_ACCIDENTS = Path("data/processed/accidents/rural_injury.csv")
DEFAULT_WEATHER = Path("data/processed/weather/weather.parquet")
DEFAULT_OUTPUT = Path("data/processed/accidents/case_control.csv")
MAX_DISTANCE_KM = 20.0
MAX_TIME_MINUTES = 5.0

SPECS = {
    "mean_wind": ("weather_station_id", "weather_station_dist_km", "f"),
    "temperature": ("temp_station_id", "temp_distance_km", "temperature_c"),
}


def referent_times(timestamp: pd.Timestamp) -> list[pd.Timestamp]:
    """Return other matching weekdays at the same time in one calendar month."""
    days = calendar.monthrange(timestamp.year, timestamp.month)[1]
    return [
        pd.Timestamp(
            year=timestamp.year,
            month=timestamp.month,
            day=day,
            hour=timestamp.hour,
            minute=timestamp.minute,
            second=timestamp.second,
        )
        for day in range(1, days + 1)
        if pd.Timestamp(timestamp.year, timestamp.month, day).weekday()
        == timestamp.weekday()
        and day != timestamp.day
    ]


def build_candidates(accidents: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for exposure, (station_column, distance_column, value_column) in SPECS.items():
        eligible = accidents[
            accidents[station_column].notna()
            & accidents[distance_column].le(MAX_DISTANCE_KM)
            & accidents[value_column].notna()
        ]
        for accident in eligible.itertuples(index=False):
            timestamp = accident.timestamp
            for sample_time in referent_times(timestamp):
                for weather_time in {
                    sample_time.floor("10min"), sample_time.ceil("10min")
                }:
                    difference = abs((weather_time - sample_time).total_seconds()) / 60
                    if difference <= MAX_TIME_MINUTES:
                        rows.append(
                            {
                                "exposure": exposure,
                                "stratum_id": int(accident.id),
                                "timestamp": sample_time,
                                "station_id": int(getattr(accident, station_column)),
                                "weather_time": weather_time,
                                "time_difference_minutes": difference,
                            }
                        )
    return pd.DataFrame(rows)


def read_weather(path: Path, candidates: pd.DataFrame) -> pd.DataFrame:
    needed = {
        int(station): np.sort(
            group["weather_time"].to_numpy(dtype="datetime64[us]").astype("int64")
        )
        for station, group in candidates.groupby("station_id")
    }
    hits: list[pd.DataFrame] = []
    source = pq.ParquetFile(path)
    for batch in source.iter_batches(
        batch_size=1_000_000, columns=["station", "time", "f", "fg", "t"]
    ):
        station = batch.column(0).to_numpy(zero_copy_only=False)
        timestamp = (
            batch.column(1).to_numpy(zero_copy_only=False)
            .astype("datetime64[us]").astype("int64")
        )
        keep = np.zeros(len(station), dtype=bool)
        for station_id in np.unique(station):
            target = needed.get(int(station_id))
            if target is None:
                continue
            locations = np.flatnonzero(station == station_id)
            values = timestamp[locations]
            positions = np.searchsorted(target, values)
            valid = positions < len(target)
            matched = np.zeros(len(values), dtype=bool)
            matched[valid] = target[positions[valid]] == values[valid]
            keep[locations[matched]] = True
        if keep.any():
            hit = batch.filter(keep).to_pandas().rename(
                columns={"station": "station_id", "time": "weather_time"}
            )
            hits.append(hit)
    if not hits:
        raise ValueError("No case-crossover control weather was found")
    return pd.concat(hits, ignore_index=True).drop_duplicates(
        ["station_id", "weather_time"]
    )


def assemble(
    accidents: pd.DataFrame, candidates: pd.DataFrame, weather: pd.DataFrame
) -> pd.DataFrame:
    controls = candidates.merge(
        weather, on=["station_id", "weather_time"], how="inner", validate="many_to_one"
    )
    controls["value"] = np.where(
        controls["exposure"].eq("mean_wind"), controls["f"], controls["t"]
    )
    valid_temperature = controls["t"].between(-30, 30, inclusive="both")
    controls = controls[
        controls["value"].notna()
        & (~controls["exposure"].eq("temperature") | valid_temperature)
    ]
    controls = (
        controls.sort_values(
            ["exposure", "stratum_id", "timestamp", "time_difference_minutes", "weather_time"]
        )
        .drop_duplicates(["exposure", "stratum_id", "timestamp"])
    )
    controls["case"] = 0

    cases = []
    for exposure, (station_column, distance_column, value_column) in SPECS.items():
        part = accidents[
            accidents[station_column].notna()
            & accidents[distance_column].le(MAX_DISTANCE_KM)
            & accidents[value_column].notna()
        ][["id", "timestamp", station_column, value_column]].copy()
        part.columns = ["stratum_id", "timestamp", "station_id", "value"]
        part.insert(0, "exposure", exposure)
        part["case"] = 1
        cases.append(part)
    case_rows = pd.concat(cases, ignore_index=True)

    controls = controls[
        ["exposure", "stratum_id", "case", "timestamp", "station_id", "value"]
    ]
    result = pd.concat([case_rows, controls], ignore_index=True)
    counts = result.groupby(["exposure", "stratum_id"])["case"].agg(["sum", "count"])
    valid_strata = counts[(counts["sum"].eq(1)) & (counts["count"].ge(2))].index
    result = result.set_index(["exposure", "stratum_id"]).loc[valid_strata].reset_index()
    result["controls_in_stratum"] = (
        result.groupby(["exposure", "stratum_id"])["case"].transform("size") - 1
    )
    result["station_id"] = result["station_id"].astype(int)
    return result.sort_values(["exposure", "stratum_id", "case", "timestamp"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-w", "--weather", type=Path, default=DEFAULT_WEATHER)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    accidents = pd.read_csv(args.accidents, low_memory=False)
    required = {"id", "timestamp", *[item for spec in SPECS.values() for item in spec]}
    missing = required - set(accidents)
    if missing:
        raise ValueError(f"Accident data are missing columns: {sorted(missing)}")
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"], errors="raise")
    candidates = build_candidates(accidents)
    weather = read_weather(args.weather, candidates)
    result = assemble(accidents, candidates, weather)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    summary = result.groupby("exposure").agg(
        rows=("case", "size"), strata=("stratum_id", "nunique"), cases=("case", "sum")
    )
    print(summary.to_string())
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
