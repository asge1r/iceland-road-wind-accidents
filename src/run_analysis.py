"""Rebuild every table and figure retained for the thesis.

Run from the project root with::

    .venv/bin/python -m src.run_analysis

The program uses prepared clean data under ``data/processed``. Each module
validates its inputs and writes traceable tables before drawing a figure.
"""

import subprocess
import sys


def run(module: str, *arguments: str) -> None:
    command = [sys.executable, "-m", module, *arguments]
    print("Running:", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def main() -> None:
    """Calculate wind-frequency adjustment and redraw the retained figures."""
    run("src.weather.build_wind_frequency", "--distribution-only")
    run("src.analysis.build_road_section_wind_table")
    run("src.analysis.calculate_wind_risk")
    run("src.analysis.create_wind_risk_report")
    run("src.analysis.analyze_daily_traffic", "--plot-only")
    run("src.analysis.build_daily_traffic_wind_analysis")
    run("src.analysis.analyze_daily_counter_availability")
    run("src.figures.create_data_overview_figures")
    run("src.figures.create_accident_profile_figure")
    run("src.figures.create_counter_weather_distance_figure")


if __name__ == "__main__":
    main()
