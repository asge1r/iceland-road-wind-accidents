"""Same-day exposure using the nearest available station at each ten-minute time.

Each observation represents +/-5 minutes clipped to 07:00–24:00. The 07:00 and
following midnight observations each represent five minutes. Missing time is
excluded only when no candidate station within 20 km has valid wind and gust.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from src.weather.monthly_frequency import VARIABLES
from src.weather.eligibility import valid_temperature
from src.traffic.station_selection import STATIONS, SECTIONS, station_candidates, nearest_valid

DAYTIME_MINUTES = 17 * 60


def read_year(path: Path, stations: np.ndarray, year: int):
    """One-year cache retaining the archive's measurement precision."""
    first, end = pd.Timestamp(year, 1, 1), pd.Timestamp(year+1, 1, 1)
    slots = int((end - first).total_seconds() / 600) + 1
    source = ds.dataset(path, format="parquet")
    dtype = np.result_type(*[source.schema.field(name).type.to_pandas_dtype() for name in ["f", "fg", "t"]], np.float32)
    values = np.full((len(stations), slots, 3), np.nan, dtype=dtype)
    seen = np.zeros((len(stations), slots), dtype=bool)
    query = (ds.field("time") >= first) & (ds.field("time") <= end) & ds.field("station").isin(stations)
    off_grid = 0
    for batch in source.scanner(columns=["station", "time", "f", "fg", "t"],
                                filter=query, batch_size=1_000_000).to_batches():
        stamp = batch.column("time").to_numpy(zero_copy_only=False).astype("datetime64[us]")
        on_grid = stamp.astype(np.int64) % 600_000_000 == 0
        off_grid += int((~on_grid).sum())
        row = np.searchsorted(stations, batch.column("station").to_numpy(zero_copy_only=False)[on_grid])
        column = ((stamp[on_grid] - first.to_datetime64()) / np.timedelta64(10, "m")).astype(int)
        encoded = row * slots + column
        if len(np.unique(encoded)) != len(encoded) or seen[row, column].any():
            raise ValueError("Duplicate station/time weather observation")
        seen[row, column] = True
        for i, name in enumerate(["f", "fg", "t"]):
            values[row, column, i] = batch.column(name).to_numpy(zero_copy_only=False)[on_grid]
    return values, off_grid


def build_daytime_weather(path: Path, counter_days: pd.DataFrame,
                          sections_path: Path = SECTIONS, stations_path: Path = STATIONS) -> pd.DataFrame:
    days = counter_days.loc[counter_days.vehicle_km.gt(0), ["counter_section_id", "date"]].drop_duplicates().copy()
    days["date"] = pd.to_datetime(days["date"])
    if days.empty:
        raise ValueError("No positive rural counter-day exposure")
    sections = pd.read_csv(sections_path)
    sections = sections[sections.counter_section_id.isin(days.counter_section_id)]
    candidates = station_candidates(sections, pd.read_csv(stations_path))
    ranked = {key: group for key, group in candidates.groupby("counter_section_id", sort=False)}
    frames = []
    # Cache one year's station observations, not a large section x time table.
    for year, year_days in days.groupby(days.date.dt.year):
        year_candidates = candidates[candidates.counter_section_id.isin(year_days.counter_section_id)]
        stations = np.sort(year_candidates.weather_station_id.unique()).astype(int)
        if not len(stations):
            continue
        values, off_grid = read_year(path, stations, int(year))
        for section_id, section_days in year_days.groupby("counter_section_id", sort=False):
            near = ranked.get(section_id)
            if near is None:
                continue
            dates = section_days.date.sort_values().to_numpy()
            day_index = ((dates - np.datetime64(f"{year}-01-01")) / np.timedelta64(1, "D")).astype(int)
            slot = (day_index[:, None] * 144 + np.arange(42, 145)).ravel()
            row = np.searchsorted(stations, near.weather_station_id.to_numpy())
            selected, weather = nearest_valid(near.weather_station_id.to_numpy(), values[row[:, None], slot[None, :]])
            minute = np.tile(np.r_[5, np.full(101, 10), 5], len(dates))
            observation_days = np.repeat(dates, 103)
            for variable, (bounds, names) in VARIABLES.items():
                measurements = weather[:, {"f": 0, "fg": 1, "temperature": 2}[variable]]
                use = (selected >= 0) & (valid_temperature(measurements) if variable == "temperature" else True)
                if not use.any():
                    continue
                rows = pd.DataFrame({"date": observation_days[use], "weather_station_id": selected[use],
                                     "bin_order": np.searchsorted(bounds, measurements[use], side="right"),
                                     "observed_minutes": minute[use]})
                rows = rows.groupby(["date", "weather_station_id", "bin_order"], as_index=False).observed_minutes.sum()
                rows["counter_section_id"], rows["variable"] = section_id, variable
                rows["bin_label"] = rows.bin_order.map(dict(enumerate(names)))
                frames.append(rows)
        print(f"same-day nearest-available weather: year={year}; counter_days={len(year_days):,}; "
              f"candidate_stations={len(stations)}; off_grid_excluded={off_grid:,}", flush=True)
        del values
    columns = ["date", "weather_station_id", "bin_order", "observed_minutes", "counter_section_id", "variable", "bin_label"]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)
