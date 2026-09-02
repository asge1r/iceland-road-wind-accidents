"""Estimate accident rates using observed daily traffic allocated by wind time."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.tables.daily_counter_rate import (
    ACCIDENTS, DAILY, LOCATIONS, fit_model,
    match_accidents, read_inputs, require_columns,
)


CONDITIONS = Path("data/analysis/accident_conditions.csv")
OUTPUT = Path("reports/main/tables/daily_allocated_rate_ratio_by_wind.csv")
AUDIT = Path("reports/working/tables/daily_allocated_rate_audit.csv")
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
    parser.add_argument("-c", "--conditions", type=Path, default=CONDITIONS)
    parser.add_argument("-d", "--daily-traffic", type=Path, default=DAILY)
    parser.add_argument("-l", "--locations", type=Path, default=LOCATIONS)
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

    accidents, daily, locations = read_inputs(
        args.accidents, args.daily_traffic, args.locations
    )
    require_columns(accidents, {"meidsli"}, "Accident input")
    conditions = pd.read_csv(args.conditions)
    require_columns(conditions, {"id", "f"}, "Accident-condition input")
    if conditions["id"].duplicated().any():
        raise ValueError("Accident conditions are not unique by id")
    count_columns = COUNT_COLUMNS if args.time_window == "full-day" else ACTIVE_COUNT_COLUMNS
    observation_column = (
        "full_observation_count"
        if args.time_window == "full-day"
        else "active_07_24_observation_count"
    )
    required_daily = {observation_column} | {
        column for columns in count_columns.values() for column in columns
    }
    require_columns(daily, required_daily, "Daily traffic input")
    matches, exact_candidates = match_accidents(accidents, locations, args.max_distance_km)
    events = matches.merge(
        accidents[["id", "timestamp", "meidsli"]],
        on="id", how="left", validate="one_to_one",
    ).merge(
        conditions[["id", "f"]], on="id", how="left", validate="one_to_one"
    )
    if args.outcome == "serious-fatal":
        events = events[pd.to_numeric(events["meidsli"], errors="raise").le(2)].copy()
    if args.time_window == "07-24":
        events = events[events["timestamp"].dt.hour.ge(7)].copy()
    minimum_observations = 108 if args.time_window == "full-day" else 77
    valid_daily = daily[
        daily["traffic"].gt(0) & daily[observation_column].ge(minimum_observations)
    ].copy()
    events = events.merge(
        valid_daily[["counter_id", "date"]],
        on=["counter_id", "date"], how="inner", validate="many_to_one",
    )
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
        ("within_distance", matches["id"].nunique()),
        ("with_valid_daily_traffic_and_accident_wind", events["id"].nunique()),
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
