"""Calculate counter-section accident rates from same-day weather exposure."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.traffic.counter_day_weather import VARIABLES, require_columns
COUNTER_DAYS = Path("data/processed/traffic/counter_day_weather.parquet")
ACCIDENTS = Path("data/processed/traffic/counter_accidents.csv")
OUTPUT = Path("data/processed/traffic/daily_vkt.csv")
OUTCOMES = {
    "Minor injury accidents": lambda value: value.eq(3),
    "Severe/fatal accidents": lambda value: value.isin([1, 2]),
}


def allocate_same_day_exposure(
    counter_days: pd.DataFrame, variable: str, bin_labels: list[str]
) -> pd.DataFrame:
    """Allocate each day's vehicle-km using its actual weather observations."""
    valid_column = f"{variable}_valid_observations"
    coverage_column = f"{variable}_coverage_ok"
    bin_columns = [f"{variable}_bin_{label}_count" for label in bin_labels]
    require_columns(
        counter_days,
        {
            "date", "year", "season", "counter_section_id", "vehicle_km",
            "traffic_vehicles", "weather_station_id", valid_column,
            coverage_column, *bin_columns,
        },
        "Counter-day weather",
    )
    days = counter_days[
        counter_days["traffic_vehicles"].gt(0)
        & counter_days[coverage_column].fillna(False)
        & counter_days[valid_column].gt(0)
    ].copy()
    rows: list[pd.DataFrame] = []
    for order, (label, count_column) in enumerate(zip(bin_labels, bin_columns, strict=True)):
        frame = days[
            [
                "date", "year", "season", "counter_section_id",
                "weather_station_id", "vehicle_km", valid_column, count_column,
            ]
        ].copy()
        frame = frame[frame[count_column].gt(0)].copy()
        frame["bin_label"] = label
        frame["bin_order"] = order
        frame["estimated_vehicle_km"] = (
            frame["vehicle_km"] * frame[count_column] / frame[valid_column]
        )
        rows.append(frame)
    exposure = pd.concat(rows, ignore_index=True)
    reconstructed = exposure.groupby(
        ["date", "counter_section_id"], observed=True
    )["estimated_vehicle_km"].sum()
    expected = days.set_index(["date", "counter_section_id"])["vehicle_km"].reindex(
        reconstructed.index
    )
    if not np.allclose(
        reconstructed.to_numpy(float), expected.to_numpy(float), rtol=1e-10, atol=1e-6
    ):
        raise ValueError(f"{variable} allocation does not reconstruct daily vehicle-km")
    exposure["variable"] = variable
    return exposure


def summarise_rates(
    counter_days: pd.DataFrame, accidents: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int]]:
    output: list[pd.DataFrame] = []
    summary: dict[str, int] = {}
    counter_days = counter_days.copy()
    counter_days["date"] = pd.to_datetime(counter_days["date"], errors="raise")
    for variable, (_, raw_labels) in VARIABLES.items():
        bin_labels = list(raw_labels)
        exposure = allocate_same_day_exposure(counter_days, variable, bin_labels)
        valid_days = exposure[["date", "counter_section_id"]].drop_duplicates()
        events = accidents.merge(
            valid_days, on=["date", "counter_section_id"], how="inner",
            validate="many_to_one",
        )
        values = events["temperature"] if variable == "temperature" else events[variable]
        bounds = np.asarray(VARIABLES[variable][0], dtype=float)
        edges = [-np.inf, *bounds, np.inf] if variable == "temperature" else [0, *bounds, np.inf]
        events = events.copy()
        events["bin_label"] = pd.cut(
            values, edges, labels=bin_labels, right=False, include_lowest=True
        )
        events = events.dropna(subset=["bin_label"])
        summary[f"{variable}_accidents"] = events["id"].nunique()
        for outcome, selector in OUTCOMES.items():
            selected = events[selector(events["meidsli"])].copy()
            observed = selected.groupby(
                ["season", "bin_label"], as_index=False, observed=True
            ).agg(accidents=("id", "nunique"))
            observed["period"] = observed["season"].replace({"Fall": "Autumn"})
            annual_observed = selected.groupby(
                "bin_label", as_index=False, observed=True
            ).agg(accidents=("id", "nunique"))
            annual_observed["period"] = "All year"
            observed = pd.concat([annual_observed, observed], ignore_index=True)

            exposure_summary = exposure.groupby(
                ["season", "bin_label", "bin_order"], as_index=False, observed=True
            ).agg(
                estimated_vehicle_km=("estimated_vehicle_km", "sum"),
                counter_days=("date", "size"),
                counter_sections=("counter_section_id", "nunique"),
            )
            exposure_summary["period"] = exposure_summary["season"].replace(
                {"Fall": "Autumn"}
            )
            annual_exposure = exposure.groupby(
                ["bin_label", "bin_order"], as_index=False, observed=True
            ).agg(
                estimated_vehicle_km=("estimated_vehicle_km", "sum"),
                counter_days=("date", "size"),
                counter_sections=("counter_section_id", "nunique"),
            )
            annual_exposure["period"] = "All year"
            exposure_summary = pd.concat(
                [annual_exposure, exposure_summary], ignore_index=True
            )
            result = exposure_summary.merge(
                observed[["period", "bin_label", "accidents"]],
                on=["period", "bin_label"], how="left", validate="one_to_one",
            )
            result["accidents"] = result["accidents"].fillna(0).astype(int)
            result["rate_per_100m_vehicle_km"] = (
                result["accidents"] / result["estimated_vehicle_km"] * 100_000_000
            )
            result["variable"] = variable
            result["outcome"] = outcome
            result["allocation_method"] = "observed daily traffic allocated by same-day 10-minute weather"
            output.append(result)
    combined = pd.concat(output, ignore_index=True)
    combined["_period_order"] = combined["period"].map(
        {"All year": 0, "Winter": 1, "Spring": 2, "Summer": 3, "Autumn": 4}
    )
    combined["_variable_order"] = combined["variable"].map(
        {"f": 0, "fg": 1, "temperature": 2}
    )
    combined["_outcome_order"] = combined["outcome"].map(
        {name: index for index, name in enumerate(OUTCOMES)}
    )
    combined = combined.sort_values(
        ["_variable_order", "_outcome_order", "_period_order", "bin_order"]
    )
    columns = [
        "variable", "outcome", "period", "bin_label", "bin_order", "accidents",
        "estimated_vehicle_km", "rate_per_100m_vehicle_km", "counter_days",
        "counter_sections", "allocation_method",
    ]
    return combined[columns].reset_index(drop=True), summary


def build(
    counter_days_path: Path, accidents_path: Path
) -> tuple[pd.DataFrame, dict[str, int]]:
    counter_days = pd.read_parquet(counter_days_path)
    accidents = pd.read_csv(accidents_path, low_memory=False)
    accidents["date"] = pd.to_datetime(accidents["date"], errors="raise")
    return summarise_rates(counter_days, accidents)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--counter-days", type=Path, default=COUNTER_DAYS)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result, summary = build(args.counter_days, args.accidents)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print("; ".join(f"{key}={value:,}" for key, value in summary.items()))
    print(f"wrote={args.output} rows={len(result):,}")


if __name__ == "__main__":
    main()
