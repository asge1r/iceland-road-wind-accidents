"""Plot weather-frequency, annual-traffic, and daily-traffic wind O/E."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.common import interval_labels


INPUT = Path("reports/main/tables/wind_oe_comparison.csv")
OUTPUT = Path("reports/main/figures/wind_oe_comparison.png")
METHODS = ["Weather frequency", "Annual traffic", "Daily traffic"]
TITLES = {
    "Weather frequency": "A. Weather frequency (primary)",
    "Annual traffic": "B. Annual traffic (broad support)",
    "Daily traffic": "C. Daily traffic (stricter check)",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {
        "method", "wind_bin", "observed_accidents", "observed_expected_ratio",
        "ci_95_low", "ci_95_high", "analysis_accidents",
    }
    if not required <= set(data):
        raise ValueError("Wind O/E comparison table is incomplete")
    if set(data["method"]) != set(METHODS):
        raise ValueError("Wind O/E comparison does not contain all three methods")

    figure, axes = plt.subplots(
        1, 3, figsize=(15.5, 5.8), sharey=True, constrained_layout=True
    )
    ymax = max(1.5, float(data["observed_expected_ratio"].max()) * 1.15)
    for axis, method in zip(axes, METHODS, strict=True):
        panel = data[data["method"].eq(method)].sort_values("bin_order")
        x = np.arange(len(panel))
        ratio = panel["observed_expected_ratio"].to_numpy(float)
        colours = np.where(panel["observed_accidents"].lt(20), "#A7A7A7", "#287271")
        bars = axis.bar(x, ratio, color=colours, width=0.7)
        axis.axhline(1, color="#202020", linestyle="--", linewidth=1)
        axis.set_xticks(x, interval_labels(panel["wind_bin"]), rotation=25)
        axis.set_xlabel("Mean wind, f (m/s)")
        axis.set_title(
            f"{TITLES[method]}\nN={int(panel['analysis_accidents'].iloc[0]):,}",
            fontsize=12,
        )
        axis.set_ylim(0, ymax)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
        for bar, count in zip(bars, panel["observed_accidents"], strict=True):
            axis.annotate(
                f"n={int(count)}",
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 5), textcoords="offset points",
                ha="center", va="bottom", fontsize=8,
            )
    axes[0].set_ylabel("Observed / expected accidents (O/E)")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
