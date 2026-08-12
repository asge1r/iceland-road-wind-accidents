"""Render the traffic-adjusted road-wind figure from compact analysis input."""

from pathlib import Path

import pandas as pd

from src.analysis.plots import plot_road_adjustment


INPUT = Path("data/analysis/road_wind.csv")
OUTPUT = Path("reports/main/figures/traffic_adjustment.png")


def main() -> None:
    data = pd.read_csv(INPUT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    plot_road_adjustment(data, OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
