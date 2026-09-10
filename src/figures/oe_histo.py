"""Draw the four retained weather O/E histogram figures."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.ticker import MaxNLocator, StrMethodFormatter


INPUT = Path("reports/main/tables/weather_oe.csv")
OUTPUT_DIRECTORY = Path("reports/main/figures")
ANNUAL_OUTPUT = "weather_oe_annual.png"
SEASON_OUTPUTS = {
    "f": "wind_oe_panels.png",
    "fg": "gust_oe_panels.png",
    "temperature": "temperature_oe_panels.png",
}
VARIABLES = ("f", "fg", "temperature")
SEASONS = ("Winter", "Spring", "Summer", "Autumn")
SEASON_LABELS = {
    "Winter": "Winter (Dec–Mar)",
    "Spring": "Spring (Apr–May)",
    "Summer": "Summer (Jun–Sep)",
    "Autumn": "Autumn (Oct–Nov)",
}
VARIABLE_TITLES = {
    "f": "Mean wind — All year (Jan–Dec)",
    "fg": "Wind gust — All year (Jan–Dec)",
    "temperature": "Temperature — All year (Jan–Dec)",
}
X_LABELS = {
    "f": "Mean wind, f (m/s)",
    "fg": "Wind gust, fg (m/s)",
    "temperature": "Temperature °C",
}
OUTCOMES = (
    "Minor injury accidents",
    "Severe/fatal accidents",
)
COLORS = ("#0072B2", "#D55E00")
BAR_WIDTH = 0.425
TICK_FONT_SIZE = 12
COUNT_FONT_SIZE = 11
AXIS_TITLE_FONT_SIZE = 16.5
INTERVAL = re.compile(r"^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$")
REQUIRED_COLUMNS = {
    "variable",
    "outcome",
    "period",
    "bin_label",
    "bin_order",
    "observed_accidents",
    "relative_accident_frequency",
}


def interval_label(value: str, bracketed: bool = False) -> str:
    """Format a stored interval for a figure axis."""
    if value.startswith(">="):
        return "≥" + value[2:].replace("-", "−")
    if value.startswith("<"):
        return "<" + value[1:].replace("-", "−")
    match = INTERVAL.fullmatch(value)
    if not match:
        return value
    lower, upper = (part.replace("-", "−") for part in match.groups())
    if bracketed:
        return f"[{lower},{upper}]"
    return f"{lower}-{upper}"


def validate(data: pd.DataFrame) -> None:
    """Reject an incomplete or incompatible O/E result table."""
    missing = REQUIRED_COLUMNS - set(data)
    if missing:
        raise ValueError(f"O/E table is missing columns: {sorted(missing)}")
    if set(data["variable"]) != set(VARIABLES):
        raise ValueError("O/E table does not contain exactly f, fg, and temperature")
    if set(data["outcome"]) != set(OUTCOMES):
        raise ValueError("O/E table does not contain the two expected outcomes")
    expected_periods = {"All year", *SEASONS}
    if set(data["period"]) != expected_periods:
        raise ValueError("O/E table does not contain the five expected periods")


def display_limit(panel: pd.DataFrame) -> float:
    """Leave vertical room for the tallest bar's count."""
    maximum = float(panel["relative_accident_frequency"].max())
    return max(1.5, maximum * 1.18)


def add_counts(axis: Axes, bars: BarContainer, counts: np.ndarray) -> None:
    """Write accident counts above the bars."""
    for bar, count in zip(bars, counts, strict=True):
        axis.annotate(
            f"{count}",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=COUNT_FONT_SIZE,
            fontweight="bold",
            color="#202020",
            zorder=3,
        )


def draw_panel(
    axis: Axes,
    data: pd.DataFrame,
    variable: str,
    period: str,
    title: str,
) -> None:
    """Draw one variable-period panel."""
    panel = data[data["variable"].eq(variable) & data["period"].eq(period)]
    labels = (
        panel[["bin_label", "bin_order"]]
        .drop_duplicates()
        .sort_values("bin_order")["bin_label"]
        .tolist()
    )
    if not labels:
        raise ValueError(f"No data for {variable}, {period}")

    x = np.arange(len(labels))
    axis.set_axisbelow(True)
    axis.grid(axis="y", color="#E8E8E8", linewidth=0.7, zorder=0)
    axis.axhline(1, color="#B8B8B8", linewidth=1.7, zorder=1)

    for index, (outcome, color) in enumerate(zip(OUTCOMES, COLORS, strict=True)):
        series = panel[panel["outcome"].eq(outcome)].sort_values("bin_order")
        if series["bin_label"].tolist() != labels:
            raise ValueError(f"Inconsistent bins for {variable}, {period}, {outcome}")
        positions = x + (index - 0.5) * BAR_WIDTH
        bars = axis.bar(
            positions,
            series["relative_accident_frequency"].to_numpy(float),
            width=BAR_WIDTH,
            color=color,
            label=outcome,
            edgecolor="white",
            linewidth=0.6,
            zorder=2,
        )
        add_counts(axis, bars, series["observed_accidents"].to_numpy(int))

    axis.set_xticks(
        x,
        [interval_label(label, variable == "temperature") for label in labels],
    )
    axis.tick_params(axis="both", labelsize=TICK_FONT_SIZE)
    axis.yaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 5, 10]))
    axis.yaxis.set_major_formatter(StrMethodFormatter("{x:g}"))
    axis.set_ylim(0, display_limit(panel))
    axis.margins(x=0.025)
    axis.text(
        0.015,
        0.965,
        title,
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        fontweight="semibold",
        zorder=4,
    )


def add_legend(figure: plt.Figure, axis: Axes) -> None:
    """Add one shared legend above the panels."""
    handles, labels = axis.get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="outside upper center",
        ncols=2,
        frameon=False,
        fontsize=TICK_FONT_SIZE,
    )


def plot_annual(data: pd.DataFrame, output: Path) -> None:
    """Draw all three weather variables for the complete year."""
    figure, axes = plt.subplots(3, 1, figsize=(10.125, 12), layout="constrained")
    for axis, variable in zip(axes, VARIABLES, strict=True):
        draw_panel(axis, data, variable, "All year", VARIABLE_TITLES[variable])
        axis.set_xlabel(X_LABELS[variable], fontsize=AXIS_TITLE_FONT_SIZE)
    add_legend(figure, axes[0])
    figure.supylabel(
        "Observed / expected accidents (O/E)", fontsize=AXIS_TITLE_FONT_SIZE
    )
    figure.savefig(output, dpi=240)
    plt.close(figure)


def plot_seasons(data: pd.DataFrame, variable: str, output: Path) -> None:
    """Draw the four seasons for one weather variable."""
    figure, axes = plt.subplots(2, 2, figsize=(14.5, 9.5), layout="constrained")
    for axis, period in zip(axes.flat, SEASONS, strict=True):
        draw_panel(axis, data, variable, period, SEASON_LABELS[period])
    add_legend(figure, axes.flat[0])
    figure.supxlabel(X_LABELS[variable], fontsize=AXIS_TITLE_FONT_SIZE)
    figure.supylabel(
        "Observed / expected accidents (O/E)", fontsize=AXIS_TITLE_FONT_SIZE
    )
    figure.savefig(output, dpi=240)
    plt.close(figure)


def plot_all(data: pd.DataFrame, output_directory: Path) -> list[Path]:
    """Validate the result table and write the four retained figures."""
    validate(data)
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs = [output_directory / ANNUAL_OUTPUT]
    plot_annual(data, outputs[0])
    for variable in VARIABLES:
        output = output_directory / SEASON_OUTPUTS[variable]
        plot_seasons(data, variable, output)
        outputs.append(output)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument(
        "-o", "--output-directory", type=Path, default=OUTPUT_DIRECTORY
    )
    args = parser.parse_args()
    outputs = plot_all(pd.read_csv(args.input), args.output_directory)
    print("wrote=" + ",".join(map(str, outputs)))


if __name__ == "__main__":
    main()
