"""Run the documented raw-data preparation pipeline and, optionally, results.

Run from the project root. Raw data must first be placed in the directories
listed in ``data/README.md``. The default ``prepare`` stage does not redraw
figures; use ``--stage all`` only when the complete raw-data pipeline is wanted.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


PREPARE_STEPS = [
    "src.prepare.accidents.prepare_accidents",
    "src.prepare.weather.clean_weather",
    "src.prepare.traffic.prepare_annual_traffic",
    "src.prepare.traffic.extract_daily_traffic",
    "src.prepare.traffic.download_road_geometry",
    "src.prepare.traffic.locate_daily_counters_from_station",
    "src.prepare.match_daily_traffic_weather",
    "src.prepare.accidents.match_accidents_weather",
    "src.prepare.weather.build_wind_frequency",
    "src.prepare.export_analysis_data",
]


def run(module: str) -> None:
    command = [sys.executable, "-m", module]
    print("Running:", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["prepare", "results", "all"], default="prepare")
    args = parser.parse_args()
    if args.stage in {"prepare", "all"}:
        for module in PREPARE_STEPS:
            run(module)
    if args.stage in {"results", "all"}:
        run("src.run_analysis")


if __name__ == "__main__":
    main()
