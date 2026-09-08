"""Validate annual-road and daily-counter traffic results."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.validation.common import (
    DEFAULT_TEMPERATURE_RATE,
    DEFAULT_RATE_MODEL,
    DEFAULT_TRAFFIC_ALLOCATION_CHECK,
    DEFAULT_TRAFFIC_WIND,
    DEFAULT_VEHICLE_RATE_MULTIPLE,
    DEFAULT_VEHICLE_RATE_ONE,
    require,
)


def validate_traffic_models(
    daily_path: Path, daily_accident_weather_path: Path,
    traffic_audit_path: Path, rate_input_path: Path, rate_model_path: Path,
    rate_serious_path: Path, seasonal_rate_path: Path,
    seasonal_serious_path: Path,
) -> dict[str, object]:
    daily_rows: int | None = None
    daily_with_wind: int | None = None
    if daily_path.exists():
        if daily_path.suffix != ".csv":
            raise ValueError(f"Analysis input must be a CSV file: {daily_path}")
        daily = pd.read_csv(daily_path, usecols=["f_mean"])
        daily_rows = len(daily)
        daily_with_wind = int(daily["f_mean"].notna().sum())
        require(daily_rows > 0, "No daily counter-days")
        require(daily_with_wind > 0, "No daily counter-days with wind")

    daily_accident_weather = pd.read_csv(daily_accident_weather_path)
    required_daily_accident_columns = {
        "id", "counter_id", "counter_distance_km",
        "counter_weather_station_id", "counter_weather_station_dist_km",
        "counter_station_accident_distance_km",
        "weather_time_difference_minutes", "f",
    }
    require(
        required_daily_accident_columns <= set(daily_accident_weather),
        "Daily accident-weather input is incomplete",
    )
    require(
        daily_accident_weather["id"].is_unique,
        "Daily accident-weather input is not unique by accident",
    )
    usable_daily_accident_weather = daily_accident_weather[
        daily_accident_weather["f"].notna()
    ]
    require(
        usable_daily_accident_weather["counter_distance_km"].le(20).all()
        and usable_daily_accident_weather["counter_weather_station_dist_km"].le(20).all()
        and usable_daily_accident_weather[
            "counter_station_accident_distance_km"
        ].le(20).all()
        and usable_daily_accident_weather[
            "weather_time_difference_minutes"
        ].le(5).all(),
        "A same-station daily accident-weather match exceeds a fixed limit",
    )

    traffic_audit = pd.read_csv(traffic_audit_path).set_index("metric")
    required_traffic_metrics = {
        "section_years",
        "nonpositive_vdu",
        "nonpositive_derived_vhdu",
    }
    require(
        required_traffic_metrics <= set(traffic_audit.index),
        "Annual-traffic quality audit is incomplete",
    )

    rate_input = pd.read_csv(rate_input_path)
    required_rate_columns = {
        "injury_accidents", "serious_or_fatal_accidents", "estimated_vehicle_km",
    }
    require(required_rate_columns <= set(rate_input), "Rate-model input is incomplete")
    rate_model = pd.read_csv(rate_model_path)
    require(
        int(rate_model["observed_accidents"].sum()) == int(rate_input["injury_accidents"].sum()),
        "Rate-model counts do not sum to the compact rate-model input",
    )
    high_rate = rate_model.loc[rate_model["bin_label"].eq(">=25")].iloc[0]
    require(float(high_rate["time_proportional_rate_ratio"]) > 1, "High-wind rate ratio is not above one")
    rate_serious = pd.read_csv(rate_serious_path)
    require(
        int(rate_serious["observed_accidents"].sum())
        == int(rate_input["serious_or_fatal_accidents"].sum()),
        "Serious/fatal model counts do not sum to its canonical input",
    )
    seasonal_rate = pd.read_csv(seasonal_rate_path)
    require(
        set(seasonal_rate["season"]) == {"Winter", "Spring", "Summer", "Fall"}
        and set(seasonal_rate["bin_label"]) == {"0-10", "10-15", ">=15"}
        and seasonal_rate[seasonal_rate["bin_label"].eq(">=15")][
            "time_proportional_rate_ratio"
        ].gt(1).all(),
        "Season-specific mean-wind model is incomplete or has unexpected direction",
    )
    seasonal_serious = pd.read_csv(seasonal_serious_path)
    require(
        set(seasonal_serious["season"]) == {"Winter", "Spring", "Summer", "Fall"}
        and set(seasonal_serious["bin_label"]) == {"0-10", "10-15", ">=15"}
        and seasonal_serious["analysis_outcome"].eq("serious-fatal").all()
        and seasonal_serious["observed_accidents"].ge(0).all(),
        "Season-specific serious-or-fatal model is incomplete",
    )
    return {
        "daily_rows": daily_rows, "daily_with_wind": daily_with_wind,
        "traffic_audit": traffic_audit,
        "rate_accidents": int(rate_input["injury_accidents"].sum()),
        "high_rate": high_rate, "rate_serious": rate_serious,
        "seasonal_rate": seasonal_rate, "seasonal_serious": seasonal_serious,
    }


def validate_traffic_checks(
    radius_result_path: Path, traffic_checks_path: Path,
    daily_rate_path: Path, daily_rate_coarse_path: Path,
    daily_rate_radius_path: Path, daily_duration_path: Path,
    daily_allocated_path: Path, daily_sample_path: Path, daily_serious_path: Path,
    daily_07_24_path: Path, mean_wind: pd.DataFrame,
) -> dict[str, object]:
    radius_result = pd.read_csv(radius_result_path)
    require(len(radius_result) == 9, "Primary radius table must contain nine rows")
    primary_radius = radius_result[radius_result["primary_radius"]].sort_values("coarse_bin")
    primary_wind = mean_wind[
        mean_wind["mean_wind_interval_ms"].isin(primary_radius["coarse_bin"])
    ].sort_values("mean_wind_interval_ms")
    require(
        primary_radius["coarse_bin"].tolist()
        == primary_wind["mean_wind_interval_ms"].tolist()
        and np.allclose(
            primary_radius["relative_accident_frequency"],
            primary_wind["observed_expected_ratio"],
            atol=0.01,
        )
        and np.allclose(
            primary_radius["bootstrap_ci_95_low"],
            primary_wind["station_bootstrap_ci_95_low"],
            atol=0.01,
        )
        and np.allclose(
            primary_radius["bootstrap_ci_95_high"],
            primary_wind["station_bootstrap_ci_95_high"],
            atol=0.01,
        ),
        "Primary radius rows do not match the primary mean-wind table",
    )
    radius_20_25 = radius_result[radius_result["coarse_bin"].eq("20-25")]
    require(
        set(radius_20_25["radius_km"]) == {10, 20, 30}
        and radius_20_25["relative_accident_frequency"].gt(1).all(),
        "Primary 20--25 m/s radius sensitivity is incomplete or inconsistent",
    )
    traffic_checks = pd.read_csv(traffic_checks_path)
    official_20_25 = traffic_checks[
        traffic_checks["check"].eq("Rate model, 20-25 m/s")
        & traffic_checks["primary_or_full_scope"].str.contains("Official")
    ]
    require(
        len(official_20_25) == 1 and float(official_20_25.iloc[0]["estimate"]) > 1,
        "Official-period traffic sensitivity does not retain the high-wind pattern",
    )
    allocation_check = pd.read_csv(DEFAULT_TRAFFIC_ALLOCATION_CHECK)
    upper_check = allocation_check[
        allocation_check["bin_label"].isin(["15-20", "20-25", ">=25"])
    ]
    require(
        set(allocation_check["bin_label"])
        == {"0-5", "5-10", "10-15", "15-20", "20-25", ">=25"}
        and upper_check["illustrative_rate_ratio"].gt(
            upper_check["time_proportional_rate_ratio"]
        ).all(),
        "Traffic-allocation direction check is incomplete or has an unexpected direction",
    )
    daily_20_25 = traffic_checks[
        traffic_checks["check"].eq("Daily traffic, 20-25 m/s")
    ]
    require(
        len(daily_20_25) == 2
        and daily_20_25["estimate"].max() - daily_20_25["estimate"].min() < 2,
        "Zero-counter-day sensitivity changes the 20--25 m/s estimate materially",
    )
    daily_rate = pd.read_csv(daily_rate_path)
    require(
        daily_rate["wind_bin"].tolist() == ["0-5", "5-10", "10-15", "15-20", "20-25", ">=25"],
        "Detailed observed daily-rate table must use the standard bins",
    )
    daily_rate_coarse = pd.read_csv(daily_rate_coarse_path)
    require(
        daily_rate_coarse["wind_bin"].tolist() == ["0-10", "10-15", ">=15"],
        "Preferred observed daily-rate sensitivity must use the documented coarse bins",
    )
    for name, table in [("detailed", daily_rate), ("coarse", daily_rate_coarse)]:
        require(table["observed_vehicles"].gt(0).all(), f"{name} daily-rate exposure must be positive")
        estimated = table[table["ci_95_low"].notna()]
        require(
            estimated["ci_95_low"].le(estimated["rate_ratio"]).all()
            and estimated["rate_ratio"].le(estimated["ci_95_high"]).all(),
            f"{name} daily-rate confidence intervals are malformed",
        )
    require(
        daily_rate["model_accidents"].nunique() == 1
        and daily_rate_coarse["model_accidents"].nunique() == 1
        and int(daily_rate["model_accidents"].iloc[0])
        == int(daily_rate_coarse["model_accidents"].iloc[0])
        == int(daily_rate["observed_accidents"].sum())
        == int(daily_rate_coarse["observed_accidents"].sum()),
        "Detailed and coarse daily-rate tables must retain the same accidents",
    )
    daily_rate_high = daily_rate_coarse[daily_rate_coarse["wind_bin"].eq(">=15")].iloc[0]
    require(
        int(daily_rate_coarse["model_accidents"].iloc[0]) <= 1863
        and float(daily_rate_high["rate_ratio"]) > 1,
        "Observed daily-rate sensitivity has unexpected scope or direction",
    )
    daily_rate_radius = pd.read_csv(daily_rate_radius_path)
    require(
        set(daily_rate_radius["max_counter_distance_km"]) == {5, 10, 20}
        and set(daily_rate_radius["wind_bin"]) == {"10-15", ">=15"}
        and len(daily_rate_radius) == 6
        and daily_rate_radius["rate_ratio"].gt(0).all()
        and daily_rate_radius["ci_95_low"].le(daily_rate_radius["rate_ratio"]).all()
        and daily_rate_radius["rate_ratio"].le(daily_rate_radius["ci_95_high"]).all()
        and daily_rate_radius.groupby("max_counter_distance_km")["with_valid_counter_day"].first().is_monotonic_increasing,
        "Observed daily-rate distance sensitivity is incomplete or inconsistent",
    )
    daily_duration = pd.read_csv(daily_duration_path)
    require(
        daily_duration["hours_with_f_ge15"].tolist() == ["0", ">0-2", "2-6", ">=6"]
        and daily_duration["counter_days"].gt(0).all()
        and daily_duration["ci_95_low_pct"].le(daily_duration["relative_traffic_pct"]).all()
        and daily_duration["relative_traffic_pct"].le(daily_duration["ci_95_high_pct"]).all(),
        "Strong-wind-duration traffic table is incomplete or malformed",
    )
    daily_allocated = pd.read_csv(daily_allocated_path)
    require(
        daily_allocated["wind_bin"].tolist() == ["0-10", "10-15", ">=15"]
        and daily_allocated["estimated_vehicles_within_wind_bin"].gt(0).all()
        and int(daily_allocated["observed_accidents"].sum()) <= 1863,
        "Allocated daily-counter rate table has unexpected bins or scope",
    )
    allocated_estimates = daily_allocated[daily_allocated["ci_95_low"].notna()]
    require(
        allocated_estimates["ci_95_low"].le(allocated_estimates["rate_ratio"]).all()
        and allocated_estimates["rate_ratio"].le(allocated_estimates["ci_95_high"]).all(),
        "Allocated daily-counter confidence intervals are malformed",
    )
    temperature_rate = pd.read_csv(DEFAULT_TEMPERATURE_RATE)
    require(
        temperature_rate["bin_label"].tolist()
        == ["<-6", "-6--3", "-3-0", "0-3", "3-6", "6-9", "9-12", "12-15", ">=15"]
        and temperature_rate["reference_bin"].eq("0-3").all()
        and temperature_rate["time_proportional_rate_ratio"].gt(0).all()
        and int(temperature_rate["observed_accidents"].sum()) > 3000,
        "Temperature traffic-rate model has unexpected intervals or scope",
    )
    vehicle_rates = {
        "one": pd.read_csv(DEFAULT_VEHICLE_RATE_ONE),
        "two-plus": pd.read_csv(DEFAULT_VEHICLE_RATE_MULTIPLE),
    }
    main_rate = pd.read_csv(DEFAULT_RATE_MODEL)
    require(
        all(
            table["bin_label"].tolist() == ["0-10", "10-15", ">=15"]
            and table["analysis_outcome"].eq(outcome).all()
            and table["analysis_binning"].eq("coarse").all()
            and table["time_proportional_rate_ratio"].gt(0).all()
            for outcome, table in vehicle_rates.items()
        )
        and sum(int(table["observed_accidents"].sum()) for table in vehicle_rates.values())
        == int(main_rate["observed_accidents"].sum()),
        "Vehicle-group traffic-rate models are incomplete or inconsistent",
    )
    traffic_wind = pd.read_csv(DEFAULT_TRAFFIC_WIND)
    require(
        set(traffic_wind["scope"]) == {"All periods", "VDU", "SDU", "VHDU"}
        and traffic_wind.groupby("scope").size().eq(6).all()
        and traffic_wind["relative_traffic_pct"].gt(0).all(),
        "Traffic-period daily response table is incomplete or malformed",
    )
    daily_sample = pd.read_csv(daily_sample_path).set_index("group")
    expected_groups = {
        "All accidents", "No exact counter link", "Exact link, not retained",
        "Allocated-rate sample",
    }
    require(
        set(daily_sample.index) == expected_groups
        and int(daily_sample.loc["All accidents", "accidents"])
        == int(daily_sample.loc[list(expected_groups - {"All accidents"}), "accidents"].sum())
        and int(daily_sample.loc["Allocated-rate sample", "accidents"])
        == int(daily_allocated["observed_accidents"].sum()),
        "Daily-counter sample audit does not reproduce the allocated model selection",
    )
    daily_serious = pd.read_csv(daily_serious_path)
    daily_07_24 = pd.read_csv(daily_07_24_path)
    for name, table, outcome, window in [
        ("serious/fatal", daily_serious, "serious-fatal", "full-day"),
        ("07:00--24:00", daily_07_24, "injury", "07-24"),
    ]:
        require(
            table["wind_bin"].tolist() == ["0-10", "10-15", ">=15"]
            and table["analysis_outcome"].eq(outcome).all()
            and table["analysis_time_window"].eq(window).all()
            and table["estimated_vehicles_within_wind_bin"].gt(0).all(),
            f"Allocated daily {name} sensitivity is incomplete",
        )
    return {
        "radius_20_25": radius_20_25,
        "official_20_25": official_20_25.iloc[0],
        "allocation_check": allocation_check, "daily_20_25": daily_20_25,
        "daily_rate_high": daily_rate_high,
        "daily_rate_total": int(daily_rate_coarse["model_accidents"].iloc[0]),
        "daily_rate_radius": daily_rate_radius, "daily_duration": daily_duration,
        "daily_allocated": daily_allocated, "daily_sample": daily_sample,
        "temperature_rate": temperature_rate, "vehicle_rates": vehicle_rates,
        "traffic_wind": traffic_wind,
        "daily_serious": daily_serious,
        "daily_07_24": daily_07_24,
    }
