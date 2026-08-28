"""Draw a stratified accident-rate figure from its completed result table."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.common import interval_labels

DEFAULT_INPUT = Path("reports/main/tables/conditional_poisson_rate_ratio_by_wind.csv")
DEFAULT_OUTPUT = Path("reports/main/figures/conditional_poisson_rate_ratio_by_wind.png")


def title(data: pd.DataFrame) -> str:
    period = str(data["analysis_traffic_period"].iloc[0])
    vehicle = str(data["analysis_vehicle_group"].iloc[0])
    scope: list[str] = []
    if period == "official":
        scope.append("official VDU + SDU periods")
    elif period != "all":
        scope.append(period.upper())
    if vehicle != "all":
        scope.append("one vehicle" if vehicle == "one" else "two or more vehicles")
    suffix = "" if not scope else " (" + ", ".join(scope) + ")"
    return "Estimated rural injury-accident rate ratio by mean wind speed" + suffix


def plot(result: pd.DataFrame, path: Path, figure_title: str) -> None:
    x = np.arange(len(result))
    values = result["time_proportional_rate_ratio"].to_numpy(float)
    figure, axis = plt.subplots(figsize=(11.4, 6.6), constrained_layout=True)
    bars = axis.bar(x, values, color="#287271", width=0.72)
    axis.axhline(1, color="#202020", linestyle="--", linewidth=1.1)
    axis.set_xticks(x, interval_labels(result["bin_label"]))
    axis.set_xlabel("Mean wind-speed interval, f (m/s)")
    axis.set_ylabel("Within-stratum rate ratio versus 0–5 m/s")
    axis.set_title(figure_title)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    top = max(1.2, float(values.max()) * 1.22)
    axis.set_ylim(0, top)
    for bar, row in zip(bars, result.itertuples(index=False), strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height() * 0.5, top * 0.06), f"n={row.observed_accidents}", ha="center", va="center", fontsize=9, color="white")
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=240)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    plot(data, args.output, title(data))
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
