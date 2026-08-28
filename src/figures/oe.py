"""Draw O/E figures from the completed O/E result table."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.tables.oe import (
    PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
    PRIMARY_VARIABLE,
    VARIABLE_COLORS,
    VARIABLE_LABELS,
    VARIABLE_XLABELS,
)
from src.figures.common import interval_labels


DEFAULT_INPUT = Path("reports/main/tables/oe_results.csv")
DEFAULT_OUTPUT = Path("reports/main/figures")


def plot_one_variable(data: pd.DataFrame, variable: str, path: Path) -> None:
    subset = data[data["variable"].eq(variable)].sort_values("bin_order")
    x = np.arange(len(subset))
    values = subset["relative_accident_frequency"].to_numpy(float)
    figure, axis = plt.subplots(figsize=(14.5, 7.2), constrained_layout=True)
    bars = axis.bar(x, values, color=np.where(subset["observed_accidents"].lt(20), "#A7A7A7", VARIABLE_COLORS[variable]), width=0.72)
    axis.axhline(1, color="#222222", linestyle="--", linewidth=1)
    axis.set_xticks(x, interval_labels(subset["coarse_bin"]))
    axis.set_xlabel(VARIABLE_XLABELS[variable])
    axis.set_ylabel("Observed / expected accidents")
    axis.set_title(f"Accident occurrence by {VARIABLE_LABELS[variable].lower()}")
    axis.grid(axis="y", alpha=0.2)
    top = max(1.5, np.nanmax(values) * 1.18)
    axis.set_ylim(0, top)
    for bar, count in zip(bars, subset["observed_accidents"], strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height() * 0.55, top * 0.06), f"n={int(count)}", ha="center", va="center", fontsize=9, color="white")
    figure.savefig(path, dpi=240)
    plt.close(figure)


def plot_primary(data: pd.DataFrame, path: Path) -> None:
    subset = data[data["variable"].eq(PRIMARY_VARIABLE)].sort_values("bin_order")
    x = np.arange(len(subset))
    ratio = subset["relative_accident_frequency"].to_numpy(float)
    figure, axis = plt.subplots(figsize=(14.5, 7.2), constrained_layout=True)
    bars = axis.bar(x, ratio, color=VARIABLE_COLORS[PRIMARY_VARIABLE], width=0.72)
    axis.axhline(1, color="#222222", linestyle="--", linewidth=1)
    axis.set_ylabel("Observed / expected accidents (O/E)")
    axis.set_xlabel("Mean wind-speed interval, f (m/s)")
    axis.set_xticks(x, interval_labels(subset["coarse_bin"]))
    axis.set_title("Relative occurrence of rural injury accidents by mean wind speed")
    axis.grid(axis="y", alpha=0.2)
    top = max(1.5, ratio.max() * 1.18)
    axis.set_ylim(0, top)
    for bar, count in zip(bars, subset["observed_accidents"], strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height() * 0.55, top * 0.06), f"n={int(count)}", ha="center", va="center", fontsize=10, color="white")
    figure.savefig(path, dpi=240)
    plt.close(figure)


def plot_mean_wind_strata(data: pd.DataFrame, variable: str, group_column: str, groups: list[str], fixed_column: str, fixed_value: str, title: str, path: Path) -> None:
    subset = data[data["variable"].eq(variable) & data["radius_km"].eq(20) & data["max_time_difference_minutes"].eq(PRIMARY_MAX_TIME_DIFFERENCE_MINUTES) & data[fixed_column].eq(fixed_value) & data[group_column].isin(groups)].copy()
    upper_mapping = (
        {"20-25": ">=20", ">=25": ">=20"}
        if variable == "f"
        else {"25-30": ">=25", "30-35": ">=25", ">=35": ">=25"}
    )
    subset["display_bin"] = subset["coarse_bin"].replace(upper_mapping)
    display_order = (
        ["0-5", "5-10", "10-15", "15-20", ">=20"]
        if variable == "f"
        else ["0-5", "5-10", "10-15", "15-20", "20-25", ">=25"]
    )
    subset = subset.groupby([group_column, "display_bin"], as_index=False).agg(
        observed_accidents=("observed_accidents", "sum"),
        expected_accidents=("expected_accidents", "sum"),
    )
    subset["relative_accident_frequency"] = (
        subset["observed_accidents"] / subset["expected_accidents"]
    )
    subset["bin_order"] = subset["display_bin"].map(
        {label: index for index, label in enumerate(display_order)}
    )
    top = max(1.5, subset["relative_accident_frequency"].max() * 1.18)
    rows = int(np.ceil(len(groups) / 2))
    figure, axes = plt.subplots(rows, 2, figsize=(14.5, 5.3 * rows), sharey=True, constrained_layout=True)
    axes = np.atleast_1d(axes).ravel()
    for axis, group in zip(axes, groups, strict=True):
        panel = subset[subset[group_column].eq(group)].sort_values("bin_order")
        x = np.arange(len(panel))
        colors = np.where(
            panel["observed_accidents"].lt(20),
            "#A7A7A7",
            VARIABLE_COLORS[variable],
        )
        bars = axis.bar(
            x,
            panel["relative_accident_frequency"],
            color=colors,
            width=0.72,
        )
        axis.axhline(1, color="#222222", linestyle="--", linewidth=1)
        axis.set_xticks(x, interval_labels(panel["display_bin"]))
        axis.set_title(group)
        axis.set_ylim(0, top)
        axis.grid(axis="y", alpha=0.2)
        for bar, count in zip(bars, panel["observed_accidents"], strict=True):
            axis.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height() * 0.55, top * 0.06), f"n={int(count)}", ha="center", va="center", fontsize=8, color="white")
    for axis in axes[len(groups):]:
        axis.set_axis_off()
    figure.supxlabel(VARIABLE_XLABELS[variable])
    figure.supylabel("Observed / expected accidents (O/E)")
    figure.suptitle(title)
    figure.savefig(path, dpi=240)
    plt.close(figure)


def primary_rows(results: pd.DataFrame) -> pd.DataFrame:
    return results[
        results["radius_km"].eq(20)
        & results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & results["severity_group"].eq("Injury accidents")
        & results["analysis_season"].eq("All seasons")
    ].copy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    results = pd.read_csv(args.input)
    primary = primary_rows(results)
    args.output.mkdir(parents=True, exist_ok=True)
    plot_primary(primary, args.output / "mean_wind_oe.png")
    plot_one_variable(primary, "fg", args.output / "gust_oe.png")
    plot_one_variable(primary, "gust_factor", args.output / "gust_factor_oe.png")
    plot_one_variable(primary, "temperature", args.output / "temperature_oe.png")
    plot_mean_wind_strata(
        results,
        "f",
        "analysis_season",
        ["Winter", "Spring", "Summer", "Fall"],
        "severity_group",
        "Injury accidents",
        "Mean wind O/E by season",
        args.output / "mean_wind_by_season_oe.png",
    )
    plot_mean_wind_strata(
        results,
        "f",
        "severity_group",
        ["1 vehicle", "2 or more vehicles"],
        "analysis_season",
        "All seasons",
        "Mean wind O/E by number of vehicles involved",
        args.output / "mean_wind_by_vehicle_group_oe.png",
    )
    plot_mean_wind_strata(
        results,
        "fg",
        "analysis_season",
        ["Winter", "Spring", "Summer", "Fall"],
        "severity_group",
        "Injury accidents",
        "Matched-time wind-gust O/E by season",
        args.output / "gust_by_season_oe.png",
    )
    plot_mean_wind_strata(
        results,
        "fg",
        "severity_group",
        ["1 vehicle", "2 or more vehicles"],
        "analysis_season",
        "All seasons",
        "Matched-time wind-gust O/E by number of vehicles involved",
        args.output / "gust_by_vehicle_group_oe.png",
    )
    print(f"wrote O/E figures to {args.output}")


if __name__ == "__main__":
    main()
