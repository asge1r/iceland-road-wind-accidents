"""Export readable canonical analysis CSV files from prepared local data."""

from __future__ import annotations

import argparse
import calendar
from pathlib import Path

import numpy as np
import pandas as pd


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


def solar_elevation(timestamp: pd.Series, lat: pd.Series, lon: pd.Series) -> np.ndarray:
    """Approximate solar elevation for Icelandic local time (UTC year-round)."""
    time = pd.to_datetime(timestamp)
    day = time.dt.dayofyear.to_numpy(float)
    hour = (
        time.dt.hour.to_numpy(float)
        + time.dt.minute.to_numpy(float) / 60
        + time.dt.second.to_numpy(float) / 3600
    )
    gamma = 2 * np.pi / 365 * (day - 1 + (hour - 12) / 24)
    equation_of_time = 229.18 * (
        0.000075 + 0.001868 * np.cos(gamma) - 0.032077 * np.sin(gamma)
        - 0.014615 * np.cos(2 * gamma) - 0.040849 * np.sin(2 * gamma)
    )
    declination = (
        0.006918 - 0.399912 * np.cos(gamma) + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2 * gamma) + 0.000907 * np.sin(2 * gamma)
        - 0.002697 * np.cos(3 * gamma) + 0.00148 * np.sin(3 * gamma)
    )
    solar_minutes = hour * 60 + equation_of_time + 4 * lon.to_numpy(float)
    hour_angle = np.radians(solar_minutes / 4 - 180)
    latitude = np.radians(lat.to_numpy(float))
    cosine_zenith = (
        np.sin(latitude) * np.sin(declination)
        + np.cos(latitude) * np.cos(declination) * np.cos(hour_angle)
    )
    return 90 - np.degrees(np.arccos(np.clip(cosine_zenith, -1, 1)))


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
    source["gust_factor"] = np.where(source["f"].ge(3), source["fg"] / source["f"], np.nan)
    source["solar_elevation_deg"] = solar_elevation(
        source["timestamp"], source["lat"], source["lon"]
    )
    source["daylight_class"] = pd.cut(
        source["solar_elevation_deg"],
        bins=[-np.inf, -6, 0, np.inf],
        labels=["Darkness", "Civil twilight", "Daylight"],
        right=False,
    ).astype("string")
    events = [
        "id", "timestamp", "year", "month", "weekday", "hour", "lat", "lon",
        "meidsli", "tegohapps", "vehicle_count", "registered_road_section",
        "season", "traffic_period",
    ]
    conditions = [
        "id", "weather_station_id", "weather_station_dist_km",
        "weather_time_difference_minutes", "f", "fg", "gust_factor",
        "temp_station_id", "temp_distance_km", "temp_time_diff_min", "temperature_c",
        "solar_elevation_deg", "daylight_class",
    ]
    event_table = source[events].rename(columns={"registered_road_section": "road_section"})
    event_count = write_csv(event_table, output / "accidents.csv")
    condition_table = source[conditions]
    condition_count = write_csv(condition_table, output / "accident_conditions.csv")
    return [
        (
            "accidents.csv", event_count, list(event_table.columns),
            "Rural injury accident events with outcome, location, and calendar fields.",
        ),
        (
            "accident_conditions.csv", condition_count, list(condition_table.columns),
            "Independent wind and temperature matches plus astronomical daylight.",
        ),
    ]


def export_frequency(output: Path) -> tuple[int, list[str]]:
    source = read_table(ROOT / "weather/frequency.csv").copy()
    source = source[source["variable"].isin(["f", "fg", "gust_factor", "temperature"])].copy()
    source["unit"] = source["variable"].map(
        {"f": "m/s", "fg": "m/s", "gust_factor": "ratio", "temperature": "deg C"}
    )
    group = ["station", "season", "variable", "bin_label", "unit"]
    counts = source.groupby(group, as_index=False, observed=True).agg(
        measurement_count=("measurement_count", "sum"),
        bin_lower=("bin_lower_value", "first"),
    )
    totals = source.groupby(
        ["station", "year", "season", "variable", "unit"],
        as_index=False,
        observed=True,
    ).agg(total_measurements_in_period=("total_measurements_in_period", "first"))
    totals = totals.groupby(
        ["station", "season", "variable", "unit"], as_index=False, observed=True
    ).agg(total_measurements_in_period=("total_measurements_in_period", "sum"))
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

    ``traffic_exposure_full.csv`` retains all valid road exposure, aggregated to
    traffic period and wind interval. ``conditional_poisson_input.csv`` retains the complete
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
    keys = ["year", "road_section", "traffic_period", "weather_station_id", "bin_label"]
    if panel.duplicated(keys).any():
        raise ValueError("Road exposure has duplicate road-year-period-wind rows")

    accident_columns = [
        "id", "year", "road_section", "traffic_period", "rate_weather_station_id",
        "weather_time_difference_minutes", "rate_station_accident_distance_km", "f",
        "fg", "vehicle_group",
    ]
    accidents = read_table(accident_path)[accident_columns].copy()
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
    for column in ["injury_accidents", "one_vehicle_accidents", "multiple_vehicle_accidents"]:
        model[column] = model[column].fillna(0).astype(int)
    model = model.rename(columns={"bin_label": "wind_bin", "bin_lower_ms": "wind_bin_lower_ms"})[
        [
            "year", "road_section", "traffic_period", "weather_station_id", "wind_bin",
            "wind_bin_lower_ms", "estimated_vehicle_km", "injury_accidents",
            "one_vehicle_accidents", "multiple_vehicle_accidents",
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
    )
    summary = summary.merge(period_counts, on=["traffic_period", "wind_bin"], how="left")
    summary["injury_accidents"] = summary["injury_accidents"].fillna(0).astype(int)
    model_count = write_csv(model, output / "conditional_poisson_input.csv")
    summary_count = write_csv(
        summary.sort_values(["traffic_period", "wind_bin_lower_ms"]),
        output / "traffic_exposure_full.csv",
    )
    return [
        (
            "conditional_poisson_input.csv", model_count, list(model.columns),
            "Road-period wind exposure and matched accidents for the rate model.",
        ),
        (
            "traffic_exposure_full.csv", summary_count, list(summary.columns),
            "Vehicle-kilometres and injury accidents by traffic period and wind interval.",
        ),
    ]


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
        "fg_daytime_mean", "f_full_day_mean", "fg_full_day_mean",
        "full_observation_count", "f_full_bin_0_5_count", "f_full_bin_5_10_count",
        "f_full_bin_10_15_count", "f_full_bin_15_20_count",
        "f_full_bin_20_25_count", "f_full_bin_ge25_count",
    ]
    text_columns = [column for column in text_columns if column in source]
    readable = source[text_columns].sort_values(["counter_site_id", "date"])
    csv_columns = [
        "date", "counter_site_id", "traffic_volume", "f_daytime_mean",
        "fg_daytime_mean", "f_full_day_mean", "fg_full_day_mean",
        "full_observation_count", "f_full_bin_0_5_count", "f_full_bin_5_10_count",
        "f_full_bin_10_15_count", "f_full_bin_15_20_count",
        "f_full_bin_20_25_count", "f_full_bin_ge25_count",
    ]
    csv_columns = [column for column in csv_columns if column in readable]
    daily = readable[csv_columns].rename(
        columns={
            "counter_site_id": "counter_id",
            "traffic_volume": "traffic",
            "f_daytime_mean": "f_mean",
            "fg_daytime_mean": "fg_mean",
            "f_full_day_mean": "f_full_day_mean",
            "fg_full_day_mean": "fg_full_day_mean",
        }
    )
    if "traffic" in daily:
        daily["traffic"] = daily["traffic"].round().astype("Int64")
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
    location_count = write_csv(locations, output / "daily_counter_locations.csv")
    return [
        (
            "daily_traffic.csv", count, list(daily.columns),
            "Daily counter totals with wind summaries and full-day counts in six mean-wind intervals.",
        ),
        (
            "daily_counter_locations.csv", location_count, list(locations.columns),
            "One estimated counter location per counter-site year.",
        ),
    ]


def write_readme(output: Path, daily_present: bool) -> None:
    daily_text = (
        "`daily_traffic.csv` is included when the local daily PDF data are available."
        if daily_present
        else "Daily traffic data are added when the local daily PDF data are available."
    )
    accidents = pd.read_csv(output / "accidents.csv", usecols=["timestamp"])
    years = pd.to_datetime(accidents["timestamp"], errors="coerce").dt.year.dropna()
    period = f"{int(years.min())}–{int(years.max())}"
    text = f"""# Canonical analysis data

This directory is the only input layer used by the ordinary analysis scripts.
The files are generated during preparation and are deliberately CSV so that
they can be opened and checked directly. Do not edit them by hand.

- `accidents.csv`: the {period} rural injury-accident events, outcomes, locations, and calendar classifications.
- `accident_conditions.csv`: independently matched wind and temperature plus estimated astronomical daylight at each accident time.
- `weather_frequency.csv`: pooled 2007–2025 station-season wind and temperature counts. `f` and `fg` are in m/s; temperature is in degrees Celsius; `gust_factor` is the unitless ratio `fg / f` and is defined only when `f >= 3 m/s`.
- `case_control.csv`: accident times and same-hour, same-weekday control times for conditional logistic wind and temperature models.
- `annual_traffic.csv`: annual road-section traffic exposure (ADU, SDU and VDU).
- `conditional_poisson_input.csv`: compact road-section/year/traffic-period/wind-bin input for the conditional Poisson model.
- `traffic_exposure_full.csv`: 18 aggregated rows used for the descriptive accident-per-vehicle-km table.
- `selection_summary.csv`: counts for the accident and traffic selection figures.
- `daily_traffic.csv`: one daily counter total with wind summaries and full-day observation counts in six mean-wind intervals, 2019–2024.
- `daily_counter_locations.csv`: one geometry-interpolated location per counter-site year for the selected-counter analyses.
- {daily_text}
- `manifest.csv`: row counts, columns, and a short description of each analysis file.
"""
    (output / "README.md").write_text(text, encoding="utf-8")


def write_manifest(output: Path, entries: list[tuple[str, int, list[str], str]]) -> None:
    manifest = pd.DataFrame(entries, columns=["file", "records", "columns", "description"])
    manifest["columns"] = manifest["columns"].str.join(", ")
    manifest.to_csv(output / "manifest.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=Path("data/analysis"), help="Output directory.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, int, list[str], str]] = []
    entries.extend(export_accident_tables(args.output))
    for filename, description, exporter in [
        ("weather_frequency.csv", "Station-season wind and temperature frequencies used as O/E denominators.", export_frequency),
        ("annual_traffic.csv", "Annual road-section traffic volumes and lengths.", export_annual_traffic),
        ("case_control.csv", "Time-stratified wind and temperature case-crossover samples.", export_case_control),
    ]:
        records, columns = exporter(args.output)
        entries.append((filename, records, columns, description))
    entries.extend(export_rate_tables(args.output))
    records, columns = export_selection_summary(args.output)
    entries.append(("selection_summary.csv", records, columns, "Counts used in data-selection figures."))
    daily_entries = export_daily_traffic(args.output)
    entries.extend(daily_entries)
    write_readme(args.output, bool(daily_entries))
    entries.append(("README.md", 0, ["file descriptions", "rebuild instruction"], "Description of the analysis data layer."))
    entries.append(("manifest.csv", len(entries) + 1, ["file", "records", "columns", "description"], "Inventory of the analysis data files."))
    write_manifest(args.output, entries)
    print(f"Wrote {len(entries)} canonical files to {args.output}")


if __name__ == "__main__":
    main()
