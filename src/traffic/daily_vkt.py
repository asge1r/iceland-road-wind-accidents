"""Accident rates using rural lengths, daily traffic and same-day weather.

Denominator: sum of vehicles * rural section km * observed bin minutes / 1020.
Numerator: rural accidents classified by their actual event-time weather.
All traffic is assumed to occur uniformly between 07:00 and 24:00.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.traffic.counter_days import require_columns
from src.weather.monthly_frequency import VARIABLES
from src.traffic.daytime_weather import build_daytime_weather, DAYTIME_MINUTES
from src.traffic.counter_accidents import WEATHER
from src.weather.eligibility import valid_temperature
from src.traffic.station_selection import STATIONS, SECTIONS

COUNTER_DAYS = Path("data/processed/traffic/counter_days.csv")
ACCIDENTS = Path("data/processed/traffic/counter_accidents.csv")
OUTPUT = Path("data/processed/traffic/daily_vkt.csv")
ALLOCATION_METHOD = "rural daily vehicle-km uniformly allocated over 07:00-24:00; nearest available station per timestamp within 20 km; missing time excluded"
OUTCOMES = {
    "Minor injury accidents": lambda value: value.eq(3),
    "Severe/fatal accidents": lambda value: value.isin([1, 2]),
}


def allocate_daily_exposure(
    counter_days: pd.DataFrame, weather: pd.DataFrame, variable: str,
) -> pd.DataFrame:
    """Allocate every observed positive-traffic day, including accident-free days."""
    require_columns(counter_days, {
        "date", "year", "season", "counter_section_id", "vehicle_km",
        "traffic_vehicles", "weather_station_id",
        "rural_section_length_km",
    }, "Counter days")
    require_columns(weather, {
        "counter_section_id", "weather_station_id", "date", "variable", "bin_label", "bin_order", "observed_minutes",
    }, "Same-day weather")
    days = counter_days.copy()
    days["date"] = pd.to_datetime(days["date"], errors="raise")
    if days.duplicated(["date", "counter_section_id"]).any():
        raise ValueError("Duplicate counter-days")
    if not np.isfinite(days["vehicle_km"]).all() or days["vehicle_km"].lt(0).any():
        raise ValueError("Invalid daily vehicle-km")
    if not np.allclose(days.vehicle_km, days.traffic_vehicles * days.rural_section_length_km,
                       rtol=1e-10, atol=1e-6):
        raise ValueError("Vehicle-km must use rural lengths; rebuild counter_days.csv")
    days = days[days["traffic_vehicles"].gt(0) & days["vehicle_km"].gt(0)]
    days = days.drop(columns="weather_station_id")  # nominal annual station
    background = weather[weather["variable"].eq(variable)].copy()
    background["date"] = pd.to_datetime(background["date"], errors="raise")
    keys = ["counter_section_id", "date"]
    if background.duplicated([*keys, "weather_station_id", "bin_label"]).any():
        raise ValueError("Duplicate daily weather bins")
    if not np.isfinite(background["observed_minutes"]).all() or background["observed_minutes"].le(0).any():
        raise ValueError("Daily observed minutes must be positive and finite")
    sums = background.groupby(keys, observed=True)["observed_minutes"].sum()
    if sums.gt(DAYTIME_MINUTES).any():
        raise ValueError("Daily weather coverage exceeds 07:00-24:00")
    expected_bins = dict(enumerate(VARIABLES[variable][1]))
    if not background["bin_order"].map(expected_bins).eq(background["bin_label"]).all():
        raise ValueError("Daily bins disagree with the analysis bins")
    exposure = days.merge(
        background[[*keys, "weather_station_id", "bin_label", "bin_order", "observed_minutes"]],
        on=keys, how="inner", validate="many_to_many",
    )
    exposure["estimated_vehicle_km"] = exposure["vehicle_km"] * exposure["observed_minutes"] / DAYTIME_MINUTES
    reconstructed = exposure.groupby(["date", "counter_section_id"])["estimated_vehicle_km"].sum()
    eligible_days = days.merge(sums.rename("valid_minutes"), on=keys, how="inner", validate="many_to_one")
    eligible_days["covered_vehicle_km"] = eligible_days.vehicle_km * eligible_days.valid_minutes / DAYTIME_MINUTES
    expected = eligible_days.set_index(["date", "counter_section_id"])["covered_vehicle_km"].reindex(reconstructed.index)
    if not np.allclose(reconstructed, expected, rtol=1e-10, atol=1e-6):
        raise ValueError("Daily allocation does not reconstruct weather-covered vehicle-km")
    print(f"{variable}: eligible_counter_days={len(reconstructed):,}; "
          f"excluded_without_daytime_weather={len(days) - len(reconstructed):,}; "
          f"excluded_unobserved_vehicle_km={days.vehicle_km.sum() - reconstructed.sum():,.0f}", flush=True)
    exposure["variable"] = variable
    exposure["counter_day_key"] = exposure.groupby(["counter_section_id", "date"]).ngroup()
    return exposure


def summarise_rates(
    counter_days: pd.DataFrame, accidents: pd.DataFrame, weather: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int]]:
    output: list[pd.DataFrame] = []
    summary: dict[str, int] = {}
    counter_days = counter_days.copy()
    counter_days["date"] = pd.to_datetime(counter_days["date"], errors="raise")
    accidents = accidents.copy()
    accidents["date"] = pd.to_datetime(accidents["date"], errors="raise")
    if accidents["id"].duplicated().any():
        raise ValueError("Duplicate accident IDs")
    for variable, (_, raw_labels) in VARIABLES.items():
        bin_labels = list(raw_labels)
        exposure = allocate_daily_exposure(counter_days, weather, variable)
        valid_days = exposure[["date", "counter_section_id", "weather_station_id"]].drop_duplicates()
        events = accidents.merge(
            valid_days, on=["date", "counter_section_id", "weather_station_id"], how="inner",
            validate="many_to_one",
        )
        summary[f"{variable}_excluded_accidents_no_daytime_weather"] = len(accidents) - len(events)
        values = events[variable]
        values = values.where(valid_temperature(values) if variable == "temperature" else np.isfinite(values) & values.ge(0))
        bounds = np.asarray(VARIABLES[variable][0], dtype=float)
        edges = [-np.inf, *bounds, np.inf] if variable == "temperature" else [0, *bounds, np.inf]
        events = events.copy()
        events["bin_label"] = pd.cut(
            values, edges, labels=bin_labels, right=False, include_lowest=True
        )
        events = events.dropna(subset=["bin_label"])
        covered_bins = exposure[["date", "counter_section_id", "weather_station_id", "bin_label"]].drop_duplicates()
        checked = events.merge(covered_bins, on=["date", "counter_section_id", "weather_station_id", "bin_label"],
                               how="left", indicator=True, validate="many_to_one")
        if checked["_merge"].ne("both").any():
            raise ValueError("Accident weather bin has no matching same-day exposure")
        summary[f"{variable}_accidents"] = events["id"].nunique()
        for outcome, selector in OUTCOMES.items():
            selected = events[selector(events["meidsli"])].copy()
            observed = selected.groupby(
                ["season", "bin_label"], as_index=False, observed=True
            ).agg(accidents=("id", "nunique"))
            observed["period"] = observed["season"].replace({"Fall": "Autumn"})
            annual_observed = selected.groupby(
                "bin_label", as_index=False, observed=True
            ).agg(accidents=("id", "nunique"))
            annual_observed["period"] = "All year"
            observed = pd.concat([annual_observed, observed], ignore_index=True)

            exposure_summary = exposure.groupby(
                ["season", "bin_label", "bin_order"], as_index=False, observed=True
            ).agg(
                estimated_vehicle_km=("estimated_vehicle_km", "sum"),
                counter_days=("counter_day_key", "nunique"),
                counter_sections=("counter_section_id", "nunique"),
            )
            exposure_summary["period"] = exposure_summary["season"].replace(
                {"Fall": "Autumn"}
            )
            annual_exposure = exposure.groupby(
                ["bin_label", "bin_order"], as_index=False, observed=True
            ).agg(
                estimated_vehicle_km=("estimated_vehicle_km", "sum"),
                counter_days=("counter_day_key", "nunique"),
                counter_sections=("counter_section_id", "nunique"),
            )
            annual_exposure["period"] = "All year"
            exposure_summary = pd.concat(
                [annual_exposure, exposure_summary], ignore_index=True
            )
            grid = pd.MultiIndex.from_product(
                [["All year", "Winter", "Spring", "Summer", "Autumn"], bin_labels],
                names=["period", "bin_label"],
            ).to_frame(index=False)
            exposure_summary = grid.merge(
                exposure_summary.drop(columns="season", errors="ignore"),
                on=["period", "bin_label"], how="left", validate="one_to_one",
            )
            exposure_summary["bin_order"] = exposure_summary["bin_label"].map(
                {label: order for order, label in enumerate(bin_labels)}
            )
            for column in ["estimated_vehicle_km", "counter_days", "counter_sections"]:
                exposure_summary[column] = exposure_summary[column].fillna(0)
            result = exposure_summary.merge(
                observed[["period", "bin_label", "accidents"]],
                on=["period", "bin_label"], how="left", validate="one_to_one",
            )
            result["accidents"] = result["accidents"].fillna(0).astype(int)
            result["rate_per_million_vehicle_km"] = (
                result["accidents"] / result["estimated_vehicle_km"].where(result["estimated_vehicle_km"].gt(0)) * 1_000_000
            )
            result["variable"] = variable
            result["outcome"] = outcome
            result["allocation_method"] = ALLOCATION_METHOD
            output.append(result)
    combined = pd.concat(output, ignore_index=True)
    combined["_period_order"] = combined["period"].map(
        {"All year": 0, "Winter": 1, "Spring": 2, "Summer": 3, "Autumn": 4}
    )
    combined["_variable_order"] = combined["variable"].map(
        {"f": 0, "fg": 1, "temperature": 2}
    )
    combined["_outcome_order"] = combined["outcome"].map(
        {name: index for index, name in enumerate(OUTCOMES)}
    )
    combined = combined.sort_values(
        ["_variable_order", "_outcome_order", "_period_order", "bin_order"]
    )
    columns = [
        "variable", "outcome", "period", "bin_label", "bin_order", "accidents",
        "estimated_vehicle_km", "rate_per_million_vehicle_km", "counter_days",
        "counter_sections", "allocation_method",
    ]
    return combined[columns].reset_index(drop=True), summary


def build(
    counter_days_path: Path, accidents_path: Path, weather_path: Path,
    sections_path: Path = SECTIONS, stations_path: Path = STATIONS,
) -> tuple[pd.DataFrame, dict[str, int]]:
    counter_days = pd.read_csv(counter_days_path)
    accidents = pd.read_csv(accidents_path, low_memory=False)
    accidents["date"] = pd.to_datetime(accidents["date"], errors="raise")
    weather = build_daytime_weather(weather_path, counter_days, sections_path, stations_path)
    return summarise_rates(counter_days, accidents, weather)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--counter-days", type=Path, default=COUNTER_DAYS)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-w", "--weather", type=Path, default=WEATHER)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-s", "--stations", type=Path, default=STATIONS)
    parser.add_argument("-k", "--counter-sections", type=Path, default=SECTIONS)
    args = parser.parse_args()
    result, summary = build(args.counter_days, args.accidents, args.weather, args.counter_sections, args.stations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print("; ".join(f"{key}={value:,}" for key, value in summary.items()))
    print(f"wrote={args.output} rows={len(result):,}")


if __name__ == "__main__":
    main()
