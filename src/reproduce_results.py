"""Redraw core thesis results from the small Git-tracked replication bundle."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from src.analysis.build_daily_traffic_wind_analysis import plot_results
from src.figures.create_crosswind_figure import create_figure


INPUT = Path("data/replication/tables")
OUTPUT = Path("reports/reproduced/figures")
REFERENCE = Path("data/replication/figures")


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
    snapshot = OUTPUT.parent / "reference_snapshot"
    snapshot.mkdir(parents=True, exist_ok=True)
    for figure in REFERENCE.glob("*.png"):
        shutil.copy2(figure, snapshot / figure.name)
    # The snapshot contains every exact published figure. The two core figures
    # above are additionally redrawn from their tracked numerical tables.
    print(f"Wrote core reproduced figures to {OUTPUT}")
    print(f"Copied exact result snapshot to {snapshot}")


if __name__ == "__main__":
    main()
