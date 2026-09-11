"""Summarise sample reconstruction and sparse intervals for every O/E panel."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


INPUT = Path("reports/main/tables/weather_oe.csv")
OUTPUT = Path("reports/main/tables/weather_oe_audit.csv")


def build(data: pd.DataFrame) -> pd.DataFrame:
    required = {
        "variable", "outcome", "period", "observed_accidents",
        "expected_accidents", "analysed_accidents", "contributing_stations",
        "sparse_bin",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"O/E result is missing columns: {sorted(missing)}")
    result = data.groupby(
        ["variable", "outcome", "period"], as_index=False, observed=True
    ).agg(
        analysed_accidents=("analysed_accidents", "first"),
        observed_total=("observed_accidents", "sum"),
        expected_total=("expected_accidents", "sum"),
        contributing_stations=("contributing_stations", "max"),
        sparse_intervals=("sparse_bin", "sum"),
    )
    if not result["observed_total"].eq(result["analysed_accidents"]).all():
        raise ValueError("O/E observed totals do not reconstruct every panel")
    if not np.allclose(
        result["expected_total"], result["analysed_accidents"], atol=1e-6
    ):
        raise ValueError("O/E expected totals do not reconstruct every panel")
    result["expected_total"] = result["expected_total"].round(6)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"wrote={args.output} rows={len(result):,}")


if __name__ == "__main__":
    main()
