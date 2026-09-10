"""Plot traffic-standardised O/E by wind speed and season."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.common import interval_labels


INPUT = Path("reports/main/tables/daily_season_oe.csv")
OUTPUT = Path("reports/main/figures/daily_season_oe.png")
SEASONS = ["Winter", "Spring", "Summer", "Fall"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {
        "season", "wind_bin", "observed_accidents", "traffic_standardised_oe",
        "ci_95_low", "ci_95_high",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"Seasonal O/E table is missing columns: {sorted(missing)}")

    figure, axes = plt.subplots(
        2, 2, figsize=(12.5, 8.5), sharex=True, sharey=True,
        constrained_layout=True,
    )
    ymax = max(2.0, float(data["traffic_standardised_oe"].max()) * 1.15)
    for axis, season in zip(axes.flat, SEASONS, strict=True):
        subset = data[data["season"].eq(season)].copy()
        x = np.arange(len(subset))
        estimate = subset["traffic_standardised_oe"].to_numpy(float)
        axis.scatter(x, estimate, color="#287271", s=48, zorder=3)
        axis.axhline(1, color="#444444", linestyle="--", linewidth=1)
        axis.set_title("Autumn" if season == "Fall" else season, fontsize=13)
        axis.set_xticks(x, interval_labels(subset["wind_bin"]))
        axis.set_ylim(0, ymax)
        axis.grid(axis="y", alpha=0.2)
        for position, value, count in zip(
            x, estimate, subset["observed_accidents"], strict=True
        ):
            axis.annotate(
                f"n={int(count)}", (position, value), xytext=(7, 5),
                textcoords="offset points", fontsize=8,
            )
    figure.supxlabel("Wind speed, f (m/s)", fontsize=13)
    figure.supylabel("Traffic-standardised accident O/E", fontsize=13)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
