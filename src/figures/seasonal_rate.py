"""Draw four season-specific mean-wind rate-ratio panels."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.common import interval_labels


INPUT = Path("reports/main/tables/seasonal_poisson_rate_ratio_by_wind.csv")
OUTPUT = Path("reports/main/figures/seasonal_poisson_rate_ratio_by_wind.png")
SEASONS = ["Winter", "Spring", "Summer", "Fall"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {
        "season", "bin_label", "observed_accidents",
        "time_proportional_rate_ratio", "time_proportional_ci_95_low",
        "time_proportional_ci_95_high",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"Seasonal rate table is missing columns: {sorted(missing)}")
    figure, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, constrained_layout=True)
    finite_high = data["time_proportional_ci_95_high"].replace([np.inf, -np.inf], np.nan)
    ymax = max(2.0, float(finite_high.max()) * 1.08)
    for axis, season in zip(axes.flat, SEASONS, strict=True):
        subset = data[data["season"].eq(season)].copy()
        x = np.arange(len(subset))
        values = subset["time_proportional_rate_ratio"].to_numpy(float)
        low = subset["time_proportional_ci_95_low"].fillna(
            subset["time_proportional_rate_ratio"]
        ).to_numpy(float)
        high = subset["time_proportional_ci_95_high"].fillna(
            subset["time_proportional_rate_ratio"]
        ).to_numpy(float)
        bars = axis.bar(x, values, color="#287271", width=0.7)
        axis.errorbar(
            x, values, yerr=np.vstack([values - low, high - values]),
            fmt="none", ecolor="#202020", capsize=3,
        )
        axis.axhline(1, color="#202020", linestyle="--", linewidth=1)
        axis.set_title(season)
        axis.set_ylim(0, ymax)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
        axis.set_xticks(x, interval_labels(subset["bin_label"]), rotation=25, ha="right")
        for bar, row in zip(bars, subset.itertuples(index=False), strict=True):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                max(0.12, min(bar.get_height() * 0.45, ymax * 0.35)),
                f"n={row.observed_accidents}", ha="center", va="center",
                fontsize=7.5, color="white",
            )
    figure.supylabel("Within-road-year rate ratio versus 0–5 m/s")
    figure.supxlabel("Mean wind-speed interval, f (m/s)")
    figure.suptitle("Estimated rural injury-accident rate ratio by season")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
