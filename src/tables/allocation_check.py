"""Quantify the direction implied by the observed daily traffic pattern."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


RATE_INPUT = Path("reports/main/tables/wind_rate.csv")
DAILY_INPUT = Path("reports/main/tables/traffic_wind.csv")
OUTPUT = Path("reports/main/tables/allocation_check.csv")
WIND_BINS = ["0-5", "5-10", "10-15", "15-20", "20-25", ">=25"]


def require_columns(data: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(data)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def build(rate: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        rate,
        {"bin_label", "time_proportional_rate_ratio"},
        "Annual rate result",
    )
    require_columns(
        daily,
        {"f_bin", "relative_traffic_pct", "counter_days", "scope"},
        "Daily traffic result",
    )
    daily = daily[daily["scope"].eq("All periods")].copy()
    if rate["bin_label"].duplicated().any() or daily["f_bin"].duplicated().any():
        raise ValueError("Wind intervals must be unique in both inputs")
    if set(rate["bin_label"]) != set(WIND_BINS) or set(daily["f_bin"]) != set(WIND_BINS):
        raise ValueError("Annual and daily results must contain the six fixed wind intervals")

    result = rate[
        ["bin_label", "time_proportional_rate_ratio"]
    ].merge(
        daily[["f_bin", "relative_traffic_pct", "counter_days"]],
        left_on="bin_label",
        right_on="f_bin",
        how="inner",
        validate="one_to_one",
    )
    if result["relative_traffic_pct"].le(0).any():
        raise ValueError("Daily relative traffic must be positive")
    reference_factor = float(
        result.loc[result["bin_label"].eq("0-5"), "relative_traffic_pct"].iloc[0]
    )
    result["illustrative_rate_ratio"] = (
        result["time_proportional_rate_ratio"]
        * reference_factor
        / result["relative_traffic_pct"]
    )
    result["illustrative_change_pct"] = 100 * (
        result["illustrative_rate_ratio"]
        / result["time_proportional_rate_ratio"]
        - 1
    )
    result["interpretation"] = (
        "Direction check only: full-day traffic response at selected counters, "
        "2019-2024, applied to the annual model; not a corrected estimate."
    )
    order = {value: index for index, value in enumerate(WIND_BINS)}
    return result[
        [
            "bin_label", "time_proportional_rate_ratio", "relative_traffic_pct",
            "counter_days", "illustrative_rate_ratio", "illustrative_change_pct",
            "interpretation",
        ]
    ].sort_values("bin_label", key=lambda values: values.map(order))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-r", "--rate-input", type=Path, default=RATE_INPUT)
    parser.add_argument("-d", "--daily-input", type=Path, default=DAILY_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    for path in [args.rate_input, args.daily_input]:
        if path.suffix.lower() != ".csv":
            raise ValueError(f"Result input must be CSV: {path}")
    result = build(pd.read_csv(args.rate_input), pd.read_csv(args.daily_input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
