"""Estimate within-road/year/period wind-rate ratios from a compact CSV file."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.discrete.conditional_models import ConditionalPoisson


INPUT = Path("data/analysis/rate_model.csv")
OUTPUT = Path("reports/main/tables/stratified_crash_rate_ratio_by_wind.csv")
FIGURE = Path("reports/main/figures/stratified_crash_rate_ratio_by_wind.png")

COUNT_COLUMN = {
    "all": "injury_accidents",
    "one": "one_vehicle_accidents",
    "two-plus": "multiple_vehicle_accidents",
}


def select_periods(data: pd.DataFrame, traffic_period: str) -> pd.DataFrame:
    if traffic_period == "all":
        return data.copy()
    if traffic_period == "official":
        return data[data["traffic_period"].isin(["VDU", "SDU"])].copy()
    return data[data["traffic_period"].eq(traffic_period.upper())].copy()


def prepare_data(source: pd.DataFrame, traffic_period: str, vehicle_group: str) -> pd.DataFrame:
    required = {
        "year", "road_section", "traffic_period", "wind_bin", "wind_bin_lower_ms",
        "estimated_vehicle_km", *COUNT_COLUMN.values(),
    }
    missing = required - set(source.columns)
    if missing:
        raise ValueError(f"Rate-model CSV is missing columns: {sorted(missing)}")
    data = select_periods(source, traffic_period)
    count_column = COUNT_COLUMN[vehicle_group]
    data = data.copy()
    data["observed_accidents"] = pd.to_numeric(data[count_column], errors="raise").astype(int)
    totals = data.groupby(["year", "road_section", "traffic_period"])["observed_accidents"].transform("sum")
    data = data[totals.gt(0) & data["estimated_vehicle_km"].gt(0)].copy()
    data["stratum"] = (
        data["road_section"].astype(str)
        + "|" + data["year"].astype(str)
        + "|" + data["traffic_period"].astype(str)
    )
    return data


def fit_model(data: pd.DataFrame) -> pd.DataFrame:
    bins = data[["wind_bin", "wind_bin_lower_ms"]].drop_duplicates().sort_values("wind_bin_lower_ms")
    labels = bins["wind_bin"].tolist()
    baseline = labels[0]
    exog = pd.get_dummies(data["wind_bin"], dtype=float).reindex(columns=labels, fill_value=0.0)
    exog = exog.drop(columns=baseline)
    model = ConditionalPoisson(
        data["observed_accidents"].to_numpy(),
        exog.to_numpy(),
        groups=data["stratum"].to_numpy(),
        offset=np.log(data["estimated_vehicle_km"].to_numpy(float)),
    )
    fitted = model.fit(disp=False, maxiter=200)
    confidence = fitted.conf_int()
    observed = data.groupby("wind_bin", as_index=False)["observed_accidents"].sum()
    result = bins.merge(observed, on="wind_bin", how="left", validate="one_to_one")
    result["time_proportional_rate_ratio"] = 1.0
    result["time_proportional_ci_95_low"] = np.nan
    result["time_proportional_ci_95_high"] = np.nan
    result["time_proportional_p_value"] = np.nan
    for index, label in enumerate(labels[1:]):
        coefficient = float(fitted.params[index])
        mask = result["wind_bin"].eq(label)
        result.loc[mask, "time_proportional_rate_ratio"] = np.exp(coefficient)
        result.loc[mask, "time_proportional_ci_95_low"] = np.exp(confidence[index, 0])
        result.loc[mask, "time_proportional_ci_95_high"] = np.exp(confidence[index, 1])
        result.loc[mask, "time_proportional_p_value"] = float(fitted.pvalues[index])
    result["model_accidents"] = int(data["observed_accidents"].sum())
    result["model_strata"] = int(model._n_groups)
    result["model_rows"] = int(model.nobs)
    return result


def plot(result: pd.DataFrame, path: Path, title: str) -> None:
    x = np.arange(len(result))
    values = result["time_proportional_rate_ratio"].to_numpy(float)
    figure, axis = plt.subplots(figsize=(11.4, 6.6))
    bars = axis.bar(x, values, color="#287271", width=0.72)
    axis.axhline(1, color="#202020", linestyle="--", linewidth=1.1)
    axis.set_xticks(x, result["bin_label"].str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Mean wind-speed interval, f (m/s)")
    axis.set_ylabel("Within-stratum rate ratio versus 0–5 m/s")
    axis.set_title(title)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    top = max(1.2, float(values.max()) * 1.22)
    axis.set_ylim(0, top)
    for bar, row in zip(bars, result.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            max(bar.get_height() * 0.5, top * 0.06),
            f"n={row.observed_accidents}",
            ha="center", va="center", fontsize=9, color="white",
        )
    figure.text(
        0.5, 0.02,
        "Conditional Poisson model within road section, year, and traffic period.\n"
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
    parser.add_argument("-g", "--vehicle-group", choices=list(COUNT_COLUMN), default="all")
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-f", "--figure", type=Path, default=FIGURE)
    args = parser.parse_args()
    data = prepare_data(pd.read_csv(args.input), args.traffic_period, args.vehicle_group)
    if data.empty:
        raise ValueError("No informative road-year-period strata remain after selection")
    result = fit_model(data)
    result = result.rename(columns={"wind_bin": "bin_label", "wind_bin_lower_ms": "bin_lower_ms"})
    result["analysis_traffic_period"] = args.traffic_period
    result["analysis_vehicle_group"] = args.vehicle_group
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    scope = []
    if args.traffic_period == "official":
        scope.append("official VDU + SDU periods")
    elif args.traffic_period != "all":
        scope.append(args.traffic_period.upper())
    if args.vehicle_group != "all":
        scope.append("one vehicle" if args.vehicle_group == "one" else "two or more vehicles")
    title = "Estimated rural injury-accident rate ratio by mean wind speed"
    if scope:
        title += " (" + ", ".join(scope) + ")"
    plot(result, args.figure, title)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
