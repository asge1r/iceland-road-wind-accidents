"""Validate canonical accident, weather, O/E, and coverage tables."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.validation.common import require, weather_checks


def validate_weather(
    accidents_path: Path, conditions_path: Path, weather_audit_path: Path,
    mean_wind_path: Path, temperature_path: Path, coverage_path: Path,
    oe_results_path: Path,
) -> dict[str, object]:
    if accidents_path.suffix != ".csv":
        raise ValueError(f"Analysis input must be a CSV file: {accidents_path}")
    accidents = pd.read_csv(accidents_path)
    require(len(accidents) > 0, "No rural injury accidents in canonical table")
    require(accidents["id"].is_unique, "Study accident IDs are not unique")
    conditions = pd.read_csv(conditions_path)
    required_condition_columns = {
        "id", "weather_station_id", "weather_station_dist_km",
        "weather_time_difference_minutes", "f", "fg",
        "temp_station_id", "temp_distance_km", "temp_time_diff_min",
        "temperature_c", "solar_elevation_deg", "daylight_class",
    }
    require(
        required_condition_columns <= set(conditions),
        "Accident conditions are missing required columns",
    )
    require(conditions["id"].is_unique, "Accident condition IDs are not unique")
    require(set(accidents["id"]) == set(conditions["id"]), "Event and condition IDs differ")
    accidents = accidents.merge(conditions, on="id", how="left", validate="one_to_one")
    accident_year = pd.to_datetime(accidents["timestamp"], errors="coerce").dt.year
    study_period = f"{int(accident_year.min())}--{int(accident_year.max())}"
    primary_mask = (
        accidents["weather_station_dist_km"].le(20)
        & accidents["weather_time_difference_minutes"].le(5)
        & accidents["f"].notna()
    )
    primary_accidents = int(primary_mask.sum())
    require(primary_accidents > 0, "No primary weather matches")
    temperature_mask = conditions["temperature_c"].notna()
    require(
        conditions.loc[temperature_mask, "temperature_c"].between(-30, 30).all(),
        "Temperature is outside the fixed QC range",
    )
    require(
        conditions.loc[
            temperature_mask,
            ["temp_station_id", "temp_distance_km", "temp_time_diff_min"],
        ].notna().all().all(),
        "A temperature value is missing match metadata",
    )
    require(
        conditions.loc[temperature_mask, "temp_distance_km"].le(20).all()
        and conditions.loc[temperature_mask, "temp_time_diff_min"].le(5).all(),
        "A temperature match exceeds the fixed distance or time limit",
    )
    temperature_accidents = int(temperature_mask.sum())
    require(
        temperature_accidents / len(conditions) >= 0.8,
        "Temperature coverage is below 80%",
    )
    temperature_result = pd.read_csv(temperature_path)
    expected_temperature_bins = [
        "<-6", "-6--3", "-3-0", "0-3", "3-6", "6-9", "9-12",
        "12-15", ">=15",
    ]
    require(
        temperature_result["temperature_interval_c"].tolist()
        == expected_temperature_bins,
        "Temperature O/E table does not use the documented bins",
    )
    require(
        int(temperature_result["observed_accidents"].sum()) == temperature_accidents
        and temperature_result["expected_accidents"].gt(0).all(),
        "Temperature O/E counts or exposure are incomplete",
    )

    weather = weather_checks(weather_audit_path)

    mean_wind = pd.read_csv(mean_wind_path)
    require(int(mean_wind["observed_accidents"].sum()) == primary_accidents, "Observed mean-wind counts do not sum to primary sample")
    require(
        np.isclose(mean_wind["expected_accidents"].sum(), primary_accidents, atol=0.2),
        "Rounded expected mean-wind counts do not sum to the primary sample",
    )
    highest = mean_wind.loc[mean_wind["mean_wind_interval_ms"].eq(">=25")].iloc[0]
    main_upper = mean_wind.loc[
        mean_wind["mean_wind_interval_ms"].eq("20-25")
    ].iloc[0]
    require(int(highest["observed_accidents"]) > 0, "No observed accidents in the highest mean-wind interval")
    require(float(highest["expected_accidents"]) > 0, "No expected accidents in the highest mean-wind interval")

    coverage = pd.read_csv(coverage_path).set_index("radius_km")
    for radius in [10, 20, 30]:
        require(radius in coverage.index, f"Missing {radius} km coverage")
        require(int(coverage.loc[radius, "analysed_accidents"]) > 0, f"No {radius} km coverage")

    oe_results = pd.read_csv(oe_results_path)
    radius_sensitivity = oe_results[
        oe_results["variable"].eq("fg")
        & oe_results["coarse_bin"].eq(">=35")
        & oe_results["severity_group"].eq("Injury accidents")
        & oe_results["analysis_season"].eq("All seasons")
        & oe_results["max_time_difference_minutes"].eq(5)
    ].set_index("radius_km")
    for radius in [10, 20, 30]:
        require(radius in radius_sensitivity.index, f"Missing gust distance result for {radius} km")
    return {
        "study_accidents": len(accidents), "study_period": study_period,
        "primary_accidents": primary_accidents,
        "temperature_accidents": temperature_accidents,
        "weather": weather, "highest": highest, "main_upper": main_upper,
        "coverage": coverage, "radius_sensitivity": radius_sensitivity,
        "_accidents": accidents, "_mean_wind": mean_wind,
        "_oe_results": oe_results,
    }
