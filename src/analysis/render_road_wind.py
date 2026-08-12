"""Render the traffic-adjusted road-wind figure from compact analysis input."""

from pathlib import Path

import pandas as pd

from src.analysis.build_road_section_wind_table import plot_adjustment_comparison


INPUT = Path("data/analysis/road_wind.csv")
OUTPUT = Path("reports/main/figures/traffic_adjustment.png")


def main() -> None:
    data = pd.read_csv(INPUT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    plot_adjustment_comparison(data, OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
