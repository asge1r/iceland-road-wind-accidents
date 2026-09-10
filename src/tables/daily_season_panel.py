"""Build the common counter-year-season input for seasonal traffic analyses."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.tables.counter_rate import ACCIDENTS, DAILY, require_columns


MATCHES = Path("data/analysis/counter_wind.csv")
OUTPUT = Path("reports/working/tables/daily_season_panel.csv")
LABELS = ["0-10", "10-15", ">=15"]
SEASONS = ["Winter", "Spring", "Summer", "Fall"]
COUNT_COLUMNS = {
    "0-10": ["f_full_bin_0_5_count", "f_full_bin_5_10_count"],
    "10-15": ["f_full_bin_10_15_count"],
    ">=15": [
        "f_full_bin_15_20_count",
        "f_full_bin_20_25_count",
        "f_full_bin_ge25_count",
    ],
}


def season_from_month(month: pd.Series) -> pd.Series:
    result = pd.Series(index=month.index, dtype="string")
    result[month.isin([12, 1, 2, 3])] = "Winter"
    result[month.isin([4, 5])] = "Spring"
    result[month.isin([6, 7, 8, 9])] = "Summer"
    result[month.isin([10, 11])] = "Fall"
    if result.isna().any():
        raise ValueError("Could not assign season to every row")
    return result


def build_panel(
    accidents_path: Path,
    matches_path: Path,
    daily_path: Path,
    max_distance_km: float,
) -> pd.DataFrame:
    """Return one row per counter, year, season and wind category."""
    accidents = pd.read_csv(accidents_path)
    matches = pd.read_csv(matches_path)
    daily = pd.read_csv(daily_path)

    require_columns(accidents, {"id", "timestamp", "year", "season"}, "Accident input")
    require_columns(
        matches,
        {
            "id", "year", "date", "counter_id", "counter_distance_km",
            "counter_weather_station_id", "counter_weather_station_dist_km",
            "counter_station_accident_distance_km",
            "weather_time_difference_minutes", "f",
        },
        "Daily accident-weather input",
    )
    all_bin_columns = [column for columns in COUNT_COLUMNS.values() for column in columns]
    require_columns(
        daily,
        {"date", "counter_id", "traffic", "weather_station_id",
         "full_observation_count", *all_bin_columns},
        "Daily traffic input",
    )
    if matches["id"].duplicated().any():
        raise ValueError("Daily accident-weather rows are not unique by id")

    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"], errors="raise")
    accidents = accidents[accidents["year"].between(2019, 2024)].copy()
    matches["date"] = pd.to_datetime(matches["date"], errors="raise")
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    daily["year"] = daily["date"].dt.year
    daily["season"] = season_from_month(daily["date"].dt.month)

    matches = matches[
        matches["counter_distance_km"].le(max_distance_km)
        & matches["counter_weather_station_dist_km"].le(max_distance_km)
        & matches["counter_station_accident_distance_km"].le(max_distance_km)
        & matches["weather_time_difference_minutes"].le(5)
    ].copy()
    events = matches.merge(
        accidents[["id", "timestamp", "season"]],
        on="id", how="inner", validate="one_to_one",
    )

    valid_daily = daily[
        daily["traffic"].gt(0) & daily["full_observation_count"].ge(108)
    ].copy()
    if not valid_daily[all_bin_columns].sum(axis=1).eq(
        valid_daily["full_observation_count"]
    ).all():
        raise ValueError("Wind-bin counts do not reconstruct full observation counts")

    events = events.merge(
        valid_daily[["counter_id", "date", "weather_station_id"]],
        on=["counter_id", "date"], how="inner", validate="many_to_one",
    )
    if not events["counter_weather_station_id"].eq(events["weather_station_id"]).all():
        raise ValueError("Accident and counter-day exposure use different weather stations")

    events = events[events["f"].between(0, 45, inclusive="left")].copy()
    events["wind_bin"] = pd.cut(
        events["f"], [0, 10, 15, np.inf], labels=LABELS,
        right=False, include_lowest=True,
    ).astype("string")
    if not events["season"].astype("string").eq(
        season_from_month(events["timestamp"].dt.month)
    ).all():
        raise ValueError("Accident season disagrees with timestamp-derived season")

    event_counts = events.groupby(
        ["counter_id", "year", "season", "wind_bin"],
        observed=True, as_index=False,
    ).agg(observed_accidents=("id", "nunique"))

    exposure_rows: list[pd.DataFrame] = []
    for label, columns in COUNT_COLUMNS.items():
        frame = valid_daily[
            ["counter_id", "year", "date", "season", "traffic",
             "full_observation_count"]
        ].copy()
        frame["wind_bin"] = label
        frame["wind_observations"] = valid_daily[columns].sum(axis=1)
        frame = frame[frame["wind_observations"].gt(0)].copy()
        frame["allocated_vehicles"] = (
            frame["traffic"] * frame["wind_observations"]
            / frame["full_observation_count"]
        )
        exposure_rows.append(frame)

    exposure = pd.concat(exposure_rows, ignore_index=True)
    reconstructed = exposure.groupby(["counter_id", "date"])["allocated_vehicles"].sum()
    original = valid_daily.set_index(["counter_id", "date"])["traffic"].reindex(
        reconstructed.index
    )
    if not np.allclose(
        reconstructed.to_numpy(float), original.to_numpy(float),
        rtol=1e-10, atol=1e-6,
    ):
        raise ValueError("Allocated wind exposure does not reconstruct daily traffic")

    exposure = exposure.groupby(
        ["counter_id", "year", "season", "wind_bin"],
        observed=True, as_index=False,
    ).agg(
        allocated_vehicles=("allocated_vehicles", "sum"),
        counter_days=("date", "nunique"),
    )
    panel = exposure.merge(
        event_counts,
        on=["counter_id", "year", "season", "wind_bin"],
        how="left", validate="one_to_one",
    )
    panel["observed_accidents"] = panel["observed_accidents"].fillna(0).astype(int)
    panel["stratum"] = (
        panel["counter_id"].astype(str) + "|" + panel["year"].astype(str)
        + "|" + panel["season"].astype(str)
    )
    panel = panel[panel["allocated_vehicles"].gt(0)].copy()
    # Zero-accident strata cannot contribute to the conditional or O/E
    # comparisons. Excluding them here keeps the shared analysis file compact.
    has_accident = panel.groupby("stratum")["observed_accidents"].transform("sum").gt(0)
    panel = panel[has_accident].copy()
    panel["season"] = pd.Categorical(panel["season"], SEASONS, ordered=True)
    panel["wind_bin"] = pd.Categorical(panel["wind_bin"], LABELS, ordered=True)
    return panel.sort_values(["season", "counter_id", "year", "wind_bin"]).reset_index(drop=True)


def read_panel(path: Path) -> pd.DataFrame:
    panel = pd.read_csv(path)
    require_columns(
        panel,
        {"counter_id", "year", "season", "wind_bin", "allocated_vehicles",
         "counter_days", "observed_accidents", "stratum"},
        "Seasonal traffic panel",
    )
    return panel


def informative_model_data(data: pd.DataFrame) -> pd.DataFrame:
    group_rows = data.groupby("stratum")["wind_bin"].transform("size")
    outcome_variation = data.groupby("stratum")["observed_accidents"].transform("nunique")
    result = data[group_rows.ge(2) & outcome_variation.ge(2)].copy()
    if result.empty:
        raise ValueError("No informative strata remain")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-m", "--matches", type=Path, default=MATCHES)
    parser.add_argument("-d", "--daily-traffic", type=Path, default=DAILY)
    parser.add_argument("-r", "--max-distance-km", type=float, default=20.0)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    panel = build_panel(
        args.accidents, args.matches, args.daily_traffic, args.max_distance_km
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.output, index=False)
    summary = panel.groupby("season", observed=True).agg(
        accidents=("observed_accidents", "sum"),
        strata=("stratum", "nunique"),
        counters=("counter_id", "nunique"),
        rows=("wind_bin", "size"),
    )
    print(f"wrote={args.output} rows={len(panel)}")
    print(summary.to_string())


if __name__ == "__main__":
    main()
