"""Compare weather-frequency and traffic-standardised wind O/E results."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.tables.rate import prepare_data


WEATHER = Path("reports/main/tables/oe_results.csv")
ANNUAL = Path("data/analysis/road_rate.csv")
DAILY = Path("reports/working/tables/daily_season_panel.csv")
OUTPUT = Path("reports/main/tables/wind_oe_comparison.csv")
STANDARD_BINS = ["0-5", "5-10", "10-15", "15-20", "20-25", ">=25"]
DAILY_BINS = ["0-10", "10-15", ">=15"]


def standardised_oe(
    data: pd.DataFrame,
    *,
    stratum: str,
    cluster: str,
    exposure: str,
    bins: list[str],
    replicates: int,
    seed: int,
) -> pd.DataFrame:
    """Allocate each stratum's accidents by exposure and bootstrap clusters."""
    frame = data.copy()
    totals = frame.groupby(stratum, observed=True).agg(
        stratum_accidents=("observed_accidents", "sum"),
        stratum_exposure=(exposure, "sum"),
    )
    totals = totals[
        totals["stratum_accidents"].gt(0) & totals["stratum_exposure"].gt(0)
    ]
    frame = frame.merge(totals, left_on=stratum, right_index=True, validate="many_to_one")
    frame["expected_accidents"] = (
        frame["stratum_accidents"] * frame[exposure] / frame["stratum_exposure"]
    )
    check = frame.groupby(stratum, observed=True).agg(
        observed=("observed_accidents", "sum"),
        expected=("expected_accidents", "sum"),
    )
    if not np.allclose(check["observed"], check["expected"]):
        raise ValueError("Expected accidents do not reconstruct stratum totals")

    result = frame.groupby("wind_bin", observed=True, as_index=False).agg(
        observed_accidents=("observed_accidents", "sum"),
        expected_accidents=("expected_accidents", "sum"),
    )
    result = result.set_index("wind_bin").reindex(bins).reset_index()
    result["observed_expected_ratio"] = (
        result["observed_accidents"] / result["expected_accidents"]
    )

    cluster_values = np.sort(frame[cluster].drop_duplicates().to_numpy())
    cluster_bins = frame.groupby(
        [cluster, "wind_bin"], observed=True, as_index=False
    ).agg(
        observed=("observed_accidents", "sum"),
        expected=("expected_accidents", "sum"),
    )
    observed = cluster_bins.pivot(
        index=cluster, columns="wind_bin", values="observed"
    ).reindex(index=cluster_values, columns=bins, fill_value=0).fillna(0).to_numpy(float)
    expected = cluster_bins.pivot(
        index=cluster, columns="wind_bin", values="expected"
    ).reindex(index=cluster_values, columns=bins, fill_value=0).fillna(0).to_numpy(float)
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(cluster_values), size=(replicates, len(cluster_values)))
    boot_observed = observed[sampled].sum(axis=1)
    boot_expected = expected[sampled].sum(axis=1)
    ratios = np.divide(
        boot_observed,
        boot_expected,
        out=np.full_like(boot_observed, np.nan),
        where=boot_expected > 0,
    )
    result["ci_95_low"] = np.nanquantile(ratios, 0.025, axis=0)
    result["ci_95_high"] = np.nanquantile(ratios, 0.975, axis=0)
    result["bootstrap_replicates"] = replicates
    result["bootstrap_cluster"] = cluster.replace("_", " ")
    result["analysis_accidents"] = int(frame["observed_accidents"].sum())
    return result


def weather_rows(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path)
    required = {
        "coarse_bin", "observed_accidents", "expected_accidents",
        "relative_accident_frequency", "bootstrap_ci_95_low",
        "bootstrap_ci_95_high", "variable", "radius_km", "severity_group",
        "analysis_season", "max_time_difference_minutes", "bin_order",
    }
    if not required <= set(source):
        raise ValueError("Primary mean-wind O/E table is incomplete")
    source = source[
        source["variable"].eq("f")
        & source["radius_km"].eq(20)
        & source["severity_group"].eq("Injury accidents")
        & source["analysis_season"].eq("All seasons")
        & source["max_time_difference_minutes"].eq(5)
    ].sort_values("bin_order")
    result = source.rename(columns={
        "coarse_bin": "wind_bin",
        "relative_accident_frequency": "observed_expected_ratio",
        "bootstrap_ci_95_low": "ci_95_low",
        "bootstrap_ci_95_high": "ci_95_high",
    })[[
        "wind_bin", "observed_accidents", "expected_accidents",
        "observed_expected_ratio", "ci_95_low", "ci_95_high",
    ]].copy()
    result["bootstrap_replicates"] = 5000
    result["bootstrap_cluster"] = "weather station"
    result["analysis_accidents"] = int(result["observed_accidents"].sum())
    result["method"] = "Weather frequency"
    result["analysis_period"] = "2007-2025"
    result["standardisation"] = "weather station and season"
    result["exposure_method"] = "frequency of valid 10-minute weather observations"
    return result


def annual_rows(path: Path, replicates: int) -> pd.DataFrame:
    data = prepare_data(pd.read_csv(path), "all", "all")
    result = standardised_oe(
        data, stratum="stratum", cluster="road_section",
        exposure="estimated_vehicle_km", bins=STANDARD_BINS,
        replicates=replicates, seed=20260911,
    )
    result["method"] = "Annual traffic"
    result["analysis_period"] = "2007-2025"
    result["standardisation"] = "road section, year, and traffic period"
    result["exposure_method"] = (
        "annual traffic allocated by local wind frequency"
    )
    return result


def daily_rows(path: Path, replicates: int) -> pd.DataFrame:
    data = pd.read_csv(path)
    required = {
        "stratum", "counter_id", "wind_bin", "allocated_vehicles",
        "observed_accidents",
    }
    if not required <= set(data):
        raise ValueError("Daily seasonal panel is incomplete")
    result = standardised_oe(
        data, stratum="stratum", cluster="counter_id",
        exposure="allocated_vehicles", bins=DAILY_BINS,
        replicates=replicates, seed=20260912,
    )
    result["method"] = "Daily traffic"
    result["analysis_period"] = "2019-2024"
    result["standardisation"] = "counter, year, and season"
    result["exposure_method"] = (
        "observed daily traffic allocated by 10-minute wind frequency"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weather", type=Path, default=WEATHER)
    parser.add_argument("--annual", type=Path, default=ANNUAL)
    parser.add_argument("--daily", type=Path, default=DAILY)
    parser.add_argument("-b", "--bootstrap-replicates", type=int, default=5000)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.bootstrap_replicates <= 0:
        raise ValueError("Bootstrap replicates must be positive")
    result = pd.concat([
        weather_rows(args.weather),
        annual_rows(args.annual, args.bootstrap_replicates),
        daily_rows(args.daily, args.bootstrap_replicates),
    ], ignore_index=True)
    result["bin_order"] = result.groupby("method", sort=False).cumcount()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
