"""Compare wind-frequency O/E with annual-traffic-standardised O/E."""

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
ACCIDENTS = Path("data/processed/accidents/rural_injury_accidents.parquet")
OUTPUT = Path("reports/main/tables/traffic_adjusted_oe.csv")
AUDIT = Path("reports/working/tables/traffic_adjusted_oe_audit.csv")
FIGURE = Path("reports/main/figures/traffic_adjusted_oe.png")

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
    return panel


def load_accidents(path: Path, panel: pd.DataFrame, variable: str) -> tuple[pd.DataFrame, dict[str, int]]:
    columns = [
        "nid", "timestamp", "registered_road_section", "weather_station_id",
        "weather_time_difference_minutes", "within_20km", "wind_available", "f", "fg",
    ]
    accidents = pd.read_parquet(path, columns=columns)
    timestamp = pd.to_datetime(accidents["timestamp"], errors="coerce")
    accidents["year"] = timestamp.dt.year
    accidents["traffic_period"] = timestamp.dt.month.map(PERIOD_BY_MONTH)
    accidents["road_section"] = normalize_section(accidents["registered_road_section"])
    valid = (
        accidents["within_20km"].fillna(False)
        & accidents["wind_available"].fillna(False)
        & accidents["weather_time_difference_minutes"].le(5)
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
    same_station = matched["weather_station_id_accident"].eq(
        matched["weather_station_id_section"]
    )
    matched = matched[same_station].copy()
    matched["wind_value"] = matched[variable]
    return matched, {
        "accidents_with_clean_primary_weather": int(valid.sum()),
        "accidents_on_covered_road_section_period": int(len(same_station)),
        "accidents_same_section_weather_station": int(same_station.sum()),
        "road_section_periods_with_accidents": int(
            matched[["year", "road_section", "traffic_period"]].drop_duplicates().shape[0]
        ),
    }


def calculate(panel: pd.DataFrame, accidents: pd.DataFrame) -> pd.DataFrame:
    key = ["year", "road_section", "traffic_period"]
    strata = accidents.groupby(key, as_index=False)["nid"].nunique().rename(
        columns={"nid": "stratum_accidents"}
    )
    panel = panel.merge(strata, on=key, how="inner", validate="many_to_one")
    labels = (
        panel[["bin_label", "bin_lower_ms"]]
        .drop_duplicates()
        .sort_values("bin_lower_ms")
    )
    labels_list = labels["bin_label"].tolist()
    panel["weather_expected_accidents"] = (
        panel["stratum_accidents"] * panel["frequency_pct"] / 100
    )
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
            weather_expected_accidents=("weather_expected_accidents", "sum"),
            estimated_vehicle_km=("estimated_vehicle_km", "sum"),
            road_section_periods=("estimated_vehicle_km", "count"),
        )
    )
    result = labels.merge(exposure, on="bin_label", how="left").merge(
        observed, on="bin_label", how="left"
    )
    result["observed_accidents"] = result["observed_accidents"].fillna(0).astype(int)
    total_accidents = result["observed_accidents"].sum()
    total_vehicle_km = result["estimated_vehicle_km"].sum()
    result["traffic_expected_accidents"] = (
        total_accidents * result["estimated_vehicle_km"] / total_vehicle_km
    )
    result["weather_only_oe"] = (
        result["observed_accidents"] / result["weather_expected_accidents"]
    )
    result["annual_traffic_adjusted_oe"] = (
        result["observed_accidents"] / result["traffic_expected_accidents"]
    )
    result["rate_per_100m_vehicle_km"] = (
        result["observed_accidents"] / result["estimated_vehicle_km"] * 100_000_000
    )
    result["analysis_population"] = total_accidents
    return result


def plot(result: pd.DataFrame, path: Path) -> None:
    x = np.arange(len(result))
    width = 0.38
    fig, axis = plt.subplots(figsize=(11.4, 6.6))
    axis.bar(x - width / 2, result["weather_only_oe"], width, color="#287271", label="Weather frequency only")
    axis.bar(x + width / 2, result["annual_traffic_adjusted_oe"], width, color="#C7522A", label="Weather frequency and annual traffic")
    axis.axhline(1, color="#202020", linestyle="--", linewidth=1.1)
    axis.set_xticks(x, result["bin_label"].str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Mean wind-speed interval, f (m/s)")
    axis.set_ylabel("Observed / expected injury accidents")
    axis.set_title("Road-section accident occurrence by mean wind speed")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    ymax = max(1.25, float(result[["weather_only_oe", "annual_traffic_adjusted_oe"]].max().max()) * 1.22)
    axis.set_ylim(0, ymax)
    for xpos, row in zip(x, result.itertuples(index=False), strict=True):
        axis.text(xpos, min(ymax - 0.05, max(row.weather_only_oe, row.annual_traffic_adjusted_oe) + 0.08), f"n={row.observed_accidents}", ha="center", va="bottom", fontsize=8.5)
    axis.legend(frameon=False, loc="upper left")
    fig.text(0.5, 0.02, "Annual traffic exposure uses ADU, SDU, VDU and a derived April-May/October-November value; traffic is allocated across wind intervals by local wind frequency.", ha="center", fontsize=8.2, color="#444444")
    fig.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.20)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-v", "--variable", choices=["f", "fg"], default="f")
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-u", "--audit", type=Path, default=AUDIT)
    parser.add_argument("-f", "--figure", type=Path, default=FIGURE)
    args = parser.parse_args()
    panel = load_panel(args.panel, args.variable)
    accidents, audit = load_accidents(args.accidents, panel, args.variable)
    result = calculate(panel, accidents)
    for path in [args.output, args.audit, args.figure]:
        path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    pd.DataFrame([{"metric": key, "value": value} for key, value in audit.items()]).to_csv(args.audit, index=False)
    plot(result, args.figure)
    print(result.to_string(index=False))
    print(pd.DataFrame([audit]).to_string(index=False))


if __name__ == "__main__":
    main()
