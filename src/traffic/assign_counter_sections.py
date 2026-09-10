"""Assign 2019--2024 rural injury accidents to daily-traffic counter sections."""

from __future__ import annotations

import argparse
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

from src.traffic.daily_common import normalize_section
from src.traffic.locate_counters import geometry_sequences, load_roads


ACCIDENTS = Path("data/processed/accidents/all.csv")
COUNTER_SECTIONS = Path("data/processed/traffic/counter_sections.csv")
ROADS = Path("data/raw/traffic/reference/roads.geojson")
OUTPUT = Path("data/processed/accidents/accidents-near-counter.csv")


def project_road_station(
    feature: dict[str, object], x: float, y: float
) -> tuple[float, float]:
    """Return MapServer road station and offset for the closest point on a feature."""
    properties = feature["properties"]  # type: ignore[index]
    start = float(properties["KAFLISTODUPPHAF"])
    end = float(properties["KAFLISTODENDIR"])
    if end <= start:
        raise ValueError("Road feature has an invalid station range")

    segments: list[tuple[float, float, float, float, float]] = []
    for sequence in geometry_sequences(feature["geometry"]):  # type: ignore[index]
        for point_a, point_b in zip(sequence, sequence[1:]):
            x1, y1 = point_a[:2]
            x2, y2 = point_b[:2]
            length = math.hypot(x2 - x1, y2 - y1)
            if length:
                segments.append((x1, y1, x2, y2, length))
    total_length = sum(segment[4] for segment in segments)
    if not total_length:
        raise ValueError("Road feature has no usable geometry")

    best: tuple[float, float] | None = None
    accumulated = 0.0
    for x1, y1, x2, y2, length in segments:
        dx, dy = x2 - x1, y2 - y1
        fraction = ((x - x1) * dx + (y - y1) * dy) / (length * length)
        fraction = min(1.0, max(0.0, fraction))
        near_x, near_y = x1 + fraction * dx, y1 + fraction * dy
        distance = math.hypot(x - near_x, y - near_y)
        station_fraction = (accumulated + fraction * length) / total_length
        if best is None or distance < best[1]:
            best = (station_fraction, distance)
        accumulated += length

    assert best is not None
    return start + best[0] * (end - start), best[1]


def assign(
    accidents_path: Path,
    counter_sections_path: Path,
    roads_path: Path,
    output_path: Path,
    max_road_distance_m: float,
) -> tuple[pd.DataFrame, Counter[str]]:
    """Project accidents to road stations and retain those within a counter section."""
    if max_road_distance_m < 0:
        raise ValueError("Maximum road distance must be nonnegative")
    accidents = pd.read_csv(accidents_path, low_memory=False)
    required_accident_columns = {
        "id", "timestamp", "lat", "lon", "meidsli", "urban_rural",
        "registered_road_section",
    }
    missing = required_accident_columns - set(accidents)
    if missing:
        raise ValueError(f"Accident data are missing columns: {sorted(missing)}")
    sections = pd.read_csv(counter_sections_path, low_memory=False)
    required_section_columns = {
        "year", "counter_section_id", "road_section",
        "counter_section_start_km", "counter_section_end_km",
        "counter_section_length_km", "weather_station_id", "weather_station_dist_km",
    }
    missing = required_section_columns - set(sections)
    if missing:
        raise ValueError(f"Counter sections are missing columns: {sorted(missing)}")

    accidents = accidents.copy()
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"], errors="raise")
    accidents["year"] = accidents["timestamp"].dt.year
    accidents["road_section"] = normalize_section(accidents["registered_road_section"])
    accidents["lat"] = pd.to_numeric(accidents["lat"], errors="coerce")
    accidents["lon"] = pd.to_numeric(accidents["lon"], errors="coerce")
    accidents["meidsli"] = pd.to_numeric(accidents["meidsli"], errors="coerce")
    selection = Counter[str]()
    selection["all_accidents"] = len(accidents)
    in_year_span = accidents["year"].between(2019, 2024)
    selection["outside_year_span"] = int((~in_year_span).sum())
    accidents = accidents[in_year_span].copy()
    selection["in_year_span"] = len(accidents)
    rural = accidents["urban_rural"].eq("Rural")
    selection["urban_or_unclassified"] = int((~rural).sum())
    accidents = accidents[rural].copy()
    selection["rural"] = len(accidents)
    injury = accidents["meidsli"].isin([1, 2, 3])
    selection["no_injury_or_unknown"] = int((~injury).sum())
    accidents = accidents[injury].copy()
    selection["rural_injury"] = len(accidents)
    sections = sections.copy()
    sections["road_section"] = normalize_section(sections["road_section"])
    for column in ["counter_section_start_km", "counter_section_end_km"]:
        sections[column] = pd.to_numeric(sections[column], errors="coerce")
    sections = sections.dropna(
        subset=["counter_section_start_km", "counter_section_end_km"]
    ).sort_values(["year", "road_section", "counter_section_end_km"])
    section_groups = {
        key: group.reset_index(drop=True)
        for key, group in sections.groupby(["year", "road_section"], sort=False)
    }
    roads = load_roads(roads_path)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3057", always_xy=True)

    rows: list[dict[str, object]] = []
    outcomes: Counter[str] = Counter()
    for accident in accidents.itertuples(index=False):
        key = (int(accident.year), str(accident.road_section))
        candidates = section_groups.get(key)
        if candidates is None:
            outcomes["no_counter_section_in_year"] += 1
            continue
        if not np.isfinite(accident.lat) or not np.isfinite(accident.lon):
            outcomes["invalid_coordinates"] += 1
            continue
        try:
            road_number, section_code = key[1].split("-", maxsplit=1)
        except ValueError:
            outcomes["invalid_road_section"] += 1
            continue
        features = roads.get((road_number, section_code.lower()), [])
        if not features:
            outcomes["no_road_geometry"] += 1
            continue
        x, y = transformer.transform(float(accident.lon), float(accident.lat))
        projections: list[tuple[float, float]] = []
        for feature in features:
            try:
                projections.append(project_road_station(feature, x, y))
            except ValueError:
                continue
        if not projections:
            outcomes["invalid_road_geometry"] += 1
            continue
        station_m, distance_m = min(projections, key=lambda projection: projection[1])
        if distance_m > max_road_distance_m:
            outcomes["road_projection_too_far"] += 1
            continue
        station_km = station_m / 1000
        matched = candidates[
            candidates["counter_section_start_km"].le(station_km)
            & candidates["counter_section_end_km"].ge(station_km)
        ]
        if matched.empty:
            outcomes["outside_counter_sections"] += 1
            continue
        counter = matched.iloc[0]
        row = accident._asdict()
        row.update(
            {
                "accident_station_m": station_m,
                "road_projection_distance_m": distance_m,
                "counter_section_id": counter.counter_section_id,
                "counter_section_length_km": counter.counter_section_length_km,
                "counter_weather_station_id": counter.weather_station_id,
                "counter_weather_station_dist_km": counter.weather_station_dist_km,
                "counter_section_assignment": "assigned",
            }
        )
        rows.append(row)
        outcomes["assigned"] += 1

    result = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    outcomes.update(selection)
    outcomes["not_assigned_to_counter_section"] = (
        selection["rural_injury"] - outcomes["assigned"]
    )
    return result, outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=ACCIDENTS)
    parser.add_argument("-c", "--counter-sections", type=Path, default=COUNTER_SECTIONS)
    parser.add_argument("-r", "--roads", type=Path, default=ROADS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "-d", "--max-road-distance-m", type=float, default=100,
        help="Reject accidents farther than this from their registered road geometry.",
    )
    args = parser.parse_args()
    assigned, outcomes = assign(
        args.input, args.counter_sections, args.roads, args.output,
        args.max_road_distance_m,
    )
    print("Selection overview:")
    print(f"  All accidents: {outcomes['all_accidents']:,}")
    print(f"  Excluded outside 2019--2024: {outcomes['outside_year_span']:,}")
    print(f"  Retained in 2019--2024: {outcomes['in_year_span']:,}")
    print(f"  Excluded urban or unclassified: {outcomes['urban_or_unclassified']:,}")
    print(f"  Retained rural: {outcomes['rural']:,}")
    print(f"  Excluded no injury or unknown injury: {outcomes['no_injury_or_unknown']:,}")
    print(f"  Retained rural injury: {outcomes['rural_injury']:,}")
    print(f"  Excluded without a counter-section assignment: {outcomes['not_assigned_to_counter_section']:,}")
    for reason in [
        "no_counter_section_in_year", "no_road_geometry", "invalid_road_geometry",
        "road_projection_too_far", "outside_counter_sections", "invalid_coordinates",
        "invalid_road_section",
    ]:
        if outcomes[reason]:
            print(f"    {reason.replace('_', ' ')}: {outcomes[reason]:,}")
    print(f"  Assigned counter-section accidents: {outcomes['assigned']:,}")
    print(f"Wrote {len(assigned):,} assigned accidents to {args.output}.")


if __name__ == "__main__":
    main()
