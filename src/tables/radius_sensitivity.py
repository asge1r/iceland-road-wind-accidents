"""Write the primary mean-wind sensitivity table for 10, 20, and 30 km."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = Path("reports/main/tables/oe_results.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/mean_wind_radius_sensitivity.csv")
UPPER_BINS = ["15-20", "20-25", ">=25"]


def build_table(source: pd.DataFrame) -> pd.DataFrame:
    required = {
        "variable", "radius_km", "severity_group", "analysis_season",
        "coarse_bin", "observed_accidents", "expected_accidents",
        "relative_accident_frequency", "bootstrap_ci_95_low",
        "bootstrap_ci_95_high",
    }
    missing = required - set(source)
    if missing:
        raise ValueError(f"O/E results are missing columns: {sorted(missing)}")
    result = source[
        source["variable"].eq("f")
        & source["severity_group"].eq("Injury accidents")
        & source["analysis_season"].eq("All seasons")
        & source["radius_km"].isin([10, 20, 30])
        & source["coarse_bin"].isin(UPPER_BINS)
    ].copy()
    if len(result) != 9:
        raise ValueError(f"Expected nine primary radius-sensitivity rows, found {len(result)}")
    result["primary_radius"] = result["radius_km"].eq(20)
    result["expected_accidents"] = result["expected_accidents"].round(1)
    for column in [
        "relative_accident_frequency", "bootstrap_ci_95_low", "bootstrap_ci_95_high"
    ]:
        result[column] = result[column].round(2)
    order = {label: index for index, label in enumerate(UPPER_BINS)}
    result["bin_order"] = result["coarse_bin"].map(order)
    return result.sort_values(["radius_km", "bin_order"])[
        [
            "radius_km", "primary_radius", "coarse_bin", "observed_accidents",
            "expected_accidents", "relative_accident_frequency",
            "bootstrap_ci_95_low", "bootstrap_ci_95_high",
        ]
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_table(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
