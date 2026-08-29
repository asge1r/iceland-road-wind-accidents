"""Create O/E result tables with station-clustered bootstrap intervals."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.weather.frequency import (
    FG_UPPER_BOUNDS,
    F_UPPER_BOUNDS,
    TEMPERATURE_LABELS,
    labels,
)


DEFAULT_DETAILS = Path("reports/working/tables/oe_station_bins.csv")
DEFAULT_COVERAGE = Path("archive/generated_diagnostics/oe/coverage.csv")
ACCIDENT_MATCH_COVERAGE = Path(
    "archive/generated_diagnostics/oe/accident_weather_coverage.csv"
)
DEFAULT_OUTPUT_DIR = Path("reports/main/tables")
DEFAULT_SUBGROUP_OUTPUT = Path("reports/working/tables/mean_wind_subgroups.csv")
DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_WEATHER_CLEANING = Path(
    "archive/generated_diagnostics/weather_cleaning_by_year.csv"
)
PRIMARY_MAX_TIME_DIFFERENCE_MINUTES = 5
PRIMARY_VARIABLE = "f"

VARIABLE_LABELS = {
    "f": "Mean wind speed",
    "fg": "Wind gust at matched accident time",
    "temperature": "Temperature",
}
VARIABLE_COLORS = {"f": "#287271", "fg": "#C7522A", "temperature": "#555555"}
VARIABLE_XLABELS = {
    "f": "Mean wind-speed interval, f (m/s)",
    "fg": "Wind-gust interval at matched time, fg (m/s)",
    "temperature": "Temperature interval (°C)",
}
COARSE_BINS = {
    "f": {value: value for value in labels(F_UPPER_BOUNDS)},
    "fg": {value: value for value in labels(FG_UPPER_BOUNDS)},
    "temperature": {
        value: value for value in TEMPERATURE_LABELS
    },
}
BIN_ORDER = {
    "f": labels(F_UPPER_BOUNDS),
    "fg": labels(FG_UPPER_BOUNDS),
    "temperature": TEMPERATURE_LABELS,
}
def prepare_details(path: Path) -> pd.DataFrame:
    details = pd.read_csv(path)
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


def read_accidents(path: Path, columns: list[str]) -> pd.DataFrame:
    if path.suffix != ".csv":
        raise ValueError(f"Analysis input must be a CSV file: {path}")
    return pd.read_csv(path, usecols=columns)


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


def write_weather_coverage(
    accidents_path: Path,
    conditions_path: Path,
    cleaning_path: Path,
    output_path: Path,
) -> pd.DataFrame:
    """Write one audit table for accident matching and weather cleaning."""
    events = read_accidents(accidents_path, ["id"])
    conditions = read_accidents(
        conditions_path,
        [
            "id",
            "weather_station_id",
            "weather_station_dist_km",
            "weather_time_difference_minutes",
            "f",
            "fg",
        ],
    )
    accidents = events.merge(conditions, on="id", how="left", validate="one_to_one")
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
        "Primary accident population, 2007-2025.",
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


def write_thesis_outputs(
    primary: pd.DataFrame,
    risk_coverage: pd.DataFrame,
    output_dir: Path,
) -> None:
    primary_data = primary[primary["variable"].eq(PRIMARY_VARIABLE)].sort_values("bin_order").copy()
    thesis = primary_data[
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
            "coarse_bin": "mean_wind_interval_ms",
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
    thesis.to_csv(output_dir / "mean_wind_oe.csv", index=False)
    for variable, filename, interval_column in [
        ("fg", "gust_oe.csv", "gust_interval_ms"),
        ("temperature", "temperature_oe.csv", "temperature_interval_c"),
    ]:
        secondary = primary[primary["variable"].eq(variable)].sort_values("bin_order")[
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
                "coarse_bin": interval_column,
                "relative_accident_frequency": "observed_expected_ratio",
                "bootstrap_ci_95_low": "station_bootstrap_ci_95_low",
                "bootstrap_ci_95_high": "station_bootstrap_ci_95_high",
            }
        )
        secondary["expected_accidents"] = secondary["expected_accidents"].round(1)
        for column in [
            "observed_expected_ratio",
            "station_bootstrap_ci_95_low",
            "station_bootstrap_ci_95_high",
        ]:
            secondary[column] = secondary[column].round(2)
        secondary["sparse_bin_fewer_than_20_accidents"] = secondary[
            "observed_accidents"
        ].lt(20)
        secondary.to_csv(output_dir / filename, index=False)
    primary_coverage = risk_coverage[
        risk_coverage["variable"].eq(PRIMARY_VARIABLE)
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




def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finalize coarse wind-risk curves with station-cluster bootstrap intervals."
    )
    parser.add_argument("-d", "--details", type=Path, default=DEFAULT_DETAILS)
    parser.add_argument("-c", "--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-g", "--subgroup-output", type=Path, default=DEFAULT_SUBGROUP_OUTPUT)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-C", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument(
        "-w", "--weather-cleaning", type=Path, default=DEFAULT_WEATHER_CLEANING
    )
    parser.add_argument("-b", "--bootstrap-reps", type=int, default=5000)
    parser.add_argument("-s", "--seed", type=int, default=20260719)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    details = prepare_details(args.details)
    coverage = pd.read_csv(args.coverage)
    results: list[pd.DataFrame] = []
    scenarios: list[tuple[str, int, str, str]] = []
    for variable in VARIABLE_LABELS:
        for radius in [10, 20, 30]:
            scenarios.append((variable, radius, "Injury accidents", "All seasons"))
        for severity in ["Serious or fatal", "Fatal"]:
            scenarios.append((variable, 20, severity, "All seasons"))
        for season in ["Winter", "Spring", "Summer", "Fall"]:
            scenarios.append((variable, 20, "Injury accidents", season))
    for vehicle_group in ["1 vehicle", "2 or more vehicles"]:
        for variable in ["f", "fg"]:
            scenarios.append((variable, 20, vehicle_group, "All seasons"))

    for scenario_index, (variable, radius, severity, season) in enumerate(scenarios):
        result, _ = analyse_scenario(
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

    all_results = pd.concat(results, ignore_index=True)
    all_results.to_csv(args.output_dir / "oe_results.csv", index=False)
    primary = all_results[
        all_results["radius_km"].eq(20)
        & all_results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & all_results["severity_group"].eq("Injury accidents")
        & all_results["analysis_season"].eq("All seasons")
    ].copy()
    subgroup = all_results[
        all_results["variable"].isin(["f", "fg"])
        & all_results["radius_km"].eq(20)
        & all_results["max_time_difference_minutes"].eq(
            PRIMARY_MAX_TIME_DIFFERENCE_MINUTES
        )
        & (
            (
                all_results["severity_group"].eq("Injury accidents")
                & all_results["analysis_season"].isin(["Winter", "Spring", "Summer", "Fall"])
            )
            | (
                all_results["severity_group"].isin(["1 vehicle", "2 or more vehicles"])
                & all_results["analysis_season"].eq("All seasons")
            )
        )
    ].copy()
    args.subgroup_output.parent.mkdir(parents=True, exist_ok=True)
    subgroup.to_csv(args.subgroup_output, index=False)

    write_thesis_outputs(
        primary,
        coverage,
        args.output_dir,
    )

    write_weather_coverage(
        args.accidents,
        args.conditions,
        args.weather_cleaning,
        args.output_dir / "weather_cleaning_audit.csv",
    )

    print(f"scenarios={len(scenarios)} bootstrap_reps={args.bootstrap_reps:,}")
    print(primary.to_string(index=False))


if __name__ == "__main__":
    main()
