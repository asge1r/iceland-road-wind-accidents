"""Match counter-section accidents to weather at their assigned station."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.accidents.match_weather import read_candidate_weather, select_best
from src.export_common import season_from_month
from src.traffic.counter_day_weather import require_columns


ACCIDENTS = Path("data/processed/accidents/accidents-near-counter.csv")
COUNTER_DAYS = Path("data/processed/traffic/counter_day_weather.parquet")
WEATHER = Path("data/processed/weather/weather.parquet")
OUTPUT = Path("data/processed/traffic/counter_accidents.csv")


def accident_candidates(accidents: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in accidents.itertuples(index=True):
        for weather_time in {row.timestamp.floor("10min"), row.timestamp.ceil("10min")}:
            difference = abs((weather_time - row.timestamp).total_seconds()) / 60
            if difference <= 5:
                rows.append(
                    {
                        "acc_index": row.Index,
                        "weather_station_id": int(row.weather_station_id),
                        "weather_station_dist_km": float(row.weather_station_dist_km),
                        "weather_time": weather_time,
                        "weather_time_difference_minutes": difference,
                    }
                )
    return pd.DataFrame(rows)


def build(
    accidents_path: Path, counter_days_path: Path, weather_path: Path
) -> pd.DataFrame:
    accidents = pd.read_csv(accidents_path, low_memory=False)
    counter_days = pd.read_parquet(
        counter_days_path,
        columns=[
            "date", "counter_section_id", "weather_station_id",
            "traffic_vehicles",
        ],
    )
    require_columns(
        accidents,
        {
            "id", "timestamp", "meidsli", "counter_section_id",
            "counter_weather_station_id", "counter_weather_station_dist_km",
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
    traffic_days = counter_days[counter_days["traffic_vehicles"].gt(0)].drop_duplicates(
        ["date", "counter_section_id"]
    )
    accidents = accidents.merge(
        traffic_days,
        on=["date", "counter_section_id"], how="inner", validate="many_to_one",
        suffixes=("", "_day"),
    )
    if not accidents["counter_weather_station_id"].eq(
        accidents["weather_station_id"]
    ).all():
        raise ValueError("Accident and counter-day weather station disagree")
    accidents["weather_station_dist_km"] = accidents[
        "counter_weather_station_dist_km"
    ]
    accidents = accidents.reset_index(drop=True)
    candidates = accident_candidates(accidents)
    weather = read_candidate_weather(pq.ParquetFile(weather_path), candidates)
    matched = select_best(candidates, weather)
    result = accidents.merge(
        matched[
            [
                "acc_index", "weather_time", "weather_time_difference_minutes",
                "f", "fg", "t",
            ]
        ],
        left_index=True, right_on="acc_index", how="inner", validate="one_to_one",
    )
    result["temperature"] = result["t"].where(result["t"].between(-30, 30))
    columns = [
        "id", "timestamp", "date", "year", "season", "meidsli",
        "counter_section_id", "weather_station_id", "weather_station_dist_km",
        "weather_time", "weather_time_difference_minutes", "f", "fg", "temperature",
    ]
    result = result[columns].sort_values("id").reset_index(drop=True)
    if result["id"].duplicated().any():
        raise ValueError("Counter-section accident-weather matches are not unique")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-c", "--counter-days", type=Path, default=COUNTER_DAYS)
    parser.add_argument("-w", "--weather", type=Path, default=WEATHER)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build(args.accidents, args.counter_days, args.weather)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"wrote={args.output} rows={len(result):,}")


if __name__ == "__main__":
    main()
