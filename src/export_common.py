"""Shared definitions for building the canonical analysis CSV layer."""

from __future__ import annotations

import calendar
from pathlib import Path

import pandas as pd

ROOT = Path("data/processed")
PERIOD_MONTHS = {
    "VDU": [12, 1, 2, 3],
    "SDU": [6, 7, 8, 9],
    "VHDU": [4, 5, 10, 11],
}

def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required prepared file: {path}")
    return (
        pd.read_parquet(path)
        if path.suffix == ".parquet"
        else pd.read_csv(path, low_memory=False)
    )

def write_csv(frame: pd.DataFrame, path: Path) -> int:
    frame.to_csv(path, index=False)
    return len(frame)

def days_in_traffic_period(year: int, traffic_period: str) -> int:
    return sum(calendar.monthrange(int(year), month)[1] for month in PERIOD_MONTHS[traffic_period])

def season_from_month(month: pd.Series) -> pd.Series:
    season = pd.Series(index=month.index, dtype="object")
    season.loc[month.isin([12, 1, 2, 3])] = "Winter"
    season.loc[month.isin([4, 5])] = "Spring"
    season.loc[month.isin([6, 7, 8, 9])] = "Summer"
    season.loc[month.isin([10, 11])] = "Fall"
    return season

def traffic_period_from_month(month: pd.Series) -> pd.Series:
    period = pd.Series("VHDU", index=month.index, dtype="string")
    period.loc[month.isin(PERIOD_MONTHS["VDU"])] = "VDU"
    period.loc[month.isin(PERIOD_MONTHS["SDU"])] = "SDU"
    return period
