"""Plot daily traffic relative to calendar expectation by weather interval."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.figures.presentation import save_figure, PANEL_TITLE_SIZE
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator, StrMethodFormatter

from src.figures.oe_histo import (
    AXIS_TITLE_FONT_SIZE,
    COUNT_FONT_SIZE,
    TICK_FONT_SIZE,
    VARIABLE_NAMES,
)
from src.figures.weather_rate import display_interval


INPUT = Path("data/analysis/traffic_weather_response.csv")
OUTPUT = Path("reports/main/figures/traffic_weather_response.png")
VARIABLES = ("f", "fg", "temperature")
BAR_COLOR = "#4C9ED9"
X_LABELS = {
    "f": "Mean wind (m/s)",
    "fg": "Wind gust (m/s)",
    "temperature": "Temperature (°C)",
}


def make_figure(data: pd.DataFrame, output: Path) -> Path:
    required = {
        "variable", "bin_label", "bin_order", "traffic_multiplier",
        "traffic_change_pct",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"Traffic-response table is missing: {sorted(missing)}")
    if set(data["variable"]) != set(VARIABLES):
        raise ValueError("Traffic-response table must contain f, fg, and temperature")
    if data.duplicated(["variable", "bin_label"]).any():
        raise ValueError("Traffic-response table has duplicate variable-bin rows")

    figure, axes = plt.subplots(
        3, 1, figsize=(10.875, 13), sharey=True, layout="constrained"
    )
    percentages = 100 * data["traffic_multiplier"]
    upper = max(120, float(np.ceil(percentages.max() * 1.15 / 10) * 10))
    for axis, variable in zip(axes, VARIABLES, strict=True):
        panel = data[data["variable"].eq(variable)].sort_values("bin_order")
        x = np.arange(len(panel))
        values = 100 * panel["traffic_multiplier"].to_numpy(float)
        bars = axis.bar(x, values, width=0.82, color=BAR_COLOR, zorder=2)
        axis.axhline(100, color="#C8C8C8", linewidth=1.8, zorder=1)
        axis.grid(axis="y", color="#EBEBEB", linewidth=0.7, zorder=0)
        axis.set_axisbelow(True)
        axis.set_xticks(
            x,
            [
                display_interval(label, variable == "temperature")
                for label in panel["bin_label"]
            ],
        )
        axis.tick_params(
            axis="both", which="both", labelsize=TICK_FONT_SIZE, length=0
        )
        axis.yaxis.set_major_locator(MaxNLocator(nbins=7, steps=[1, 2, 5, 10]))
        axis.yaxis.set_major_formatter(StrMethodFormatter("{x:g}"))
        axis.set_ylim(0, upper)
        axis.set_xlabel(X_LABELS[variable], fontsize=AXIS_TITLE_FONT_SIZE)
        axis.text(
            0.015,
            0.965,
            VARIABLE_NAMES[variable],
            transform=axis.transAxes,
            ha="left",
            va="top",
            fontsize=PANEL_TITLE_SIZE,
            fontweight="bold",
            zorder=4,
        )
        axis.text(.98, .965, "All year", transform=axis.transAxes,
                  ha="right", va="top", fontsize=PANEL_TITLE_SIZE, fontweight="bold")
        for bar, change in zip(
            bars, panel["traffic_change_pct"].to_numpy(float), strict=True
        ):
            label = f"{change:+.1f}%".replace("-", "−")
            axis.annotate(
                label,
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=COUNT_FONT_SIZE,
                fontweight="bold",
                zorder=3,
            )
    figure.supylabel(
        "Observed traffic / expected traffic (%)",
        fontsize=AXIS_TITLE_FONT_SIZE,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    save_figure(figure, output, dpi=240)
    plt.close(figure)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(f"wrote={make_figure(pd.read_csv(args.input), args.output)}")


if __name__ == "__main__":
    main()
