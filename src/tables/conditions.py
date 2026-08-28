"""Summarize accident-time temperature, daylight, season, and hour."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/accident_conditions_summary.csv")
DEFAULT_COVERAGE = Path("reports/main/tables/temperature_coverage.csv")
TEMPERATURE_BINS = [-np.inf, -9, -6, -3, 0, 3, 6, 9, 12, 15, 18, np.inf]
TEMPERATURE_LABELS = [
    "<-9", "-9--6", "-6--3", "-3-0", "0-3", "3-6",
    "6-9", "9-12", "12-15", "15-18", ">=18",
]


def require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def counts(data: pd.DataFrame, dimension: str, order: list[object]) -> pd.DataFrame:
    result = data[dimension].value_counts(dropna=False).reindex(order, fill_value=0)
    frame = result.rename_axis("category").reset_index(name="accidents")
    frame["available_accidents"] = int(data[dimension].notna().sum())
    frame["percent_of_available"] = np.where(
        frame["available_accidents"].gt(0),
        100 * frame["accidents"] / frame["available_accidents"],
        np.nan,
    )
    frame.insert(0, "dimension", dimension)
    return frame


def build_tables(accidents: pd.DataFrame, conditions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    require_columns(
        accidents,
        {"id", "year", "hour", "season", "traffic_period"},
        "accidents.csv",
    )
    require_columns(
        conditions,
        {"id", "temperature_c", "solar_elevation_deg", "daylight_class"},
        "accident_conditions.csv",
    )
    if not accidents["id"].is_unique or not conditions["id"].is_unique:
        raise ValueError("Accident and condition IDs must be unique")
    data = accidents.merge(conditions, on="id", how="left", validate="one_to_one")
    data["temperature_interval_c"] = pd.cut(
        data["temperature_c"],
        bins=TEMPERATURE_BINS,
        labels=TEMPERATURE_LABELS,
        right=False,
    ).astype("string")
    summary = pd.concat(
        [
            counts(data, "hour", list(range(24))),
            counts(data, "season", ["Winter", "Spring", "Summer", "Fall"]),
            counts(data, "traffic_period", ["VDU", "SDU", "VHDU"]),
            counts(data, "daylight_class", ["Darkness", "Civil twilight", "Daylight"]),
            counts(data, "temperature_interval_c", TEMPERATURE_LABELS),
        ],
        ignore_index=True,
    )
    data["temperature_available"] = data["temperature_c"].notna()
    overall = pd.DataFrame(
        [{
            "scope": "All accidents",
            "group": "All",
            "accidents": len(data),
            "temperature_available": int(data["temperature_available"].sum()),
        }]
    )
    by_year = data.groupby("year", as_index=False).agg(
        accidents=("id", "size"),
        temperature_available=("temperature_available", "sum"),
    ).rename(columns={"year": "group"})
    by_year.insert(0, "scope", "Year")
    by_season = data.groupby("season", as_index=False).agg(
        accidents=("id", "size"),
        temperature_available=("temperature_available", "sum"),
    ).rename(columns={"season": "group"})
    by_season.insert(0, "scope", "Season")
    coverage = pd.concat([overall, by_year, by_season], ignore_index=True)
    coverage["temperature_coverage_pct"] = (
        100 * coverage["temperature_available"] / coverage["accidents"]
    )
    return summary, coverage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-c", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-C", "--coverage-output", type=Path, default=DEFAULT_COVERAGE)
    args = parser.parse_args()
    summary, coverage = build_tables(
        pd.read_csv(args.accidents), pd.read_csv(args.conditions)
    )
    for path in [args.output, args.coverage_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output, index=False)
    coverage.to_csv(args.coverage_output, index=False)
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()
