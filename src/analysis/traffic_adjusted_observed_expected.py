"""Plot observed/expected injury accidents using estimated vehicle-km by wind bin."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.estimated_crash_rate import load_accidents, load_panel
from src.analysis.stratified_crash_rate import (
    add_counter_informed_exposure,
    analysis_bins,
    build_model_data,
)


PANEL = Path("data/processed/traffic/road_section_wind_panel_2007_2025.parquet")
ACCIDENTS = Path("data/processed/accidents/rate_accidents_weather.parquet")
TRAFFIC_WEIGHTS = Path("reports/main/tables/daily_traffic_factor_by_wind.csv")
OUTPUT = Path("reports/working/tables/traffic_adjusted_observed_expected_by_wind.csv")
FIGURE = Path("reports/working/figures/traffic_adjusted_observed_expected_by_wind.png")


def observed_expected(data: pd.DataFrame, exposure_column: str, prefix: str) -> pd.DataFrame:
    result = (
        data.groupby(["bin_label", "bin_lower_ms"], as_index=False, observed=False)
        .agg(
            observed_accidents=("observed_accidents", "sum"),
            estimated_vehicle_km=(exposure_column, "sum"),
        )
        .sort_values("bin_lower_ms")
    )
    total_accidents = result["observed_accidents"].sum()
    result[f"{prefix}_expected_accidents"] = (
        total_accidents * result["estimated_vehicle_km"] / result["estimated_vehicle_km"].sum()
    )
    result[f"{prefix}_oe"] = (
        result["observed_accidents"] / result[f"{prefix}_expected_accidents"]
    )
    return result.drop(columns=["estimated_vehicle_km"])


def plot(result: pd.DataFrame, path: Path) -> None:
    x = np.arange(len(result))
    fig, axis = plt.subplots(figsize=(11.4, 6.6))
    width = 0.34
    time_bars = axis.bar(
        x - width / 2, result["time_proportional_oe"], width=width,
        color="#6C757D", label="Annual traffic and local wind frequency",
    )
    counter_bars = axis.bar(
        x + width / 2, result["counter_informed_oe"], width=width,
        color="#C7522A", label="Allocation informed by daily counters",
    )
    axis.axhline(1, color="#202020", linestyle="--", linewidth=1.1)
    axis.set_xticks(x, result["bin_label"].str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Mean wind-speed interval, f (m/s)")
    axis.set_ylabel("Observed / expected injury accidents")
    axis.set_title("Traffic-adjusted observed/expected rural injury accidents")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    ymax = max(1.2, float(result[["time_proportional_oe", "counter_informed_oe"]].max().max()) * 1.24)
    axis.set_ylim(0, ymax)
    for bar, row in zip(counter_bars, result.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2, max(bar.get_height() * 0.45, ymax * 0.05),
            f"n={row.observed_accidents}", ha="center", va="center", fontsize=9, color="white",
        )
    axis.legend(frameon=False, ncols=2, loc="upper left")
    fig.text(
        0.5, 0.02,
        "Expected accidents are proportional to estimated vehicle-km. Daily-counter allocation uses 2019–2024 data.",
        ha="center", fontsize=8.2, color="#444444",
    )
    fig.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.20)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-w", "--traffic-weights", type=Path, default=TRAFFIC_WEIGHTS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-f", "--figure", type=Path, default=FIGURE)
    args = parser.parse_args()
    panel = load_panel(args.panel, "f_5m")
    accidents, audit = load_accidents(args.accidents, panel, "f_5m")
    data = build_model_data(panel, accidents, "all", "all")
    data = add_counter_informed_exposure(data, args.traffic_weights)
    bins = analysis_bins(panel)
    time_result = observed_expected(data, "estimated_vehicle_km", "time_proportional")
    counter_result = observed_expected(data, "counter_informed_vehicle_km", "counter_informed")
    result = bins.merge(time_result, on=["bin_label", "bin_lower_ms"], how="left").merge(
        counter_result.drop(columns=["observed_accidents"]), on=["bin_label", "bin_lower_ms"], how="left"
    )
    result["analysis_accidents"] = int(data["observed_accidents"].sum())
    result["daily_counter_period"] = "2019-2024"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    plot(result, args.figure)
    print(result.to_string(index=False))
    print(pd.DataFrame([audit]).to_string(index=False))


if __name__ == "__main__":
    main()
