"""Accident rates from daily traffic allocated by pooled monthly weather frequency.

For each counter-section/day, the full rural vehicle-km total is distributed
over the bins using the assigned station's 07:00--24:00 calendar-month weather
frequency pooled across 2007--2025. Accident bins use observed event-time
weather. Every eligible positive-traffic day contributes to the denominator.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.traffic.counter_days import require_columns
from src.weather.monthly_frequency import VARIABLES


COUNTER_DAYS = Path("data/processed/traffic/counter_days.csv")
ACCIDENTS = Path("data/processed/traffic/counter_accidents.csv")
MONTHLY_FREQUENCY = Path("data/processed/weather/monthly_frequency.csv")
OUTPUT = Path("data/processed/traffic/monthly_vkt.csv")
SECTION_OUTPUT = Path("data/processed/traffic/monthly_vkt_section.csv")
ALLOCATION_METHOD = (
    "full rural daily vehicle-km allocated by assigned-station calendar-month "
    "07:00-24:00 weather frequency pooled across 2007-2025"
)
OUTCOMES = {
    "All injury accidents": lambda value: value.isin([1, 2, 3]),
    "Minor injury accidents": lambda value: value.eq(3),
    "Serious or fatal injury accidents": lambda value: value.isin([1, 2]),
}


def _bin_values(values: pd.Series, variable: str) -> pd.Categorical:
    bounds, labels = VARIABLES[variable]
    return pd.cut(
        pd.to_numeric(values, errors="coerce"),
        [0, *bounds, np.inf], labels=list(labels), right=False,
        include_lowest=True,
    )


def allocate_monthly_exposure(
    counter_days: pd.DataFrame, frequency: pd.DataFrame, variable: str,
) -> pd.DataFrame:
    """Allocate all recorded nonnegative counter-days and conserve VKT."""
    require_columns(counter_days, {
        "date", "year", "season", "month", "counter_section_id",
        "weather_station_id", "traffic_vehicles", "rural_section_length_km",
        "vehicle_km",
    }, "Counter days")
    require_columns(frequency, {
        "weather_station_id", "month", "variable", "bin_label", "bin_order",
        "frequency", "first_year", "last_year", "start_hour", "end_hour",
    }, "Monthly weather frequency")
    days = counter_days.copy()
    days["date"] = pd.to_datetime(days["date"], errors="raise")
    if days.duplicated(["counter_section_id", "date"]).any():
        raise ValueError("Duplicate counter-days")
    days = days[
        days["traffic_vehicles"].ge(0)
        & days["vehicle_km"].ge(0)
        & days["rural_section_length_km"].gt(0)
    ].copy()
    if not np.allclose(
        days["vehicle_km"],
        days["traffic_vehicles"] * days["rural_section_length_km"],
        rtol=1e-10, atol=1e-6,
    ):
        raise ValueError("Vehicle-km must equal traffic vehicles times rural length")

    freq = frequency[frequency["variable"].eq(variable)].copy()
    if not (
        freq["first_year"].eq(2007).all()
        and freq["last_year"].eq(2025).all()
        and freq["start_hour"].eq(7).all()
        and freq["end_hour"].eq(24).all()
    ):
        raise ValueError("Monthly frequency does not represent pooled 2007-2025 07:00-24:00 weather")
    keys = ["weather_station_id", "month"]
    valid = freq.groupby(keys, observed=True)["frequency"].sum()
    valid = valid[np.isclose(valid, 1.0, rtol=0, atol=1e-10)].index
    freq = freq.set_index(keys).loc[valid].reset_index()
    expected = dict(enumerate(VARIABLES[variable][1]))
    if not freq["bin_order"].map(expected).eq(freq["bin_label"]).all():
        raise ValueError("Monthly frequency bins disagree with analysis bins")
    exposure = days.merge(
        freq[[*keys, "bin_label", "bin_order", "frequency"]],
        on=keys, how="inner", validate="many_to_many",
    )
    exposure["estimated_vehicle_km"] = exposure["vehicle_km"] * exposure["frequency"]
    reconstructed = exposure.groupby(["counter_section_id", "date"], observed=True)[
        "estimated_vehicle_km"
    ].sum()
    source = days.set_index(["counter_section_id", "date"])["vehicle_km"].reindex(reconstructed.index)
    if not np.allclose(reconstructed, source, rtol=1e-10, atol=1e-6):
        raise ValueError("Monthly allocation does not conserve daily vehicle-km")
    exposure["variable"] = variable
    exposure["counter_day_key"] = exposure.groupby(
        ["counter_section_id", "date"], observed=True
    ).ngroup()
    return exposure


def build_tables(
    counter_days: pd.DataFrame, accidents: pd.DataFrame, frequency: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int | float]]:
    accidents = accidents.copy()
    accidents["date"] = pd.to_datetime(accidents["date"], errors="raise")
    if accidents["id"].duplicated().any():
        raise ValueError("Duplicate accident IDs")
    if not accidents["id"].nunique() == 694:
        raise ValueError(f"Expected 694 numerator-eligible accidents, found {accidents['id'].nunique()}")
    output: list[pd.DataFrame] = []
    sections: list[pd.DataFrame] = []
    audit: dict[str, int | float] = {"numerator_eligible_accidents": 694}
    for variable in ("f", "fg"):
        exposure = allocate_monthly_exposure(counter_days, frequency, variable)
        eligible_days = exposure[["counter_section_id", "date"]].drop_duplicates()
        events = accidents.merge(
            eligible_days, on=["counter_section_id", "date"], how="inner",
            validate="many_to_one",
        )
        events["bin_label"] = _bin_values(events[variable], variable)
        events = events.dropna(subset=["bin_label"]).copy()
        if events["id"].nunique() != 694:
            raise ValueError(f"{variable}: monthly denominator does not cover all 694 accidents")
        audit[f"{variable}_accidents"] = events["id"].nunique()
        audit[f"{variable}_counter_days"] = exposure["counter_day_key"].nunique()
        audit[f"{variable}_allocated_vkt"] = exposure["estimated_vehicle_km"].sum()

        section_exposure = exposure.groupby(
            ["variable", "counter_section_id", "year", "season", "bin_label", "bin_order"],
            as_index=False, observed=True,
        ).agg(
            estimated_vehicle_km=("estimated_vehicle_km", "sum"),
            counter_days=("counter_day_key", "nunique"),
        )
        section_observed = events.groupby(
            ["counter_section_id", "year", "season", "bin_label"],
            as_index=False, observed=True,
        ).agg(observed_accidents=("id", "nunique"))
        section = section_exposure.merge(
            section_observed,
            on=["counter_section_id", "year", "season", "bin_label"],
            how="left", validate="one_to_one",
        )
        section["observed_accidents"] = section["observed_accidents"].fillna(0).astype(int)
        sections.append(section)

        exposure_summary = exposure.groupby(
            ["bin_label", "bin_order"], as_index=False, observed=True,
        ).agg(
            estimated_vehicle_km=("estimated_vehicle_km", "sum"),
            counter_days=("counter_day_key", "nunique"),
            counter_sections=("counter_section_id", "nunique"),
        )
        for outcome, selector in OUTCOMES.items():
            selected = events[selector(events["meidsli"])]
            observed = selected.groupby("bin_label", as_index=False, observed=True).agg(
                observed_accidents=("id", "nunique")
            )
            result = exposure_summary.merge(observed, on="bin_label", how="left", validate="one_to_one")
            result["observed_accidents"] = result["observed_accidents"].fillna(0).astype(int)
            result["rate_per_million_vehicle_km"] = (
                result["observed_accidents"] / result["estimated_vehicle_km"] * 1_000_000
            )
            result["variable"] = variable
            result["outcome"] = outcome
            result["analysed_accidents"] = selected["id"].nunique()
            result["allocation_method"] = ALLOCATION_METHOD
            output.append(result)
    rates = pd.concat(output, ignore_index=True)
    rates = rates[[
        "variable", "outcome", "bin_label", "bin_order", "observed_accidents",
        "estimated_vehicle_km", "rate_per_million_vehicle_km", "counter_days",
        "counter_sections", "analysed_accidents", "allocation_method",
    ]].sort_values(["variable", "outcome", "bin_order"]).reset_index(drop=True)
    return rates, pd.concat(sections, ignore_index=True), audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--counter-days", type=Path, default=COUNTER_DAYS)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-f", "--frequency", type=Path, default=MONTHLY_FREQUENCY)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("--section-output", type=Path, default=SECTION_OUTPUT)
    args = parser.parse_args()
    rates, sections, audit = build_tables(
        pd.read_csv(args.counter_days), pd.read_csv(args.accidents), pd.read_csv(args.frequency)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rates.to_csv(args.output, index=False)
    sections.to_csv(args.section_output, index=False)
    print("; ".join(f"{key}={value:,}" for key, value in audit.items()))
    print(f"wrote={args.output} rows={len(rates):,}")
    print(f"wrote={args.section_output} rows={len(sections):,}")


if __name__ == "__main__":
    main()
