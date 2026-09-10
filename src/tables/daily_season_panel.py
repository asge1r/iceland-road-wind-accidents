"""Write the canonical counter-year-season daily-traffic analysis panel."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.analysis.traffic_daily_panel import build_panel
from src.export_docs import register_manifest_file


ACCIDENTS = Path("data/analysis/accidents.csv")
MATCHES = Path("data/analysis/counter_wind.csv")
DAILY = Path("data/analysis/daily_traffic.csv")
OUTPUT = Path("data/analysis/daily_season_panel.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-m", "--matches", type=Path, default=MATCHES)
    parser.add_argument("-d", "--daily-traffic", type=Path, default=DAILY)
    parser.add_argument("-r", "--max-distance-km", type=float, default=20.0)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    panel = build_panel(
        args.accidents, args.matches, args.daily_traffic, args.max_distance_km
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.output, index=False)
    register_manifest_file(
        args.output.parent,
        args.output.name,
        "Canonical counter-year-season input for seasonal allocated-traffic analyses.",
    )
    summary = panel.groupby("season", observed=True).agg(
        accidents=("observed_accidents", "sum"),
        strata=("stratum", "nunique"),
        counters=("counter_id", "nunique"),
        rows=("wind_bin", "size"),
    )
    print(f"wrote={args.output} rows={len(panel)}")
    print(summary.to_string())


if __name__ == "__main__":
    main()
