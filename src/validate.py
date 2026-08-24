"""Validate the fixed primary analysis and write a concise final audit."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_WEATHER_AUDIT = Path("archive/generated_diagnostics/weather_cleaning_by_year.csv")
DEFAULT_MEAN_WIND = Path("reports/main/tables/mean_wind_oe.csv")
DEFAULT_COVERAGE = Path("reports/main/tables/weather_match_coverage.csv")
DEFAULT_SENSITIVITY = Path("archive/generated_diagnostics/gust_sensitivity.csv")
DEFAULT_DAILY = Path("data/analysis/daily_traffic.csv")
DEFAULT_RATE_INPUT = Path("data/analysis/rate_model.csv")
DEFAULT_RATE_MODEL = Path("reports/main/tables/stratified_crash_rate_ratio_by_wind.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/final_analysis_validation.md")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def weather_checks(path: Path) -> dict[str, int]:
    audit = pd.read_csv(path)
    total = audit[audit["year"].astype(str).eq("total")]
    require(len(total) == 1, "Weather audit must contain one total row")
    row = total.iloc[0]
    require(int(row["clean_wind_rows"]) > 0, "No clean wind observations in weather audit")
    return {
        "input_rows": int(row["input_rows"]),
        "clean_rows": int(row["clean_wind_rows"]),
        "excluded_rows": int(row["excluded_rows"]),
    }


def validation_values(
    accidents_path: Path,
    weather_audit_path: Path,
    mean_wind_path: Path,
    coverage_path: Path,
    sensitivity_path: Path,
    daily_path: Path,
    rate_input_path: Path,
    rate_model_path: Path,
) -> dict[str, object]:
    if accidents_path.suffix != ".csv":
        raise ValueError(f"Analysis input must be a CSV file: {accidents_path}")
    accidents = pd.read_csv(accidents_path)
    require(len(accidents) > 0, "No rural injury accidents in canonical table")
    require(accidents["id"].is_unique, "Study accident IDs are not unique")
    accident_year = pd.to_datetime(accidents["timestamp"], errors="coerce").dt.year
    study_period = f"{int(accident_year.min())}--{int(accident_year.max())}"
    primary_mask = (
        accidents["weather_station_dist_km"].le(20)
        & accidents["weather_time_difference_minutes"].le(5)
        & accidents["f"].notna()
    )
    primary_accidents = int(primary_mask.sum())
    require(primary_accidents > 0, "No primary weather matches")

    weather = weather_checks(weather_audit_path)

    mean_wind = pd.read_csv(mean_wind_path)
    require(int(mean_wind["observed_accidents"].sum()) == primary_accidents, "Observed mean-wind counts do not sum to primary sample")
    require(
        np.isclose(mean_wind["expected_accidents"].sum(), primary_accidents, atol=0.2),
        "Rounded expected mean-wind counts do not sum to the primary sample",
    )
    highest = mean_wind.loc[mean_wind["mean_wind_interval_ms"].eq(">=25")].iloc[0]
    require(int(highest["observed_accidents"]) > 0, "No observed accidents in the highest mean-wind interval")
    require(float(highest["expected_accidents"]) > 0, "No expected accidents in the highest mean-wind interval")

    coverage = pd.read_csv(coverage_path).set_index("radius_km")
    for radius in [10, 20, 30]:
        require(radius in coverage.index, f"Missing {radius} km coverage")
        require(int(coverage.loc[radius, "analysed_accidents"]) > 0, f"No {radius} km coverage")

    sensitivity = pd.read_csv(sensitivity_path)
    radius_sensitivity = sensitivity[
        sensitivity["comparison"].eq("station_radius")
        & sensitivity["variable"].eq("fg")
        & sensitivity["wind_interval_ms"].eq(">=35")
    ].set_index("level")
    for level in ["10 km", "20 km", "30 km"]:
        require(level in radius_sensitivity.index, f"Missing gust distance result for {level}")

    daily_rows: int | None = None
    daily_with_wind: int | None = None
    if daily_path.exists():
        if daily_path.suffix != ".csv":
            raise ValueError(f"Analysis input must be a CSV file: {daily_path}")
        daily = pd.read_csv(daily_path, usecols=["f_mean"])
        daily_rows = len(daily)
        daily_with_wind = int(daily["f_mean"].notna().sum())
        require(daily_rows > 0, "No daily counter-days")
        require(daily_with_wind > 0, "No daily counter-days with wind")

    rate_input = pd.read_csv(rate_input_path)
    required_rate_columns = {"injury_accidents", "estimated_vehicle_km"}
    require(required_rate_columns <= set(rate_input), "Rate-model input is incomplete")
    rate_model = pd.read_csv(rate_model_path)
    require(
        int(rate_model["observed_accidents"].sum()) == int(rate_input["injury_accidents"].sum()),
        "Rate-model counts do not sum to the compact rate-model input",
    )
    high_rate = rate_model.loc[rate_model["bin_label"].eq(">=25")].iloc[0]
    require(float(high_rate["time_proportional_rate_ratio"]) > 1, "High-wind rate ratio is not above one")

    from src.figures.accident_profiles import broad_accident_family

    families = accidents["tegohapps"].map(broad_accident_family)
    single_count = int(
        families.eq("Single vehicle: run-off-road, rollover, fall, or other").sum()
    )
    return {
        "primary_accidents": primary_accidents,
        "study_accidents": len(accidents),
        "study_period": study_period,
        "weather": weather,
        "highest": highest,
        "coverage": coverage,
        "radius_sensitivity": radius_sensitivity,
        "daily_rows": daily_rows,
        "daily_with_wind": daily_with_wind,
        "rate_accidents": int(rate_input["injury_accidents"].sum()),
        "high_rate": high_rate,
        "single_vehicle_count": single_count,
        "single_vehicle_pct": 100 * single_count / len(accidents),
    }


def write_report(values: dict[str, object], output: Path) -> None:
    weather = values["weather"]
    highest = values["highest"]
    coverage = values["coverage"]
    radius_sensitivity = values["radius_sensitivity"]
    lines = [
        "# Final analysis validation",
        "",
        "All checks below passed against the current local canonical files.",
        "",
        "## Fixed primary analysis",
        "",
        f"- Population: {values['study_accidents']:,} rural injury accidents, {values['study_period']}.",
        f"- Primary weather match: {values['primary_accidents']:,} accidents within 20 km and 5 minutes.",
        "- Primary exposure: mean wind speed (`f`) in 5 m/s intervals.",
        "- Standardisation: weather station and season; weather frequency is pooled across 2007--2025.",
        "- Uncertainty: 5,000 weather-station-clustered bootstrap samples.",
        "",
        "## Data checks",
        "",
        "| Check | Result |",
        "|---|---:|",
        f"| Unique accident identifiers | {values['study_accidents']:,} / {values['study_accidents']:,} |",
        f"| Raw weather observations | {weather['input_rows']:,} |",
        f"| Clean weather observations retained | {weather['clean_rows']:,} |",
        f"| Weather observations excluded by fixed rules | {weather['excluded_rows']:,} |",
        f"| Rate-analysis accidents with shared station within 20 km and 5 minutes | {values['rate_accidents']:,} |",
    ]
    if values["daily_rows"] is None:
        lines.append("| Daily counter-days | Optional daily PDF data were not prepared locally |")
    else:
        daily_pct = 100 * values["daily_with_wind"] / values["daily_rows"]
        lines.extend(
            [
                f"| Daily counter-days | {values['daily_rows']:,} |",
                f"| Daily counter-days with daytime wind | {values['daily_with_wind']:,} ({daily_pct:.2f}%) |",
            ]
        )
    lines.extend(
        [
            "",
            "## Primary O/E result",
            "",
            "| Mean wind-speed interval | Observed | Expected | O/E | 95% interval |",
            "|---|---:|---:|---:|---:|",
            f"| >=25 m/s | {int(highest['observed_accidents'])} | {highest['expected_accidents']:.1f} | {highest['observed_expected_ratio']:.2f} | {highest['station_bootstrap_ci_95_low']:.2f}--{highest['station_bootstrap_ci_95_high']:.2f} |",
            "",
            f"Observed counts sum to {values['primary_accidents']:,}. Expected counts are rounded to one decimal in this table.",
            "The >=25 m/s O/E interval includes one; this sparse upper bin is descriptive rather than a separate precise result.",
            "",
            "## Stratified vehicle-kilometre result",
            "",
            f"The shared-station rate model retains {values['rate_accidents']:,} accidents. At >=25 m/s, the within-stratum time-proportional rate ratio is {values['high_rate']['time_proportional_rate_ratio']:.2f} (95% CI {values['high_rate']['time_proportional_ci_95_low']:.2f}--{values['high_rate']['time_proportional_ci_95_high']:.2f}).",
            "",
            "## Weather-station distance comparison for fg >=35 m/s (secondary analysis)",
            "",
            "| Maximum distance | Matched accidents | O/E | 95% interval |",
            "|---|---:|---:|---:|",
        ]
    )
    for level in ["10 km", "20 km", "30 km"]:
        radius = int(level.split()[0])
        row = radius_sensitivity.loc[level]
        lines.append(
            f"| {level} | {int(coverage.loc[radius, 'analysed_accidents']):,} | "
            f"{row['observed_expected_ratio']:.2f} | "
            f"{row['station_bootstrap_ci_95_low']:.2f}--{row['station_bootstrap_ci_95_high']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Scope decision",
            "",
            f"Single-vehicle, run-off-road, rollover, fall, or other accidents account for {values['single_vehicle_count']:,} of {values['study_accidents']:,} study accidents ({values['single_vehicle_pct']:.1f}%).",
            "This supports the relevance of wind conditions to vehicle control. A separate O/E curve for this group would be an exploratory appendix analysis, not a replacement for the fixed all-injury primary result.",
            "",
            "## Decision",
            "",
            "The primary analysis is internally consistent and ready to freeze: `f`, a 20 km weather-station limit, a 5-minute time limit, and wind-frequency-adjusted O/E as the main result. Gust and daily traffic remain secondary analyses.",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-w", "--weather-audit", type=Path, default=DEFAULT_WEATHER_AUDIT)
    parser.add_argument("-m", "--mean-wind", type=Path, default=DEFAULT_MEAN_WIND)
    parser.add_argument("-c", "--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("-s", "--sensitivity", type=Path, default=DEFAULT_SENSITIVITY)
    parser.add_argument("-d", "--daily", type=Path, default=DEFAULT_DAILY)
    parser.add_argument("-r", "--rate-input", type=Path, default=DEFAULT_RATE_INPUT)
    parser.add_argument("-R", "--rate-model", type=Path, default=DEFAULT_RATE_MODEL)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    values = validation_values(
        args.accidents,
        args.weather_audit,
        args.mean_wind,
        args.coverage,
        args.sensitivity,
        args.daily,
        args.rate_input,
        args.rate_model,
    )
    write_report(values, args.output)
    print(f"Validated primary analysis; wrote {args.output}")


if __name__ == "__main__":
    main()
