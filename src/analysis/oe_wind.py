"""Compare accident occurrence with local mean-wind frequency.

The observed/expected (O/E) ratio compares the share of accidents in each
mean-wind interval with the share of clean ten-minute observations in that
interval.  Expected counts are calculated within weather station and season,
then pooled.  Traffic volume and road length are not used.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.weather.frequency import F_UPPER_BOUNDS, labels


DEFAULT_ACCIDENTS = Path("data/analysis/accidents.csv")
DEFAULT_CONDITIONS = Path("data/analysis/accident_conditions.csv")
DEFAULT_FREQUENCY = Path("data/analysis/weather_frequency.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/oe_wind.csv")

SEASONS = ["Winter", "Spring", "Summer", "Fall"]
ALL_YEAR = "All year"
WIND_LABELS = labels(F_UPPER_BOUNDS)
WIND_EDGES = [0, *F_UPPER_BOUNDS, np.inf]
OUTCOMES = {
    "Injury accidents": lambda data: pd.Series(True, index=data.index),
    "Serious or fatal": lambda data: data["meidsli"].le(2),
}


def require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    """Raise a useful error when an input table has the wrong schema."""
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def load_inputs(
    accidents_path: Path,
    conditions_path: Path,
    frequency_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and validate the compact analysis-layer inputs."""
    accidents = pd.read_csv(
        accidents_path,
        usecols=["id", "meidsli", "season"],
    )
    conditions = pd.read_csv(
        conditions_path,
        usecols=[
            "id",
            "weather_station_id",
            "weather_station_dist_km",
            "weather_time_difference_minutes",
            "f",
        ],
    )
    frequency = pd.read_csv(frequency_path)
    require_columns(accidents, {"id", "meidsli", "season"}, "Accident input")
    require_columns(
        conditions,
        {
            "id",
            "weather_station_id",
            "weather_station_dist_km",
            "weather_time_difference_minutes",
            "f",
        },
        "Accident-condition input",
    )
    require_columns(
        frequency,
        {
            "station",
            "season",
            "variable",
            "bin_label",
            "measurement_count",
            "total_measurements_in_period",
        },
        "Weather-frequency input",
    )
    if not accidents["id"].is_unique or not conditions["id"].is_unique:
        raise ValueError("Accident and condition IDs must each be unique")
    if set(accidents["id"]) != set(conditions["id"]):
        raise ValueError("Accident and condition IDs do not match")

    events = accidents.merge(conditions, on="id", how="inner", validate="one_to_one")
    events["weather_station_id"] = pd.to_numeric(
        events["weather_station_id"], errors="coerce"
    ).astype("Int64")
    events["meidsli"] = pd.to_numeric(events["meidsli"], errors="raise")

    wind_frequency = frequency[frequency["variable"].eq("f")].copy()
    wind_frequency["station"] = pd.to_numeric(
        wind_frequency["station"], errors="raise"
    ).astype(int)
    duplicate_keys = ["station", "season", "bin_label"]
    if wind_frequency.duplicated(duplicate_keys).any():
        raise ValueError("Wind-frequency input has duplicate station-season-bin rows")
    unexpected_bins = set(wind_frequency["bin_label"]) - set(WIND_LABELS)
    if unexpected_bins:
        raise ValueError(f"Wind-frequency input has unexpected bins: {sorted(unexpected_bins)}")
    return events, wind_frequency


def eligible_events(
    events: pd.DataFrame,
    max_distance_km: float,
    max_time_difference_minutes: float,
) -> pd.DataFrame:
    """Apply the fixed spatial and temporal weather-match requirements."""
    selected = events[
        events["weather_station_id"].notna()
        & events["weather_station_dist_km"].le(max_distance_km)
        & events["weather_time_difference_minutes"].le(
            max_time_difference_minutes
        )
        & events["f"].notna()
    ].copy()
    selected["weather_station_id"] = selected["weather_station_id"].astype(int)
    selected["wind_interval_ms"] = pd.cut(
        selected["f"],
        bins=WIND_EDGES,
        labels=WIND_LABELS,
        right=False,
        include_lowest=True,
    ).astype("string")
    if selected["wind_interval_ms"].isna().any():
        examples = selected.loc[
            selected["wind_interval_ms"].isna(), ["id", "f"]
        ].head()
        raise ValueError(
            "Eligible accidents contain mean wind outside the defined intervals: "
            f"{examples.to_dict('records')}"
        )
    return selected


def expected_by_station_season(
    events: pd.DataFrame,
    frequency: pd.DataFrame,
) -> pd.DataFrame:
    """Return observed and expected counts for each station-season-bin."""
    group_keys = ["weather_station_id", "season"]
    group_totals = (
        events.groupby(group_keys, as_index=False)["id"]
        .nunique()
        .rename(columns={"id": "group_accidents"})
    )
    observed = (
        events.groupby([*group_keys, "wind_interval_ms"], as_index=False)["id"]
        .nunique()
        .rename(columns={"id": "observed_accidents"})
    )
    background = frequency.rename(
        columns={"station": "weather_station_id", "bin_label": "wind_interval_ms"}
    )
    detail = group_totals.merge(
        background[
            [
                "weather_station_id",
                "season",
                "wind_interval_ms",
                "measurement_count",
                "total_measurements_in_period",
            ]
        ],
        on=group_keys,
        how="left",
        validate="one_to_many",
    )
    if detail["measurement_count"].isna().any():
        missing = detail.loc[
            detail["measurement_count"].isna(), group_keys
        ].drop_duplicates()
        raise ValueError(
            "No mean-wind background frequency for accident groups: "
            f"{missing.to_dict('records')}"
        )
    frequency_sums = detail.groupby(group_keys)["measurement_count"].sum()
    reported_totals = detail.groupby(group_keys)[
        "total_measurements_in_period"
    ].first()
    if not np.array_equal(
        frequency_sums.to_numpy(dtype=np.int64),
        reported_totals.to_numpy(dtype=np.int64),
    ):
        raise ValueError("Mean-wind bin counts do not reconstruct station-season totals")

    detail = detail.merge(
        observed,
        on=[*group_keys, "wind_interval_ms"],
        how="left",
        validate="one_to_one",
    )
    detail["observed_accidents"] = detail["observed_accidents"].fillna(0).astype(int)
    detail["expected_accidents"] = (
        detail["group_accidents"]
        * detail["measurement_count"]
        / detail["total_measurements_in_period"]
    )
    return detail


def bootstrap_intervals(
    detail: pd.DataFrame,
    repetitions: int,
    seed: int,
) -> pd.DataFrame:
    """Bootstrap whole weather stations and return percentile intervals."""
    station_bins = detail.groupby(
        ["weather_station_id", "wind_interval_ms"], as_index=False
    ).agg(
        observed_accidents=("observed_accidents", "sum"),
        expected_accidents=("expected_accidents", "sum"),
    )
    observed = station_bins.pivot(
        index="weather_station_id",
        columns="wind_interval_ms",
        values="observed_accidents",
    ).reindex(columns=WIND_LABELS, fill_value=0).fillna(0)
    expected = station_bins.pivot(
        index="weather_station_id",
        columns="wind_interval_ms",
        values="expected_accidents",
    ).reindex(index=observed.index, columns=WIND_LABELS, fill_value=0).fillna(0)
    station_count = len(observed)
    if station_count == 0:
        raise ValueError("No weather stations remain for the requested analysis")
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(
        station_count,
        np.full(station_count, 1 / station_count),
        size=repetitions,
    )
    observed_draws = weights @ observed.to_numpy(float)
    expected_draws = weights @ expected.to_numpy(float)
    ratios = np.divide(
        observed_draws,
        expected_draws,
        out=np.full_like(observed_draws, np.nan),
        where=expected_draws > 0,
    )
    return pd.DataFrame(
        {
            "wind_interval_ms": WIND_LABELS,
            "ci_95_low": np.nanpercentile(ratios, 2.5, axis=0),
            "ci_95_high": np.nanpercentile(ratios, 97.5, axis=0),
            "bootstrap_probability_above_1": np.nanmean(ratios > 1, axis=0),
            "bootstrap_stations": station_count,
            "bootstrap_repetitions": repetitions,
        }
    )


def analyse_one(
    events: pd.DataFrame,
    frequency: pd.DataFrame,
    outcome: str,
    period: str,
    bootstrap_repetitions: int,
    seed: int,
) -> pd.DataFrame:
    """Calculate one outcome-period table."""
    selected = events[OUTCOMES[outcome](events)].copy()
    if period != ALL_YEAR:
        selected = selected[selected["season"].eq(period)].copy()
    if selected.empty:
        raise ValueError(f"No accidents remain for {outcome}, {period}")
    detail = expected_by_station_season(selected, frequency)
    result = detail.groupby("wind_interval_ms", as_index=False).agg(
        observed_accidents=("observed_accidents", "sum"),
        expected_accidents=("expected_accidents", "sum"),
        background_measurements=("measurement_count", "sum"),
        contributing_stations=("weather_station_id", "nunique"),
    )
    result["relative_accident_frequency"] = (
        result["observed_accidents"] / result["expected_accidents"]
    )
    result = result.merge(
        bootstrap_intervals(detail, bootstrap_repetitions, seed),
        on="wind_interval_ms",
        how="left",
        validate="one_to_one",
    )
    analysed_accidents = selected["id"].nunique()
    if int(result["observed_accidents"].sum()) != analysed_accidents:
        raise ValueError("Observed bin counts do not sum to analysed accidents")
    if not np.isclose(result["expected_accidents"].sum(), analysed_accidents):
        raise ValueError("Expected bin counts do not sum to analysed accidents")
    result["outcome"] = outcome
    result["period"] = period
    result["analysed_accidents"] = analysed_accidents
    return result


def analyse(
    events: pd.DataFrame,
    frequency: pd.DataFrame,
    bootstrap_repetitions: int,
    seed: int,
) -> pd.DataFrame:
    """Calculate both outcomes for the whole year and each season."""
    results = []
    scenario = 0
    for outcome in OUTCOMES:
        for period in [ALL_YEAR, *SEASONS]:
            results.append(
                analyse_one(
                    events,
                    frequency,
                    outcome,
                    period,
                    bootstrap_repetitions,
                    seed + scenario,
                )
            )
            scenario += 1
    output = pd.concat(results, ignore_index=True)
    output["outcome_order"] = output["outcome"].map(
        {name: index for index, name in enumerate(OUTCOMES)}
    )
    output["period_order"] = output["period"].map(
        {name: index for index, name in enumerate([ALL_YEAR, *SEASONS])}
    )
    output["wind_order"] = output["wind_interval_ms"].map(
        {name: index for index, name in enumerate(WIND_LABELS)}
    )
    output = output.sort_values(["outcome_order", "period_order", "wind_order"])
    columns = [
        "outcome",
        "period",
        "wind_interval_ms",
        "observed_accidents",
        "expected_accidents",
        "relative_accident_frequency",
        "ci_95_low",
        "ci_95_high",
        "bootstrap_probability_above_1",
        "analysed_accidents",
        "background_measurements",
        "contributing_stations",
        "bootstrap_stations",
        "bootstrap_repetitions",
    ]
    return output[columns].reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-c", "--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("-f", "--frequency", type=Path, default=DEFAULT_FREQUENCY)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-b", "--bootstrap-repetitions", type=int, default=5000)
    parser.add_argument("-s", "--seed", type=int, default=20260910)
    parser.add_argument("-r", "--max-distance-km", type=float, default=20.0)
    parser.add_argument(
        "-t", "--max-time-difference-minutes", type=float, default=5.0
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.bootstrap_repetitions <= 0:
        raise ValueError("Bootstrap repetitions must be positive")
    events, frequency = load_inputs(
        args.accidents, args.conditions, args.frequency
    )
    events = eligible_events(
        events, args.max_distance_km, args.max_time_difference_minutes
    )
    result = analyse(events, frequency, args.bootstrap_repetitions, args.seed)
    result["max_distance_km"] = args.max_distance_km
    result["max_time_difference_minutes"] = args.max_time_difference_minutes
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))
    print(f"wrote={args.output} rows={len(result):,}")


if __name__ == "__main__":
    main()
