"""Rebuild every table and figure retained for the thesis.

Run from the project root with::

    .venv/bin/python -m src.analyze

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
    run("src.weather.frequency", "--distribution-only", dry_run=args.dry_run)
    run("src.analysis.traffic_sensitivity", dry_run=args.dry_run)
    run("src.analysis.build_oe", dry_run=args.dry_run)
    run("src.analysis.report_oe", "-b", str(args.bootstrap_reps), dry_run=args.dry_run)
    run("src.analysis.match_daily_weather", "--plot-only", dry_run=args.dry_run)
    run("src.analysis.daily_traffic_response", dry_run=args.dry_run)
    run("src.analysis.daily_counter_coverage", dry_run=args.dry_run)
    run("src.figures.data_flow", dry_run=args.dry_run)
    run("src.figures.accident_profiles", dry_run=args.dry_run)
    run("src.figures.counter_distance", dry_run=args.dry_run)


if __name__ == "__main__":
    main()
