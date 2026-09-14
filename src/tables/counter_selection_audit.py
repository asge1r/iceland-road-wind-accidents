"""Reproduce the 2019--2024 monthly-VKT accident selection with ID hashes."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.accidents.match_weather import read_candidate_weather, select_best
from src.traffic.assign_counter_sections import ACCIDENTS, COUNTER_SECTIONS
from src.traffic.counter_accidents import accident_candidates
from src.traffic.counter_days import OUTPUT as COUNTER_DAYS
from src.traffic.daily_common import normalize_section
from src.traffic.station_selection import STATIONS, station_candidates, valid_wind


ASSIGNED = Path("data/processed/accidents/accidents-near-counter.csv")
WEATHER = Path("data/processed/weather/weather.parquet")
OUTPUT = Path("reports/main/tables/monthly_vkt_selection.csv")


def id_hash(values: pd.Series) -> str:
    ordered = sorted(str(value) for value in values.drop_duplicates())
    return hashlib.sha256(("\n".join(ordered) + "\n").encode()).hexdigest()


def build(
    accidents_path: Path = ACCIDENTS,
    sections_path: Path = COUNTER_SECTIONS,
    assigned_path: Path = ASSIGNED,
    counter_days_path: Path = COUNTER_DAYS,
    weather_path: Path = WEATHER,
    stations_path: Path = STATIONS,
) -> pd.DataFrame:
    all_accidents = pd.read_csv(accidents_path, low_memory=False)
    all_accidents["timestamp"] = pd.to_datetime(all_accidents["timestamp"], errors="raise")
    all_accidents["year"] = all_accidents["timestamp"].dt.year
    all_accidents["road_section"] = normalize_section(all_accidents["registered_road_section"])
    injury = all_accidents[all_accidents["meidsli"].isin([1, 2, 3])].copy()
    in_period = injury[injury["year"].between(2019, 2024)].copy()
    rural = in_period[in_period["urban_rural"].eq("Rural")].copy()

    sections = pd.read_csv(sections_path, low_memory=False)
    sections["road_section"] = normalize_section(sections["road_section"])
    road_keys = sections[["year", "road_section"]].drop_duplicates()
    with_section = rural.merge(road_keys, on=["year", "road_section"], how="inner", validate="many_to_one")
    assigned = pd.read_csv(assigned_path, low_memory=False)
    assigned["timestamp"] = pd.to_datetime(assigned["timestamp"], errors="raise")
    if not set(assigned["id"]).issubset(set(with_section["id"])):
        raise ValueError("Assigned accident IDs are not a subset of eligible road/year IDs")
    daytime = assigned[assigned["timestamp"].dt.hour.ge(7)].copy().reset_index(drop=True)

    candidates = accident_candidates(
        daytime, station_candidates(sections, pd.read_csv(stations_path))
    )
    weather = read_candidate_weather(pq.ParquetFile(weather_path), candidates)
    weather = weather[valid_wind(weather["f"], weather["fg"])]
    matched = select_best(candidates, weather)
    weather_ids = daytime.loc[matched["acc_index"].astype(int), "id"]
    usable_weather = daytime[daytime["id"].isin(weather_ids)].copy()

    counter_days = pd.read_csv(counter_days_path, usecols=[
        "date", "counter_section_id", "traffic_vehicles", "vehicle_km",
    ])
    counter_days["date"] = pd.to_datetime(counter_days["date"], errors="raise")
    daytime["date"] = daytime["timestamp"].dt.normalize()
    usable_weather["date"] = usable_weather["timestamp"].dt.normalize()
    day_keys = counter_days[counter_days["traffic_vehicles"].gt(0) & counter_days["vehicle_km"].gt(0)][
        ["date", "counter_section_id"]
    ].drop_duplicates()
    final = usable_weather.merge(day_keys, on=["date", "counter_section_id"], how="inner", validate="many_to_one")
    recorded = usable_weather.merge(
        counter_days[["date", "counter_section_id", "traffic_vehicles"]],
        on=["date", "counter_section_id"], how="left", validate="many_to_one",
    )
    lost = recorded[~recorded["id"].isin(final["id"])]
    if lost["traffic_vehicles"].notna().any():
        raise ValueError("An accident was removed for a recorded non-positive traffic count")

    stages = [
        ("All injury accidents, 2007-2025", injury, "Injury severity code 1, 2, or 3", "2007-2025; all locations"),
        ("0) Restrict to 2019-2024", in_period, "Accident year outside 2019-2024", "Timestamp calendar year"),
        ("a) Exclude urban accidents", rural, "Urban or unclassified location", "urban_rural = Rural"),
        ("b) Require counter-section road/year", with_section, "No counter-section for registered road in accident year", "Exact normalized road-section and year"),
        ("c) Require successful road-location assignment", assigned, "5 no road geometry; 15 farther than 100 m; 1 outside counter-sections", "Projected to registered road within 100 m and inside counter-section"),
        ("d) Exclude 00:00-07:00", daytime, "Accident time before 07:00", "07:00 <= event time < 24:00"),
        ("e) Require usable wind and gust", usable_weather, "No valid f and fg observation within limits", "Station measured from counter-section; <=20 km and <=5 minutes"),
        ("Require daily traffic count", final, "No corresponding positive counter-day record; none were recorded zero", "Exact counter-section and accident date"),
    ]
    rows = []
    previous = None
    for step, data, reason, rule in stages:
        remaining = data["id"].nunique()
        rows.append({
            "step": step,
            "starting_count": previous if previous is not None else remaining,
            "removed": 0 if previous is None else previous - remaining,
            "remaining": remaining,
            "exact_exclusion_reason": reason,
            "geographic_or_time_rule": rule,
            "id_set_sha256": id_hash(data["id"]),
        })
        previous = remaining
    expected = [17045, 5196, 1863, 869, 848, 781, 777, 694]
    actual = [row["remaining"] for row in rows]
    if actual != expected:
        raise ValueError(f"Selection differs from supervisor specification: {actual} != {expected}")
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result[["step", "removed", "remaining"]].to_string(index=False))
    print(f"wrote={args.output} rows={len(result)}")


if __name__ == "__main__":
    main()
