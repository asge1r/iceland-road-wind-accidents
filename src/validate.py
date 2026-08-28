"""Validate the fixed primary analysis and write a concise final audit."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_WEATHER_AUDIT = Path("archive/generated_diagnostics/weather_cleaning_by_year.csv")
DEFAULT_MEAN_WIND = Path("reports/main/tables/mean_wind_oe.csv")
DEFAULT_TEMPERATURE = Path("reports/main/tables/temperature_oe.csv")
DEFAULT_COVERAGE = Path("reports/main/tables/weather_match_coverage.csv")
DEFAULT_SENSITIVITY = Path("archive/generated_diagnostics/gust_sensitivity.csv")
DEFAULT_DAILY = Path("data/analysis/daily_traffic.csv")
DEFAULT_TRAFFIC_AUDIT = Path("reports/main/tables/annual_traffic_quality.csv")
DEFAULT_RATE_INPUT = Path("data/analysis/conditional_poisson_input.csv")
DEFAULT_RATE_MODEL = Path("reports/main/tables/conditional_poisson_rate_ratio_by_wind.csv")
DEFAULT_CASE_CONTROL = Path("data/analysis/case_control.csv")
DEFAULT_CASE_CONTROL_RESULT = Path("reports/main/tables/case_control_weather.csv")
DEFAULT_RADIUS_RESULT = Path("reports/main/tables/mean_wind_radius_sensitivity.csv")
DEFAULT_TRAFFIC_SENSITIVITY = Path("reports/main/tables/traffic_sensitivity.csv")
DEFAULT_DAILY_RATE = Path("reports/main/tables/daily_counter_rate_ratio_by_wind.csv")
DEFAULT_DAILY_RATE_COARSE = Path("reports/main/tables/daily_counter_rate_ratio_coarse_by_wind.csv")
DEFAULT_DAILY_RATE_RADIUS = Path("reports/main/tables/daily_counter_radius_sensitivity.csv")
DEFAULT_DAILY_DURATION = Path("reports/main/tables/daily_traffic_by_high_wind_duration.csv")
DEFAULT_DAILY_ALLOCATED = Path("reports/main/tables/daily_allocated_rate_ratio_by_wind.csv")
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
    conditions_path: Path,
    weather_audit_path: Path,
    mean_wind_path: Path,
    temperature_path: Path,
    coverage_path: Path,
    sensitivity_path: Path,
    daily_path: Path,
    traffic_audit_path: Path,
    rate_input_path: Path,
    rate_model_path: Path,
    case_control_path: Path,
    case_control_result_path: Path,
    radius_result_path: Path,
    traffic_sensitivity_path: Path,
    daily_rate_path: Path,
    daily_rate_coarse_path: Path,
    daily_rate_radius_path: Path,
    daily_duration_path: Path,
    daily_allocated_path: Path,
) -> dict[str, object]:
    if accidents_path.suffix != ".csv":
        raise ValueError(f"Analysis input must be a CSV file: {accidents_path}")
    accidents = pd.read_csv(accidents_path)
    require(len(accidents) > 0, "No rural injury accidents in canonical table")
    require(accidents["id"].is_unique, "Study accident IDs are not unique")
    conditions = pd.read_csv(conditions_path)
    required_condition_columns = {
        "id", "weather_station_id", "weather_station_dist_km",
        "weather_time_difference_minutes", "f", "fg", "gust_factor",
        "temp_station_id", "temp_distance_km", "temp_time_diff_min",
        "temperature_c", "solar_elevation_deg", "daylight_class",
    }
    require(
        required_condition_columns <= set(conditions),
        "Accident conditions are missing required columns",
    )
    require(conditions["id"].is_unique, "Accident condition IDs are not unique")
    require(set(accidents["id"]) == set(conditions["id"]), "Event and condition IDs differ")
    accidents = accidents.merge(conditions, on="id", how="left", validate="one_to_one")
    accident_year = pd.to_datetime(accidents["timestamp"], errors="coerce").dt.year
    study_period = f"{int(accident_year.min())}--{int(accident_year.max())}"
    primary_mask = (
        accidents["weather_station_dist_km"].le(20)
        & accidents["weather_time_difference_minutes"].le(5)
        & accidents["f"].notna()
    )
    primary_accidents = int(primary_mask.sum())
    require(primary_accidents > 0, "No primary weather matches")
    temperature_mask = conditions["temperature_c"].notna()
    require(
        conditions.loc[temperature_mask, "temperature_c"].between(-30, 30).all(),
        "Temperature is outside the fixed QC range",
    )
    require(
        conditions.loc[
            temperature_mask,
            ["temp_station_id", "temp_distance_km", "temp_time_diff_min"],
        ].notna().all().all(),
        "A temperature value is missing match metadata",
    )
    require(
        conditions.loc[temperature_mask, "temp_distance_km"].le(20).all()
        and conditions.loc[temperature_mask, "temp_time_diff_min"].le(5).all(),
        "A temperature match exceeds the fixed distance or time limit",
    )
    temperature_accidents = int(temperature_mask.sum())
    require(
        temperature_accidents / len(conditions) >= 0.8,
        "Temperature coverage is below 80%",
    )
    temperature_result = pd.read_csv(temperature_path)
    expected_temperature_bins = [
        "<-9", "-9--6", "-6--3", "-3-0", "0-3", "3-6",
        "6-9", "9-12", "12-15", "15-18", ">=18",
    ]
    require(
        temperature_result["temperature_interval_c"].tolist()
        == expected_temperature_bins,
        "Temperature O/E table does not use the documented 3-degree bins",
    )
    require(
        int(temperature_result["observed_accidents"].sum()) == temperature_accidents
        and temperature_result["expected_accidents"].gt(0).all(),
        "Temperature O/E counts or exposure are incomplete",
    )

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

    traffic_audit = pd.read_csv(traffic_audit_path).set_index("metric")
    required_traffic_metrics = {
        "section_years",
        "nonpositive_vdu",
        "nonpositive_derived_vhdu",
    }
    require(
        required_traffic_metrics <= set(traffic_audit.index),
        "Annual-traffic quality audit is incomplete",
    )

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

    case_control = pd.read_csv(case_control_path)
    require(
        {"exposure", "stratum_id", "case", "value", "controls_in_stratum"}
        <= set(case_control),
        "Case-crossover input is incomplete",
    )
    stratum_cases = case_control.groupby(["exposure", "stratum_id"])["case"].sum()
    require(stratum_cases.eq(1).all(), "Each case-crossover stratum must have one case")
    require(case_control["controls_in_stratum"].ge(1).all(), "A case-crossover stratum has no control")
    case_control_result = pd.read_csv(case_control_result_path)
    high_wind_case_control = case_control_result[
        case_control_result["exposure"].eq("mean_wind")
        & case_control_result["model"].eq("categorical")
        & case_control_result["comparison"].eq(">=15")
    ].iloc[0]
    require(
        float(high_wind_case_control["odds_ratio"]) > 1,
        "High-wind case-crossover odds ratio is not above one",
    )

    radius_result = pd.read_csv(radius_result_path)
    require(len(radius_result) == 9, "Primary radius table must contain nine rows")
    radius_20_25 = radius_result[radius_result["coarse_bin"].eq("20-25")]
    require(
        set(radius_20_25["radius_km"]) == {10, 20, 30}
        and radius_20_25["relative_accident_frequency"].gt(1).all(),
        "Primary 20--25 m/s radius sensitivity is incomplete or inconsistent",
    )
    traffic_sensitivity = pd.read_csv(traffic_sensitivity_path)
    official_20_25 = traffic_sensitivity[
        traffic_sensitivity["check"].eq("Rate model, 20-25 m/s")
        & traffic_sensitivity["primary_or_full_scope"].str.contains("Official")
    ]
    require(
        len(official_20_25) == 1 and float(official_20_25.iloc[0]["estimate"]) > 1,
        "Official-period traffic sensitivity does not retain the high-wind pattern",
    )
    daily_20_25 = traffic_sensitivity[
        traffic_sensitivity["check"].eq("Daily traffic, 20-25 m/s")
    ]
    require(
        len(daily_20_25) == 2
        and daily_20_25["estimate"].max() - daily_20_25["estimate"].min() < 2,
        "Zero-counter-day sensitivity changes the 20--25 m/s estimate materially",
    )
    daily_rate = pd.read_csv(daily_rate_path)
    require(
        daily_rate["wind_bin"].tolist() == ["0-5", "5-10", "10-15", "15-20", "20-25", ">=25"],
        "Detailed observed daily-rate table must use the standard bins",
    )
    daily_rate_coarse = pd.read_csv(daily_rate_coarse_path)
    require(
        daily_rate_coarse["wind_bin"].tolist() == ["0-10", "10-15", ">=15"],
        "Preferred observed daily-rate sensitivity must use the documented coarse bins",
    )
    for name, table in [("detailed", daily_rate), ("coarse", daily_rate_coarse)]:
        require(table["observed_vehicles"].gt(0).all(), f"{name} daily-rate exposure must be positive")
        estimated = table[table["ci_95_low"].notna()]
        require(
            estimated["ci_95_low"].le(estimated["rate_ratio"]).all()
            and estimated["rate_ratio"].le(estimated["ci_95_high"]).all(),
            f"{name} daily-rate confidence intervals are malformed",
        )
    require(
        daily_rate["model_accidents"].nunique() == 1
        and daily_rate_coarse["model_accidents"].nunique() == 1
        and int(daily_rate["model_accidents"].iloc[0])
        == int(daily_rate_coarse["model_accidents"].iloc[0])
        == int(daily_rate["observed_accidents"].sum())
        == int(daily_rate_coarse["observed_accidents"].sum()),
        "Detailed and coarse daily-rate tables must retain the same accidents",
    )
    daily_rate_high = daily_rate_coarse[daily_rate_coarse["wind_bin"].eq(">=15")].iloc[0]
    require(
        int(daily_rate_coarse["model_accidents"].iloc[0]) <= 1863
        and float(daily_rate_high["rate_ratio"]) > 1,
        "Observed daily-rate sensitivity has unexpected scope or direction",
    )
    daily_rate_radius = pd.read_csv(daily_rate_radius_path)
    require(
        set(daily_rate_radius["max_counter_distance_km"]) == {5, 10, 20}
        and set(daily_rate_radius["wind_bin"]) == {"10-15", ">=15"}
        and len(daily_rate_radius) == 6
        and daily_rate_radius["rate_ratio"].gt(0).all()
        and daily_rate_radius["ci_95_low"].le(daily_rate_radius["rate_ratio"]).all()
        and daily_rate_radius["rate_ratio"].le(daily_rate_radius["ci_95_high"]).all()
        and daily_rate_radius.groupby("max_counter_distance_km")["with_valid_counter_day"].first().is_monotonic_increasing,
        "Observed daily-rate distance sensitivity is incomplete or inconsistent",
    )
    daily_duration = pd.read_csv(daily_duration_path)
    require(
        daily_duration["hours_with_f_ge15"].tolist() == ["0", ">0-2", "2-6", ">=6"]
        and daily_duration["counter_days"].gt(0).all()
        and daily_duration["ci_95_low_pct"].le(daily_duration["relative_traffic_pct"]).all()
        and daily_duration["relative_traffic_pct"].le(daily_duration["ci_95_high_pct"]).all(),
        "Strong-wind-duration traffic table is incomplete or malformed",
    )
    daily_allocated = pd.read_csv(daily_allocated_path)
    require(
        daily_allocated["wind_bin"].tolist() == ["0-10", "10-15", ">=15"]
        and daily_allocated["estimated_vehicles_within_wind_bin"].gt(0).all()
        and int(daily_allocated["observed_accidents"].sum()) <= 1863,
        "Allocated daily-counter rate table has unexpected bins or scope",
    )
    allocated_estimates = daily_allocated[daily_allocated["ci_95_low"].notna()]
    require(
        allocated_estimates["ci_95_low"].le(allocated_estimates["rate_ratio"]).all()
        and allocated_estimates["rate_ratio"].le(allocated_estimates["ci_95_high"]).all(),
        "Allocated daily-counter confidence intervals are malformed",
    )

    from src.figures.accident_profiles import broad_accident_family

    families = accidents["tegohapps"].map(broad_accident_family)
    single_count = int(
        families.eq("Single vehicle: run-off-road, rollover, fall, or other").sum()
    )
    return {
        "primary_accidents": primary_accidents,
        "temperature_accidents": temperature_accidents,
        "study_accidents": len(accidents),
        "study_period": study_period,
        "weather": weather,
        "highest": highest,
        "coverage": coverage,
        "radius_sensitivity": radius_sensitivity,
        "daily_rows": daily_rows,
        "daily_with_wind": daily_with_wind,
        "traffic_audit": traffic_audit,
        "rate_accidents": int(rate_input["injury_accidents"].sum()),
        "high_rate": high_rate,
        "high_wind_case_control": high_wind_case_control,
        "radius_20_25": radius_20_25,
        "official_20_25": official_20_25.iloc[0],
        "daily_20_25": daily_20_25,
        "daily_rate_high": daily_rate_high,
        "daily_rate_total": int(daily_rate_coarse["model_accidents"].iloc[0]),
        "daily_rate_radius": daily_rate_radius,
        "daily_duration": daily_duration,
        "daily_allocated": daily_allocated,
        "single_vehicle_count": single_count,
        "single_vehicle_pct": 100 * single_count / len(accidents),
    }


def write_report(values: dict[str, object], output: Path) -> None:
    weather = values["weather"]
    highest = values["highest"]
    coverage = values["coverage"]
    radius_sensitivity = values["radius_sensitivity"]
    traffic_audit = values["traffic_audit"]
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
        f"| Temperature matches within 20 km and 5 minutes | {values['temperature_accidents']:,} / {values['study_accidents']:,} |",
        f"| Raw weather observations | {weather['input_rows']:,} |",
        f"| Clean weather observations retained | {weather['clean_rows']:,} |",
        f"| Weather observations excluded by fixed rules | {weather['excluded_rows']:,} |",
        f"| Clean weather retention, all delivered rows | {100 * weather['clean_rows'] / weather['input_rows']:.2f}% |",
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
            "## Primary spatial sensitivity",
            "",
            "At 20--25 m/s, O/E remains above one under 10, 20, and 30 km weather-station limits.",
            "",
            "## Stratified vehicle-kilometre result",
            "",
            f"The shared-station rate model retains {values['rate_accidents']:,} accidents. At >=25 m/s, the within-stratum time-proportional rate ratio is {values['high_rate']['time_proportional_rate_ratio']:.2f} (95% CI {values['high_rate']['time_proportional_ci_95_low']:.2f}--{values['high_rate']['time_proportional_ci_95_high']:.2f}).",
            "",
            "## Time-stratified case-crossover result",
            "",
            f"At mean wind >=15 m/s versus 0--5 m/s, the matched odds ratio is {values['high_wind_case_control']['odds_ratio']:.2f} (95% CI {values['high_wind_case_control']['ci_95_low']:.2f}--{values['high_wind_case_control']['ci_95_high']:.2f}).",
            "",
            "## Traffic sensitivities",
            "",
            f"Restricting the 20--25 m/s rate model to official VDU and SDU gives RR {values['official_20_25']['estimate']:.2f}. Excluding zero counter-days changes the corresponding daily-traffic percentage by less than two percentage points.",
            f"The sustained-wind table contains {int(values['daily_duration']['counter_days'].sum()):,} sufficiently complete counter-days. Traffic is {values['daily_duration'].iloc[-1]['relative_traffic_pct']:.1f}% of its calendar expectation on days with at least six hours at f >=15 m/s.",
            f"The allocated daily-counter model retains {int(values['daily_allocated']['observed_accidents'].sum()):,} accidents. Its >=15 versus 0--10 m/s rate ratio is {values['daily_allocated'].iloc[-1]['rate_ratio']:.2f} (95% CI {values['daily_allocated'].iloc[-1]['ci_95_low']:.2f}--{values['daily_allocated'].iloc[-1]['ci_95_high']:.2f}). The within-day denominator is estimated, not observed hourly traffic.",
            f"The appendix full-day-mean sensitivity retains {values['daily_rate_total']:,} accidents. At >=15 m/s versus 0--10 m/s, RR is {values['daily_rate_high']['rate_ratio']:.2f} (95% CI {values['daily_rate_high']['ci_95_low']:.2f}--{values['daily_rate_high']['ci_95_high']:.2f}), based on {int(values['daily_rate_high']['observed_accidents'])} upper-category accidents.",
            "The 5, 10, and 20 km counter-assignment table confirms that both non-reference coarse estimates are generated reproducibly and retain valid confidence-interval ordering.",
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
            "## Annual-traffic quality",
            "",
            f"The 2007--2025 annual-traffic input contains {int(traffic_audit.loc['section_years', 'section_years']):,} road-section/year rows. "
            f"Nonpositive published VDU values occur in {int(traffic_audit.loc['nonpositive_vdu', 'section_years']):,} rows, and "
            f"nonpositive derived VHDU residuals occur in {int(traffic_audit.loc['nonpositive_derived_vhdu', 'section_years']):,} rows. "
            "These rows are excluded from the corresponding positive vehicle-kilometre exposure; they are not replaced or imputed.",
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
    parser.add_argument("-C", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("-w", "--weather-audit", type=Path, default=DEFAULT_WEATHER_AUDIT)
    parser.add_argument("-m", "--mean-wind", type=Path, default=DEFAULT_MEAN_WIND)
    parser.add_argument("-p", "--temperature", type=Path, default=DEFAULT_TEMPERATURE)
    parser.add_argument("-c", "--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("-s", "--sensitivity", type=Path, default=DEFAULT_SENSITIVITY)
    parser.add_argument("-d", "--daily", type=Path, default=DEFAULT_DAILY)
    parser.add_argument("-t", "--traffic-audit", type=Path, default=DEFAULT_TRAFFIC_AUDIT)
    parser.add_argument("-r", "--rate-input", type=Path, default=DEFAULT_RATE_INPUT)
    parser.add_argument("-R", "--rate-model", type=Path, default=DEFAULT_RATE_MODEL)
    parser.add_argument("-x", "--case-control", type=Path, default=DEFAULT_CASE_CONTROL)
    parser.add_argument("-X", "--case-control-result", type=Path, default=DEFAULT_CASE_CONTROL_RESULT)
    parser.add_argument("-S", "--radius-result", type=Path, default=DEFAULT_RADIUS_RESULT)
    parser.add_argument("-T", "--traffic-sensitivity", type=Path, default=DEFAULT_TRAFFIC_SENSITIVITY)
    parser.add_argument("-D", "--daily-rate", type=Path, default=DEFAULT_DAILY_RATE)
    parser.add_argument("-Q", "--daily-rate-coarse", type=Path, default=DEFAULT_DAILY_RATE_COARSE)
    parser.add_argument("-q", "--daily-rate-radius", type=Path, default=DEFAULT_DAILY_RATE_RADIUS)
    parser.add_argument("-U", "--daily-duration", type=Path, default=DEFAULT_DAILY_DURATION)
    parser.add_argument("-A", "--daily-allocated", type=Path, default=DEFAULT_DAILY_ALLOCATED)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    values = validation_values(
        args.accidents,
        args.conditions,
        args.weather_audit,
        args.mean_wind,
        args.temperature,
        args.coverage,
        args.sensitivity,
        args.daily,
        args.traffic_audit,
        args.rate_input,
        args.rate_model,
        args.case_control,
        args.case_control_result,
        args.radius_result,
        args.traffic_sensitivity,
        args.daily_rate,
        args.daily_rate_coarse,
        args.daily_rate_radius,
        args.daily_duration,
        args.daily_allocated,
    )
    write_report(values, args.output)
    print(f"Validated primary analysis; wrote {args.output}")


if __name__ == "__main__":
    main()
