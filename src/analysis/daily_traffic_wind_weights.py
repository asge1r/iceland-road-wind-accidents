"""Estimate counter-informed traffic-allocation weights for 5 m/s wind bins."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT = Path("data/analysis/daily_traffic.csv")
OUTPUT = Path("reports/main/tables/daily_traffic_factor_by_wind.csv")
FIGURE = Path("reports/working/figures/daily_traffic_factor_by_wind.png")
LABELS = ["0-5", "5-10", "10-15", "15-20", "20-25", ">=25"]
EDGES = [0, 5, 10, 15, 20, 25, np.inf]


def load_data(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path, parse_dates=["date"])
    data = data[["date", "counter_site_id", "traffic_volume", "f_daytime_mean"]].copy()
    data["year"] = data["date"].dt.year
    data["month"] = data["date"].dt.month
    data["weekday"] = data["date"].dt.weekday
    data = data[
        data["traffic_volume"].gt(0)
        & data["f_daytime_mean"].between(0, 45, inclusive="left")
    ].copy()
    data["f_bin"] = pd.cut(
        data["f_daytime_mean"], bins=EDGES, labels=LABELS,
        right=False, include_lowest=True,
    )
    keys = ["counter_site_id", "year", "month", "weekday"]
    baseline = data.groupby(keys, as_index=False)["traffic_volume"].mean()
    baseline = baseline.rename(columns={"traffic_volume": "expected_daily_traffic"})
    data = data.merge(baseline, on=keys, how="left", validate="many_to_one")
    return data


def summarize(data: pd.DataFrame) -> pd.DataFrame:
    result = data.groupby("f_bin", as_index=False, observed=False).agg(
        counter_days=("date", "size"),
        counters=("counter_site_id", "nunique"),
        observed_daily_vehicles=("traffic_volume", "sum"),
        expected_daily_vehicles=("expected_daily_traffic", "sum"),
    )
    result["observed_to_expected_traffic"] = (
        result["observed_daily_vehicles"] / result["expected_daily_vehicles"]
    )
    baseline = result.loc[result["f_bin"].astype(str).eq("0-5"), "observed_to_expected_traffic"].iloc[0]
    result["traffic_response_factor"] = result["observed_to_expected_traffic"] / baseline
    return result


def plot(result: pd.DataFrame, path: Path) -> None:
    x = np.arange(len(result))
    values = 100 * result["traffic_response_factor"].to_numpy(float)
    fig, axis = plt.subplots(figsize=(10.6, 6.2))
    bars = axis.bar(x, values, color="#287271", width=0.72)
    axis.axhline(100, color="#202020", linestyle="--", linewidth=1.1)
    axis.set_xticks(x, result["f_bin"].astype(str).str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Daytime mean wind-speed interval (m/s)")
    axis.set_ylabel("Daily traffic relative to 0–5 m/s (%)")
    axis.set_title("Daily counter traffic by mean wind speed")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    axis.set_ylim(0, max(110, values.max() * 1.1))
    for bar, row in zip(bars, result.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            max(4, bar.get_height() * 0.52),
            f"n={row.counter_days:,}",
            ha="center", va="center", fontsize=8.5, color="white",
        )
    fig.text(
        0.5, 0.02,
        "Expected traffic is the mean for the same counter, year, month, and weekday. Wind is the mean from 10:00 to 21:59.",
        ha="center", fontsize=8.2, color="#444444",
    )
    fig.subplots_adjust(left=0.11, right=0.98, top=0.90, bottom=0.20)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-f", "--figure", type=Path, default=FIGURE)
    args = parser.parse_args()
    result = summarize(load_data(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    plot(result, args.figure)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
