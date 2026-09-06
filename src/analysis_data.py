"""Build the documented analysis CSVs used by tables and figures.

The small public entry point is ``src/export_tables.py``. This module keeps the
related source-specific export functions together so their column selections
and validation rules are inspectable in one place.
"""

from __future__ import annotations

import argparse
import calendar
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.solar import daylight_class, solar_elevation
from src.export_docs import write_manifest, write_readme


ROOT = Path("data/processed")

PERIOD_MONTHS = {
    "VDU": [12, 1, 2, 3],
    "SDU": [6, 7, 8, 9],
    "VHDU": [4, 5, 10, 11],
}


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required prepared file: {path}")
    return (
        pd.read_parquet(path)
        if path.suffix == ".parquet"
        else pd.read_csv(path, low_memory=False)
    )


def write_csv(frame: pd.DataFrame, path: Path) -> int:
    frame.to_csv(path, index=False)
    return len(frame)


def export_counter_validation(output: Path) -> tuple[int, list[str]]:
    source = read_table(ROOT / "traffic/daily_counter_station_validation.csv")
    columns = [
        "road_section", "station_id", "status", "official_station_m",
        "station_difference_m", "coordinate_difference_m",
    ]
    missing = set(columns) - set(source)
    if missing:
        raise ValueError(f"Counter validation is missing columns: {sorted(missing)}")
    table = source[columns].sort_values(["status", "road_section", "station_id"])
    return write_csv(table, output / "counter_check.csv"), columns


def export_weather_cleaning(output: Path) -> tuple[int, list[str]]:
    """Copy the compact cleaning summary into the canonical analysis layer."""
    source = read_table(ROOT / "weather/cleaning.csv")
    required = {
        "year", "input_rows", "no_wind_station_year", "missing_wind",
        "negative", "upper_threshold", "inconsistent_zero_gust",
        "gust_below_mean", "frozen_zero", "clean_wind_rows",
        "negative_f", "negative_fg", "f_at_or_above_45",
        "fg_at_or_above_65", "fg_zero_rows", "fg_zero_with_positive_f",
        "excluded_rows",
    }
    missing = required - set(source)
    if missing:
        raise ValueError(f"Weather cleaning summary is missing columns: {sorted(missing)}")
    columns = [column for column in source.columns if column in required]
    table = source[columns]
    return write_csv(table, output / "weather_cleaning.csv"), columns


def days_in_traffic_period(year: int, traffic_period: str) -> int:
    return sum(calendar.monthrange(int(year), month)[1] for month in PERIOD_MONTHS[traffic_period])


def season_from_month(month: pd.Series) -> pd.Series:
    season = pd.Series(index=month.index, dtype="object")
    season.loc[month.isin([12, 1, 2, 3])] = "Winter"
    season.loc[month.isin([4, 5])] = "Spring"
    season.loc[month.isin([6, 7, 8, 9])] = "Summer"
    season.loc[month.isin([10, 11])] = "Fall"
    return season


def traffic_period_from_month(month: pd.Series) -> pd.Series:
    period = pd.Series("VHDU", index=month.index, dtype="string")
    period.loc[month.isin(PERIOD_MONTHS["VDU"])] = "VDU"
    period.loc[month.isin(PERIOD_MONTHS["SDU"])] = "SDU"
    return period


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


def export_frequency(output: Path) -> tuple[int, list[str]]:
    source = read_table(ROOT / "weather/frequency.csv").copy()
    source = source[source["variable"].isin(["f", "fg", "temperature"])].copy()
    source["unit"] = source["variable"].map(
        {"f": "m/s", "fg": "m/s", "temperature": "deg C"}
    )
    group = ["station", "season", "variable", "bin_label", "unit"]
    counts = source.groupby(group, as_index=False, observed=True).agg(
        measurement_count=("measurement_count", "sum"),
        bin_lower=("bin_lower_value", "first"),
    )
    totals = source.groupby(
        ["station", "season", "variable", "unit"], as_index=False, observed=True
    ).agg(total_measurements_in_period=("total_measurements_in_period", "first"))
    tidy = counts.merge(
        totals, on=["station", "season", "variable", "unit"], how="left", validate="many_to_one"
    )
    tidy["frequency_pct"] = 100 * tidy["measurement_count"] / tidy["total_measurements_in_period"]
    columns = [
        "station", "season", "variable", "bin_label", "unit",
        "measurement_count", "total_measurements_in_period", "frequency_pct",
    ]
    tidy = tidy.sort_values(["station", "season", "variable", "bin_lower"])[columns]
    return write_csv(tidy, output / "weather_frequency.csv"), columns


def export_yearly_frequency(output: Path) -> tuple[int, list[str]]:
    source = read_table(ROOT / "weather/yearly_frequency.csv").copy()
    source = source[source["variable"].isin(["f", "temperature"])].copy()
    source["unit"] = source["variable"].map(
        {"f": "m/s", "temperature": "deg C"}
    )
    columns = [
        "station", "year", "season", "variable", "bin_label", "unit",
        "measurement_count", "total_measurements_in_period", "frequency_pct",
    ]
    missing = set(columns) - set(source)
    if missing:
        raise ValueError(f"Yearly weather frequency is missing columns: {sorted(missing)}")
    table = source.sort_values(
        ["station", "year", "season", "variable", "bin_lower_value"]
    )[columns]
    return write_csv(table, output / "weather_yearly.csv"), columns


def export_annual_traffic(output: Path) -> tuple[int, list[str]]:
    source = pd.read_csv(ROOT / "traffic/annual.csv", low_memory=False)
    columns = [column for column in ["year", "road_section", "section_length_km", "adu", "sdu", "vdu"] if column in source]
    return write_csv(source[columns], output / "annual_traffic.csv"), columns


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


def export_selection_summary(output: Path) -> tuple[int, list[str]]:
    """Write the small count table used for the three data-selection figures."""
    all_accidents = read_table(ROOT / "accidents/all.csv")
    study = read_table(ROOT / "accidents/rural_injury.csv")
    valid_coordinates = int(all_accidents["urban_rural"].ne("Unknown").sum())
    rural = int(all_accidents["urban_rural"].eq("Rural").sum())
    primary = int(
        (
            study["weather_station_dist_km"].le(20)
            & study["weather_time_difference_minutes"].le(5)
            & study["f"].notna()
            & study["fg"].notna()
        ).sum()
    )
    panel = read_table(ROOT / "traffic/road_period.csv")
    annual_total = int(panel[["year", "road_section", "traffic_period"]].drop_duplicates().shape[0])
    annual_wind = panel[
        panel["variable"].eq("f_5m")
        & panel["wind_frequency_available"].fillna(False)
        & panel["weather_station_id"].notna()
    ]
    annual_wind = int(
        annual_wind[["year", "road_section", "traffic_period"]].drop_duplicates().shape[0]
    )
    daily_path = ROOT / "traffic/daily_weather.csv"
    if daily_path.exists():
        daily = read_table(daily_path)
        daily_total = len(daily)
        daily_wind = int(daily["f_daytime_mean"].notna().sum())
    else:
        daily_total = 0
        daily_wind = 0
    summary = pd.DataFrame(
        [
            ("accidents", "valid_time_and_coordinates", valid_coordinates),
            ("accidents", "rural_accidents", rural),
            ("accidents", "rural_injury_accidents", len(study)),
            ("accidents", "primary_wind_oe_sample", primary),
            ("annual_traffic", "road_section_year_periods", annual_total),
            ("annual_traffic", "road_periods_with_wind", annual_wind),
            ("daily_traffic", "counter_days", daily_total),
            ("daily_traffic", "counter_days_with_daytime_wind", daily_wind),
        ],
        columns=["dataset", "step", "records"],
    )
    return write_csv(summary, output / "selection_summary.csv"), list(summary.columns)


def export_daily_traffic(
    output: Path,
) -> list[tuple[str, int, list[str], str]]:
    path = ROOT / "traffic/daily_weather.csv"
    if not path.exists():
        return []
    source = read_table(path).rename(columns={"station_id": "road_station_m"})
    text_columns = [
        "date", "counter_site_id", "traffic_volume", "f_daytime_mean",
        "f_full_day_mean", "weather_station_id",
        "full_observation_count", "f_full_bin_0_5_count", "f_full_bin_5_10_count",
        "f_full_bin_10_15_count", "f_full_bin_15_20_count",
        "f_full_bin_20_25_count", "f_full_bin_ge25_count",
        "active_07_24_observation_count", "f_07_24_bin_0_5_count",
        "f_07_24_bin_5_10_count", "f_07_24_bin_10_15_count",
        "f_07_24_bin_15_20_count", "f_07_24_bin_20_25_count",
        "f_07_24_bin_ge25_count",
    ]
    text_columns = [column for column in text_columns if column in source]
    readable = source[text_columns].sort_values(["counter_site_id", "date"])
    csv_columns = [
        "date", "counter_site_id", "traffic_volume", "f_daytime_mean",
        "f_full_day_mean", "weather_station_id",
        "full_observation_count", "f_full_bin_0_5_count", "f_full_bin_5_10_count",
        "f_full_bin_10_15_count", "f_full_bin_15_20_count",
        "f_full_bin_20_25_count", "f_full_bin_ge25_count",
        "active_07_24_observation_count", "f_07_24_bin_0_5_count",
        "f_07_24_bin_5_10_count", "f_07_24_bin_10_15_count",
        "f_07_24_bin_15_20_count", "f_07_24_bin_20_25_count",
        "f_07_24_bin_ge25_count",
    ]
    csv_columns = [column for column in csv_columns if column in readable]
    daily = readable[csv_columns].rename(
        columns={
            "counter_site_id": "counter_id",
            "traffic_volume": "traffic",
            "f_daytime_mean": "f_mean",
            "f_full_day_mean": "f_full_day_mean",
        }
    )
    if "traffic" in daily:
        daily["traffic"] = daily["traffic"].round().astype("Int64")
    count_columns = [column for column in daily if column.endswith("_count")]
    for column in ["weather_station_id", *count_columns]:
        daily[column] = pd.to_numeric(daily[column], errors="coerce").astype("Int64")
    for column in ["f_mean", "f_full_day_mean"]:
        daily[column] = pd.to_numeric(daily[column], errors="coerce").round(3)
    count = write_csv(daily, output / "daily_traffic.csv")
    locations = read_table(ROOT / "traffic/locations.csv")
    location_columns = [
        "year", "counter_site_id", "location_lon", "location_lat",
        "location_method", "location_is_estimated",
    ]
    missing = set(location_columns) - set(locations)
    if missing:
        raise ValueError(f"Daily counter locations are missing columns: {sorted(missing)}")
    locations = locations[location_columns].rename(
        columns={
            "counter_site_id": "counter_id",
            "location_lon": "lon",
            "location_lat": "lat",
        }
    )
    locations["road_section"] = (
        locations["counter_id"].astype("string").str.split(":").str[0]
    )
    locations = locations[
        [
            "year", "counter_id", "road_section", "lon", "lat",
            "location_method", "location_is_estimated",
        ]
    ].sort_values(["year", "counter_id"])
    if locations.duplicated(["year", "counter_id"]).any():
        raise ValueError("Daily counter locations are not unique by year and counter")
    location_count = write_csv(locations, output / "counter_locations.csv")
    return [
        (
            "daily_traffic.csv", count, list(daily.columns),
            "Optional large daily-counter table with observed traffic and mean-wind observation counts.",
        ),
        (
            "counter_locations.csv", location_count, list(locations.columns),
            "One estimated counter location per counter-site year.",
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=Path("data/analysis"), help="Output directory.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, int, list[str], str]] = []
    entries.extend(export_accident_tables(args.output))
    for filename, description, exporter in [
        ("weather_frequency.csv", "Station-season wind and temperature frequencies used as O/E denominators.", export_frequency),
        ("weather_yearly.csv", "Station-year-season mean-wind and temperature frequencies used for the year-adjusted O/E check.", export_yearly_frequency),
        ("weather_cleaning.csv", "Annual and total counts from the fixed weather-quality rules.", export_weather_cleaning),
        ("annual_traffic.csv", "Annual road-section traffic volumes and lengths.", export_annual_traffic),
        ("case_control.csv", "Time-stratified mean-wind, gust, and temperature samples.", export_case_control),
    ]:
        records, columns = exporter(args.output)
        entries.append((filename, records, columns, description))
    entries.extend(export_rate_tables(args.output))
    entries.append(export_season_rate_input(args.output))
    records, columns = export_selection_summary(args.output)
    entries.append(("selection_summary.csv", records, columns, "Counts used in data-selection figures."))
    daily_entries = export_daily_traffic(args.output)
    entries.extend(daily_entries)
    counter_validation = ROOT / "traffic/daily_counter_station_validation.csv"
    if counter_validation.exists():
        records, columns = export_counter_validation(args.output)
        entries.append(
            (
                "counter_check.csv", records, columns,
                "Estimated counter coordinates compared with official 20 m road-station points.",
            )
        )
    write_readme(args.output, bool(daily_entries))
    entries.append(("README.md", 0, ["file descriptions", "rebuild instruction"], "Description of the analysis data layer."))
    entries.append(("manifest.csv", len(entries) + 1, ["file", "records", "columns", "description"], "Inventory of the analysis data files."))
    write_manifest(args.output, entries)
    print(f"Wrote {len(entries)} analysis-layer files to {args.output}")


if __name__ == "__main__":
    main()
