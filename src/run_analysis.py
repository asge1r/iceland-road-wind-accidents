"""Rebuild every table and figure retained for the thesis.

Run from the project root with::

    .venv/bin/python -m src.run_analysis

The program uses only the five versioned inputs under ``data/analysis``. Each
module validates its inputs and writes traceable tables before drawing a figure.
"""

import subprocess
import sys


def run(module: str, *arguments: str) -> None:
    command = [sys.executable, "-m", module, *arguments]
    print("Running:", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def main() -> None:
    """Calculate wind-frequency adjustment and redraw the retained figures."""
    run("src.analysis.calculate_wind_risk")
    run("src.analysis.create_wind_risk_report")
    run("src.analysis.render_road_wind")
    run("src.analysis.render_daily_wind")


if __name__ == "__main__":
    main()
