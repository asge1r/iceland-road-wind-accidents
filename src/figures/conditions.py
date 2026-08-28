"""Draw a compact descriptive overview of accident-time conditions."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.figures.common import interval_label


DEFAULT_INPUT = Path("reports/main/tables/accident_conditions_summary.csv")
DEFAULT_OUTPUT = Path("reports/main/figures/accident_conditions_overview.png")
COLOR = "#547A99"


def panel(axis: plt.Axes, data: pd.DataFrame, title: str, xlabel: str = "") -> None:
    categories = data["category"].map(interval_label)
    bars = axis.bar(categories, data["accidents"], color=COLOR)
    axis.set_title(title)
    axis.set_xlabel(xlabel)
    axis.set_ylabel("Accidents")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    for bar, value in zip(bars, data["accidents"], strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{int(value):,}",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = pd.read_csv(args.input)
    figure, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    panel(axes[0, 0], summary[summary["dimension"].eq("hour")], "Accidents by hour", "Hour")
    panel(
        axes[0, 1],
        summary[summary["dimension"].eq("season")],
        "Accidents by season",
    )
    panel(
        axes[1, 0],
        summary[summary["dimension"].eq("daylight_class")],
        "Accidents by estimated daylight",
    )
    panel(
        axes[1, 1],
        summary[summary["dimension"].eq("temperature_interval_c")],
        "Accidents by matched temperature",
        "Temperature interval (°C)",
    )
    axes[0, 0].tick_params(axis="x", labelrotation=45)
    for axis in [axes[1, 0], axes[1, 1]]:
        axis.tick_params(axis="x", labelrotation=25)
    figure.suptitle("Rural injury accidents: time and environmental conditions")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
