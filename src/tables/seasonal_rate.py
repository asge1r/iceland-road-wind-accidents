"""Estimate mean-wind rate ratios separately for four seasons."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.tables.rate import fit_model


INPUT = Path("data/analysis/seasonal_poisson_input.csv")
OUTPUT = Path("reports/main/tables/seasonal_poisson_rate_ratio_by_wind.csv")
SEASONS = ["Winter", "Spring", "Summer", "Fall"]
OUTCOMES = {
    "injury": "injury_accidents",
    "serious-fatal": "serious_or_fatal_accidents",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-g", "--outcome", choices=list(OUTCOMES), default="injury")
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    source = pd.read_csv(args.input)
    required = {
        "year", "road_section", "season", "wind_bin", "wind_bin_lower_ms",
        "estimated_vehicle_km", OUTCOMES[args.outcome],
    }
    missing = required - set(source)
    if missing:
        raise ValueError(f"Seasonal rate input is missing columns: {sorted(missing)}")
    results = []
    for season in SEASONS:
        data = source[source["season"].eq(season)].copy()
        data["observed_accidents"] = pd.to_numeric(
            data[OUTCOMES[args.outcome]], errors="raise"
        ).astype(int)
        data["wind_bin"] = pd.cut(
            data["wind_bin_lower_ms"], [-0.1, 10, 15, float("inf")],
            labels=["0-10", "10-15", ">=15"], right=False,
        ).astype("string")
        data["wind_bin_lower_ms"] = data["wind_bin"].map(
            {"0-10": 0.0, "10-15": 10.0, ">=15": 15.0}
        ).astype(float)
        data = data.groupby(
            ["year", "road_section", "season", "wind_bin", "wind_bin_lower_ms"],
            observed=True, as_index=False,
        ).agg(
            estimated_vehicle_km=("estimated_vehicle_km", "sum"),
            observed_accidents=("observed_accidents", "sum"),
        )
        data["stratum"] = data["road_section"].astype(str) + "|" + data["year"].astype(str)
        informative = data.groupby("stratum")["observed_accidents"].transform("sum").gt(0)
        data = data[informative & data["estimated_vehicle_km"].gt(0)].copy()
        if data.empty:
            raise ValueError(f"No informative seasonal strata remain for {season}")
        result = fit_model(data).rename(
            columns={"wind_bin": "bin_label", "wind_bin_lower_ms": "bin_lower_ms"}
        )
        result["season"] = season
        result["analysis_outcome"] = args.outcome
        results.append(result)
    output = pd.concat(results, ignore_index=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()
