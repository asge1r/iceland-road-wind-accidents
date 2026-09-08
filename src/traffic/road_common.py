"""Shared definitions for road-period traffic preparation."""

from __future__ import annotations

import calendar
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_ANNUAL_TRAFFIC = Path(
    "data/processed/traffic/annual.csv"
)
DEFAULT_INJURY_ACCIDENTS = Path("data/processed/accidents/rural_injury.csv")
DEFAULT_WEATHER = Path("data/processed/weather/weather.parquet")
DEFAULT_PERIOD_WIND_FREQUENCY = Path(
    "data/processed/weather/road_period_frequency.csv"
)
DEFAULT_STATIONS = Path("data/raw/weather/stations.csv")
DEFAULT_SECTION_MIDPOINTS = Path(
    "data/raw/traffic/reference/road_section_midpoints.csv"
)
DEFAULT_ROAD_GEOMETRIES = Path(
    "data/raw/traffic/reference/road_sections.parquet"
)
DEFAULT_LONG = Path("data/processed/traffic/road_period.csv")

YEARS = range(2007, 2026)
FIRST_YEAR = 2007
LAST_YEAR = 2025
EARTH_RADIUS_KM = 6371.0088
PRIMARY_STATION_RADIUS_KM = 20.0
TRAFFIC_PERIOD_ORDER = ["VDU", "SDU", "VHDU"]
TRAFFIC_PERIOD_MONTHS = {
    "VDU": "Dec-Mar",
    "SDU": "Jun, Jul, Aug, Sep",
    "VHDU": "Apr, May, Oct, Nov",
}
TRAFFIC_PERIOD_BY_MONTH = {
    1: "VDU",
    2: "VDU",
    3: "VDU",
    4: "VHDU",
    5: "VHDU",
    6: "SDU",
    7: "SDU",
    8: "SDU",
    9: "SDU",
    10: "VHDU",
    11: "VHDU",
    12: "VDU",
}
TRAFFIC_PERIOD_MONTH_NUMBERS = {
    "VDU": [1, 2, 3, 12],
    "SDU": [6, 7, 8, 9],
    "VHDU": [4, 5, 10, 11],
}

def normalize_section(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.lower()

def traffic_period_index(month: np.ndarray) -> np.ndarray:
    result = np.full(len(month), 2, dtype=np.int8)
    result[np.isin(month, [1, 2, 3, 12])] = 0
    result[np.isin(month, [6, 7, 8, 9])] = 1
    return result

def load_annual_traffic(path: Path) -> pd.DataFrame:
    annual = pd.read_csv(path, low_memory=False)
    annual["year"] = pd.to_numeric(annual["year"], errors="coerce").astype("Int64")
    annual = annual[annual["year"].isin(YEARS)].copy()
    annual["year"] = annual["year"].astype(int)
    annual["road_section"] = normalize_section(annual["road_section"])
    if annual.duplicated(["year", "road_section"]).any():
        raise ValueError("Annual traffic contains duplicate road-section/year keys")
    return annual

def build_all_annual_traffic_scope(annual: pd.DataFrame) -> pd.DataFrame:
    """Return every road section represented in the annual-traffic file."""
    return (
        annual[["road_section"]]
        .dropna()
        .drop_duplicates()
        .sort_values("road_section")
        .reset_index(drop=True)
    )
def traffic_period_days(year: int, period: str) -> int:
    return sum(
        calendar.monthrange(int(year), month)[1]
        for month in TRAFFIC_PERIOD_MONTH_NUMBERS[period]
    )
