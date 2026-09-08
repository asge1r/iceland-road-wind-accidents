"""Fit a joint matched-time model for mean wind and temperature."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.discrete.conditional_models import ConditionalLogit

from src.weather.frequency import TEMPERATURE_LABELS, TEMPERATURE_THRESHOLDS


INPUT = Path("data/analysis/case_control.csv")
OUTPUT = Path("reports/main/tables/weather_model.csv")
WIND_BINS = [0, 5, 10, 15, np.inf]
WIND_LABELS = ["0-5", "5-10", "10-15", ">=15"]
TEMP_BINS = [-np.inf, *TEMPERATURE_THRESHOLDS, np.inf]
TEMP_LABELS = TEMPERATURE_LABELS


def prepare(data: pd.DataFrame) -> pd.DataFrame:
    required = {"exposure", "stratum_id", "case", "timestamp", "value"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Matched-time data are missing columns: {sorted(missing)}")
    scoped = data[data["exposure"].isin(["mean_wind", "temperature"])].copy()
    scoped["timestamp"] = pd.to_datetime(scoped["timestamp"], errors="raise")
    wide = scoped.pivot(
        index=["stratum_id", "case", "timestamp"],
        columns="exposure",
        values="value",
    ).dropna().reset_index()
    counts = wide.groupby("stratum_id")["case"].agg(["sum", "count"])
    valid = counts[counts["sum"].eq(1) & counts["count"].ge(2)].index
    return wide[wide["stratum_id"].isin(valid)].copy()


def model_rows(data: pd.DataFrame) -> pd.DataFrame:
    data["mean_wind_interval"] = pd.cut(
        data["mean_wind"], WIND_BINS, labels=WIND_LABELS, right=False
    )
    data["temperature_interval"] = pd.cut(
        data["temperature"], TEMP_BINS, labels=TEMP_LABELS, right=False
    )
    wind = pd.get_dummies(data["mean_wind_interval"], prefix="wind", dtype=float).drop(
        columns="wind_0-5"
    )
    temperature = pd.get_dummies(
        data["temperature_interval"], prefix="temperature", dtype=float
    ).drop(columns="temperature_0-3")
    design = pd.concat([wind, temperature], axis=1)
    model = ConditionalLogit(
        data["case"].astype(int), design, groups=data["stratum_id"]
    ).fit(disp=False, maxiter=500)
    intervals = model.conf_int()
    rows: list[dict[str, object]] = []
    for term in design:
        if term.startswith("wind_"):
            variable = "Mean wind"
            comparison = term.removeprefix("wind_")
            reference = "0-5 m/s"
            comparison = f"{comparison} m/s"
        else:
            variable = "Temperature"
            comparison = term.removeprefix("temperature_")
            reference = "0-3 °C"
            comparison = f"{comparison} °C"
        rows.append(
            {
                "variable": variable,
                "comparison": comparison,
                "reference": reference,
                "adjusted_odds_ratio": np.exp(model.params[term]),
                "ci_95_low": np.exp(intervals.loc[term].iloc[0]),
                "ci_95_high": np.exp(intervals.loc[term].iloc[1]),
                "p_value": model.pvalues[term],
            }
        )
    result = pd.DataFrame(rows)
    result["strata"] = data["stratum_id"].nunique()
    result["cases"] = int(data["case"].sum())
    result["control_times"] = int(data["case"].eq(0).sum())
    result["model_note"] = "Mean wind and temperature included together"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = model_rows(prepare(pd.read_csv(args.input)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
