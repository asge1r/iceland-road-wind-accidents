"""Compare accidents retained and excluded by the daily-counter linkage."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ACCIDENTS = Path("data/analysis/accidents.csv")
MATCHES = Path("data/analysis/counter_wind.csv")
DAILY = Path("data/analysis/daily_traffic.csv")
LOCATIONS = Path("data/analysis/counter_locations.csv")
OUTPUT = Path("reports/main/tables/daily_sample.csv")
EXCLUSIONS = Path("reports/main/tables/daily_exclusions.csv")
MAP_POINTS = Path("reports/main/tables/daily_map.csv")
YEARS = range(2019, 2025)
GROUP_ORDER = [
    "All accidents",
    "No exact counter link",
    "Exact link, not retained",
    "Allocated-rate sample",
]


def require_columns(data: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(data)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def selected_ids(
    matches: pd.DataFrame,
    daily: pd.DataFrame,
    max_distance_km: float,
) -> set[int]:
    """Return IDs satisfying the allocated daily-rate selection rules."""
    matches["date"] = pd.to_datetime(matches["date"], errors="raise")
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    eligible = matches[
        matches["counter_distance_km"].le(max_distance_km)
        & matches["counter_weather_station_dist_km"].le(max_distance_km)
        & matches["counter_station_accident_distance_km"].le(max_distance_km)
        & matches["weather_time_difference_minutes"].le(5)
        & matches["f"].between(0, 45, inclusive="left")
    ].copy()
    valid_daily = daily[
        daily["traffic"].gt(0) & daily["full_observation_count"].ge(108)
    ][["counter_id", "date", "weather_station_id"]]
    eligible = eligible.merge(
        valid_daily,
        on=["counter_id", "date"],
        how="inner",
        validate="many_to_one",
    )
    eligible = eligible[
        eligible["counter_weather_station_id"].eq(eligible["weather_station_id"])
    ]
    return set(eligible["id"].astype(int))


def summarise(group: str, data: pd.DataFrame, total: int) -> dict[str, object]:
    count = len(data)
    severity = pd.to_numeric(data["meidsli"], errors="raise")
    vehicles = pd.to_numeric(data["vehicle_count"], errors="coerce")
    result: dict[str, object] = {
        "group": group,
        "accidents": count,
        "share_of_all_pct": 100 * count / total,
        "road_sections": data["road_section"].nunique(),
        "serious_or_fatal_pct": 100 * severity.le(2).mean(),
        "one_vehicle_pct": 100 * vehicles.eq(1).mean(),
    }
    for season in ["Winter", "Spring", "Summer", "Fall"]:
        result[f"{season.lower()}_pct"] = 100 * data["season"].eq(season).mean()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-m", "--matches", type=Path, default=MATCHES)
    parser.add_argument("-d", "--daily-traffic", type=Path, default=DAILY)
    parser.add_argument("-l", "--locations", type=Path, default=LOCATIONS)
    parser.add_argument("-r", "--max-distance-km", type=float, default=20.0)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-e", "--exclusions", type=Path, default=EXCLUSIONS)
    parser.add_argument("-P", "--map-points", type=Path, default=MAP_POINTS)
    args = parser.parse_args()
    for path in [args.accidents, args.matches, args.daily_traffic, args.locations]:
        if path.suffix.lower() != ".csv":
            raise ValueError(f"Analysis input must be CSV: {path}")
    if args.max_distance_km <= 0:
        raise ValueError("Maximum distance must be positive")

    accidents = pd.read_csv(args.accidents)
    matches = pd.read_csv(args.matches)
    daily = pd.read_csv(args.daily_traffic)
    locations = pd.read_csv(args.locations)
    require_columns(
        accidents,
        {"id", "year", "road_section", "meidsli", "vehicle_count", "season"},
        "Accident input",
    )
    require_columns(
        matches,
        {
            "id",
            "date",
            "counter_id",
            "counter_distance_km",
            "counter_weather_station_id",
            "counter_weather_station_dist_km",
            "counter_station_accident_distance_km",
            "weather_time_difference_minutes",
            "f",
        },
        "Counter-wind input",
    )
    require_columns(
        daily,
        {
            "counter_id",
            "date",
            "traffic",
            "weather_station_id",
            "full_observation_count",
        },
        "Daily-traffic input",
    )
    require_columns(
        locations,
        {"year", "road_section", "lon", "lat"},
        "Counter-location input",
    )
    if accidents["id"].duplicated().any() or matches["id"].duplicated().any():
        raise ValueError("Accident and counter-wind identifiers must be unique")

    accidents = accidents[accidents["year"].isin(YEARS)].copy()
    exact_ids = set(matches["id"].astype(int))
    retained_ids = selected_ids(matches, daily, args.max_distance_km)
    accident_ids = set(accidents["id"].astype(int))
    if not retained_ids <= exact_ids <= accident_ids:
        raise ValueError("Daily-counter selection contains an unexpected accident ID")

    groups = {
        "All accidents": accidents,
        "No exact counter link": accidents[~accidents["id"].isin(exact_ids)],
        "Exact link, not retained": accidents[
            accidents["id"].isin(exact_ids - retained_ids)
        ],
        "Allocated-rate sample": accidents[accidents["id"].isin(retained_ids)],
    }
    if sum(len(groups[name]) for name in GROUP_ORDER[1:]) != len(accidents):
        raise ValueError("Daily-counter selection groups do not partition accidents")
    result = pd.DataFrame(
        [summarise(name, groups[name], len(accidents)) for name in GROUP_ORDER]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    no_link = groups["No exact counter link"].copy()
    no_link["section_year"] = list(
        zip(no_link["year"].astype(int), no_link["road_section"].astype(str))
    )
    all_sections = set(locations["road_section"].dropna().astype(str))
    all_section_years = set(
        zip(locations["year"].astype(int), locations["road_section"].astype(str))
    )
    located = locations.dropna(subset=["lon", "lat"])
    located_section_years = set(
        zip(located["year"].astype(int), located["road_section"].astype(str))
    )
    reasons = [
        (
            "Road section absent from daily-counter files",
            ~no_link["road_section"].astype(str).isin(all_sections),
        ),
        (
            "Road section countered only in another year",
            no_link["road_section"].astype(str).isin(all_sections)
            & ~no_link["section_year"].isin(all_section_years),
        ),
        (
            "Historical counter location unavailable",
            no_link["section_year"].isin(all_section_years)
            & ~no_link["section_year"].isin(located_section_years),
        ),
    ]
    exclusions = pd.DataFrame(
        {
            "reason": [reason for reason, _ in reasons],
            "accidents": [int(mask.sum()) for _, mask in reasons],
        }
    )
    if int(exclusions["accidents"].sum()) != len(no_link):
        raise ValueError("No-link reasons do not partition excluded accidents")
    exclusions["share_of_all_pct"] = 100 * exclusions["accidents"] / len(accidents)
    args.exclusions.parent.mkdir(parents=True, exist_ok=True)
    exclusions.to_csv(args.exclusions, index=False)
    accident_points = accidents[["id", "lon", "lat"]].copy()
    accident_points["point_type"] = "Accident"
    accident_points["group"] = "No exact counter link"
    accident_points.loc[
        accident_points["id"].isin(exact_ids - retained_ids), "group"
    ] = "Exact link, not retained"
    accident_points.loc[
        accident_points["id"].isin(retained_ids), "group"
    ] = "Allocated-rate sample"
    counter_points = locations.dropna(subset=["lon", "lat"])[
        ["counter_id", "lon", "lat"]
    ].drop_duplicates(["counter_id", "lon", "lat"])
    counter_points = counter_points.rename(columns={"counter_id": "id"})
    counter_points["point_type"] = "Counter"
    counter_points["group"] = "Located daily counter"
    map_points = pd.concat(
        [accident_points, counter_points], ignore_index=True
    )[["point_type", "group", "id", "lon", "lat"]]
    args.map_points.parent.mkdir(parents=True, exist_ok=True)
    map_points.to_csv(args.map_points, index=False)
    print(result.to_string(index=False))
    print(exclusions.to_string(index=False))


if __name__ == "__main__":
    main()
