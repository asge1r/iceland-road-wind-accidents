"""Rebuild the canonical tables and figures retained for the thesis.

Run from the project root with::

    .venv/bin/python -m src.analyze

The primary O/E and daily-traffic results use compact canonical inputs under
``data/analysis``. The restricted annual-traffic comparison additionally reads
its documented road-period cache under ``data/processed``.
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
    """Calculate the retained thesis results from prepared local data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-b", "--bootstrap-reps", type=int, default=5000)
    parser.add_argument(
        "-D", "--skip-daily-traffic", action="store_true",
        help="Skip the optional daily-counter result and its traffic flow figure.",
    )
    parser.add_argument("-n", "--dry-run", action="store_true")
    args = parser.parse_args()
    run("src.export_tables", dry_run=args.dry_run)
    run("src.analysis.build_oe", dry_run=args.dry_run)
    run("src.analysis.report_oe", "-b", str(args.bootstrap_reps), dry_run=args.dry_run)
    run("src.analysis.traffic_adjusted_oe", dry_run=args.dry_run)
    if args.skip_daily_traffic:
        print("Skipping optional daily-counter result and traffic flow figure.")
    else:
        run("src.analysis.daily_traffic_response", dry_run=args.dry_run)
        run("src.figures.data_flow", dry_run=args.dry_run)
    run("src.figures.accident_profiles", dry_run=args.dry_run)
    run("src.validate", dry_run=args.dry_run)


if __name__ == "__main__":
    main()
