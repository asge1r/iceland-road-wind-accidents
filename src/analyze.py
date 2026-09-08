"""Rebuild the tables and figures retained for the thesis.

Run from the project root with::

    .venv/bin/python -m src.analyze

All results use documented CSV inputs under ``data/analysis``. Run
``src.prepare`` first when source data or preparation rules have changed.
"""

import argparse
from pathlib import Path
import subprocess
import sys


def run(module: str, *arguments: str, dry_run: bool = False) -> None:
    command = [sys.executable, "-m", module, *arguments]
    print("Running:", " ".join(command), flush=True)
    if not dry_run:
        subprocess.run(command, check=True)


def main() -> None:
    """Calculate the retained thesis results from prepared local data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-b", "--bootstrap-reps", type=int, default=5000)
    parser.add_argument(
        "-D", "--skip-daily-traffic", action="store_true",
        help="Skip the optional daily-counter result.",
    )
    parser.add_argument("-n", "--dry-run", action="store_true")
    args = parser.parse_args()
    run("src.tables.pipeline", dry_run=args.dry_run)
    run("src.analysis.oe", dry_run=args.dry_run)
    run("src.tables.oe", "-b", str(args.bootstrap_reps), dry_run=args.dry_run)
    run("src.tables.year_oe", "-b", str(args.bootstrap_reps), dry_run=args.dry_run)
    run("src.tables.wind_radius", dry_run=args.dry_run)
    run("src.figures.oe", dry_run=args.dry_run)
    run("src.tables.annual_quality", dry_run=args.dry_run)
    run("src.tables.estimated_rate", dry_run=args.dry_run)
    run("src.tables.rate", dry_run=args.dry_run)
    run("src.figures.rate", dry_run=args.dry_run)
    run("src.tables.temp_rate", dry_run=args.dry_run)
    run("src.figures.temp_rate", dry_run=args.dry_run)
    run(
        "src.tables.rate", "--outcome", "one", "--coarse",
        "--output", "reports/main/tables/wind_rate_one.csv",
        dry_run=args.dry_run,
    )
    run(
        "src.tables.rate", "--outcome", "two-plus", "--coarse",
        "--output", "reports/main/tables/wind_rate_multiple.csv",
        dry_run=args.dry_run,
    )
    run("src.figures.vehicle_rate", dry_run=args.dry_run)
    run(
        "src.tables.rate", "--outcome", "serious-fatal", "--output",
        "reports/main/tables/wind_rate_severity.csv",
        dry_run=args.dry_run,
    )
    run(
        "src.figures.rate", "--input",
        "reports/main/tables/wind_rate_severity.csv",
        "--output",
        "reports/main/figures/wind_rate_severity.png",
        dry_run=args.dry_run,
    )
    run("src.tables.season_rate", dry_run=args.dry_run)
    run("src.figures.season_rate", dry_run=args.dry_run)
    run(
        "src.tables.season_rate", "--outcome", "serious-fatal", "--output",
        "reports/main/tables/season_rate_severity.csv",
        dry_run=args.dry_run,
    )
    run(
        "src.figures.season_rate", "--input",
        "reports/main/tables/season_rate_severity.csv",
        "--output",
        "reports/main/figures/season_rate_severity.png",
        dry_run=args.dry_run,
    )
    run(
        "src.tables.rate", "--traffic-period", "official",
        "--output", "reports/working/tables/wind_rate_official.csv",
        dry_run=args.dry_run,
    )
    run(
        "src.figures.rate",
        "--input", "reports/working/tables/wind_rate_official.csv",
        "--output", "reports/working/figures/wind_rate_official.png",
        dry_run=args.dry_run,
    )
    daily_path = Path("data/analysis/daily_traffic.csv")
    if args.skip_daily_traffic or not daily_path.exists():
        reason = "requested" if args.skip_daily_traffic else f"missing {daily_path}"
        print(f"Skipping optional daily-counter result: {reason}.")
    else:
        run("src.tables.daily_traffic", dry_run=args.dry_run)
        run("src.tables.wind_duration", dry_run=args.dry_run)
        run("src.figures.wind_duration", dry_run=args.dry_run)
        run("src.tables.allocated_rate", dry_run=args.dry_run)
        run("src.tables.daily_sample", dry_run=args.dry_run)
        run("src.figures.counter_map", dry_run=args.dry_run)
        run("src.figures.allocated_rate", dry_run=args.dry_run)
        run(
            "src.tables.allocated_rate", "--outcome", "serious-fatal",
            "--output", "reports/main/tables/allocated_rate_severity.csv",
            "--audit", "reports/working/tables/allocated_rate_severity_audit.csv",
            dry_run=args.dry_run,
        )
        run(
            "src.tables.allocated_rate", "--time-window", "07-24",
            "--output", "reports/main/tables/allocated_rate_day.csv",
            "--audit", "reports/working/tables/allocated_rate_day_audit.csv",
            dry_run=args.dry_run,
        )
        run("src.tables.counter_rate", dry_run=args.dry_run)
        run(
            "src.tables.counter_rate",
            "--coarse",
            dry_run=args.dry_run,
        )
        run("src.tables.counter_radius", dry_run=args.dry_run)
        run("src.figures.counter_rate", dry_run=args.dry_run)
        run("src.tables.daily_adu", dry_run=args.dry_run)
        run("src.tables.traffic_checks", dry_run=args.dry_run)
        run("src.tables.allocation_check", dry_run=args.dry_run)
        run("src.figures.daily_traffic", dry_run=args.dry_run)
    run("src.figures.data_flow", dry_run=args.dry_run)
    run("src.figures.accident_profiles", dry_run=args.dry_run)
    run("src.figures.accident_map", dry_run=args.dry_run)
    run("src.tables.annual_coverage", dry_run=args.dry_run)
    run("src.tables.match_quality", dry_run=args.dry_run)
    run("src.figures.annual_coverage", dry_run=args.dry_run)
    run("src.tables.conditions", dry_run=args.dry_run)
    run("src.figures.conditions", dry_run=args.dry_run)
    run("src.tables.case_control", dry_run=args.dry_run)
    run("src.tables.wind_season", dry_run=args.dry_run)
    run(
        "src.figures.estimates",
        "-i", "reports/main/tables/wind_season.csv",
        "-o", "reports/main/figures/wind_season.png",
        "-t", "Matched strong-wind association by season",
        "-g", "season", "-G", "Winter", "Spring", "Summer", "Autumn",
        dry_run=args.dry_run,
    )
    run("src.tables.weather_model", dry_run=args.dry_run)
    run(
        "src.figures.estimates",
        "-i", "reports/main/tables/weather_model.csv",
        "-o", "reports/main/figures/weather_model.png",
        "-t", "Matched-time wind and temperature model",
        "-g", "variable",
        "-e", "adjusted_odds_ratio",
        dry_run=args.dry_run,
    )
    run("src.tables.severity", dry_run=args.dry_run)
    run(
        "src.figures.estimates",
        "-i", "reports/main/tables/severity_conditions.csv",
        "-o", "reports/main/figures/severity_conditions.png",
        "-t", "Serious or fatal severity among recorded injury accidents",
        dry_run=args.dry_run,
    )
    run(
        "src.figures.estimates",
        "-i", "reports/main/tables/severity_conditions.csv",
        "-o", "reports/main/figures/severity_context.png",
        "-t", "Adjusted injury severity by time, daylight, and season",
        "-G", "Time of day", "Daylight", "Season",
        dry_run=args.dry_run,
    )
    run("src.tables.daylight", dry_run=args.dry_run)
    run(
        "src.figures.estimates",
        "-i", "reports/main/tables/daylight.csv",
        "-o", "reports/main/figures/daylight.png",
        "-t", "Daylight at accident dates and matched dates",
        dry_run=args.dry_run,
    )
    run("src.tables.wind_profile", dry_run=args.dry_run)
    run("src.validate", dry_run=args.dry_run)
    run("src.tables.thesis", dry_run=args.dry_run)


if __name__ == "__main__":
    main()
