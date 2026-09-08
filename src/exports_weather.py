"""Export weather audit and frequency analysis tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.export_common import ROOT, read_table, write_csv

def export_weather_cleaning(output: Path) -> tuple[int, list[str]]:
    """Copy the compact cleaning summary into the canonical analysis layer."""
    source = read_table(ROOT / "weather/cleaning.csv")
    required = {
        "year", "input_rows", "no_wind_station_year", "missing_wind",
        "negative", "upper_threshold", "inconsistent_zero_gust",
        "gust_below_mean", "frozen_zero", "clean_wind_rows",
        "negative_f", "negative_fg", "f_at_or_above_45",
        "fg_at_or_above_65", "fg_zero_rows", "fg_zero_with_positive_f",
        "excluded_rows",
    }
    missing = required - set(source)
    if missing:
        raise ValueError(f"Weather cleaning summary is missing columns: {sorted(missing)}")
    columns = [column for column in source.columns if column in required]
    table = source[columns]
    return write_csv(table, output / "weather_cleaning.csv"), columns

def export_frequency(output: Path) -> tuple[int, list[str]]:
    source = read_table(ROOT / "weather/frequency.csv").copy()
    source = source[source["variable"].isin(["f", "fg", "temperature"])].copy()
    source["unit"] = source["variable"].map(
        {"f": "m/s", "fg": "m/s", "temperature": "deg C"}
    )
    group = ["station", "season", "variable", "bin_label", "unit"]
    counts = source.groupby(group, as_index=False, observed=True).agg(
        measurement_count=("measurement_count", "sum"),
        bin_lower=("bin_lower_value", "first"),
    )
    totals = source.groupby(
        ["station", "season", "variable", "unit"], as_index=False, observed=True
    ).agg(total_measurements_in_period=("total_measurements_in_period", "first"))
    tidy = counts.merge(
        totals, on=["station", "season", "variable", "unit"], how="left", validate="many_to_one"
    )
    tidy["frequency_pct"] = 100 * tidy["measurement_count"] / tidy["total_measurements_in_period"]
    columns = [
        "station", "season", "variable", "bin_label", "unit",
        "measurement_count", "total_measurements_in_period", "frequency_pct",
    ]
    tidy = tidy.sort_values(["station", "season", "variable", "bin_lower"])[columns]
    return write_csv(tidy, output / "weather_frequency.csv"), columns

def export_yearly_frequency(output: Path) -> tuple[int, list[str]]:
    source = read_table(ROOT / "weather/yearly_frequency.csv").copy()
    source = source[source["variable"].isin(["f", "temperature"])].copy()
    source["unit"] = source["variable"].map(
        {"f": "m/s", "temperature": "deg C"}
    )
    columns = [
        "station", "year", "season", "variable", "bin_label", "unit",
        "measurement_count", "total_measurements_in_period", "frequency_pct",
    ]
    missing = set(columns) - set(source)
    if missing:
        raise ValueError(f"Yearly weather frequency is missing columns: {sorted(missing)}")
    table = source.sort_values(
        ["station", "year", "season", "variable", "bin_lower_value"]
    )[columns]
    return write_csv(table, output / "weather_yearly.csv"), columns
