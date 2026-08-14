"""Create the five small, human-readable working tables.

The detailed files under ``data/processed/{accidents,weather,traffic}`` remain
pipeline caches.  This module deliberately exports only the columns used for
analysis or routine inspection. ``daily.txt`` is a deliberately shorter
tab-separated inspection table in the style of the earlier Drive layout.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


ROOT = Path("data/processed")
ACCIDENT_SOURCE = ROOT / "accidents/rural_injury_accidents.parquet"
WEATHER_SOURCE = ROOT / "weather/weather_10min_clean.parquet"
STATION_SOURCE = ROOT / "weather/stations.csv"
ANNUAL_SOURCE = ROOT / "traffic/annual_road_section_exposure.csv"
DAILY_SOURCE = ROOT / "traffic/daily_traffic_weather.parquet"


def write_accidents() -> None:
    columns = {
        "nid": "nid", "timestamp": "timestamp", "date": "date",
        "hour": "hour", "lat": "lat", "lon": "lon",
        "meidsli": "meidsli", "severity": "severity", "tegohapps": "tegohapps",
        "flokkur2": "flokkur2", "urban_rural": "urban_rural",
        "registered_road_section": "road_section",
        "weather_station_id": "weather_station_id", "weather_station_dist_km": "weather_station_dist_km",
        "f": "f", "fg": "fg", "t": "t",
    }
    data = pd.read_parquet(ACCIDENT_SOURCE, columns=list(columns)).rename(columns=columns)
    data["year"] = pd.to_datetime(data["date"]).dt.year
    data.sort_values(["timestamp", "nid"]).to_csv(ROOT / "accidents.csv", index=False)


def link_weather() -> None:
    """Expose the clean five-column weather table without copying ~2 GB."""
    output = ROOT / "weather.parquet"
    if output.exists() or output.is_symlink():
        output.unlink()
    os.link(WEATHER_SOURCE, output)


def write_stations() -> None:
    data = pd.read_csv(STATION_SOURCE, usecols=["station", "name", "lat", "lon", "start", "ending"])
    data.sort_values("station").to_csv(ROOT / "stations.csv", index=False)


def write_annual_traffic() -> None:
    columns = ["year", "road_section", "section_length_km", "adu", "sdu", "vdu", "thousand_vehicle_km"]
    data = pd.read_csv(ANNUAL_SOURCE, usecols=columns)
    data.sort_values(["year", "road_section"]).to_csv(ROOT / "annual_traffic.csv", index=False)


def write_daily_traffic() -> None:
    columns = [
        "date", "year", "counter_site_id", "road_section", "station_id", "traffic_volume",
        "location_lat", "location_lon", "location_method", "weather_station_id",
        "weather_station_dist_km", "f_daytime_mean", "fg_daytime_max", "month", "weekday",
    ]
    data = pd.read_parquet(DAILY_SOURCE, columns=columns).rename(
        columns={"location_lat": "lat", "location_lon": "lon"}
    )
    data = data.sort_values(["counter_site_id", "date"])
    data.to_csv(ROOT / "daily_traffic.csv", index=False)
    # Keep this deliberately small. Year/month/weekday and the composite site
    # ID can be recreated from date, road section and PDF station. Location
    # diagnostics remain in daily_traffic.csv rather than this inspection file.
    drive_columns = [
        "date", "road_section", "station_id", "traffic_volume", "lat", "lon",
        "weather_station_id", "weather_station_dist_km", "f_daytime_mean",
        "fg_daytime_max",
    ]
    data[drive_columns].to_csv(ROOT / "daily.txt", sep="\t", index=False)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for source in [ACCIDENT_SOURCE, WEATHER_SOURCE, STATION_SOURCE, ANNUAL_SOURCE, DAILY_SOURCE]:
        if not source.exists():
            raise FileNotFoundError(f"Missing {source}; run the relevant preparation step first.")
    write_accidents()
    link_weather()
    write_stations()
    write_annual_traffic()
    write_daily_traffic()
    print("Wrote five working tables under data/processed/ and data/processed/daily.txt")


if __name__ == "__main__":
    main()
