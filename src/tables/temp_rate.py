"""Estimate temperature rate ratios from road-period vehicle-kilometres."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.tables.rate import fit_model


INPUT = Path("data/analysis/road_temperature.csv")
OUTPUT = Path("reports/main/tables/temperature_rate.csv")
REFERENCE = "0-3"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.input.suffix.lower() != ".csv":
        raise ValueError(f"Analysis input must be CSV: {args.input}")
    source = pd.read_csv(args.input)
    required = {
        "year", "road_section", "traffic_period", "temperature_bin",
        "temperature_bin_lower_c", "estimated_vehicle_km", "injury_accidents",
    }
    missing = required - set(source)
    if missing:
        raise ValueError(f"Temperature-rate input is missing columns: {sorted(missing)}")
    data = source.rename(
        columns={
            "temperature_bin": "wind_bin",
            "temperature_bin_lower_c": "wind_bin_lower_ms",
            "injury_accidents": "observed_accidents",
        }
    ).copy()
    data["stratum"] = (
        data["road_section"].astype(str)
        + "|" + data["year"].astype(str)
        + "|" + data["traffic_period"].astype(str)
    )
    informative = data.groupby("stratum")["observed_accidents"].transform("sum").gt(0)
    data = data[informative & data["estimated_vehicle_km"].gt(0)].copy()
    if data.empty:
        raise ValueError("No informative temperature-rate strata remain")
    result = fit_model(data, baseline=REFERENCE).rename(
        columns={"wind_bin": "bin_label", "wind_bin_lower_ms": "bin_lower_c"}
    )
    result["reference_bin"] = REFERENCE
    result["analysis_variable"] = "temperature"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
