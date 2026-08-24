"""Draw daily-traffic response figures from completed result tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.tables.daily_traffic import plot_period_results, plot_results


DEFAULT_INPUT = Path("reports/main/tables/daily_traffic_by_wind.csv")
DEFAULT_MAIN = Path("reports/main/figures/daily_traffic_by_wind.png")
DEFAULT_PERIOD = Path("reports/working/figures/daily_traffic_by_period.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("-p", "--period-output", type=Path, default=DEFAULT_PERIOD)
    args = parser.parse_args()

    results = pd.read_csv(args.input)
    for path in [args.output, args.period_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    plot_results(
        results,
        args.output,
        "All periods",
        "Daily traffic relative to expected traffic by mean wind speed",
    )
    plot_period_results(results, args.period_output)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
