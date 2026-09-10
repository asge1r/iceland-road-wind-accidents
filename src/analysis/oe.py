"""Calculate frequency-adjusted observed/expected ratios for defined samples."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.accidents.types import broad_accident_family
from src.analysis.oe_core import (
    PRIMARY_MAX_TIME_DIFFERENCE_MINUTES,
    VARIABLES,
    read_csv,
    station_frequency_scenario,
)


DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_FREQUENCY = Path("data/analysis/weather_frequency.csv")
DEFAULT_RESULTS = Path("reports/working/tables/oe_scenarios.csv")
DEFAULT_DETAILS = Path("reports/working/tables/oe_station_bins.csv")
DEFAULT_COVERAGE = Path("reports/working/tables/oe_coverage.csv")
DEFAULT_NOTES = Path("reports/working/oe_notes.txt")

SEASON_ORDER = ["Winter", "Spring", "Summer", "Fall"]
RADII = [10, 20, 30]
TIME_SENSITIVITY_MINUTES = [0, 2]


def count_column(variable: str, bin_label: str) -> str:
    safe_label = bin_label.replace(">=", "ge_").replace("-", "_")
    return f"{variable}_{safe_label}_count"


def frequency_to_long(frequency: pd.DataFrame) -> pd.DataFrame:
    if "variable" in frequency:
        if "frequency_pct" not in frequency:
            frequency = frequency.copy()
            frequency["frequency_pct"] = (
                100
                * frequency["measurement_count"]
                / frequency["total_measurements_in_period"]
            )
        return frequency
    keys = ["station", "name", "year", "season", "period", "total_measurements_in_period"]
    missing = set(keys) - set(frequency)
    if missing:
        raise ValueError(f"Frequency table is missing required columns: {sorted(missing)}")
    rows: list[pd.DataFrame] = []
    for spec in VARIABLES:
        for bin_label in spec.bin_labels:
            column = count_column(spec.variable, bin_label)
            if column not in frequency:
                raise ValueError(f"Frequency table is missing {column}")
            part = frequency[keys].copy()
            part["variable"] = spec.variable
            part["bin_label"] = bin_label
            part["measurement_count"] = frequency[column]
            part["frequency_pct"] = 100 * part["measurement_count"] / part["total_measurements_in_period"]
            rows.append(part)
    return pd.concat(rows, ignore_index=True)


def load_data(
    accidents_path: Path,
    conditions_path: Path,
    frequency_path: Path,
    start: str | None,
    end: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_columns = [
        "id", "timestamp", "meidsli", "tegohapps", "vehicle_count", "season"
    ]
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
    events = read_csv(accidents_path, event_columns)
    conditions = read_csv(conditions_path, condition_columns)
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
    accidents["accident_family"] = accidents["tegohapps"].map(broad_accident_family)
    accidents["year"] = accidents["timestamp"].dt.year

    frequency = frequency_to_long(read_csv(frequency_path))
    frequency = frequency.rename(columns={"station": "weather_station_id"})
    frequency["weather_station_id"] = pd.to_numeric(
        frequency["weather_station_id"], errors="raise"
    ).astype(int)
    return accidents, frequency


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
    scenarios.extend(
        ("f", 20, group, "All seasons", 5)
        for group in ["Single-vehicle accident type", "Other accident types"]
    )
    scenarios.extend(("fg", 20, "Injury accidents", "All seasons", minutes) for minutes in TIME_SENSITIVITY_MINUTES)
    # Append new scenarios so the established result order remains stable.
    for variable in specs:
        scenarios.extend(
            (variable, 20, "Serious or fatal", season, 5)
            for season in SEASON_ORDER
        )

    results: list[pd.DataFrame] = []
    details: list[pd.DataFrame] = []
    coverage: list[dict[str, object]] = []
    for variable, radius, severity, analysis_season, max_time in scenarios:
        result, detail, cover = station_frequency_scenario(
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
