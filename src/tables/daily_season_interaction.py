"""Test whether the daily-traffic-adjusted mean-wind association differs by season."""

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


OUTPUT = Path("reports/working/tables/daily_season_interaction.csv")


def main() -> None:

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)

    args = parser.parse_args()

    data = informative_model_data(read_panel(args.panel))

    # 0-10 m/s is the reference category.
    wind = (
        pd.get_dummies(
            data["wind_bin"],
            prefix="wind",
            dtype=float,
        )
        .reindex(
            columns=[
                "wind_0-10",
                "wind_10-15",
                "wind_>=15",
            ],
            fill_value=0.0,
        )
        .drop(columns="wind_0-10")
    )

    # Reduced model: one common wind relationship across seasons.
    reduced_design = wind.copy()

    # Full model: wind x season interactions.
    # Winter is the reference season.
    full_design = wind.copy()

    interaction_terms = []

    for season in SEASONS[1:]:

        in_season = data["season"].eq(season).astype(float)

        for wind_term in wind.columns:

            name = f"{wind_term}:{season}"

            full_design[name] = (
                wind[wind_term] * in_season
            )

            interaction_terms.append(name)

    outcome = data["observed_accidents"].to_numpy()
    groups = data["stratum"].to_numpy()
    offset = np.log(data["allocated_vehicles"].to_numpy(float))

    reduced = ConditionalPoisson(
        outcome,
        reduced_design.to_numpy(),
        groups=groups,
        offset=offset,
    ).fit(
        disp=False,
        maxiter=500,
    )

    full = ConditionalPoisson(
        outcome,
        full_design.to_numpy(),
        groups=groups,
        offset=offset,
    ).fit(
        disp=False,
        maxiter=500,
    )

    statistic = max(
        0.0,
        2 * (full.llf - reduced.llf),
    )

    degrees_of_freedom = len(interaction_terms)

    omnibus_p = float(
        chi2.sf(
            statistic,
            degrees_of_freedom,
        )
    )

    parameter_names = list(full_design.columns)

    params = pd.Series(
        full.params,
        index=parameter_names,
    )

    covariance = pd.DataFrame(
        full.cov_params(),
        index=parameter_names,
        columns=parameter_names,
    )

    rows = [
        {
            "result": "Season interaction test",
            "season": "All seasons",
            "comparison": "All wind-by-season interaction terms",
            "reference": "Common wind association across seasons",
            "rate_ratio": np.nan,
            "ci_95_low": np.nan,
            "ci_95_high": np.nan,
            "p_value": omnibus_p,
            "likelihood_ratio_chi2": statistic,
            "degrees_of_freedom": degrees_of_freedom,
        }
    ]

    # Report both non-reference wind categories for each season.
    for season in SEASONS:

        for wind_label, wind_term in [
            ("10-15 m/s", "wind_10-15"),
            (">=15 m/s", "wind_>=15"),
        ]:

            weights = pd.Series(
                0.0,
                index=parameter_names,
            )

            weights[wind_term] = 1.0

            if season != "Winter":
                weights[f"{wind_term}:{season}"] = 1.0

            coefficient = float(
                weights @ params
            )

            standard_error = float(
                np.sqrt(
                    weights
                    @ covariance
                    @ weights
                )
            )

            rows.append(
                {
                    "result": "Season-specific estimate",
                    "season": season,
                    "comparison": wind_label,
                    "reference": "0-10 m/s",
                    "rate_ratio": np.exp(coefficient),
                    "ci_95_low": np.exp(
                        coefficient
                        - 1.96 * standard_error
                    ),
                    "ci_95_high": np.exp(
                        coefficient
                        + 1.96 * standard_error
                    ),
                    "p_value": 2 * norm.sf(
                        abs(
                            coefficient
                            / standard_error
                        )
                    ),
                    "likelihood_ratio_chi2": np.nan,
                    "degrees_of_freedom": np.nan,
                }
            )

    result = pd.DataFrame(rows)

    result["model_accidents"] = int(
        data["observed_accidents"].sum()
    )

    result["strata"] = int(
        data["stratum"].nunique()
    )

    result["model_rows"] = len(data)

    result["analysis_period"] = "2019-2024"

    result["exposure_method"] = (
        "observed daily traffic allocated by full-day wind frequency"
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        args.output,
        index=False,
    )

    print(result.to_string(index=False))

    print("\nMODEL SAMPLE")
    print(
        data.groupby("season", observed=True).agg(
            accidents=("observed_accidents", "sum"),
            strata=("stratum", "nunique"),
            rows=("wind_bin", "size"),
        ).reindex(SEASONS).to_string()
    )

    print(
        "\nReduced log-likelihood:",
        reduced.llf,
    )

    print(
        "Full log-likelihood:",
        full.llf,
    )

    print(
        f"Interaction LR chi2({degrees_of_freedom}) "
        f"= {statistic:.4f}, p = {omnibus_p:.6f}"
    )


if __name__ == "__main__":
    main()
