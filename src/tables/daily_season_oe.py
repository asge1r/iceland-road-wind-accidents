"""Write traffic-standardised seasonal O/E from the canonical panel."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.analysis.traffic_daily import calculate_seasonal_oe as calculate
from src.analysis.traffic_daily_panel import read_panel
from src.tables.daily_season_panel import OUTPUT as PANEL


OUTPUT = Path("reports/main/tables/daily_season_oe.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-b", "--bootstrap-replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260909)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = calculate(read_panel(args.panel), args.bootstrap_replicates, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
