"""Select the five-period, two-outcome O/E results for thesis figures."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.analysis.oe_core import PRIMARY_MAX_TIME_DIFFERENCE_MINUTES


INPUT = Path("reports/main/tables/oe_results.csv")
OUTPUT = Path("reports/main/tables/weather_oe_panels.csv")
VARIABLES = ["f", "fg", "temperature"]
OUTCOMES = ["Injury accidents", "Serious or fatal"]
PERIODS = ["All seasons", "Winter", "Spring", "Summer", "Fall"]


def select_panels(results: pd.DataFrame) -> pd.DataFrame:
    """Return one consistent table for all three five-panel figures."""
    required = {
        "variable", "radius_km", "severity_group", "analysis_season",
        "max_time_difference_minutes", "coarse_bin", "bin_order",
        "observed_accidents", "expected_accidents",
        "relative_accident_frequency", "bootstrap_ci_95_low",
        "bootstrap_ci_95_high", "bootstrap_reps", "bootstrap_stations",
    }
    if missing := required - set(results):
        raise ValueError(f"O/E result table is missing columns: {sorted(missing)}")
    selected = results[
        results["variable"].isin(VARIABLES)
        & results["radius_km"].eq(20)
        & results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & results["severity_group"].isin(OUTCOMES)
        & results["analysis_season"].isin(PERIODS)
    ].copy()
    expected_scenarios = {
        (variable, outcome, period)
        for variable in VARIABLES
        for outcome in OUTCOMES
        for period in PERIODS
    }
    actual_scenarios = set(
        selected[["variable", "severity_group", "analysis_season"]]
        .itertuples(index=False, name=None)
    )
    if actual_scenarios != expected_scenarios:
        missing = sorted(expected_scenarios - actual_scenarios)
        raise ValueError(f"Missing O/E panel scenarios: {missing}")
    sample_sizes = (
        selected.groupby(
            ["variable", "severity_group", "analysis_season"], as_index=False
        )["observed_accidents"]
        .sum()
        .rename(columns={"observed_accidents": "analysed_accidents"})
    )
    selected = selected.merge(
        sample_sizes,
        on=["variable", "severity_group", "analysis_season"],
        validate="many_to_one",
    )
    selected["outcome"] = selected["severity_group"].map(
        {
            "Injury accidents": "All injury accidents (meiðsli ≤ 3)",
            "Serious or fatal": "Serious/fatal subset (meiðsli ≤ 2)",
        }
    )
    selected["period"] = selected["analysis_season"].replace(
        {"All seasons": "All year", "Fall": "Autumn"}
    )
    selected["sparse_bin"] = selected["observed_accidents"].lt(20)
    columns = [
        "variable", "period", "outcome", "coarse_bin", "bin_order",
        "observed_accidents", "expected_accidents",
        "relative_accident_frequency", "bootstrap_ci_95_low",
        "bootstrap_ci_95_high", "analysed_accidents", "sparse_bin",
        "bootstrap_stations", "bootstrap_reps",
    ]
    return selected[columns].sort_values(
        ["variable", "period", "outcome", "bin_order"]
    ).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = select_panels(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"wrote={args.output} rows={len(result):,}")


if __name__ == "__main__":
    main()
