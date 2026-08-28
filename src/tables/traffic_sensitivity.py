"""Consolidate the retained annual- and daily-traffic sensitivity checks."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.tables.daily_traffic import prepare_data, summarize


DEFAULT_ALL_PERIODS = Path("reports/main/tables/conditional_poisson_rate_ratio_by_wind.csv")
DEFAULT_OFFICIAL = Path("reports/working/tables/stratified_crash_rate_ratio_official_traffic.csv")
DEFAULT_DAILY = Path("data/analysis/daily_traffic.csv")
DEFAULT_ANNUAL_QUALITY = Path("reports/main/tables/annual_traffic_quality.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/traffic_sensitivity.csv")


def rate_row(source: pd.DataFrame, wind_bin: str, scope: str) -> dict[str, object]:
    row = source[source["bin_label"].eq(wind_bin)]
    if len(row) != 1:
        raise ValueError(f"Expected one {scope} rate row for {wind_bin}")
    value = row.iloc[0]
    return {
        "check": f"Rate model, {wind_bin} m/s",
        "primary_or_full_scope": scope,
        "estimate": float(value["time_proportional_rate_ratio"]),
        "ci_95_low": float(value["time_proportional_ci_95_low"]),
        "ci_95_high": float(value["time_proportional_ci_95_high"]),
        "records": int(value["observed_accidents"]),
        "interpretation": "Rate ratio relative to 0-5 m/s.",
    }


def daily_row(source: pd.DataFrame, exclude_zero: bool) -> dict[str, object]:
    scoped = source[source["traffic"].gt(0)].copy() if exclude_zero else source.copy()
    panel = prepare_data(scoped)
    result = summarize(
        panel,
        scope="Excluding zero traffic" if exclude_zero else "All counter-days",
        replicates=1000,
        seed=20260827 + int(exclude_zero),
    )
    row = result[result["f_bin"].astype("string").eq("20-25")].iloc[0]
    return {
        "check": "Daily traffic, 20-25 m/s",
        "primary_or_full_scope": "Exclude zero counter-days" if exclude_zero else "Retain zero counter-days",
        "estimate": float(row["relative_traffic_pct"]),
        "ci_95_low": float(row["relative_traffic_ci_95_low_pct"]),
        "ci_95_high": float(row["relative_traffic_ci_95_high_pct"]),
        "records": int(row["counter_days"]),
        "interpretation": "Observed traffic as percent of the calendar-standardised expectation.",
    }


def quality_row(quality: pd.DataFrame, metric: str, label: str) -> dict[str, object]:
    row = quality[quality["metric"].eq(metric)]
    total = quality.loc[quality["metric"].eq("section_years"), "section_years"]
    if len(row) != 1 or len(total) != 1:
        raise ValueError(f"Annual-traffic quality table is missing {metric}")
    count = int(row.iloc[0]["section_years"])
    return {
        "check": label,
        "primary_or_full_scope": "Excluded, not imputed",
        "estimate": 100 * count / int(total.iloc[0]),
        "ci_95_low": pd.NA,
        "ci_95_high": pd.NA,
        "records": count,
        "interpretation": "Percent of 22,982 road-section/year rows.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--all-periods", type=Path, default=DEFAULT_ALL_PERIODS)
    parser.add_argument("-s", "--official-periods", type=Path, default=DEFAULT_OFFICIAL)
    parser.add_argument("-d", "--daily", type=Path, default=DEFAULT_DAILY)
    parser.add_argument("-q", "--annual-quality", type=Path, default=DEFAULT_ANNUAL_QUALITY)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    all_periods = pd.read_csv(args.all_periods)
    official = pd.read_csv(args.official_periods)
    daily = pd.read_csv(args.daily)
    quality = pd.read_csv(args.annual_quality)
    rows = []
    for wind_bin in ["20-25", ">=25"]:
        rows.extend([
            rate_row(all_periods, wind_bin, "All VDU, SDU, and derived VHDU periods"),
            rate_row(official, wind_bin, "Official VDU and SDU periods only"),
        ])
    rows.extend([daily_row(daily, False), daily_row(daily, True)])
    rows.extend([
        quality_row(quality, "nonpositive_vdu", "Nonpositive published VDU"),
        quality_row(quality, "nonpositive_derived_vhdu", "Nonpositive derived VHDU"),
    ])
    result = pd.DataFrame(rows)
    for column in ["estimate", "ci_95_low", "ci_95_high"]:
        result[column] = pd.to_numeric(result[column], errors="coerce").round(2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
