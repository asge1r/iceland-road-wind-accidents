"""Preparation helpers for the 2007–2025 road-period exposure table."""

from __future__ import annotations

import calendar
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pyproj import Transformer
from sklearn.neighbors import BallTree

from src.weather.frequency import (
    F_FIVE_MS_UPPER_BOUNDS,
    labels,
)


DEFAULT_ANNUAL_TRAFFIC = Path(
    "data/processed/traffic/annual.csv"
)
DEFAULT_INJURY_ACCIDENTS = Path("data/processed/accidents/rural_injury.csv")
DEFAULT_WEATHER = Path("data/processed/weather/weather.parquet")
DEFAULT_PERIOD_WIND_FREQUENCY = Path(
    "data/processed/weather/road_period_frequency.csv"
)
DEFAULT_STATIONS = Path("data/raw/weather/stations.csv")
DEFAULT_SECTION_MIDPOINTS = Path(
    "data/raw/traffic/reference/road_section_midpoints.csv"
)
DEFAULT_ROAD_GEOMETRIES = Path(
    "data/raw/traffic/reference/road_sections.parquet"
)
DEFAULT_LONG = Path("data/processed/traffic/road_period.csv")

YEARS = range(2007, 2026)
FIRST_YEAR = 2007
LAST_YEAR = 2025
EARTH_RADIUS_KM = 6371.0088
PRIMARY_STATION_RADIUS_KM = 20.0
TRAFFIC_PERIOD_ORDER = ["VDU", "SDU", "VHDU"]
TRAFFIC_PERIOD_MONTHS = {
    "VDU": "Dec-Mar",
    "SDU": "Jun, Jul, Aug, Sep",
    "VHDU": "Apr, May, Oct, Nov",
}
TRAFFIC_PERIOD_BY_MONTH = {
    1: "VDU",
    2: "VDU",
    3: "VDU",
    4: "VHDU",
    5: "VHDU",
    6: "SDU",
    7: "SDU",
    8: "SDU",
    9: "SDU",
    10: "VHDU",
    11: "VHDU",
    12: "VDU",
}
TRAFFIC_PERIOD_MONTH_NUMBERS = {
    "VDU": [1, 2, 3, 12],
    "SDU": [6, 7, 8, 9],
    "VHDU": [4, 5, 10, 11],
}
def normalize_section(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.lower()


def traffic_period_index(month: np.ndarray) -> np.ndarray:
    result = np.full(len(month), 2, dtype=np.int8)
    result[np.isin(month, [1, 2, 3, 12])] = 0
    result[np.isin(month, [6, 7, 8, 9])] = 1
    return result


def build_period_wind_frequency(
    weather_path: Path,
    output_path: Path,
    assigned_stations: np.ndarray,
    max_row_groups: int | None = None,
) -> pd.DataFrame:
    """Count 5 m/s mean-wind intervals by station, year, and traffic period."""
    parquet_file = pq.ParquetFile(weather_path)
    row_groups = parquet_file.metadata.num_row_groups
    if max_row_groups is not None:
        row_groups = min(row_groups, max_row_groups)

    assigned_stations = np.sort(assigned_stations.astype(np.int32))
    year_count = LAST_YEAR - FIRST_YEAR + 1
    period_count = len(TRAFFIC_PERIOD_ORDER)
    group_count = len(assigned_stations) * year_count * period_count
    totals = np.zeros(group_count, dtype=np.int64)
    counts = np.zeros(
        (group_count, len(F_FIVE_MS_UPPER_BOUNDS) + 1), dtype=np.int64
    )
    rows_scanned = 0
    rows_used = 0
    started = time.perf_counter()

    for row_group in range(row_groups):
        table = parquet_file.read_row_group(row_group, columns=["station", "time", "f"])
        station = table.column("station").to_numpy()
        timestamp = table.column("time").to_numpy().astype("datetime64[us]")
        year = timestamp.astype("datetime64[Y]").astype(np.int64) + 1970
        keep = (
            (year >= FIRST_YEAR)
            & (year <= LAST_YEAR)
            & np.isin(station, assigned_stations)
        )
        rows_scanned += len(table)
        if keep.any():
            station = station[keep]
            timestamp = timestamp[keep]
            year = year[keep]
            wind = table.column("f").to_numpy()[keep]
            month = timestamp.astype("datetime64[M]").astype(np.int64) % 12 + 1
            station_index = np.searchsorted(assigned_stations, station)
            group = (
                (station_index * year_count + (year - FIRST_YEAR)) * period_count
                + traffic_period_index(month)
            )
            totals += np.bincount(group, minlength=group_count)
            wind_bin = np.searchsorted(F_FIVE_MS_UPPER_BOUNDS, wind, side="right")
            counts += np.bincount(
                group * counts.shape[1] + wind_bin, minlength=counts.size
            ).reshape(counts.shape)
            rows_used += int(keep.sum())
        if (row_group + 1) % 25 == 0 or row_group + 1 == row_groups:
            print(
                f"traffic_period_wind row_groups={row_group + 1}/{row_groups} "
                f"rows_scanned={rows_scanned:,} rows_used={rows_used:,}",
                flush=True,
            )

    group, bin_index = np.nonzero(counts)
    station_index = group // (year_count * period_count)
    remainder = group % (year_count * period_count)
    lower_bounds = np.concatenate(([0.0], F_FIVE_MS_UPPER_BOUNDS))
    upper_bounds = np.concatenate((F_FIVE_MS_UPPER_BOUNDS, [np.inf]))
    result = pd.DataFrame(
        {
            "weather_station_id": assigned_stations[station_index],
            "year": FIRST_YEAR + remainder // period_count,
            "traffic_period": np.array(TRAFFIC_PERIOD_ORDER)[remainder % period_count],
            "variable": "f_5m",
            "bin_label": np.array(labels(F_FIVE_MS_UPPER_BOUNDS))[bin_index],
            "bin_lower_ms": lower_bounds[bin_index],
            "bin_upper_ms": upper_bounds[bin_index],
            "measurement_count": counts[group, bin_index],
            "total_measurements_in_period": totals[group],
        }
    )
    result["frequency_pct"] = (
        100 * result["measurement_count"] / result["total_measurements_in_period"]
    )
    result = result.sort_values(
        ["weather_station_id", "year", "traffic_period", "bin_lower_ms"]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(
        f"wrote={output_path} rows={len(result):,} "
        f"elapsed={time.perf_counter() - started:.1f}s",
        flush=True,
    )
    return result


def load_annual_traffic(path: Path) -> pd.DataFrame:
    annual = pd.read_csv(path, low_memory=False)
    annual["year"] = pd.to_numeric(annual["year"], errors="coerce").astype("Int64")
    annual = annual[annual["year"].isin(YEARS)].copy()
    annual["year"] = annual["year"].astype(int)
    annual["road_section"] = normalize_section(annual["road_section"])
    if annual.duplicated(["year", "road_section"]).any():
        raise ValueError("Annual traffic contains duplicate road-section/year keys")
    return annual


def build_all_annual_traffic_scope(annual: pd.DataFrame) -> pd.DataFrame:
    """Return every road section represented in the annual-traffic file."""
    return (
        annual[["road_section"]]
        .dropna()
        .drop_duplicates()
        .sort_values("road_section")
        .reset_index(drop=True)
    )

def build_station_candidates(
    section_scope: pd.DataFrame,
    midpoint_path: Path,
    station_path: Path,
    radius_km: float = PRIMARY_STATION_RADIUS_KM,
) -> pd.DataFrame:
    """Find all weather stations within the primary radius of each midpoint."""
    midpoints = pd.read_csv(
        midpoint_path,
        usecols=["road_section", "midpoint_lat", "midpoint_lon"],
    )
    midpoints["road_section"] = normalize_section(midpoints["road_section"])
    missing_sections = set(section_scope["road_section"]) - set(midpoints["road_section"])
    if missing_sections:
        roads = pd.read_parquet(
            DEFAULT_ROAD_GEOMETRIES, columns=["road_section", "paths_json"]
        )
        roads["road_section"] = normalize_section(roads["road_section"])
        roads = roads[roads["road_section"].isin(missing_sections)].copy()
        transformer = Transformer.from_crs(
            "EPSG:3057", "EPSG:4326", always_xy=True
        )

        def geometry_midpoint(paths_json: str) -> tuple[float, float]:
            paths = json.loads(paths_json)
            segments: list[tuple[np.ndarray, np.ndarray, float]] = []
            total = 0.0
            for path in paths:
                vertices = np.asarray([point[:2] for point in path], dtype=float)
                for start, end in zip(vertices[:-1], vertices[1:], strict=True):
                    length = float(np.linalg.norm(end - start))
                    if length > 0:
                        segments.append((start, end, length))
                        total += length
            target = total / 2
            traversed = 0.0
            for start, end, length in segments:
                if traversed + length >= target:
                    point = start + (target - traversed) / length * (end - start)
                    lon, lat = transformer.transform(float(point[0]), float(point[1]))
                    return lat, lon
                traversed += length
            return np.nan, np.nan

        derived = roads["paths_json"].map(geometry_midpoint)
        roads["midpoint_lat"] = derived.str[0]
        roads["midpoint_lon"] = derived.str[1]
        midpoints = pd.concat(
            [
                midpoints,
                roads[["road_section", "midpoint_lat", "midpoint_lon"]],
            ],
            ignore_index=True,
        ).drop_duplicates("road_section", keep="first")
    midpoints = section_scope.merge(
        midpoints, on="road_section", how="left", validate="one_to_one"
    ).dropna(subset=["midpoint_lat", "midpoint_lon"])

    stations = pd.read_csv(
        station_path, usecols=["station", "name", "lat", "lon"]
    ).drop_duplicates("station")
    stations = stations.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    tree = BallTree(
        np.radians(stations[["lat", "lon"]].to_numpy()), metric="haversine"
    )
    indices, distances = tree.query_radius(
        np.radians(midpoints[["midpoint_lat", "midpoint_lon"]].to_numpy()),
        r=radius_km / EARTH_RADIUS_KM,
        return_distance=True,
        sort_results=True,
    )

    rows: list[tuple[str, int, str, float]] = []
    for section, station_indices, distance_radians in zip(
        midpoints["road_section"], indices, distances, strict=True
    ):
        for station_index, distance_radian in zip(
            station_indices, distance_radians, strict=True
        ):
            station = stations.iloc[station_index]
            rows.append(
                (
                    section,
                    int(station["station"]),
                    str(station["name"]),
                    float(distance_radian * EARTH_RADIUS_KM),
                )
            )
    return pd.DataFrame(
        rows,
        columns=[
            "road_section",
            "weather_station_id",
            "weather_station_name",
            "weather_station_distance_km",
        ],
    )


def assign_nearest_valid_station(
    annual: pd.DataFrame,
    section_scope: pd.DataFrame,
    candidates: pd.DataFrame,
    wind: pd.DataFrame,
) -> pd.DataFrame:
    """Assign the closest station with clean data for each section/period."""
    panel = annual.merge(
        section_scope, on="road_section", how="inner", validate="many_to_one"
    )
    periods = pd.DataFrame(
        {
            "traffic_period": TRAFFIC_PERIOD_ORDER,
            "traffic_period_order": range(len(TRAFFIC_PERIOD_ORDER)),
        }
    )
    panel = panel.assign(_cross=1).merge(periods.assign(_cross=1), on="_cross")
    panel = panel.drop(columns="_cross")

    available = wind[["weather_station_id", "year", "traffic_period"]].drop_duplicates()
    eligible = candidates.merge(
        available,
        on="weather_station_id",
        how="inner",
        validate="many_to_many",
    )
    eligible = eligible.sort_values(
        [
            "road_section",
            "year",
            "traffic_period",
            "weather_station_distance_km",
            "weather_station_id",
        ]
    ).drop_duplicates(["road_section", "year", "traffic_period"], keep="first")
    assigned = panel.merge(
        eligible,
        on=["road_section", "year", "traffic_period"],
        how="left",
        validate="one_to_one",
    )
    has_spatial_candidate = assigned["road_section"].isin(
        candidates["road_section"].unique()
    )
    assigned["station_assignment_method"] = np.select(
        [
            assigned["weather_station_id"].notna(),
            has_spatial_candidate,
        ],
        [
            "nearest_station_to_section_midpoint_with_clean_period_data_within_20km",
            "nearby_stations_but_no_clean_period_data",
        ],
        default="no_station_within_20km_of_section_midpoint",
    )
    return assigned


def build_accident_counts(
    accidents_path: Path, annual: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    accidents = pd.read_csv(
        accidents_path,
        usecols=[
            "id",
            "timestamp",
            "meidsli",
            "registered_road_section",
            "within_20km",
            "wind_available",
            "f",
            "fg",
        ],
    )
    timestamp = pd.to_datetime(accidents["timestamp"], errors="coerce")
    accidents["year"] = timestamp.dt.year
    accidents["traffic_period"] = timestamp.dt.month.map(TRAFFIC_PERIOD_BY_MONTH)
    accidents["road_section"] = normalize_section(
        accidents["registered_road_section"]
    )
    accidents["severity_code"] = pd.to_numeric(accidents["meidsli"], errors="coerce")
    accidents = accidents[accidents["year"].isin(YEARS)].merge(
        annual[["year", "road_section"]],
        on=["year", "road_section"],
        how="inner",
        validate="many_to_one",
    )
    diagnostics = {
        "rural_injury_accidents_2007_2025": int(
            pd.read_csv(accidents_path, usecols=["timestamp"])["timestamp"]
            .pipe(pd.to_datetime, errors="coerce")
            .dt.year.isin(YEARS)
            .sum()
        ),
        "exact_annual_road_section_matches": len(accidents),
        "exact_matches_serious_or_fatal": int(accidents["severity_code"].le(2).sum()),
    }
    counts = (
        accidents.groupby(
            ["year", "road_section", "traffic_period"], as_index=False
        )
        .agg(
            injury_accidents=("id", "size"),
            serious_or_fatal_accidents=(
                "severity_code",
                lambda values: int(values.le(2).sum()),
            ),
            fatal_accidents=("severity_code", lambda values: int(values.eq(1).sum())),
        )
    )

    clean_wind = accidents[
        accidents["within_20km"].fillna(False)
        & accidents["wind_available"].fillna(False)
        & accidents["f"].between(0, 45, inclusive="left")
        & accidents["fg"].between(0, 65, inclusive="left")
        & accidents["fg"].add(0.5).ge(accidents["f"])
    ].copy()
    diagnostics["exact_matches_with_clean_wind_within_20km"] = len(clean_wind)
    diagnostics["exact_matches_excluded_from_wind_bins"] = len(accidents) - len(clean_wind)
    diagnostics["clean_wind_bin_coverage_pct_x100"] = int(
        round(10_000 * len(clean_wind) / len(accidents))
    )
    diagnostics["clean_wind_serious_or_fatal"] = int(
        clean_wind["severity_code"].le(2).sum()
    )

    clean_wind["variable"] = "f_5m"
    clean_wind["bin_label"] = pd.cut(
        clean_wind["f"],
        bins=np.concatenate(([0.0], F_FIVE_MS_UPPER_BOUNDS, [np.inf])),
        labels=labels(F_FIVE_MS_UPPER_BOUNDS),
        right=False,
        include_lowest=True,
    ).astype("string")
    bin_counts = (
        clean_wind.groupby(
            ["year", "road_section", "traffic_period", "variable", "bin_label"],
            as_index=False,
            observed=True,
        )
        .agg(
            bin_injury_accidents=("id", "size"),
            bin_serious_or_fatal_accidents=(
                "severity_code", lambda series: int(series.le(2).sum())
            ),
            bin_fatal_accidents=(
                "severity_code", lambda series: int(series.eq(1).sum())
            ),
        )
    )
    return counts, bin_counts, diagnostics


def traffic_period_days(year: int, period: str) -> int:
    return sum(
        calendar.monthrange(int(year), month)[1]
        for month in TRAFFIC_PERIOD_MONTH_NUMBERS[period]
    )


def build_base_table(
    assigned_panel: pd.DataFrame,
    counts: pd.DataFrame,
) -> pd.DataFrame:
    base = assigned_panel.merge(
        counts,
        on=["year", "road_section", "traffic_period"],
        how="left",
        validate="one_to_one",
    )
    for column in [
        "injury_accidents",
        "serious_or_fatal_accidents",
        "fatal_accidents",
    ]:
        base[column] = base[column].fillna(0).astype(int)
    base["traffic_period_months"] = base["traffic_period"].map(
        TRAFFIC_PERIOD_MONTHS
    )
    base["period"] = base["traffic_period"] + " " + base["year"].astype(str)
    year_days = base["year"].map(lambda year: 366 if calendar.isleap(year) else 365)
    sdu_days = base["year"].map(lambda year: traffic_period_days(year, "SDU"))
    vdu_days = base["year"].map(lambda year: traffic_period_days(year, "VDU"))
    other_days = year_days - sdu_days - vdu_days
    base["other_daily_traffic_derived"] = (
        base["adu"] * year_days - base["sdu"] * sdu_days - base["vdu"] * vdu_days
    ) / other_days
    invalid_other = base["other_daily_traffic_derived"].le(0)
    base.loc[invalid_other, "other_daily_traffic_derived"] = np.nan
    base["traffic_reference_name"] = base["traffic_period"].map(
        {"VDU": "VDU", "SDU": "SDU", "VHDU": "Derived VHDU"}
    )
    base["traffic_reference_daily_volume"] = np.select(
        [
            base["traffic_period"].eq("VDU"),
            base["traffic_period"].eq("SDU"),
        ],
        [base["vdu"], base["sdu"]],
        default=base["other_daily_traffic_derived"],
    )
    base["traffic_reference_method"] = np.where(
        base["traffic_period"].eq("VHDU"),
        "derived residual from ADU, SDU, VDU and calendar-day weights",
        "official seasonal average for the defined traffic period",
    )
    return base.sort_values(
        ["road_section", "year", "traffic_period_order"]
    )


def build_long_table(
    base: pd.DataFrame, wind: pd.DataFrame, bin_counts: pd.DataFrame
) -> pd.DataFrame:
    wind = wind[
        wind["year"].isin(YEARS) & wind["variable"].eq("f_5m")
    ].copy()
    wind_columns = [
        "weather_station_id",
        "year",
        "traffic_period",
        "variable",
        "bin_label",
        "bin_lower_ms",
        "bin_upper_ms",
        "measurement_count",
        "total_measurements_in_period",
        "frequency_pct",
    ]
    wind_key = [
        "weather_station_id",
        "year",
        "traffic_period",
        "variable",
        "bin_label",
    ]
    if wind.duplicated(wind_key).any():
        raise ValueError("Wind frequency contains duplicate station-period-bin keys")

    bin_template = (
        wind[["variable", "bin_label", "bin_lower_ms", "bin_upper_ms"]]
        .drop_duplicates()
        .sort_values(["variable", "bin_lower_ms"])
    )
    expanded = base.assign(_cross=1).merge(
        bin_template.assign(_cross=1), on="_cross", how="inner"
    ).drop(columns="_cross")
    long = expanded.merge(
        wind[wind_columns].drop(
            columns=["bin_lower_ms", "bin_upper_ms"]
        ),
        on=wind_key,
        how="left",
        validate="many_to_one",
    )
    period_totals = (
        wind.groupby(
            ["weather_station_id", "year", "traffic_period", "variable"],
            as_index=False,
        )["total_measurements_in_period"]
        .max()
        .rename(
            columns={"total_measurements_in_period": "available_period_measurements"}
        )
    )
    long = long.merge(
        period_totals,
        on=["weather_station_id", "year", "traffic_period", "variable"],
        how="left",
        validate="many_to_one",
    )
    long["wind_frequency_available"] = long["available_period_measurements"].notna()
    missing_zero = long["wind_frequency_available"] & long["frequency_pct"].isna()
    long.loc[missing_zero, "measurement_count"] = 0
    long.loc[missing_zero, "frequency_pct"] = 0.0
    long.loc[long["wind_frequency_available"], "total_measurements_in_period"] = (
        long.loc[long["wind_frequency_available"], "available_period_measurements"]
    )
    long = long.drop(columns="available_period_measurements")
    long = long.merge(
        bin_counts,
        on=[
            "year",
            "road_section",
            "traffic_period",
            "variable",
            "bin_label",
        ],
        how="left",
        validate="one_to_one",
    )
    for column in [
        "bin_injury_accidents",
        "bin_serious_or_fatal_accidents",
        "bin_fatal_accidents",
    ]:
        long[column] = long[column].fillna(0).astype(int)
    return long.sort_values(
        [
            "road_section",
            "year",
            "traffic_period_order",
            "variable",
            "bin_lower_ms",
        ],
        na_position="last",
    )
