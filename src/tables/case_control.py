"""Fit time-stratified conditional logistic weather models."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.discrete.conditional_models import ConditionalLogit


DEFAULT_INPUT = Path("data/analysis/case_control.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/case_control_weather.csv")
SPECS = {
    "mean_wind": {
        "bins": [0, 5, 10, 15, np.inf],
        "labels": ["0-5", "5-10", "10-15", ">=15"],
        "reference": "0-5",
        "unit": "m/s",
    },
    "temperature": {
        "bins": [-np.inf, -5, 0, 5, 10, 15, np.inf],
        "labels": ["<-5", "-5-0", "0-5", "5-10", "10-15", ">=15"],
        "reference": "0-5",
        "unit": "deg C",
    },
}


def fit(data: pd.DataFrame, exposure: str) -> pd.DataFrame:
    spec = SPECS[exposure]
    scoped = data[data["exposure"].eq(exposure)].copy()
    groups = scoped["stratum_id"]
    continuous = scoped[["value"]].div(5).rename(columns={"value": "per_5_units"})
    continuous_model = ConditionalLogit(
        scoped["case"], continuous, groups=groups
    ).fit(disp=False, maxiter=300)
    continuous_ci = continuous_model.conf_int().loc["per_5_units"]
    rows = [
        {
            "exposure": exposure,
            "model": "continuous",
            "comparison": f"per 5 {spec['unit']}",
            "reference": "",
            "odds_ratio": np.exp(continuous_model.params["per_5_units"]),
            "ci_95_low": np.exp(continuous_ci.iloc[0]),
            "ci_95_high": np.exp(continuous_ci.iloc[1]),
            "p_value": continuous_model.pvalues["per_5_units"],
        }
    ]

    scoped["interval"] = pd.cut(
        scoped["value"], bins=spec["bins"], labels=spec["labels"], right=False
    )
    design = pd.get_dummies(scoped["interval"], dtype=float).drop(
        columns=spec["reference"]
    )
    categorical_model = ConditionalLogit(
        scoped["case"], design, groups=groups
    ).fit(disp=False, maxiter=300)
    intervals = categorical_model.conf_int()
    for comparison in design.columns:
        rows.append(
            {
                "exposure": exposure,
                "model": "categorical",
                "comparison": comparison,
                "reference": spec["reference"],
                "odds_ratio": np.exp(categorical_model.params[comparison]),
                "ci_95_low": np.exp(intervals.loc[comparison].iloc[0]),
                "ci_95_high": np.exp(intervals.loc[comparison].iloc[1]),
                "p_value": categorical_model.pvalues[comparison],
            }
        )
    result = pd.DataFrame(rows)
    result["strata"] = scoped["stratum_id"].nunique()
    result["cases"] = int(scoped["case"].sum())
    result["control_times"] = int(scoped["case"].eq(0).sum())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {"exposure", "stratum_id", "case", "value"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Case-crossover data are missing columns: {sorted(missing)}")
    result = pd.concat([fit(data, exposure) for exposure in SPECS], ignore_index=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
