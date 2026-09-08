"""Draw the traffic-adjusted temperature rate-ratio figure."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.common import interval_labels


INPUT = Path("reports/main/tables/temperature_rate.csv")
OUTPUT = Path("reports/main/figures/temperature_rate.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {
        "bin_label", "observed_accidents", "time_proportional_rate_ratio",
        "time_proportional_ci_95_low", "time_proportional_ci_95_high",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"Temperature-rate table is missing columns: {sorted(missing)}")
    values = data["time_proportional_rate_ratio"].to_numpy(float)
    low = data["time_proportional_ci_95_low"].fillna(
        data["time_proportional_rate_ratio"]
    ).to_numpy(float)
    high = data["time_proportional_ci_95_high"].fillna(
        data["time_proportional_rate_ratio"]
    ).to_numpy(float)
    x = np.arange(len(data))
    figure, axis = plt.subplots(figsize=(11.4, 6.6), constrained_layout=True)
    bars = axis.bar(x, values, width=0.72, color="#287271")
    axis.errorbar(
        x, values, yerr=np.vstack([values - low, high - values]),
        fmt="none", ecolor="#202020", capsize=4,
    )
    axis.axhline(1, color="#202020", linestyle="--", linewidth=1.1)
    axis.set_xticks(x, interval_labels(data["bin_label"]))
    axis.set_xlabel("Temperature interval (°C)")
    axis.set_ylabel("Within-stratum rate ratio versus 0 to 3°C")
    axis.set_title("Estimated rural injury-accident rate ratio by temperature")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    top = max(1.2, float(high.max()) * 1.08)
    axis.set_ylim(0, top)
    for bar, row in zip(bars, data.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            max(bar.get_height() * 0.5, top * 0.06),
            f"n={row.observed_accidents}", ha="center", va="center",
            fontsize=8.5, color="white",
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
