"""Run the documented raw-data preparation pipeline and, optionally, results.

Run from the project root. Raw data must first be placed in the directories
listed in ``data/README.md``. The default ``prepare`` stage does not redraw
figures; use ``--stage all`` only when the complete raw-data pipeline is wanted.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


CORE_PREPARE_STEPS = [
    "src.accidents.build",
    "src.weather.clean",
    "src.traffic.annual",
    "src.accidents.match_weather",
    "src.accidents.case_control",
    "src.weather.frequency",
    "src.traffic.build_road_period",
    "src.traffic.rate_weather",
]

DAILY_TRAFFIC_STEPS = [
    "src.traffic.daily",
    "src.traffic.download_roads",
    "src.traffic.locate_counters",
    "src.traffic.daily_weather",
]


def run(module: str, *arguments: str, dry_run: bool = False) -> None:
    command = [sys.executable, "-m", module, *arguments]
    print("Running:", " ".join(command), flush=True)
    if not dry_run:
        subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-s", "--stage", choices=["prepare", "results", "all"], default="prepare")
    parser.add_argument(
        "-t", "--daily-traffic", action="store_true",
        help="Rebuild daily traffic from the six local PDF files (2019-2024).",
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="Print the selected local steps without changing files.",
    )
    args = parser.parse_args()
    if args.stage in {"prepare", "all"}:
        for module in CORE_PREPARE_STEPS:
            extra = ("--include-2025",) if module == "src.accidents.build" else ()
            run(module, *extra, dry_run=args.dry_run)
        pdf_directory = Path("data/raw/traffic/daily_pdf")
        if args.daily_traffic:
            for module in DAILY_TRAFFIC_STEPS:
                run(module, dry_run=args.dry_run)
        elif not pdf_directory.exists():
            print("Skipping daily-traffic rebuild: data/raw/traffic/daily_pdf/ is absent. "
                  "Use --daily-traffic after adding the six PDFs.")
        else:
            print("Skipping daily-traffic rebuild by default. Use --daily-traffic to parse PDFs.")
        run("src.export_tables", dry_run=args.dry_run)
    if args.stage in {"results", "all"}:
        run("src.analyze", dry_run=args.dry_run)


if __name__ == "__main__":
    main()
