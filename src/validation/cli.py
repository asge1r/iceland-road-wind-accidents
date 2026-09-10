"""Command-line interface for the final analysis validation."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.validation.audit import validation_values
from src.validation.common import (
    DEFAULT_ACCIDENTS,
    DEFAULT_CASE_CONTROL,
    DEFAULT_CASE_CONTROL_RESULT,
    DEFAULT_CONDITIONS,
    DEFAULT_DAILY,
    DEFAULT_DAILY_07_24,
    DEFAULT_DAILY_ACCIDENT_WEATHER,
    DEFAULT_DAILY_ALLOCATED,
    DEFAULT_DAILY_DURATION,
    DEFAULT_DAILY_RATE,
    DEFAULT_DAILY_RATE_COARSE,
    DEFAULT_DAILY_RATE_RADIUS,
    DEFAULT_DAILY_SAMPLE,
    DEFAULT_DAILY_SERIOUS,
    DEFAULT_OUTPUT,
    DEFAULT_RATE_INPUT,
    DEFAULT_RATE_MODEL,
    DEFAULT_RATE_SERIOUS,
    DEFAULT_SEASONAL_RATE,
    DEFAULT_SEASONAL_SERIOUS,
    DEFAULT_WEATHER_OE,
    DEFAULT_TRAFFIC_AUDIT,
    DEFAULT_TRAFFIC_CHECKS,
    DEFAULT_WEATHER_AUDIT,
)
from src.validation.report import write_report

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-C", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("-w", "--weather-audit", type=Path, default=DEFAULT_WEATHER_AUDIT)
    parser.add_argument("-O", "--weather-oe", type=Path, default=DEFAULT_WEATHER_OE)
    parser.add_argument("-d", "--daily", type=Path, default=DEFAULT_DAILY)
    parser.add_argument("--daily-accident-weather", type=Path, default=DEFAULT_DAILY_ACCIDENT_WEATHER)
    parser.add_argument("-t", "--traffic-audit", type=Path, default=DEFAULT_TRAFFIC_AUDIT)
    parser.add_argument("-r", "--rate-input", type=Path, default=DEFAULT_RATE_INPUT)
    parser.add_argument("-R", "--rate-model", type=Path, default=DEFAULT_RATE_MODEL)
    parser.add_argument("--rate-serious", type=Path, default=DEFAULT_RATE_SERIOUS)
    parser.add_argument("--seasonal-rate", type=Path, default=DEFAULT_SEASONAL_RATE)
    parser.add_argument("--seasonal-serious", type=Path, default=DEFAULT_SEASONAL_SERIOUS)
    parser.add_argument("-x", "--case-control", type=Path, default=DEFAULT_CASE_CONTROL)
    parser.add_argument("-X", "--case-control-result", type=Path, default=DEFAULT_CASE_CONTROL_RESULT)
    parser.add_argument("-T", "--traffic-checks", type=Path, default=DEFAULT_TRAFFIC_CHECKS)
    parser.add_argument("-D", "--daily-rate", type=Path, default=DEFAULT_DAILY_RATE)
    parser.add_argument("-Q", "--daily-rate-coarse", type=Path, default=DEFAULT_DAILY_RATE_COARSE)
    parser.add_argument("-q", "--daily-rate-radius", type=Path, default=DEFAULT_DAILY_RATE_RADIUS)
    parser.add_argument("-U", "--daily-duration", type=Path, default=DEFAULT_DAILY_DURATION)
    parser.add_argument("-A", "--daily-allocated", type=Path, default=DEFAULT_DAILY_ALLOCATED)
    parser.add_argument("-J", "--daily-sample", type=Path, default=DEFAULT_DAILY_SAMPLE)
    parser.add_argument("--daily-serious", type=Path, default=DEFAULT_DAILY_SERIOUS)
    parser.add_argument("--daily-07-24", type=Path, default=DEFAULT_DAILY_07_24)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    values = validation_values(
        args.accidents,
        args.conditions,
        args.weather_audit,
        args.weather_oe,
        args.daily,
        args.daily_accident_weather,
        args.traffic_audit,
        args.rate_input,
        args.rate_model,
        args.rate_serious,
        args.seasonal_rate,
        args.seasonal_serious,
        args.case_control,
        args.case_control_result,
        args.traffic_checks,
        args.daily_rate,
        args.daily_rate_coarse,
        args.daily_rate_radius,
        args.daily_duration,
        args.daily_allocated,
        args.daily_sample,
        args.daily_serious,
        args.daily_07_24,
    )
    write_report(values, args.output)
    print(f"Validated primary analysis; wrote {args.output}")


if __name__ == "__main__":
    main()
