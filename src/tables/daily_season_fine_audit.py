"""Audit whether fine wind bins are usable in seasonal daily-traffic analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.tables.counter_rate import ACCIDENTS, DAILY
from src.tables.daily_season_panel import (
    FINE_COUNT_COLUMNS,
    FINE_EDGES,
    FINE_LABELS,
    MATCHES,
    SEASONS,
    build_panel,
)


OUTPUT = Path("reports/main/tables/daily_season_fine_audit.csv")


def summarise(panel: pd.DataFrame) -> pd.DataFrame:
    """Summarise counts and allocated traffic in the proposed fine cells."""
    totals = panel.groupby("stratum", observed=True).agg(
        stratum_accidents=("observed_accidents", "sum"),
        stratum_exposure=("allocated_vehicles", "sum"),
    )
    data = panel.merge(totals, on="stratum", validate="many_to_one")
    data["traffic_expected_accidents"] = (
        data["stratum_accidents"]
        * data["allocated_vehicles"]
        / data["stratum_exposure"]
    )
    result = data.groupby(
        ["season", "wind_bin"], observed=True, as_index=False
    ).agg(
        observed_accidents=("observed_accidents", "sum"),
        traffic_expected_accidents=("traffic_expected_accidents", "sum"),
        allocated_vehicles=("allocated_vehicles", "sum"),
        contributing_strata=("stratum", "nunique"),
        counters=("counter_id", "nunique"),
        counter_days=("counter_days", "sum"),
    )
    result["traffic_standardised_oe"] = np.divide(
        result["observed_accidents"], result["traffic_expected_accidents"]
    )
    result["fewer_than_10_accidents"] = result["observed_accidents"].lt(10)
    result["fewer_than_20_accidents"] = result["observed_accidents"].lt(20)
    result["season"] = pd.Categorical(result["season"], SEASONS, ordered=True)
    result["wind_bin"] = pd.Categorical(
        result["wind_bin"], FINE_LABELS, ordered=True
    )
    return result.sort_values(["season", "wind_bin"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-m", "--matches", type=Path, default=MATCHES)
    parser.add_argument("-d", "--daily-traffic", type=Path, default=DAILY)
    parser.add_argument("-r", "--max-distance-km", type=float, default=20.0)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    panel = build_panel(
        args.accidents,
        args.matches,
        args.daily_traffic,
        args.max_distance_km,
        labels=FINE_LABELS,
        edges=FINE_EDGES,
        count_columns=FINE_COUNT_COLUMNS,
    )
    result = summarise(panel)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
