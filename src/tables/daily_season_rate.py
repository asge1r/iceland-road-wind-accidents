"""Write seasonal daily-counter rate estimates from the canonical panel."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.analysis.traffic_daily import fit_seasonal_rates
from src.analysis.traffic_daily_panel import read_panel
from src.tables.daily_season_panel import OUTPUT as PANEL


OUTPUT = Path("reports/working/tables/daily_season_rate.csv")
AUDIT = Path("reports/working/tables/daily_season_rate_audit.csv")
calculate = fit_seasonal_rates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-u", "--audit", type=Path, default=AUDIT)
    args = parser.parse_args()
    output, audit = calculate(read_panel(args.panel))
    for path in [args.output, args.audit]:
        path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    audit.to_csv(args.audit, index=False)
    print("\nAUDIT")
    print(audit.to_string(index=False))
    print("\nRESULTS")
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()
