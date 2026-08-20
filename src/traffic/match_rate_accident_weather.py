"""Match rate-analysis accidents to the weather station used for road exposure."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.accidents.match_weather import read_candidate_weather, select_best


PANEL = Path("data/processed/traffic/road_section_wind_panel_2007_2025.parquet")
ACCIDENTS = Path("data/processed/accidents/rural_injury_accidents.parquet")
WEATHER = Path("data/processed/weather/weather_10min_clean.parquet")
STATIONS = Path("data/processed/weather/stations.csv")
OUTPUT = Path("data/processed/accidents/rate_accidents_weather.parquet")
AUDIT = Path("reports/working/tables/rate_accident_weather_audit.csv")
VEHICLE_SOURCES = [
    (Path("data/raw/accidents/vehicles_2007_2024.txt"), "nid", "taeki"),
    (Path("data/raw/accidents/vehicles_2025.txt"), "NID", "Nr. Ökutækis"),
]

PERIOD_BY_MONTH = {
    1: "VDU", 2: "VDU", 3: "VDU", 4: "VHDU", 5: "VHDU", 6: "SDU",
    7: "SDU", 8: "SDU", 9: "SDU", 10: "VHDU", 11: "VHDU", 12: "VDU",
}


def normalize_section(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.lower()


def haversine_km(
    lat_1: pd.Series, lon_1: pd.Series, lat_2: pd.Series, lon_2: pd.Series
) -> np.ndarray:
    lat_1_rad, lon_1_rad = np.radians(lat_1.astype(float)), np.radians(lon_1.astype(float))
    lat_2_rad, lon_2_rad = np.radians(lat_2.astype(float)), np.radians(lon_2.astype(float))
    haversine = (
        np.sin((lat_2_rad - lat_1_rad) / 2) ** 2
        + np.cos(lat_1_rad) * np.cos(lat_2_rad) * np.sin((lon_2_rad - lon_1_rad) / 2) ** 2
    )
    return 2 * 6371.0 * np.arcsin(np.sqrt(haversine))


def load_road_station_panel(path: Path) -> pd.DataFrame:
    columns = [
        "year", "road_section", "traffic_period", "weather_station_id",
        "weather_station_distance_km", "section_length_km", "variable",
        "wind_frequency_available", "traffic_reference_daily_volume",
    ]
    panel = pd.read_parquet(path, columns=columns)
    panel = panel[
        panel["variable"].eq("f_5m")
        & panel["wind_frequency_available"].fillna(False)
        & panel["weather_station_id"].notna()
        & panel["weather_station_distance_km"].le(20)
        & panel["section_length_km"].gt(0)
        & panel["traffic_reference_daily_volume"].gt(0)
    ].copy()
    panel["road_section"] = normalize_section(panel["road_section"])
    panel = panel.drop(columns="variable").drop_duplicates()
    keys = ["year", "road_section", "traffic_period"]
    if panel.duplicated(keys).any():
        raise ValueError("Road-period panel has more than one weather station per exposure stratum")
    return panel


def load_accidents(path: Path) -> pd.DataFrame:
    columns = ["nid", "timestamp", "registered_road_section", "lat", "lon"]
    accidents = pd.read_parquet(path, columns=columns)
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"], errors="coerce")
    accidents["year"] = accidents["timestamp"].dt.year
    accidents["traffic_period"] = accidents["timestamp"].dt.month.map(PERIOD_BY_MONTH)
    accidents["road_section"] = normalize_section(accidents["registered_road_section"])
    return accidents.dropna(subset=["timestamp", "lat", "lon", "traffic_period"]).copy()


def build_candidates(accidents: pd.DataFrame) -> pd.DataFrame:
    rows: list[tuple[int, int, float, pd.Timestamp, float]] = []
    for row in accidents.itertuples(index=True):
        for weather_time in {row.timestamp.floor("10min"), row.timestamp.ceil("10min")}:
            difference = abs((weather_time - row.timestamp).total_seconds()) / 60
            if difference <= 5:
                rows.append(
                    (
                        row.Index,
                        int(row.rate_weather_station_id),
                        float(row.rate_station_accident_distance_km),
                        weather_time,
                        difference,
                    )
                )
    return pd.DataFrame(
        rows,
        columns=[
            "acc_index", "weather_station_id", "weather_station_dist_km", "weather_time",
            "weather_time_difference_minutes",
        ],
    )


def add_vehicle_count(accidents: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for path, identifier, vehicle in VEHICLE_SOURCES:
        if path.exists():
            source = pd.read_csv(path, sep="\t", usecols=[identifier, vehicle])
            frames.append(source.rename(columns={identifier: "nid", vehicle: "vehicle_id"}))
    if not frames:
        accidents["vehicle_count"] = pd.NA
        accidents["vehicle_group"] = pd.NA
        return accidents
    vehicles = pd.concat(frames, ignore_index=True)
    vehicles["nid"] = pd.to_numeric(vehicles["nid"], errors="coerce")
    counts = vehicles.dropna(subset=["nid"]).groupby("nid")["vehicle_id"].nunique()
    accidents = accidents.join(counts.rename("vehicle_count"), on="nid")
    accidents["vehicle_group"] = np.where(
        accidents["vehicle_count"].eq(1), "1 vehicle", "2 or more vehicles"
    )
    return accidents


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-w", "--weather", type=Path, default=WEATHER)
    parser.add_argument("-s", "--stations", type=Path, default=STATIONS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-u", "--audit", type=Path, default=AUDIT)
    args = parser.parse_args()

    panel = load_road_station_panel(args.panel)
    accidents = load_accidents(args.accidents)
    source_accidents = len(accidents)
    accidents = accidents.merge(
        panel.rename(columns={"weather_station_id": "rate_weather_station_id"}),
        on=["year", "road_section", "traffic_period"],
        how="inner",
        validate="many_to_one",
    )
    matched_to_road_period = len(accidents)
    stations = pd.read_csv(args.stations, usecols=["station", "lat", "lon"]).drop_duplicates("station")
    accidents = accidents.merge(
        stations,
        left_on="rate_weather_station_id",
        right_on="station",
        how="left",
        validate="many_to_one",
        suffixes=("", "_station"),
    )
    accidents["rate_station_accident_distance_km"] = haversine_km(
        accidents["lat"], accidents["lon"], accidents["lat_station"], accidents["lon_station"]
    )
    accidents = accidents[accidents["rate_station_accident_distance_km"].le(20)].copy()
    within_20km = len(accidents)
    accidents.index.name = "acc_index"
    candidates = build_candidates(accidents)
    weather = read_candidate_weather(pq.ParquetFile(args.weather), candidates)
    matched = select_best(candidates, weather).rename(
        columns={"weather_station_id": "rate_weather_station_id", "weather_time": "rate_weather_time"}
    )
    output = accidents.reset_index().merge(
        matched,
        on=["acc_index", "rate_weather_station_id"],
        how="inner",
        validate="one_to_one",
    )
    valid_wind = (
        output["f"].between(0, 45, inclusive="left")
        & output["fg"].between(0, 65, inclusive="left")
        & output["fg"].add(0.5).ge(output["f"])
    )
    output = output[valid_wind].copy()
    output = add_vehicle_count(output)
    keep = [
        "nid", "timestamp", "year", "road_section", "traffic_period",
        "rate_weather_station_id", "rate_weather_time", "weather_time_difference_minutes",
        "rate_station_accident_distance_km", "weather_station_distance_km",
        "section_length_km", "f", "fg",
        "vehicle_count", "vehicle_group",
    ]
    output = output[keep].sort_values("nid")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    audit = pd.DataFrame(
        [
            {"metric": "rural_injury_accidents", "value": source_accidents},
            {"metric": "accidents_with_annual_traffic_road_period", "value": matched_to_road_period},
            {"metric": "accidents_with_same_rate_station_within_20km", "value": within_20km},
            {"metric": "accidents_with_clean_rate_station_wind", "value": len(output)},
            {"metric": "accidents_with_vehicle_count", "value": int(output["vehicle_count"].notna().sum())},
        ]
    )
    audit.to_csv(args.audit, index=False)
    print(audit.to_string(index=False))
    print(f"wrote={args.output} rows={len(output):,}")


if __name__ == "__main__":
    main()
