"""Redraw core thesis results from the small Git-tracked replication bundle."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analysis.build_daily_traffic_wind_analysis import plot_results
from src.figures.create_crosswind_figure import create_figure


INPUT = Path("data/replication/tables")
OUTPUT = Path("reports/reproduced/figures")


def main() -> None:
    required = ["gust_risk.csv", "daily_traffic_wind.csv", "crosswind.csv"]
    missing = [name for name in required if not (INPUT / name).exists()]
    if missing:
        raise FileNotFoundError(f"Replication bundle is incomplete: {', '.join(missing)}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    daily = pd.read_csv(INPUT / "daily_traffic_wind.csv")
    plot_results(
        daily[daily["scope"].eq("All periods")],
        OUTPUT / "daily_traffic_wind.png",
        "All periods",
        "Daily traffic relative to expected traffic by mean wind speed",
    )
    create_figure(pd.read_csv(INPUT / "crosswind.csv"), OUTPUT / "crosswind.png")
    # The exact published gust figure is included in data/replication/figures.
    # Its table is copied alongside it for inspection and independent checking.
    print(f"Wrote core reproduced figures to {OUTPUT}")


if __name__ == "__main__":
    main()
