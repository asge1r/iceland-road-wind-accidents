"""Compare accidents with station-season-year wind and temperature frequencies."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.analysis.oe_analysis import (
    VARIABLES,
    load_data,
    station_frequency_scenario,
)


DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_FREQUENCY = Path("data/analysis/weather_yearly.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/year_oe.csv")


def calculate(
    accidents_path: Path,
    conditions_path: Path,
    frequency_path: Path,
) -> pd.DataFrame:
    accidents, frequency = load_data(
        accidents_path, conditions_path, frequency_path, None, None
    )
    specs = {spec.variable: spec for spec in VARIABLES}
    outputs = []
    for variable in ["f", "temperature"]:
        _, details, coverage = station_frequency_scenario(
            accidents, frequency, specs[variable], 20,
            "Injury accidents", "All seasons",
        )
        station_bins = (
            details.groupby(["weather_station_id", "weather_bin"], observed=False)
            .agg(
                observed_accidents=("observed_accidents", "sum"),
                expected_accidents=("expected_accidents", "sum"),
                background_measurements=("measurement_count", "sum"),
            )
            .reset_index()
            .rename(columns={"weather_bin": "coarse_bin"})
        )
        result = (
            station_bins.groupby("coarse_bin", as_index=False, observed=False)
            .agg(
                observed_accidents=("observed_accidents", "sum"),
                expected_accidents=("expected_accidents", "sum"),
                background_measurements=("background_measurements", "sum"),
                stations=("weather_station_id", "nunique"),
            )
        )
        result["observed_expected_ratio"] = (
            result["observed_accidents"] / result["expected_accidents"]
        )
        result["variable"] = variable
        result["analysed_accidents"] = int(coverage["analysed_accidents"])
        result["stratification"] = "weather station, season, and year"
        order = {
            label: index for index, label in enumerate(specs[variable].bin_labels)
        }
        result["bin_order"] = result["coarse_bin"].map(order)
        outputs.append(result)
    return pd.concat(outputs, ignore_index=True).sort_values(
        ["variable", "bin_order"]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-c", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("-f", "--frequency", type=Path, default=DEFAULT_FREQUENCY)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = calculate(args.accidents, args.conditions, args.frequency)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
