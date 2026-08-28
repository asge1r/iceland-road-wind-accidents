"""Draw the coarse observed daily-counter accident-rate result."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.common import interval_labels


INPUT = Path("reports/main/tables/daily_counter_rate_ratio_coarse_by_wind.csv")
OUTPUT = Path("reports/main/figures/daily_counter_rate_ratio_coarse_by_wind.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    required = {"wind_bin", "observed_accidents", "rate_ratio", "ci_95_low", "ci_95_high"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Daily-counter rate table is missing columns: {sorted(missing)}")
    if data["wind_bin"].tolist() != ["0-10", "10-15", ">=15"]:
        raise ValueError("Daily-counter figure requires the documented coarse bins")

    x = np.arange(len(data))
    values = data["rate_ratio"].to_numpy(float)
    low = data["ci_95_low"].fillna(data["rate_ratio"]).to_numpy(float)
    high = data["ci_95_high"].fillna(data["rate_ratio"]).to_numpy(float)
    errors = np.vstack([values - low, high - values])
    figure, axis = plt.subplots(figsize=(9.4, 5.8), constrained_layout=True)
    bars = axis.bar(x, values, color="#287271", width=0.68)
    axis.errorbar(x, values, yerr=errors, fmt="none", ecolor="#202020", capsize=4)
    axis.axhline(1, color="#202020", linestyle="--", linewidth=1.1)
    axis.set_xticks(x, interval_labels(data["wind_bin"]))
    axis.set_xlabel("Full-day mean wind-speed interval, f (m/s)")
    axis.set_ylabel("Within-counter-year rate ratio versus 0–10 m/s")
    axis.set_title("Observed daily-counter accident-rate sensitivity, 2019–2024")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    top = float(high.max()) * 1.14
    axis.set_ylim(0, top)
    for bar, row in zip(bars, data.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            min(bar.get_height() * 0.52, top * 0.43),
            f"n={row.observed_accidents}",
            ha="center", va="center", fontsize=9, color="white",
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
