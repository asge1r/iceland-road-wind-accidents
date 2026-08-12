"""Calculate frequency-adjusted observed/expected ratios for defined samples."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2

from src.weather.build_wind_frequency import (
    FG_MINUS_F_UPPER_BOUNDS,
    FG_UPPER_BOUNDS,
    F_UPPER_BOUNDS,
    labels,
)


DEFAULT_ACCIDENTS = Path(
    "data/processed/accidents/rural_injury_accidents.parquet"
)
DEFAULT_FREQUENCY = Path(
    "data/processed/weather/wind_frequency_station_year_season.parquet"
)
DEFAULT_RESULTS = Path("archive/generated_diagnostics/oe/detailed_results.csv")
DEFAULT_DETAILS = Path(
    "data/processed/accidents/oe_station_period_bins.parquet"
)
DEFAULT_COVERAGE = Path("archive/generated_diagnostics/oe/coverage.csv")
DEFAULT_NOTES = Path("archive/generated_diagnostics/oe/calculation_notes.txt")
DEFAULT_FIGURES = Path("archive/generated_diagnostics/figures")

SEASON_ORDER = ["Winter", "Spring", "Summer", "Fall"]
RADII = [10, 20, 30]
PRIMARY_MAX_TIME_DIFFERENCE_MINUTES = 5
TIME_SENSITIVITY_MINUTES = [0, 2]


@dataclass(frozen=True)
class VariableSpec:
    variable: str
    accident_column: str
    upper_bounds: np.ndarray
    title: str

    @property
    def bin_labels(self) -> list[str]:
        return labels(self.upper_bounds)


VARIABLES = [
    VariableSpec("f", "f", F_UPPER_BOUNDS, "Mean wind speed"),
    VariableSpec("fg", "fg", FG_UPPER_BOUNDS, "Maximum wind gust"),
    VariableSpec(
        "fg_minus_f",
        "fg_minus_f",
        FG_MINUS_F_UPPER_BOUNDS,
        "Gust difference (fg - f)",
    ),
]

SEVERITIES = {
    "Injury accidents": lambda data: pd.Series(True, index=data.index),
    "Serious or fatal": lambda data: data["meidsli"].le(2),
    "Fatal": lambda data: data["meidsli"].eq(1),
}


def season_from_month(month: pd.Series) -> pd.Series:
    season = pd.Series(index=month.index, dtype="object")
    season.loc[month.isin([12, 1, 2])] = "Winter"
    season.loc[month.isin([3, 4, 5])] = "Spring"
    season.loc[month.isin([6, 7, 8])] = "Summer"
    season.loc[month.isin([9, 10, 11])] = "Fall"
    return season


def load_data(
    accidents_path: Path, frequency_path: Path, start: str | None, end: str | None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    columns = [
        "nid",
        "timestamp",
        "meidsli",
        "weather_station_id",
        "weather_station_dist_km",
        "weather_time_difference_minutes",
        "f",
        "fg",
    ]
    accidents = pd.read_parquet(accidents_path, columns=columns)
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"])
    if start:
        accidents = accidents[accidents["timestamp"].ge(pd.Timestamp(start))]
    if end:
        accidents = accidents[accidents["timestamp"].le(pd.Timestamp(end))]
    accidents = accidents.copy()
    accidents["year"] = accidents["timestamp"].dt.year
    accidents["season"] = season_from_month(accidents["timestamp"].dt.month)
    accidents["fg_minus_f"] = (accidents["fg"] - accidents["f"]).clip(lower=0)

    frequency = pd.read_parquet(frequency_path)
    frequency = frequency.rename(columns={"station": "weather_station_id"})
    frequency["weather_station_id"] = pd.to_numeric(
        frequency["weather_station_id"], errors="raise"
    ).astype(int)
    return accidents, frequency


def poisson_ratio_interval(observed: pd.Series, expected: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    obs = observed.to_numpy(dtype=float)
    exp = expected.to_numpy(dtype=float)
    low_count = np.where(obs > 0, 0.5 * chi2.ppf(0.025, 2 * obs), 0.0)
    high_count = 0.5 * chi2.ppf(0.975, 2 * (obs + 1))
    low = np.divide(low_count, exp, out=np.full_like(exp, np.nan), where=exp > 0)
    high = np.divide(high_count, exp, out=np.full_like(exp, np.nan), where=exp > 0)
    return low, high


def one_analysis(
    accidents: pd.DataFrame,
    frequency: pd.DataFrame,
    spec: VariableSpec,
    radius: int,
    severity: str,
    analysis_season: str,
    max_time_difference_minutes: float = PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    scoped = accidents[
        accidents["weather_station_dist_km"].le(radius)
        & accidents["weather_time_difference_minutes"].le(
            max_time_difference_minutes
        )
        & accidents[spec.accident_column].notna()
        & SEVERITIES[severity](accidents)
    ].copy()
    if analysis_season != "All seasons":
        scoped = scoped[scoped["season"].eq(analysis_season)].copy()
    scoped["weather_station_id"] = scoped["weather_station_id"].astype(int)
    scoped["weather_bin"] = pd.cut(
        scoped[spec.accident_column],
        bins=[0, *spec.upper_bounds, np.inf],
        labels=spec.bin_labels,
        right=False,
        include_lowest=True,
        ordered=True,
    )
    scoped = scoped.dropna(subset=["weather_bin"])

    group_columns = ["weather_station_id", "year", "season"]
    group_totals = (
        scoped.groupby(group_columns, observed=False)["nid"]
        .nunique()
        .rename("group_accidents")
        .reset_index()
    )
    observed = (
        scoped.groupby([*group_columns, "weather_bin"], observed=False)["nid"]
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
    details = group_totals.merge(
        background, on=group_columns, how="inner", validate="one_to_many"
    ).merge(
        observed,
        on=[*group_columns, "weather_bin"],
        how="left",
        validate="one_to_one",
    )
    details["observed_accidents"] = details["observed_accidents"].fillna(0).astype(int)
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
        scoped[["nid", *group_columns]], on=group_columns, how="inner"
    )["nid"].nunique()
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


def plot_main(results: pd.DataFrame, figure_dir: Path) -> None:
    data = results[
        results["radius_km"].eq(20)
        & results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & results["severity_group"].eq("Injury accidents")
        & results["analysis_season"].eq("All seasons")
    ]
    colors = {"f": "#287271", "fg": "#C7522A", "fg_minus_f": "#5B5F97"}
    fig, axes = plt.subplots(3, 1, figsize=(12.5, 13), constrained_layout=True)
    for ax, spec in zip(axes, VARIABLES, strict=True):
        subset = data[data["variable"].eq(spec.variable)].sort_values("bin_order")
        x = np.arange(len(subset))
        y = subset["relative_accident_frequency"].to_numpy(float)
        low = subset["ci_95_low"].to_numpy(float)
        high = subset["ci_95_high"].to_numpy(float)
        reliable = subset["observed_accidents"].ge(20).to_numpy()
        ax.bar(x, y, color=np.where(reliable, colors[spec.variable], "#A8A8A8"))
        ax.errorbar(
            x[reliable],
            y[reliable],
            yerr=np.vstack([y[reliable] - low[reliable], high[reliable] - y[reliable]]),
            fmt="none",
            ecolor="#222222",
            capsize=3,
        )
        ax.axhline(1, color="#222222", linestyle="--", linewidth=1)
        ax.set_xticks(x, subset["weather_bin"], rotation=35, ha="right")
        ax.set_ylabel("Observed / expected")
        ax.set_title(spec.title)
        ax.grid(axis="y", alpha=0.2)
        reliable_high = high[reliable & np.isfinite(high)]
        finite_y = y[np.isfinite(y)]
        ax.set_ylim(
            0,
            max(
                1.5,
                reliable_high.max(initial=1.2) * 1.12,
                finite_y.max(initial=1.2) * 1.12,
            ),
        )
    axes[-1].set_xlabel("Wind interval (m/s)")
    fig.suptitle(
        "Rural injury accidents relative to station-specific 10-minute wind frequency\n"
        "20 km radius; gray bins contain fewer than 20 accidents"
    )
    fig.savefig(figure_dir / "wind_risk_overview.png", dpi=240)
    plt.close(fig)


def plot_sensitivity(results: pd.DataFrame, figure_dir: Path) -> None:
    data = results[
        results["severity_group"].eq("Injury accidents")
        & results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & results["analysis_season"].eq("All seasons")
    ]
    colors = {10: "#287271", 20: "#C7522A", 30: "#5B5F97"}
    fig, axes = plt.subplots(3, 1, figsize=(12.5, 13), constrained_layout=True)
    for ax, spec in zip(axes, VARIABLES, strict=True):
        for radius in RADII:
            subset = data[
                data["variable"].eq(spec.variable) & data["radius_km"].eq(radius)
            ].sort_values("bin_order")
            ax.plot(
                np.arange(len(subset)),
                subset["relative_accident_frequency"],
                marker="o",
                linewidth=1.7,
                color=colors[radius],
                label=f"{radius} km",
            )
        ax.axhline(1, color="#222222", linestyle="--", linewidth=1)
        ax.set_xticks(np.arange(len(spec.bin_labels)), spec.bin_labels, rotation=35, ha="right")
        ax.set_ylabel("Observed / expected")
        ax.set_title(spec.title)
        ax.grid(axis="y", alpha=0.2)
        ax.legend()
    axes[-1].set_xlabel("Wind interval (m/s)")
    fig.suptitle("Sensitivity of 10-minute wind results to station radius")
    fig.savefig(figure_dir / "wind_risk_radius.png", dpi=240)
    plt.close(fig)


def plot_comparison(
    results: pd.DataFrame,
    figure_dir: Path,
    comparison_column: str,
    values: list[str],
    filename: str,
    title: str,
) -> None:
    data = results[
        results["variable"].eq("fg")
        & results["radius_km"].eq(20)
        & results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
    ]
    fixed_column = "analysis_season" if comparison_column == "severity_group" else "severity_group"
    fixed_value = "All seasons" if fixed_column == "analysis_season" else "Injury accidents"
    data = data[data[fixed_column].eq(fixed_value)]
    colors = ["#287271", "#C7522A", "#5B5F97", "#D9A441", "#6A994E"]
    fig, ax = plt.subplots(figsize=(12.5, 6.5), constrained_layout=True)
    for value, color in zip(values, colors):
        subset = data[data[comparison_column].eq(value)].sort_values("bin_order")
        ax.plot(
            np.arange(len(subset)),
            subset["relative_accident_frequency"],
            marker="o",
            linewidth=1.7,
            color=color,
            label=value,
        )
    fg_labels = next(spec.bin_labels for spec in VARIABLES if spec.variable == "fg")
    ax.axhline(1, color="#222222", linestyle="--", linewidth=1)
    ax.set_xticks(np.arange(len(fg_labels)), fg_labels, rotation=35, ha="right")
    ax.set_xlabel("Maximum wind gust interval (m/s)")
    ax.set_ylabel("Observed / expected")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.2)
    ax.legend()
    fig.savefig(figure_dir / filename, dpi=240)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Station-frequency-adjusted wind risk using cleaned 10-minute data."
    )
    parser.add_argument("--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("--frequency", type=Path, default=DEFAULT_FREQUENCY)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--details", type=Path, default=DEFAULT_DETAILS)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("--figures", type=Path, default=DEFAULT_FIGURES)
    parser.add_argument(
        "--diagnostic-figures",
        action="store_true",
        help="Also write the four detailed diagnostic plots.",
    )
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()

    accidents, frequency = load_data(
        args.accidents, args.frequency, args.start, args.end
    )
    results: list[pd.DataFrame] = []
    details: list[pd.DataFrame] = []
    coverage: list[dict[str, object]] = []
    for spec in VARIABLES:
        for radius in RADII:
            for severity in SEVERITIES:
                for analysis_season in ["All seasons", *SEASON_ORDER]:
                    result, detail, cover = one_analysis(
                        accidents,
                        frequency,
                        spec,
                        radius,
                        severity,
                        analysis_season,
                    )
                    results.append(result)
                    details.append(detail)
                    coverage.append(cover)

    # Tighter accident-to-observation timing is retained as a primary-gust
    # sensitivity only. The main analysis remains the nearest observation on
    # the 10-minute grid, whose maximum possible difference is five minutes.
    gust_spec = next(spec for spec in VARIABLES if spec.variable == "fg")
    for max_time in TIME_SENSITIVITY_MINUTES:
        result, detail, cover = one_analysis(
            accidents,
            frequency,
            gust_spec,
            20,
            "Injury accidents",
            "All seasons",
            max_time_difference_minutes=max_time,
        )
        results.append(result)
        details.append(detail)
        coverage.append(cover)

    result_table = pd.concat(results, ignore_index=True)
    detail_table = pd.concat(details, ignore_index=True)
    coverage_table = pd.DataFrame(coverage)
    total_check = (coverage_table["expected_sum"] - coverage_table["observed_sum"]).abs()
    if total_check.max() > 1e-6:
        raise SystemExit(
            f"Observed/expected total validation failed; max difference={total_check.max()}"
        )

    for path in (args.results, args.details, args.coverage, args.notes):
        path.parent.mkdir(parents=True, exist_ok=True)
    result_table.to_csv(args.results, index=False)
    detail_table.to_parquet(args.details, index=False, compression="zstd")
    coverage_table.to_csv(args.coverage, index=False)
    if args.diagnostic_figures:
        args.figures.mkdir(parents=True, exist_ok=True)
        plot_main(result_table, args.figures)
        plot_sensitivity(result_table, args.figures)
        plot_comparison(
            result_table,
            args.figures,
            "severity_group",
            list(SEVERITIES),
            "wind_risk_gust_by_severity.png",
            "Maximum wind gust results by accident severity (20 km)",
        )
        plot_comparison(
            result_table,
            args.figures,
            "analysis_season",
            SEASON_ORDER,
            "wind_risk_gust_by_season.png",
            "Maximum wind gust results by season (20 km)",
        )

    primary = result_table[
        result_table["radius_km"].eq(20)
        & result_table["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & result_table["severity_group"].eq("Injury accidents")
        & result_table["analysis_season"].eq("All seasons")
    ]
    notes = f"""10-minute wind-frequency-adjusted accident analysis
==================================================

Accidents: {args.accidents}
Background wind frequency: {args.frequency}
Accidents in input scope: {len(accidents):,}

Method
------
Within each weather-station/year/season group, observed accident counts in each
wind interval are compared with expected counts based on the fraction of all clean
10-minute measurements in that interval. Results are then aggregated:

R_j = sum_g A_jg / sum_g (A_g * T_jg / T_g)

R_j = 1 means accident occurrence matches the background wind frequency. R_j above
1 means accidents are over-represented in that wind interval. It is a descriptive
relative accident frequency, not a causal risk estimate. Traffic volume is not
included.

Primary specification
---------------------
- Rural injury accidents, 2007-2024
- Maximum station distance: 20 km
- Variables: f, fg and max(fg-f, 0)
- Background controlled by station, calendar year and season
- Exact Poisson 95% intervals; bins with fewer than 20 accidents marked sparse

Validation
----------
- Analysis scenarios: {len(coverage_table):,}
- Maximum absolute difference between total observed and total expected accidents:
  {total_check.max():.12f}

Primary results
---------------
{primary[['variable', 'weather_bin', 'observed_accidents', 'expected_accidents', 'relative_accident_frequency', 'ci_95_low', 'ci_95_high', 'sparse_bin']].to_string(index=False)}

Limitations
-----------
- Weather-station measurements are proxies for conditions at the accident site.
- Missing measurements may not be random, especially during severe weather.
- No non-accident road traffic is in this ratio. Wind can change travel demand.
- Repeated bins and comparisons are exploratory; individual high-wind bins are sparse.
- The wind-quality rules are 0 <= f < 45 m/s and 0 <= fg < 65 m/s. Negative
  values and values at or above either upper bound are excluded and reported
  in the weather-cleaning audit.
  rules and are reported explicitly in the coverage table.
"""
    args.notes.write_text(notes, encoding="utf-8")
    print(f"wrote={args.results} rows={len(result_table):,}")
    print(f"wrote={args.details} rows={len(detail_table):,}")
    print(primary.to_string(index=False))


if __name__ == "__main__":
    main()
