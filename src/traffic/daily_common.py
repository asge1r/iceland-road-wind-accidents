"""Shared definitions for daily-counter preparation and summaries."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.weather.frequency import FG_UPPER_BOUNDS, labels

EARTH_RADIUS_KM = 6371.0088
DAILY_F_UPPER_BOUNDS = np.arange(3, 34, 3, dtype=float)
DAILY_WIND_EXCLUDED_STATION_IDS = {7475}

def normalize_section(values: pd.Series) -> pd.Series:
    """Normalize registered road-section identifiers."""
    return values.astype("string").str.strip().str.lower()

def read_daily(path: Path, start_year: int, end_year: int) -> pd.DataFrame:
    """Read one CSV row per physical counter site and date."""
    raw = pd.read_csv(path, dtype={"source_fastnr": "string"}, low_memory=False)
    required = {
        "date", "year", "counter_site_id", "station_id", "road_section",
        "traffic_volume",
    }
    missing = required - set(raw)
    if missing:
        raise ValueError(f"Daily counter data are missing columns: {sorted(missing)}")
    raw = raw[raw["year"].between(start_year, end_year)].copy()
    raw["date"] = pd.to_datetime(raw["date"])
    raw["road_section"] = normalize_section(raw["road_section"])
    raw["station_id"] = pd.to_numeric(
        raw["station_id"], errors="raise"
    ).astype(int)
    raw["traffic_volume"] = pd.to_numeric(
        raw["traffic_volume"], errors="raise"
    ).astype(float)
    if raw["traffic_volume"].lt(0).any():
        raise ValueError("Daily traffic contains negative values")

    if raw.duplicated(["counter_site_id", "date"]).any():
        raise ValueError("Daily traffic is not unique on site + date")
    return raw
