"""Test whether the matched mean-wind association differs by season."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm
from statsmodels.discrete.conditional_models import ConditionalLogit


INPUT = Path("data/analysis/case_control.csv")
OUTPUT = Path("reports/main/tables/wind_season.csv")
SEASONS = ["Winter", "Spring", "Summer", "Autumn"]
WIND_LABELS = ["0-10", "10-15", ">=15"]


def season_from_timestamp(timestamp: pd.Series) -> pd.Series:
    month = pd.to_datetime(timestamp, errors="raise").dt.month
    season = pd.Series("Autumn", index=timestamp.index, dtype="string")
    season.loc[month.isin([12, 1, 2, 3])] = "Winter"
    season.loc[month.isin([4, 5])] = "Spring"
    season.loc[month.isin([6, 7, 8, 9])] = "Summer"
    return season


def fit(data: pd.DataFrame) -> pd.DataFrame:
    required = {"exposure", "stratum_id", "case", "timestamp", "value"}
    if missing := required - set(data):
        raise ValueError(f"Case-crossover data are missing columns: {sorted(missing)}")
    scoped = data[data["exposure"].eq("mean_wind")].copy()
    scoped["season"] = season_from_timestamp(scoped["timestamp"])
    scoped["wind_interval"] = pd.cut(
        scoped["value"], [0, 10, 15, np.inf], labels=WIND_LABELS, right=False
    )
    if scoped["wind_interval"].isna().any():
        raise ValueError("Mean-wind values fall outside the defined intervals")

    wind = pd.get_dummies(scoped["wind_interval"], prefix="wind", dtype=float).drop(
        columns="wind_0-10"
    )
    full_design = wind.copy()
    interaction_terms: list[str] = []
    for season in SEASONS[1:]:
        in_season = scoped["season"].eq(season).astype(float)
        for wind_term in wind:
            name = f"{wind_term}:{season}"
            full_design[name] = wind[wind_term] * in_season
            interaction_terms.append(name)

    groups = scoped["stratum_id"]
    outcome = scoped["case"].astype(int)
    reduced = ConditionalLogit(outcome, wind, groups=groups).fit(
        disp=False, maxiter=500
    )
    full = ConditionalLogit(outcome, full_design, groups=groups).fit(
        disp=False, maxiter=500
    )
    statistic = max(0.0, 2 * (full.llf - reduced.llf))
    degrees_of_freedom = len(interaction_terms)
    omnibus_p = float(chi2.sf(statistic, degrees_of_freedom))

    rows: list[dict[str, object]] = [
        {
            "result": "Season interaction test",
            "season": "All seasons",
            "comparison": "All wind-by-season interaction terms",
            "reference": "Common wind association across seasons",
            "odds_ratio": np.nan,
            "ci_95_low": np.nan,
            "ci_95_high": np.nan,
            "p_value": omnibus_p,
            "likelihood_ratio_chi2": statistic,
            "degrees_of_freedom": degrees_of_freedom,
        }
    ]
    covariance = full.cov_params()
    high_term = "wind_>=15"
    for season in SEASONS:
        weights = pd.Series(0.0, index=full.params.index)
        weights[high_term] = 1.0
        if season != "Winter":
            weights[f"{high_term}:{season}"] = 1.0
        coefficient = float(weights @ full.params)
        standard_error = float(np.sqrt(weights @ covariance @ weights))
        rows.append(
            {
                "result": "Season-specific estimate",
                "season": season,
                "comparison": ">=15 m/s",
                "reference": "0-10 m/s",
                "odds_ratio": np.exp(coefficient),
                "ci_95_low": np.exp(coefficient - 1.96 * standard_error),
                "ci_95_high": np.exp(coefficient + 1.96 * standard_error),
                "p_value": 2 * norm.sf(abs(coefficient / standard_error)),
                "likelihood_ratio_chi2": np.nan,
                "degrees_of_freedom": np.nan,
            }
        )
    result = pd.DataFrame(rows)
    result["strata"] = scoped["stratum_id"].nunique()
    result["cases"] = int(scoped["case"].sum())
    result["control_times"] = int(scoped["case"].eq(0).sum())
    result["matching"] = "same station, year, month, weekday, and clock time"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = fit(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
