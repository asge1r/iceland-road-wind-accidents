"""Check the primary mean-wind O/E result under alternative all-zero rules.

This is an explicit raw-data validation, not part of the ordinary analysis
run.  It reads the unchanged weather archive, recalculates accident matches
and background frequencies, and writes one comparison table.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.accidents.match_weather import (
    build_candidates,
    load_accidents,
    load_stations,
    read_candidate_weather,
    select_best,
    weather_station_ids,
)
from src.accidents.types import broad_accident_family
from src.analysis.oe_analysis import (
    VARIABLES,
    prepare_frequency,
    station_frequency_scenario,
)
from src.weather.clean import (
    GUST_TOLERANCE,
    MAX_F,
    MAX_FG,
    frozen_mask,
    scan_frozen_runs,
)
from src.weather.frequency import SEASONS, season_index


RAW_WEATHER = Path("data/raw/weather/weather_10min_raw.parquet")
ALL_ACCIDENTS = Path("data/processed/accidents/all.csv")
STUDY_ACCIDENTS = Path("data/analysis/accidents.csv")
STATIONS = Path("data/raw/weather/stations.csv")
BASE_FREQUENCY = Path("data/analysis/weather_frequency.csv")
OUTPUT = Path("reports/main/tables/zero_run_check.csv")


def duration_minutes(start: np.datetime64, end: np.datetime64) -> int:
    return int((end - start) / np.timedelta64(1, "m"))


def split_runs(
    runs: dict[int, list[tuple[np.datetime64, np.datetime64]]],
    threshold_hours: int | None,
) -> tuple[
    dict[int, list[tuple[np.datetime64, np.datetime64]]],
    dict[int, list[tuple[np.datetime64, np.datetime64]]],
]:
    """Return runs excluded and returned under one threshold."""
    if threshold_hours is None:
        return {}, runs
    threshold_minutes = threshold_hours * 60
    excluded: dict[int, list[tuple[np.datetime64, np.datetime64]]] = {}
    returned: dict[int, list[tuple[np.datetime64, np.datetime64]]] = {}
    for station, intervals in runs.items():
        excluded[station] = [
            interval for interval in intervals
            if duration_minutes(*interval) >= threshold_minutes
        ]
        returned[station] = [
            interval for interval in intervals
            if duration_minutes(*interval) < threshold_minutes
        ]
    return excluded, returned


def returned_counts(
    runs: dict[int, list[tuple[np.datetime64, np.datetime64]]],
) -> pd.DataFrame:
    """Count returned ten-minute zero observations by station and season."""
    rows: list[tuple[int, str, int]] = []
    step = np.timedelta64(10, "m")
    for station, intervals in runs.items():
        counts = np.zeros(len(SEASONS), dtype=np.int64)
        for start, end in intervals:
            timestamps = np.arange(start, end + step, step)
            months = timestamps.astype("datetime64[M]").astype(np.int64) % 12 + 1
            counts += np.bincount(season_index(months), minlength=len(SEASONS))
        rows.extend(
            (station, str(SEASONS[index]), int(value))
            for index, value in enumerate(counts) if value
        )
    return pd.DataFrame(rows, columns=["station", "season", "returned_zero_rows"])


def adjusted_frequency(base: pd.DataFrame, returned: pd.DataFrame) -> pd.DataFrame:
    """Add returned zero rows to the 0--5 m/s background interval."""
    frequency = base[base["variable"].eq("f")].copy()
    additions = returned.assign(
        variable="f", bin_label="0-5", bin_lower_value=0.0,
        measurement_count=returned["returned_zero_rows"],
    )[[
        "station", "season", "variable", "bin_label", "bin_lower_value",
        "measurement_count",
    ]]
    frequency = pd.concat([frequency, additions], ignore_index=True)
    frequency = frequency.groupby(
        ["station", "season", "variable", "bin_label"],
        as_index=False, observed=True,
    ).agg(
        bin_lower_value=("bin_lower_value", "first"),
        measurement_count=("measurement_count", "sum"),
    )
    frequency["total_measurements_in_period"] = frequency.groupby(
        ["station", "season", "variable"], observed=True
    )["measurement_count"].transform("sum")
    frequency["frequency_pct"] = (
        100 * frequency["measurement_count"]
        / frequency["total_measurements_in_period"]
    )
    return prepare_frequency(frequency).rename(
        columns={"station": "weather_station_id"}
    )


def valid_wind(weather: pd.DataFrame) -> pd.Series:
    f = weather["f"]
    fg = weather["fg"]
    return (
        f.notna() & fg.notna()
        & f.ge(0) & fg.ge(0) & f.lt(MAX_F) & fg.lt(MAX_FG)
        & ~((fg.eq(0)) & f.gt(0))
        & fg.add(GUST_TOLERANCE).ge(f)
    )


def analysis_accidents(events: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    conditions = matches[[
        "id", "weather_station_id", "weather_station_dist_km",
        "weather_time_difference_minutes", "f",
    ]]
    data = events.merge(conditions, on="id", how="left", validate="one_to_one")
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    data["vehicle_group"] = np.where(
        data["vehicle_count"].eq(1), "1 vehicle", "2 or more vehicles"
    )
    data["accident_family"] = data["tegohapps"].map(broad_accident_family)
    data["year"] = data["timestamp"].dt.year
    return data


def scenario_result(
    events: pd.DataFrame,
    accidents: pd.DataFrame,
    candidates: pd.DataFrame,
    candidate_weather: pd.DataFrame,
    base_frequency: pd.DataFrame,
    all_runs: dict[int, list[tuple[np.datetime64, np.datetime64]]],
    threshold_hours: int | None,
) -> pd.DataFrame:
    excluded, returned = split_runs(all_runs, threshold_hours)
    weather = candidate_weather[valid_wind(candidate_weather)].copy()
    is_excluded = frozen_mask(
        weather["weather_station_id"].to_numpy(),
        weather["weather_time"].to_numpy(dtype="datetime64[us]"),
        excluded,
    )
    best = select_best(candidates, weather.loc[~is_excluded])
    matches = accidents.reset_index()[["acc_index", "id"]].merge(
        best, on="acc_index", how="left", validate="one_to_one"
    )
    data = analysis_accidents(events, matches)
    frequency = adjusted_frequency(base_frequency, returned_counts(returned))
    _, details, coverage = station_frequency_scenario(
        data, frequency, VARIABLES[0], 20, "Injury accidents", "All seasons"
    )
    station_bins = details.groupby(
        ["weather_station_id", "weather_bin"], as_index=False, observed=False
    ).agg(
        observed_accidents=("observed_accidents", "sum"),
        expected_accidents=("expected_accidents", "sum"),
        background_measurements=("measurement_count", "sum"),
    ).rename(columns={"weather_bin": "coarse_bin"})
    result = station_bins.groupby("coarse_bin", as_index=False, observed=False).agg(
        observed_accidents=("observed_accidents", "sum"),
        expected_accidents=("expected_accidents", "sum"),
    )
    result["observed_expected_ratio"] = (
        result["observed_accidents"] / result["expected_accidents"]
    )
    label = "No all-zero exclusion" if threshold_hours is None else f"Exclude runs >= {threshold_hours} h"
    result.insert(0, "zero_run_rule", label)
    result.insert(1, "matched_accidents", int(coverage["analysed_accidents"]))
    return result[[
        "zero_run_rule", "matched_accidents", "coarse_bin",
        "observed_accidents", "expected_accidents", "observed_expected_ratio",
    ]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-w", "--weather", type=Path, default=RAW_WEATHER)
    parser.add_argument("-a", "--all-accidents", type=Path, default=ALL_ACCIDENTS)
    parser.add_argument("-e", "--study-accidents", type=Path, default=STUDY_ACCIDENTS)
    parser.add_argument("-s", "--stations", type=Path, default=STATIONS)
    parser.add_argument("-f", "--frequency", type=Path, default=BASE_FREQUENCY)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    source = pq.ParquetFile(args.weather)
    all_runs = scan_frozen_runs(source)
    accidents = load_accidents(
        args.all_accidents, "2007-01-01", "2025-12-31 23:59:59.999999"
    )
    stations = load_stations(args.stations, weather_station_ids(source))
    candidates, _ = build_candidates(accidents, stations)
    candidate_weather = read_candidate_weather(source, candidates)
    events = pd.read_csv(args.study_accidents)
    base_frequency = pd.read_csv(args.frequency)
    results = [
        scenario_result(
            events, accidents, candidates, candidate_weather, base_frequency,
            all_runs, threshold,
        )
        for threshold in (2, 24, None)
    ]
    output = pd.concat(results, ignore_index=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(output.to_string(index=False))
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
