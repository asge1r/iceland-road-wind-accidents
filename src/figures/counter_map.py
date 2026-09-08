"""Map daily counters and accidents retained or excluded by their coverage."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


INPUT = Path("reports/main/tables/daily_map.csv")
OUTPUT = Path("reports/main/figures/counter_coverage.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {"point_type", "group", "lon", "lat"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Daily-map table is missing columns: {sorted(missing)}")
    styles = {
        "No exact counter link": ("#B9BEC2", 10, 0.5, "o"),
        "Exact link, not retained": ("#D9A441", 13, 0.7, "o"),
        "Allocated-rate sample": ("#287271", 15, 0.72, "o"),
        "Located daily counter": ("#202020", 18, 0.8, "x"),
    }
    figure, axis = plt.subplots(figsize=(9.5, 7.5), constrained_layout=True)
    for group, (colour, size, alpha, marker) in styles.items():
        subset = data[data["group"].eq(group)]
        axis.scatter(
            subset["lon"], subset["lat"], s=size, color=colour, alpha=alpha,
            marker=marker, linewidths=0.7,
            label=f"{group} (n={len(subset):,})",
        )
    axis.set_xlim(-25, -13)
    axis.set_ylim(63.2, 66.7)
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.set_title("Daily-counter coverage of rural injury accidents, 2019–2024")
    axis.grid(alpha=0.15)
    axis.legend(frameon=False, loc="lower left", fontsize=8.5)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
