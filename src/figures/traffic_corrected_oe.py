"""Draw whole-year O/E after the daily-counter traffic correction."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.figures.oe_histo import plot_whole_year


INPUT = Path("reports/main/tables/weather_oe_traffic_corrected.csv")
OUTPUT = Path("reports/main/figures/weather_oe_traffic_corrected.png")
X_LABELS = {
    "f": "Mean wind (m/s)",
    "fg": "Wind gust (m/s)",
    "temperature": "Temperature °C",
}
Y_LIMITS = {"f": 6.0, "fg": 6.0, "temperature": 2.0}
Y_STEPS = {"f": 1.0, "fg": 1.0, "temperature": 0.2}


def plotting_table(data: pd.DataFrame) -> pd.DataFrame:
    """Map the corrected result columns to the established O/E figure contract."""
    required = {
        "variable", "outcome", "period", "bin_label", "bin_order",
        "observed_accidents", "traffic_corrected_expected_accidents",
        "traffic_corrected_oe",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"Corrected O/E table is missing: {sorted(missing)}")
    columns = [
        "variable", "outcome", "period", "bin_label", "bin_order",
        "observed_accidents", "traffic_corrected_expected_accidents",
        "traffic_corrected_oe",
    ]
    return data[columns].rename(
        columns={
            "traffic_corrected_expected_accidents": "expected_accidents",
            "traffic_corrected_oe": "relative_accident_frequency",
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    plot_whole_year(
        plotting_table(pd.read_csv(args.input)),
        args.output,
        "2007–2025, approximate adjustment from 2019–2024 daily counters",
        x_labels=X_LABELS,
        y_limits=Y_LIMITS,
        y_steps=Y_STEPS,
        variables=("f", "fg"),
    )
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
