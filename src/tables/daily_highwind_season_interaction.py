"""Write the focused >=15 m/s daily wind-by-season interaction test."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.analysis.traffic_daily import fit_highwind_interaction as fit
from src.analysis.traffic_daily_panel import informative_model_data, read_panel
from src.tables.daily_season_panel import OUTPUT as PANEL


OUTPUT = Path("reports/working/tables/daily_highwind_season_interaction.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = fit(informative_model_data(read_panel(args.panel)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
