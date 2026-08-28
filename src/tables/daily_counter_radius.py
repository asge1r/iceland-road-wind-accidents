"""Test the observed daily-counter rate result at 5, 10, and 20 km."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.tables.daily_counter_rate import (
    ACCIDENTS,
    COARSE_EDGES,
    COARSE_LABELS,
    DAILY,
    LOCATIONS,
    aggregate_model_data,
    build_panel,
    fit_model,
    match_accidents,
    read_inputs,
)


OUTPUT = Path("reports/main/tables/daily_counter_radius_sensitivity.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-d", "--daily-traffic", type=Path, default=DAILY)
    parser.add_argument("-l", "--locations", type=Path, default=LOCATIONS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    accidents, daily, locations = read_inputs(
        args.accidents, args.daily_traffic, args.locations
    )
    rows: list[dict[str, object]] = []
    for radius in [5, 10, 20]:
        matches, exact_candidates = match_accidents(accidents, locations, radius)
        panel, matched_valid = build_panel(
            daily, matches, COARSE_EDGES, COARSE_LABELS
        )
        model_data = aggregate_model_data(panel)
        result = fit_model(model_data, COARSE_LABELS)
        for wind_bin in ["10-15", ">=15"]:
            estimate = result.loc[result["wind_bin"].eq(wind_bin)].iloc[0]
            rows.append({
                "max_counter_distance_km": radius,
                "wind_bin": wind_bin,
                "study_accidents": len(accidents),
                "exact_section_candidates": exact_candidates,
                "within_distance": matches["id"].nunique(),
                "with_valid_counter_day": matched_valid,
                "fitted_model_strata": int(estimate["model_strata"]),
                "observed_accidents": int(estimate["observed_accidents"]),
                "rate_ratio": estimate["rate_ratio"],
                "ci_95_low": estimate["ci_95_low"],
                "ci_95_high": estimate["ci_95_high"],
            })
    output = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()
