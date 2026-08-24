"""Create the daily-counter to weather-station distance quality-control figure.

Each physical traffic counter contributes one value: the median distance to the
weather station assigned on its valid daily traffic records.  This prevents a
counter with many available calendar days from dominating the distribution.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT = Path("data/analysis/daily_traffic.csv")
TABLE = Path("reports/working/tables/counter_weather_distance.csv")
FIGURE = Path("reports/working/figures/counter_weather_distance.png")

BIN_EDGES = list(range(0, 22, 2))
BIN_LABELS = [f"{lower}–<{upper}" for lower, upper in zip(BIN_EDGES[:-2], BIN_EDGES[1:-1], strict=True)] + ["18–20"]


def prepare_counter_distances(path: Path) -> tuple[pd.DataFrame, int]:
    """Return the representative weather-match distance for each counter."""
    data = pd.read_csv(path, usecols=["counter_id", "weather_station_dist_km"])
    data = data.rename(columns={"counter_id": "counter_site_id"})
    total_counters = data["counter_site_id"].nunique()
    data["weather_station_dist_km"] = pd.to_numeric(
        data["weather_station_dist_km"], errors="coerce"
    )
    data = data[data["weather_station_dist_km"].between(0, 20, inclusive="both")]
    distances = (
        data.groupby("counter_site_id", as_index=False)["weather_station_dist_km"]
        .median()
        .rename(columns={"weather_station_dist_km": "median_weather_station_distance_km"})
    )
    if distances.empty:
        raise ValueError("No daily counters have a valid weather-station distance")
    return distances, total_counters


def summarise(distances: pd.DataFrame) -> pd.DataFrame:
    """Create a compact binned table for the figure and thesis documentation."""
    bins = pd.cut(
        distances["median_weather_station_distance_km"],
        bins=BIN_EDGES,
        labels=BIN_LABELS,
        right=False,
        include_lowest=True,
    )
    summary = bins.value_counts(sort=False).rename_axis("distance_bin_km").reset_index(name="counters")
    summary["counter_pct"] = 100 * summary["counters"] / len(distances)
    return summary


def plot(summary: pd.DataFrame, distances: pd.DataFrame, total_counters: int, path: Path) -> None:
    """Plot the counter-weighted distribution of weather-match distance."""
    fig, axis = plt.subplots(figsize=(9.4, 5.8))
    x = np.arange(len(summary))
    bars = axis.bar(x, summary["counters"], width=0.72, color="#287271")
    axis.set_xticks(x, summary["distance_bin_km"])
    axis.set_xlabel("Distance from traffic counter to assigned weather station (km)")
    axis.set_ylabel("Traffic counters")
    axis.set_title("Distance from daily traffic counters to assigned weather stations")
    axis.grid(axis="y", alpha=0.22)
    axis.set_axisbelow(True)
    for bar, count in zip(bars, summary["counters"], strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f"n={count}", ha="center", va="bottom", fontsize=9)
    axis.set_ylim(0, max(summary["counters"]) * 1.18)
    median = distances["median_weather_station_distance_km"].median()
    p95 = distances["median_weather_station_distance_km"].quantile(0.95)
    fig.subplots_adjust(left=0.11, right=0.98, top=0.90, bottom=0.22)
    fig.text(
        0.5, 0.045,
        f"Of {total_counters:,} daily counters, {len(distances):,} have a usable weather match. One value per matched counter: median assigned-station distance.\n"
        f"Median = {median:.1f} km; 95th percentile = {p95:.1f} km.",
        ha="center", fontsize=8.5, color="#444444",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot daily counter-to-weather-station distances.")
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-t", "--table", type=Path, default=TABLE)
    parser.add_argument("-o", "--output", "--figure", dest="figure", type=Path, default=FIGURE)
    args = parser.parse_args()

    distances, total_counters = prepare_counter_distances(args.input)
    summary = summarise(distances)
    args.table.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.table, index=False)
    plot(summary, distances, total_counters, args.figure)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
