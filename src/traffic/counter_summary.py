"""Calculate normalized daily-counter summaries and ADU checks."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.traffic.daily_common import (
    DAILY_F_UPPER_BOUNDS,
    FG_UPPER_BOUNDS,
    labels,
    normalize_section,
)

def add_normalized_traffic(panel: pd.DataFrame) -> pd.DataFrame:
    """Normalize traffic within counter, year, month, and weekday."""
    panel = panel.copy()
    panel["weekday"] = panel["date"].dt.weekday
    panel["month"] = panel["date"].dt.month
    panel["year"] = panel["date"].dt.year
    baseline_columns = ["counter_site_id", "year", "month", "weekday"]
    baseline = panel.groupby(baseline_columns, as_index=False).agg(
        typical_traffic=("traffic_volume", "median"),
        baseline_days=("traffic_volume", "size"),
    )
    panel = panel.merge(
        baseline, on=baseline_columns, how="left", validate="many_to_one"
    )
    panel["traffic_index"] = np.where(
        panel["typical_traffic"].gt(0),
        100 * panel["traffic_volume"] / panel["typical_traffic"],
        np.nan,
    )
    return panel

def add_bin(data: pd.DataFrame, variable: str, upper_bounds: list[int]) -> pd.DataFrame:
    output = data.copy()
    output["bin"] = pd.cut(
        output[variable],
        bins=[0, *upper_bounds, np.inf],
        labels=labels(upper_bounds),
        right=False,
        include_lowest=True,
        ordered=True,
    )
    return output

def cluster_bootstrap_counter_medians(
    counter_bins: pd.DataFrame,
    bins: list[str],
    replicates: int,
    seed: int = 20260721,
) -> pd.DataFrame:
    """Bootstrap equal-weighted counter medians by resampling counters."""
    wide = counter_bins.pivot(
        index="counter_site_id", columns="bin", values="counter_median_traffic_index"
    ).reindex(columns=bins)
    values = wide.to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    boot = np.full((replicates, len(bins)), np.nan)
    for replicate in range(replicates):
        sampled = rng.integers(0, len(values), len(values))
        with np.errstate(all="ignore"):
            boot[replicate] = np.nanmedian(values[sampled], axis=0)
    return pd.DataFrame(
        {
            "bin": bins,
            "ci_95_low": np.nanpercentile(boot, 2.5, axis=0),
            "ci_95_high": np.nanpercentile(boot, 97.5, axis=0),
        }
    )

def build_wind_summary(panel: pd.DataFrame, replicates: int) -> pd.DataFrame:
    """Summarize normalized traffic by wind with counter-cluster intervals."""
    frames: list[pd.DataFrame] = []
    specs = [
        ("f_daytime_mean", DAILY_F_UPPER_BOUNDS),
        ("fg_daytime_mean", FG_UPPER_BOUNDS),
    ]
    for variable, upper_bounds in specs:
        data = panel.dropna(subset=[variable, "traffic_index"]).copy()
        if variable == "f_daytime_mean":
            # The display ends at 33 m/s. After the station-quality screen,
            # the remaining >=33 m/s tail has only five counter-days.
            data = data[data[variable].lt(33)]
        data = add_bin(data, variable, upper_bounds)
        categories = [
            str(value)
            for value in data["bin"].cat.categories
            if data["bin"].eq(value).any()
        ]
        data["bin"] = data["bin"].astype("string")
        counter_bins = data.groupby(["counter_site_id", "bin"], as_index=False).agg(
            counter_median_traffic_index=("traffic_index", "median"),
            counter_days=("date", "size"),
        )
        summary = counter_bins.groupby("bin", as_index=False).agg(
            traffic_index_median=("counter_median_traffic_index", "median"),
            traffic_index_mean=("counter_median_traffic_index", "mean"),
            counters=("counter_site_id", "nunique"),
            counter_days=("counter_days", "sum"),
        )
        nonzero_counter_bins = (
            data[data["traffic_volume"].gt(0)]
            .groupby(["counter_site_id", "bin"], as_index=False)
            .agg(nonzero_counter_median_traffic_index=("traffic_index", "median"))
        )
        nonzero_summary = nonzero_counter_bins.groupby(
            "bin", as_index=False
        ).agg(
            traffic_index_median_excluding_zero=(
                "nonzero_counter_median_traffic_index",
                "median",
            )
        )
        zero_days = (
            data.assign(is_zero=data["traffic_volume"].eq(0))
            .groupby("bin", as_index=False)
            .agg(zero_counter_days=("is_zero", "sum"))
        )
        summary = summary.merge(nonzero_summary, on="bin", how="left").merge(
            zero_days, on="bin", how="left"
        )
        summary = pd.DataFrame({"bin": categories}).merge(
            summary, on="bin", how="left"
        )
        intervals = cluster_bootstrap_counter_medians(
            counter_bins, categories, replicates
        )
        summary = summary.merge(intervals, on="bin", how="left")
        summary["variable"] = variable
        summary["bin_order"] = np.arange(len(summary))
        frames.append(summary)
    return pd.concat(frames, ignore_index=True)

def build_adu_validation(
    daily: pd.DataFrame, annual_path: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare observed counter-year means with exact road-section ADU."""
    annual = pd.read_csv(
        annual_path, usecols=["year", "road_section", "adu", "sdu", "vdu"]
    )
    annual["road_section"] = normalize_section(annual["road_section"])
    if annual.duplicated(["year", "road_section"]).any():
        raise ValueError("Annual traffic is not unique on year + road_section")

    counter_year = daily.groupby(
        ["counter_site_id", "year", "road_section"], as_index=False
    ).agg(
        observed_days=("date", "nunique"),
        observed_daily_mean=("traffic_volume", "mean"),
        observed_daily_median=("traffic_volume", "median"),
        observed_daily_sum=("traffic_volume", "sum"),
    )
    section_counts = counter_year.groupby(
        ["year", "road_section"], as_index=False
    ).agg(counters_on_section=("counter_site_id", "nunique"))
    result = counter_year.merge(
        section_counts, on=["year", "road_section"], how="left"
    ).merge(
        annual,
        on=["year", "road_section"],
        how="left",
        validate="many_to_one",
    )
    result["mean_to_adu_ratio"] = result["observed_daily_mean"] / result["adu"]
    result["median_to_adu_ratio"] = result["observed_daily_median"] / result["adu"]
    result["adu_available"] = result["adu"].notna()
    result["near_complete_year"] = result["observed_days"].ge(300)
    result["single_counter_section"] = result["counters_on_section"].eq(1)

    summaries = []
    scopes = {
        "all_exact_matches": result[result["adu_available"]],
        "at_least_300_days": result[
            result["adu_available"] & result["near_complete_year"]
        ],
        "at_least_300_days_single_counter_section": result[
            result["adu_available"]
            & result["near_complete_year"]
            & result["single_counter_section"]
        ],
    }
    for name, data in scopes.items():
        valid = data[
            data["adu"].gt(0) & data["observed_daily_mean"].gt(0)
        ]
        summaries.append(
            {
                "scope": name,
                "counter_years": len(valid),
                "counters": valid["counter_site_id"].nunique(),
                "road_sections": valid["road_section"].nunique(),
                "median_mean_to_adu_ratio": valid["mean_to_adu_ratio"].median(),
                "p10_mean_to_adu_ratio": valid["mean_to_adu_ratio"].quantile(0.10),
                "p90_mean_to_adu_ratio": valid["mean_to_adu_ratio"].quantile(0.90),
                "pearson_log_correlation": np.log(valid["adu"]).corr(
                    np.log(valid["observed_daily_mean"])
                ),
            }
        )
    return result, pd.DataFrame(summaries)
