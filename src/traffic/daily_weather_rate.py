"""Estimate 07:00--24:00 accident rates by weather interval and counter traffic."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.accidents.match_weather import read_candidate_weather, select_best
from src.export_common import season_from_month
from src.weather.frequency import (
    OE_FG_UPPER_BOUNDS,
    OE_F_UPPER_BOUNDS,
    OE_TEMPERATURE_LABELS,
    OE_TEMPERATURE_UPPER_BOUNDS,
    labels,
)


ACCIDENTS = Path("data/processed/accidents/accidents-near-counter.csv")
DAILY = Path("data/processed/traffic/daily_raw.csv")
COUNTER_SECTIONS = Path("data/processed/traffic/counter_sections.csv")
FREQUENCY = Path("data/processed/weather/monthly_frequency.csv")
WEATHER = Path("data/processed/weather/weather.parquet")
OUTPUT = Path("data/processed/traffic/daily_weather_rate.csv")

VARIABLES = {
    "f": (OE_F_UPPER_BOUNDS, labels(OE_F_UPPER_BOUNDS)),
    "fg": (OE_FG_UPPER_BOUNDS, labels(OE_FG_UPPER_BOUNDS)),
    "temperature": (OE_TEMPERATURE_UPPER_BOUNDS, OE_TEMPERATURE_LABELS),
}
OUTCOMES = {
    "Injury accidents": lambda value: value.isin([1, 2, 3]),
    "Severe/fatal accidents": lambda value: value.isin([1, 2]),
}


def require_columns(data: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(data)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def build_counter_days(daily_path: Path, sections_path: Path) -> pd.DataFrame:
    """Sum lane counts into physical counter-sections and convert them to vehicle-km."""
    daily = pd.read_csv(daily_path, low_memory=False)
    sections = pd.read_csv(sections_path, low_memory=False)
    require_columns(
        daily, {"date", "year", "station_id", "road_section", "traffic_volume"},
        "Daily traffic",
    )
    require_columns(
        sections,
        {
            "year", "road_section", "counter_section_id", "source_station_min_m",
            "source_station_max_m", "counter_section_length_km", "weather_station_id",
            "weather_station_dist_km",
        },
        "Counter sections",
    )
    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    daily["road_section"] = daily["road_section"].astype("string").str.lower().str.strip()
    daily["station_id"] = pd.to_numeric(daily["station_id"], errors="raise")
    daily["traffic_volume"] = pd.to_numeric(daily["traffic_volume"], errors="raise")
    daily["daily_row"] = np.arange(len(daily))
    sections = sections.copy()
    sections["road_section"] = sections["road_section"].astype("string").str.lower().str.strip()
    joined = daily.merge(sections, on=["year", "road_section"], how="left")
    joined = joined[
        joined["station_id"].between(
            joined["source_station_min_m"], joined["source_station_max_m"]
        )
    ].copy()
    if joined.duplicated("daily_row").any():
        raise ValueError("A daily counter row maps to more than one counter-section")
    joined = joined[
        joined["counter_section_length_km"].gt(0)
        & joined["weather_station_id"].notna()
        & joined["weather_station_dist_km"].le(20)
        & joined["traffic_volume"].ge(0)
    ].copy()
    joined["weather_station_id"] = joined["weather_station_id"].astype(int)
    group = [
        "date", "year", "counter_section_id", "counter_section_length_km",
        "weather_station_id",
    ]
    result = joined.groupby(group, as_index=False, observed=True).agg(
        traffic_vehicles=("traffic_volume", "sum")
    )
    result["month"] = result["date"].dt.month
    result["season"] = season_from_month(result["month"])
    result["vehicle_km"] = result["traffic_vehicles"] * result["counter_section_length_km"]
    return result


def allocate_exposure(counter_days: pd.DataFrame, frequency_path: Path) -> pd.DataFrame:
    """Allocate observed daily vehicle-km by station-month weather frequencies."""
    frequency = pd.read_csv(frequency_path, low_memory=False)
    require_columns(
        frequency,
        {
            "station", "month", "time_window", "variable", "bin_label",
            "measurement_count", "total_measurements_in_month", "frequency_pct",
        },
        "Monthly weather frequency",
    )
    frequency = frequency[frequency["time_window"].eq("07:00-24:00")].copy()
    frequency["station"] = pd.to_numeric(frequency["station"], errors="raise").astype(int)
    joined = counter_days.merge(
        frequency,
        left_on=["weather_station_id", "month"], right_on=["station", "month"],
        how="inner", validate="many_to_many",
    )
    totals = joined.groupby(
        ["date", "counter_section_id", "variable"], observed=True
    )["frequency_pct"].sum()
    if not np.allclose(totals.to_numpy(), 100.0, atol=1e-8):
        raise ValueError("Monthly weather-bin frequencies do not sum to 100%")
    joined["estimated_vehicle_km"] = joined["vehicle_km"] * joined["frequency_pct"] / 100
    return joined


def accident_candidates(accidents: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in accidents.itertuples(index=True):
        for weather_time in {row.timestamp.floor("10min"), row.timestamp.ceil("10min")}:
            difference = abs((weather_time - row.timestamp).total_seconds()) / 60
            if difference <= 5:
                rows.append(
                    {
                        "acc_index": row.Index,
                        "weather_station_id": int(row.weather_station_id),
                        "weather_station_dist_km": float(row.weather_station_dist_km),
                        "weather_time": weather_time,
                        "weather_time_difference_minutes": difference,
                    }
                )
    return pd.DataFrame(rows)


def matched_accidents(accidents_path: Path, counter_days: pd.DataFrame, weather_path: Path) -> pd.DataFrame:
    """Keep daytime accidents with a traffic day and match their section's station weather."""
    accidents = pd.read_csv(accidents_path, low_memory=False)
    require_columns(
        accidents,
        {
            "id", "timestamp", "meidsli", "counter_section_id",
            "counter_weather_station_id", "counter_weather_station_dist_km",
        },
        "Assigned accidents",
    )
    accidents = accidents.copy()
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"], errors="raise")
    accidents["date"] = accidents["timestamp"].dt.normalize()
    accidents["month"] = accidents["timestamp"].dt.month
    accidents["season"] = season_from_month(accidents["month"])
    accidents["meidsli"] = pd.to_numeric(accidents["meidsli"], errors="coerce")
    accidents = accidents[
        accidents["timestamp"].dt.hour.ge(7)
        & accidents["counter_weather_station_dist_km"].le(20)
    ].copy()
    traffic_days = counter_days[["date", "counter_section_id", "weather_station_id"]]
    accidents = accidents.merge(
        traffic_days, on=["date", "counter_section_id"], how="inner", validate="many_to_one"
    )
    accidents = accidents.rename(
        columns={
            "weather_station_id": "assigned_weather_station_id",
            "counter_weather_station_id": "weather_station_id",
            "counter_weather_station_dist_km": "weather_station_dist_km",
        }
    )
    if not accidents["weather_station_id"].eq(accidents["assigned_weather_station_id"]).all():
        raise ValueError("Accident and counter-day weather station disagree")
    accidents = accidents.reset_index(drop=True)
    candidates = accident_candidates(accidents)
    weather = read_candidate_weather(pq.ParquetFile(weather_path), candidates)
    matched = select_best(candidates, weather)
    result = accidents.merge(
        matched[["acc_index", "f", "fg", "t"]],
        left_index=True, right_on="acc_index", how="inner", validate="one_to_one"
    ).drop(columns="acc_index")
    result["temperature"] = result["t"].where(result["t"].between(-30, 30))
    return result


def build(accidents_path: Path, daily_path: Path, sections_path: Path, frequency_path: Path,
          weather_path: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    counter_days = build_counter_days(daily_path, sections_path)
    exposure = allocate_exposure(counter_days, frequency_path)
    accidents = matched_accidents(accidents_path, counter_days, weather_path)
    output: list[pd.DataFrame] = []
    for variable, (bounds, bin_labels) in VARIABLES.items():
        exposures = exposure[exposure["variable"].eq(variable)].copy()
        exposure_group = ["season", "bin_label"]
        exposure_summary = exposures.groupby(exposure_group, as_index=False, observed=True).agg(
            estimated_vehicle_km=("estimated_vehicle_km", "sum"),
            counter_days=("date", "size"),
            counter_sections=("counter_section_id", "nunique"),
        )
        exposure_summary["period"] = exposure_summary["season"].replace({"Fall": "Autumn"})
        all_exposure = exposures.groupby("bin_label", as_index=False, observed=True).agg(
            estimated_vehicle_km=("estimated_vehicle_km", "sum"),
            counter_days=("date", "size"),
            counter_sections=("counter_section_id", "nunique"),
        )
        all_exposure["period"] = "All year"
        exposure_summary = pd.concat([all_exposure, exposure_summary], ignore_index=True)
        for outcome, selector in OUTCOMES.items():
            events = accidents[selector(accidents["meidsli"])].copy()
            values = events["temperature"] if variable == "temperature" else events[variable]
            edges = [-np.inf, *bounds, np.inf] if variable == "temperature" else [0, *bounds, np.inf]
            events["bin_label"] = pd.cut(values, edges, labels=bin_labels, right=False, include_lowest=True)
            observed = events.dropna(subset=["bin_label"]).groupby(
                ["season", "bin_label"], as_index=False, observed=True
            ).agg(accidents=("id", "nunique"))
            observed["period"] = observed["season"].replace({"Fall": "Autumn"})
            all_observed = events.dropna(subset=["bin_label"]).groupby(
                "bin_label", as_index=False, observed=True
            ).agg(accidents=("id", "nunique"))
            all_observed["period"] = "All year"
            observed = pd.concat([all_observed, observed], ignore_index=True)
            result = exposure_summary.merge(
                observed[["period", "bin_label", "accidents"]],
                on=["period", "bin_label"], how="left", validate="one_to_one"
            )
            result["accidents"] = result["accidents"].fillna(0).astype(int)
            result["rate_per_million_vehicle_km"] = (
                result["accidents"] / result["estimated_vehicle_km"] * 1_000_000
            )
            result["variable"] = variable
            result["outcome"] = outcome
            result["bin_order"] = result["bin_label"].map(
                {label: index for index, label in enumerate(bin_labels)}
            )
            output.append(result)
    result = pd.concat(output, ignore_index=True)
    result["_period_order"] = result["period"].map(
        {"All year": 0, "Winter": 1, "Spring": 2, "Summer": 3, "Autumn": 4}
    )
    result["_variable_order"] = result["variable"].map({"f": 0, "fg": 1, "temperature": 2})
    result["_outcome_order"] = result["outcome"].map({name: index for index, name in enumerate(OUTCOMES)})
    result = result.sort_values(["_variable_order", "_outcome_order", "_period_order", "bin_order"])
    columns = [
        "variable", "outcome", "period", "bin_label", "bin_order", "accidents",
        "estimated_vehicle_km", "rate_per_million_vehicle_km", "counter_days", "counter_sections",
    ]
    summary = {
        "counter_days": int(counter_days[["date", "counter_section_id"]].drop_duplicates().shape[0]),
        "counter_sections": int(counter_days["counter_section_id"].nunique()),
        "assigned_accidents_with_daytime_traffic": len(accidents),
    }
    return result[columns], summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-d", "--daily", type=Path, default=DAILY)
    parser.add_argument("-c", "--counter-sections", type=Path, default=COUNTER_SECTIONS)
    parser.add_argument("-f", "--frequency", type=Path, default=FREQUENCY)
    parser.add_argument("-w", "--weather", type=Path, default=WEATHER)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result, summary = build(args.accidents, args.daily, args.counter_sections, args.frequency, args.weather)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(
        f"counter_days={summary['counter_days']:,}; counter_sections={summary['counter_sections']:,}; "
        f"daytime accidents with traffic and matched weather={summary['assigned_accidents_with_daytime_traffic']:,}; "
        f"wrote={args.output} rows={len(result):,}"
    )


if __name__ == "__main__":
    main()
