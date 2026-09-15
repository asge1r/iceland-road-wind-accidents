"""Draw stacked minor and severe/fatal daily-traffic rates, annually and by season."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MultipleLocator, StrMethodFormatter

from src.figures.oe_histo import (
    AXIS_TITLE_FONT_SIZE, COUNT_FONT_SIZE, TICK_FONT_SIZE, SEASON_LABELS,
)


INPUT = Path("data/analysis/daily_vkt.csv")
OUTPUT = Path("reports/main/figures")
VARIABLES = ("f", "fg", "temperature")
OUTCOMES = ("Minor injury accidents", "Severe/fatal accidents")
PERIODS = ("All year", "Winter", "Spring", "Summer", "Autumn")
COLORS = ("#79BCE0", "#D62728")
RATE = "rate_per_million_vehicle_km"
ANNUAL_Y_MAX = {"f": 1.3, "fg": 1.3, "temperature": .3}
SEASONAL_Y_MAX = {"f": .8, "fg": .5}
X_LABELS = {
    "f": "Mean wind (m/s)",
    "fg": "Wind gust (m/s)",
    "temperature": "Temperature (°C)",
}
INTERVAL = re.compile(r"^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$")


def display_interval(value: str, bracketed: bool = False) -> str:
    if value.startswith(">="):
        return "≥" + value[2:].replace("-", "−")
    if value.startswith("<"):
        return "<" + value[1:].replace("-", "−")
    match = INTERVAL.fullmatch(value)
    if not match:
        return value
    separator = ", " if bracketed else "–"
    interval = separator.join(part.replace("-", "−") for part in match.groups())
    return f"[{interval}]" if bracketed else interval


def seasonal_limit(data: pd.DataFrame, variable: str) -> float:
    """Use requested wind/gust scales; fit the temperature stacks automatically."""
    if variable in SEASONAL_Y_MAX:
        return SEASONAL_Y_MAX[variable]
    selected = data[data["variable"].eq(variable)
                    & data["period"].isin(PERIODS[1:])
                    & data["outcome"].isin(OUTCOMES)]
    maximum = selected.groupby(["period", "bin_label"])[RATE].sum(min_count=1).max()
    step = .1
    return float(np.ceil(maximum * 1.2 / step) * step) if np.isfinite(maximum) and maximum > 0 else step


def combine_seasonal_tails(data: pd.DataFrame) -> pd.DataFrame:
    """Sum counts and exposure, never rates; leave annual/temperature bins alone."""
    result = data.copy()
    for variable, labels, combined, order in [
        ("f", ["15-20", ">=20"], ">=15", 3),
        ("fg", ["20-25", "25-30", ">=30"], ">=20", 4),
    ]:
        use = (result.variable.eq(variable) & result.period.isin(PERIODS[1:])
               & result.bin_label.isin(labels))
        if not use.any():
            continue
        keys = ["variable", "outcome", "period"]
        tails = result.loc[use].groupby(keys, as_index=False).agg(
            accidents=("accidents", "sum"), estimated_vehicle_km=("estimated_vehicle_km", "sum"),
        )
        tails["bin_label"], tails["bin_order"] = combined, order
        tails[RATE] = tails.accidents / tails.estimated_vehicle_km.where(tails.estimated_vehicle_km.gt(0)) * 1e6
        result = pd.concat([result.loc[~use], tails], ignore_index=True)
    return result


def draw(axis, data: pd.DataFrame, variable: str, period: str) -> None:
    panel = data[data["variable"].eq(variable) & data["period"].eq(period)]
    labels = panel[["bin_label", "bin_order"]].drop_duplicates().sort_values("bin_order")
    x = np.arange(len(labels))
    annual = period == "All year"
    bottom = np.zeros(len(labels))
    for index, outcome in enumerate(OUTCOMES):
        colour = COLORS[index]
        rows = panel[panel["outcome"].eq(outcome)].sort_values("bin_order")
        if rows["bin_label"].tolist() != labels["bin_label"].tolist():
            raise ValueError(f"Inconsistent bins for {variable}, {period}, {outcome}")
        # The disjoint injury categories share a denominator, so their rates
        # add to the total injury-accident rate at the top of the stack.
        heights = rows[RATE].to_numpy(float)
        bars = axis.bar(x, heights, bottom=bottom, width=.82,
                        color=colour, edgecolor="white", linewidth=.6,
                        label=("Minor injury" if index == 0 else "Serious or fatal injury"), zorder=2 + index)
        for bar, count in zip(bars, rows["accidents"], strict=True):
            if count <= 0 or not np.isfinite(bar.get_height()) or bar.get_height() <= 0:
                continue
            inside = index == 0
            y = bar.get_y() + bar.get_height() * (.5 if inside else 1)
            axis.annotate(str(int(count)), (bar.get_x() + bar.get_width()/2, y),
                          xytext=(0, 0 if inside else 4),
                          textcoords="offset points", ha="center",
                          va="center" if inside else "bottom",
                          fontsize=COUNT_FONT_SIZE, fontweight="bold", zorder=4)
        bottom += heights
    axis.set_xticks(x, [display_interval(value, variable == "temperature")
                       for value in labels["bin_label"]], rotation=0)
    axis.grid(axis="y", color="#E8E8E8", linewidth=.7)
    axis.set_axisbelow(True)
    axis.tick_params(axis="both", which="both", labelsize=TICK_FONT_SIZE, length=0)
    axis.yaxis.set_major_locator(
        MultipleLocator(.05 if annual and variable == "temperature" else .1)
    )
    axis.yaxis.set_major_formatter(StrMethodFormatter("{x:g}"))
    limit = ANNUAL_Y_MAX[variable] if annual else seasonal_limit(panel, variable)
    if np.nanmax(bottom) > limit:
        raise ValueError(f"{variable}, {period}: stack exceeds recovered supervisor y limit {limit}")
    axis.set_ylim(0, limit)
    axis.margins(x=.025)
    title = "All year" if annual else SEASON_LABELS[period]
    axis.text(.015, .965, title, transform=axis.transAxes, ha="left", va="top",
              fontsize=TICK_FONT_SIZE, fontweight="semibold", zorder=5)


def make_figures(data: pd.DataFrame, output: Path, *, variables=VARIABLES, prefix="") -> list[Path]:
    required = {"variable", "outcome", "period", "bin_label", "bin_order",
                "accidents", "estimated_vehicle_km", "rate_per_million_vehicle_km"}
    if not required <= set(data):
        raise ValueError(f"Daily weather-rate table is missing {sorted(required - set(data))}")
    if set(data["outcome"]) != set(OUTCOMES):
        raise ValueError("Daily weather-rate outcomes do not match the weather O/E outcomes")
    data = combine_seasonal_tails(data)
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    figure, axes = plt.subplots(len(variables), 1, figsize=(10.2, 4 * len(variables)), layout="constrained")
    for axis, variable in zip(axes, variables, strict=True):
        draw(axis, data, variable, "All year")
        axis.set_xlabel(X_LABELS[variable], fontsize=AXIS_TITLE_FONT_SIZE)
    figure.supylabel("Accidents per million vehicle-km", fontsize=AXIS_TITLE_FONT_SIZE)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside upper center", ncols=2, frameon=False, fontsize=TICK_FONT_SIZE)
    annual = output / f"{prefix}weather_rate_annual.png"
    figure.savefig(annual, dpi=240)
    plt.close(figure)
    paths.append(annual)
    for variable in variables:
        from src.figures.season_layout import seasonal_figure
        figure, axes = seasonal_figure()
        for axis, period in zip(axes, PERIODS, strict=True):
            draw(axis, data, variable, period)
        figure.supxlabel(X_LABELS[variable], fontsize=AXIS_TITLE_FONT_SIZE, x=.5)
        figure.supylabel("Accidents per million vehicle-km", fontsize=AXIS_TITLE_FONT_SIZE)
        handles, labels = axes[0].get_legend_handles_labels()
        figure.legend(handles, labels, loc="outside upper center", ncols=len(handles), frameon=False, fontsize=TICK_FONT_SIZE)
        path = output / f"{prefix}{variable}_traffic_rate_panels.png"
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
