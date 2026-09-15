"""Compare original and corrected All year O/E without refitting the analysis."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.oe_histo import VARIABLE_NAMES, X_LABELS, interval_label, plot_whole_year

INPUT = Path("reports/main/tables/weather_oe_traffic_corrected.csv")
OUTPUT = Path("reports/main/figures/weather_oe_traffic_corrected.png")


def plotting_table(data: pd.DataFrame) -> pd.DataFrame:
    """Retain the existing corrected O/E plotting interface."""
    columns = ["variable", "outcome", "period", "bin_label", "bin_order",
               "observed_accidents", "traffic_corrected_expected_accidents",
               "traffic_corrected_oe"]
    return data[columns].rename(columns={
        "traffic_corrected_expected_accidents": "expected_accidents",
        "traffic_corrected_oe": "relative_accident_frequency",
    })


def draw(axis, part: pd.DataFrame, variable: str) -> None:
    part = part.sort_values("bin_order")
    x = np.arange(len(part))
    axis.bar(x - .19, part.time_oe, width=.36, facecolor="white",
             edgecolor="#287271", linewidth=1.4, label="Original O/E", zorder=3)
    bars = axis.bar(x + .19, part.traffic_corrected_oe, width=.36,
                    color="#287271", label="Traffic-corrected O/E", zorder=3)
    maximum = max(part.time_oe.max(), part.traffic_corrected_oe.max())
    axis.set_ylim(0, maximum * 1.35)
    if variable in ("f", "fg"):
        row = part.iloc[-1]
        axis.text(.03, .9, f"{interval_label(row.bin_label)} m/s: "
                  f"{row.time_oe:.2f} → {row.traffic_corrected_oe:.2f}",
                  transform=axis.transAxes, fontsize=12)
    axis.set_title(VARIABLE_NAMES[variable], fontsize=15, loc="left")
    axis.text(1, 1.025, "All year", transform=axis.transAxes, ha="right", fontsize=12)
    axis.set_xticks(x, [interval_label(v, variable == "temperature") for v in part.bin_label])
    axis.set_xlabel(X_LABELS[variable], fontsize=13)
    axis.set_ylabel("Observed / expected accidents (O/E)", fontsize=12)
    axis.axhline(1, color="#B8B8B8", linewidth=1.5)
    axis.grid(axis="y", color="#E8E8E8")
    axis.set_axisbelow(True)
    axis.tick_params(labelsize=11)


def make_figure(data: pd.DataFrame, output: Path, variables: tuple[str, ...]) -> None:
    if set(data.period) != {"All year"}:
        raise ValueError("This figure requires the existing All year correction")
    selected = data[data.outcome.eq("All injury accidents")]
    if selected.duplicated(["variable", "bin_label"]).any():
        raise ValueError("Duplicate corrected O/E bins")
    fig, axes = plt.subplots(len(variables), 1, figsize=(10.5, 4.3 * len(variables)),
                             layout="constrained", squeeze=False)
    for axis, variable in zip(axes.flat, variables, strict=True):
        part = selected[selected.variable.eq(variable)]
        if part.empty:
            raise ValueError(f"No corrected result for {variable}")
        draw(axis, part, variable)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncols=2, frameon=False, fontsize=12)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("--split", action="store_true", help="Also write one figure per parameter")
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    variables = tuple(v for v in VARIABLE_NAMES if v in set(data.variable))
    source_scales = {"f": 6.0, "fg": 6.0, "temperature": 2.0} if "2019_2024" in args.input.stem else None
    plot_whole_year(plotting_table(data), args.output, "", variables=variables,
                    y_limits=source_scales,
                    y_steps={"f": 1.0, "fg": 1.0, "temperature": .2} if source_scales else None)
    if args.split or args.input == INPUT:
        for variable in variables:
            make_figure(data, args.output.with_name(f"{args.output.stem}_{variable}.png"), (variable,))
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
