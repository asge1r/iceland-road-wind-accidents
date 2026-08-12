"""Create the five small analysis-ready CSV inputs from local processed caches."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


SOURCE = Path("data/processed")
OUTPUT = Path("data/analysis")


def write_csv(data: pd.DataFrame, name: str, order: list[str]) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data[order].to_csv(OUTPUT / name, index=False)


def accidents() -> None:
    data = pd.read_parquet(SOURCE / "accidents/rural_injury_accidents.parquet", columns=[
        "nid", "timestamp", "meidsli", "tegohapps", "flokkur2", "urban_rural",
        "registered_road_section", "surface_code_set", "weather_station_id",
        "weather_station_dist_km", "weather_time_difference_minutes", "f", "fg", "t",
    ]).rename(columns={"registered_road_section": "road_section"})
    write_csv(data, "accidents.csv", list(data.columns))


def station_frequency() -> None:
    data = pd.read_parquet(SOURCE / "weather/wind_frequency_station_year_season.parquet")
    write_csv(data, "weather_station_frequency.csv", list(data.columns))


def annual_traffic() -> None:
    columns = ["year", "road_section", "section_length_km", "adu", "sdu", "vdu", "thousand_vehicle_km"]
    data = pd.read_csv(SOURCE / "traffic/annual_road_section_exposure.csv", usecols=columns)
    write_csv(data, "annual_traffic.csv", columns)


def daily_counter_wind() -> None:
    data = pd.read_parquet(SOURCE / "traffic/daily_traffic_wind_response.parquet", columns=[
        "counter_site_id", "traffic_period", "f_bin", "estimated_daytime_traffic",
        "expected_daytime_traffic",
    ])
    data = data[data["f_bin"].notna()].copy()
    data["f_bin"] = data["f_bin"].astype(str).replace({"24-27": ">=24", "27-30": ">=24", "30-33": ">=24"})
    grouped = data.groupby(["counter_site_id", "traffic_period", "f_bin"], as_index=False, observed=True).agg(
        observed_daytime_vehicles=("estimated_daytime_traffic", "sum"),
        expected_daytime_vehicles=("expected_daytime_traffic", "sum"),
        counter_days=("f_bin", "size"),
    )
    all_periods = grouped.groupby(["counter_site_id", "f_bin"], as_index=False).agg(
        observed_daytime_vehicles=("observed_daytime_vehicles", "sum"),
        expected_daytime_vehicles=("expected_daytime_vehicles", "sum"),
        counter_days=("counter_days", "sum"),
    )
    all_periods["traffic_period"] = "All periods"
    output = pd.concat([grouped, all_periods], ignore_index=True)
    write_csv(output, "daily_counter_wind.csv", ["counter_site_id", "traffic_period", "f_bin", "counter_days", "observed_daytime_vehicles", "expected_daytime_vehicles"])


def road_wind() -> None:
    # This is the final road-section traffic-adjustment input: one row per
    # variable and wind bin, already summed over the valid section/year/periods.
    data = pd.read_csv(Path("archive/generated_diagnostics/traffic_rates_sdu_vdu.csv"))
    write_csv(data, "road_wind.csv", list(data.columns))


def main() -> None:
    accidents(); station_frequency(); annual_traffic(); daily_counter_wind(); road_wind()
    print(f"Wrote five analysis-ready files to {OUTPUT}")


if __name__ == "__main__":
    main()
