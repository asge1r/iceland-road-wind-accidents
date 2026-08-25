"""Draw daily-traffic response figures from completed result tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.tables.daily_traffic import PERIOD_ORDER


DEFAULT_INPUT = Path("reports/main/tables/daily_traffic_by_wind.csv")
DEFAULT_MAIN = Path("reports/main/figures/daily_traffic_by_wind.png")
DEFAULT_PERIOD = Path("reports/working/figures/daily_traffic_by_period.png")


def plot_results(results: pd.DataFrame, path: Path, scope: str, title: str) -> None:
    data = results[results["scope"].eq(scope)].copy()
    x = np.arange(len(data))
    sparse = data["counters"].lt(20)
    values = data["relative_traffic_pct"].to_numpy(float)
    figure, axis = plt.subplots(figsize=(11.4, 6.6))
    bars = axis.bar(x, values, width=0.72, color=np.where(sparse, "#A8A8A8", "#287271"))
    axis.axhline(100, color="#202020", linestyle="--", linewidth=1.2)
    display_bins = data["f_bin"].astype("string").str.replace(">=", "≥", regex=False)
    axis.set_xticks(x, display_bins, rotation=0)
    axis.set_xlabel("Daytime mean wind speed, 10:00–21:59 (m/s)")
    axis.set_ylabel("Daily traffic relative to expected (%)")
    axis.set_title(title)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    ymax = max(110, float(data["relative_traffic_pct"].max()) * 1.08)
    axis.set_ylim(0, ymax)
    for bar, row in zip(bars, data.itertuples(index=False), strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2, max(4, row.relative_traffic_pct - 3), f"n={row.counter_days:,}", ha="center", va="top", fontsize=8.1, color="white", fontweight="bold")
    figure.subplots_adjust(left=0.11, right=0.98, top=0.91, bottom=0.24)
    figure.text(0.5, 0.035, "Expected daily traffic: mean for the same counter, year, month, and weekday. Wind is the mean from 10:00 to 21:59.", ha="center", fontsize=8.3, color="#444444")
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=240)
    plt.close(figure)


def plot_period_results(results: pd.DataFrame, path: Path) -> None:
    figure, axes = plt.subplots(3, 1, figsize=(11.4, 12.6), sharex=True)
    ymax = max(112, float(results["relative_traffic_ci_95_high_pct"].max()) * 1.12)
    titles = {"VDU": "Winter daily traffic (VDU: December–March)", "SDU": "Summer daily traffic (SDU: June–September)", "VHDU": "Spring/autumn traffic (VHDU: April–May, October–November)"}
    for axis, period in zip(axes, PERIOD_ORDER, strict=True):
        data = results[results["scope"].eq(period)]
        x = np.arange(len(data))
        bars = axis.bar(x, data["relative_traffic_pct"].to_numpy(float), width=0.72, color=np.where(data["counters"].lt(20), "#A8A8A8", "#287271"))
        axis.axhline(100, color="#202020", linestyle="--", linewidth=1.1)
        axis.set_title(titles[period], fontsize=11)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
        axis.set_ylim(0, ymax)
        for bar, row in zip(bars, data.itertuples(index=False), strict=True):
            axis.text(bar.get_x() + bar.get_width() / 2, min(ymax - 2, row.relative_traffic_pct + 1.2), f"n={row.counter_days:,}", ha="center", va="bottom", fontsize=7.5)
    axes[-1].set_xticks(np.arange(len(data)), data["f_bin"], rotation=0)
    axes[-1].set_xlabel("Daytime mean wind speed, 10:00–21:59 (m/s)")
    figure.supylabel("Daily traffic relative to expected (%)")
    figure.text(0.5, 0.012, "Expected traffic is standardized within counter, year, month, and weekday. Grey bars have fewer than 20 counters.", ha="center", fontsize=8.3, color="#444444")
    figure.tight_layout(rect=(0.03, 0.04, 1, 0.99))
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=240)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("-p", "--period-output", type=Path, default=DEFAULT_PERIOD)
    args = parser.parse_args()

    results = pd.read_csv(args.input)
    for path in [args.output, args.period_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    plot_results(
        results,
        args.output,
        "All periods",
        "Daily traffic relative to expected traffic by mean wind speed",
    )
    plot_period_results(results, args.period_output)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
