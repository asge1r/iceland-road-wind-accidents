"""Validate the fixed primary analysis and write a concise final audit."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


DEFAULT_ACCIDENTS = Path("data/processed/accidents/rural_injury_accidents.parquet")
DEFAULT_WEATHER = Path("data/processed/weather/weather_10min_clean.parquet")
DEFAULT_GUST = Path("reports/main/tables/gust_risk.csv")
DEFAULT_COVERAGE = Path("reports/main/tables/gust_coverage.csv")
DEFAULT_SENSITIVITY = Path("archive/generated_diagnostics/gust_sensitivity.csv")
DEFAULT_DAILY = Path("data/processed/traffic/daily_traffic_weather.parquet")
DEFAULT_OUTPUT = Path("reports/main/tables/final_analysis_validation.md")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def weather_checks(path: Path) -> dict[str, float | int]:
    parquet = pq.ParquetFile(path)
    rows = 0
    invalid_f = 0
    invalid_fg = 0
    invalid_relation = 0
    min_f = np.inf
    max_f = -np.inf
    min_fg = np.inf
    max_fg = -np.inf
    for batch in parquet.iter_batches(batch_size=1_000_000, columns=["f", "fg"]):
        f = batch.column(0).to_numpy(zero_copy_only=False)
        fg = batch.column(1).to_numpy(zero_copy_only=False)
        rows += len(f)
        invalid_f += int(np.count_nonzero((f < 0) | (f >= 45)))
        invalid_fg += int(np.count_nonzero((fg < 0) | (fg >= 65)))
        invalid_relation += int(np.count_nonzero(fg + 0.5 < f))
        min_f = min(min_f, float(np.min(f)))
        max_f = max(max_f, float(np.max(f)))
        min_fg = min(min_fg, float(np.min(fg)))
        max_fg = max(max_fg, float(np.max(fg)))
    require(invalid_f == 0, f"Weather has {invalid_f:,} invalid f values")
    require(invalid_fg == 0, f"Weather has {invalid_fg:,} invalid fg values")
    require(invalid_relation == 0, f"Weather has {invalid_relation:,} fg < f values")
    return {
        "rows": rows,
        "min_f": min_f,
        "max_f": max_f,
        "min_fg": min_fg,
        "max_fg": max_fg,
    }


def validation_values(
    accidents_path: Path,
    weather_path: Path,
    gust_path: Path,
    coverage_path: Path,
    sensitivity_path: Path,
    daily_path: Path,
) -> dict[str, object]:
    accidents = pd.read_parquet(accidents_path)
    require(len(accidents) == 6_120, f"Expected 6,120 injury accidents, found {len(accidents):,}")
    require(accidents["nid"].is_unique, "Study accident IDs are not unique")
    primary_mask = (
        accidents["weather_station_dist_km"].le(20)
        & accidents["weather_time_difference_minutes"].le(5)
        & accidents["f"].notna()
        & accidents["fg"].notna()
    )
    primary_accidents = int(primary_mask.sum())
    require(primary_accidents == 5_912, f"Expected 5,912 primary matches, found {primary_accidents:,}")

    weather = weather_checks(weather_path)
    require(weather["rows"] == 211_497_897, f"Expected 211,497,897 weather rows, found {weather['rows']:,}")

    gust = pd.read_csv(gust_path)
    require(int(gust["observed_accidents"].sum()) == primary_accidents, "Observed gust counts do not sum to primary sample")
    require(
        np.isclose(gust["expected_accidents"].sum(), primary_accidents, atol=0.2),
        "Rounded expected gust counts do not sum to the primary sample",
    )
    highest = gust.loc[gust["wind_gust_interval_ms"].eq(">=36")].iloc[0]
    require(int(highest["observed_accidents"]) == 25, "Highest gust observed count changed")
    require(np.isclose(highest["expected_accidents"], 4.105106, atol=0.01), "Highest gust expectation changed")
    require(np.isclose(highest["observed_expected_ratio"], 6.089976, atol=0.01), "Highest gust O/E changed")

    coverage = pd.read_csv(coverage_path).set_index("radius_km")
    expected_coverage = {10: 4_622, 20: 5_912, 30: 6_109}
    for radius, count in expected_coverage.items():
        require(int(coverage.loc[radius, "analysed_accidents"]) == count, f"Unexpected {radius} km coverage")

    sensitivity = pd.read_csv(sensitivity_path)
    radius_sensitivity = sensitivity[
        sensitivity["comparison"].eq("station_radius")
        & sensitivity["variable"].eq("fg")
        & sensitivity["wind_interval_ms"].eq(">=36")
    ].set_index("level")
    expected_ratios = {"10 km": 7.27, "20 km": 6.09, "30 km": 5.99}
    for level, ratio in expected_ratios.items():
        require(np.isclose(radius_sensitivity.loc[level, "observed_expected_ratio"], ratio, atol=0.01), f"Unexpected {level} sensitivity ratio")

    daily = pd.read_parquet(daily_path, columns=["f_daytime_mean"])
    daily_with_wind = int(daily["f_daytime_mean"].notna().sum())
    require(len(daily) == 774_274, f"Expected 774,274 counter-days, found {len(daily):,}")
    require(daily_with_wind == 738_424, f"Expected 738,424 counter-days with wind, found {daily_with_wind:,}")

    accident_types = pd.read_csv("reports/main/tables/accident_characteristics.csv")
    single = accident_types[
        accident_types["category"].eq("Single vehicle: run-off-road, rollover, fall, or other")
        & accident_types["dimension"].eq("accident_family")
    ].iloc[0]
    return {
        "primary_accidents": primary_accidents,
        "weather": weather,
        "highest": highest,
        "coverage": coverage,
        "radius_sensitivity": radius_sensitivity,
        "daily_rows": len(daily),
        "daily_with_wind": daily_with_wind,
        "single_vehicle_count": int(single["count"]),
        "single_vehicle_pct": float(single["percent"]),
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
        "- Population: 6,120 rural injury accidents, 2007--2024.",
        f"- Primary weather match: {values['primary_accidents']:,} accidents within 20 km and 5 minutes.",
        "- Primary exposure: maximum wind gust (`fg`) in 3 m/s intervals.",
        "- Standardisation: weather station, calendar year, and season.",
        "- Uncertainty: 5,000 weather-station-clustered bootstrap samples.",
        "",
        "## Data checks",
        "",
        "| Check | Result |",
        "|---|---:|",
        "| Unique accident identifiers | 6,120 / 6,120 |",
        f"| Clean weather observations scanned | {weather['rows']:,} |",
        f"| `f` range | {weather['min_f']:.3f} to {weather['max_f']:.3f} m/s |",
        f"| `fg` range | {weather['min_fg']:.3f} to {weather['max_fg']:.3f} m/s |",
        "| Invalid `f`, invalid `fg`, or `fg + 0.5 < f` | 0, 0, 0 |",
        f"| Daily counter-days | {values['daily_rows']:,} |",
        f"| Daily counter-days with daytime wind | {values['daily_with_wind']:,} (95.37%) |",
        "",
        "## Primary O/E result",
        "",
        "| Gust interval | Observed | Expected | O/E | 95% interval |",
        "|---|---:|---:|---:|---:|",
        f"| >=36 m/s | {int(highest['observed_accidents'])} | {highest['expected_accidents']:.1f} | {highest['observed_expected_ratio']:.2f} | {highest['station_bootstrap_ci_95_low']:.2f}--{highest['station_bootstrap_ci_95_high']:.2f} |",
        "",
        "Observed counts sum to 5,912. Expected counts are rounded to one decimal in this table and therefore sum to 5,912.1.",
        "",
        "## Distance sensitivity for fg >=36 m/s",
        "",
        "| Maximum distance | Matched accidents | O/E | 95% interval |",
        "|---|---:|---:|---:|",
    ]
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
            f"Single-vehicle, run-off-road, rollover, fall, or other accidents account for {values['single_vehicle_count']:,} of 6,120 study accidents ({values['single_vehicle_pct']:.1f}%).",
            "This supports the physical relevance of wind gusts. A separate O/E curve for this group would be an exploratory appendix analysis, not a replacement for the fixed all-injury primary result.",
            "",
            "## Decision",
            "",
            "The primary analysis is internally consistent and ready to freeze: `fg`, a 20 km weather-station limit, a 5-minute time limit, and wind-frequency-adjusted O/E as the main result. Daily traffic remains a supporting analysis.",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-w", "--weather", type=Path, default=DEFAULT_WEATHER)
    parser.add_argument("-g", "--gust", type=Path, default=DEFAULT_GUST)
    parser.add_argument("-c", "--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("-s", "--sensitivity", type=Path, default=DEFAULT_SENSITIVITY)
    parser.add_argument("-d", "--daily", type=Path, default=DEFAULT_DAILY)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    values = validation_values(
        args.accidents,
        args.weather,
        args.gust,
        args.coverage,
        args.sensitivity,
        args.daily,
    )
    write_report(values, args.output)
    print(f"Validated primary analysis; wrote {args.output}")


if __name__ == "__main__":
    main()
