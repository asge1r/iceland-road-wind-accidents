"""Compare all-period and official VDU+SDU vehicle-kilometre rate ratios."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ALL_PERIODS = Path("reports/main/tables/conditional_poisson_rate_ratio_by_wind.csv")
OFFICIAL_PERIODS = Path("reports/working/tables/stratified_crash_rate_ratio_official_traffic.csv")
OUTPUT = Path("reports/working/tables/traffic_scope_comparison.csv")


def load(path: Path, prefix: str) -> pd.DataFrame:
    columns = [
        "bin_label", "observed_accidents", "time_proportional_rate_ratio",
        "time_proportional_ci_95_low", "time_proportional_ci_95_high",
    ]
    data = pd.read_csv(path, usecols=columns)
    return data.rename(
        columns={column: f"{prefix}_{column}" for column in columns if column != "bin_label"}
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--all-periods", type=Path, default=ALL_PERIODS)
    parser.add_argument("-s", "--official-periods", type=Path, default=OFFICIAL_PERIODS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    comparison = load(args.all_periods, "all").merge(
        load(args.official_periods, "official"), on="bin_label", validate="one_to_one"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(args.output, index=False)
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
