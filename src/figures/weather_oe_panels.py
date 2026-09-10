"""Draw five-period O/E panels for one weather variable and two outcomes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.common import interval_labels


INPUT = Path("reports/main/tables/weather_oe_panels.csv")
OUTPUTS = {
    "f": Path("reports/main/figures/wind_oe_panels.png"),
    "fg": Path("reports/main/figures/gust_oe_panels.png"),
    "temperature": Path("reports/main/figures/temperature_oe_panels.png"),
}
PERIODS = ["All year", "Winter", "Spring", "Summer", "Autumn"]
OUTCOMES = [
    "All injury accidents (meiðsli ≤ 3)",
    "Serious/fatal subset (meiðsli ≤ 2)",
]
COLORS = ["#287271", "#C7522A"]
X_LABELS = {
    "f": "Mean wind, f (m/s)",
    "fg": "Wind gust, fg (m/s)",
    "temperature": "Temperature (°C)",
}


def display_limit(data: pd.DataFrame) -> float:
    """Keep sparse extreme ratios from flattening every informative bar."""
    stable = data.loc[~data["sparse_bin"], "relative_accident_frequency"]
    source = stable if not stable.empty else data["relative_accident_frequency"]
    return max(2.0, float(source.max()) * 1.22)


def plot(data: pd.DataFrame, variable: str, output: Path) -> None:
    subset = data[data["variable"].eq(variable)].copy()
    if set(subset["period"]) != set(PERIODS):
        raise ValueError(f"Incomplete panel periods for {variable}")
    figure = plt.figure(figsize=(13.5, 12.2), constrained_layout=True)
    axes = figure.subplot_mosaic(
        [["All year", "All year"], ["Winter", "Spring"], ["Summer", "Autumn"]],
        sharey=True,
    )
    ymax = display_limit(subset)
    width = 0.38
    for period in PERIODS:
        axis = axes[period]
        panel = subset[subset["period"].eq(period)]
        labels = (
            panel[["coarse_bin", "bin_order"]]
            .drop_duplicates()
            .sort_values("bin_order")["coarse_bin"]
            .tolist()
        )
        x = np.arange(len(labels))
        totals: list[str] = []
        for outcome_index, (outcome, color) in enumerate(
            zip(OUTCOMES, COLORS, strict=True)
        ):
            series = panel[panel["outcome"].eq(outcome)].sort_values("bin_order")
            if series["coarse_bin"].tolist() != labels:
                raise ValueError(f"Inconsistent bins for {variable}, {period}, {outcome}")
            values = series["relative_accident_frequency"].to_numpy(float)
            counts = series["observed_accidents"].to_numpy(int)
            positions = x + (outcome_index - 0.5) * width
            colors = np.where(series["sparse_bin"], "#A9A9A9", color)
            bars = axis.bar(
                positions, np.minimum(values, ymax), width=width,
                color=colors, label=outcome,
                hatch="//" if outcome_index else None,
            )
            totals.append(f"{counts.sum():,}")
            for bar, value, count in zip(bars, values, counts, strict=True):
                text = str(count)
                if value > ymax:
                    text = f"{value:.1f}↑\n{text}"
                axis.annotate(
                    text,
                    (bar.get_x() + bar.get_width() / 2, min(value, ymax)),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=6.7,
                )
        axis.axhline(1, color="#303030", linestyle="--", linewidth=1)
        axis.set_title(
            f"{period}\nN={totals[0]} all injury; N={totals[1]} serious/fatal",
            fontsize=11,
        )
        axis.set_xticks(
            x, interval_labels(pd.Series(labels)), rotation=25, ha="right"
        )
        axis.set_ylim(0, ymax)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
    axes["All year"].legend(frameon=False, loc="upper left", fontsize=9)
    figure.supxlabel(X_LABELS[variable])
    figure.supylabel("Observed / expected accidents (O/E)")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=240)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-v", "--variable", choices=OUTPUTS, required=True)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    output = args.output or OUTPUTS[args.variable]
    plot(pd.read_csv(args.input), args.variable, output)
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
