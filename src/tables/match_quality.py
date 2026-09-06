"""Summarise spatial and temporal quality of accident-weather matches."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/match_quality.csv")


def require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def metric_row(
    label: str,
    data: pd.DataFrame,
    station: str,
    distance: str,
    time_difference: str,
    value: str,
    total: int,
) -> dict[str, object]:
    matched = (
        data[value].notna()
        & data[station].notna()
        & data[distance].le(20)
        & data[time_difference].le(5)
    )
    retained = data.loc[matched]
    return {
        "weather_variable": label,
        "available_accidents": total,
        "matched_accidents": int(matched.sum()),
        "matched_pct": 100 * matched.mean(),
        "unmatched_accidents": int((~matched).sum()),
        "stations_used": int(retained[station].nunique()),
        "median_distance_km": retained[distance].median(),
        "p90_distance_km": retained[distance].quantile(0.9),
        "median_time_difference_min": retained[time_difference].median(),
        "maximum_time_difference_min": retained[time_difference].max(),
    }


def build_table(accidents: pd.DataFrame, conditions: pd.DataFrame) -> pd.DataFrame:
    require_columns(accidents, {"id"}, "accidents.csv")
    required = {
        "id", "weather_station_id", "weather_station_dist_km",
        "weather_time_difference_minutes", "f", "temp_station_id",
        "temp_distance_km", "temp_time_diff_min", "temperature_c",
    }
    require_columns(conditions, required, "accident_conditions.csv")
    if not accidents["id"].is_unique or not conditions["id"].is_unique:
        raise ValueError("Accident and condition IDs must be unique")
    data = accidents[["id"]].merge(
        conditions, on="id", how="left", validate="one_to_one"
    )
    total = len(data)
    rows = [
        metric_row(
            "Mean wind and gust", data, "weather_station_id",
            "weather_station_dist_km", "weather_time_difference_minutes", "f", total,
        ),
        metric_row(
            "Temperature", data, "temp_station_id", "temp_distance_km",
            "temp_time_diff_min", "temperature_c", total,
        ),
    ]
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-c", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    table = build_table(pd.read_csv(args.accidents), pd.read_csv(args.conditions))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
