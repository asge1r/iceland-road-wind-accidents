"""Draw the accident-time rate model with within-day allocated traffic."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.common import interval_labels


INPUT = Path("reports/main/tables/daily_allocated_rate_ratio_by_wind.csv")
OUTPUT = Path("reports/main/figures/daily_allocated_rate_ratio_by_wind.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {"wind_bin", "observed_accidents", "rate_ratio", "ci_95_low", "ci_95_high"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Allocated-rate table is missing columns: {sorted(missing)}")
    x = np.arange(len(data))
    values = data["rate_ratio"].to_numpy(float)
    low = data["ci_95_low"].fillna(data["rate_ratio"]).to_numpy(float)
    high = data["ci_95_high"].fillna(data["rate_ratio"]).to_numpy(float)
    figure, axis = plt.subplots(figsize=(9.4, 5.8), constrained_layout=True)
    bars = axis.bar(x, values, color="#287271", width=0.68)
    axis.errorbar(x, values, yerr=np.vstack([values-low, high-values]), fmt="none", ecolor="#202020", capsize=4)
    axis.axhline(1, color="#202020", linestyle="--", linewidth=1.1)
    axis.set_xticks(x, interval_labels(data["wind_bin"]))
    axis.set_xlabel("Mean wind at the matched accident time, f (m/s)")
    axis.set_ylabel("Within-counter-year rate ratio versus 0–10 m/s")
    axis.set_title("Accident rate with observed daily traffic allocated by wind time")
    axis.set_ylim(0, float(high.max()) * 1.14)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    for bar, row in zip(bars, data.itertuples(index=False), strict=True):
        axis.text(bar.get_x()+bar.get_width()/2, max(0.18, bar.get_height()*0.45), f"n={row.observed_accidents}", ha="center", va="center", fontsize=9, color="white")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
