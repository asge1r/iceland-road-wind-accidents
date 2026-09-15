"""Draw a compact descriptive overview of accident-time conditions."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.figures.common import interval_label
from src.figures.weather_rate import display_interval
from src.figures.oe_histo import separate_count_labels


DEFAULT_INPUT = Path("reports/main/tables/conditions.csv")
DEFAULT_OUTPUT = Path("reports/main/figures/conditions.png")
COLOR = "#79BCE0"


def panel(axis: plt.Axes, data: pd.DataFrame, title: str, xlabel: str = "") -> None:
    categories = data["category"].map(lambda value: display_interval(str(value), True) if "Temperature" in xlabel else interval_label(str(value)))
    minor = axis.bar(
        categories, data["minor_injury"], color=COLOR, label="Minor injury"
    )
    serious = axis.bar(
        categories,
        data["serious_or_fatal"],
        bottom=data["minor_injury"],
        color="#D62728",
        label="Serious or fatal",
    )
    axis.set_title(title, fontsize=16)
    axis.set_xlabel(xlabel, fontsize=15)
    axis.set_ylabel("Accidents", fontsize=15)
    axis.tick_params(labelsize=14)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    axis.set_ylim(0, data["accidents"].max() * 1.25)
    for bar, value in zip(minor, data["accidents"], strict=True):
        if value <= 0:
            continue
        axis.annotate(
            f"{int(value):,}",
            (bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 3), textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=12,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = pd.read_csv(args.input)

    # Keep the validated internal season label "Fall", but use the
    # reader-facing term "Autumn" in this thesis figure.
    season_mask = summary["dimension"].eq("season")
    summary.loc[season_mask, "category"] = summary.loc[season_mask, "category"].replace({"Fall": "Autumn"})

    seasons = summary[season_mask].copy()
    seasons["category"] = seasons.category.replace({"Spring": "Spring/Autumn", "Autumn": "Spring/Autumn"})
    seasons = seasons.groupby("category", sort=False, as_index=False)[["accidents", "minor_injury", "serious_or_fatal"]].sum()

    figure, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    panel(axes[0, 0], summary[summary["dimension"].eq("hour")], "Hour", "Hour")
    panel(
        axes[0, 1],
        seasons,
        "Season",
    )
    panel(
        axes[1, 0],
        summary[summary["dimension"].eq("daylight_class")],
        "Daylight",
    )
    panel(
        axes[1, 1],
        summary[summary["dimension"].eq("temperature_interval_c")],
        "Temperature",
        "Temperature interval (°C)",
    )
    axes[0, 0].tick_params(axis="x", labelrotation=45, labelsize=12)
    for axis in [axes[1, 0], axes[1, 1]]:
        axis.tick_params(axis="x", labelrotation=25)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(
        handles, labels, loc="outside upper center", ncol=2, frameon=False, fontsize=14
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    separate_count_labels(figure)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
