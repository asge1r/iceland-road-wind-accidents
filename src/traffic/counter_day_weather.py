"""Build the canonical counter-section/day traffic and weather panel."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.export_common import season_from_month
from src.traffic.counter_weather import row_group_can_contain_station
from src.weather.frequency import (
    OE_FG_UPPER_BOUNDS,
    OE_F_UPPER_BOUNDS,
    OE_TEMPERATURE_LABELS,
    OE_TEMPERATURE_UPPER_BOUNDS,
    labels,
)


DAILY = Path("data/processed/traffic/daily_raw.csv")
COUNTER_SECTIONS = Path("data/processed/traffic/counter_sections.csv")
WEATHER = Path("data/processed/weather/weather.parquet")
OUTPUT = Path("data/processed/traffic/counter_day_weather.parquet")
START_YEAR = 2019
END_YEAR = 2024
START_HOUR = 7
EXPECTED_OBSERVATIONS = 17 * 6
MIN_COVERAGE_FRACTION = 0.90

VARIABLES = {
    "f": (OE_F_UPPER_BOUNDS, labels(OE_F_UPPER_BOUNDS)),
    "fg": (OE_FG_UPPER_BOUNDS, labels(OE_FG_UPPER_BOUNDS)),
    "temperature": (OE_TEMPERATURE_UPPER_BOUNDS, OE_TEMPERATURE_LABELS),
}


def require_columns(data: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(data)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def build_counter_days(daily_path: Path, sections_path: Path) -> pd.DataFrame:
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
        },
        "Counter sections",
    )
    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    daily["road_section"] = daily["road_section"].astype("string").str.lower().str.strip()
    daily["station_id"] = pd.to_numeric(daily["station_id"], errors="raise")
    daily["traffic_volume"] = pd.to_numeric(daily["traffic_volume"], errors="raise")
    daily["daily_row"] = np.arange(len(daily))
    sections = sections.copy()
    sections["road_section"] = sections["road_section"].astype("string").str.lower().str.strip()
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
        "weather_station_id",
    ]
    result = joined.groupby(group, as_index=False, observed=True).agg(
        traffic_vehicles=("traffic_volume", "sum")
    )
    result["month"] = result["date"].dt.month
    result["season"] = season_from_month(result["month"])
    result["vehicle_km"] = (
        result["traffic_vehicles"] * result["counter_section_length_km"]
    )
    return result


def _bin_counts(values: np.ndarray, bounds: np.ndarray) -> np.ndarray:
    """Count finite values in left-closed intervals defined by bounds."""
    return np.bincount(
        np.searchsorted(bounds, values, side="right"),
        minlength=len(bounds) + 1,
    )


def aggregate_weather(
    weather_path: Path, needed_stations: np.ndarray
) -> pd.DataFrame:
    """Aggregate actual 07:00--24:00 observations by station and date."""
    source = pq.ParquetFile(weather_path)
    partials: list[pd.DataFrame] = []
    for row_group in range(source.metadata.num_row_groups):
        if not row_group_can_contain_station(source, row_group, needed_stations):
            continue
        table = source.read_row_group(
            row_group, columns=["station", "time", "f", "fg", "t"]
        )
        station = table.column("station").to_numpy(zero_copy_only=False).astype(int)
        timestamp = table.column("time").to_numpy(zero_copy_only=False).astype("datetime64[us]")
        year = timestamp.astype("datetime64[Y]").astype(np.int64) + 1970
        hour = timestamp.astype("datetime64[h]").astype(np.int64) % 24
        keep = (
            np.isin(station, needed_stations)
            & (year >= START_YEAR)
            & (year <= END_YEAR)
            & (hour >= START_HOUR)
        )
        if not keep.any():
            continue
        frame = pd.DataFrame(
            {
                "weather_station_id": station[keep],
                "date": timestamp[keep].astype("datetime64[D]"),
                "f": table.column("f").to_numpy(zero_copy_only=False)[keep],
                "fg": table.column("fg").to_numpy(zero_copy_only=False)[keep],
                "temperature": table.column("t").to_numpy(zero_copy_only=False)[keep],
            }
        )
        rows: list[dict[str, object]] = []
        for (station_id, date), group in frame.groupby(
            ["weather_station_id", "date"], observed=True, sort=False
        ):
            record: dict[str, object] = {
                "weather_station_id": int(station_id), "date": date,
            }
            for variable, (bounds, bin_labels) in VARIABLES.items():
                values = pd.to_numeric(group[variable], errors="coerce").to_numpy(float)
                if variable == "temperature":
                    values = values[np.isfinite(values) & (values >= -30) & (values <= 30)]
                else:
                    values = values[np.isfinite(values)]
                record[f"{variable}_valid_observations"] = len(values)
                counts = _bin_counts(values, np.asarray(bounds, dtype=float))
                for label, count in zip(bin_labels, counts, strict=True):
                    record[f"{variable}_bin_{label}_count"] = int(count)
            rows.append(record)
        partials.append(pd.DataFrame(rows))
    if not partials:
        raise ValueError("No counter-station weather observations were found")
    weather = pd.concat(partials, ignore_index=True)
    count_columns = [
        column for column in weather
        if column not in {"weather_station_id", "date"}
    ]
    return weather.groupby(
        ["weather_station_id", "date"], as_index=False, observed=True
    )[count_columns].sum()


def build(
    daily_path: Path, sections_path: Path, weather_path: Path
) -> tuple[pd.DataFrame, dict[str, int]]:
    counter_days = build_counter_days(daily_path, sections_path)
    weather = aggregate_weather(
        weather_path, np.sort(counter_days["weather_station_id"].unique())
    )
    panel = counter_days.merge(
        weather, on=["weather_station_id", "date"], how="left", validate="many_to_one"
    )
    minimum = int(np.ceil(EXPECTED_OBSERVATIONS * MIN_COVERAGE_FRACTION))
    for variable, (_, bin_labels) in VARIABLES.items():
        valid = f"{variable}_valid_observations"
        bin_columns = [f"{variable}_bin_{label}_count" for label in bin_labels]
        panel[valid] = panel[valid].fillna(0).astype(int)
        panel[bin_columns] = panel[bin_columns].fillna(0).astype(int)
        if not panel[bin_columns].sum(axis=1).eq(panel[valid]).all():
            raise ValueError(f"{variable} bins do not reconstruct valid observations")
        panel[f"{variable}_coverage_ok"] = panel[valid].ge(minimum)
    panel = panel.sort_values(["counter_section_id", "date"]).reset_index(drop=True)
    summary = {
        "counter_days": len(panel),
        "counter_sections": panel["counter_section_id"].nunique(),
        **{
            f"{variable}_complete_days": int(panel[f"{variable}_coverage_ok"].sum())
            for variable in VARIABLES
        },
    }
    return panel, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-d", "--daily", type=Path, default=DAILY)
    parser.add_argument("-c", "--counter-sections", type=Path, default=COUNTER_SECTIONS)
    parser.add_argument("-w", "--weather", type=Path, default=WEATHER)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result, summary = build(args.daily, args.counter_sections, args.weather)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(args.output, index=False, compression="zstd")
    print("; ".join(f"{key}={value:,}" for key, value in summary.items()))
    print(f"wrote={args.output} rows={len(result):,}")


if __name__ == "__main__":
    main()
