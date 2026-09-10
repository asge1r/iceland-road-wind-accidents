"""Test specifically whether the >=15 m/s daily association varies by season."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm
from statsmodels.discrete.conditional_models import ConditionalPoisson

from src.tables.daily_season_panel import (
    LABELS,
    OUTPUT as PANEL,
    SEASONS,
    informative_model_data,
    read_panel,
)


OUTPUT = Path("reports/working/tables/daily_highwind_season_interaction.csv")


def fit(data: pd.DataFrame) -> pd.DataFrame:
    wind = (
        pd.get_dummies(data["wind_bin"], prefix="wind", dtype=float)
        .reindex(columns=[f"wind_{label}" for label in LABELS], fill_value=0.0)
        .drop(columns="wind_0-10")
    )
    reduced = wind.copy()
    for season in SEASONS[1:]:
        reduced[f"wind_10-15:{season}"] = (
            wind["wind_10-15"] * data["season"].eq(season).to_numpy(float)
        )
    full = reduced.copy()
    highwind_terms = []
    for season in SEASONS[1:]:
        name = f"wind_>=15:{season}"
        full[name] = wind["wind_>=15"] * data["season"].eq(season).to_numpy(float)
        highwind_terms.append(name)

    outcome = data["observed_accidents"].to_numpy()
    groups = data["stratum"].to_numpy()
    offset = np.log(data["allocated_vehicles"].to_numpy(float))
    reduced_fit = ConditionalPoisson(
        outcome, reduced.to_numpy(), groups=groups, offset=offset
    ).fit(disp=False, maxiter=500)
    full_fit = ConditionalPoisson(
        outcome, full.to_numpy(), groups=groups, offset=offset
    ).fit(disp=False, maxiter=500)
    statistic = max(0.0, 2 * (full_fit.llf - reduced_fit.llf))
    p_value = float(chi2.sf(statistic, len(highwind_terms)))

    names = list(full.columns)
    params = pd.Series(full_fit.params, index=names)
    covariance = pd.DataFrame(full_fit.cov_params(), index=names, columns=names)
    common = {
        "model_accidents": int(data["observed_accidents"].sum()),
        "strata": int(data["stratum"].nunique()),
        "model_rows": len(data),
        "analysis_period": "2019-2024",
        "exposure_method": "observed daily traffic allocated by full-day wind frequency",
    }
    rows = [
        {
            "result": ">=15 m/s season interaction test",
            "season": "All seasons",
            "comparison": ">=15 m/s interaction terms",
            "reference": "Common >=15 vs 0-10 m/s association; 10-15 interactions retained",
            "rate_ratio": np.nan,
            "ci_95_low": np.nan,
            "ci_95_high": np.nan,
            "p_value": p_value,
            "likelihood_ratio_chi2": statistic,
            "degrees_of_freedom": len(highwind_terms),
            "observed_highwind_accidents": int(
                data.loc[data["wind_bin"].eq(">=15"), "observed_accidents"].sum()
            ),
            **common,
        }
    ]
    for season in SEASONS:
        weights = pd.Series(0.0, index=names)
        weights["wind_>=15"] = 1.0
        if season != "Winter":
            weights[f"wind_>=15:{season}"] = 1.0
        coefficient = float(weights @ params)
        standard_error = float(np.sqrt(weights @ covariance @ weights))
        rows.append(
            {
                "result": "Season-specific estimate",
                "season": season,
                "comparison": ">=15 m/s",
                "reference": "0-10 m/s",
                "rate_ratio": np.exp(coefficient),
                "ci_95_low": np.exp(coefficient - 1.96 * standard_error),
                "ci_95_high": np.exp(coefficient + 1.96 * standard_error),
                "p_value": 2 * norm.sf(abs(coefficient / standard_error)),
                "likelihood_ratio_chi2": np.nan,
                "degrees_of_freedom": np.nan,
                "observed_highwind_accidents": int(
                    data.loc[
                        data["season"].eq(season) & data["wind_bin"].eq(">=15"),
                        "observed_accidents",
                    ].sum()
                ),
                **common,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = informative_model_data(read_panel(args.panel))
    result = fit(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
