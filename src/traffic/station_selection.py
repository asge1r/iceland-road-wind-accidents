"""Shared spatial candidates and time-specific weather eligibility for traffic."""

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.neighbors import BallTree

from src.traffic.daily_common import EARTH_RADIUS_KM

STATIONS = Path("data/raw/weather/stations.csv")
SECTIONS = Path("data/processed/traffic/counter_sections.csv")
DISTANCE_LIMIT_KM = 20.


def valid_wind(f, fg):
    return np.isfinite(f) & (f >= 0) & np.isfinite(fg) & (fg >= 0)


def station_candidates(sections: pd.DataFrame, stations: pd.DataFrame,
                       limit_km: float = DISTANCE_LIMIT_KM) -> pd.DataFrame:
    """Rank stations from counter locations, independently of accident occurrence."""
    if limit_km <= 0:
        raise ValueError("Station distance limit must be positive")
    stations = stations.dropna(subset=["station", "lat", "lon"]).drop_duplicates("station").copy()
    stations["station"] = stations.station.astype(int)
    located = sections.dropna(subset=["counter_location_lat", "counter_location_lon"])
    columns = ["counter_section_id", "weather_station_id", "weather_station_dist_km"]
    if stations.empty or located.empty:
        return pd.DataFrame(columns=columns)
    tree = BallTree(np.radians(stations[["lat", "lon"]]), metric="haversine")
    indices, distances = tree.query_radius(
        np.radians(located[["counter_location_lat", "counter_location_lon"]]),
        r=limit_km/EARTH_RADIUS_KM, return_distance=True)
    rows = [(section, int(stations.iloc[index].station), float(distance * EARTH_RADIUS_KM))
            for section, near, lengths in zip(located.counter_section_id, indices, distances, strict=True)
            for index, distance in zip(near, lengths, strict=True)]
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["counter_section_id", "weather_station_dist_km", "weather_station_id"])


def available_station_years(path: Path) -> dict[int, set[int]]:
    """Use actual valid daytime records, not catalogue dates or archive membership."""
    available: dict[int, set[int]] = {}
    for batch in pq.ParquetFile(path).iter_batches(batch_size=2_000_000,
                                                  columns=["station", "time", "f", "fg"]):
        stamp = batch.column("time").to_numpy(zero_copy_only=False).astype("datetime64[us]")
        midnight = stamp == stamp.astype("datetime64[D]")
        dates = stamp.astype("datetime64[D]") - midnight.astype("timedelta64[D]")
        years = dates.astype("datetime64[Y]").astype(int) + 1970
        hours = stamp.astype("datetime64[h]").astype(int) % 24
        use = ((hours >= 7) | midnight) & (stamp.astype(np.int64) % 600_000_000 == 0)
        use &= valid_wind(batch.column("f").to_numpy(zero_copy_only=False), batch.column("fg").to_numpy(zero_copy_only=False))
        station = batch.column("station").to_numpy(zero_copy_only=False)
        for year in np.unique(years[use]):
            available.setdefault(int(year), set()).update(map(int, np.unique(station[use & (years == year)])))
    return available


def nearest_valid(stations: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Select first eligible candidate at each instant; values: station × time × f/fg/t.

    The caller supplies the shared distance/id order. A missing temperature
    does not change the wind station; it removes only temperature exposure.
    """
    selected = np.full(values.shape[1], -1, dtype=np.int32)
    weather = np.full((values.shape[1], 3), np.nan, dtype=values.dtype)
    for station, row in zip(stations, values, strict=True):
        use = (selected < 0) & valid_wind(row[:, 0], row[:, 1])
        selected[use] = station
        weather[use] = row[use]
    return selected, weather
