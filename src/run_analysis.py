"""Rebuild every table and figure retained for the thesis.

Run from the project root with::

    .venv/bin/python -m src.run_analysis

The program uses prepared clean data under ``data/processed``. Each module
validates its inputs and writes traceable tables before drawing a figure.
"""

import argparse
import subprocess
import sys


def run(module: str, *arguments: str, dry_run: bool = False) -> None:
    command = [sys.executable, "-m", module, *arguments]
    print("Running:", " ".join(command), flush=True)
    if not dry_run:
        subprocess.run(command, check=True)


def main() -> None:
    """Calculate wind-frequency adjustment and redraw the retained figures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-b", "--bootstrap-reps", type=int, default=5000)
    parser.add_argument("-n", "--dry-run", action="store_true")
    args = parser.parse_args()
    run("src.weather.build_wind_frequency", "--distribution-only", dry_run=args.dry_run)
    run("src.analysis.build_road_section_wind_table", dry_run=args.dry_run)
    run("src.analysis.calculate_wind_risk", dry_run=args.dry_run)
    run("src.analysis.create_wind_risk_report", "-b", str(args.bootstrap_reps), dry_run=args.dry_run)
    run("src.analysis.analyze_daily_traffic", "--plot-only", dry_run=args.dry_run)
    run("src.analysis.build_daily_traffic_wind_analysis", dry_run=args.dry_run)
    run("src.analysis.analyze_daily_counter_availability", dry_run=args.dry_run)
    run("src.figures.create_data_overview_figures", dry_run=args.dry_run)
    run("src.figures.create_accident_profile_figure", dry_run=args.dry_run)
    run("src.figures.create_counter_weather_distance_figure", dry_run=args.dry_run)


if __name__ == "__main__":
    main()
