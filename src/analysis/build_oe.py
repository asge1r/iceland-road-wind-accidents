"""Calculate frequency-adjusted observed/expected ratios for defined samples."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

from src.weather.frequency import (
    FG_UPPER_BOUNDS,
    F_UPPER_BOUNDS,
    TEMPERATURE_UPPER_BOUNDS,
    TEMPERATURE_LABELS,
    labels,
)


DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_FREQUENCY = Path("data/analysis/weather_frequency.csv")
DEFAULT_RESULTS = Path("archive/generated_diagnostics/oe/detailed_results.csv")
DEFAULT_DETAILS = Path("reports/working/tables/oe_station_bins.csv")
DEFAULT_COVERAGE = Path("archive/generated_diagnostics/oe/coverage.csv")
DEFAULT_NOTES = Path("archive/generated_diagnostics/oe/calculation_notes.txt")

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
    VariableSpec(
        "f",
        "f",
        F_UPPER_BOUNDS,
        "Mean wind speed",
    ),
    VariableSpec(
        "fg",
        "fg",
        FG_UPPER_BOUNDS,
        "Wind gust at matched observation time",
    ),
    VariableSpec(
        "temperature",
        "temperature_c",
        TEMPERATURE_UPPER_BOUNDS,
        "Temperature",
        station_column="temp_station_id",
        distance_column="temp_distance_km",
        time_difference_column="temp_time_diff_min",
        custom_bin_labels=tuple(TEMPERATURE_LABELS),
        custom_bin_edges=(-np.inf, *TEMPERATURE_UPPER_BOUNDS, np.inf),
    ),
]
SAMPLES = {
    "Injury accidents": lambda data: pd.Series(True, index=data.index),
    "Serious or fatal": lambda data: data["meidsli"].le(2),
    "Fatal": lambda data: data["meidsli"].eq(1),
    "1 vehicle": lambda data: data["vehicle_group"].eq("1 vehicle"),
    "2 or more vehicles": lambda data: data["vehicle_group"].eq("2 or more vehicles"),
}


def season_from_month(month: pd.Series) -> pd.Series:
    season = pd.Series(index=month.index, dtype="object")
    season.loc[month.isin([12, 1, 2, 3])] = "Winter"
    season.loc[month.isin([4, 5])] = "Spring"
    season.loc[month.isin([6, 7, 8, 9])] = "Summer"
    season.loc[month.isin([10, 11])] = "Fall"
    return season


def read_frame(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if path.suffix != ".csv":
        raise ValueError(f"Analysis input must be a CSV file: {path}")
    return pd.read_csv(path, usecols=columns)


def frequency_to_long(frequency: pd.DataFrame) -> pd.DataFrame:
    required = {
        "station", "season", "variable", "bin_label", "measurement_count",
        "total_measurements_in_period",
    }
    missing = required - set(frequency)
    if missing:
        raise ValueError(f"Frequency table is missing required columns: {sorted(missing)}")
    frequency = frequency[frequency["variable"].isin({spec.variable for spec in VARIABLES})].copy()
    if "frequency_pct" not in frequency:
        frequency["frequency_pct"] = (
            100 * frequency["measurement_count"] / frequency["total_measurements_in_period"]
        )
    return frequency


def load_data(
    accidents_path: Path,
    conditions_path: Path,
    frequency_path: Path,
    start: str | None,
    end: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_columns = ["id", "timestamp", "meidsli", "vehicle_count", "season"]
    condition_columns = [
        "id",

        "weather_station_id",
        "weather_station_dist_km",
        "weather_time_difference_minutes",
        "f",
        "fg",

        "temp_station_id",
        "temp_distance_km",
        "temp_time_diff_min",
        "temperature_c",
    ]
    events = read_frame(accidents_path, event_columns)
    conditions = read_frame(conditions_path, condition_columns)
    if not events["id"].is_unique or not conditions["id"].is_unique:
        raise ValueError("Accident event and condition IDs must each be unique")
    accidents = events.merge(conditions, on="id", how="left", validate="one_to_one")
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"])
    if start:
        accidents = accidents[accidents["timestamp"].ge(pd.Timestamp(start))]
    if end:
        accidents = accidents[accidents["timestamp"].le(pd.Timestamp(end))]
    accidents = accidents.copy()
    accidents["vehicle_group"] = np.where(
        accidents["vehicle_count"].eq(1), "1 vehicle", "2 or more vehicles"
    )
    accidents["year"] = accidents["timestamp"].dt.year

    frequency = frequency_to_long(read_frame(frequency_path))
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
        accidents[spec.distance_column].le(radius)
        & accidents[spec.time_difference_column].le(
            max_time_difference_minutes
        )
        & accidents[spec.accident_column].notna()
        & accidents[spec.station_column].notna()
        & SAMPLES[severity](accidents)
    ].copy()

    if analysis_season != "All seasons":
        scoped = scoped[scoped["season"].eq(analysis_season)].copy()

    # Normalize the variable-specific station to one common internal column.
    # Wind uses weather_station_id; temperature uses temp_station_id.
    scoped["weather_station_id"] = (
        scoped[spec.station_column]
        .astype(int)
    )

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Station-frequency-adjusted wind risk using cleaned 10-minute data."
    )
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-C", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("-f", "--frequency", type=Path, default=DEFAULT_FREQUENCY)
    parser.add_argument("-r", "--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("-d", "--details", type=Path, default=DEFAULT_DETAILS)
    parser.add_argument("-c", "--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("-n", "--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("-s", "--start")
    parser.add_argument("-e", "--end")
    args = parser.parse_args()

    accidents, frequency = load_data(
        args.accidents, args.conditions, args.frequency, args.start, args.end
    )
    specs = {spec.variable: spec for spec in VARIABLES}
    scenarios: list[tuple[str, int, str, str, int]] = []
    for variable in specs:
        scenarios.extend((variable, radius, "Injury accidents", "All seasons", 5) for radius in RADII)
        scenarios.extend((variable, 20, severity, "All seasons", 5) for severity in ["Serious or fatal", "Fatal"])
        scenarios.extend((variable, 20, "Injury accidents", season, 5) for season in SEASON_ORDER)
    for variable in ["f", "fg"]:
        scenarios.extend((variable, 20, group, "All seasons", 5) for group in ["1 vehicle", "2 or more vehicles"])
    scenarios.extend(("fg", 20, "Injury accidents", "All seasons", minutes) for minutes in TIME_SENSITIVITY_MINUTES)

    results: list[pd.DataFrame] = []
    details: list[pd.DataFrame] = []
    coverage: list[dict[str, object]] = []
    for variable, radius, severity, analysis_season, max_time in scenarios:
        result, detail, cover = one_analysis(
            accidents,
            frequency,
            specs[variable],
            radius,
            severity,
            analysis_season,
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
    detail_table.to_csv(args.details, index=False)
    coverage_table.to_csv(args.coverage, index=False)
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
Within each weather-station/season group, observed accident counts in each
wind interval are compared with expected counts based on the fraction of all clean
10-minute measurements in that interval. Results are then aggregated:

R_j = sum_g A_jg / sum_g (A_g * T_jg / T_g)

R_j = 1 means accident occurrence matches the background wind frequency. R_j above
1 means accidents are over-represented in that wind interval. It is a descriptive
relative accident frequency, not a causal risk estimate. Traffic volume is not
included.

Primary specification
---------------------
- Rural injury accidents, 2007-2025
- Maximum station distance: 20 km
- Variables: mean wind (f), matched-time gust (fg), and temperature
- Background controlled by station and season, pooled over 2007-2025
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
"""
    args.notes.write_text(notes, encoding="utf-8")
    print(f"wrote={args.results} rows={len(result_table):,}")
    print(f"wrote={args.details} rows={len(detail_table):,}")
    print(primary.to_string(index=False))


if __name__ == "__main__":
    main()
