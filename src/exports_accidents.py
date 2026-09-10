"""Export compact accident and matched-time analysis tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analysis.solar import daylight_class, solar_elevation
from src.export_common import ROOT, read_table, season_from_month, traffic_period_from_month, write_csv

def export_accident_tables(output: Path) -> list[tuple[str, int, list[str], str]]:
    source = read_table(ROOT / "accidents/rural_injury.csv").copy()
    source["timestamp"] = pd.to_datetime(source["timestamp"], errors="raise")
    source["weather_station_id"] = pd.to_numeric(
        source["weather_station_id"], errors="coerce"
    ).astype("Int64")
    source["year"] = source["timestamp"].dt.year
    source["month"] = source["timestamp"].dt.month
    source["weekday"] = source["timestamp"].dt.day_name()
    source["hour"] = source["timestamp"].dt.hour
    source["season"] = season_from_month(source["month"])
    source["traffic_period"] = traffic_period_from_month(source["month"])
    source["solar_elevation_deg"] = solar_elevation(
        source["timestamp"], source["lat"], source["lon"]
    )
    source["daylight_class"] = daylight_class(source["solar_elevation_deg"])
    events = [
        "id", "timestamp", "year", "month", "weekday", "hour", "lat", "lon",
        "meidsli", "tegohapps", "vehicle_count", "registered_road_section",
        "season", "traffic_period",
    ]
    conditions = [
        "id", "weather_station_id", "weather_station_dist_km",
        "weather_time_difference_minutes", "f", "fg",
        "temp_station_id", "temp_distance_km", "temp_time_diff_min", "temperature_c",
        "temp_source",
        "solar_elevation_deg", "daylight_class",
    ]
    event_table = source[events].rename(columns={"registered_road_section": "road_section"})
    event_count = write_csv(event_table, output / "accidents.csv")
    condition_table = source[conditions]
    condition_count = write_csv(condition_table, output / "accident_conditions.csv")
    entries = [
        (
            "accidents.csv", event_count, list(event_table.columns),
            "Rural injury accident events with outcome, location, and calendar fields.",
        ),
        (
            "accident_conditions.csv", condition_count, list(condition_table.columns),
            "Independent wind and temperature matches plus astronomical daylight.",
        ),
    ]
    accident_weather_path = ROOT / "traffic/accident_wind.csv"
    if accident_weather_path.exists():
        accident_weather = read_table(accident_weather_path)
        accident_weather_columns = [
            "id", "year", "date", "counter_id", "counter_distance_km",
            "counter_weather_station_id", "counter_weather_station_dist_km",
            "counter_station_accident_distance_km", "weather_time",
            "weather_time_difference_minutes", "f",
        ]
        missing = set(accident_weather_columns) - set(accident_weather)
        if missing:
            raise ValueError(
                f"Daily-counter accident weather is missing columns: {sorted(missing)}"
            )
        accident_weather = accident_weather[accident_weather_columns].sort_values("id")
        accident_weather_count = write_csv(
            accident_weather, output / "counter_wind.csv"
        )
        entries.append(
            (
                "counter_wind.csv",
                accident_weather_count,
                accident_weather_columns,
                "Accident-time mean wind from the same station used for the assigned counter-day.",
            )
        )
    return entries

def export_case_control(output: Path) -> tuple[int, list[str]]:
    source = pd.read_csv(ROOT / "accidents/case_control.csv", low_memory=False)
    columns = [
        "exposure", "stratum_id", "case", "timestamp", "station_id", "value",
        "controls_in_stratum",
    ]
    missing = set(columns) - set(source)
    if missing:
        raise ValueError(f"Case-crossover input is missing columns: {sorted(missing)}")
    if not source["case"].isin([0, 1]).all():
        raise ValueError("Case-crossover case indicator must contain only zero and one")
    return write_csv(source[columns], output / "case_control.csv"), columns


def export_temperature_matches(output: Path) -> tuple[int, list[str]]:
    """Export the one-row-per-accident temperature match for direct inspection."""
    source = read_table(ROOT / "accidents/rural_injury.csv")
    columns = [
        "id", "timestamp", "temp_station_id", "temp_distance_km",
        "temp_time_diff_min", "temperature_c", "temp_source",
    ]
    missing = set(columns) - set(source)
    if missing:
        raise ValueError(f"Temperature matches are missing columns: {sorted(missing)}")
    table = source[columns].sort_values(["timestamp", "id"])
    return write_csv(table, output / "temperature_matches.csv"), columns
