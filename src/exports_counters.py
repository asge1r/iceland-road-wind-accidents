"""Export daily-counter inputs and selection summaries."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.export_common import ROOT, read_table, write_csv

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

def export_counter_sections(
    output: Path,
) -> tuple[str, int, list[str], str] | None:
    path = ROOT / "traffic/counter_sections.csv"
    if not path.exists():
        return None
    source = read_table(path)
    columns = [
        "year", "counter_section_id", "road_section",
        "counter_location_lat", "counter_location_lon",
        "counter_section_length_km", "weather_station_id",
        "weather_station_name", "weather_station_dist_km",
        "weather_station_within_limit", "counter_station_m",
        "counter_section_start_km", "counter_section_end_km",
        "source_station_min_m", "source_station_max_m", "channel_count",
        "source_fastnr",
    ]
    missing = set(columns) - set(source)
    if missing:
        raise ValueError(f"Counter sections are missing columns: {sorted(missing)}")
    table = source[columns].sort_values(
        ["year", "road_section", "counter_station_m"]
    )
    table["weather_station_id"] = pd.to_numeric(
        table["weather_station_id"], errors="coerce"
    ).astype("Int64")
    count = write_csv(table, output / "counter_sections.csv")
    return (
        "counter_sections.csv", count, columns,
        "Counter-section lengths, locations, source channels, and nearest weather stations.",
    )


def export_daily_vkt(
    output: Path,
) -> tuple[str, int, list[str], str] | None:
    path = ROOT / "traffic/daily_vkt.csv"
    if not path.exists():
        return None
    source = read_table(path)
    columns = [
        "variable", "outcome", "period", "bin_label", "bin_order", "accidents",
        "estimated_vehicle_km", "rate_per_100m_vehicle_km", "counter_days",
        "counter_sections", "allocation_method",
    ]
    missing = set(columns) - set(source)
    if missing:
        raise ValueError(f"Daily weather rate is missing columns: {sorted(missing)}")
    table = source[columns].sort_values(["variable", "outcome", "period", "bin_order"])
    count = write_csv(table, output / "daily_vkt.csv")
    return (
        "daily_vkt.csv", count, columns,
        "Same-day 07:00--24:00 counter-section accident rates per 100 million vehicle-km.",
    )

def export_selection_summary(output: Path) -> tuple[int, list[str]]:
    """Write the small count table used for the three data-selection figures."""
    all_accidents = read_table(ROOT / "accidents/all.csv")
    study = read_table(ROOT / "accidents/rural_injury.csv")
    study["year"] = pd.to_datetime(study["timestamp"], errors="raise").dt.year
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
    case_control = read_table(ROOT / "accidents/case_control.csv")
    matched_time = int(case_control.loc[case_control["case"].eq(1), "stratum_id"].nunique())
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
    model_accidents = int(read_table(ROOT / "accidents/rate.csv")["id"].nunique())
    annual_keys = read_table(ROOT / "traffic/annual.csv")[["year", "road_section"]].drop_duplicates()
    annual_keys["road_section"] = (
        annual_keys["road_section"].astype("string").str.strip().str.lower()
    )
    study_links = study.rename(columns={"registered_road_section": "road_section"}).copy()
    study_links["road_section"] = (
        study_links["road_section"].astype("string").str.strip().str.lower()
    )
    annual_links = int(
        study_links.merge(annual_keys, on=["year", "road_section"], how="inner")["id"]
        .nunique()
    )
    rural_2019_2024 = int(study["timestamp"].pipe(pd.to_datetime).dt.year.between(2019, 2024).sum())
    counter_assignments_path = ROOT / "accidents/accidents-near-counter.csv"
    counter_assignments = (
        len(read_table(counter_assignments_path)) if counter_assignments_path.exists() else 0
    )
    counter_accidents_path = ROOT / "traffic/counter_accidents.csv"
    counter_accidents = (
        len(read_table(counter_accidents_path)) if counter_accidents_path.exists() else 0
    )
    daily_vkt_path = ROOT / "traffic/daily_vkt.csv"
    daily_vkt_accidents = 0
    if daily_vkt_path.exists():
        daily_vkt = read_table(daily_vkt_path)
        annual_vkt = daily_vkt[
            daily_vkt["variable"].eq("f") & daily_vkt["period"].eq("All year")
        ]
        daily_vkt_accidents = int(annual_vkt["accidents"].sum())
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
            ("analysis_samples", "source_accidents", len(all_accidents)),
            ("analysis_samples", "rural_injury_2007_2025", len(study)),
            ("analysis_samples", "weather_oe", primary),
            ("analysis_samples", "matched_time", matched_time),
            ("analysis_samples", "annual_road_link", annual_links),
            ("analysis_samples", "annual_rate", model_accidents),
            ("analysis_samples", "rural_injury_2019_2024", rural_2019_2024),
            ("analysis_samples", "counter_section_assigned", counter_assignments),
            ("analysis_samples", "counter_accident_weather", counter_accidents),
            ("analysis_samples", "same_day_vkt", daily_vkt_accidents),
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
