"""Draw one five-panel O/E figure for each weather variable."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.figures.presentation import save_figure, PANEL_TITLE_SIZE, panel_limit
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.ticker import MaxNLocator, MultipleLocator, StrMethodFormatter


INPUT = Path("reports/main/tables/weather_oe.csv")
OUTPUT_DIRECTORY = Path("reports/main/figures")
SEASON_OUTPUTS = {
    "f": "wind_oe_panels.png",
    "fg": "gust_oe_panels.png",
    "temperature": "temperature_oe_panels.png",
}
VARIABLES = ("f", "fg", "temperature")
SEASONS = ("Winter", "Spring", "Summer", "Autumn")
PERIODS = ("All year", *SEASONS)
SEASON_LABELS = {
    "Winter": "Winter",
    "Spring": "Spring",
    "Summer": "Summer",
    "Autumn": "Autumn",
}
VARIABLE_TITLES = {
    "f": "All year",
    "fg": "All year",
    "temperature": "All year",
}
VARIABLE_NAMES = {
    "f": "Mean wind",
    "fg": "Wind gust",
    "temperature": "Temperature",
}
X_LABELS = {
    "f": "Mean wind (m/s)",
    "fg": "Wind gust (m/s)",
    "temperature": "Temperature (°C)",
}
OUTCOMES = (
    "Minor injury accidents",
    "Severe/fatal accidents",
)
SOURCE_OUTCOMES = ("All injury accidents", "Severe/fatal accidents")
COLORS = ("#79BCE0", "#D62728")
DISPLAY_OUTCOMES = {
    "Minor injury accidents": "Minor injury",
    "Severe/fatal accidents": "Serious or fatal injury",
}
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
    "expected_accidents",
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
        return f"[{lower}, {upper}]"
    return f"{lower}–{upper}"


def validate(
    data: pd.DataFrame, expected_periods: tuple[str, ...] = PERIODS,
    expected_variables: tuple[str, ...] = VARIABLES,
) -> None:
    """Reject an incomplete or incompatible O/E result table."""
    missing = REQUIRED_COLUMNS - set(data)
    if missing:
        raise ValueError(f"O/E table is missing columns: {sorted(missing)}")
    if set(data["variable"]) != set(expected_variables):
        raise ValueError("O/E table does not contain the requested weather variables")
    if set(data["outcome"]) != set(SOURCE_OUTCOMES):
        raise ValueError("O/E table does not contain the two expected outcomes")
    if set(data["period"]) != set(expected_periods):
        raise ValueError(
            "O/E table does not contain the requested periods: "
            f"{', '.join(expected_periods)}"
        )


def disjoint_outcomes(
    data: pd.DataFrame, expected_periods: tuple[str, ...] = PERIODS,
    expected_variables: tuple[str, ...] = VARIABLES,
) -> pd.DataFrame:
    """Recover minor-injury counts from additive O and E, never from ratios.

    Both source outcomes use identical station-season weather fractions, so
    expected counts are additive across their disjoint severity components.
    Keep only plotting columns; background station counts are not additive.
    """
    validate(data, expected_periods, expected_variables)
    keys = ["variable", "period", "bin_label", "bin_order"]
    counts = ["observed_accidents", "expected_accidents"]
    total = data[data.outcome.eq(SOURCE_OUTCOMES[0])].set_index(keys)[counts]
    severe = data[data.outcome.eq(SOURCE_OUTCOMES[1])].set_index(keys)[counts]
    if not total.index.is_unique or not severe.index.is_unique:
        raise ValueError("Duplicate O/E plot cells")
    if set(total.index) != set(severe.index):
        raise ValueError("Severity groups have different O/E cells")
    minor = total - severe
    if (minor < -1e-9).any().any():
        raise ValueError("Severe/fatal counts exceed all-injury counts")
    frames = []
    for outcome, frame in zip(OUTCOMES, (minor, severe), strict=True):
        frame = frame.copy()
        frame["outcome"] = outcome
        frame["relative_accident_frequency"] = (
            frame.observed_accidents / frame.expected_accidents
        )
        frames.append(frame.reset_index())
    return pd.concat(frames, ignore_index=True)


def display_limit(panel: pd.DataFrame) -> float:
    """Scale each panel independently, retaining room for accident counts."""
    return panel_limit(float(panel["relative_accident_frequency"].max()))


def panel_readability_limit(panel: pd.DataFrame) -> float:
    return display_limit(panel)


def add_counts(axis: Axes, bars: BarContainer, counts: np.ndarray) -> None:
    """Write accident counts above the bars."""
    for bar, count in zip(bars, counts, strict=True):
        if count <= 0:
            continue
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
            label=DISPLAY_OUTCOMES[outcome],
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
    if variable == "temperature":
        axis.tick_params(axis="x", labelrotation=0, labelsize=11)
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
        fontsize=PANEL_TITLE_SIZE,
        fontweight="bold",
        zorder=4,
    )


def separate_count_labels(figure: plt.Figure) -> None:
    """Lift adjacent count labels when their rendered boxes touch."""
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    for axis in figure.axes:
        placed = []
        for text in sorted((t for t in axis.texts if hasattr(t, "xy")), key=lambda t: t.xy[0]):
            for _ in range(12):
                box = text.get_window_extent(renderer).expanded(1.12, 1.05)
                if not any(box.overlaps(other) for other in placed):
                    break
                x, y = text.get_position()
                text.set_position((x, y + COUNT_FONT_SIZE + 1))
            placed.append(text.get_window_extent(renderer).expanded(1.12, 1.05))


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


def plot_variable(data: pd.DataFrame, variable: str, output: Path) -> None:
    """Draw the complete year and four seasons for one weather variable."""
    from src.figures.season_layout import seasonal_figure
    figure, axes = seasonal_figure()
    titles = {"All year": VARIABLE_TITLES[variable], **SEASON_LABELS}
    for axis, period in zip(axes, PERIODS, strict=True):
        draw_panel(axis, data, variable, period, titles[period])
        panel = data[data.variable.eq(variable) & data.period.eq(period)]
        axis.set_ylim(0, panel_readability_limit(panel))
    add_legend(figure, axes[0])
    figure.supxlabel(X_LABELS[variable], fontsize=AXIS_TITLE_FONT_SIZE)
    figure.supylabel(
        "Observed / expected accidents (O/E)", fontsize=AXIS_TITLE_FONT_SIZE
    )
    separate_count_labels(figure)
    save_figure(figure, output, dpi=240)
    plt.close(figure)


def plot_all(data: pd.DataFrame, output_directory: Path) -> list[Path]:
    """Validate the result table and write the three retained figures."""
    data = disjoint_outcomes(data)
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    for variable in VARIABLES:
        output = output_directory / SEASON_OUTPUTS[variable]
        plot_variable(data, variable, output)
        outputs.append(output)
    return outputs


def plot_whole_year(
    data: pd.DataFrame,
    output: Path,
    year_label: str,
    *,
    x_labels: dict[str, str] | None = None,
    y_limits: dict[str, float] | None = None,
    y_steps: dict[str, float] | None = None,
    variables: tuple[str, ...] = VARIABLES,
) -> Path:
    """Draw whole-year panels for the requested weather variables."""
    data = disjoint_outcomes(data, ("All year",), variables)
    labels = X_LABELS if x_labels is None else x_labels
    figure, axes = plt.subplots(
        len(variables),
        1,
        figsize=(10.875, 4.35 * len(variables)),
        sharey=False,
        layout="constrained",
    )
    axes = np.atleast_1d(axes)
    for axis, variable in zip(axes, variables, strict=True):
        draw_panel(
            axis,
            data,
            variable,
            "All year",
            VARIABLE_NAMES[variable],
        )
        axis.text(.98, 1.025, "All year", transform=axis.transAxes, ha="right",
                  va="bottom", fontsize=PANEL_TITLE_SIZE, fontweight="bold")
        axis.set_xlabel(labels[variable], fontsize=AXIS_TITLE_FONT_SIZE)
        if y_limits is not None:
            axis.set_ylim(0, y_limits[variable])
        if y_steps is not None:
            axis.yaxis.set_major_locator(MultipleLocator(y_steps[variable]))
    add_legend(figure, axes[0])
    figure.supylabel(
        "Observed / expected accidents (O/E)", fontsize=AXIS_TITLE_FONT_SIZE
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    separate_count_labels(figure)
    save_figure(figure, output, dpi=240)
    plt.close(figure)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument(
        "-o", "--output-directory", type=Path, default=OUTPUT_DIRECTORY
    )
    parser.add_argument(
        "--whole-year-output",
        type=Path,
        help="Write one three-panel whole-year figure to this path.",
    )
    parser.add_argument(
        "--year-label",
        help="Year range shown inside whole-year panels (for example 2007–2018).",
    )
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    if args.whole_year_output:
        if not args.year_label:
            parser.error("--year-label is required with --whole-year-output")
        outputs = [
            plot_whole_year(data, args.whole_year_output, args.year_label)
        ]
    elif args.year_label:
        parser.error("--year-label requires --whole-year-output")
    else:
        outputs = plot_all(data, args.output_directory)
    print("wrote=" + ",".join(map(str, outputs)))


if __name__ == "__main__":
    main()
