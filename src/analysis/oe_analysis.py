"""Shared definitions and calculations for weather-frequency O/E analyses.

This module has no command-line interface and writes no files.  The pipeline
entry points use it so wind, gust, and temperature follow exactly the same
aggregation and bootstrap rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

from src.accidents.types import SINGLE_VEHICLE_FAMILY
from src.weather.frequency import (
    FG_UPPER_BOUNDS,
    F_UPPER_BOUNDS,
    TEMPERATURE_LABELS,
    TEMPERATURE_THRESHOLDS,
    labels,
)


PRIMARY_MAX_TIME_DIFFERENCE_MINUTES = 5
PRIMARY_VARIABLE = "f"


@dataclass(frozen=True)
class VariableSpec:
    """Columns and intervals required to analyse one weather variable."""

    variable: str
    accident_column: str
    upper_bounds: np.ndarray
    title: str
    station_column: str = "weather_station_id"
    distance_column: str = "weather_station_dist_km"
    time_difference_column: str = "weather_time_difference_minutes"
    custom_bin_labels: tuple[str, ...] | None = None
    custom_bin_edges: tuple[float, ...] | None = None

    @property
    def bin_labels(self) -> list[str]:
        if self.custom_bin_labels is not None:
            return list(self.custom_bin_labels)
        return labels(self.upper_bounds)

    @property
    def bin_edges(self) -> list[float]:
        if self.custom_bin_edges is not None:
            return list(self.custom_bin_edges)
        return [0, *self.upper_bounds, np.inf]


VARIABLES = [
    VariableSpec("f", "f", F_UPPER_BOUNDS, "Mean wind speed"),
    VariableSpec(
        "fg", "fg", FG_UPPER_BOUNDS, "Wind gust at matched accident time"
    ),
    VariableSpec(
        "temperature",
        "temperature_c",
        TEMPERATURE_THRESHOLDS,
        "Temperature",
        station_column="temp_station_id",
        distance_column="temp_distance_km",
        time_difference_column="temp_time_diff_min",
        custom_bin_labels=tuple(TEMPERATURE_LABELS),
        custom_bin_edges=(-np.inf, *TEMPERATURE_THRESHOLDS, np.inf),
    ),
]
SAMPLES = {
    "Injury accidents": lambda data: pd.Series(True, index=data.index),
    "Serious or fatal": lambda data: data["meidsli"].le(2),
    "Fatal": lambda data: data["meidsli"].eq(1),
    "1 vehicle": lambda data: data["vehicle_group"].eq("1 vehicle"),
    "2 or more vehicles": lambda data: data["vehicle_group"].eq(
        "2 or more vehicles"
    ),
    "Single-vehicle accident type": lambda data: data["accident_family"].eq(
        SINGLE_VEHICLE_FAMILY
    ),
    "Other accident types": lambda data: ~data["accident_family"].eq(
        SINGLE_VEHICLE_FAMILY
    ),
}
COARSE_BINS = {
    "f": {value: value for value in labels(F_UPPER_BOUNDS)},
    "fg": {value: value for value in labels(FG_UPPER_BOUNDS)},
    "temperature": {value: value for value in TEMPERATURE_LABELS},
}
BIN_ORDER = {
    "f": labels(F_UPPER_BOUNDS),
    "fg": labels(FG_UPPER_BOUNDS),
    "temperature": TEMPERATURE_LABELS,
}


def read_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Read an inspectable analysis CSV and reject other input formats."""
    if path.suffix != ".csv":
        raise ValueError(f"Analysis input must be a CSV file: {path}")
    return pd.read_csv(path, usecols=columns)


def prepare_details(path: Path) -> pd.DataFrame:
    """Load station-bin counts and attach the common analysis bins."""
    details = read_csv(path)
    if "max_time_difference_minutes" not in details:
        details["max_time_difference_minutes"] = PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
    details["coarse_bin"] = pd.NA
    for variable, mapping in COARSE_BINS.items():
        mask = details["variable"].eq(variable)
        details.loc[mask, "coarse_bin"] = details.loc[mask, "weather_bin"].map(
            mapping
        )
    if details["coarse_bin"].isna().any():
        examples = details.loc[
            details["coarse_bin"].isna(), ["variable", "weather_bin"]
        ]
        raise ValueError(
            f"Unmapped detailed weather bins: "
            f"{examples.drop_duplicates().to_dict('records')}"
        )
    return details


def poisson_ratio_interval(
    observed: pd.Series, expected: pd.Series
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate exact Poisson intervals for observed/expected ratios."""
    obs = observed.to_numpy(dtype=float)
    exp = expected.to_numpy(dtype=float)
    low_count = np.where(obs > 0, 0.5 * chi2.ppf(0.025, 2 * obs), 0.0)
    high_count = 0.5 * chi2.ppf(0.975, 2 * (obs + 1))
    low = np.divide(low_count, exp, out=np.full_like(exp, np.nan), where=exp > 0)
    high = np.divide(high_count, exp, out=np.full_like(exp, np.nan), where=exp > 0)
    return low, high


def station_frequency_scenario(
    accidents: pd.DataFrame,
    frequency: pd.DataFrame,
    spec: VariableSpec,
    radius: int,
    severity: str,
    analysis_season: str,
    max_time_difference_minutes: float = PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Build observed and expected counts for one station-frequency scenario."""
    scoped = accidents[
        accidents[spec.distance_column].le(radius)
        & accidents[spec.time_difference_column].le(max_time_difference_minutes)
        & accidents[spec.accident_column].notna()
        & accidents[spec.station_column].notna()
        & SAMPLES[severity](accidents)
    ].copy()
    if analysis_season != "All seasons":
        scoped = scoped[scoped["season"].eq(analysis_season)].copy()

    # Both variables use this internal name after their independent match.
    scoped["weather_station_id"] = scoped[spec.station_column].astype(int)
    scoped["weather_bin"] = pd.cut(
        scoped[spec.accident_column],
        bins=spec.bin_edges,
        labels=spec.bin_labels,
        right=False,
        include_lowest=True,
        ordered=True,
    )
    scoped = scoped.dropna(subset=["weather_bin"])

    group_columns = ["weather_station_id", "season"]
    if "year" in frequency.columns:
        group_columns.append("year")
    group_totals = (
        scoped.groupby(group_columns, observed=False)["id"]
        .nunique()
        .rename("group_accidents")
        .reset_index()
    )
    observed = (
        scoped.groupby([*group_columns, "weather_bin"], observed=False)["id"]
        .nunique()
        .rename("observed_accidents")
        .reset_index()
    )
    background = frequency[frequency["variable"].eq(spec.variable)][
        [
            *group_columns,
            "bin_label",
            "measurement_count",
            "total_measurements_in_period",
            "frequency_pct",
        ]
    ].rename(columns={"bin_label": "weather_bin"})
    if background.duplicated([*group_columns, "weather_bin"]).any():
        raise ValueError(
            f"Duplicate background bins found for variable {spec.variable}"
        )
    frequency_totals = background.groupby(group_columns)["frequency_pct"].sum()
    bad = ~np.isclose(frequency_totals.to_numpy(float), 100.0, atol=1e-6)
    if bad.any():
        examples = frequency_totals[bad].head().to_dict()
        raise ValueError(
            f"Background frequencies for {spec.variable} do not sum to 100%; "
            f"examples={examples}"
        )

    details = group_totals.merge(
        background, on=group_columns, how="inner", validate="one_to_many"
    ).merge(
        observed,
        on=[*group_columns, "weather_bin"],
        how="left",
        validate="one_to_one",
    )
    details["observed_accidents"] = (
        details["observed_accidents"].fillna(0).astype(int)
    )
    details["expected_accidents"] = (
        details["group_accidents"] * details["frequency_pct"] / 100
    )
    details["variable"] = spec.variable
    details["radius_km"] = radius
    details["severity_group"] = severity
    details["analysis_season"] = analysis_season
    details["max_time_difference_minutes"] = max_time_difference_minutes

    result = (
        details.groupby("weather_bin", as_index=False, sort=False)
        .agg(
            observed_accidents=("observed_accidents", "sum"),
            expected_accidents=("expected_accidents", "sum"),
            background_measurements=("measurement_count", "sum"),
            station_periods=("group_accidents", "size"),
            stations=("weather_station_id", "nunique"),
        )
    )
    result["relative_accident_frequency"] = (
        result["observed_accidents"] / result["expected_accidents"]
    )
    low, high = poisson_ratio_interval(
        result["observed_accidents"], result["expected_accidents"]
    )
    result["ci_95_low"] = low
    result["ci_95_high"] = high
    result["sparse_bin"] = result["observed_accidents"].lt(20)
    result["variable"] = spec.variable
    result["radius_km"] = radius
    result["severity_group"] = severity
    result["analysis_season"] = analysis_season
    result["max_time_difference_minutes"] = max_time_difference_minutes
    result["bin_order"] = result["weather_bin"].map(
        {label: index for index, label in enumerate(spec.bin_labels)}
    )

    analysed_ids = details[group_columns].drop_duplicates().merge(
        scoped[["id", *group_columns]], on=group_columns, how="inner"
    )["id"].nunique()
    coverage = {
        "variable": spec.variable,
        "radius_km": radius,
        "severity_group": severity,
        "analysis_season": analysis_season,
        "max_time_difference_minutes": max_time_difference_minutes,
        "eligible_accidents": len(scoped),
        "analysed_accidents": int(analysed_ids),
        "coverage_pct": 100 * analysed_ids / len(scoped) if len(scoped) else np.nan,
        "expected_sum": details["expected_accidents"].sum(),
        "observed_sum": details["observed_accidents"].sum(),
    }
    return result, details, coverage


def cluster_bootstrap(
    station_bins: pd.DataFrame,
    variable: str,
    reps: int,
    seed: int,
    bins: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resample whole weather stations and return O/E intervals and draws."""
    bins = BIN_ORDER[variable] if bins is None else bins
    observed = (
        station_bins.pivot(
            index="weather_station_id",
            columns="coarse_bin",
            values="observed_accidents",
        )
        .reindex(columns=bins, fill_value=0)
        .fillna(0)
    )
    expected = (
        station_bins.pivot(
            index="weather_station_id",
            columns="coarse_bin",
            values="expected_accidents",
        )
        .reindex(index=observed.index, columns=bins, fill_value=0)
        .fillna(0)
    )
    station_count = len(observed)
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(
        station_count,
        np.full(station_count, 1 / station_count),
        size=reps,
    )
    observed_draws = weights @ observed.to_numpy(float)
    expected_draws = weights @ expected.to_numpy(float)
    ratios = np.divide(
        observed_draws,
        expected_draws,
        out=np.full_like(observed_draws, np.nan),
        where=expected_draws > 0,
    )
    intervals = pd.DataFrame(
        {
            "coarse_bin": bins,
            "bootstrap_ci_95_low": np.nanpercentile(ratios, 2.5, axis=0),
            "bootstrap_ci_95_high": np.nanpercentile(ratios, 97.5, axis=0),
            "bootstrap_median": np.nanmedian(ratios, axis=0),
            "bootstrap_standard_error": np.nanstd(ratios, axis=0, ddof=1),
            "bootstrap_probability_above_1": np.nanmean(ratios > 1, axis=0),
            "bootstrap_reps": reps,
            "bootstrap_stations": station_count,
        }
    )
    draws = pd.DataFrame(ratios, columns=bins)
    draws.insert(0, "bootstrap_rep", np.arange(reps))
    draws = draws.melt(
        id_vars="bootstrap_rep",
        var_name="coarse_bin",
        value_name="relative_accident_frequency",
    )
    draws["variable"] = variable
    return intervals, draws


def analyse_scenario(
    details: pd.DataFrame,
    variable: str,
    radius: int,
    severity: str,
    season: str,
    reps: int,
    seed: int,
    max_time_difference_minutes: float = PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
    bin_mapping: dict[str, str] | None = None,
    bin_order: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate one defined O/E sample and calculate clustered intervals."""
    subset = details[
        details["variable"].eq(variable)
        & details["radius_km"].eq(radius)
        & details["severity_group"].eq(severity)
        & details["analysis_season"].eq(season)
        & details["max_time_difference_minutes"].eq(
            max_time_difference_minutes
        )
    ].copy()
    if bin_mapping is None:
        subset["analysis_bin"] = subset["coarse_bin"]
        active_order = BIN_ORDER[variable]
    else:
        subset["analysis_bin"] = subset["weather_bin"].map(bin_mapping)
        active_order = bin_order or list(dict.fromkeys(bin_mapping.values()))
        if subset["analysis_bin"].isna().any():
            raise ValueError("Alternative bin mapping left detailed bins unmapped")
    station_bins = (
        subset.groupby(["weather_station_id", "analysis_bin"], as_index=False)
        .agg(
            observed_accidents=("observed_accidents", "sum"),
            expected_accidents=("expected_accidents", "sum"),
            background_measurements=("measurement_count", "sum"),
        )
        .rename(columns={"analysis_bin": "coarse_bin"})
    )
    intervals, draws = cluster_bootstrap(
        station_bins, variable, reps, seed, bins=active_order
    )
    result = (
        station_bins.groupby("coarse_bin", as_index=False)
        .agg(
            observed_accidents=("observed_accidents", "sum"),
            expected_accidents=("expected_accidents", "sum"),
            background_measurements=("background_measurements", "sum"),
            stations=("weather_station_id", "nunique"),
        )
        .merge(intervals, on="coarse_bin", how="left", validate="one_to_one")
    )
    result["relative_accident_frequency"] = (
        result["observed_accidents"] / result["expected_accidents"]
    )
    result["variable"] = variable
    result["radius_km"] = radius
    result["severity_group"] = severity
    result["analysis_season"] = season
    result["max_time_difference_minutes"] = max_time_difference_minutes
    order = {value: index for index, value in enumerate(active_order)}
    result["bin_order"] = result["coarse_bin"].map(order)
    result = result.sort_values("bin_order")
    draws["radius_km"] = radius
    draws["severity_group"] = severity
    draws["analysis_season"] = season
    draws["max_time_difference_minutes"] = max_time_difference_minutes
    return result, draws


def validate_totals(result: pd.DataFrame, expected_accidents: int) -> None:
    """Require observed and expected totals to equal the defined sample size."""
    observed = int(result["observed_accidents"].sum())
    expected = float(result["expected_accidents"].sum())
    if observed != expected_accidents:
        raise ValueError(
            f"Coarse-bin accidents changed: {observed} != {expected_accidents}"
        )
    if not np.isclose(expected, expected_accidents, atol=1e-6):
        raise ValueError(
            f"Coarse-bin expected total changed: {expected} != {expected_accidents}"
        )
