"""Draw daily-traffic quality-control figures from completed tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.traffic import daily_traffic_tools as tools


DEFAULT_SUMMARY = Path("reports/working/tables/daily_traffic_diagnostic.csv")
DEFAULT_VALIDATION = Path("archive/generated_diagnostics/daily_traffic_adu_validation.csv")
DEFAULT_ADU_FIGURE = Path("reports/working/traffic_validation.png")
DEFAULT_FIGURE = Path("reports/working/daily_traffic_diagnostic.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-s", "--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("-v", "--adu-validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("-f", "--adu-figure", type=Path, default=DEFAULT_ADU_FIGURE)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_FIGURE)
    args = parser.parse_args()

    summary = pd.read_csv(args.summary)
    validation = pd.read_csv(args.adu_validation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.adu_figure.parent.mkdir(parents=True, exist_ok=True)
    tools.plot_wind_summary(summary, args.output)
    tools.plot_adu_validation(validation, args.adu_figure)
    print(f"wrote={args.output}")
    print(f"wrote={args.adu_figure}")


if __name__ == "__main__":
    main()
