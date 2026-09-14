"""Correct whole-year weather O/E using observed daily traffic response."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.oe_analysis import (
    DEFAULT_ACCIDENTS,
    DEFAULT_CONDITIONS,
    WHOLE_YEAR_PERIOD,
    analyse,
    load_data,
)


YEARLY_FREQUENCY = Path("data/analysis/weather_yearly.csv")
TRAFFIC_RESPONSE = Path("data/analysis/traffic_weather_response.csv")
UNCORRECTED = Path("reports/main/tables/weather_oe_2019_2024.csv")
OUTPUT = Path("reports/main/tables/weather_oe_traffic_corrected_2019_2024.csv")


def adjust_frequency(
    frequency: pd.DataFrame, response: pd.DataFrame
) -> pd.DataFrame:
    """Apply and normalize variable-bin traffic multipliers within each stratum."""
    required = {"variable", "bin_label", "traffic_multiplier"}
    missing = required - set(response)
    if missing:
        raise ValueError(
            f"Traffic response is missing columns: {sorted(missing)}"
        )
    multipliers = response[
        ["variable", "bin_label", "traffic_multiplier"]
    ].copy()
    if multipliers.duplicated(["variable", "bin_label"]).any():
        raise ValueError("Traffic response has duplicate variable-bin rows")
    adjusted = frequency.merge(
        multipliers,
        on=["variable", "bin_label"],
        how="left",
        validate="many_to_one",
    )
    invalid = (
        adjusted["traffic_multiplier"].isna()
        | ~np.isfinite(adjusted["traffic_multiplier"])
        | adjusted["traffic_multiplier"].le(0)
    )
    if invalid.any():
        cells = adjusted.loc[invalid, ["variable", "bin_label"]].drop_duplicates()
        raise ValueError(
            "Missing or invalid traffic multipliers: "
            + cells.to_dict("records").__repr__()
        )
    adjusted["weighted_frequency"] = (
        adjusted["frequency_pct"] * adjusted["traffic_multiplier"]
    )
    keys = ["weather_station_id", "season", "variable"]
    total = adjusted.groupby(keys, observed=True)[
        "weighted_frequency"
    ].transform("sum")
    if total.le(0).any():
        raise ValueError("Traffic-adjusted frequency has a nonpositive total")
    adjusted["frequency_pct"] = 100 * adjusted["weighted_frequency"] / total
    check = adjusted.groupby(keys, observed=True)["frequency_pct"].sum()
    if not np.allclose(check, 100, rtol=0, atol=1e-8):
        raise ValueError("Traffic-adjusted frequencies do not sum to 100%")
    return adjusted.drop(columns="weighted_frequency")


def build_result(
    accidents: pd.DataFrame,
    frequency: pd.DataFrame,
    response: pd.DataFrame,
    uncorrected: pd.DataFrame,
) -> pd.DataFrame:
    """Return original and corrected expected counts in one auditable table."""
    adjusted = adjust_frequency(frequency, response)
    corrected = analyse(accidents, adjusted, periods=WHOLE_YEAR_PERIOD)
    keys = ["variable", "outcome", "period", "bin_label", "bin_order"]
    original_columns = [
        *keys,
        "observed_accidents",
        "expected_accidents",
        "relative_accident_frequency",
        "analysed_accidents",
    ]
    missing = set(original_columns) - set(uncorrected)
    if missing:
        raise ValueError(f"Uncorrected O/E table is missing: {sorted(missing)}")
    original = uncorrected[original_columns].rename(
        columns={
            "expected_accidents": "time_expected_accidents",
            "relative_accident_frequency": "time_oe",
        }
    )
    corrected = corrected[
        [*keys, "observed_accidents", "expected_accidents",
         "relative_accident_frequency", "analysed_accidents"]
    ].rename(
        columns={
            "observed_accidents": "corrected_observed_accidents",
            "expected_accidents": "traffic_corrected_expected_accidents",
            "relative_accident_frequency": "traffic_corrected_oe",
            "analysed_accidents": "corrected_analysed_accidents",
        }
    )
    result = original.merge(
        corrected, on=keys, how="inner", validate="one_to_one"
    )
    if not result["observed_accidents"].eq(
        result["corrected_observed_accidents"]
    ).all():
        raise ValueError("Traffic correction changed observed accident counts")
    if not result["analysed_accidents"].eq(
        result["corrected_analysed_accidents"]
    ).all():
        raise ValueError("Traffic correction changed analysed sample sizes")
    multipliers = response[
        ["variable", "bin_label", "traffic_multiplier", "traffic_change_pct"]
    ]
    result = result.merge(
        multipliers,
        on=["variable", "bin_label"],
        how="left",
        validate="many_to_one",
    )
    result["analysis_period"] = "2019-2024"
    columns = [
        *keys,
        "observed_accidents",
        "time_expected_accidents",
        "time_oe",
        "traffic_multiplier",
        "traffic_change_pct",
        "traffic_corrected_expected_accidents",
        "traffic_corrected_oe",
        "analysed_accidents",
        "analysis_period",
    ]
    return result[columns].sort_values(
        ["variable", "outcome", "period", "bin_order"]
    ).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-C", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("-f", "--frequency", type=Path, default=YEARLY_FREQUENCY)
    parser.add_argument("-r", "--traffic-response", type=Path, default=TRAFFIC_RESPONSE)
    parser.add_argument("-u", "--uncorrected", type=Path, default=UNCORRECTED)
    parser.add_argument("--start-year", type=int, default=2019)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    accidents, frequency = load_data(
        args.accidents,
        args.conditions,
        args.frequency,
        None,
        None,
        args.start_year,
        args.end_year,
    )
    result = build_result(
        accidents,
        frequency,
        pd.read_csv(args.traffic_response),
        pd.read_csv(args.uncorrected),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"wrote={args.output} rows={len(result):,}")


if __name__ == "__main__":
    main()
