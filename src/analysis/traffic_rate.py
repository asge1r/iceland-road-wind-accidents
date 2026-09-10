"""Reusable conditional Poisson fit for daily-counter rate comparisons."""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.discrete.conditional_models import ConditionalPoisson


def fit_daily_rate_model(data: pd.DataFrame, labels: list[str]) -> pd.DataFrame:
    """Fit a within-stratum rate model and return estimates plus sample totals."""
    exog = pd.get_dummies(data["wind_bin"], dtype=float).reindex(
        columns=labels, fill_value=0.0
    )
    model = ConditionalPoisson(
        data["observed_accidents"].to_numpy(),
        exog.drop(columns=labels[0]).to_numpy(),
        groups=data["stratum"].to_numpy(),
        offset=np.log(data["observed_vehicles"].to_numpy(float)),
    )
    fitted = model.fit(disp=False, maxiter=300)
    confidence = fitted.conf_int()
    result = (
        data.groupby("wind_bin", as_index=False, observed=True)
        .agg(
            observed_accidents=("observed_accidents", "sum"),
            observed_vehicles=("observed_vehicles", "sum"),
            counter_days=("counter_days", "sum"),
            counters=("counter_id", "nunique"),
        )
        .set_index("wind_bin")
        .reindex(labels)
        .reset_index()
    )
    result["accidents_per_100k_counted_vehicles"] = (
        result["observed_accidents"] / result["observed_vehicles"] * 100_000
    )
    result["rate_ratio"] = 1.0
    result["ci_95_low"] = np.nan
    result["ci_95_high"] = np.nan
    result["p_value"] = np.nan
    for index, label in enumerate(labels[1:]):
        mask = result["wind_bin"].eq(label)
        result.loc[mask, "rate_ratio"] = np.exp(fitted.params[index])
        result.loc[mask, "ci_95_low"] = np.exp(confidence[index, 0])
        result.loc[mask, "ci_95_high"] = np.exp(confidence[index, 1])
        result.loc[mask, "p_value"] = fitted.pvalues[index]
    result["model_accidents"] = int(data["observed_accidents"].sum())
    result["model_strata"] = int(model._n_groups)
    result["model_rows"] = int(model.nobs)
    return result
