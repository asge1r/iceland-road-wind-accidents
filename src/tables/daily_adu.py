"""Compare daily counter totals with published annual daily traffic."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.traffic.daily_tools import build_adu_validation


DAILY = Path("data/analysis/daily_traffic.csv")
LOCATIONS = Path("data/analysis/counter_locations.csv")
ANNUAL = Path("data/analysis/annual_traffic.csv")
OUTPUT = Path("reports/main/tables/counter_adu.csv")
DETAILS = Path("reports/working/tables/daily_traffic_adu_validation.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-d", "--daily", type=Path, default=DAILY)
    parser.add_argument("-l", "--locations", type=Path, default=LOCATIONS)
    parser.add_argument("-a", "--annual", type=Path, default=ANNUAL)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-v", "--validation-output", type=Path, default=DETAILS)
    args = parser.parse_args()
    daily = pd.read_csv(args.daily)
    locations = pd.read_csv(args.locations)
    required_daily = {"date", "counter_id", "traffic"}
    required_locations = {"year", "counter_id", "road_section"}
    if missing := required_daily - set(daily):
        raise ValueError(f"Daily traffic is missing columns: {sorted(missing)}")
    if missing := required_locations - set(locations):
        raise ValueError(f"Counter locations are missing columns: {sorted(missing)}")
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    daily["year"] = daily["date"].dt.year
    location_keys = locations[["year", "counter_id", "road_section"]]
    if location_keys.duplicated(["year", "counter_id"]).any():
        raise ValueError("Counter locations are not unique by year and counter")
    panel = daily.merge(
        location_keys, on=["year", "counter_id"], how="left", validate="many_to_one"
    ).rename(
        columns={"counter_id": "counter_site_id", "traffic": "traffic_volume"}
    )
    panel = panel.dropna(subset=["road_section"])
    validation, summary = build_adu_validation(panel, args.annual)
    for path in [args.output, args.validation_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output, index=False)
    validation.to_csv(args.validation_output, index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
