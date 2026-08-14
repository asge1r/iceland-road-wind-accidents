"""Create the main figure, thesis table, and station-clustered intervals."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.weather.frequency import FG_UPPER_BOUNDS, F_UPPER_BOUNDS, labels


DEFAULT_DETAILS = Path(
    "data/processed/accidents/oe_station_period_bins.parquet"
)
DEFAULT_COVERAGE = Path("archive/generated_diagnostics/oe/coverage.csv")
ACCIDENT_MATCH_COVERAGE = Path(
    "archive/generated_diagnostics/oe/accident_weather_coverage.csv"
)
DEFAULT_OUTPUT_DIR = Path("reports/main/tables")
DEFAULT_FIGURE_DIR = Path("reports/main/figures")
DEFAULT_ACCIDENTS = Path("data/processed/accidents/rural_injury_accidents.parquet")
DEFAULT_WEATHER_CLEANING = Path(
    "archive/generated_diagnostics/weather_cleaning_by_year.csv"
)
PRIMARY_MAX_TIME_DIFFERENCE_MINUTES = 5

VARIABLE_LABELS = {
    "f": "Mean wind speed",
    "fg": "Maximum wind gust",
    "fg_minus_f": "Maximum gust minus mean wind speed",
}
VARIABLE_COLORS = {"f": "#287271", "fg": "#C7522A", "fg_minus_f": "#5B5F97"}
VARIABLE_XLABELS = {
    "f": "Mean wind-speed interval, f (m/s)",
    "fg": "Maximum wind-gust interval, fg (m/s)",
    "fg_minus_f": "Maximum gust minus mean wind speed, fg - f (m/s)",
}
COARSE_BINS = {
    "f": {value: value for value in labels(F_UPPER_BOUNDS)},
    "fg": {value: value for value in labels(FG_UPPER_BOUNDS)},
    "fg_minus_f": {
        "0-2": "0-4",
        "2-4": "0-4",
        "4-6": "4-8",
        "6-8": "4-8",
        "8-10": "8-12",
        "10-12": "8-12",
        "12-14": ">=12",
        "14-16": ">=12",
        "16-18": ">=12",
        "18-20": ">=12",
        ">=20": ">=12",
    },
}
BIN_ORDER = {
    "f": labels(F_UPPER_BOUNDS),
    "fg": labels(FG_UPPER_BOUNDS),
    "fg_minus_f": ["0-4", "4-8", "8-12", ">=12"],
}
FG_THREE_MS_BINS = {value: value for value in labels(FG_UPPER_BOUNDS)}
FG_THREE_MS_ORDER = labels(FG_UPPER_BOUNDS)


def prepare_details(path: Path) -> pd.DataFrame:
    details = pd.read_parquet(path)
    if "max_time_difference_minutes" not in details:
        details["max_time_difference_minutes"] = PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
    details["coarse_bin"] = pd.NA
    for variable, mapping in COARSE_BINS.items():
        mask = details["variable"].eq(variable)
        details.loc[mask, "coarse_bin"] = details.loc[mask, "weather_bin"].map(mapping)
    if details["coarse_bin"].isna().any():
        examples = details.loc[details["coarse_bin"].isna(), ["variable", "weather_bin"]]
        raise ValueError(f"Unmapped detailed wind bins: {examples.drop_duplicates().to_dict('records')}")
    return details


def cluster_bootstrap(
    station_bins: pd.DataFrame,
    variable: str,
    reps: int,
    seed: int,
    bins: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    bins = BIN_ORDER[variable] if bins is None else bins
    observed = (
        station_bins.pivot(index="weather_station_id", columns="coarse_bin", values="observed_accidents")
        .reindex(columns=bins, fill_value=0)
        .fillna(0)
    )
    expected = (
        station_bins.pivot(index="weather_station_id", columns="coarse_bin", values="expected_accidents")
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
    for frame in (draws,):
        frame["radius_km"] = radius
        frame["severity_group"] = severity
        frame["analysis_season"] = season
        frame["max_time_difference_minutes"] = max_time_difference_minutes
    return result, draws


def validate_totals(result: pd.DataFrame, expected_accidents: int) -> None:
    observed = int(result["observed_accidents"].sum())
    expected = float(result["expected_accidents"].sum())
    if observed != expected_accidents:
        raise ValueError(f"Coarse-bin accidents changed: {observed} != {expected_accidents}")
    if not np.isclose(expected, expected_accidents, atol=1e-6):
        raise ValueError(f"Coarse-bin expected total changed: {expected} != {expected_accidents}")


def plot_one_variable(data: pd.DataFrame, variable: str, path: Path) -> None:
    subset = data[data["variable"].eq(variable)].sort_values("bin_order")
    x = np.arange(len(subset))
    y = subset["relative_accident_frequency"].to_numpy(float)
    low = subset["bootstrap_ci_95_low"].to_numpy(float)
    high = subset["bootstrap_ci_95_high"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(14.5, 7.2), constrained_layout=True)
    sparse = subset["observed_accidents"].lt(20).to_numpy()
    colors = np.where(sparse, "#A7A7A7", VARIABLE_COLORS[variable])
    bars = ax.bar(x, y, color=colors, width=0.72)
    ax.errorbar(
        x,
        y,
        yerr=np.vstack([np.maximum(0, y - low), np.maximum(0, high - y)]),
        fmt="none",
        ecolor="#222222",
        capsize=4,
        linewidth=1.2,
    )
    ax.axhline(1, color="#222222", linestyle="--", linewidth=1)
    display_bins = subset["coarse_bin"].str.replace(">=", "≥", regex=False)
    ax.set_xticks(x, display_bins)
    ax.set_xlabel(VARIABLE_XLABELS[variable])
    ax.set_ylabel("Observed / expected accidents")
    ax.set_title(f"Accident occurrence by {VARIABLE_LABELS[variable].lower()}")
    ax.grid(axis="y", alpha=0.2)
    plot_top = max(1.5, np.nanmax(high) * 1.18)
    ax.set_ylim(0, plot_top)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def plot_primary_gust(data: pd.DataFrame, path: Path) -> None:
    """Plot the primary O/E result with observed and expected accident counts."""
    subset = data[data["variable"].eq("fg")].sort_values("bin_order")
    x = np.arange(len(subset))
    ratio = subset["relative_accident_frequency"].to_numpy(float)
    low = subset["bootstrap_ci_95_low"].to_numpy(float)
    high = subset["bootstrap_ci_95_high"].to_numpy(float)
    observed = subset["observed_accidents"].to_numpy(float)
    expected = subset["expected_accidents"].to_numpy(float)
    display_bins = subset["coarse_bin"].str.replace(">=", "≥", regex=False)

    figure, axes = plt.subplots(
        2,
        1,
        figsize=(14.5, 9.2),
        sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1]},
        constrained_layout=True,
    )
    ratio_axis, count_axis = axes
    ratio_axis.bar(x, ratio, color="#C7522A", width=0.72)
    ratio_axis.errorbar(
        x,
        ratio,
        yerr=np.vstack([np.maximum(0, ratio - low), np.maximum(0, high - ratio)]),
        fmt="none",
        ecolor="#222222",
        capsize=4,
        linewidth=1.2,
        label="95% bootstrap interval",
    )
    ratio_axis.axhline(1, color="#222222", linestyle="--", linewidth=1)
    ratio_axis.set_ylabel("Observed / expected accidents (O/E)")
    ratio_axis.set_title("Relative occurrence of rural injury accidents by maximum wind gust")
    ratio_axis.set_ylim(0, max(1.5, np.nanmax(high) * 1.14))
    ratio_axis.grid(axis="y", alpha=0.2)
    ratio_axis.legend(loc="upper left", frameon=False)

    width = 0.36
    observed_bars = count_axis.bar(
        x - width / 2,
        observed,
        width,
        color="#3F6C8C",
        label="Observed accidents",
    )
    count_axis.bar(
        x + width / 2,
        expected,
        width,
        color="#A8C2D1",
        label="Expected from local gust frequency",
    )
    count_axis.set_ylabel("Injury accidents (n)")
    count_axis.set_xlabel("Maximum wind-gust interval, fg (m/s)")
    count_axis.set_xticks(x, display_bins)
    count_axis.grid(axis="y", alpha=0.2)
    count_axis.legend(loc="upper right", frameon=False)
    count_axis.set_ylim(0, observed.max() * 1.14)
    label_offset = observed.max() * 0.018
    for bar, value in zip(observed_bars, observed, strict=True):
        count_axis.text(
            bar.get_x() + bar.get_width() / 2,
            value + label_offset,
            f"n={int(value)}",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#263238",
        )
    figure.savefig(path, dpi=240)
    plt.close(figure)


def plot_distribution_comparison(data: pd.DataFrame, path: Path) -> None:
    """Show observed counts, locally standardized expectation, and their ratio."""
    subset = data[data["variable"].eq("fg")].sort_values("bin_order").copy()
    subset["observed_pct"] = (
        100 * subset["observed_accidents"] / subset["observed_accidents"].sum()
    )
    subset["expected_pct"] = (
        100 * subset["expected_accidents"] / subset["expected_accidents"].sum()
    )
    x = np.arange(len(subset))
    labels = subset["coarse_bin"].str.replace(">=", "≥", regex=False)
    fig, axes = plt.subplots(3, 1, figsize=(14.5, 12), constrained_layout=True)

    axes[0].bar(x, subset["observed_accidents"], color="#577590")
    axes[0].set_ylabel("Observed accidents")
    axes[0].set_title("Observed accident count")

    width = 0.38
    axes[1].bar(
        x - width / 2,
        subset["observed_pct"],
        width,
        color="#577590",
        label="Observed accident share",
    )
    axes[1].bar(
        x + width / 2,
        subset["expected_pct"],
        width,
        color="#B8B8B8",
        label="Expected share from local wind frequency",
    )
    axes[1].set_ylabel("Share (%)")
    axes[1].set_title("Observed and locally expected distributions")
    axes[1].legend(frameon=False, ncol=2)

    ratio = subset["relative_accident_frequency"].to_numpy(float)
    low = subset["bootstrap_ci_95_low"].to_numpy(float)
    high = subset["bootstrap_ci_95_high"].to_numpy(float)
    axes[2].bar(x, ratio, color=VARIABLE_COLORS["fg"])
    axes[2].errorbar(
        x,
        ratio,
        yerr=np.vstack([np.maximum(0, ratio - low), np.maximum(0, high - ratio)]),
        fmt="none",
        ecolor="#222222",
        capsize=3,
    )
    axes[2].axhline(1, color="#222222", linestyle="--", linewidth=1)
    axes[2].set_ylabel("Observed / expected injury accidents (O/E ratio)")
    axes[2].set_title("Wind-frequency-standardized relative accident frequency")
    axes[2].set_xlabel(VARIABLE_XLABELS["fg"])
    axes[2].set_ylim(0, max(1.5, np.nanmax(high) * 1.12))

    for axis in axes:
        axis.set_xticks(x, labels)
        axis.grid(axis="y", alpha=0.2)
    axes[0].tick_params(labelbottom=False)
    axes[1].tick_params(labelbottom=False)
    fig.suptitle(
        "Why local wind-frequency standardization changes the interpretation\n"
        "Rural injury accidents, 2007–2024; traffic volume not included"
    )
    fig.savefig(path, dpi=240)
    plt.close(fig)


def write_weather_coverage(
    accidents_path: Path,
    cleaning_path: Path,
    output_path: Path,
) -> pd.DataFrame:
    """Write one audit table for accident matching and weather cleaning."""
    accidents = pd.read_parquet(
        accidents_path,
        columns=[
            "nid",
            "weather_station_id",
            "weather_station_dist_km",
            "weather_time_difference_minutes",
            "f",
            "fg",
        ],
    )
    total_accidents = len(accidents)
    valid_wind = accidents["f"].notna() & accidents["fg"].notna()
    rows: list[dict[str, object]] = []

    def accident_row(metric: str, mask: pd.Series, note: str) -> None:
        count = int(mask.sum())
        rows.append(
            {
                "unit": "accidents",
                "metric": metric,
                "value": count,
                "percent_of_input": 100 * count / total_accidents,
                "note": note,
            }
        )

    accident_row(
        "rural_injury_accidents_in_scope",
        pd.Series(True, index=accidents.index),
        "Primary accident population, 2007-2024.",
    )
    accident_row(
        "valid_wind_within_10_km",
        valid_wind & accidents["weather_station_dist_km"].le(10),
        "Spatial sensitivity.",
    )
    accident_row(
        "valid_wind_within_20_km",
        valid_wind & accidents["weather_station_dist_km"].le(20),
        "Primary spatial criterion.",
    )
    accident_row(
        "valid_wind_within_30_km",
        valid_wind & accidents["weather_station_dist_km"].le(30),
        "Loose spatial sensitivity only.",
    )
    for minutes in [0, 2, 5]:
        accident_row(
            f"valid_wind_within_20_km_and_{minutes}_minute_difference",
            valid_wind
            & accidents["weather_station_dist_km"].le(20)
            & accidents["weather_time_difference_minutes"].le(minutes),
            "Time-match sensitivity; <=5 minutes is primary.",
        )
    primary = valid_wind & accidents["weather_station_dist_km"].le(20)
    rows.append(
        {
            "unit": "weather_stations",
            "metric": "stations_in_primary_accident_analysis",
            "value": int(accidents.loc[primary, "weather_station_id"].nunique()),
            "percent_of_input": np.nan,
            "note": "Distinct stations assigned to primary accidents.",
        }
    )

    cleaning = pd.read_csv(cleaning_path)
    # The audit has an explicit total row. Exclude it before reporting
    # otherwise every weather count would be doubled.
    cleaning = cleaning[cleaning["year"].astype(str).ne("total")].copy()
    input_rows = int(cleaning["input_rows"].sum())
    measurement_metrics = [
        ("raw_10_minute_rows", "input_rows", "Raw weather observations."),
        (
            "station_year_without_wind_data",
            "no_wind_station_year",
            "Station-time rows from station-years with no wind values.",
        ),
        (
            "missing_wind_in_wind_capable_station_year",
            "missing_wind",
            "Missing f or fg within a station-year that otherwise measures wind.",
        ),
        ("negative_wind_values", "negative", "Invalid negative f or fg value."),
        ("f_below_zero_ms", "negative_f", "Reported negative mean-wind value."),
        ("fg_below_zero_ms", "negative_fg", "Reported negative gust value."),
        ("f_at_or_above_45_ms", "f_at_or_above_45", "Operational upper threshold."),
        ("fg_at_or_above_65_ms", "fg_at_or_above_65", "Operational upper threshold."),
        ("fg_equal_zero_ms", "fg_zero_rows", "Reported separately; gusts of zero are unusual."),
        (
            "fg_zero_with_positive_f",
            "fg_zero_with_positive_f",
            "Internally inconsistent zero gust; excluded.",
        ),
        (
            "fg_below_f_beyond_tolerance",
            "gust_below_mean",
            "Failed internal wind consistency rule.",
        ),
        ("frozen_zero_runs", "frozen_zero", "Both f and fg equal zero for at least two hours."),
        ("clean_wind_rows", "clean_wind_rows", "Rows retained with valid f and fg."),
    ]
    for metric, column, note in measurement_metrics:
        value = int(cleaning[column].sum())
        rows.append(
            {
                "unit": "10_minute_weather_rows",
                "metric": metric,
                "value": value,
                "percent_of_input": 100 * value / input_rows,
                "note": note,
            }
        )
    clean_rows = int(cleaning["clean_wind_rows"].sum())
    rows.append(
        {
            "unit": "10_minute_weather_rows",
            "metric": "weather_rows_excluded_total",
            "value": input_rows - clean_rows,
            "percent_of_input": 100 * (input_rows - clean_rows) / input_rows,
            "note": "Exclusive total removed by all wind-cleaning rules combined.",
        }
    )
    coverage = pd.DataFrame(rows)
    coverage["percent_of_input"] = coverage["percent_of_input"].round(2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(output_path, index=False)
    return coverage


def plot_supporting(data: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10.8, 10.5), constrained_layout=True)
    for ax, variable in zip(axes, ["f", "fg_minus_f"], strict=True):
        subset = data[data["variable"].eq(variable)].sort_values("bin_order")
        x = np.arange(len(subset))
        y = subset["relative_accident_frequency"].to_numpy(float)
        low = subset["bootstrap_ci_95_low"].to_numpy(float)
        high = subset["bootstrap_ci_95_high"].to_numpy(float)
        ax.bar(x, y, color=VARIABLE_COLORS[variable], width=0.72)
        ax.errorbar(
            x,
            y,
            yerr=np.vstack([np.maximum(0, y - low), np.maximum(0, high - y)]),
            fmt="none",
            ecolor="#222222",
            capsize=4,
        )
        ax.axhline(1, color="#222222", linestyle="--", linewidth=1)
        display_bins = subset["coarse_bin"].str.replace(">=", "≥", regex=False)
        ax.set_xticks(x, display_bins)
        ax.set_ylabel("Observed / expected")
        ax.set_title(VARIABLE_LABELS[variable])
        ax.grid(axis="y", alpha=0.2)
        ax.set_ylim(0, max(1.5, np.nanmax(high) * 1.13))
    axes[-1].set_xlabel("Wind interval (m/s)")
    fig.suptitle(
        "Supporting wind measures and rural injury accidents\n"
        "20 km radius; 95% weather-station cluster bootstrap intervals"
    )
    fig.savefig(path, dpi=240)
    plt.close(fig)


def write_thesis_outputs(
    primary: pd.DataFrame,
    radius: pd.DataFrame,
    severity: pd.DataFrame,
    risk_coverage: pd.DataFrame,
    time_sensitivity: pd.DataFrame,
    bin_width_sensitivity: pd.DataFrame,
    output_dir: Path,
) -> None:
    def format_is(value: float, digits: int = 2) -> str:
        return f"{value:.{digits}f}".replace(".", ",")

    gust = primary[primary["variable"].eq("fg")].sort_values("bin_order").copy()
    thesis = gust[
        [
            "coarse_bin",
            "observed_accidents",
            "expected_accidents",
            "relative_accident_frequency",
            "bootstrap_ci_95_low",
            "bootstrap_ci_95_high",
            "bootstrap_probability_above_1",
        ]
    ].rename(
        columns={
            "coarse_bin": "wind_gust_interval_ms",
            "relative_accident_frequency": "observed_expected_ratio",
            "bootstrap_ci_95_low": "station_bootstrap_ci_95_low",
            "bootstrap_ci_95_high": "station_bootstrap_ci_95_high",
        }
    )
    thesis["expected_accidents"] = thesis["expected_accidents"].round(1)
    for column in [
        "observed_expected_ratio",
        "station_bootstrap_ci_95_low",
        "station_bootstrap_ci_95_high",
    ]:
        thesis[column] = thesis[column].round(2)
    thesis["sparse_bin_fewer_than_20_accidents"] = thesis[
        "observed_accidents"
    ].lt(20)
    thesis.to_csv(output_dir / "gust_oe.csv", index=False)
    display = thesis.rename(
        columns={
            "wind_gust_interval_ms": "Wind gust (m/s)",
            "observed_accidents": "Observed",
            "expected_accidents": "Expected",
            "observed_expected_ratio": "Observed/expected",
            "station_bootstrap_ci_95_low": "95% CI low",
            "station_bootstrap_ci_95_high": "95% CI high",
        }
    )
    latex_lines = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Wind gust (m/s) & Observed & Expected & Observed/expected & 95\% CI low & 95\% CI high \\",
        r"\midrule",
    ]
    for row in thesis.itertuples(index=False):
        interval = (
            r"$\geq 36$" if row.wind_gust_interval_ms == ">=36" else row.wind_gust_interval_ms
        )
        latex_lines.append(
            f"{interval} & {int(row.observed_accidents)} & "
            f"{row.expected_accidents:.1f} & {row.observed_expected_ratio:.2f} & "
            f"{row.station_bootstrap_ci_95_low:.2f} & "
            f"{row.station_bootstrap_ci_95_high:.2f} " + r"\\"
        )
    latex_lines.extend([r"\bottomrule", r"\end{tabular}"])
    diagnostic_dir = Path("archive/generated_diagnostics")
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    (diagnostic_dir / "gust_risk.tex").write_text(
        "\n".join(latex_lines) + "\n", encoding="utf-8"
    )

    primary_coverage = risk_coverage[
        risk_coverage["variable"].eq("fg")
        & risk_coverage["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & risk_coverage["severity_group"].eq("Injury accidents")
        & risk_coverage["analysis_season"].eq("All seasons")
    ][["radius_km", "eligible_accidents", "analysed_accidents"]].copy()
    if ACCIDENT_MATCH_COVERAGE.exists():
        match_coverage = pd.read_csv(ACCIDENT_MATCH_COVERAGE)
        scope_accidents = int(match_coverage["scope_accidents"].max())
    else:
        scope_accidents = 6120
    primary_coverage.insert(1, "scope_accidents", scope_accidents)
    primary_coverage["coverage_pct"] = (
        100 * primary_coverage["analysed_accidents"] / scope_accidents
    )
    primary_coverage.to_csv(
        output_dir / "weather_match_coverage.csv", index=False
    )

    high_bins = {"f": ">=24", "fg": ">=36", "fg_minus_f": ">=12"}
    sensitivity_rows = []
    for variable, coarse_bin in high_bins.items():
        selected = radius[
            radius["variable"].eq(variable) & radius["coarse_bin"].eq(coarse_bin)
        ]
        for row in selected.itertuples():
            sensitivity_rows.append(
                {
                    "comparison": "station_radius",
                    "level": f"{row.radius_km} km",
                    "variable": variable,
                    "wind_interval_ms": coarse_bin,
                    "observed_accidents": row.observed_accidents,
                    "observed_expected_ratio": row.relative_accident_frequency,
                    "station_bootstrap_ci_95_low": row.bootstrap_ci_95_low,
                    "station_bootstrap_ci_95_high": row.bootstrap_ci_95_high,
                }
            )
        selected = severity[
            severity["variable"].eq(variable)
            & severity["coarse_bin"].eq(coarse_bin)
            & severity["radius_km"].eq(20)
        ]
        for row in selected.itertuples():
            sensitivity_rows.append(
                {
                    "comparison": "accident_severity",
                    "level": row.severity_group,
                    "variable": variable,
                    "wind_interval_ms": coarse_bin,
                    "observed_accidents": row.observed_accidents,
                    "observed_expected_ratio": row.relative_accident_frequency,
                    "station_bootstrap_ci_95_low": row.bootstrap_ci_95_low,
                    "station_bootstrap_ci_95_high": row.bootstrap_ci_95_high,
                }
            )
    selected_time = time_sensitivity[
        time_sensitivity["variable"].eq("fg")
        & time_sensitivity["coarse_bin"].eq(">=36")
    ]
    for row in selected_time.itertuples():
        sensitivity_rows.append(
            {
                "comparison": "maximum_time_difference",
                "level": f"<= {row.max_time_difference_minutes:g} minutes",
                "variable": "fg",
                "wind_interval_ms": ">=36",
                "observed_accidents": row.observed_accidents,
                "observed_expected_ratio": row.relative_accident_frequency,
                "station_bootstrap_ci_95_low": row.bootstrap_ci_95_low,
                "station_bootstrap_ci_95_high": row.bootstrap_ci_95_high,
            }
        )
    sensitivity_table = pd.DataFrame(sensitivity_rows)
    numeric = [
        "observed_expected_ratio",
        "station_bootstrap_ci_95_low",
        "station_bootstrap_ci_95_high",
    ]
    sensitivity_table[numeric] = sensitivity_table[numeric].round(2)
    sensitivity_table.to_csv(
        diagnostic_dir / "gust_sensitivity.csv", index=False
    )
    bin_width_output = bin_width_sensitivity[
        [
            "coarse_bin",
            "observed_accidents",
            "expected_accidents",
            "relative_accident_frequency",
            "bootstrap_ci_95_low",
            "bootstrap_ci_95_high",
        ]
    ].rename(columns={"coarse_bin": "wind_gust_interval_ms"})
    bin_width_output[
        [
            "expected_accidents",
            "relative_accident_frequency",
            "bootstrap_ci_95_low",
            "bootstrap_ci_95_high",
        ]
    ] = bin_width_output[
        [
            "expected_accidents",
            "relative_accident_frequency",
            "bootstrap_ci_95_low",
            "bootstrap_ci_95_high",
        ]
    ].round(2)
    bin_width_output.to_csv(
        diagnostic_dir / "gust_bins.csv", index=False
    )

    fg_rows = gust.set_index("coarse_bin")
    high = fg_rows.loc[">=36"]
    thesis_text = f"""# Suggested method and results text

## Method

Rural injury accidents in 2007–2024 were matched to the nearest valid
10-minute wind observation within 20 km. For each weather station, calendar
year, and season, the observed number of accidents in each gust interval was
compared with the expected number based on the share of all cleaned 10-minute
observations in that interval. The pooled ratio is therefore the observed
accident count divided by the expected count after standardization for local
wind frequency.

Uncertainty was estimated with a weather-station-clustered bootstrap. Stations
were sampled with replacement 5,000 times, and all observations and accidents
associated with a station remained together in each sample. The 95% confidence
limits were the 2.5th and 97.5th percentiles of the bootstrap distribution.
Maximum gust was grouped into 3 m/s intervals from 0–3 through 33–36 m/s,
with an open-ended interval for ≥36 m/s. Mean wind used 3 m/s intervals from
0–3 through 21–24 m/s, with an open-ended interval for ≥24 m/s.

## Results

The curve shows the observed/expected ratio for each 3 m/s gust interval.
The strongest overrepresentation occurred at gusts ≥36 m/s, where
{int(high['observed_accidents'])} accidents were observed compared with
{high['expected_accidents']:.1f} expected. The ratio was
{high['relative_accident_frequency']:.2f} (95% station-clustered confidence
interval {high['bootstrap_ci_95_low']:.2f}–{high['bootstrap_ci_95_high']:.2f}).

## Limitations

The ratios are descriptive observed/expected measures, not causal effects.
A weather station is a proxy for conditions at the accident location, and
local terrain may cause differences within 20 km. The station-clustered
bootstrap accounts for repeated observations within stations but does not
adjust for traffic volume, potentially non-random gaps in weather data, or
multiple comparisons. Consequently, the result measures accident occurrence
relative to wind frequency, not risk per vehicle or vehicle-kilometre. Hourly
traffic exposure can be incorporated later without changing this primary
weather-standardization analysis.
"""
    (diagnostic_dir / "gust_method.md").write_text(
        thesis_text, encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finalize coarse wind-risk curves with station-cluster bootstrap intervals."
    )
    parser.add_argument("-d", "--details", type=Path, default=DEFAULT_DETAILS)
    parser.add_argument("-c", "--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-f", "--figure-dir", type=Path, default=DEFAULT_FIGURE_DIR)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument(
        "-w", "--weather-cleaning", type=Path, default=DEFAULT_WEATHER_CLEANING
    )
    parser.add_argument("-b", "--bootstrap-reps", type=int, default=5000)
    parser.add_argument("-s", "--seed", type=int, default=20260719)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    details = prepare_details(args.details)
    coverage = pd.read_csv(args.coverage)
    results: list[pd.DataFrame] = []
    primary_draws: list[pd.DataFrame] = []

    scenarios: list[tuple[str, int, str, str]] = []
    for variable in VARIABLE_LABELS:
        for radius in [10, 20, 30]:
            scenarios.append((variable, radius, "Injury accidents", "All seasons"))
        for severity in ["Serious or fatal", "Fatal"]:
            scenarios.append((variable, 20, severity, "All seasons"))
        for season in ["Winter", "Spring", "Summer", "Fall"]:
            scenarios.append((variable, 20, "Injury accidents", season))

    for scenario_index, (variable, radius, severity, season) in enumerate(scenarios):
        result, draws = analyse_scenario(
            details,
            variable,
            radius,
            severity,
            season,
            args.bootstrap_reps,
            args.seed + scenario_index,
            max_time_difference_minutes=PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
        )
        expected_total = int(
            coverage[
                coverage["variable"].eq(variable)
                & coverage["radius_km"].eq(radius)
                & coverage["severity_group"].eq(severity)
                & coverage["analysis_season"].eq(season)
                & coverage["max_time_difference_minutes"].eq(
                    PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
                )
            ]["observed_sum"].iloc[0]
        )
        validate_totals(result, expected_total)
        results.append(result)
        if radius == 20 and severity == "Injury accidents" and season == "All seasons":
            primary_draws.append(draws)

    all_results = pd.concat(results, ignore_index=True)
    primary = all_results[
        all_results["radius_km"].eq(20)
        & all_results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & all_results["severity_group"].eq("Injury accidents")
        & all_results["analysis_season"].eq("All seasons")
    ].copy()
    radius = all_results[
        all_results["severity_group"].eq("Injury accidents")
        & all_results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & all_results["analysis_season"].eq("All seasons")
    ].copy()
    severity = all_results[
        all_results["radius_km"].eq(20)
        & all_results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & all_results["analysis_season"].eq("All seasons")
    ].copy()
    season = all_results[
        all_results["radius_km"].eq(20)
        & all_results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & all_results["severity_group"].eq("Injury accidents")
    ].copy()

    supporting_dir = Path("archive/generated_diagnostics")
    supporting_dir.mkdir(parents=True, exist_ok=True)

    time_results = []
    for time_index, max_time in enumerate([0, 2]):
        result, _ = analyse_scenario(
            details,
            "fg",
            20,
            "Injury accidents",
            "All seasons",
            args.bootstrap_reps,
            args.seed + 100 + time_index,
            max_time_difference_minutes=max_time,
        )
        expected_total = int(
            coverage[
                coverage["variable"].eq("fg")
                & coverage["radius_km"].eq(20)
                & coverage["severity_group"].eq("Injury accidents")
                & coverage["analysis_season"].eq("All seasons")
                & coverage["max_time_difference_minutes"].eq(max_time)
            ]["observed_sum"].iloc[0]
        )
        validate_totals(result, expected_total)
        time_results.append(result)
    time_results.append(primary[primary["variable"].eq("fg")].copy())
    time_sensitivity = pd.concat(time_results, ignore_index=True)

    bin_width_sensitivity, _ = analyse_scenario(
        details,
        "fg",
        20,
        "Injury accidents",
        "All seasons",
        args.bootstrap_reps,
        args.seed + 200,
        max_time_difference_minutes=PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
        bin_mapping=FG_THREE_MS_BINS,
        bin_order=FG_THREE_MS_ORDER,
    )
    # A different bin width must retain exactly the current primary sample.
    # Do not hard-code an old accident count: valid weather cleaning rules can
    # legitimately change the matched sample while preserving this invariant.
    primary_fg_total = int(
        primary.loc[primary["variable"].eq("fg"), "observed_accidents"].sum()
    )
    validate_totals(bin_width_sensitivity, primary_fg_total)

    write_thesis_outputs(
        primary,
        radius,
        severity,
        coverage,
        time_sensitivity,
        bin_width_sensitivity,
        args.output_dir,
    )

    plot_primary_gust(
        primary,
        args.figure_dir / "gust_oe.png",
    )
    plot_one_variable(
        primary,
        "f",
        supporting_dir / "mean_wind_accident_frequency.png",
    )
    plot_one_variable(
        primary,
        "fg_minus_f",
        Path("archive/generated_diagnostics/gust_variability_accident_frequency.png"),
    )
    plot_distribution_comparison(
        primary,
        supporting_dir / "wind_gust_distribution_and_standardization.png",
    )

    gust_distribution = primary[primary["variable"].eq("fg")].copy()
    gust_distribution["observed_share_pct"] = (
        100
        * gust_distribution["observed_accidents"]
        / gust_distribution["observed_accidents"].sum()
    )
    gust_distribution["expected_share_pct"] = (
        100
        * gust_distribution["expected_accidents"]
        / gust_distribution["expected_accidents"].sum()
    )
    gust_distribution[
        [
            "coarse_bin",
            "observed_accidents",
            "observed_share_pct",
            "expected_accidents",
            "expected_share_pct",
            "relative_accident_frequency",
        ]
    ].rename(columns={"coarse_bin": "wind_gust_interval_ms"}).to_csv(
        supporting_dir / "wind_gust_distribution_and_standardization.csv",
        index=False,
    )
    weather_coverage = write_weather_coverage(
        args.accidents,
        args.weather_cleaning,
        args.output_dir / "weather_cleaning_audit.csv",
    )

    notes = f"""Final wind-risk curve method
============================

Input: {args.details}
Primary population: rural injury accidents, 2007-2024
Primary station radius: 20 km
Bootstrap resamples: {args.bootstrap_reps:,}
Random seed: {args.seed}

Coarse bins
-----------
- f: {', '.join(BIN_ORDER['f'])} m/s
- fg: {', '.join(BIN_ORDER['fg'])} m/s
- fg-f: {', '.join(BIN_ORDER['fg_minus_f'])} m/s

The point estimate remains observed accidents divided by expected accidents after
standardizing the background frequency within station, calendar year and season.
For uncertainty, entire weather stations are sampled with replacement. Every
station/year/season/bin contribution belonging to a sampled station is retained,
so spatial clustering and repeated accidents assigned to the same station remain
together. The 2.5th and 97.5th percentiles of the bootstrap distribution form the
95% interval. The seed makes the result reproducible.

This is a descriptive standardized observed/expected curve, not a causal effect.
The bootstrap addresses station clustering but does not correct traffic exposure,
non-random weather missingness, station-to-crash spatial error or multiple testing.
The supporting outputs compare raw accident counts with the locally expected
distribution, test 10/20/30 km radii, 0/2/5 minute timing, serious/fatal outcomes,
4 m/s gust bins, mean wind speed, and fg-f. None of these replaces the primary
20 km, <=5 minute, 2 m/s maximum-gust specification.

Primary results
---------------
{primary[['variable', 'coarse_bin', 'observed_accidents', 'expected_accidents', 'relative_accident_frequency', 'bootstrap_ci_95_low', 'bootstrap_ci_95_high', 'bootstrap_probability_above_1']].to_string(index=False)}

Coverage and exclusions
-----------------------
{weather_coverage.to_string(index=False)}
"""
    (Path("archive/generated_diagnostics/oe") / "bootstrap_notes.txt").write_text(
        notes, encoding="utf-8"
    )
    print(f"scenarios={len(scenarios)} bootstrap_reps={args.bootstrap_reps:,}")
    print(primary.to_string(index=False))


if __name__ == "__main__":
    main()
