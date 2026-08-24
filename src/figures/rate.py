"""Draw a stratified accident-rate figure from its completed result table."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.tables.rate import plot


DEFAULT_INPUT = Path("reports/main/tables/stratified_crash_rate_ratio_by_wind.csv")
DEFAULT_OUTPUT = Path("reports/main/figures/stratified_crash_rate_ratio_by_wind.png")


def title(data: pd.DataFrame) -> str:
    period = str(data["analysis_traffic_period"].iloc[0])
    vehicle = str(data["analysis_vehicle_group"].iloc[0])
    scope: list[str] = []
    if period == "official":
        scope.append("official VDU + SDU periods")
    elif period != "all":
        scope.append(period.upper())
    if vehicle != "all":
        scope.append("one vehicle" if vehicle == "one" else "two or more vehicles")
    suffix = "" if not scope else " (" + ", ".join(scope) + ")"
    return "Estimated rural injury-accident rate ratio by mean wind speed" + suffix


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    plot(data, args.output, title(data))
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
