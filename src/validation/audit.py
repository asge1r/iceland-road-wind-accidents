"""Coordinate focused validation of retained analysis results."""

from __future__ import annotations

from pathlib import Path

from src.accidents.types import broad_accident_family
from src.validation.models import validate_models
from src.validation.traffic import validate_traffic_checks, validate_traffic_models
from src.validation.weather import validate_weather


def validation_values(
    accidents_path: Path, conditions_path: Path, weather_audit_path: Path,
    weather_oe_path: Path, daily_path: Path, daily_accident_weather_path: Path,
    traffic_audit_path: Path, rate_input_path: Path, rate_model_path: Path,
    rate_serious_path: Path, seasonal_rate_path: Path,
    seasonal_serious_path: Path, case_control_path: Path,
    case_control_result_path: Path, traffic_checks_path: Path,
    daily_rate_path: Path,
    daily_rate_coarse_path: Path, daily_rate_radius_path: Path,
    daily_duration_path: Path, daily_allocated_path: Path,
    daily_sample_path: Path, daily_serious_path: Path, daily_07_24_path: Path,
) -> dict[str, object]:
    values = validate_weather(
        accidents_path, conditions_path, weather_audit_path, weather_oe_path,
    )
    values.update(validate_traffic_models(
        daily_path, daily_accident_weather_path, traffic_audit_path,
        rate_input_path, rate_model_path, rate_serious_path,
        seasonal_rate_path, seasonal_serious_path,
    ))
    values.update(validate_models(
        case_control_path, case_control_result_path, values["_accidents"],
    ))
    values.update(validate_traffic_checks(
        traffic_checks_path, daily_rate_path,
        daily_rate_coarse_path, daily_rate_radius_path, daily_duration_path,
        daily_allocated_path, daily_sample_path, daily_serious_path,
        daily_07_24_path,
    ))
    accidents = values.pop("_accidents")
    values.pop("_weather_oe")
    families = accidents["tegohapps"].map(broad_accident_family)
    single_count = int(
        families.eq("Single vehicle: run-off-road, rollover, fall, or other").sum()
    )
    values["single_vehicle_count"] = single_count
    values["single_vehicle_pct"] = 100 * single_count / len(accidents)
    return values
