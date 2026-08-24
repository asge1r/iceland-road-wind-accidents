"""Write rural injury-accident rate tables from the compact traffic CSV summary."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT = Path("data/analysis/traffic_rate_summary.csv")
OUTPUT = Path("reports/working/tables/estimated_crash_rate_by_wind.csv")
AUDIT = Path("reports/working/tables/estimated_crash_rate_by_wind_audit.csv")


def select_periods(data: pd.DataFrame, traffic_period: str) -> pd.DataFrame:
    if traffic_period == "all":
        return data.copy()
    if traffic_period == "official":
        return data[data["traffic_period"].isin(["VDU", "SDU"])].copy()
    return data[data["traffic_period"].eq(traffic_period.upper())].copy()


def calculate(data: pd.DataFrame) -> pd.DataFrame:
    result = data.groupby(["wind_bin", "wind_bin_lower_ms"], as_index=False).agg(
        estimated_vehicle_km=("estimated_vehicle_km", "sum"),
        observed_accidents=("injury_accidents", "sum"),
    ).sort_values("wind_bin_lower_ms")
    result["rate_per_100m_vehicle_km"] = (
        result["observed_accidents"] / result["estimated_vehicle_km"] * 100_000_000
    )
    baseline = result.loc[
        result["wind_bin_lower_ms"].eq(result["wind_bin_lower_ms"].min()),
        "rate_per_100m_vehicle_km",
    ].iloc[0]
    result["rate_ratio_vs_0_5_ms"] = result["rate_per_100m_vehicle_km"] / baseline
    return result


def plot(result: pd.DataFrame, path: Path) -> None:
    x = np.arange(len(result))
    rate = result["rate_per_100m_vehicle_km"].to_numpy(float)
    figure, axis = plt.subplots(figsize=(11.4, 6.6))
    bars = axis.bar(x, rate, color="#C7522A", width=0.72)
    axis.set_xticks(x, result["wind_bin"].str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Mean wind-speed interval, f (m/s)")
    axis.set_ylabel("Estimated injury accidents per 100 million vehicle-km")
    axis.set_title("Estimated rural injury-accident rate by mean wind speed")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    top = max(1.0, float(rate.max()) * 1.22)
    axis.set_ylim(0, top)
    for bar, row in zip(bars, result.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            max(bar.get_height() * 0.52, top * 0.06),
            f"n={row.observed_accidents}",
            ha="center", va="center", fontsize=9, color="white",
        )
    figure.text(
        0.5, 0.02,
        "Annual road traffic is allocated across wind intervals according to local wind frequency.",
        ha="center", fontsize=8.2, color="#444444",
    )
    figure.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.20)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=240)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument(
        "-t", "--traffic-period", choices=["all", "official", "vdu", "sdu", "vhdu"], default="all",
    )
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-a", "--audit", type=Path, default=AUDIT)
    args = parser.parse_args()
    source = pd.read_csv(args.input)
    required = {"traffic_period", "wind_bin", "wind_bin_lower_ms", "estimated_vehicle_km", "injury_accidents"}
    missing = required - set(source.columns)
    if missing:
        raise ValueError(f"Traffic-rate summary is missing columns: {sorted(missing)}")
    result = calculate(select_periods(source, args.traffic_period))
    result["analysis_traffic_period"] = args.traffic_period
    audit = pd.DataFrame([{
        "traffic_period": args.traffic_period,
        "observed_accidents": int(result["observed_accidents"].sum()),
        "estimated_vehicle_km": float(result["estimated_vehicle_km"].sum()),
    }])
    for path in [args.output, args.audit]:
        path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    audit.to_csv(args.audit, index=False)
    print(result.to_string(index=False))
    print(audit.to_string(index=False))


if __name__ == "__main__":
    main()
