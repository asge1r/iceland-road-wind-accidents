"""Map study accidents and accidents occurring in strong mean wind."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ACCIDENTS = Path("data/analysis/accidents.csv")
CONDITIONS = Path("data/analysis/accident_conditions.csv")
OUTPUT = Path("reports/main/figures/accident_map.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-c", "--conditions", type=Path, default=CONDITIONS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    accidents = pd.read_csv(args.accidents, usecols=["id", "lon", "lat"])
    conditions = pd.read_csv(
        args.conditions,
        usecols=["id", "f", "weather_station_dist_km", "weather_time_difference_minutes"],
    )
    data = accidents.merge(conditions, on="id", validate="one_to_one")
    strong = (
        data["f"].ge(15)
        & data["weather_station_dist_km"].le(20)
        & data["weather_time_difference_minutes"].le(5)
    )
    figure, axis = plt.subplots(figsize=(9.5, 7.5), constrained_layout=True)
    axis.scatter(
        data.loc[~strong, "lon"], data.loc[~strong, "lat"],
        s=8, color="#A5ADB3", alpha=0.42,
        label=f"Other rural injury accidents (n={(~strong).sum():,})",
    )
    axis.scatter(
        data.loc[strong, "lon"], data.loc[strong, "lat"],
        s=18, color="#B85C4A", alpha=0.85,
        label=f"Mean wind ≥15 m/s (n={strong.sum():,})",
    )
    axis.set_xlim(-25, -13)
    axis.set_ylim(63.2, 66.7)
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.set_title("Locations of rural injury accidents, 2007–2025")
    axis.grid(alpha=0.15)
    axis.legend(frameon=False, loc="lower left")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
