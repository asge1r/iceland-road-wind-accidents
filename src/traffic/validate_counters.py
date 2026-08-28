"""Validate PDF-``stöð`` counter coordinates against official 20 m road points.

This is a quality-control script only. It never changes counter coordinates.
For each site-year located from official road geometry it queries the Road
Administration MapServer/4 layer for the nearest 20 m point on the same road
section, then reports the positional difference.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


LAYER_URL = "https://vegasja.vegagerdin.is/arcgis/rest/services/data/vegakerfi/MapServer/4/query"
DAILY = Path("data/processed/traffic/daily.csv")
LOCATIONS = Path("data/processed/traffic/locations.csv")
ROADS = Path("data/raw/traffic/reference/roads.geojson")
OUTPUT = Path("data/processed/traffic/daily_counter_station_validation.csv")
TOLERANCE_M = 10
WORKERS = 8


def query(site: tuple[str, str, int, float, float, tuple[int, ...]]) -> dict[str, object]:
    """Fetch the matching official 20 m point for one road-section/station."""
    road, section, station, x, y, section_ids = site
    if not section_ids:
        return {"road_section": f"{road}-{section}", "station_id": station, "status": "no_road_section_id"}
    where = (
        f"IDKAFLI IN ({','.join(map(str, section_ids))}) AND "
        f"STOD BETWEEN {max(0, station - TOLERANCE_M)} AND {station + TOLERANCE_M}"
    )
    parameters = {"where": where, "outFields": "STOD,IDKAFLI", "returnGeometry": "true", "outSR": "3057", "f": "geojson"}
    with urlopen(f"{LAYER_URL}?{urlencode(parameters)}", timeout=90) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    features = payload.get("features", [])
    if not features:
        return {"road_section": f"{road}-{section}", "station_id": station, "status": "no_20m_point"}
    feature = min(
        features,
        key=lambda item: abs(float(item["properties"]["STOD"]) - station),
    )
    point = feature["geometry"]["coordinates"]
    distance = math.hypot(float(point[0]) - x, float(point[1]) - y)
    return {
        "road_section": f"{road}-{section}", "station_id": station,
        "status": "matched", "official_station_m": float(feature["properties"]["STOD"]),
        "station_difference_m": abs(float(feature["properties"]["STOD"]) - station),
        "coordinate_difference_m": distance,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-d", "--daily", type=Path, default=DAILY)
    parser.add_argument("-l", "--locations", type=Path, default=LOCATIONS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    daily = pd.read_csv(args.daily, low_memory=False)
    locations = pd.read_csv(args.locations, low_memory=False)
    sites = daily[["year", "counter_site_id", "road_section", "station_id"]].drop_duplicates()
    sites = sites.merge(
        locations[
            [
                "year", "counter_site_id", "location_method",
                "location_x_3057", "location_y_3057",
            ]
        ],
        on=["year", "counter_site_id"],
        how="left",
        validate="one_to_one",
    )
    roads = json.loads(ROADS.read_text(encoding="utf-8"))["features"]
    section_ids: dict[str, set[int]] = {}
    for feature in roads:
        properties = feature["properties"]
        key = f"{properties['NRVEGUR']}-{str(properties['NRKAFLI']).lower()}"
        section_ids.setdefault(key, set()).add(int(properties["IDKAFLI"]))
    sites = sites.loc[
        sites["location_method"].eq("station_interpolated_from_official_road_geometry"),
        ["road_section", "station_id", "location_x_3057", "location_y_3057"],
    ].drop_duplicates()
    tasks = []
    for row in sites.itertuples(index=False):
        road, section = str(row.road_section).split("-", maxsplit=1)
        tasks.append((
            road, section, int(row.station_id), float(row.location_x_3057), float(row.location_y_3057),
            tuple(sorted(section_ids.get(str(row.road_section).lower(), set()))),
        ))
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        rows = list(executor.map(query, tasks))
    result = pd.DataFrame(rows).sort_values(["status", "road_section", "station_id"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    matched = result[result["status"].eq("matched")]
    print(f"Matched {len(matched):,}/{len(result):,} sites to an official 20 m point.")
    if len(matched):
        print(f"Median coordinate difference: {matched['coordinate_difference_m'].median():.2f} m")


if __name__ == "__main__":
    main()
