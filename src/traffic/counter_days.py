"""Build observed daily vehicle-km for the assigned counter-sections."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.export_common import season_from_month
from src.accidents.urban import URBAN_GEOJSON_FILE
from src.traffic.locate_counters import ROADS
from src.traffic.rural_lengths import add_rural_lengths

DAILY = Path("data/processed/traffic/daily_raw.csv")
COUNTER_SECTIONS = Path("data/processed/traffic/counter_sections.csv")
OUTPUT = Path("data/processed/traffic/counter_days.csv")
START_YEAR = 2019
END_YEAR = 2024


def require_columns(data: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(data)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def build_counter_days(
    daily_path: Path, sections_path: Path,
    roads_path: Path = ROADS, urban_path: Path = URBAN_GEOJSON_FILE,
) -> pd.DataFrame:
    """Return one observed traffic total for each physical counter-section/day."""
    daily = pd.read_csv(daily_path, low_memory=False)
    sections = pd.read_csv(sections_path, low_memory=False)
    require_columns(
        daily, {"date", "year", "station_id", "road_section", "traffic_volume"},
        "Daily traffic",
    )
    require_columns(
        sections,
        {
            "year", "road_section", "counter_section_id", "source_station_min_m",
            "source_station_max_m", "counter_section_length_km",
            "weather_station_id", "weather_station_dist_km",
            "counter_section_start_km", "counter_section_end_km",
        },
        "Counter sections",
    )
    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    daily["road_section"] = daily["road_section"].astype("string").str.lower().str.strip()
    daily["station_id"] = pd.to_numeric(daily["station_id"], errors="raise")
    daily["traffic_volume"] = pd.to_numeric(daily["traffic_volume"], errors="raise")
    if not daily["year"].eq(daily["date"].dt.year).all():
        raise ValueError("Daily traffic year disagrees with its date")
    if daily.duplicated(["date", "road_section", "station_id"]).any():
        raise ValueError("Duplicate daily counter readings")
    if sections["counter_section_id"].isna().any() or sections["counter_section_id"].duplicated().any():
        raise ValueError("Counter-section IDs must be present and unique")
    daily["daily_row"] = np.arange(len(daily))
    sections = sections.copy()
    sections["road_section"] = sections["road_section"].astype("string").str.lower().str.strip()
    sections = add_rural_lengths(sections, roads_path, urban_path)
    joined = daily.merge(sections, on=["year", "road_section"], how="left")
    joined = joined[
        joined["station_id"].between(
            joined["source_station_min_m"], joined["source_station_max_m"]
        )
    ].copy()
    if joined.duplicated("daily_row").any():
        raise ValueError("A daily counter row maps to more than one counter-section")
    joined = joined[
        joined["year"].between(START_YEAR, END_YEAR)
        & joined["counter_section_length_km"].gt(0)
        & joined["weather_station_id"].notna()
        & joined["weather_station_dist_km"].le(20)
        & joined["traffic_volume"].ge(0)
    ].copy()
    joined["weather_station_id"] = joined["weather_station_id"].astype(int)
    group = [
        "date", "year", "counter_section_id", "counter_section_length_km",
        "rural_section_length_km", "unmapped_section_length_km", "weather_station_id",
    ]
    result = joined.groupby(group, as_index=False, observed=True).agg(
        traffic_vehicles=("traffic_volume", "sum")
    )
    result["month"] = result["date"].dt.month
    result["season"] = season_from_month(result["month"])
    result["vehicle_km"] = (
        result["traffic_vehicles"] * result["rural_section_length_km"]
    )
    total = (result["traffic_vehicles"] * result["counter_section_length_km"]).sum()
    unknown = (result["traffic_vehicles"] * result["unmapped_section_length_km"]).sum()
    print(f"full_section_vehicle_km={total:,.0f}; rural_vehicle_km={result.vehicle_km.sum():,.0f}; "
          f"excluded_unmapped_vehicle_km={unknown:,.0f}", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-d", "--daily", type=Path, default=DAILY)
    parser.add_argument("-c", "--counter-sections", type=Path, default=COUNTER_SECTIONS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-r", "--roads", type=Path, default=ROADS)
    parser.add_argument("-u", "--urban", type=Path, default=URBAN_GEOJSON_FILE)
    args = parser.parse_args()
    result = build_counter_days(args.daily, args.counter_sections, args.roads, args.urban)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"wrote={args.output} counter_days={len(result):,}")


if __name__ == "__main__":
    main()
