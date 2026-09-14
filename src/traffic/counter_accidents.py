"""Match counter-section accidents to the nearest station available at event time."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.accidents.match_weather import read_candidate_weather, select_best
from src.export_common import season_from_month
from src.traffic.counter_days import require_columns
from src.weather.eligibility import valid_temperature
from src.accidents.urban import URBAN_GEOJSON_FILE
from src.traffic.locate_counters import ROADS
from src.traffic.rural_lengths import on_rural_road
from src.traffic.station_selection import STATIONS, SECTIONS, station_candidates, valid_wind


ACCIDENTS = Path("data/processed/accidents/accidents-near-counter.csv")
COUNTER_DAYS = Path("data/processed/traffic/counter_days.csv")
WEATHER = Path("data/processed/weather/weather.parquet")
OUTPUT = Path("data/processed/traffic/counter_accidents.csv")


def accident_candidates(accidents: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    ranked = {key: group for key, group in candidates.groupby("counter_section_id")}
    for row in accidents.itertuples(index=True):
        near = ranked.get(row.counter_section_id)
        if near is None:
            continue
        for weather_time in {row.timestamp.floor("10min"), row.timestamp.ceil("10min")}:
            difference = abs((weather_time - row.timestamp).total_seconds()) / 60
            if difference <= 5:
                for station in near.itertuples(index=False):
                    rows.append(
                        {
                            "acc_index": row.Index,
                            "weather_station_id": int(station.weather_station_id),
                            "weather_station_dist_km": float(station.weather_station_dist_km),
                            "weather_time": weather_time,
                            "weather_time_difference_minutes": difference,
                        }
                    )
    return pd.DataFrame(rows, columns=[
        "acc_index", "weather_station_id", "weather_station_dist_km",
        "weather_time", "weather_time_difference_minutes",
    ])


def build(
    accidents_path: Path, counter_days_path: Path, weather_path: Path,
    roads_path: Path = ROADS, urban_path: Path = URBAN_GEOJSON_FILE,
    sections_path: Path = SECTIONS, stations_path: Path = STATIONS,
) -> pd.DataFrame:
    accidents = pd.read_csv(accidents_path, low_memory=False)
    counter_days = pd.read_csv(
        counter_days_path,
        usecols=[
            "date", "counter_section_id",
            "traffic_vehicles", "vehicle_km",
        ],
    )
    counter_days["date"] = pd.to_datetime(counter_days["date"], errors="raise")
    if counter_days.duplicated(["date", "counter_section_id"]).any():
        raise ValueError("Counter-days are not unique")
    require_columns(
        accidents,
        {
            "id", "timestamp", "meidsli", "counter_section_id",
            "counter_weather_station_id", "counter_weather_station_dist_km",
            "road_section", "accident_station_m",
        },
        "Assigned accidents",
    )
    accidents = accidents.copy()
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"], errors="raise")
    accidents["date"] = accidents["timestamp"].dt.normalize()
    accidents["year"] = accidents["timestamp"].dt.year
    accidents["season"] = season_from_month(accidents["timestamp"].dt.month)
    accidents["meidsli"] = pd.to_numeric(accidents["meidsli"], errors="coerce")
    accidents = accidents[
        accidents["timestamp"].dt.hour.ge(7)
        & accidents["counter_weather_station_dist_km"].le(20)
    ].copy()
    daytime_count = len(accidents)
    accidents = accidents[on_rural_road(accidents, roads_path, urban_path)].copy()
    rural_count = len(accidents)
    traffic_days = counter_days[counter_days["traffic_vehicles"].gt(0)
                                & counter_days["vehicle_km"].gt(0)].drop_duplicates(
        ["date", "counter_section_id"]
    )
    accidents = accidents.merge(
        traffic_days,
        on=["date", "counter_section_id"], how="inner", validate="many_to_one",
        suffixes=("", "_day"),
    )
    # The nominal counter station is metadata, not a time-specific observation.
    accidents = accidents.drop(columns=["weather_station_id", "weather_station_dist_km"], errors="ignore")
    accidents = accidents.reset_index(drop=True)
    traffic_count = len(accidents)
    sections = pd.read_csv(sections_path)
    candidates = accident_candidates(accidents, station_candidates(sections, pd.read_csv(stations_path)))
    weather = read_candidate_weather(pq.ParquetFile(weather_path), candidates)
    weather = weather[valid_wind(weather["f"], weather["fg"])]
    matched = select_best(candidates, weather)
    result = accidents.merge(
        matched[
            [
                "acc_index", "weather_time", "weather_time_difference_minutes",
                "weather_station_id", "weather_station_dist_km", "f", "fg", "t",
            ]
        ],
        left_index=True, right_on="acc_index", how="inner", validate="one_to_one",
    )
    result["temperature"] = result["t"].where(valid_temperature(result["t"]))
    columns = [
        "id", "timestamp", "date", "year", "season", "meidsli",
        "counter_section_id", "weather_station_id", "weather_station_dist_km",
        "weather_time", "weather_time_difference_minutes", "f", "fg", "temperature",
    ]
    result = result[columns].sort_values("id").reset_index(drop=True)
    if result["id"].duplicated().any():
        raise ValueError("Counter-section accident-weather matches are not unique")
    print(
        f"daytime_with_station_within_20km={daytime_count:,}; "
        f"outside_rural_road_exposure={daytime_count - rural_count:,}; "
        f"without_positive_rural_daily_traffic={rural_count - traffic_count:,}; "
        f"without_accident_time_weather={traffic_count - len(result):,}"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-c", "--counter-days", type=Path, default=COUNTER_DAYS)
    parser.add_argument("-w", "--weather", type=Path, default=WEATHER)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-r", "--roads", type=Path, default=ROADS)
    parser.add_argument("-u", "--urban", type=Path, default=URBAN_GEOJSON_FILE)
    parser.add_argument("-s", "--stations", type=Path, default=STATIONS)
    parser.add_argument("-k", "--counter-sections", type=Path, default=SECTIONS)
    args = parser.parse_args()
    result = build(args.accidents, args.counter_days, args.weather, args.roads, args.urban,
                   args.counter_sections, args.stations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"wrote={args.output} rows={len(result):,}")


if __name__ == "__main__":
    main()
