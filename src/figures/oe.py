"""Draw O/E figures from the completed O/E result table."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.tables.oe import (
    PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
    plot_mean_wind_strata,
    plot_one_variable,
    plot_primary,
)


DEFAULT_INPUT = Path("reports/main/tables/oe_results.csv")
DEFAULT_OUTPUT = Path("reports/main/figures")


def primary_rows(results: pd.DataFrame) -> pd.DataFrame:
    return results[
        results["radius_km"].eq(20)
        & results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & results["severity_group"].eq("Injury accidents")
        & results["analysis_season"].eq("All seasons")
    ].copy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    results = pd.read_csv(args.input)
    primary = primary_rows(results)
    args.output.mkdir(parents=True, exist_ok=True)
    plot_primary(primary, args.output / "mean_wind_oe.png")
    plot_one_variable(primary, "fg", args.output / "gust_oe.png")
    plot_one_variable(primary, "gust_factor", args.output / "gust_factor_oe.png")
    plot_mean_wind_strata(
        results,
        "f",
        "analysis_season",
        ["Winter", "Spring", "Summer", "Fall"],
        "severity_group",
        "Injury accidents",
        "Mean wind O/E by season",
        args.output / "mean_wind_by_season_oe.png",
    )
    plot_mean_wind_strata(
        results,
        "f",
        "severity_group",
        ["1 vehicle", "2 or more vehicles"],
        "analysis_season",
        "All seasons",
        "Mean wind O/E by number of vehicles involved",
        args.output / "mean_wind_by_vehicle_group_oe.png",
    )
    plot_mean_wind_strata(
        results,
        "fg",
        "analysis_season",
        ["Winter", "Spring", "Summer", "Fall"],
        "severity_group",
        "Injury accidents",
        "Maximum gust O/E by season",
        args.output / "gust_by_season_oe.png",
    )
    plot_mean_wind_strata(
        results,
        "fg",
        "severity_group",
        ["1 vehicle", "2 or more vehicles"],
        "analysis_season",
        "All seasons",
        "Maximum gust O/E by number of vehicles involved",
        args.output / "gust_by_vehicle_group_oe.png",
    )
    print(f"wrote O/E figures to {args.output}")


if __name__ == "__main__":
    main()
