"""Estimate within-road-section accident-rate ratios by mean wind speed."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.discrete.conditional_models import ConditionalPoisson

from src.analysis.estimated_crash_rate import load_accidents, load_panel


PANEL = Path("data/processed/traffic/road_section_wind_panel_2007_2025.parquet")
ACCIDENTS = Path("data/processed/accidents/rate_accidents_weather.parquet")
TRAFFIC_WEIGHTS = Path("reports/main/tables/daily_traffic_factor_by_wind.csv")
OUTPUT = Path("reports/main/tables/stratified_crash_rate_ratio_by_wind.csv")
FIGURE = Path("reports/main/figures/stratified_crash_rate_ratio_by_wind.png")


def analysis_bins(panel: pd.DataFrame) -> pd.DataFrame:
    return (
        panel[["bin_label", "bin_lower_ms"]]
        .drop_duplicates()
        .sort_values("bin_lower_ms")
        .reset_index(drop=True)
    )


def build_model_data(
    panel: pd.DataFrame,
    accidents: pd.DataFrame,
    traffic_period: str,
    vehicle_group: str,
) -> pd.DataFrame:
    if traffic_period != "all":
        period = traffic_period.upper()
        panel = panel[panel["traffic_period"].eq(period)].copy()
        accidents = accidents[accidents["traffic_period"].eq(period)].copy()
    if vehicle_group != "all":
        group = "1 vehicle" if vehicle_group == "one" else "2 or more vehicles"
        accidents = accidents[accidents["vehicle_group"].eq(group)].copy()
    bins = analysis_bins(panel)
    labels = bins["bin_label"].tolist()
    edges = np.r_[bins["bin_lower_ms"].to_numpy(float), np.inf]
    accidents = accidents.copy()
    accidents["bin_label"] = pd.cut(
        accidents["wind_value"], bins=edges, labels=labels, right=False, include_lowest=True
    )
    key = ["year", "road_section", "traffic_period", "bin_label"]
    counts = accidents.groupby(key, as_index=False, observed=False)["nid"].nunique()
    counts = counts.rename(columns={"nid": "observed_accidents"})
    data = panel.merge(counts, on=key, how="left", validate="one_to_one")
    data["observed_accidents"] = data["observed_accidents"].fillna(0).astype(int)
    data = data[data["estimated_vehicle_km"].gt(0)].copy()
    data["stratum"] = (
        data["road_section"].astype(str)
        + "|" + data["year"].astype(str)
        + "|" + data["traffic_period"].astype(str)
    )
    data["offset"] = np.log(data["estimated_vehicle_km"])
    return data


def add_counter_informed_exposure(data: pd.DataFrame, weights_path: Path) -> pd.DataFrame:
    weights = pd.read_csv(weights_path, usecols=["f_bin", "traffic_response_factor"])
    weights = weights.rename(columns={"f_bin": "bin_label"})
    data = data.merge(weights, on="bin_label", how="left", validate="many_to_one")
    if data["traffic_response_factor"].isna().any():
        raise ValueError("Daily traffic factors are missing one or more rate-analysis wind bins")
    data["weighted_vehicle_km"] = (
        data["estimated_vehicle_km"] * data["traffic_response_factor"]
    )
    key = ["year", "road_section", "traffic_period"]
    totals = data.groupby(key, as_index=False).agg(
        annual_vehicle_km=("estimated_vehicle_km", "sum"),
        weighted_vehicle_km=("weighted_vehicle_km", "sum"),
    )
    data = data.merge(totals, on=key, how="left", validate="many_to_one")
    data["counter_informed_vehicle_km"] = (
        data["weighted_vehicle_km_x"]
        * data["annual_vehicle_km"]
        / data["weighted_vehicle_km_y"]
    )
    return data.drop(columns=["weighted_vehicle_km_x", "weighted_vehicle_km_y"])


def fit_model(
    data: pd.DataFrame, bins: pd.DataFrame, exposure_column: str, prefix: str
) -> pd.DataFrame:
    labels = bins["bin_label"].tolist()
    baseline = labels[0]
    exog = pd.get_dummies(data["bin_label"], dtype=float).reindex(columns=labels, fill_value=0.0)
    exog = exog.drop(columns=baseline)
    model = ConditionalPoisson(
        data["observed_accidents"].to_numpy(),
        exog.to_numpy(),
        groups=data["stratum"].to_numpy(),
        offset=np.log(data[exposure_column].to_numpy(float)),
    )
    fitted = model.fit(disp=False, maxiter=200)
    confidence = fitted.conf_int()
    observed = data.groupby("bin_label", as_index=False, observed=False)["observed_accidents"].sum()
    result = bins.merge(observed, on="bin_label", how="left")
    result["observed_accidents"] = result["observed_accidents"].fillna(0).astype(int)
    result[f"{prefix}_rate_ratio"] = 1.0
    result[f"{prefix}_ci_95_low"] = np.nan
    result[f"{prefix}_ci_95_high"] = np.nan
    result[f"{prefix}_p_value"] = np.nan
    for index, label in enumerate(labels[1:]):
        coefficient = float(fitted.params[index])
        result.loc[result["bin_label"].eq(label), f"{prefix}_rate_ratio"] = np.exp(coefficient)
        result.loc[result["bin_label"].eq(label), f"{prefix}_ci_95_low"] = np.exp(confidence[index, 0])
        result.loc[result["bin_label"].eq(label), f"{prefix}_ci_95_high"] = np.exp(confidence[index, 1])
        result.loc[result["bin_label"].eq(label), f"{prefix}_p_value"] = float(fitted.pvalues[index])
    result["model_accidents"] = int(data["observed_accidents"].sum())
    result["model_strata"] = int(model._n_groups)
    result["model_rows"] = int(model.nobs)
    return result


def plot(result: pd.DataFrame, path: Path, title: str) -> None:
    x = np.arange(len(result))
    time_values = result["time_proportional_rate_ratio"].to_numpy(float)
    has_counter_informed = "counter_informed_rate_ratio" in result
    counter_values = (
        result["counter_informed_rate_ratio"].to_numpy(float)
        if has_counter_informed else None
    )
    fig, axis = plt.subplots(figsize=(11.4, 6.6))
    width = 0.34 if has_counter_informed else 0.72
    bars = axis.bar(
        x - width / 2 if has_counter_informed else x,
        time_values,
        color="#6C757D", width=width, label="Time-proportional allocation",
    )
    counter_bars = bars
    if has_counter_informed:
        counter_bars = axis.bar(
            x + width / 2, counter_values, color="#C7522A", width=width,
            label="Counter-informed allocation",
        )
    axis.axhline(1, color="#202020", linestyle="--", linewidth=1.1)
    axis.set_xticks(x, result["bin_label"].str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Mean wind-speed interval, f (m/s)")
    axis.set_ylabel("Within-stratum rate ratio versus 0–5 m/s")
    axis.set_title(title)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    plotted_values = np.maximum(time_values, counter_values) if has_counter_informed else time_values
    ymax = max(1.2, float(plotted_values.max()) * 1.22)
    axis.set_ylim(0, ymax)
    for bar, row in zip(counter_bars, result.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            max(bar.get_height() * 0.5, ymax * 0.06),
            f"n={row.observed_accidents}",
            ha="center", va="center", fontsize=9, color="white",
        )
    if has_counter_informed:
        axis.legend(frameon=False, ncols=2, loc="upper left")
    fig.text(
        0.5,
        0.02,
        "Conditional Poisson model within road section, year, and traffic period."
        + (" Counter-informed allocation uses 2019–2024 daily counter data." if has_counter_informed else ""),
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
    parser.add_argument("-S", "--skip-counter-informed", action="store_true")
    parser.add_argument("-t", "--traffic-period", choices=["all", "vdu", "sdu"], default="all")
    parser.add_argument("-g", "--vehicle-group", choices=["all", "one", "two-plus"], default="all")
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-f", "--figure", type=Path, default=FIGURE)
    args = parser.parse_args()
    panel = load_panel(args.panel, "f_5m")
    accidents, audit = load_accidents(args.accidents, panel, "f_5m")
    data = build_model_data(panel, accidents, args.traffic_period, args.vehicle_group)
    if data.empty or data["observed_accidents"].sum() == 0:
        raise ValueError("No accidents remain after subgroup selection")
    bins = analysis_bins(panel)
    time_result = fit_model(data, bins, "estimated_vehicle_km", "time_proportional")
    result = time_result
    if not args.skip_counter_informed:
        data = add_counter_informed_exposure(data, args.traffic_weights)
        counter_result = fit_model(data, bins, "counter_informed_vehicle_km", "counter_informed")
        result = time_result.merge(
            counter_result.drop(columns=["observed_accidents", "model_accidents", "model_strata", "model_rows"]),
            on=["bin_label", "bin_lower_ms"],
            how="left",
            validate="one_to_one",
        )
    result["analysis_traffic_period"] = args.traffic_period
    result["analysis_vehicle_group"] = args.vehicle_group
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    scope = []
    if args.traffic_period != "all":
        scope.append("winter VDU" if args.traffic_period == "vdu" else "summer SDU")
    if args.vehicle_group != "all":
        scope.append("one vehicle" if args.vehicle_group == "one" else "two or more vehicles")
    title = "Estimated rural injury-accident rate ratio by mean wind speed"
    if scope:
        title += " (" + ", ".join(scope) + ")"
    plot(result, args.figure, title)
    print(result.to_string(index=False))
    print(pd.DataFrame([audit]).to_string(index=False))


if __name__ == "__main__":
    main()
