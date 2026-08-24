"""Draw the gust-factor distribution from the canonical weather-frequency CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_INPUT = Path("data/analysis/weather_frequency.csv")
DEFAULT_OUTPUT = Path("reports/main/figures/gust_factor_distribution.png")
ORDER = ["0-1.2", "1.2-1.4", "1.4-1.6", "1.6-1.8", "1.8-2", ">=2"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    frequency = pd.read_csv(args.input)
    data = frequency[frequency["variable"].eq("gust_factor")].copy()
    data = data.groupby("bin_label", as_index=False).agg(
        measurements=("measurement_count", "sum")
    )
    data["bin_label"] = pd.Categorical(data["bin_label"], ORDER, ordered=True)
    data = data.sort_values("bin_label")
    data["share_pct"] = 100 * data["measurements"] / data["measurements"].sum()

    x = np.arange(len(data))
    figure, axis = plt.subplots(figsize=(10.5, 5.8), constrained_layout=True)
    bars = axis.bar(x, data["share_pct"], color="#287271", width=0.72)
    axis.set_xticks(x, data["bin_label"].astype("string").str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Gust factor, fg / f (unitless; f ≥ 3 m/s)")
    axis.set_ylabel("Share of eligible 10-minute observations (%)")
    axis.set_title("Gust-factor distribution in cleaned weather data")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    upper = float(data["share_pct"].max())
    axis.set_ylim(0, upper * 1.16)
    for bar, value in zip(bars, data["share_pct"], strict=True):
        label = f"{value:.2f}%" if value < 1 else f"{value:.1f}%"
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value + upper * 0.018,
            label,
            ha="center",
            va="bottom",
            fontsize=8,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
