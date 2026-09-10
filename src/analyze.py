"""Rebuild retained thesis results from the compact analysis CSV layer.

Run without a stage option for the complete analysis. Named stages make focused
rebuilds possible without repeating unrelated bootstrap models or figures.
No task in this entry point reads raw or processed data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys


@dataclass(frozen=True)
class Task:
    """One independently executable module and its command-line arguments."""

    module: str
    arguments: tuple[str, ...] = ()


STAGE_ORDER = (
    "workflow",
    "primary-weather",
    "annual-traffic",
    "daily-traffic",
    "sample-description",
    "matched-time",
    "severity-context",
    "products",
)


def task(module: str, *arguments: str) -> Task:
    return Task(module, arguments)


def run(selected: Task, dry_run: bool = False) -> None:
    command = [sys.executable, "-m", selected.module, *selected.arguments]
    print("Running:", " ".join(command), flush=True)
    if not dry_run:
        subprocess.run(command, check=True)


def primary_weather_tasks(bootstrap_reps: int) -> list[Task]:
    return [
        task("src.analysis.oe"),
        task("src.tables.oe", "-b", str(bootstrap_reps)),
        task("src.tables.weather_oe_panels"),
        task("src.tables.year_oe", "-b", str(bootstrap_reps)),
        task("src.tables.wind_radius"),
        task("src.figures.oe"),
        task("src.figures.weather_oe_panels", "-v", "f"),
        task("src.figures.weather_oe_panels", "-v", "fg"),
        task("src.figures.weather_oe_panels", "-v", "temperature"),
    ]


def annual_traffic_tasks() -> list[Task]:
    return [
        task("src.tables.annual_quality"),
        task("src.tables.estimated_rate"),
        task("src.tables.rate"),
        task("src.tables.temp_rate"),
        task(
            "src.tables.rate", "--outcome", "one", "--coarse",
            "--output", "reports/main/tables/wind_rate_one.csv",
        ),
        task(
            "src.tables.rate", "--outcome", "two-plus", "--coarse",
            "--output", "reports/main/tables/wind_rate_multiple.csv",
        ),
        task(
            "src.tables.rate", "--outcome", "serious-fatal",
            "--output", "reports/main/tables/wind_rate_severity.csv",
        ),
        task("src.tables.season_rate"),
        task(
            "src.tables.season_rate", "--outcome", "serious-fatal",
            "--output", "reports/main/tables/season_rate_severity.csv",
        ),
        task(
            "src.tables.rate", "--traffic-period", "official",
            "--output", "reports/working/tables/wind_rate_official.csv",
        ),
        task("src.figures.rate"),
        task("src.figures.temp_rate"),
        task("src.figures.vehicle_rate"),
        task(
            "src.figures.rate",
            "--input", "reports/main/tables/wind_rate_severity.csv",
            "--output", "reports/main/figures/wind_rate_severity.png",
        ),
        task("src.figures.season_rate"),
        task(
            "src.figures.season_rate",
            "--input", "reports/main/tables/season_rate_severity.csv",
            "--output", "reports/main/figures/season_rate_severity.png",
        ),
        task(
            "src.figures.rate",
            "--input", "reports/working/tables/wind_rate_official.csv",
            "--output", "reports/working/figures/wind_rate_official.png",
        ),
    ]


def daily_traffic_tasks(bootstrap_reps: int) -> list[Task]:
    return [
        task("src.tables.daily_traffic"),
        task("src.tables.wind_duration"),
        task("src.tables.allocated_rate"),
        task("src.tables.daily_sample"),
        task(
            "src.tables.allocated_rate", "--outcome", "serious-fatal",
            "--output", "reports/main/tables/allocated_rate_severity.csv",
            "--audit", "reports/working/tables/allocated_rate_severity_audit.csv",
        ),
        task(
            "src.tables.allocated_rate", "--time-window", "07-24",
            "--output", "reports/main/tables/allocated_rate_day.csv",
            "--audit", "reports/working/tables/allocated_rate_day_audit.csv",
        ),
        task("src.tables.counter_rate"),
        task("src.tables.counter_rate", "--coarse"),
        task("src.tables.counter_radius"),
        task("src.tables.daily_adu"),
        task("src.tables.traffic_checks"),
        task("src.tables.allocation_check"),
        # All seasonal daily results deliberately share this one panel.
        task("src.tables.daily_season_panel"),
        task("src.tables.daily_season_rate"),
        task("src.tables.daily_season_interaction"),
        task("src.tables.daily_highwind_season_interaction"),
        task("src.tables.daily_season_oe", "-b", str(bootstrap_reps)),
        task("src.figures.wind_duration"),
        task("src.figures.counter_map"),
        task("src.figures.allocated_rate"),
        task("src.figures.counter_rate"),
        task("src.figures.daily_traffic"),
        task("src.figures.daily_season_oe"),
    ]


def sample_description_tasks() -> list[Task]:
    return [
        task("src.tables.annual_coverage"),
        task("src.tables.match_quality"),
        task("src.tables.conditions"),
        task("src.figures.data_flow"),
        task("src.figures.accident_profiles"),
        task("src.figures.accident_map"),
        task("src.figures.annual_coverage"),
        task("src.figures.conditions"),
    ]


def matched_time_tasks() -> list[Task]:
    return [
        task("src.tables.case_control"),
        task("src.tables.wind_season"),
        task("src.tables.weather_model"),
        task(
            "src.figures.estimates",
            "-i", "reports/main/tables/wind_season.csv",
            "-o", "reports/main/figures/wind_season.png",
            "-t", "Matched strong-wind association by season",
            "-g", "season", "-G", "Winter", "Spring", "Summer", "Autumn",
        ),
        task(
            "src.figures.estimates",
            "-i", "reports/main/tables/weather_model.csv",
            "-o", "reports/main/figures/weather_model.png",
            "-t", "Matched-time wind and temperature model",
            "-g", "variable", "-e", "adjusted_odds_ratio",
        ),
    ]


def severity_context_tasks() -> list[Task]:
    return [
        task("src.tables.severity"),
        task("src.tables.daylight"),
        task("src.tables.wind_profile"),
        task(
            "src.figures.estimates",
            "-i", "reports/main/tables/severity_conditions.csv",
            "-o", "reports/main/figures/severity_conditions.png",
            "-t", "Serious or fatal severity among recorded injury accidents",
        ),
        task(
            "src.figures.estimates",
            "-i", "reports/main/tables/severity_conditions.csv",
            "-o", "reports/main/figures/severity_context.png",
            "-t", "Adjusted injury severity by time, daylight, and season",
            "-G", "Time of day", "Daylight", "Season",
        ),
        task(
            "src.figures.estimates",
            "-i", "reports/main/tables/daylight.csv",
            "-o", "reports/main/figures/daylight.png",
            "-t", "Daylight at accident dates and matched dates",
        ),
    ]


def stage_tasks(
    stage: str, bootstrap_reps: int, include_daily: bool
) -> list[Task]:
    """Return tasks in reproducible dependency order for one stage."""
    if stage == "workflow":
        return [task("src.tables.pipeline")]
    if stage == "primary-weather":
        return primary_weather_tasks(bootstrap_reps)
    if stage == "annual-traffic":
        return annual_traffic_tasks()
    if stage == "daily-traffic":
        return daily_traffic_tasks(bootstrap_reps) if include_daily else []
    if stage == "sample-description":
        return sample_description_tasks()
    if stage == "matched-time":
        return matched_time_tasks()
    if stage == "severity-context":
        return severity_context_tasks()
    if stage == "products":
        tasks = []
        if include_daily:
            tasks.extend([
                task(
                    "src.tables.wind_oe_comparison", "-b", str(bootstrap_reps)
                ),
                task("src.tables.season_method_comparison"),
            ])
        return [
            *tasks,
            task("src.validate"),
            task("src.tables.thesis"),
            *([task("src.figures.wind_oe_comparison")] if include_daily else []),
        ]
    raise ValueError(f"Unknown analysis stage: {stage}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-b", "--bootstrap-reps", type=int, default=5000)
    parser.add_argument(
        "-s", "--stage", action="append", choices=STAGE_ORDER,
        help="Run only this stage; repeat the option for several stages.",
    )
    parser.add_argument(
        "-D", "--skip-daily-traffic", action="store_true",
        help="Skip results requiring the optional daily-counter input.",
    )
    parser.add_argument("-n", "--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.bootstrap_reps <= 0:
        raise ValueError("Bootstrap replicates must be positive")
    stages = list(dict.fromkeys(args.stage or STAGE_ORDER))
    daily_path = Path("data/analysis/daily_traffic.csv")
    include_daily = not args.skip_daily_traffic and daily_path.exists()
    if "daily-traffic" in stages and not include_daily:
        reason = "requested" if args.skip_daily_traffic else f"missing {daily_path}"
        print(f"Skipping daily-traffic stage: {reason}.", flush=True)
    for stage in STAGE_ORDER:
        if stage not in stages:
            continue
        print(f"\nAnalysis stage: {stage}", flush=True)
        for selected in stage_tasks(stage, args.bootstrap_reps, include_daily):
            run(selected, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
