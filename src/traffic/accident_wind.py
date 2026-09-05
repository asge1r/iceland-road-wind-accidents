"""Match daily-counter accidents to the counter's own weather station."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


ACCIDENTS = Path("data/processed/accidents/rural_injury.csv")
DAILY = Path("data/processed/traffic/daily_weather.csv")
LOCATIONS = Path("data/processed/traffic/locations.csv")
STATIONS = Path("data/raw/weather/stations.csv")
WEATHER = Path("data/processed/weather/weather.parquet")
OUTPUT = Path("data/processed/traffic/accident_wind.csv")
EARTH_RADIUS_KM = 6371.0088


def require_columns(data: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(data)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def distance_km(lon: float, lat: float, candidates: pd.DataFrame) -> np.ndarray:
    lon1, lat1 = np.radians([lon, lat])
    lon2 = np.radians(candidates["lon"].to_numpy(float))
    lat2 = np.radians(candidates["lat"].to_numpy(float))
    value = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(value))


def assign_counters(accidents: pd.DataFrame, locations: pd.DataFrame) -> pd.DataFrame:
    locations = locations.rename(
        columns={
            "counter_site_id": "counter_id",
            "location_lon": "lon",
            "location_lat": "lat",
        }
    )
    locations["road_section"] = locations["counter_id"].astype("string").str.split(":").str[0]
    locations["road_section"] = locations["road_section"].str.strip().str.lower()
    locations = locations.dropna(subset=["lon", "lat"])
    if locations.duplicated(["year", "counter_id"]).any():
        raise ValueError("Counter locations are not unique by year and counter")
    groups = {
        key: group.reset_index(drop=True)
        for key, group in locations.groupby(["year", "road_section"], observed=True)
    }
    rows: list[dict[str, object]] = []
    for accident in accidents.itertuples(index=False):
        candidates = groups.get((accident.year, accident.road_section))
        if candidates is None or candidates.empty:
            continue
        distances = distance_km(accident.lon, accident.lat, candidates)
        position = int(np.argmin(distances))
        rows.append(
            {
                "id": int(accident.id),
                "timestamp": accident.timestamp,
                "date": accident.timestamp.normalize(),
                "year": int(accident.year),
                "counter_id": candidates.iloc[position]["counter_id"],
                "counter_distance_km": float(distances[position]),
                "accident_lon": float(accident.lon),
                "accident_lat": float(accident.lat),
            }
        )
    return pd.DataFrame(rows)


def candidate_times(events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    eligible = events[
        events["counter_distance_km"].le(20)
        & events["counter_weather_station_id"].notna()
        & events["counter_weather_station_dist_km"].le(20)
        & events["counter_station_accident_distance_km"].le(20)
    ]
    for event in eligible.itertuples(index=False):
        for weather_time in {event.timestamp.floor("10min"), event.timestamp.ceil("10min")}:
            difference = abs((weather_time - event.timestamp).total_seconds()) / 60
            if difference <= 5:
                rows.append(
                    {
                        "id": event.id,
                        "counter_weather_station_id": int(event.counter_weather_station_id),
                        "weather_time": weather_time,
                        "weather_time_difference_minutes": difference,
                    }
                )
    return pd.DataFrame(rows)


def read_weather(path: Path, candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=["counter_weather_station_id", "weather_time", "f"])
    needed = {
        int(station): np.sort(group["weather_time"].to_numpy(dtype="datetime64[us]").astype("int64"))
        for station, group in candidates.groupby("counter_weather_station_id")
    }
    hits: list[pd.DataFrame] = []
    source = pq.ParquetFile(path)
    for batch in source.iter_batches(batch_size=1_000_000, columns=["station", "time", "f"]):
        station = batch.column(0).to_numpy(zero_copy_only=False)
        timestamp = batch.column(1).to_numpy(zero_copy_only=False).astype("datetime64[us]").astype("int64")
        keep = np.zeros(len(station), dtype=bool)
        for station_id in np.unique(station):
            target = needed.get(int(station_id))
            if target is None:
                continue
            positions_in_batch = np.flatnonzero(station == station_id)
            values = timestamp[positions_in_batch]
            positions = np.searchsorted(target, values)
            valid = positions < len(target)
            matched = np.zeros(len(values), dtype=bool)
            matched[valid] = target[positions[valid]] == values[valid]
            keep[positions_in_batch[matched]] = True
        if keep.any():
            hits.append(
                batch.filter(keep).to_pandas().rename(
                    columns={
                        "station": "counter_weather_station_id",
                        "time": "weather_time",
                    }
                )
            )
    if not hits:
        return pd.DataFrame(columns=["counter_weather_station_id", "weather_time", "f"])
    return pd.concat(hits, ignore_index=True).drop_duplicates(
        ["counter_weather_station_id", "weather_time"]
    )


def build(
    accidents_path: Path,
    daily_path: Path,
    locations_path: Path,
    stations_path: Path,
    weather_path: Path,
) -> pd.DataFrame:
    accidents = pd.read_csv(accidents_path, low_memory=False)
    require_columns(
        accidents,
        {"id", "timestamp", "lat", "lon", "registered_road_section"},
        "Accident input",
    )
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"], errors="raise")
    accidents["year"] = accidents["timestamp"].dt.year
    accidents = accidents[accidents["year"].between(2019, 2024)].copy()
    accidents["road_section"] = (
        accidents["registered_road_section"].astype("string").str.strip().str.lower()
    )
    locations = pd.read_csv(locations_path)
    require_columns(
        locations,
        {"year", "counter_site_id", "location_lon", "location_lat"},
        "Counter-location input",
    )
    events = assign_counters(accidents, locations)
    if events["id"].duplicated().any():
        raise ValueError(
            "Counter assignment produced multiple rows for an accident"
        )
    daily = pd.read_csv(daily_path, low_memory=False)
    require_columns(
        daily,
        {"date", "counter_site_id", "weather_station_id", "weather_station_dist_km"},
        "Counter-day weather input",
    )
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    station_day = daily[
        ["counter_site_id", "date", "weather_station_id", "weather_station_dist_km"]
    ].rename(
        columns={
            "counter_site_id": "counter_id",
            "weather_station_id": "counter_weather_station_id",
            "weather_station_dist_km": "counter_weather_station_dist_km",
        }
    )
    events = events.merge(
        station_day, on=["counter_id", "date"], how="left", validate="many_to_one"
    )
    stations = pd.read_csv(stations_path, usecols=["station", "lat", "lon"]).rename(
        columns={
            "station": "counter_weather_station_id",
            "lat": "station_lat",
            "lon": "station_lon",
        }
    )
    events = events.merge(
        stations, on="counter_weather_station_id", how="left", validate="many_to_one"
    )
    valid_station = events[["station_lon", "station_lat"]].notna().all(axis=1)
    events["counter_station_accident_distance_km"] = np.nan
    if valid_station.any():
        lon1 = np.radians(events.loc[valid_station, "accident_lon"].to_numpy(float))
        lat1 = np.radians(events.loc[valid_station, "accident_lat"].to_numpy(float))
        lon2 = np.radians(events.loc[valid_station, "station_lon"].to_numpy(float))
        lat2 = np.radians(events.loc[valid_station, "station_lat"].to_numpy(float))
        value = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
        events.loc[valid_station, "counter_station_accident_distance_km"] = (
            2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(value))
        )

    candidates = candidate_times(events)
    weather = read_weather(weather_path, candidates)
    matched = candidates.merge(
        weather,
        on=["counter_weather_station_id", "weather_time"],
        how="inner",
        validate="many_to_one",
    )
    matched = matched[matched["f"].between(0, 45, inclusive="left")]
    matched = matched.sort_values(
        ["id", "weather_time_difference_minutes", "weather_time"]
    ).drop_duplicates("id")
    columns = [
        "id", "year", "date", "counter_id", "counter_distance_km",
        "counter_weather_station_id", "counter_weather_station_dist_km",
        "counter_station_accident_distance_km",
    ]
    result = events[columns].merge(
        matched[["id", "weather_time", "weather_time_difference_minutes", "f"]],
        on="id", how="left", validate="one_to_one",
    )
    if result["id"].duplicated().any():
        raise ValueError("Daily-counter accident weather is not unique by id")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-d", "--daily-weather", type=Path, default=DAILY)
    parser.add_argument("-l", "--locations", type=Path, default=LOCATIONS)
    parser.add_argument("-s", "--stations", type=Path, default=STATIONS)
    parser.add_argument("-w", "--weather", type=Path, default=WEATHER)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build(args.accidents, args.daily_weather, args.locations, args.stations, args.weather)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"counter_candidates={len(result):,}")
    print(f"same_station_weather_matches={result['f'].notna().sum():,}")
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
