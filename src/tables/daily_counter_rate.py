"""Estimate a daily counter-based accident-rate sensitivity, 2019--2024.

Accidents are assigned only to a counter on the same registered road section
and year, within a specified straight-line distance. Full-day accident counts
are compared with observed 24-hour traffic and full-day mean wind. The result
covers selected counters and is not a national accident rate.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.discrete.conditional_models import ConditionalPoisson


ACCIDENTS = Path("data/analysis/accidents.csv")
DAILY = Path("data/analysis/daily_traffic.csv")
LOCATIONS = Path("data/analysis/daily_counter_locations.csv")
STANDARD_OUTPUT = Path("reports/main/tables/daily_counter_rate_ratio_by_wind.csv")
COARSE_OUTPUT = Path("reports/main/tables/daily_counter_rate_ratio_coarse_by_wind.csv")
STANDARD_AUDIT = Path("reports/working/tables/daily_counter_rate_audit.csv")
COARSE_AUDIT = Path("reports/working/tables/daily_counter_rate_coarse_audit.csv")
YEARS = range(2019, 2025)
STANDARD_EDGES = [0, 5, 10, 15, 20, 25, np.inf]
STANDARD_LABELS = ["0-5", "5-10", "10-15", "15-20", "20-25", ">=25"]
COARSE_EDGES = [0, 10, 15, np.inf]
COARSE_LABELS = ["0-10", "10-15", ">=15"]
EARTH_RADIUS_KM = 6371.0088


def require_columns(data: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(data)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def haversine_km(lon: float, lat: float, candidates: pd.DataFrame) -> np.ndarray:
    lon1, lat1 = np.radians([lon, lat])
    lon2 = np.radians(candidates["lon"].to_numpy(float))
    lat2 = np.radians(candidates["lat"].to_numpy(float))
    value = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(value))


def read_inputs(
    accidents_path: Path, daily_path: Path, locations_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path in [accidents_path, daily_path, locations_path]:
        if path.suffix.lower() != ".csv":
            raise ValueError(f"Analysis input must be CSV: {path}")
    accidents = pd.read_csv(accidents_path)
    daily = pd.read_csv(daily_path)
    locations = pd.read_csv(locations_path)
    require_columns(
        accidents, {"id", "timestamp", "year", "road_section", "lon", "lat"},
        "Accident input",
    )
    require_columns(
        daily, {"date", "counter_id", "traffic", "f_full_day_mean"},
        "Daily traffic input",
    )
    require_columns(
        locations, {"year", "counter_id", "road_section", "lon", "lat"},
        "Counter-location input",
    )
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"], errors="raise")
    accidents["date"] = accidents["timestamp"].dt.normalize()
    accidents = accidents[accidents["year"].isin(YEARS)].copy()
    accidents["road_section"] = accidents["road_section"].astype("string").str.strip().str.lower()
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    daily["year"] = daily["date"].dt.year
    daily = daily[daily["year"].isin(YEARS)].copy()
    locations = locations[
        locations["year"].isin(YEARS)
        & locations["lon"].notna()
        & locations["lat"].notna()
    ].copy()
    locations["road_section"] = locations["road_section"].astype("string").str.strip().str.lower()
    if locations.duplicated(["year", "counter_id"]).any():
        raise ValueError("Counter locations are not unique by year and counter")
    return accidents, daily, locations


def match_accidents(
    accidents: pd.DataFrame, locations: pd.DataFrame, max_distance_km: float,
) -> tuple[pd.DataFrame, int]:
    groups = {
        key: group.reset_index(drop=True)
        for key, group in locations.groupby(["year", "road_section"], observed=True)
    }
    rows: list[dict[str, object]] = []
    exact_candidates = 0
    for accident in accidents.itertuples(index=False):
        candidates = groups.get((accident.year, accident.road_section))
        if candidates is None or candidates.empty:
            continue
        exact_candidates += 1
        distances = haversine_km(accident.lon, accident.lat, candidates)
        position = int(np.argmin(distances))
        distance = float(distances[position])
        if distance > max_distance_km:
            continue
        counter = candidates.iloc[position]
        rows.append(
            {
                "id": accident.id,
                "date": accident.date,
                "year": accident.year,
                "road_section": accident.road_section,
                "counter_id": counter["counter_id"],
                "counter_distance_km": distance,
            }
        )
    result = pd.DataFrame(rows)
    if not result.empty and result["id"].duplicated().any():
        raise ValueError("An accident was assigned to more than one counter")
    return result, exact_candidates


def build_panel(
    daily: pd.DataFrame, matches: pd.DataFrame,
    edges: list[float], labels: list[str],
) -> tuple[pd.DataFrame, int]:
    daily = daily[
        daily["traffic"].gt(0)
        & daily["f_full_day_mean"].between(0, 45, inclusive="left")
    ].copy()
    if daily.duplicated(["counter_id", "date"]).any():
        raise ValueError("Daily traffic is not unique by counter and date")
    matched_valid = matches.merge(
        daily[["counter_id", "date"]], on=["counter_id", "date"], how="inner"
    )
    counts = matched_valid.groupby(["counter_id", "date"], as_index=False).agg(
        observed_accidents=("id", "nunique")
    )
    daily = daily.merge(
        counts, on=["counter_id", "date"], how="left", validate="one_to_one"
    )
    daily["observed_accidents"] = daily["observed_accidents"].fillna(0).astype(int)
    daily["wind_bin"] = pd.cut(
        daily["f_full_day_mean"], bins=edges, labels=labels,
        right=False, include_lowest=True,
    ).astype("string")
    return daily.dropna(subset=["wind_bin"]), int(matched_valid["id"].nunique())


def aggregate_model_data(panel: pd.DataFrame) -> pd.DataFrame:
    data = panel.groupby(
        ["counter_id", "year", "wind_bin"], as_index=False, observed=True
    ).agg(
        observed_accidents=("observed_accidents", "sum"),
        observed_vehicles=("traffic", "sum"),
        counter_days=("date", "size"),
    )
    data["stratum"] = data["counter_id"].astype(str) + "|" + data["year"].astype(str)
    total_accidents = data.groupby("stratum")["observed_accidents"].transform("sum")
    return data[total_accidents.gt(0) & data["observed_vehicles"].gt(0)].copy()


def fit_model(data: pd.DataFrame, labels: list[str]) -> pd.DataFrame:
    exog = pd.get_dummies(data["wind_bin"], dtype=float).reindex(columns=labels, fill_value=0.0)
    model = ConditionalPoisson(
        data["observed_accidents"].to_numpy(),
        exog.drop(columns=labels[0]).to_numpy(),
        groups=data["stratum"].to_numpy(),
        offset=np.log(data["observed_vehicles"].to_numpy(float)),
    )
    fitted = model.fit(disp=False, maxiter=300)
    confidence = fitted.conf_int()
    result = data.groupby("wind_bin", as_index=False, observed=True).agg(
        observed_accidents=("observed_accidents", "sum"),
        observed_vehicles=("observed_vehicles", "sum"),
        counter_days=("counter_days", "sum"),
        counters=("counter_id", "nunique"),
    ).set_index("wind_bin").reindex(labels).reset_index()
    result["accidents_per_100k_counted_vehicles"] = (
        result["observed_accidents"] / result["observed_vehicles"] * 100_000
    )
    result["rate_ratio"] = 1.0
    result["ci_95_low"] = np.nan
    result["ci_95_high"] = np.nan
    result["p_value"] = np.nan
    for index, label in enumerate(labels[1:]):
        mask = result["wind_bin"].eq(label)
        result.loc[mask, "rate_ratio"] = np.exp(fitted.params[index])
        result.loc[mask, "ci_95_low"] = np.exp(confidence[index, 0])
        result.loc[mask, "ci_95_high"] = np.exp(confidence[index, 1])
        result.loc[mask, "p_value"] = fitted.pvalues[index]
    result["model_accidents"] = int(data["observed_accidents"].sum())
    result["model_strata"] = int(model._n_groups)
    result["model_rows"] = int(model.nobs)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-d", "--daily-traffic", type=Path, default=DAILY)
    parser.add_argument("-l", "--locations", type=Path, default=LOCATIONS)
    parser.add_argument("-r", "--max-distance-km", type=float, default=20.0)
    parser.add_argument("-c", "--coarse", action="store_true", help="Use 0--10, 10--15 and >=15 m/s bins.")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("-u", "--audit", type=Path)
    args = parser.parse_args()
    if args.max_distance_km <= 0:
        raise ValueError("Maximum counter distance must be positive")
    edges, labels = (
        (COARSE_EDGES, COARSE_LABELS) if args.coarse
        else (STANDARD_EDGES, STANDARD_LABELS)
    )
    output = args.output or (COARSE_OUTPUT if args.coarse else STANDARD_OUTPUT)
    audit_path = args.audit or (COARSE_AUDIT if args.coarse else STANDARD_AUDIT)
    accidents, daily, locations = read_inputs(args.accidents, args.daily_traffic, args.locations)
    matches, exact_candidates = match_accidents(accidents, locations, args.max_distance_km)
    panel, matched_valid = build_panel(daily, matches, edges, labels)
    model_data = aggregate_model_data(panel)
    result = fit_model(model_data, labels)
    audit = pd.DataFrame(
        [
            ("rural_injury_accidents_2019_2024", len(accidents)),
            ("exact_road_section_counter_candidates", exact_candidates),
            ("within_distance", matches["id"].nunique()),
            ("with_valid_counter_day", matched_valid),
            ("valid_counter_days", len(panel)),
            ("valid_counters", panel["counter_id"].nunique()),
            ("model_accidents", int(model_data["observed_accidents"].sum())),
            ("candidate_model_strata", model_data["stratum"].nunique()),
            ("fitted_model_strata", int(result["model_strata"].iloc[0])),
        ],
        columns=["metric", "value"],
    )
    audit["max_counter_distance_km"] = args.max_distance_km
    audit["wind_binning"] = "coarse" if args.coarse else "standard"
    for path in [output, audit_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    audit.to_csv(audit_path, index=False)
    print(audit.to_string(index=False))
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
