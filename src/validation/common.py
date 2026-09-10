"""Shared paths and assertions for final-analysis validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_WEATHER_AUDIT = Path("data/analysis/weather_cleaning.csv")
DEFAULT_WEATHER_OE = Path("reports/main/tables/weather_oe.csv")
DEFAULT_DAILY = Path("data/analysis/daily_traffic.csv")
DEFAULT_DAILY_ACCIDENT_WEATHER = Path("data/analysis/counter_wind.csv")
DEFAULT_TRAFFIC_AUDIT = Path("reports/main/tables/annual_quality.csv")
DEFAULT_RATE_INPUT = Path("data/analysis/road_rate.csv")
DEFAULT_RATE_MODEL = Path("reports/main/tables/wind_rate.csv")
DEFAULT_RATE_SERIOUS = Path("reports/main/tables/wind_rate_severity.csv")
DEFAULT_TRAFFIC_ALLOCATION_CHECK = Path(
    "reports/main/tables/allocation_check.csv"
)
DEFAULT_TEMPERATURE_RATE = Path("reports/main/tables/temperature_rate.csv")
DEFAULT_VEHICLE_RATE_ONE = Path("reports/main/tables/wind_rate_one.csv")
DEFAULT_VEHICLE_RATE_MULTIPLE = Path("reports/main/tables/wind_rate_multiple.csv")
DEFAULT_TRAFFIC_WIND = Path("reports/main/tables/traffic_wind.csv")
DEFAULT_SEASONAL_RATE = Path("reports/main/tables/season_rate.csv")
DEFAULT_SEASONAL_SERIOUS = Path("reports/main/tables/season_rate_severity.csv")
DEFAULT_CASE_CONTROL = Path("data/analysis/case_control.csv")
DEFAULT_CASE_CONTROL_RESULT = Path("reports/main/tables/matched_weather.csv")
DEFAULT_SEASON_INTERACTION = Path(
    "reports/main/tables/wind_season.csv"
)
DEFAULT_JOINT_WEATHER = Path("reports/main/tables/weather_model.csv")
DEFAULT_SEVERITY = Path("reports/main/tables/severity_conditions.csv")
DEFAULT_DAYLIGHT = Path("reports/main/tables/daylight.csv")
DEFAULT_TRAFFIC_CHECKS = Path("reports/main/tables/traffic_checks.csv")
DEFAULT_DAILY_RATE = Path("reports/main/tables/day_rate.csv")
DEFAULT_DAILY_RATE_COARSE = Path("reports/main/tables/day_rate_coarse.csv")
DEFAULT_DAILY_RATE_RADIUS = Path("reports/main/tables/counter_radius.csv")
DEFAULT_DAILY_DURATION = Path("reports/main/tables/wind_duration.csv")
DEFAULT_DAILY_ALLOCATED = Path("reports/main/tables/allocated_rate.csv")
DEFAULT_DAILY_SAMPLE = Path("reports/main/tables/daily_sample.csv")
DEFAULT_DAILY_SERIOUS = Path("reports/main/tables/allocated_rate_severity.csv")
DEFAULT_DAILY_07_24 = Path("reports/main/tables/allocated_rate_day.csv")
DEFAULT_DAILY_SEASON_PANEL = Path(
    "data/analysis/daily_season_panel.csv"
)
DEFAULT_DAILY_SEASON_OE = Path("reports/main/tables/daily_season_oe.csv")
DEFAULT_DAILY_WEATHER_RATE = Path("data/analysis/daily_weather_rate.csv")
DEFAULT_DAILY_SEASON_INTERACTION = Path(
    "reports/working/tables/daily_season_interaction.csv"
)
DEFAULT_DAILY_HIGHWIND_SEASON_INTERACTION = Path(
    "reports/working/tables/daily_highwind_season_interaction.csv"
)
DEFAULT_WIND_OE_COMPARISON = Path(
    "reports/main/tables/wind_oe_comparison.csv"
)
DEFAULT_OUTPUT = Path("reports/main/tables/validation.md")

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

def weather_checks(path: Path) -> dict[str, int]:
    audit = pd.read_csv(path)
    total = audit[audit["year"].astype(str).eq("total")]
    require(len(total) == 1, "Weather audit must contain one total row")
    row = total.iloc[0]
    require(int(row["clean_wind_rows"]) > 0, "No clean wind observations in weather audit")
    return {
        "input_rows": int(row["input_rows"]),
        "clean_rows": int(row["clean_wind_rows"]),
        "excluded_rows": int(row["excluded_rows"]),
    }
