"""Summarize accident counts and weather-match coverage by year."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ACCIDENTS = Path("data/analysis/accidents.csv")
CONDITIONS = Path("data/analysis/accident_conditions.csv")
OUTPUT = Path("reports/main/tables/weather_coverage.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-c", "--conditions", type=Path, default=CONDITIONS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    accidents = pd.read_csv(args.accidents, usecols=["id", "year"])
    conditions = pd.read_csv(
        args.conditions,
        usecols=[
            "id", "f", "weather_station_dist_km", "weather_time_difference_minutes",
            "temperature_c", "temp_distance_km", "temp_time_diff_min",
        ],
    )
    if not accidents["id"].is_unique or not conditions["id"].is_unique:
        raise ValueError("Accident IDs must be unique in both analysis files")
    data = accidents.merge(conditions, on="id", validate="one_to_one")
    data["wind_match"] = (
        data["f"].notna()
        & data["weather_station_dist_km"].le(20)
        & data["weather_time_difference_minutes"].le(5)
    )
    data["temperature_match"] = (
        data["temperature_c"].notna()
        & data["temp_distance_km"].le(20)
        & data["temp_time_diff_min"].le(5)
    )
    data["strong_wind"] = data["wind_match"] & data["f"].ge(15)
    result = data.groupby("year", as_index=False).agg(
        rural_injury_accidents=("id", "size"),
        wind_matches=("wind_match", "sum"),
        temperature_matches=("temperature_match", "sum"),
        accidents_at_f_ge15=("strong_wind", "sum"),
    )
    result["wind_coverage_pct"] = 100 * result["wind_matches"] / result["rural_injury_accidents"]
    result["temperature_coverage_pct"] = 100 * result["temperature_matches"] / result["rural_injury_accidents"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
