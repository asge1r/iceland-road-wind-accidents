"""Rebuild the canonical tables and figures retained for the thesis.

Run from the project root with::

    .venv/bin/python -m src.analyze

All results use compact canonical CSV inputs under ``data/analysis``. Run
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
    run("src.analysis.build_oe", dry_run=args.dry_run)
    run("src.tables.oe", "-b", str(args.bootstrap_reps), dry_run=args.dry_run)
    run("src.figures.oe", dry_run=args.dry_run)
    run("src.figures.gust_factor", dry_run=args.dry_run)
    run("src.tables.estimated_rate", dry_run=args.dry_run)
    run("src.figures.estimated_rate", dry_run=args.dry_run)
    run("src.tables.rate", dry_run=args.dry_run)
    run("src.figures.rate", dry_run=args.dry_run)
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
    run("src.analysis.compare_traffic_scopes", dry_run=args.dry_run)
    daily_path = Path("data/analysis/daily_traffic.csv")
    if args.skip_daily_traffic or not daily_path.exists():
        reason = "requested" if args.skip_daily_traffic else f"missing {daily_path}"
        print(f"Skipping optional daily-counter result: {reason}.")
    else:
        run("src.tables.daily_traffic", dry_run=args.dry_run)
        run("src.figures.daily_traffic", dry_run=args.dry_run)
    run("src.figures.data_flow", dry_run=args.dry_run)
    run("src.figures.accident_profiles", dry_run=args.dry_run)
    run("src.validate", dry_run=args.dry_run)


if __name__ == "__main__":
    main()
