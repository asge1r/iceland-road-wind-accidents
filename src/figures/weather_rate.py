"""Draw traffic-adjusted weather-rate figures from the compact daily table."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT = Path("data/analysis/daily_weather_rate.csv")
OUTPUT = Path("reports/main/figures")
VARIABLES = ("f", "fg", "temperature")
OUTCOMES = ("Minor injury accidents", "Severe/fatal accidents")
PERIODS = ("All year", "Winter", "Spring", "Summer", "Autumn")
NAMES = {"f": "Mean wind", "fg": "Wind gust", "temperature": "Temperature"}
X_LABELS = {"f": "Mean wind, f (m/s)", "fg": "Wind gust, fg (m/s)",
            "temperature": "Temperature (°C)"}
COLORS = ("#0072B2", "#D55E00")
INTERVAL = re.compile(r"^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$")


def display_interval(value: str) -> str:
    if value.startswith(">="):
        return "≥" + value[2:].replace("-", "−")
    if value.startswith("<"):
        return "<" + value[1:].replace("-", "−")
    match = INTERVAL.fullmatch(value)
    if not match:
        return value
    return "–".join(part.replace("-", "−") for part in match.groups())


def draw(axis, data: pd.DataFrame, variable: str, period: str) -> None:
    panel = data[data["variable"].eq(variable) & data["period"].eq(period)]
    labels = panel[["bin_label", "bin_order"]].drop_duplicates().sort_values("bin_order")
    x = np.arange(len(labels))
    width = 0.42
    for index, (outcome, colour) in enumerate(zip(OUTCOMES, COLORS, strict=True)):
        rows = panel[panel["outcome"].eq(outcome)].sort_values("bin_order")
        bars = axis.bar(x + (index - .5) * width, rows["rate_per_100m_vehicle_km"],
                        width=width, color=colour, edgecolor="white", label=outcome)
        for bar, count in zip(bars, rows["accidents"], strict=True):
            axis.annotate(str(int(count)), (bar.get_x() + bar.get_width()/2, bar.get_height()),
                          xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)
    axis.set_xticks(x, [display_interval(value) for value in labels["bin_label"]], rotation=20)
    axis.grid(axis="y", color="#e5e5e5", linewidth=.7)
    axis.set_axisbelow(True)
    axis.set_title(period)


def make_figures(data: pd.DataFrame, output: Path) -> list[Path]:
    required = {"variable", "outcome", "period", "bin_label", "bin_order",
                "accidents", "estimated_vehicle_km", "rate_per_100m_vehicle_km"}
    if not required <= set(data):
        raise ValueError(f"Daily weather-rate table is missing {sorted(required - set(data))}")
    if set(data["outcome"]) != set(OUTCOMES):
        raise ValueError("Daily weather-rate outcomes do not match the weather O/E outcomes")
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    figure, axes = plt.subplots(3, 1, figsize=(10.2, 12), layout="constrained")
    for axis, variable in zip(axes, VARIABLES, strict=True):
        draw(axis, data, variable, "All year")
        axis.set_xlabel(X_LABELS[variable])
        axis.set_title(f"{NAMES[variable]} — All year")
    figure.supylabel("Accidents per 100 million estimated vehicle-km")
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside upper center", ncols=2, frameon=False)
    annual = output / "weather_rate_annual.png"
    figure.savefig(annual, dpi=240)
    plt.close(figure)
    paths.append(annual)
    for variable in VARIABLES:
        figure, axes = plt.subplots(2, 2, figsize=(14.5, 9.5), sharey=True, layout="constrained")
        for axis, period in zip(axes.flat, PERIODS[1:], strict=True):
            draw(axis, data, variable, period)
        figure.supxlabel(X_LABELS[variable])
        figure.supylabel("Accidents per 100 million estimated vehicle-km")
        handles, labels = axes.flat[0].get_legend_handles_labels()
        figure.legend(handles, labels, loc="outside upper center", ncols=2, frameon=False)
        path = output / f"{variable}_traffic_rate_panels.png"
        figure.savefig(path, dpi=240)
        plt.close(figure)
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    paths = make_figures(pd.read_csv(args.input), args.output)
    print("wrote=" + ",".join(map(str, paths)))


if __name__ == "__main__":
    main()
