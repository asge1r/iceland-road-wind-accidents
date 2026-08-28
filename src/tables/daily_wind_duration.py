"""Compare daily traffic with hours of sustained mean wind at least 15 m/s."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


INPUT = Path("data/analysis/daily_traffic.csv")
OUTPUT = Path("reports/main/tables/daily_traffic_by_high_wind_duration.csv")
LABELS = ["0", ">0-2", "2-6", ">=6"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-b", "--bootstrap-replicates", type=int, default=1000)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {
        "date", "counter_id", "traffic", "full_observation_count",
        "f_full_bin_15_20_count", "f_full_bin_20_25_count",
        "f_full_bin_ge25_count",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"Daily traffic input is missing columns: {sorted(missing)}")
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data = data[
        data["traffic"].ge(0) & data["full_observation_count"].ge(108)
    ].copy()
    data["strong_wind_hours"] = (
        data[[
            "f_full_bin_15_20_count", "f_full_bin_20_25_count",
            "f_full_bin_ge25_count",
        ]].sum(axis=1) / 6
    )
    data["duration_bin"] = pd.cut(
        data["strong_wind_hours"], [-0.001, 0.001, 2, 6, np.inf],
        labels=LABELS, right=False, include_lowest=True,
    )
    data["year"] = data["date"].dt.year
    data["month"] = data["date"].dt.month
    data["weekday"] = data["date"].dt.weekday
    keys = ["counter_id", "year", "month", "weekday"]
    baseline = data.groupby(keys, as_index=False).agg(
        expected_traffic=("traffic", "mean")
    )
    data = data.merge(baseline, on=keys, how="left", validate="many_to_one")
    by_counter = data.groupby(
        ["counter_id", "duration_bin"], observed=True, as_index=False
    ).agg(observed=("traffic", "sum"), expected=("expected_traffic", "sum"))
    counters = by_counter["counter_id"].drop_duplicates().to_numpy()
    rng = np.random.default_rng(20260828)
    rows: list[dict[str, object]] = []
    for label in LABELS:
        selected = data[data["duration_bin"].astype("string").eq(label)]
        counter = by_counter[by_counter["duration_bin"].astype("string").eq(label)].set_index("counter_id")
        observed = counter["observed"].reindex(counters, fill_value=0).to_numpy(float)
        expected = counter["expected"].reindex(counters, fill_value=0).to_numpy(float)
        sampled = rng.integers(0, len(counters), size=(args.bootstrap_replicates, len(counters)))
        ratios = observed[sampled].sum(axis=1) / expected[sampled].sum(axis=1)
        estimate = selected["traffic"].sum() / selected["expected_traffic"].sum()
        rows.append({
            "hours_with_f_ge15": label,
            "counter_days": len(selected),
            "counters": selected["counter_id"].nunique(),
            "observed_vehicles": int(selected["traffic"].sum()),
            "expected_vehicles": selected["expected_traffic"].sum(),
            "relative_traffic_pct": 100 * estimate,
            "ci_95_low_pct": 100 * np.quantile(ratios, 0.025),
            "ci_95_high_pct": 100 * np.quantile(ratios, 0.975),
        })
    output = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()
