"""Shared calculations for the seasonal daily-traffic analysis.

The canonical input is one counter-year-season panel.  Thin scripts in
``src.tables`` call these functions to preserve small, explicit pipeline
outputs without repeating model preparation or statistical code.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm
from statsmodels.discrete.conditional_models import ConditionalPoisson

from src.tables.counter_rate import fit_model
from src.tables.daily_season_panel import LABELS, SEASONS


ANALYSIS_PERIOD = "2019-2024"
EXPOSURE_METHOD = "observed daily traffic allocated by full-day wind frequency"


def fit_seasonal_rates(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit the allocated daily-counter rate model separately by season."""
    results: list[pd.DataFrame] = []
    audit_rows: list[dict[str, object]] = []
    for season_name in SEASONS:
        data = panel[panel["season"].eq(season_name)].copy()
        informative = (
            data.groupby("stratum")["observed_accidents"]
            .transform("sum")
            .gt(0)
        )
        data = data[informative & data["allocated_vehicles"].gt(0)].copy()
        if data.empty:
            raise ValueError(f"No informative strata remain for {season_name}")

        fit_input = data.rename(columns={"allocated_vehicles": "observed_vehicles"})
        result = fit_model(fit_input, LABELS).rename(
            columns={
                "observed_vehicles": "estimated_vehicles_within_wind_bin",
                "accidents_per_100k_counted_vehicles":
                    "accidents_per_100k_estimated_vehicles",
            }
        )
        result["season"] = season_name
        result["analysis_period"] = ANALYSIS_PERIOD
        result["exposure_method"] = EXPOSURE_METHOD
        results.append(result)
        audit_rows.append(
            {
                "season": season_name,
                "model_accidents": int(data["observed_accidents"].sum()),
                "candidate_strata": int(data["stratum"].nunique()),
                "fitted_strata": int(result["model_strata"].iloc[0]),
                "model_rows": int(result["model_rows"].iloc[0]),
            }
        )
    return pd.concat(results, ignore_index=True), pd.DataFrame(audit_rows)


def _model_arrays(data: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        data["observed_accidents"].to_numpy(),
        data["stratum"].to_numpy(),
        np.log(data["allocated_vehicles"].to_numpy(float)),
    )


def _fit(
    design: pd.DataFrame,
    outcome: np.ndarray,
    groups: np.ndarray,
    offset: np.ndarray,
):
    return ConditionalPoisson(
        outcome, design.to_numpy(), groups=groups, offset=offset
    ).fit(disp=False, maxiter=500)


def _wind_design(data: pd.DataFrame) -> pd.DataFrame:
    """Return two non-reference wind indicators in fixed order."""
    return (
        pd.get_dummies(data["wind_bin"], prefix="wind", dtype=float)
        .reindex(columns=[f"wind_{label}" for label in LABELS], fill_value=0.0)
        .drop(columns="wind_0-10")
    )


def _estimate(
    names: list[str],
    params: pd.Series,
    covariance: pd.DataFrame,
    terms: list[str],
) -> tuple[float, float, float, float]:
    weights = pd.Series(0.0, index=names)
    for term in terms:
        weights[term] = 1.0
    coefficient = float(weights @ params)
    standard_error = float(np.sqrt(weights @ covariance @ weights))
    return (
        float(np.exp(coefficient)),
        float(np.exp(coefficient - 1.96 * standard_error)),
        float(np.exp(coefficient + 1.96 * standard_error)),
        float(2 * norm.sf(abs(coefficient / standard_error))),
    )


def fit_full_season_interaction(data: pd.DataFrame) -> pd.DataFrame:
    """Test all six wind-by-season terms and return seasonal estimates."""
    wind = _wind_design(data)
    reduced_design = wind.copy()
    full_design = wind.copy()
    interaction_terms: list[str] = []
    for season in SEASONS[1:]:
        in_season = data["season"].eq(season).astype(float)
        for wind_term in wind.columns:
            name = f"{wind_term}:{season}"
            full_design[name] = wind[wind_term] * in_season
            interaction_terms.append(name)

    outcome, groups, offset = _model_arrays(data)
    reduced = _fit(reduced_design, outcome, groups, offset)
    full = _fit(full_design, outcome, groups, offset)
    statistic = max(0.0, 2 * (full.llf - reduced.llf))
    degrees_of_freedom = len(interaction_terms)
    omnibus_p = float(chi2.sf(statistic, degrees_of_freedom))
    parameter_names = list(full_design.columns)
    params = pd.Series(full.params, index=parameter_names)
    covariance = pd.DataFrame(
        full.cov_params(), index=parameter_names, columns=parameter_names
    )
    rows: list[dict[str, object]] = [
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
    for season in SEASONS:
        for wind_label, wind_term in [
            ("10-15 m/s", "wind_10-15"),
            (">=15 m/s", "wind_>=15"),
        ]:
            terms = [wind_term]
            if season != "Winter":
                terms.append(f"{wind_term}:{season}")
            rate_ratio, low, high, p_value = _estimate(
                parameter_names, params, covariance, terms
            )
            rows.append(
                {
                    "result": "Season-specific estimate",
                    "season": season,
                    "comparison": wind_label,
                    "reference": "0-10 m/s",
                    "rate_ratio": rate_ratio,
                    "ci_95_low": low,
                    "ci_95_high": high,
                    "p_value": p_value,
                    "likelihood_ratio_chi2": np.nan,
                    "degrees_of_freedom": np.nan,
                }
            )
    result = pd.DataFrame(rows)
    result["model_accidents"] = int(data["observed_accidents"].sum())
    result["strata"] = int(data["stratum"].nunique())
    result["model_rows"] = len(data)
    result["analysis_period"] = ANALYSIS_PERIOD
    result["exposure_method"] = EXPOSURE_METHOD
    return result


def fit_highwind_interaction(data: pd.DataFrame) -> pd.DataFrame:
    """Test only the >=15 m/s seasonal terms while retaining other terms."""
    wind = _wind_design(data)
    reduced = wind.copy()
    for season in SEASONS[1:]:
        reduced[f"wind_10-15:{season}"] = (
            wind["wind_10-15"] * data["season"].eq(season).to_numpy(float)
        )
    full = reduced.copy()
    highwind_terms: list[str] = []
    for season in SEASONS[1:]:
        name = f"wind_>=15:{season}"
        full[name] = wind["wind_>=15"] * data["season"].eq(season).to_numpy(float)
        highwind_terms.append(name)

    outcome, groups, offset = _model_arrays(data)
    reduced_fit = _fit(reduced, outcome, groups, offset)
    full_fit = _fit(full, outcome, groups, offset)
    statistic = max(0.0, 2 * (full_fit.llf - reduced_fit.llf))
    p_value = float(chi2.sf(statistic, len(highwind_terms)))
    names = list(full.columns)
    params = pd.Series(full_fit.params, index=names)
    covariance = pd.DataFrame(full_fit.cov_params(), index=names, columns=names)
    common = {
        "model_accidents": int(data["observed_accidents"].sum()),
        "strata": int(data["stratum"].nunique()),
        "model_rows": len(data),
        "analysis_period": ANALYSIS_PERIOD,
        "exposure_method": EXPOSURE_METHOD,
    }
    rows: list[dict[str, object]] = [
        {
            "result": ">=15 m/s season interaction test",
            "season": "All seasons",
            "comparison": ">=15 m/s interaction terms",
            "reference":
                "Common >=15 vs 0-10 m/s association; 10-15 interactions retained",
            "rate_ratio": np.nan,
            "ci_95_low": np.nan,
            "ci_95_high": np.nan,
            "p_value": p_value,
            "likelihood_ratio_chi2": statistic,
            "degrees_of_freedom": len(highwind_terms),
            "observed_highwind_accidents": int(
                data.loc[
                    data["wind_bin"].eq(">=15"), "observed_accidents"
                ].sum()
            ),
            **common,
        }
    ]
    for season in SEASONS:
        terms = ["wind_>=15"]
        if season != "Winter":
            terms.append(f"wind_>=15:{season}")
        rate_ratio, low, high, row_p = _estimate(
            names, params, covariance, terms
        )
        rows.append(
            {
                "result": "Season-specific estimate",
                "season": season,
                "comparison": ">=15 m/s",
                "reference": "0-10 m/s",
                "rate_ratio": rate_ratio,
                "ci_95_low": low,
                "ci_95_high": high,
                "p_value": row_p,
                "likelihood_ratio_chi2": np.nan,
                "degrees_of_freedom": np.nan,
                "observed_highwind_accidents": int(
                    data.loc[
                        data["season"].eq(season)
                        & data["wind_bin"].eq(">=15"),
                        "observed_accidents",
                    ].sum()
                ),
                **common,
            }
        )
    return pd.DataFrame(rows)


def calculate_seasonal_oe(
    panel: pd.DataFrame, replicates: int, seed: int
) -> pd.DataFrame:
    """Standardise seasonal accidents to allocated traffic and bootstrap counters."""
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

    grouped = data.groupby(
        ["season", "wind_bin"], observed=True, as_index=False
    ).agg(
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
    intervals: list[dict[str, object]] = []
    for season in SEASONS:
        for wind_bin in LABELS:
            selected = cluster[
                cluster["season"].eq(season) & cluster["wind_bin"].eq(wind_bin)
            ].set_index("counter_id")
            observed = selected["observed"].reindex(
                counter_values, fill_value=0
            ).to_numpy(float)
            expected = selected["expected"].reindex(
                counter_values, fill_value=0
            ).to_numpy(float)
            boot_expected = expected[sampled].sum(axis=1)
            valid = boot_expected > 0
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
    result["analysis_period"] = ANALYSIS_PERIOD
    result["exposure_method"] = EXPOSURE_METHOD
    result["standardisation"] = (
        "expected accidents proportional to exposure within counter-year-season"
    )
    result["season"] = pd.Categorical(result["season"], SEASONS, ordered=True)
    result["wind_bin"] = pd.Categorical(result["wind_bin"], LABELS, ordered=True)
    return result.sort_values(["season", "wind_bin"]).reset_index(drop=True)


def compare_season_methods(
    weather: pd.DataFrame,
    matched: pd.DataFrame,
    annual: pd.DataFrame,
    daily: pd.DataFrame,
    daily_oe: pd.DataFrame,
    full_interaction: pd.DataFrame,
    focused_interaction: pd.DataFrame,
) -> pd.DataFrame:
    """Place the four seasonal methods in one explicitly supporting audit."""
    weather = weather[
        weather["variable"].eq("f")
        & weather["radius_km"].eq(20)
        & weather["severity_group"].eq("Injury accidents")
        & weather["max_time_difference_minutes"].eq(5)
        & ~weather["analysis_season"].eq("All seasons")
        & weather["weather_bin"].isin(["15-20", "20-25", ">=25"])
    ].groupby("analysis_season", as_index=False).agg(
        weather_observed_highwind=("observed_accidents", "sum"),
        weather_expected_highwind=("expected_accidents", "sum"),
    )
    weather["weather_only_oe"] = (
        weather["weather_observed_highwind"]
        / weather["weather_expected_highwind"]
    )
    weather = weather.rename(columns={"analysis_season": "season"})

    matched_p = float(
        matched.loc[
            matched["result"].eq("Season interaction test"), "p_value"
        ].iloc[0]
    )
    matched = matched[matched["result"].eq("Season-specific estimate")][
        ["season", "odds_ratio", "ci_95_low", "ci_95_high"]
    ].rename(
        columns={
            "odds_ratio": "matched_time_or",
            "ci_95_low": "matched_time_ci_low",
            "ci_95_high": "matched_time_ci_high",
        }
    )
    annual = annual[annual["bin_label"].eq(">=15")][
        [
            "season", "observed_accidents", "time_proportional_rate_ratio",
            "time_proportional_ci_95_low", "time_proportional_ci_95_high",
        ]
    ].rename(
        columns={
            "observed_accidents": "annual_highwind_accidents",
            "time_proportional_rate_ratio": "annual_traffic_rr",
            "time_proportional_ci_95_low": "annual_traffic_ci_low",
            "time_proportional_ci_95_high": "annual_traffic_ci_high",
        }
    )
    daily = daily[daily["wind_bin"].eq(">=15")][
        ["season", "observed_accidents", "rate_ratio", "ci_95_low", "ci_95_high"]
    ].rename(
        columns={
            "observed_accidents": "daily_highwind_accidents",
            "rate_ratio": "daily_traffic_rr",
            "ci_95_low": "daily_traffic_ci_low",
            "ci_95_high": "daily_traffic_ci_high",
        }
    )
    daily_oe = daily_oe[daily_oe["wind_bin"].eq(">=15")][
        ["season", "traffic_standardised_oe", "ci_95_low", "ci_95_high"]
    ].rename(
        columns={
            "ci_95_low": "traffic_oe_ci_low",
            "ci_95_high": "traffic_oe_ci_high",
        }
    )
    full_p = float(
        full_interaction.loc[
            full_interaction["season"].eq("All seasons"), "p_value"
        ].iloc[0]
    )
    focused_p = float(
        focused_interaction.loc[
            focused_interaction["season"].eq("All seasons"), "p_value"
        ].iloc[0]
    )
    for frame in (weather, matched, annual, daily, daily_oe):
        frame["season"] = frame["season"].replace({"Fall": "Autumn"})
    result = weather.merge(matched, on="season", validate="one_to_one").merge(
        annual, on="season", validate="one_to_one"
    ).merge(daily, on="season", validate="one_to_one").merge(
        daily_oe, on="season", validate="one_to_one"
    )
    result["matched_time_interaction_p"] = matched_p
    result["daily_full_interaction_p"] = full_p
    result["daily_highwind_interaction_p"] = focused_p
    order = pd.Categorical(
        result["season"], ["Winter", "Spring", "Summer", "Autumn"], ordered=True
    )
    return (
        result.assign(_order=order)
        .sort_values("_order")
        .drop(columns="_order")
    )
