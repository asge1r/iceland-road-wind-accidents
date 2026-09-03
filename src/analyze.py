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
    run("src.analysis.build_oe", dry_run=args.dry_run)
    run("src.tables.oe", "-b", str(args.bootstrap_reps), dry_run=args.dry_run)
    run("src.tables.radius_sensitivity", dry_run=args.dry_run)
    run("src.figures.oe", dry_run=args.dry_run)
    run("src.tables.annual_traffic_quality", dry_run=args.dry_run)
    run("src.tables.estimated_rate", dry_run=args.dry_run)
    run("src.tables.rate", dry_run=args.dry_run)
    run("src.figures.rate", dry_run=args.dry_run)
    run(
        "src.tables.rate", "--outcome", "serious-fatal", "--output",
        "reports/main/tables/conditional_poisson_rate_ratio_serious_fatal_by_wind.csv",
        dry_run=args.dry_run,
    )
    run(
        "src.figures.rate", "--input",
        "reports/main/tables/conditional_poisson_rate_ratio_serious_fatal_by_wind.csv",
        "--output",
        "reports/main/figures/conditional_poisson_rate_ratio_serious_fatal_by_wind.png",
        dry_run=args.dry_run,
    )
    run("src.tables.seasonal_rate", dry_run=args.dry_run)
    run("src.figures.seasonal_rate", dry_run=args.dry_run)
    run(
        "src.tables.rate", "--traffic-period", "official",
        "--output", "reports/working/tables/stratified_crash_rate_ratio_official_traffic.csv",
        dry_run=args.dry_run,
    )
    run(
        "src.figures.rate",
        "--input", "reports/working/tables/stratified_crash_rate_ratio_official_traffic.csv",
        "--output", "reports/working/figures/stratified_crash_rate_ratio_official_traffic.png",
        dry_run=args.dry_run,
    )
    daily_path = Path("data/analysis/daily_traffic.csv")
    if args.skip_daily_traffic or not daily_path.exists():
        reason = "requested" if args.skip_daily_traffic else f"missing {daily_path}"
        print(f"Skipping optional daily-counter result: {reason}.")
    else:
        run("src.tables.daily_traffic", dry_run=args.dry_run)
        run("src.tables.daily_wind_duration", dry_run=args.dry_run)
        run("src.figures.daily_wind_duration", dry_run=args.dry_run)
        run("src.tables.daily_allocated_rate", dry_run=args.dry_run)
        run("src.figures.daily_allocated_rate", dry_run=args.dry_run)
        run(
            "src.tables.daily_allocated_rate", "--outcome", "serious-fatal",
            "--output", "reports/main/tables/daily_allocated_rate_serious_fatal_by_wind.csv",
            "--audit", "reports/working/tables/daily_allocated_rate_serious_fatal_audit.csv",
            dry_run=args.dry_run,
        )
        run(
            "src.tables.daily_allocated_rate", "--time-window", "07-24",
            "--output", "reports/main/tables/daily_allocated_rate_07_24_by_wind.csv",
            "--audit", "reports/working/tables/daily_allocated_rate_07_24_audit.csv",
            dry_run=args.dry_run,
        )
        run("src.tables.daily_counter_rate", dry_run=args.dry_run)
        run(
            "src.tables.daily_counter_rate",
            "--coarse",
            dry_run=args.dry_run,
        )
        run("src.tables.daily_counter_radius", dry_run=args.dry_run)
        run("src.figures.daily_counter_rate", dry_run=args.dry_run)
        run("src.tables.traffic_sensitivity", dry_run=args.dry_run)
        run("src.figures.daily_traffic", dry_run=args.dry_run)
    run("src.figures.data_flow", dry_run=args.dry_run)
    run("src.figures.accident_profiles", dry_run=args.dry_run)
    run("src.tables.conditions", dry_run=args.dry_run)
    run("src.figures.conditions", dry_run=args.dry_run)
    run("src.tables.case_control", dry_run=args.dry_run)
    run("src.tables.high_wind_profile", dry_run=args.dry_run)
    run("src.validate", dry_run=args.dry_run)


if __name__ == "__main__":
    main()
