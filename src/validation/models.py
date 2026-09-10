"""Validate matched-time, seasonal, daylight, and severity results."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.validation.common import (
    DEFAULT_DAYLIGHT,
    DEFAULT_JOINT_WEATHER,
    DEFAULT_SEASON_INTERACTION,
    DEFAULT_SEVERITY,
    require,
)


def validate_models(
    case_control_path: Path, case_control_result_path: Path,
    accidents: pd.DataFrame,
) -> dict[str, object]:
    case_control = pd.read_csv(case_control_path)
    require(
        {"exposure", "stratum_id", "case", "value", "controls_in_stratum"}
        <= set(case_control),
        "Case-crossover input is incomplete",
    )
    stratum_cases = case_control.groupby(["exposure", "stratum_id"])["case"].sum()
    require(stratum_cases.eq(1).all(), "Each case-crossover stratum must have one case")
    require(case_control["controls_in_stratum"].ge(1).all(), "A case-crossover stratum has no control")
    require(
        set(case_control["exposure"]) == {"mean_wind", "wind_gust", "temperature"},
        "Case-crossover input does not contain all three weather measures",
    )
    case_control_result = pd.read_csv(case_control_result_path)
    high_wind_case_control = case_control_result[
        case_control_result["exposure"].eq("mean_wind")
        & case_control_result["model"].eq("categorical")
        & case_control_result["comparison"].eq(">=15")
    ].iloc[0]
    require(
        float(high_wind_case_control["odds_ratio"]) > 1,
        "High-wind case-crossover odds ratio is not above one",
    )
    high_gust_case_control = case_control_result[
        case_control_result["exposure"].eq("wind_gust")
        & case_control_result["model"].eq("categorical")
        & case_control_result["comparison"].eq(">=30")
    ].iloc[0]
    require(
        float(high_gust_case_control["odds_ratio"]) > 1,
        "High-gust case-crossover odds ratio is not above one",
    )
    season_interaction = pd.read_csv(DEFAULT_SEASON_INTERACTION)
    omnibus = season_interaction[
        season_interaction["result"].eq("Season interaction test")
    ]
    seasonal_estimates = season_interaction[
        season_interaction["result"].eq("Season-specific estimate")
    ]
    require(
        len(omnibus) == 1
        and set(seasonal_estimates["season"])
        == {"Winter", "Spring", "Summer", "Autumn"}
        and int(omnibus.iloc[0]["degrees_of_freedom"]) == 6
        and 0 <= float(omnibus.iloc[0]["p_value"]) <= 1
        and seasonal_estimates["ci_95_low"].le(
            seasonal_estimates["odds_ratio"]
        ).all()
        and seasonal_estimates["odds_ratio"].le(
            seasonal_estimates["ci_95_high"]
        ).all(),
        "Matched wind-by-season comparison is incomplete or inconsistent",
    )
    weather_model = pd.read_csv(DEFAULT_JOINT_WEATHER)
    joint_high_wind = weather_model[
        weather_model["variable"].eq("Mean wind")
        & weather_model["comparison"].eq(">=15 m/s")
    ].iloc[0]
    require(
        int(joint_high_wind["strata"]) >= 5_000
        and float(joint_high_wind["adjusted_odds_ratio"]) > 1
        and float(joint_high_wind["ci_95_low"]) <= float(joint_high_wind["adjusted_odds_ratio"])
        <= float(joint_high_wind["ci_95_high"]),
        "Joint wind-temperature model is incomplete or inconsistent",
    )
    severity = pd.read_csv(DEFAULT_SEVERITY)
    complete_severity_sample = int(
        (
            accidents["f"].notna()
            & accidents["weather_station_dist_km"].le(20)
            & accidents["weather_time_difference_minutes"].le(5)
            & accidents["temperature_c"].notna()
            & accidents["temp_distance_km"].le(20)
            & accidents["temp_time_diff_min"].le(5)
            & accidents["daylight_class"].notna()
        ).sum()
    )
    require(
        set(severity["predictor"])
        == {"Mean wind", "Temperature", "Daylight", "Time of day", "Season"}
        and severity["accidents"].nunique() == 1
        and int(severity["accidents"].iloc[0]) == complete_severity_sample
        and severity["ci_95_low"].le(severity["odds_ratio"]).all()
        and severity["odds_ratio"].le(severity["ci_95_high"]).all(),
        "Severity-composition model is incomplete or inconsistent",
    )
    daylight = pd.read_csv(DEFAULT_DAYLIGHT)
    require(
        daylight["comparison"].tolist() == ["Darkness", "Civil twilight"]
        and daylight["reference"].eq("Daylight").all()
        and int(daylight["total_strata"].iloc[0]) == len(accidents)
        and int(daylight["informative_strata"].iloc[0]) > 0,
        "Matched daylight comparison is incomplete",
    )
    return {
        "high_wind_case_control": high_wind_case_control,
        "high_gust_case_control": high_gust_case_control,
        "season_interaction": season_interaction,
        "joint_high_wind": joint_high_wind,
        "severity": severity, "daylight": daylight,
    }
