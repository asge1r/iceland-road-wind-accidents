"""Draw daily traffic relative to sustained strong-wind duration."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT = Path("reports/main/tables/daily_traffic_by_high_wind_duration.csv")
OUTPUT = Path("reports/main/figures/daily_traffic_by_high_wind_duration.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {"hours_with_f_ge15", "counter_days", "relative_traffic_pct", "ci_95_low_pct", "ci_95_high_pct"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Duration table is missing columns: {sorted(missing)}")
    x = np.arange(len(data))
    values = data["relative_traffic_pct"].to_numpy(float)
    errors = np.vstack([
        values - data["ci_95_low_pct"].to_numpy(float),
        data["ci_95_high_pct"].to_numpy(float) - values,
    ])
    figure, axis = plt.subplots(figsize=(9.6, 5.8), constrained_layout=True)
    bars = axis.bar(x, values, color="#287271", width=0.68)
    axis.errorbar(x, values, yerr=errors, fmt="none", ecolor="#202020", capsize=4)
    axis.axhline(100, color="#202020", linestyle="--", linewidth=1.1)
    display_labels = {"0": "0", ">0-2": ">0–2", "2-6": "2–6", ">=6": "≥6"}
    axis.set_xticks(x, data["hours_with_f_ge15"].map(display_labels))
    axis.set_xlabel("Hours with mean wind f ≥ 15 m/s during the day")
    axis.set_ylabel("Observed traffic relative to calendar expectation (%)")
    axis.set_title("Daily traffic by duration of strong wind, 2019–2024")
    axis.set_ylim(80, 103)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    for bar, row in zip(bars, data.itertuples(index=False), strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2, 81.0, f"n={row.counter_days:,}", ha="center", va="bottom", fontsize=9, color="white")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
