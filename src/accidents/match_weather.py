"""Match rural accidents to the nearest valid 10-minute weather observation."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.neighbors import BallTree


DEFAULT_ACCIDENTS = Path("data/processed/accidents/all.parquet")
DEFAULT_WEATHER = Path("data/processed/weather/weather.parquet")
DEFAULT_STATIONS = Path("data/raw/weather/stations.csv")
DEFAULT_OUTPUT = Path(
    "data/processed/accidents/rural_injury.parquet"
)
DEFAULT_COVERAGE = Path(
    "archive/generated_diagnostics/oe/accident_weather_coverage.csv"
)
DEFAULT_BY_YEAR = Path(
    "archive/generated_diagnostics/accident_weather_coverage_by_year.csv"
)
DEFAULT_NOTES = Path(
    "archive/generated_diagnostics/accident_weather_notes.txt"
)

PRIMARY_DISTANCE_KM = 20.0
SENSITIVITY_DISTANCE_KM = 30.0
TIME_TOLERANCE_MINUTES = 5.0
EARTH_RADIUS_KM = 6371.0


def load_accidents(path: Path, start: str, end: str) -> pd.DataFrame:
    accidents = pd.read_parquet(path)
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"])
    accidents["meidsli"] = pd.to_numeric(accidents["meidsli"], errors="coerce")
    scope = (
        accidents["timestamp"].between(pd.Timestamp(start), pd.Timestamp(end))
        & accidents["urban_rural"].eq("Rural")
        & accidents["meidsli"].lt(4)
    )
    accidents = accidents.loc[scope].copy().reset_index(drop=True)
    accidents = accidents.rename(
        columns={
            "station_id": "legacy_station_id",
            "station_dist_km": "legacy_station_dist_km",
        }
    )
    accidents.index.name = "acc_index"
    return accidents


def weather_station_ids(weather_file: pq.ParquetFile) -> set[int]:
    station_ids: set[int] = set()
    for batch in weather_file.iter_batches(batch_size=2_000_000, columns=["station"]):
        station_ids.update(map(int, np.unique(batch.column(0).to_numpy())))
    return station_ids


def load_stations(path: Path, station_ids: set[int]) -> pd.DataFrame:
    stations = pd.read_csv(path)
    stations = stations[stations["station"].isin(station_ids)].copy()
    stations = stations.drop_duplicates("station").dropna(subset=["lat", "lon"])
    return stations.reset_index(drop=True)


def build_candidates(
    accidents: pd.DataFrame, stations: pd.DataFrame
) -> tuple[pd.DataFrame, np.ndarray]:
    tree = BallTree(
        np.radians(stations[["lat", "lon"]].to_numpy()), metric="haversine"
    )
    indices, distances = tree.query_radius(
        np.radians(accidents[["lat", "lon"]].to_numpy()),
        r=SENSITIVITY_DISTANCE_KM / EARTH_RADIUS_KM,
        return_distance=True,
        sort_results=True,
    )

    rows: list[tuple[int, int, float, pd.Timestamp, float]] = []
    for accident_index, (station_indices, distance_radians) in enumerate(
        zip(indices, distances, strict=True)
    ):
        accident_time = accidents.loc[accident_index, "timestamp"]
        for station_index, distance_radian in zip(
            station_indices, distance_radians, strict=True
        ):
            for weather_time in {
                accident_time.floor("10min"),
                accident_time.ceil("10min"),
            }:
                difference = abs((weather_time - accident_time).total_seconds()) / 60
                if difference <= TIME_TOLERANCE_MINUTES:
                    rows.append(
                        (
                            accident_index,
                            int(stations.loc[station_index, "station"]),
                            float(distance_radian * EARTH_RADIUS_KM),
                            weather_time,
                            difference,
                        )
                    )

    candidates = pd.DataFrame(
        rows,
        columns=[
            "acc_index",
            "weather_station_id",
            "weather_station_dist_km",
            "weather_time",
            "weather_time_difference_minutes",
        ],
    )
    has_station_within_30 = np.fromiter(
        (len(station_indices) > 0 for station_indices in indices),
        dtype=bool,
        count=len(accidents),
    )
    return candidates, has_station_within_30


def read_candidate_weather(
    weather_file: pq.ParquetFile, candidates: pd.DataFrame
) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(
            columns=["weather_station_id", "weather_time", "f", "fg", "t"]
        )
    keys = candidates[["weather_station_id", "weather_time"]].drop_duplicates()
    needed = {
        int(station_id): np.sort(
            group["weather_time"].to_numpy(dtype="datetime64[us]").astype("int64")
        )
        for station_id, group in keys.groupby("weather_station_id")
    }

    hits: list[pd.DataFrame] = []
    for batch in weather_file.iter_batches(
        batch_size=1_000_000, columns=["station", "time", "f", "fg", "t"]
    ):
        station = batch.column(0).to_numpy(zero_copy_only=False)
        timestamp = (
            batch.column(1)
            .to_numpy(zero_copy_only=False)
            .astype("datetime64[us]")
            .astype("int64")
        )
        keep = np.zeros(len(station), dtype=bool)
        for station_id in np.unique(station):
            target_times = needed.get(int(station_id))
            if target_times is None:
                continue
            locations = np.flatnonzero(station == station_id)
            values = timestamp[locations]
            positions = np.searchsorted(target_times, values)
            valid = positions < len(target_times)
            matched = np.zeros(len(values), dtype=bool)
            matched[valid] = target_times[positions[valid]] == values[valid]
            keep[locations[matched]] = True
        if keep.any():
            hit = batch.filter(keep).to_pandas()
            hits.append(
                hit.rename(
                    columns={"station": "weather_station_id", "time": "weather_time"}
                )
            )

    if not hits:
        return pd.DataFrame(
            columns=["weather_station_id", "weather_time", "f", "fg", "t"]
        )
    return pd.concat(hits, ignore_index=True).drop_duplicates(
        ["weather_station_id", "weather_time"], keep="first"
    )


def select_best(candidates: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    available = candidates.merge(
        weather,
        on=["weather_station_id", "weather_time"],
        how="inner",
        validate="many_to_one",
    )
    return (
        available.sort_values(
            [
                "acc_index",
                "weather_station_dist_km",
                "weather_time_difference_minutes",
                "weather_station_id",
                "weather_time",
            ]
        )
        .drop_duplicates("acc_index", keep="first")
        .reset_index(drop=True)
    )


def assemble_output(
    accidents: pd.DataFrame,
    stations: pd.DataFrame,
    best: pd.DataFrame,
    has_station_within_30: np.ndarray,
) -> pd.DataFrame:
    station_names = stations[["station", "name"]].rename(
        columns={"station": "weather_station_id", "name": "weather_station_name"}
    )
    best = best.merge(
        station_names, on="weather_station_id", how="left", validate="many_to_one"
    )
    output = accidents.reset_index().merge(
        best, on="acc_index", how="left", validate="one_to_one"
    )
    output["has_weather_station_within_30km"] = has_station_within_30
    output["wind_available"] = output["f"].notna() & output["fg"].notna()
    output["temperature_available"] = output["t"].notna()
    output["within_20km"] = output["weather_station_dist_km"].le(
        PRIMARY_DISTANCE_KM
    )
    output["match_status"] = np.select(
        [
            output["within_20km"],
            output["weather_station_dist_km"].between(
                PRIMARY_DISTANCE_KM, SENSITIVITY_DISTANCE_KM, inclusive="right"
            ),
            ~output["has_weather_station_within_30km"],
        ],
        [
            "matched_within_20km",
            "matched_20_to_30km",
            "no_station_within_30km",
        ],
        default="no_valid_wind_within_30km",
    )
    return output.drop(columns="acc_index").sort_values(["timestamp", "nid"])


def coverage_tables(output: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    total = len(output)
    rows = []
    for distance in (10, 20, 30):
        matched = int(output["weather_station_dist_km"].le(distance).sum())
        rows.append(
            {
                "max_station_distance_km": distance,
                "scope_accidents": total,
                "wind_matched_accidents": matched,
                "wind_coverage_pct": 100 * matched / total,
                "matched_with_temperature": int(
                    (
                        output["weather_station_dist_km"].le(distance)
                        & output["temperature_available"]
                    ).sum()
                ),
            }
        )
    coverage = pd.DataFrame(rows)

    annual = output.assign(year=output["timestamp"].dt.year)
    annual = (
        annual.assign(
            matched_10km=annual["weather_station_dist_km"].le(10),
            matched_20km=annual["weather_station_dist_km"].le(20),
            matched_30km=annual["weather_station_dist_km"].le(30),
            temperature_20km=(
                annual["weather_station_dist_km"].le(20)
                & annual["temperature_available"]
            ),
        )
        .groupby("year", as_index=False)
        .agg(
            scope_accidents=("nid", "size"),
            matched_10km=("matched_10km", "sum"),
            matched_20km=("matched_20km", "sum"),
            matched_30km=("matched_30km", "sum"),
            matched_temperature_20km=("temperature_20km", "sum"),
        )
    )
    for distance in (10, 20, 30):
        annual[f"coverage_{distance}km_pct"] = (
            100 * annual[f"matched_{distance}km"] / annual["scope_accidents"]
        )
    return coverage, annual


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Attach cleaned 10-minute weather to rural injury accidents."
    )
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-w", "--weather", type=Path, default=DEFAULT_WEATHER)
    parser.add_argument("-s", "--stations", type=Path, default=DEFAULT_STATIONS)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-c", "--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("-b", "--by-year", type=Path, default=DEFAULT_BY_YEAR)
    parser.add_argument("-n", "--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("-S", "--start", default="2007-01-01")
    parser.add_argument("-E", "--end", default="2025-12-31 23:59:59.999999")
    args = parser.parse_args()

    started = time.perf_counter()
    accidents = load_accidents(args.accidents, args.start, args.end)
    weather_file = pq.ParquetFile(args.weather)
    station_ids = weather_station_ids(weather_file)
    stations = load_stations(args.stations, station_ids)
    missing_station_ids = station_ids - set(stations["station"].astype(int))
    if missing_station_ids:
        print(
            "warning: weather stations without coordinates were excluded: "
            f"{sorted(missing_station_ids)}",
            flush=True,
        )

    candidates, has_station_within_30 = build_candidates(accidents, stations)
    weather = read_candidate_weather(weather_file, candidates)
    best = select_best(candidates, weather)
    output = assemble_output(accidents, stations, best, has_station_within_30)
    coverage, annual = coverage_tables(output)

    if len(output) != len(accidents) or output["nid"].duplicated().any():
        raise SystemExit("Output failed one-row-per-accident validation")
    primary = output["within_20km"]
    if output.loc[primary, ["f", "fg"]].isna().any().any():
        raise SystemExit("A primary match is missing wind data")

    for path in (args.output, args.coverage, args.by_year, args.notes):
        path.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    coverage.to_csv(args.coverage, index=False)
    annual.to_csv(args.by_year, index=False)
    elapsed = time.perf_counter() - started
    notes = f"""Clean accident-weather matching notes
=====================================

Accident input: {args.accidents}
Weather input: {args.weather}
Station metadata: {args.stations}
Scope: rural injury accidents (meidsli < 4), {args.start} through {args.end}.

Method
------
- Candidate measurements are the floor/ceiling 10-minute times no more than 5 minutes
  from the recorded accident time.
- Select the geographically nearest station with clean f and fg, then break ties by
  time difference, station number and measurement time.
- The primary radius is 20 km; 30 km is retained only for sensitivity analysis.
- Temperature comes from the selected wind station and may be missing. A wind match is
  not discarded solely because temperature is unavailable.
- All scoped accidents remain in the output, including unmatched accidents, with a
  match_status value explaining the result.
- Weather stations excluded because coordinates were unavailable: {sorted(missing_station_ids)}

Validation
----------
- Scoped accidents: {len(accidents):,}
- Output rows: {len(output):,}
- Unique nid values: {output['nid'].nunique():,}
- Duplicate nid values: {int(output['nid'].duplicated().sum()):,}

Coverage
--------
{coverage.to_string(index=False)}

Limitation
----------
Station weather is a spatial proxy for crash-site weather. Terrain and local exposure
can differ within 20 km. This table contains accident occasions only and cannot estimate
risk without a non-accident weather-time and traffic-exposure denominator.

Elapsed seconds: {elapsed:.1f}
"""
    args.notes.write_text(notes, encoding="utf-8")
    print(f"wrote={args.output} rows={len(output):,} elapsed={elapsed:.1f}s")
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()
