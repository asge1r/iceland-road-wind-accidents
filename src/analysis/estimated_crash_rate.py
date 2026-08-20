"""Estimate rural injury-accident rates by wind interval and annual traffic."""

from __future__ import annotations

import argparse
import calendar
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PANEL = Path("data/processed/traffic/road_section_wind_panel_2007_2025.parquet")
ACCIDENTS = Path("data/processed/accidents/rate_accidents_weather.parquet")
OUTPUT = Path("reports/working/tables/estimated_crash_rate_by_wind.csv")
AUDIT = Path("reports/working/tables/estimated_crash_rate_by_wind_audit.csv")
FIGURE = Path("reports/working/figures/estimated_crash_rate_by_wind.png")

PERIOD_BY_MONTH = {
    1: "VDU", 2: "VDU", 3: "VDU", 4: "VHDU", 5: "VHDU", 6: "SDU",
    7: "SDU", 8: "SDU", 9: "SDU", 10: "VHDU", 11: "VHDU", 12: "VDU",
}
MONTHS_BY_PERIOD = {
    "VDU": [12, 1, 2, 3],
    "SDU": [6, 7, 8, 9],
    "VHDU": [4, 5, 10, 11],
}


def normalize_section(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.lower()


def days_in_period(year: int, period: str) -> int:
    return sum(calendar.monthrange(int(year), month)[1] for month in MONTHS_BY_PERIOD[period])


def load_panel(path: Path, variable: str) -> pd.DataFrame:
    columns = [
        "year", "road_section", "traffic_period", "weather_station_id", "variable",
        "bin_label", "bin_lower_ms", "frequency_pct", "wind_frequency_available",
        "section_length_km", "traffic_reference_daily_volume",
    ]
    panel = pd.read_parquet(path, columns=columns)
    panel = panel[
        panel["variable"].eq(variable)
        & panel["wind_frequency_available"].fillna(False)
        & panel["weather_station_id"].notna()
        & panel["section_length_km"].gt(0)
        & panel["traffic_reference_daily_volume"].gt(0)
        & panel["frequency_pct"].notna()
    ].copy()
    panel["road_section"] = normalize_section(panel["road_section"])
    keys = ["year", "road_section", "traffic_period", "weather_station_id", "bin_label"]
    if panel.duplicated(keys).any():
        raise ValueError("Road-section wind panel has duplicate exposure rows")
    panel["period_days"] = [
        days_in_period(year, period)
        for year, period in zip(panel["year"], panel["traffic_period"], strict=True)
    ]
    panel["estimated_vehicle_km"] = (
        panel["traffic_reference_daily_volume"]
        * panel["section_length_km"]
        * panel["period_days"]
        * panel["frequency_pct"]
        / 100
    )
    panel["positive_exposure"] = panel["estimated_vehicle_km"].gt(0)
    return panel


def load_accidents(path: Path, panel: pd.DataFrame, variable: str) -> tuple[pd.DataFrame, dict[str, int]]:
    columns = [
        "nid", "timestamp", "year", "road_section", "traffic_period",
        "rate_weather_station_id", "weather_time_difference_minutes",
        "rate_station_accident_distance_km", "f", "fg",
        "vehicle_group",
    ]
    accidents = pd.read_parquet(path, columns=columns)
    accidents["road_section"] = normalize_section(accidents["road_section"])
    valid = (
        accidents["weather_time_difference_minutes"].le(5)
        & accidents["rate_station_accident_distance_km"].le(20)
        & accidents["f"].between(0, 45, inclusive="left")
        & accidents["fg"].between(0, 65, inclusive="left")
        & accidents["fg"].add(0.5).ge(accidents["f"])
    )
    accidents = accidents[valid].copy()
    station_panel = panel[
        ["year", "road_section", "traffic_period", "weather_station_id"]
    ].drop_duplicates()
    matched = accidents.merge(
        station_panel,
        on=["year", "road_section", "traffic_period"],
        how="inner",
        suffixes=("_accident", "_section"),
        validate="many_to_one",
    )
    same_station = matched["rate_weather_station_id"].eq(
        matched["weather_station_id"]
    )
    if not same_station.all():
        raise ValueError("Rate accidents and exposure panel do not use the same weather station")
    wind_column = "f" if variable == "f_5m" else variable
    matched["wind_value"] = matched[wind_column]
    return matched, {
        "rate_accidents_input": int(len(pd.read_parquet(path, columns=["nid"]))),
        "rate_accidents_with_clean_shared_station_wind": int(valid.sum()),
        "rate_accidents_on_annual_traffic_and_weather_coverage": int(len(matched)),
        "shared_station_match_pct": round(100 * same_station.mean(), 1),
        "road_section_periods_with_accidents": int(
            matched[["year", "road_section", "traffic_period"]].drop_duplicates().shape[0]
        ),
    }


def calculate(panel: pd.DataFrame, accidents: pd.DataFrame) -> pd.DataFrame:
    labels = (
        panel[["bin_label", "bin_lower_ms"]]
        .drop_duplicates()
        .sort_values("bin_lower_ms")
    )
    labels_list = labels["bin_label"].tolist()
    edges = np.r_[labels["bin_lower_ms"].to_numpy(float), np.inf]
    accidents = accidents.copy()
    accidents["wind_bin"] = pd.cut(
        accidents["wind_value"], bins=edges, labels=labels_list, right=False, include_lowest=True
    )
    observed = (
        accidents.groupby("wind_bin", as_index=False, observed=False)["nid"].nunique()
        .rename(columns={"wind_bin": "bin_label", "nid": "observed_accidents"})
    )
    exposure = (
        panel.groupby("bin_label", as_index=False, observed=False)
        .agg(
            estimated_vehicle_km=("estimated_vehicle_km", "sum"),
            road_section_periods_with_nonzero_exposure=("positive_exposure", "sum"),
        )
    )
    result = labels.merge(exposure, on="bin_label", how="left").merge(
        observed, on="bin_label", how="left"
    )
    result["observed_accidents"] = result["observed_accidents"].fillna(0).astype(int)
    total_accidents = result["observed_accidents"].sum()
    result["rate_per_100m_vehicle_km"] = (
        result["observed_accidents"] / result["estimated_vehicle_km"] * 100_000_000
    )
    baseline_rate = result.loc[result["bin_lower_ms"].eq(0), "rate_per_100m_vehicle_km"].iloc[0]
    result["rate_ratio_vs_0_5_ms"] = result["rate_per_100m_vehicle_km"] / baseline_rate
    result["analysis_population"] = total_accidents
    return result


def plot(result: pd.DataFrame, path: Path) -> None:
    x = np.arange(len(result))
    fig, axis = plt.subplots(figsize=(11.4, 6.6))
    rate = result["rate_per_100m_vehicle_km"].to_numpy(float)
    bars = axis.bar(x, rate, color="#C7522A", width=0.72)
    axis.set_xticks(x, result["bin_label"].str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Mean wind-speed interval, f (m/s)")
    axis.set_ylabel("Estimated injury accidents per 100 million vehicle-km")
    axis.set_title("Estimated rural injury-accident rate by mean wind speed")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    ymax = max(1.0, float(rate.max()) * 1.22)
    axis.set_ylim(0, ymax)
    for bar, row in zip(bars, result.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            max(bar.get_height() * 0.52, ymax * 0.06),
            f"n={row.observed_accidents}",
            ha="center",
            va="center",
            fontsize=9,
            color="white",
        )
    fig.text(0.5, 0.02, "Vehicle-km use ADU, SDU, VDU and derived VHDU. Within each period, traffic is allocated across wind intervals according to local wind frequency.", ha="center", fontsize=8.2, color="#444444")
    fig.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.20)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-v", "--variable", choices=["f", "f_5m", "fg"], default="f_5m")
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-u", "--audit", type=Path, default=AUDIT)
    parser.add_argument("-f", "--figure", type=Path, default=FIGURE)
    args = parser.parse_args()
    panel = load_panel(args.panel, args.variable)
    accidents, audit = load_accidents(args.accidents, panel, args.variable)
    result = calculate(panel, accidents)
    audit.update(
        {
            "road_section_year_periods_with_annual_traffic_and_wind": int(
                panel[["year", "road_section", "traffic_period"]].drop_duplicates().shape[0]
            ),
            "estimated_vehicle_km_all_wind_intervals": round(
                float(result["estimated_vehicle_km"].sum()), 1
            ),
        }
    )
    for path in [args.output, args.audit, args.figure]:
        path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    pd.DataFrame([{"metric": key, "value": value} for key, value in audit.items()]).to_csv(args.audit, index=False)
    plot(result, args.figure)
    print(result.to_string(index=False))
    print(pd.DataFrame([audit]).to_string(index=False))


if __name__ == "__main__":
    main()
