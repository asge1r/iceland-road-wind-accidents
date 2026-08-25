"""Draw the descriptive accident-per-vehicle-kilometre figure."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DEFAULT_INPUT = Path("reports/working/tables/estimated_crash_rate_by_wind.csv")
DEFAULT_OUTPUT = Path("reports/working/figures/estimated_crash_rate_by_wind.png")


def plot(result: pd.DataFrame, path: Path) -> None:
    x = np.arange(len(result))
    rate = result["rate_per_100m_vehicle_km"].to_numpy(float)
    figure, axis = plt.subplots(figsize=(11.4, 6.6))
    bars = axis.bar(x, rate, color="#C7522A", width=0.72)
    axis.set_xticks(x, result["wind_bin"].str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Mean wind-speed interval, f (m/s)")
    axis.set_ylabel("Estimated injury accidents per 100 million vehicle-km")
    axis.set_title("Estimated rural injury-accident rate by mean wind speed")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    top = max(1.0, float(rate.max()) * 1.22)
    axis.set_ylim(0, top)
    for bar, row in zip(bars, result.itertuples(index=False), strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height() * 0.52, top * 0.06), f"n={row.observed_accidents}", ha="center", va="center", fontsize=9, color="white")
    figure.text(0.5, 0.02, "Annual road traffic is allocated across wind intervals according to local wind frequency.", ha="center", fontsize=8.2, color="#444444")
    figure.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.20)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=240)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    plot(pd.read_csv(args.input), args.output)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
