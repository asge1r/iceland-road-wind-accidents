"""Validate canonical accident, weather, and descriptive O/E tables."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.validation.common import require, weather_checks


def validate_weather(
    accidents_path: Path,
    conditions_path: Path,
    weather_audit_path: Path,
    weather_oe_path: Path,
) -> dict[str, object]:
    """Check the one weather O/E contract against its compact inputs."""
    accidents = pd.read_csv(accidents_path)
    conditions = pd.read_csv(conditions_path)
    require(len(accidents) > 0, "No rural injury accidents in canonical table")
    require(accidents["id"].is_unique, "Study accident IDs are not unique")
    require(conditions["id"].is_unique, "Accident condition IDs are not unique")
    require(set(accidents["id"]) == set(conditions["id"]), "Event and condition IDs differ")

    required = {
        "weather_station_id", "weather_station_dist_km",
        "weather_time_difference_minutes", "f", "fg", "temp_station_id",
        "temp_distance_km", "temp_time_diff_min", "temperature_c",
        "solar_elevation_deg", "daylight_class",
    }
    require(required <= set(conditions), "Accident conditions are missing required columns")
    combined = accidents.merge(conditions, on="id", how="left", validate="one_to_one")
    years = pd.to_datetime(combined["timestamp"], errors="raise").dt.year

    wind_match = (
        combined["weather_station_dist_km"].le(20)
        & combined["weather_time_difference_minutes"].le(5)
        & combined[["f", "fg"]].notna().all(axis=1)
    )
    temperature_match = (
        combined["temp_distance_km"].le(20)
        & combined["temp_time_diff_min"].le(5)
        & combined["temperature_c"].between(-30, 30)
    )
    require(wind_match.any(), "No qualifying wind matches")
    require(temperature_match.any(), "No qualifying temperature matches")

    result = pd.read_csv(weather_oe_path)
    result_required = {
        "variable", "outcome", "period", "bin_label", "bin_order",
        "observed_accidents", "expected_accidents",
        "relative_accident_frequency", "analysed_accidents",
        "max_distance_km", "max_time_difference_minutes",
    }
    require(result_required <= set(result), "Weather O/E table is incomplete")
    require(set(result["variable"]) == {"f", "fg", "temperature"}, "Weather O/E variables changed")
    require(
        set(result["outcome"]) == {"Minor injury accidents", "Severe/fatal accidents"},
        "Weather O/E outcomes changed",
    )
    require(
        set(result["period"]) == {"All year", "Winter", "Spring", "Summer", "Autumn"},
        "Weather O/E periods changed",
    )
    require(
        result["max_distance_km"].eq(20).all()
        and result["max_time_difference_minutes"].eq(5).all(),
        "Weather O/E match limits changed",
    )

    expected_matches = {
        "f": int(wind_match.sum()),
        "fg": int(wind_match.sum()),
        "temperature": int(temperature_match.sum()),
    }
    annual = result[result["period"].eq("All year")]
    for variable, matched in expected_matches.items():
        variable_rows = annual[annual["variable"].eq(variable)]
        for outcome in ["Minor injury accidents", "Severe/fatal accidents"]:
            rows = variable_rows[variable_rows["outcome"].eq(outcome)]
            require(len(rows) > 0, f"Missing annual {variable} O/E rows for {outcome}")
            require(
                np.isclose(rows["expected_accidents"].sum(), rows["observed_accidents"].sum()),
                f"Expected {variable} counts do not reconstruct {outcome}",
            )
        require(
            int(variable_rows["observed_accidents"].sum()) == matched,
            f"Annual {variable} outcome groups do not partition matched accidents",
        )

    main_upper = annual[
        annual["variable"].eq("f") & annual["bin_label"].eq(">=20")
    ]
    require(
        len(main_upper) == 2
        and main_upper["relative_accident_frequency"].gt(1).all(),
        "Upper mean-wind O/E rows are missing or no longer above one",
    )
    return {
        "study_accidents": len(accidents),
        "study_period": f"{int(years.min())}--{int(years.max())}",
        "primary_accidents": int(wind_match.sum()),
        "temperature_accidents": int(temperature_match.sum()),
        "weather": weather_checks(weather_audit_path),
        "main_upper": main_upper,
        "_accidents": combined,
        "_weather_oe": result,
    }
