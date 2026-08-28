"""Build road-period data for the annual-traffic rate comparison.

This script creates one prepared table: road section × year × traffic period ×
weather-station × wind interval. It includes every road section with annual
traffic, so it can provide an exposure denominator for estimated crash rates.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.traffic.road_period import (
    DEFAULT_ANNUAL_TRAFFIC,
    DEFAULT_INJURY_ACCIDENTS,
    DEFAULT_LONG,
    DEFAULT_PERIOD_WIND_FREQUENCY,
    DEFAULT_SECTION_MIDPOINTS,
    DEFAULT_STATIONS,
    DEFAULT_WEATHER,
    assign_nearest_valid_station,
    build_accident_counts,
    build_all_annual_traffic_scope,
    build_base_table,
    build_long_table,
    build_period_wind_frequency,
    build_station_candidates,
    load_annual_traffic,
)


OUTPUT_COLUMNS = [
    "year",
    "road_section",
    "traffic_period",
    "weather_station_id",
    "weather_station_distance_km",
    "section_length_km",
    "traffic_reference_daily_volume",
    "variable",
    "bin_label",
    "bin_lower_ms",
    "frequency_pct",
    "wind_frequency_available",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--annual-traffic", type=Path, default=DEFAULT_ANNUAL_TRAFFIC)
    parser.add_argument("-i", "--injury-accidents", type=Path, default=DEFAULT_INJURY_ACCIDENTS)
    parser.add_argument("-w", "--weather", type=Path, default=DEFAULT_WEATHER)
    parser.add_argument("-p", "--period-wind-frequency", type=Path, default=DEFAULT_PERIOD_WIND_FREQUENCY)
    parser.add_argument("-r", "--rebuild-period-wind-frequency", action="store_true")
    parser.add_argument("-m", "--max-weather-row-groups", type=int)
    parser.add_argument("-s", "--stations", type=Path, default=DEFAULT_STATIONS)
    parser.add_argument("-M", "--section-midpoints", type=Path, default=DEFAULT_SECTION_MIDPOINTS)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_LONG)
    args = parser.parse_args()

    annual = load_annual_traffic(args.annual_traffic)
    scope = build_all_annual_traffic_scope(annual)
    candidates = build_station_candidates(scope, args.section_midpoints, args.stations)
    counts, bin_counts, _ = build_accident_counts(args.injury_accidents, annual)
    if args.rebuild_period_wind_frequency or not args.period_wind_frequency.exists():
        wind = build_period_wind_frequency(
            args.weather,
            args.period_wind_frequency,
            candidates["weather_station_id"].drop_duplicates().to_numpy(),
            max_row_groups=args.max_weather_row_groups,
        )
    else:
        wind = pd.read_csv(args.period_wind_frequency)
    assigned = assign_nearest_valid_station(annual, scope, candidates, wind)
    base = build_base_table(
        assigned,
        counts,
    )
    road_period = build_long_table(base, wind, bin_counts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    missing = set(OUTPUT_COLUMNS) - set(road_period.columns)
    if missing:
        raise ValueError(f"Road-period output is missing columns: {sorted(missing)}")
    road_period[OUTPUT_COLUMNS].to_csv(args.output, index=False)
    print(f"road_period_rows={len(road_period):,}")
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
