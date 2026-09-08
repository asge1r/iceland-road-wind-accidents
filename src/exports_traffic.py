"""Export annual and road-period traffic analysis tables."""

from __future__ import annotations

import calendar
from pathlib import Path

import numpy as np
import pandas as pd

from src.export_common import ROOT, PERIOD_MONTHS, days_in_traffic_period, read_table, write_csv
from src.weather.frequency import TEMPERATURE_LABELS, TEMPERATURE_THRESHOLDS

def export_annual_traffic(output: Path) -> tuple[int, list[str]]:
    source = pd.read_csv(ROOT / "traffic/annual.csv", low_memory=False)
    columns = [column for column in ["year", "road_section", "section_length_km", "adu", "sdu", "vdu"] if column in source]
    return write_csv(source[columns], output / "annual_traffic.csv"), columns

def export_rate_tables(output: Path) -> list[tuple[str, int, list[str], str]]:
    """Write the two compact CSV inputs used by the vehicle-kilometre results.

    ``road_exposure.csv`` retains all valid road exposure, aggregated to
    traffic period and wind interval. ``road_rate.csv`` retains the complete
    within-road/year/period strata only where at least one matched accident
    occurred; all-zero strata do not contribute information to a conditional
    Poisson model.
    """
    panel_path = ROOT / "traffic/road_period.csv"
    accident_path = ROOT / "accidents/rate.csv"
    panel_columns = [
        "year", "road_section", "traffic_period", "weather_station_id", "variable",
        "bin_label", "bin_lower_ms", "frequency_pct", "wind_frequency_available",
        "section_length_km", "traffic_reference_daily_volume",
    ]
    panel = read_table(panel_path)[panel_columns].copy()
    panel = panel[
        panel["variable"].eq("f_5m")
        & panel["wind_frequency_available"].fillna(False)
        & panel["weather_station_id"].notna()
        & panel["section_length_km"].gt(0)
        & panel["traffic_reference_daily_volume"].gt(0)
        & panel["frequency_pct"].notna()
    ].copy()
    panel["road_section"] = panel["road_section"].astype("string").str.strip().str.lower()
    panel["weather_station_id"] = pd.to_numeric(
        panel["weather_station_id"], errors="raise"
    ).astype("Int64")
    panel["period_days"] = [
        days_in_traffic_period(year, period)
        for year, period in zip(panel["year"], panel["traffic_period"], strict=True)
    ]
    panel["estimated_vehicle_km"] = (
        panel["traffic_reference_daily_volume"]
        * panel["section_length_km"]
        * panel["period_days"]
        * panel["frequency_pct"]
        / 100
    )
    exposure_groups = [
        "year", "road_section", "traffic_period", "weather_station_id"
    ]

    frequency_totals = panel.groupby(exposure_groups)["frequency_pct"].sum()
    bad_frequency = ~np.isclose(
        frequency_totals.to_numpy(float), 100.0, atol=1e-6
    )
    if bad_frequency.any():
        examples = frequency_totals[bad_frequency].head().to_dict()
        raise ValueError(
            "Road-period wind frequencies do not sum to 100%; "
            f"examples={examples}"
        )

    expected_period_vehicle_km = (
        panel["traffic_reference_daily_volume"]
        * panel["section_length_km"]
        * panel["period_days"]
    )

    reconstructed = panel.groupby(exposure_groups)["estimated_vehicle_km"].sum()
    target = expected_period_vehicle_km.groupby(
        [panel[column] for column in exposure_groups]
    ).first()
    if not np.allclose(
        reconstructed.to_numpy(float),
        target.to_numpy(float),
        rtol=1e-10,
        atol=1e-6,
    ):
        raise ValueError(
            "Wind-bin vehicle-kilometres do not reconstruct period exposure"
        )
    keys = ["year", "road_section", "traffic_period", "weather_station_id", "bin_label"]
    if panel.duplicated(keys).any():
        raise ValueError("Road exposure has duplicate road-year-period-wind rows")

    accident_columns = [
        "id", "year", "road_section", "traffic_period", "rate_weather_station_id",
        "weather_time_difference_minutes", "rate_station_accident_distance_km", "f",
        "fg", "vehicle_group",
    ]
    accidents = read_table(accident_path)[accident_columns].copy()
    severity = read_table(ROOT / "accidents/rural_injury.csv")[["id", "meidsli"]]
    if severity["id"].duplicated().any():
        raise ValueError("Prepared accident severity is not unique by id")
    accidents = accidents.merge(severity, on="id", how="left", validate="one_to_one")
    accidents["meidsli"] = pd.to_numeric(accidents["meidsli"], errors="raise")
    accidents["road_section"] = accidents["road_section"].astype("string").str.strip().str.lower()
    accidents = accidents[
        accidents["weather_time_difference_minutes"].le(5)
        & accidents["rate_station_accident_distance_km"].le(20)
        & accidents["f"].between(0, 45, inclusive="left")
        & accidents["fg"].between(0, 65, inclusive="left")
        & accidents["fg"].add(0.5).ge(accidents["f"])
    ].copy()
    stations = panel[["year", "road_section", "traffic_period", "weather_station_id"]].drop_duplicates()
    accidents = accidents.merge(
        stations,
        on=["year", "road_section", "traffic_period"],
        how="inner",
        validate="many_to_one",
    )
    if not accidents["rate_weather_station_id"].eq(accidents["weather_station_id"]).all():
        raise ValueError("Accident and exposure rows use different weather stations")
    bins = panel[["bin_label", "bin_lower_ms"]].drop_duplicates().sort_values("bin_lower_ms")
    accidents["wind_bin"] = pd.cut(
        accidents["f"],
        bins=[*bins["bin_lower_ms"].to_numpy(float), float("inf")],
        labels=bins["bin_label"].tolist(),
        right=False,
        include_lowest=True,
    ).astype("string")
    count_keys = ["year", "road_section", "traffic_period", "wind_bin"]
    counts = accidents.groupby(count_keys, as_index=False).agg(
        injury_accidents=("id", "nunique"),
        serious_or_fatal_accidents=("meidsli", lambda values: values.le(2).sum()),
        one_vehicle_accidents=("vehicle_group", lambda values: values.eq("1 vehicle").sum()),
        multiple_vehicle_accidents=("vehicle_group", lambda values: values.eq("2 or more vehicles").sum()),
    )
    model_strata = counts[["year", "road_section", "traffic_period"]].drop_duplicates()
    model = panel.merge(
        model_strata,
        on=["year", "road_section", "traffic_period"],
        how="inner",
        validate="many_to_one",
    ).merge(
        counts,
        left_on=["year", "road_section", "traffic_period", "bin_label"],
        right_on=count_keys,
        how="left",
        validate="one_to_one",
    )
    model = model.drop(columns="wind_bin")
    for column in [
        "injury_accidents", "serious_or_fatal_accidents",
        "one_vehicle_accidents", "multiple_vehicle_accidents",
    ]:
        model[column] = model[column].fillna(0).astype(int)
    model = model.rename(columns={"bin_label": "wind_bin", "bin_lower_ms": "wind_bin_lower_ms"})[
        [
            "year", "road_section", "traffic_period", "weather_station_id", "wind_bin",
            "wind_bin_lower_ms", "estimated_vehicle_km", "injury_accidents",
            "serious_or_fatal_accidents", "one_vehicle_accidents",
            "multiple_vehicle_accidents",
        ]
    ].sort_values(["year", "road_section", "traffic_period", "wind_bin_lower_ms"])
    model = model[model["estimated_vehicle_km"].gt(0)].copy()
    summary = panel.groupby(["traffic_period", "bin_label", "bin_lower_ms"], as_index=False).agg(
        estimated_vehicle_km=("estimated_vehicle_km", "sum"),
    ).rename(columns={"bin_label": "wind_bin", "bin_lower_ms": "wind_bin_lower_ms"})
    total_counts = counts.groupby("wind_bin", as_index=False).agg(
        injury_accidents=("injury_accidents", "sum"),
    )
    period_counts = accidents.groupby(["traffic_period", "wind_bin"], as_index=False).agg(
        injury_accidents=("id", "nunique"),
        serious_or_fatal_accidents=("meidsli", lambda values: values.le(2).sum()),
    )
    summary = summary.merge(period_counts, on=["traffic_period", "wind_bin"], how="left")
    summary["injury_accidents"] = summary["injury_accidents"].fillna(0).astype(int)
    summary["serious_or_fatal_accidents"] = (
        summary["serious_or_fatal_accidents"].fillna(0).astype(int)
    )
    model_count = write_csv(model, output / "road_rate.csv")
    summary_count = write_csv(
        summary.sort_values(["traffic_period", "wind_bin_lower_ms"]),
        output / "road_exposure.csv",
    )
    return [
        (
            "road_rate.csv", model_count, list(model.columns),
            "Road-period wind exposure and matched accidents for the rate model.",
        ),
        (
            "road_exposure.csv", summary_count, list(summary.columns),
            "Vehicle-kilometres and injury accidents by traffic period and wind interval.",
        ),
    ]

def export_temperature_rate_input(output: Path) -> tuple[str, int, list[str], str]:
    """Write the same-station temperature and estimated-traffic model input."""
    panel_columns = [
        "year", "road_section", "traffic_period", "weather_station_id",
        "section_length_km", "traffic_reference_daily_volume", "variable",
        "wind_frequency_available",
    ]
    panel = read_table(ROOT / "traffic/road_period.csv")[panel_columns]
    panel = panel[
        panel["variable"].eq("f_5m")
        & panel["wind_frequency_available"].fillna(False)
        & panel["weather_station_id"].notna()
        & panel["section_length_km"].gt(0)
        & panel["traffic_reference_daily_volume"].gt(0)
    ].drop_duplicates().copy()
    panel["road_section"] = panel["road_section"].astype("string").str.strip().str.lower()
    panel["weather_station_id"] = pd.to_numeric(
        panel["weather_station_id"], errors="raise"
    ).astype(int)

    frequency = read_table(ROOT / "weather/yearly_frequency.csv")
    required = {
        "station", "year", "season", "variable", "bin_label",
        "bin_lower_value", "measurement_count", "total_measurements_in_period",
    }
    missing = required - set(frequency)
    if missing:
        raise ValueError(f"Temperature frequency is missing columns: {sorted(missing)}")
    frequency = frequency[frequency["variable"].eq("temperature")].copy()
    frequency["traffic_period"] = frequency["season"].map(
        {"Winter": "VDU", "Spring": "VHDU", "Summer": "SDU", "Fall": "VHDU"}
    )
    season_totals = frequency.groupby(
        ["station", "year", "season", "traffic_period"], as_index=False
    )["total_measurements_in_period"].first()
    available = season_totals.groupby(
        ["station", "year", "traffic_period"], as_index=False
    ).agg(
        available_seasons=("season", "nunique"),
        temperature_measurements=("total_measurements_in_period", "sum"),
    )
    expected_seasons = available["traffic_period"].map(
        {"VDU": 1, "SDU": 1, "VHDU": 2}
    )
    available = available[available["available_seasons"].eq(expected_seasons)]
    frequency = frequency.groupby(
        ["station", "year", "traffic_period", "bin_label", "bin_lower_value"],
        as_index=False,
    )["measurement_count"].sum().merge(
        available,
        on=["station", "year", "traffic_period"],
        how="inner",
        validate="many_to_one",
    )
    frequency["frequency_fraction"] = (
        frequency["measurement_count"] / frequency["temperature_measurements"]
    )
    frequency = frequency.rename(columns={"station": "weather_station_id"})
    exposure = panel.merge(
        frequency[
            [
                "weather_station_id", "year", "traffic_period", "bin_label",
                "bin_lower_value", "frequency_fraction",
            ]
        ],
        on=["weather_station_id", "year", "traffic_period"],
        how="inner",
        validate="many_to_many",
    )
    exposure["period_days"] = [
        days_in_traffic_period(year, period)
        for year, period in zip(exposure["year"], exposure["traffic_period"], strict=True)
    ]
    exposure["estimated_vehicle_km"] = (
        exposure["traffic_reference_daily_volume"]
        * exposure["section_length_km"]
        * exposure["period_days"]
        * exposure["frequency_fraction"]
    )
    exposure_keys = ["year", "road_section", "traffic_period", "weather_station_id"]
    frequency_totals = exposure.groupby(exposure_keys)["frequency_fraction"].sum()
    if not np.allclose(frequency_totals.to_numpy(float), 1.0, atol=1e-10):
        raise ValueError("Temperature frequencies do not reconstruct period exposure")

    accidents = read_table(ROOT / "accidents/rate.csv")
    accident_columns = [
        "id", "year", "road_section", "traffic_period", "rate_weather_station_id",
        "temperature_c",
    ]
    missing = set(accident_columns) - set(accidents)
    if missing:
        raise ValueError(
            "Rebuild src.traffic.rate_weather before exporting temperature rates; "
            f"missing={sorted(missing)}"
        )
    accidents = accidents[accident_columns].copy()
    accidents["road_section"] = accidents["road_section"].astype("string").str.strip().str.lower()
    accidents = accidents[
        accidents["temperature_c"].between(-30, 30, inclusive="both")
    ].copy()
    stations = exposure[exposure_keys].drop_duplicates()
    accidents = accidents.merge(
        stations,
        on=["year", "road_section", "traffic_period"],
        how="inner",
        validate="many_to_one",
    )
    if not accidents["rate_weather_station_id"].eq(
        accidents["weather_station_id"]
    ).all():
        raise ValueError("Temperature accident and exposure stations differ")
    accidents["temperature_bin"] = pd.cut(
        accidents["temperature_c"],
        [-np.inf, *TEMPERATURE_THRESHOLDS, np.inf],
        labels=TEMPERATURE_LABELS,
        right=False,
    ).astype("string")
    count_keys = ["year", "road_section", "traffic_period", "temperature_bin"]
    counts = accidents.groupby(count_keys, as_index=False).agg(
        injury_accidents=("id", "nunique")
    )
    strata = counts[["year", "road_section", "traffic_period"]].drop_duplicates()
    model = exposure.merge(
        strata,
        on=["year", "road_section", "traffic_period"],
        how="inner",
        validate="many_to_one",
    ).merge(
        counts,
        left_on=["year", "road_section", "traffic_period", "bin_label"],
        right_on=count_keys,
        how="left",
        validate="one_to_one",
    )
    model["injury_accidents"] = model["injury_accidents"].fillna(0).astype(int)
    model = model.drop(columns="temperature_bin").rename(
        columns={
            "bin_label": "temperature_bin",
            "bin_lower_value": "temperature_bin_lower_c",
        }
    )
    columns = [
        "year", "road_section", "traffic_period", "weather_station_id",
        "temperature_bin", "temperature_bin_lower_c", "estimated_vehicle_km",
        "injury_accidents",
    ]
    model = model[columns].sort_values(
        ["year", "road_section", "traffic_period", "temperature_bin_lower_c"]
    )
    count = write_csv(model, output / "road_temperature.csv")
    return (
        "road_temperature.csv", count, columns,
        "Road-period temperature exposure and matched accidents for the secondary rate model.",
    )

def export_season_rate_input(output: Path) -> tuple[str, int, list[str], str]:
    """Write a compact year-specific seasonal mean-wind rate-model input."""
    panel_columns = [
        "year", "road_section", "traffic_period", "weather_station_id",
        "section_length_km", "traffic_reference_daily_volume", "variable",
        "wind_frequency_available",
    ]
    panel = read_table(ROOT / "traffic/road_period.csv")[panel_columns]
    panel = panel[
        panel["variable"].eq("f_5m")
        & panel["wind_frequency_available"].fillna(False)
        & panel["weather_station_id"].notna()
        & panel["section_length_km"].gt(0)
        & panel["traffic_reference_daily_volume"].gt(0)
    ].drop_duplicates().copy()
    period_seasons = pd.DataFrame(
        [("VDU", "Winter"), ("VHDU", "Spring"), ("SDU", "Summer"), ("VHDU", "Fall")],
        columns=["traffic_period", "season"],
    )
    panel = panel.merge(period_seasons, on="traffic_period", how="inner", validate="many_to_many")
    panel["road_section"] = panel["road_section"].astype("string").str.strip().str.lower()
    panel["weather_station_id"] = pd.to_numeric(panel["weather_station_id"], errors="raise").astype(int)

    frequency = read_table(ROOT / "weather/traffic_frequency.csv")
    required_frequency = {
        "station", "year", "season", "variable", "bin_label",
        "bin_lower_value", "measurement_count", "total_measurements_in_period",
    }
    missing = required_frequency - set(frequency)
    if missing:
        raise ValueError(f"Seasonal weather frequency is missing columns: {sorted(missing)}")
    frequency = frequency[frequency["variable"].eq("f")].rename(
        columns={"station": "weather_station_id", "bin_lower_value": "wind_bin_lower_ms"}
    )
    frequency["frequency_fraction"] = (
        frequency["measurement_count"] / frequency["total_measurements_in_period"]
    )
    exposure = panel.merge(
        frequency[
            ["weather_station_id", "year", "season", "bin_label",
             "wind_bin_lower_ms", "frequency_fraction"]
        ],
        on=["weather_station_id", "year", "season"],
        how="inner", validate="many_to_many",
    )
    season_months = {
        "Winter": [12, 1, 2, 3], "Spring": [4, 5],
        "Summer": [6, 7, 8, 9], "Fall": [10, 11],
    }
    exposure["season_days"] = [
        sum(calendar.monthrange(int(year), month)[1] for month in season_months[season])
        for year, season in zip(exposure["year"], exposure["season"], strict=True)
    ]
    exposure["estimated_vehicle_km"] = (
        exposure["traffic_reference_daily_volume"]
        * exposure["section_length_km"]
        * exposure["season_days"]
        * exposure["frequency_fraction"]
    )

    rate = read_table(ROOT / "accidents/rate.csv")
    severity = read_table(ROOT / "accidents/rural_injury.csv")[["id", "meidsli"]]
    rate = rate.merge(severity, on="id", how="left", validate="one_to_one")
    rate["timestamp"] = pd.to_datetime(rate["timestamp"], errors="raise")
    rate["season"] = rate["timestamp"].dt.month.map(
        {12: "Winter", 1: "Winter", 2: "Winter", 3: "Winter", 4: "Spring",
         5: "Spring", 6: "Summer", 7: "Summer", 8: "Summer", 9: "Summer",
         10: "Fall", 11: "Fall"}
    )
    rate["road_section"] = rate["road_section"].astype("string").str.strip().str.lower()
    rate["wind_bin"] = pd.cut(
        rate["f"], [0, 5, 10, 15, 20, 25, np.inf],
        labels=["0-5", "5-10", "10-15", "15-20", "20-25", ">=25"],
        right=False, include_lowest=True,
    ).astype("string")
    counts = rate.groupby(
        ["year", "road_section", "season", "wind_bin"],
        observed=True, as_index=False,
    ).agg(
        injury_accidents=("id", "nunique"),
        serious_or_fatal_accidents=("meidsli", lambda values: values.le(2).sum()),
    )
    strata = counts[["year", "road_section", "season"]].drop_duplicates()
    model = exposure.merge(
        strata, on=["year", "road_section", "season"],
        how="inner", validate="many_to_one",
    ).merge(
        counts,
        left_on=["year", "road_section", "season", "bin_label"],
        right_on=["year", "road_section", "season", "wind_bin"],
        how="left", validate="one_to_one",
    )
    model = model.drop(columns="wind_bin").rename(columns={"bin_label": "wind_bin"})
    for column in ["injury_accidents", "serious_or_fatal_accidents"]:
        model[column] = model[column].fillna(0).astype(int)
    columns = [
        "year", "road_section", "season", "weather_station_id", "wind_bin",
        "wind_bin_lower_ms", "estimated_vehicle_km", "injury_accidents",
        "serious_or_fatal_accidents",
    ]
    model = model[columns].sort_values(
        ["year", "road_section", "season", "wind_bin_lower_ms"]
    )
    count = write_csv(model, output / "road_seasons.csv")
    return (
        "road_seasons.csv", count, columns,
        "Year-specific road-section seasonal mean-wind exposure and matched accidents.",
    )
