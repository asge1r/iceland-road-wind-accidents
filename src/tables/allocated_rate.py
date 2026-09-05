"""Estimate accident rates using observed daily traffic allocated by wind time."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.tables.counter_rate import ACCIDENTS, DAILY, fit_model, require_columns


MATCHES = Path("data/analysis/counter_wind.csv")
OUTPUT = Path("reports/main/tables/allocated_rate.csv")
AUDIT = Path("reports/working/tables/allocated_rate_audit.csv")
LABELS = ["0-10", "10-15", ">=15"]
COUNT_COLUMNS = {
    "0-10": ["f_full_bin_0_5_count", "f_full_bin_5_10_count"],
    "10-15": ["f_full_bin_10_15_count"],
    ">=15": [
        "f_full_bin_15_20_count", "f_full_bin_20_25_count",
        "f_full_bin_ge25_count",
    ],
}
ACTIVE_COUNT_COLUMNS = {
    label: [column.replace("f_full_", "f_07_24_") for column in columns]
    for label, columns in COUNT_COLUMNS.items()
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-m", "--matches", type=Path, default=MATCHES)
    parser.add_argument("-d", "--daily-traffic", type=Path, default=DAILY)
    parser.add_argument("-r", "--max-distance-km", type=float, default=20)
    parser.add_argument(
        "-g", "--outcome", choices=["injury", "serious-fatal"], default="injury",
    )
    parser.add_argument(
        "-t", "--time-window", choices=["full-day", "07-24"], default="full-day",
    )
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-u", "--audit", type=Path, default=AUDIT)
    args = parser.parse_args()

    for path in [args.accidents, args.matches, args.daily_traffic]:
        if path.suffix.lower() != ".csv":
            raise ValueError(f"Analysis input must be CSV: {path}")
    accidents = pd.read_csv(args.accidents)
    daily = pd.read_csv(args.daily_traffic)
    matches = pd.read_csv(args.matches)
    require_columns(accidents, {"id", "timestamp", "year", "meidsli"}, "Accident input")
    require_columns(
        matches,
        {
            "id", "year", "date", "counter_id", "counter_distance_km",
            "counter_weather_station_id", "counter_weather_station_dist_km",
            "counter_station_accident_distance_km",
            "weather_time_difference_minutes", "f",
        },
        "Daily accident-weather input",
    )
    if matches["id"].duplicated().any():
        raise ValueError("Daily accident-weather rows are not unique by id")
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"], errors="raise")
    accidents = accidents[accidents["year"].between(2019, 2024)].copy()
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    daily["year"] = daily["date"].dt.year
    matches["date"] = pd.to_datetime(matches["date"], errors="raise")
    count_columns = COUNT_COLUMNS if args.time_window == "full-day" else ACTIVE_COUNT_COLUMNS
    observation_column = (
        "full_observation_count"
        if args.time_window == "full-day"
        else "active_07_24_observation_count"
    )
    required_daily = {observation_column, "weather_station_id"} | {
        column for columns in count_columns.values() for column in columns
    }
    require_columns(daily, required_daily, "Daily traffic input")
    exact_candidates = len(matches)
    matches = matches[
        matches["counter_distance_km"].le(args.max_distance_km)
        & matches["counter_weather_station_dist_km"].le(args.max_distance_km)
        & matches["counter_station_accident_distance_km"].le(args.max_distance_km)
        & matches["weather_time_difference_minutes"].le(5)
    ].copy()
    events = matches.merge(
        accidents[["id", "timestamp", "meidsli"]],
        on="id", how="left", validate="one_to_one",
    )
    if args.outcome == "serious-fatal":
        events = events[pd.to_numeric(events["meidsli"], errors="raise").le(2)].copy()
    if args.time_window == "07-24":
        events = events[events["timestamp"].dt.hour.ge(7)].copy()
    minimum_observations = 108 if args.time_window == "full-day" else 77
    valid_daily = daily[
        daily["traffic"].gt(0) & daily[observation_column].ge(minimum_observations)
    ].copy()
    all_bin_columns = [column for columns in count_columns.values() for column in columns]
    counted_weather = valid_daily[all_bin_columns].sum(axis=1)
    if not counted_weather.eq(valid_daily[observation_column]).all():
        bad = valid_daily.loc[
            ~counted_weather.eq(valid_daily[observation_column]),
            ["counter_id", "date", observation_column],
        ].head()
        raise ValueError(
            "Wind-bin counts do not reconstruct the daily observation count; "
            f"examples={bad.to_dict('records')}"
        )

    events = events.merge(
        valid_daily[["counter_id", "date", "weather_station_id"]],
        on=["counter_id", "date"], how="inner", validate="many_to_one",
    )
    if not events["counter_weather_station_id"].eq(events["weather_station_id"]).all():
        raise ValueError("Accident and counter-day exposure use different weather stations")
    events = events[events["f"].between(0, 45, inclusive="left")].copy()
    events["wind_bin"] = pd.cut(
        events["f"], [0, 10, 15, np.inf], labels=LABELS,
        right=False, include_lowest=True,
    ).astype("string")
    event_counts = events.groupby(
        ["counter_id", "year", "wind_bin"], observed=True, as_index=False
    ).agg(observed_accidents=("id", "nunique"))

    exposure_rows: list[pd.DataFrame] = []
    for label, columns in count_columns.items():
        frame = valid_daily[["counter_id", "year", "date", "traffic", observation_column]].copy()
        frame["wind_bin"] = label
        frame["wind_observations"] = valid_daily[columns].sum(axis=1)
        frame = frame[frame["wind_observations"].gt(0)].copy()
        frame["observed_vehicles"] = (
            frame["traffic"] * frame["wind_observations"]
            / frame[observation_column]
        )
        exposure_rows.append(frame)
    exposure = pd.concat(exposure_rows, ignore_index=True)
    reconstructed = exposure.groupby(
        ["counter_id", "date"]
    )["observed_vehicles"].sum()
    original = (
        valid_daily.set_index(["counter_id", "date"])["traffic"]
        .reindex(reconstructed.index)
    )
    if not np.allclose(
        reconstructed.to_numpy(float),
        original.to_numpy(float),
        rtol=1e-10,
        atol=1e-6,
    ):
        raise ValueError(
            "Allocated wind-bin traffic does not reconstruct observed daily traffic"
        )

    exposure = exposure.groupby(
        ["counter_id", "year", "wind_bin"], observed=True, as_index=False
    ).agg(
        observed_vehicles=("observed_vehicles", "sum"),
        counter_days=("date", "nunique"),
    )
    model_data = exposure.merge(
        event_counts, on=["counter_id", "year", "wind_bin"], how="left",
        validate="one_to_one",
    )
    model_data["observed_accidents"] = model_data["observed_accidents"].fillna(0).astype(int)
    model_data["stratum"] = model_data["counter_id"].astype(str) + "|" + model_data["year"].astype(str)
    informative = model_data.groupby("stratum")["observed_accidents"].transform("sum").gt(0)
    model_data = model_data[informative & model_data["observed_vehicles"].gt(0)].copy()
    result = fit_model(model_data, LABELS).rename(columns={
        "observed_vehicles": "estimated_vehicles_within_wind_bin",
        "accidents_per_100k_counted_vehicles": "accidents_per_100k_estimated_vehicles",
    })
    result["analysis_outcome"] = args.outcome
    result["analysis_time_window"] = args.time_window
    result["exposure_method"] = (
        "observed daily traffic allocated by wind frequency over " + args.time_window
    )
    audit = pd.DataFrame([
        ("rural_injury_accidents_2019_2024", len(accidents)),
        ("exact_road_section_counter_candidates", exact_candidates),
        ("within_all_distance_limits", matches["id"].nunique()),
        ("same_station_valid_daily_traffic_and_accident_wind", events["id"].nunique()),
        ("model_accidents", int(model_data["observed_accidents"].sum())),
        ("fitted_model_strata", int(result["model_strata"].iloc[0])),
    ], columns=["metric", "value"])
    for path in [args.output, args.audit]:
        path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    audit.to_csv(args.audit, index=False)
    print(audit.to_string(index=False))
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
