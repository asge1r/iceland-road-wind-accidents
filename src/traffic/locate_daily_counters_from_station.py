"""Locate daily PDF counters from road number, section and PDF ``stöð``.

``stöð`` is the counter's reported metre station, not a generic counter label.
This script uses official MapServer/6 start/end stations and road geometry when
``roads.geojson`` is available. It retains the established Bst/Est-based method
as a documented fallback, so existing results remain reproducible.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

from src.traffic import prepare_daily_traffic as fallback


ROADS = Path("data/raw/traffic/reference/roads.geojson")


def geometry_sequences(geometry: dict[str, object]) -> list[list[list[float]]]:
    if geometry["type"] == "LineString":
        return [geometry["coordinates"]]  # type: ignore[index]
    if geometry["type"] == "MultiLineString":
        return geometry["coordinates"]  # type: ignore[index]
    raise ValueError(f"Unsupported road geometry: {geometry['type']}")


def interpolate(feature: dict[str, object], station_m: float) -> tuple[float, float]:
    """Interpolate a station using official MapServer start/end station values."""
    properties = feature["properties"]  # type: ignore[index]
    start = float(properties["KAFLISTODUPPHAF"])
    end = float(properties["KAFLISTODENDIR"])
    if not start <= station_m <= end:
        raise ValueError("PDF station is outside the official road-section range")
    segments: list[tuple[float, float, float, float, float]] = []
    for sequence in geometry_sequences(feature["geometry"]):  # type: ignore[index]
        for point_a, point_b in zip(sequence, sequence[1:]):
            x1, y1 = point_a[:2]
            x2, y2 = point_b[:2]
            segments.append((x1, y1, x2, y2, math.hypot(x2 - x1, y2 - y1)))
    length = sum(segment[4] for segment in segments)
    if length <= 0 or end <= start:
        raise ValueError("Road feature has no usable geometry or station range")
    remaining = (station_m - start) / (end - start) * length
    for x1, y1, x2, y2, segment_length in segments:
        if remaining <= segment_length:
            fraction = remaining / segment_length if segment_length else 0
            return x1 + fraction * (x2 - x1), y1 + fraction * (y2 - y1)
        remaining -= segment_length
    return segments[-1][2], segments[-1][3]


def load_roads(path: Path) -> dict[tuple[str, str], list[dict[str, object]]]:
    """Index MapServer features by reported road number and section code."""
    source = json.loads(path.read_text(encoding="utf-8"))
    indexed: dict[tuple[str, str], list[dict[str, object]]] = {}
    for feature in source["features"]:
        properties = feature["properties"]
        key = (str(properties["NRVEGUR"]), str(properties["NRKAFLI"]).lower())
        indexed.setdefault(key, []).append(feature)
    return indexed


def locate_with_official_geometry(daily: pd.DataFrame, roads_path: Path) -> pd.DataFrame:
    """Return one location row per counter-site year using the PDF station."""
    roads = load_roads(roads_path)
    transformer = Transformer.from_crs("EPSG:3057", "EPSG:4326", always_xy=True)
    sites = daily[["year", "counter_site_id", "road_section", "station_id"]].drop_duplicates()
    rows: list[dict[str, object]] = []
    for site in sites.itertuples(index=False):
        road_number, section_code = str(site.road_section).split("-", maxsplit=1)
        matched: tuple[float, float] | None = None
        for feature in roads.get((road_number, section_code.lower()), []):
            try:
                matched = interpolate(feature, float(site.station_id))
                break
            except ValueError:
                continue
        if matched is None:
            continue
        lon, lat = transformer.transform(*matched)
        rows.append(
            {
                "year": site.year,
                "counter_site_id": site.counter_site_id,
                "location_x_3057": matched[0],
                "location_y_3057": matched[1],
                "location_lon": lon,
                "location_lat": lat,
                "location_method": "station_interpolated_from_official_road_geometry",
                "location_is_estimated": True,
                "location_max_offset_along_road_km": np.nan,
                "location_max_offset_straight_line_m": np.nan,
                "location_station_range_valid": True,
                "official_counter_name": None,
                "counter_name_score": np.nan,
                "counter_name_margin": np.nan,
            }
        )
    return pd.DataFrame(rows)


def locate() -> None:
    """Write the existing canonical daily-traffic table with the best available rule."""
    daily = pd.read_parquet(fallback.OUT_COUNTS)
    if not ROADS.exists():
        print(f"Official road geometry not found at {ROADS}; using documented Bst/Est fallback.")
        fallback.rebuild_locations_only()
        return

    direct = locate_with_official_geometry(daily, ROADS)
    legacy = fallback.add_counter_locations(daily)
    if direct.empty:
        raise RuntimeError("No daily counters could be located from the official road geometry.")
    location_columns = [column for column in legacy.columns if column not in daily.columns]
    direct_location_columns = [
        column for column in direct.columns if column not in {"year", "counter_site_id"}
    ]
    output = legacy.merge(
        direct.rename(columns={column: f"{column}_official" for column in direct_location_columns}),
        on=["year", "counter_site_id"], how="left", validate="many_to_one",
    )
    for column in direct_location_columns:
        official_column = f"{column}_official"
        if column in output:
            output[column] = output[official_column].where(output[official_column].notna(), output[column])
        else:
            output[column] = output[official_column]
        output = output.drop(columns=official_column)
    # Preserve all established columns. The direct official method replaces only
    # those locations for which the PDF station lies in a current official range.
    output = output.sort_values(["counter_site_id", "date"])
    output.to_parquet(fallback.OUT_LONG_MULTI, index=False, compression="zstd")
    output[["year", "counter_site_id", *location_columns]].drop_duplicates(
        ["year", "counter_site_id"]
    ).to_csv(fallback.OUT_LOCATIONS, index=False)
    print(
        f"Wrote {len(output):,} counter-days; official PDF-station geometry used for "
        f"{len(direct):,}/{daily[['year', 'counter_site_id']].drop_duplicates().shape[0]:,} counter-site years."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    locate()


if __name__ == "__main__":
    main()
