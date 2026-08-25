"""Draw daily-traffic quality-control figures from completed tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_SUMMARY = Path("reports/working/tables/daily_traffic_diagnostic.csv")
DEFAULT_VALIDATION = Path("archive/generated_diagnostics/daily_traffic_adu_validation.csv")
DEFAULT_ADU_FIGURE = Path("reports/working/traffic_validation.png")
DEFAULT_FIGURE = Path("reports/working/daily_traffic_diagnostic.png")


def plot_wind_summary(summary: pd.DataFrame, path: Path) -> None:
    data = summary[summary["variable"].eq("f_daytime_mean")].sort_values("bin_order")
    x = np.arange(len(data))
    figure, axis = plt.subplots(figsize=(11.2, 6.6))
    bars = axis.bar(x, data["traffic_index_median"], color=np.where(data["counters"].fillna(0).lt(20), "#A8A8A8", "#287271"), width=0.72)
    axis.errorbar(x, data["traffic_index_median"], yerr=[data["traffic_index_median"] - data["ci_95_low"], data["ci_95_high"] - data["traffic_index_median"]], fmt="none", ecolor="#202020", capsize=3)
    axis.axhline(100, color="#202020", linestyle="--", linewidth=1.2)
    axis.set_xticks(x, data["bin"], rotation=0, ha="center")
    axis.set_ylabel("Vehicles counted relative to a typical day (%)")
    axis.set_xlabel("Daytime mean wind speed, 10:00–21:59 (m/s)")
    axis.set_title("Daily traffic by mean wind speed")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    axis.set_ylim(0, max(112, float(data["ci_95_high"].max()) + 8))
    for bar, row in zip(bars, data.itertuples(index=False), strict=True):
        if not pd.isna(row.traffic_index_median):
            axis.text(bar.get_x() + bar.get_width() / 2, row.traffic_index_median + 1.5, f"n={row.counter_days:,}", ha="center", va="bottom", fontsize=8.5)
    figure.subplots_adjust(left=0.10, right=0.98, top=0.92, bottom=0.24)
    figure.text(0.5, 0.035, "Baseline: median for the same counter, year, month, and weekday. Bars show the median across counters; error bars are 95% counter-cluster bootstrap intervals.", ha="center", fontsize=8.5, color="#444444")
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=240)
    plt.close(figure)


def plot_adu_validation(validation: pd.DataFrame, path: Path) -> None:
    data = validation[validation["adu"].gt(0) & validation["observed_daily_mean"].gt(0) & validation["near_complete_year"] & validation["single_counter_section"]].copy()
    figure, axis = plt.subplots(figsize=(9, 7.5), constrained_layout=True)
    axis.scatter(data["adu"], data["observed_daily_mean"], color="#287271", alpha=0.55, s=24)
    low = min(data["adu"].min(), data["observed_daily_mean"].min())
    high = max(data["adu"].max(), data["observed_daily_mean"].max())
    axis.plot([low, high], [low, high], color="#202020", linestyle="--", linewidth=1)
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("Annual average daily traffic, ADU")
    axis.set_ylabel("Mean observed daily PDF traffic")
    axis.set_title("Daily traffic compared with official ADU")
    axis.grid(alpha=0.2)
    axis.text(0.02, 0.98, f"At least 300 observed days; one counter per road section\nn = {len(data):,} counter-years\nMedian observed / ADU = {data['mean_to_adu_ratio'].median():.3f}\nLog correlation = {np.log(data['adu']).corr(np.log(data['observed_daily_mean'])):.3f}\nDashed line: equal values", transform=axis.transAxes, va="top", fontsize=10)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=240)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-s", "--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("-v", "--adu-validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("-f", "--adu-figure", type=Path, default=DEFAULT_ADU_FIGURE)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_FIGURE)
    args = parser.parse_args()

    summary = pd.read_csv(args.summary)
    validation = pd.read_csv(args.adu_validation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.adu_figure.parent.mkdir(parents=True, exist_ok=True)
    plot_wind_summary(summary, args.output)
    plot_adu_validation(validation, args.adu_figure)
    print(f"wrote={args.output}")
    print(f"wrote={args.adu_figure}")


if __name__ == "__main__":
    main()
