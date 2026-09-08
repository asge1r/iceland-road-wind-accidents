"""Build road-period wind frequencies and assign road sections to stations."""

from __future__ import annotations

import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pyproj import Transformer
from sklearn.neighbors import BallTree

from src.traffic.road_common import (
    DEFAULT_ROAD_GEOMETRIES,
    EARTH_RADIUS_KM,
    FIRST_YEAR,
    LAST_YEAR,
    PRIMARY_STATION_RADIUS_KM,
    TRAFFIC_PERIOD_ORDER,
    normalize_section,
    traffic_period_index,
)
from src.weather.frequency import F_FIVE_MS_UPPER_BOUNDS, labels


def build_period_wind_frequency(
    weather_path: Path,
    output_path: Path,
    assigned_stations: np.ndarray,
    max_row_groups: int | None = None,
) -> pd.DataFrame:
    """Count 5 m/s mean-wind intervals by station, year, and traffic period."""
    parquet_file = pq.ParquetFile(weather_path)
    row_groups = parquet_file.metadata.num_row_groups
    if max_row_groups is not None:
        row_groups = min(row_groups, max_row_groups)

    assigned_stations = np.sort(assigned_stations.astype(np.int32))
    year_count = LAST_YEAR - FIRST_YEAR + 1
    period_count = len(TRAFFIC_PERIOD_ORDER)
    group_count = len(assigned_stations) * year_count * period_count
    totals = np.zeros(group_count, dtype=np.int64)
    counts = np.zeros(
        (group_count, len(F_FIVE_MS_UPPER_BOUNDS) + 1), dtype=np.int64
    )
    rows_scanned = 0
    rows_used = 0
    started = time.perf_counter()

    for row_group in range(row_groups):
        table = parquet_file.read_row_group(row_group, columns=["station", "time", "f"])
        station = table.column("station").to_numpy()
        timestamp = table.column("time").to_numpy().astype("datetime64[us]")
        year = timestamp.astype("datetime64[Y]").astype(np.int64) + 1970
        keep = (
            (year >= FIRST_YEAR)
            & (year <= LAST_YEAR)
            & np.isin(station, assigned_stations)
        )
        rows_scanned += len(table)
        if keep.any():
            station = station[keep]
            timestamp = timestamp[keep]
            year = year[keep]
            wind = table.column("f").to_numpy()[keep]
            month = timestamp.astype("datetime64[M]").astype(np.int64) % 12 + 1
            station_index = np.searchsorted(assigned_stations, station)
            group = (
                (station_index * year_count + (year - FIRST_YEAR)) * period_count
                + traffic_period_index(month)
            )
            totals += np.bincount(group, minlength=group_count)
            wind_bin = np.searchsorted(F_FIVE_MS_UPPER_BOUNDS, wind, side="right")
            counts += np.bincount(
                group * counts.shape[1] + wind_bin, minlength=counts.size
            ).reshape(counts.shape)
            rows_used += int(keep.sum())
        if (row_group + 1) % 25 == 0 or row_group + 1 == row_groups:
            print(
                f"traffic_period_wind row_groups={row_group + 1}/{row_groups} "
                f"rows_scanned={rows_scanned:,} rows_used={rows_used:,}",
                flush=True,
            )

    group, bin_index = np.nonzero(counts)
    station_index = group // (year_count * period_count)
    remainder = group % (year_count * period_count)
    lower_bounds = np.concatenate(([0.0], F_FIVE_MS_UPPER_BOUNDS))
    upper_bounds = np.concatenate((F_FIVE_MS_UPPER_BOUNDS, [np.inf]))
    result = pd.DataFrame(
        {
            "weather_station_id": assigned_stations[station_index],
            "year": FIRST_YEAR + remainder // period_count,
            "traffic_period": np.array(TRAFFIC_PERIOD_ORDER)[remainder % period_count],
            "variable": "f_5m",
            "bin_label": np.array(labels(F_FIVE_MS_UPPER_BOUNDS))[bin_index],
            "bin_lower_ms": lower_bounds[bin_index],
            "bin_upper_ms": upper_bounds[bin_index],
            "measurement_count": counts[group, bin_index],
            "total_measurements_in_period": totals[group],
        }
    )
    result["frequency_pct"] = (
        100 * result["measurement_count"] / result["total_measurements_in_period"]
    )
    result = result.sort_values(
        ["weather_station_id", "year", "traffic_period", "bin_lower_ms"]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(
        f"wrote={output_path} rows={len(result):,} "
        f"elapsed={time.perf_counter() - started:.1f}s",
        flush=True,
    )
    return result

def build_station_candidates(
    section_scope: pd.DataFrame,
    midpoint_path: Path,
    station_path: Path,
    radius_km: float = PRIMARY_STATION_RADIUS_KM,
) -> pd.DataFrame:
    """Find all weather stations within the primary radius of each midpoint."""
    midpoints = pd.read_csv(
        midpoint_path,
        usecols=["road_section", "midpoint_lat", "midpoint_lon"],
    )
    midpoints["road_section"] = normalize_section(midpoints["road_section"])
    missing_sections = set(section_scope["road_section"]) - set(midpoints["road_section"])
    if missing_sections:
        roads = pd.read_parquet(
            DEFAULT_ROAD_GEOMETRIES, columns=["road_section", "paths_json"]
        )
        roads["road_section"] = normalize_section(roads["road_section"])
        roads = roads[roads["road_section"].isin(missing_sections)].copy()
        transformer = Transformer.from_crs(
            "EPSG:3057", "EPSG:4326", always_xy=True
        )

        def geometry_midpoint(paths_json: str) -> tuple[float, float]:
            paths = json.loads(paths_json)
            segments: list[tuple[np.ndarray, np.ndarray, float]] = []
            total = 0.0
            for path in paths:
                vertices = np.asarray([point[:2] for point in path], dtype=float)
                for start, end in zip(vertices[:-1], vertices[1:], strict=True):
                    length = float(np.linalg.norm(end - start))
                    if length > 0:
                        segments.append((start, end, length))
                        total += length
            target = total / 2
            traversed = 0.0
            for start, end, length in segments:
                if traversed + length >= target:
                    point = start + (target - traversed) / length * (end - start)
                    lon, lat = transformer.transform(float(point[0]), float(point[1]))
                    return lat, lon
                traversed += length
            return np.nan, np.nan

        derived = roads["paths_json"].map(geometry_midpoint)
        roads["midpoint_lat"] = derived.str[0]
        roads["midpoint_lon"] = derived.str[1]
        midpoints = pd.concat(
            [
                midpoints,
                roads[["road_section", "midpoint_lat", "midpoint_lon"]],
            ],
            ignore_index=True,
        ).drop_duplicates("road_section", keep="first")
    midpoints = section_scope.merge(
        midpoints, on="road_section", how="left", validate="one_to_one"
    ).dropna(subset=["midpoint_lat", "midpoint_lon"])

    stations = pd.read_csv(
        station_path, usecols=["station", "name", "lat", "lon"]
    ).drop_duplicates("station")
    stations = stations.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    tree = BallTree(
        np.radians(stations[["lat", "lon"]].to_numpy()), metric="haversine"
    )
    indices, distances = tree.query_radius(
        np.radians(midpoints[["midpoint_lat", "midpoint_lon"]].to_numpy()),
        r=radius_km / EARTH_RADIUS_KM,
        return_distance=True,
        sort_results=True,
    )

    rows: list[tuple[str, int, str, float]] = []
    for section, station_indices, distance_radians in zip(
        midpoints["road_section"], indices, distances, strict=True
    ):
        for station_index, distance_radian in zip(
            station_indices, distance_radians, strict=True
        ):
            station = stations.iloc[station_index]
            rows.append(
                (
                    section,
                    int(station["station"]),
                    str(station["name"]),
                    float(distance_radian * EARTH_RADIUS_KM),
                )
            )
    return pd.DataFrame(
        rows,
        columns=[
            "road_section",
            "weather_station_id",
            "weather_station_name",
            "weather_station_distance_km",
        ],
    )

def assign_nearest_valid_station(
    annual: pd.DataFrame,
    section_scope: pd.DataFrame,
    candidates: pd.DataFrame,
    wind: pd.DataFrame,
) -> pd.DataFrame:
    """Assign the closest station with clean data for each section/period."""
    panel = annual.merge(
        section_scope, on="road_section", how="inner", validate="many_to_one"
    )
    periods = pd.DataFrame(
        {
            "traffic_period": TRAFFIC_PERIOD_ORDER,
            "traffic_period_order": range(len(TRAFFIC_PERIOD_ORDER)),
        }
    )
    panel = panel.assign(_cross=1).merge(periods.assign(_cross=1), on="_cross")
    panel = panel.drop(columns="_cross")

    available = wind[["weather_station_id", "year", "traffic_period"]].drop_duplicates()
    eligible = candidates.merge(
        available,
        on="weather_station_id",
        how="inner",
        validate="many_to_many",
    )
    eligible = eligible.sort_values(
        [
            "road_section",
            "year",
            "traffic_period",
            "weather_station_distance_km",
            "weather_station_id",
        ]
    ).drop_duplicates(["road_section", "year", "traffic_period"], keep="first")
    assigned = panel.merge(
        eligible,
        on=["road_section", "year", "traffic_period"],
        how="left",
        validate="one_to_one",
    )
    has_spatial_candidate = assigned["road_section"].isin(
        candidates["road_section"].unique()
    )
    assigned["station_assignment_method"] = np.select(
        [
            assigned["weather_station_id"].notna(),
            has_spatial_candidate,
        ],
        [
            "nearest_station_to_section_midpoint_with_clean_period_data_within_20km",
            "nearby_stations_but_no_clean_period_data",
        ],
        default="no_station_within_20km_of_section_midpoint",
    )
    return assigned
