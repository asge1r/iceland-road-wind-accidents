"""Traffic-standardise seasonal accident occurrence within counter-year-season."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.tables.daily_season_panel import (
    LABELS,
    OUTPUT as PANEL,
    SEASONS,
    read_panel,
)


OUTPUT = Path("reports/main/tables/daily_season_oe.csv")


def calculate(panel: pd.DataFrame, replicates: int, seed: int) -> pd.DataFrame:
    data = panel.copy()
    totals = data.groupby("stratum", observed=True).agg(
        stratum_accidents=("observed_accidents", "sum"),
        stratum_exposure=("allocated_vehicles", "sum"),
    )
    totals = totals[
        totals["stratum_accidents"].gt(0) & totals["stratum_exposure"].gt(0)
    ]
    data = data.merge(totals, on="stratum", how="inner", validate="many_to_one")
    data["traffic_expected_accidents"] = (
        data["stratum_accidents"]
        * data["allocated_vehicles"]
        / data["stratum_exposure"]
    )

    check = data.groupby("stratum", observed=True).agg(
        observed=("observed_accidents", "sum"),
        expected=("traffic_expected_accidents", "sum"),
    )
    if not np.allclose(check["observed"], check["expected"], rtol=1e-12, atol=1e-10):
        raise ValueError("Expected counts do not reconstruct accidents within strata")

    grouped = data.groupby(["season", "wind_bin"], observed=True, as_index=False).agg(
        observed_accidents=("observed_accidents", "sum"),
        traffic_expected_accidents=("traffic_expected_accidents", "sum"),
        allocated_vehicles=("allocated_vehicles", "sum"),
        contributing_strata=("stratum", "nunique"),
        counters=("counter_id", "nunique"),
    )
    grouped["traffic_standardised_oe"] = (
        grouped["observed_accidents"] / grouped["traffic_expected_accidents"]
    )

    season_check = grouped.groupby("season", observed=True).agg(
        observed=("observed_accidents", "sum"),
        expected=("traffic_expected_accidents", "sum"),
    )
    if not np.allclose(
        season_check["observed"], season_check["expected"], rtol=1e-12, atol=1e-10
    ):
        raise ValueError("Expected counts do not reconstruct accidents within seasons")

    counter_values = np.sort(data["counter_id"].drop_duplicates().to_numpy())
    cluster = data.groupby(
        ["counter_id", "season", "wind_bin"], observed=True, as_index=False
    ).agg(
        observed=("observed_accidents", "sum"),
        expected=("traffic_expected_accidents", "sum"),
    )
    rng = np.random.default_rng(seed)
    sampled = rng.integers(
        0, len(counter_values), size=(replicates, len(counter_values))
    )
    intervals = []
    for season in SEASONS:
        for wind_bin in LABELS:
            selected = cluster[
                cluster["season"].eq(season) & cluster["wind_bin"].eq(wind_bin)
            ].set_index("counter_id")
            observed = selected["observed"].reindex(counter_values, fill_value=0).to_numpy(float)
            expected = selected["expected"].reindex(counter_values, fill_value=0).to_numpy(float)
            boot_expected = expected[sampled].sum(axis=1)
            valid = boot_expected.gt(0) if isinstance(boot_expected, pd.Series) else boot_expected > 0
            ratios = observed[sampled].sum(axis=1)[valid] / boot_expected[valid]
            intervals.append(
                {
                    "season": season,
                    "wind_bin": wind_bin,
                    "ci_95_low": float(np.quantile(ratios, 0.025)),
                    "ci_95_high": float(np.quantile(ratios, 0.975)),
                    "bootstrap_valid_replicates": int(valid.sum()),
                }
            )
    result = grouped.merge(
        pd.DataFrame(intervals), on=["season", "wind_bin"], validate="one_to_one"
    )
    accidents_by_season = data.groupby("season", observed=True)[
        "observed_accidents"
    ].sum()
    result["accidents_in_season"] = result["season"].map(accidents_by_season)
    result["bootstrap_replicates"] = replicates
    result["bootstrap_cluster"] = "counter"
    result["analysis_period"] = "2019-2024"
    result["exposure_method"] = (
        "observed daily traffic allocated by full-day wind frequency"
    )
    result["standardisation"] = (
        "expected accidents proportional to exposure within counter-year-season"
    )
    result["season"] = pd.Categorical(result["season"], SEASONS, ordered=True)
    result["wind_bin"] = pd.Categorical(result["wind_bin"], LABELS, ordered=True)
    return result.sort_values(["season", "wind_bin"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-b", "--bootstrap-replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260909)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = calculate(read_panel(args.panel), args.bootstrap_replicates, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
