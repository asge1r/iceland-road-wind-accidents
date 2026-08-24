"""Draw the descriptive accident-per-vehicle-kilometre figure."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.tables.estimated_rate import plot


DEFAULT_INPUT = Path("reports/working/tables/estimated_crash_rate_by_wind.csv")
DEFAULT_OUTPUT = Path("reports/working/figures/estimated_crash_rate_by_wind.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    plot(pd.read_csv(args.input), args.output)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
