"""Compare wind rate ratios for one- and multiple-vehicle accidents."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.common import interval_labels


ONE = Path("reports/main/tables/wind_rate_one.csv")
MULTIPLE = Path("reports/main/tables/wind_rate_multiple.csv")
OUTPUT = Path("reports/main/figures/wind_rate_vehicle.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-1", "--one-vehicle", type=Path, default=ONE)
    parser.add_argument("-2", "--multiple-vehicle", type=Path, default=MULTIPLE)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    tables = [pd.read_csv(args.one_vehicle), pd.read_csv(args.multiple_vehicle)]
    names = ["One-vehicle accidents", "Two or more vehicles"]
    upper = max(float(table["time_proportional_rate_ratio"].max()) for table in tables)
    figure, axes = plt.subplots(1, 2, figsize=(11.5, 5.8), sharey=True)
    for axis, data, name in zip(axes, tables, names, strict=True):
        required = {
            "bin_label", "observed_accidents", "time_proportional_rate_ratio",
            "time_proportional_ci_95_low", "time_proportional_ci_95_high",
        }
        missing = required - set(data)
        if missing:
            raise ValueError(f"Vehicle-rate table is missing columns: {sorted(missing)}")
        values = data["time_proportional_rate_ratio"].to_numpy(float)
        x = np.arange(len(data))
        bars = axis.bar(x, values, width=0.7, color="#287271")
        axis.axhline(1, color="#202020", linestyle="--", linewidth=1)
        axis.set_xticks(x, interval_labels(data["bin_label"]), rotation=30)
        axis.set_title(name)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
        axis.set_ylim(0, max(1.2, upper * 1.08))
        for bar, row in zip(bars, data.itertuples(index=False), strict=True):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() * 0.52,
                f"n={row.observed_accidents}", ha="center", va="center",
                fontsize=7.5, color="white",
            )
    figure.supylabel("Within-stratum rate ratio versus 0–5 m/s")
    figure.supxlabel("Mean wind-speed interval, f (m/s)")
    figure.suptitle("Estimated accident rate ratios by number of vehicles")
    figure.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
