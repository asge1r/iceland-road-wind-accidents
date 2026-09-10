"""Write the supporting comparison of four seasonal wind analyses."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.analysis.traffic_daily import compare_season_methods


WEATHER = Path("reports/working/tables/oe_scenarios.csv")
MATCHED = Path("reports/main/tables/wind_season.csv")
ANNUAL = Path("reports/main/tables/season_rate.csv")
DAILY = Path("reports/working/tables/daily_season_rate.csv")
DAILY_OE = Path("reports/main/tables/daily_season_oe.csv")
DAILY_FULL_INTERACTION = Path("reports/working/tables/daily_season_interaction.csv")
DAILY_FOCUSED_INTERACTION = Path(
    "reports/working/tables/daily_highwind_season_interaction.csv"
)
OUTPUT = Path("reports/working/tables/season_method_comparison.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = compare_season_methods(
        pd.read_csv(WEATHER),
        pd.read_csv(MATCHED),
        pd.read_csv(ANNUAL),
        pd.read_csv(DAILY),
        pd.read_csv(DAILY_OE),
        pd.read_csv(DAILY_FULL_INTERACTION),
        pd.read_csv(DAILY_FOCUSED_INTERACTION),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
