"""Compare all primary-sample accidents with accidents at mean wind >=15 m/s."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.figures.accident_profiles import broad_accident_family


DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/high_wind_accident_profile.csv")


def rows(data: pd.DataFrame, dimension: str, order: list[str]) -> pd.DataFrame:
    scopes = {"Primary wind sample": data, "Mean wind >=15 m/s": data[data["f"].ge(15)]}
    output = []
    for scope, scoped in scopes.items():
        counts = scoped[dimension].value_counts().reindex(order, fill_value=0)
        for category, count in counts.items():
            output.append(
                {
                    "dimension": dimension,
                    "category": category,
                    "scope": scope,
                    "accidents": int(count),
                    "percent": 100 * count / len(scoped),
                    "scope_accidents": len(scoped),
                }
            )
    return pd.DataFrame(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-c", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    accidents = pd.read_csv(args.accidents)
    conditions = pd.read_csv(args.conditions)
    data = accidents.merge(conditions, on="id", validate="one_to_one")
    data = data[
        data["weather_station_dist_km"].le(20)
        & data["weather_time_difference_minutes"].le(5)
        & data["f"].notna()
    ].copy()
    data["vehicle_group"] = np.where(data["vehicle_count"].eq(1), "1 vehicle", "2 or more vehicles")
    data["severity"] = np.select(
        [data["meidsli"].eq(1), data["meidsli"].eq(2)],
        ["Fatal", "Serious"], default="Minor injury",
    )
    data["accident_family"] = data["tegohapps"].map(broad_accident_family)
    result = pd.concat(
        [
            rows(data, "vehicle_group", ["1 vehicle", "2 or more vehicles"]),
            rows(data, "severity", ["Fatal", "Serious", "Minor injury"]),
            rows(data, "season", ["Winter", "Spring", "Summer", "Fall"]),
            rows(data, "daylight_class", ["Darkness", "Civil twilight", "Daylight"]),
            rows(data, "accident_family", sorted(data["accident_family"].dropna().unique())),
        ],
        ignore_index=True,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
