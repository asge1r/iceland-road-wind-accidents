"""Build one counter-section record per physical counter site and year.

Lane channels on the same official road section are combined when their PDF
road stations span no more than the selected tolerance. Counter-sections split
the annual road-section length at midpoints between the resulting sites.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pyproj import Transformer
from sklearn.neighbors import BallTree

from src.traffic.counter_weather import weather_station_ids
from src.traffic.daily_common import EARTH_RADIUS_KM, normalize_section
from src.traffic.locate_counters import interpolate, load_roads


DAILY = Path("data/processed/traffic/daily_raw.csv")
ANNUAL = Path("data/processed/traffic/annual.csv")
ROADS = Path("data/raw/traffic/reference/roads.geojson")
STATIONS = Path("data/raw/weather/stations.csv")
WEATHER = Path("data/processed/weather/weather.parquet")
OUTPUT = Path("data/processed/traffic/counter_sections.csv")


def joined_values(values: pd.Series, separator: str) -> str:
    items: set[str] = set()
    for value in values.dropna().astype(str):
        items.update(item.strip() for item in value.split(separator) if item.strip())
    return separator.join(
        sorted(
            items,
            key=lambda item: (0, int(item)) if item.isdigit() else (1, item),
        )
    )


def group_counter_sites(daily: pd.DataFrame, tolerance_m: float) -> pd.DataFrame:
    """Combine distinct lane channels whose complete road-station span is small."""
    required = {
        "year", "road_section", "station_id", "site_name", "source_fastnr",
    }
    missing = required - set(daily)
    if missing:
        raise ValueError(f"Daily counter data are missing columns: {sorted(missing)}")
    if tolerance_m < 0:
        raise ValueError("Counter-site tolerance must be nonnegative")

    source = daily[list(required)].copy()
    source["road_section"] = normalize_section(source["road_section"])
    source["station_id"] = pd.to_numeric(source["station_id"], errors="raise")
    exact = source.groupby(
        ["year", "road_section", "station_id"], as_index=False
    ).agg(
        site_name=("site_name", lambda values: joined_values(values, " | ")),
        source_fastnr=("source_fastnr", lambda values: joined_values(values, "|")),
    )

    rows: list[dict[str, object]] = []
    for (year, road_section), section in exact.groupby(
        ["year", "road_section"], sort=True
    ):
        positions = sorted(section["station_id"].unique())
        clusters: list[list[float]] = []
        cluster: list[float] = []
        for position in positions:
            if not cluster or position - cluster[0] <= tolerance_m:
                cluster.append(float(position))
            else:
                clusters.append(cluster)
                cluster = [float(position)]
        if cluster:
            clusters.append(cluster)

        for cluster_number, positions_in_site in enumerate(clusters, start=1):
            selected = section[section["station_id"].isin(positions_in_site)]
            station_min = min(positions_in_site)
            station_max = max(positions_in_site)
            station = (station_min + station_max) / 2
            fastnr = joined_values(selected["source_fastnr"], "|")
            rows.append(
                {
                    "year": int(year),
                    "counter_section_id": (
                        f"{int(year)}:{road_section}:{station_min:g}-{station_max:g}"
                    ),
                    "road_section": str(road_section),
                    "counter_station_m": station,
                    "source_station_min_m": station_min,
                    "source_station_max_m": station_max,
                    "channel_count": len(fastnr.split("|")) if fastnr else 0,
                    "source_fastnr": fastnr,
                    "site_name": joined_values(selected["site_name"], " | "),
                    "site_sequence": cluster_number,
                }
            )
    return pd.DataFrame(rows)


def add_counter_section_lengths(
    sites: pd.DataFrame, annual_path: Path
) -> pd.DataFrame:
    """Split each annual official road-section length at counter midpoints."""
    annual = pd.read_csv(
        annual_path,
        usecols=["year", "road_section", "section_length_km"],
        low_memory=False,
    )
    annual["road_section"] = normalize_section(annual["road_section"])
    if annual.duplicated(["year", "road_section"]).any():
        raise ValueError("Annual traffic is not unique on year + road_section")
    result = sites.merge(
        annual, on=["year", "road_section"], how="left", validate="many_to_one"
    ).rename(columns={"section_length_km": "official_road_section_length_km"})
    result["counter_section_start_km"] = np.nan
    result["counter_section_end_km"] = np.nan

    for _, group in result.groupby(["year", "road_section"], sort=False):
        length = group["official_road_section_length_km"].iloc[0]
        if pd.isna(length) or float(length) <= 0:
            continue
        valid = group[
            group["counter_station_m"].between(0, float(length) * 1000)
        ].sort_values("counter_station_m")
        if valid.empty:
            continue
        positions = valid["counter_station_m"].to_numpy(dtype=float) / 1000
        boundaries = np.concatenate(
            ([0.0], (positions[:-1] + positions[1:]) / 2, [float(length)])
        )
        result.loc[valid.index, "counter_section_start_km"] = boundaries[:-1]
        result.loc[valid.index, "counter_section_end_km"] = boundaries[1:]

    result["counter_section_length_km"] = (
        result["counter_section_end_km"] - result["counter_section_start_km"]
    )
    return result


def add_locations(sites: pd.DataFrame, roads_path: Path) -> pd.DataFrame:
    """Interpolate each counter location along its official road geometry."""
    roads = load_roads(roads_path)
    transformer = Transformer.from_crs("EPSG:3057", "EPSG:4326", always_xy=True)
    rows = []
    for site in sites.itertuples(index=False):
        road, section = str(site.road_section).split("-", maxsplit=1)
        xy = None
        for feature in roads.get((road, section.lower()), []):
            try:
                xy = interpolate(feature, float(site.counter_station_m))
                break
            except ValueError:
                continue
        if xy is None:
            rows.append((np.nan, np.nan))
        else:
            lon, lat = transformer.transform(*xy)
            rows.append((lat, lon))
    result = sites.copy()
    result[["counter_location_lat", "counter_location_lon"]] = rows
    return result


def add_nearest_weather_station(
    counters: pd.DataFrame,
    stations_path: Path,
    weather_path: Path,
    distance_limit_km: float,
) -> pd.DataFrame:
    """Attach the nearest station represented in the cleaned weather file."""
    if distance_limit_km <= 0:
        raise ValueError("Weather-station distance limit must be positive")
    valid_ids = weather_station_ids(pq.ParquetFile(weather_path))
    stations = pd.read_csv(
        stations_path, usecols=["station", "name", "lat", "lon"]
    ).dropna(subset=["station", "lat", "lon"])
    stations["station"] = pd.to_numeric(stations["station"], errors="raise").astype(int)
    stations = stations[stations["station"].isin(valid_ids)].drop_duplicates("station")
    if stations.empty:
        raise ValueError("No station in the catalogue occurs in the cleaned weather data")

    result = counters.copy()
    result["weather_station_id"] = pd.NA
    result["weather_station_name"] = pd.NA
    result["weather_station_dist_km"] = np.nan
    located = result.dropna(subset=["counter_location_lat", "counter_location_lon"])
    if located.empty:
        return result

    tree = BallTree(np.radians(stations[["lat", "lon"]]), metric="haversine")
    distance, indices = tree.query(
        np.radians(located[["counter_location_lat", "counter_location_lon"]]), k=1
    )
    nearest = stations.iloc[indices[:, 0]].reset_index(drop=True)
    result.loc[located.index, "weather_station_id"] = nearest["station"].to_numpy()
    result.loc[located.index, "weather_station_name"] = nearest["name"].to_numpy()
    result.loc[located.index, "weather_station_dist_km"] = (
        distance[:, 0] * EARTH_RADIUS_KM
    )
    result["weather_station_within_limit"] = result[
        "weather_station_dist_km"
    ].le(distance_limit_km)
    return result


def build(
    daily_path: Path,
    annual_path: Path,
    roads_path: Path,
    stations_path: Path,
    weather_path: Path,
    output_path: Path,
    tolerance_m: float,
    distance_limit_km: float,
) -> pd.DataFrame:
    daily = pd.read_csv(daily_path, dtype={"source_fastnr": "string"}, low_memory=False)
    sites = group_counter_sites(daily, tolerance_m)
    sections = add_counter_section_lengths(sites, annual_path)
    sections = add_locations(sections, roads_path)
    sections = add_nearest_weather_station(
        sections, stations_path, weather_path, distance_limit_km
    )
    columns = [
        "year", "counter_section_id", "road_section",
        "counter_location_lat", "counter_location_lon",
        "counter_section_length_km", "weather_station_id",
        "weather_station_name", "weather_station_dist_km",
        "weather_station_within_limit", "counter_station_m",
        "counter_section_start_km", "counter_section_end_km",
        "official_road_section_length_km", "source_station_min_m",
        "source_station_max_m", "channel_count", "source_fastnr", "site_name",
    ]
    sections = sections.sort_values(
        ["year", "road_section", "counter_station_m"]
    )[columns]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sections.to_csv(output_path, index=False)
    print(
        f"Wrote {len(sections):,} counter-sections to {output_path}; "
        f"length available for {sections['counter_section_length_km'].notna().sum():,}, "
        f"location available for {sections['counter_location_lat'].notna().sum():,}, "
        f"nearest weather station within {distance_limit_km:g} km for "
        f"{sections['weather_station_within_limit'].sum():,}."
    )
    return sections


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DAILY)
    parser.add_argument("-a", "--annual", type=Path, default=ANNUAL)
    parser.add_argument("-r", "--roads", type=Path, default=ROADS)
    parser.add_argument("-s", "--stations", type=Path, default=STATIONS)
    parser.add_argument("-w", "--weather", type=Path, default=WEATHER)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-t", "--tolerance-m", type=float, default=20)
    parser.add_argument("-d", "--distance-limit-km", type=float, default=20)
    args = parser.parse_args()
    build(
        args.input, args.annual, args.roads, args.stations, args.weather,
        args.output, args.tolerance_m, args.distance_limit_km,
    )


if __name__ == "__main__":
    main()
