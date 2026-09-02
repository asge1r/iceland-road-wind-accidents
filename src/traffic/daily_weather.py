"""Match daily traffic counters to daytime weather observations.

This preparation step writes one counter-day table with a nearby clean weather
station. Counter locations are prepared separately by ``locate_counters``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.traffic import daily_tools as tools


DEFAULT_DAILY = Path("data/processed/traffic/daily.csv")
DEFAULT_STATIONS = Path("data/raw/weather/stations.csv")
DEFAULT_WEATHER = Path("data/processed/weather/weather.parquet")
DEFAULT_WEATHER_MATCH = Path("data/processed/traffic/daily_match.parquet")
DEFAULT_OUTPUT = Path("data/processed/traffic/daily_weather.csv")
DEFAULT_COVERAGE = Path("archive/generated_diagnostics/daily_traffic_coverage.csv")


def match_weather(
    daily_path: Path,
    stations_path: Path,
    weather_path: Path,
    match_path: Path,
    output_path: Path,
    coverage_path: Path,
    start_year: int,
    end_year: int,
    rebuild_match: bool,
    max_row_groups: int | None,
) -> None:
    """Write the canonical counter-day weather match and its coverage audit."""
    daily = tools.read_daily(daily_path, start_year, end_year)
    diagnostics: dict[str, int] = {}
    match_usable = match_path.exists() and not rebuild_match
    if match_usable:
        weather = pd.read_parquet(match_path)
        weather["date"] = pd.to_datetime(weather["date"])
        match_usable = (
            "weather_match_method" in weather.columns
            and weather["weather_match_method"].eq(
                "nearest_valid_station_to_interpolated_counter_within_20km"
            ).all()
            and "counter_site_id" in weather.columns
            and weather["date"].dt.year.min() <= start_year
            and weather["date"].dt.year.max() >= end_year
        )
    if not match_usable:
        weather, diagnostics = tools.build_weather_match_data(
            weather_path,
            daily,
            stations_path,
            start_year,
            end_year,
            max_row_groups,
        )
        if max_row_groups is None:
            match_path.parent.mkdir(parents=True, exist_ok=True)
            weather.to_parquet(match_path, index=False, compression="zstd")

    weather = weather[weather["date"].dt.year.between(start_year, end_year)].copy()
    excluded_station = weather["weather_station_id"].isin(
        tools.DAILY_WIND_EXCLUDED_STATION_IDS
    )
    diagnostics["counter_days_excluded_station_7475"] = int(excluded_station.sum())
    weather = weather.loc[~excluded_station].copy()
    mapped_counters = set(weather["counter_site_id"].dropna().astype(str))
    panel = daily.merge(
        weather,
        on=["counter_site_id", "road_section", "date"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_weather"),
    )
    panel = tools.add_normalized_traffic(panel)
    panel["has_counter_location_weather_match"] = panel["counter_site_id"].isin(
        mapped_counters
    )
    coverage = pd.DataFrame(
        [
            {
                "counter_days": len(panel),
                "counters": panel["counter_site_id"].nunique(),
                "road_sections": panel["road_section"].nunique(),
                "counter_days_with_location": int(panel["location_lat"].notna().sum()),
                "counter_days_with_official_road_geometry": int(
                    (
                        panel["location_method"].eq(
                            "station_interpolated_from_official_road_geometry"
                        )
                        & panel["location_lat"].notna()
                    ).sum()
                ),
                "counter_days_with_weather_station_match": int(
                    panel["has_counter_location_weather_match"].sum()
                ),
                "counter_days_with_daytime_wind": int(panel["f_daytime_mean"].notna().sum()),
                "wind_coverage_pct": 100 * panel["f_daytime_mean"].notna().mean(),
                **diagnostics,
            }
        ]
    )
    for path in [output_path, coverage_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
    output_columns = [
        "date", "year", "counter_site_id", "road_section", "traffic_volume",
        "f_daytime_mean", "fg_daytime_mean", "f_full_day_mean", "fg_full_day_mean",
        "full_observation_count", "f_full_bin_0_5_count", "f_full_bin_5_10_count",
        "f_full_bin_10_15_count", "f_full_bin_15_20_count",
        "f_full_bin_20_25_count", "f_full_bin_ge25_count",
        "active_07_24_observation_count", "f_07_24_bin_0_5_count",
        "f_07_24_bin_5_10_count", "f_07_24_bin_10_15_count",
        "f_07_24_bin_15_20_count", "f_07_24_bin_20_25_count",
        "f_07_24_bin_ge25_count",
        "traffic_index",
        "weather_station_dist_km",
    ]
    panel[output_columns].to_csv(output_path, index=False)
    coverage.to_csv(coverage_path, index=False)
    print(coverage.to_string(index=False))
    print(f"wrote={output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-d", "--daily", type=Path, default=DEFAULT_DAILY)
    parser.add_argument("-s", "--stations", type=Path, default=DEFAULT_STATIONS)
    parser.add_argument("-w", "--weather", type=Path, default=DEFAULT_WEATHER)
    parser.add_argument("-m", "--weather-match", type=Path, default=DEFAULT_WEATHER_MATCH)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-v", "--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("-y", "--start-year", type=int, default=2019)
    parser.add_argument("-Y", "--end-year", type=int, default=2024)
    parser.add_argument("-r", "--rebuild-weather-match", action="store_true")
    parser.add_argument("-g", "--max-row-groups", type=int)
    args = parser.parse_args()
    match_weather(
        args.daily,
        args.stations,
        args.weather,
        args.weather_match,
        args.output,
        args.coverage,
        args.start_year,
        args.end_year,
        args.rebuild_weather_match,
        args.max_row_groups,
    )


if __name__ == "__main__":
    main()
