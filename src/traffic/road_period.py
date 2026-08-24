"""Build the descriptive 2007-2025 road-section, traffic, and wind table.

The readable tables report wind frequency and actual accident counts by wind
interval. The annual-traffic comparison uses official SDU and VDU values
and a day-weighted residual derived from ADU for the remaining four months.
"""

from __future__ import annotations

import argparse
import calendar
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pyproj import Transformer
from scipy.stats import chi2
from sklearn.neighbors import BallTree

from src.weather.frequency import (
    FG_UPPER_BOUNDS,
    F_FIVE_MS_UPPER_BOUNDS,
    F_UPPER_BOUNDS,
    labels,
)


DEFAULT_ANNUAL_TRAFFIC = Path(
    "data/processed/traffic/annual.csv"
)
DEFAULT_ALL_ACCIDENTS = Path("data/processed/accidents/all.parquet")
DEFAULT_INJURY_ACCIDENTS = Path("data/processed/accidents/rural_injury.parquet")
DEFAULT_WEATHER = Path("data/processed/weather/weather.parquet")
DEFAULT_PERIOD_WIND_FREQUENCY = Path(
    "data/processed/weather/road_period_frequency.parquet"
)
DEFAULT_SURFACE = Path("data/raw/traffic/reference/road_surface_history.csv")
DEFAULT_STATIONS = Path("data/raw/weather/stations.csv")
DEFAULT_SECTION_MIDPOINTS = Path(
    "data/raw/traffic/reference/road_section_midpoints.csv"
)
DEFAULT_ROAD_GEOMETRIES = Path(
    "data/raw/traffic/reference/road_sections.parquet"
)
DEFAULT_LONG = Path("data/processed/traffic/road_period.parquet")
DEFAULT_WIDE = Path("reports/working/tables/road_wind_full.csv")
DEFAULT_ACCIDENT_ROWS = Path(
    "archive/generated_diagnostics/road_wind_accident_rows.csv"
)
DEFAULT_MEAN_WIND_TABLE = Path("reports/working/tables/road_wind_mean_full.csv")
DEFAULT_GUST_TABLE = Path("reports/working/tables/road_wind_gust_full.csv")
DEFAULT_COVERAGE = Path("reports/working/tables/road_coverage.csv")
DEFAULT_NOTES = Path("archive/generated_diagnostics/road_notes.txt")
DEFAULT_FIGURE = Path(
    "archive/generated_diagnostics/road_summary.png"
)
DEFAULT_TRAFFIC_ADJUSTED_RATES = Path(
    "archive/generated_diagnostics/traffic_rates.csv"
)
DEFAULT_TRAFFIC_ADJUSTED_FIGURE = Path(
    "archive/generated_diagnostics/traffic_rates.png"
)
DEFAULT_ADJUSTMENT_COMPARISON_FIGURE = Path(
    "archive/generated_diagnostics/road_period_comparison.png"
)
DEFAULT_SDU_VDU_RATES = Path(
    "archive/generated_diagnostics/traffic_rates_sdu_vdu.csv"
)
DEFAULT_SDU_VDU_FIGURE = Path(
    "archive/generated_diagnostics/traffic_rates_sdu_vdu.png"
)
DEFAULT_SCOPE_COMPARISON = Path(
    "archive/generated_diagnostics/traffic_scope.csv"
)
DEFAULT_SCOPE_COMPARISON_FIGURE = Path(
    "archive/generated_diagnostics/traffic_scope.png"
)

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
SURFACE_LABELS = {
    0: "Unknown",
    1: "Concrete",
    2: "Paved",
    3: "Gravel-surfaced",
    4: "Oil-treated",
    5: "Firm",
    6: "Loose",
    7: "Smooth",
    8: "Uneven",
    9: "Other",
    10: "Newly paved",
}


def normalize_section(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.lower()


def mode_smallest(values: pd.Series) -> int:
    """Return the smallest mode so ties are deterministic."""
    modes = pd.to_numeric(values, errors="coerce").dropna().mode()
    if modes.empty:
        raise ValueError("Cannot calculate a mode from an empty series")
    return int(modes.min())


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
    """Aggregate clean weather using the official SDU and VDU month groups."""
    parquet_file = pq.ParquetFile(weather_path)
    row_groups = parquet_file.metadata.num_row_groups
    if max_row_groups is not None:
        row_groups = min(row_groups, max_row_groups)

    assigned_stations = np.sort(assigned_stations.astype(np.int32))
    year_count = LAST_YEAR - FIRST_YEAR + 1
    period_count = len(TRAFFIC_PERIOD_ORDER)
    group_count = len(assigned_stations) * year_count * period_count
    totals = np.zeros(group_count, dtype=np.int64)
    f_counts = np.zeros(
        (group_count, len(F_UPPER_BOUNDS) + 1), dtype=np.int64
    )
    f_five_ms_counts = np.zeros(
        (group_count, len(F_FIVE_MS_UPPER_BOUNDS) + 1), dtype=np.int64
    )
    fg_counts = np.zeros(
        (group_count, len(FG_UPPER_BOUNDS) + 1), dtype=np.int64
    )
    rows_scanned = 0
    rows_used = 0
    started = time.perf_counter()

    for row_group in range(row_groups):
        table = parquet_file.read_row_group(
            row_group, columns=["station", "time", "f", "fg"]
        )
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
            f = table.column("f").to_numpy()[keep]
            fg = table.column("fg").to_numpy()[keep]
            month = timestamp.astype("datetime64[M]").astype(np.int64) % 12 + 1
            station_index = np.searchsorted(assigned_stations, station)
            group = (
                (station_index * year_count + (year - FIRST_YEAR)) * period_count
                + traffic_period_index(month)
            )
            totals += np.bincount(group, minlength=group_count)
            f_bin = np.searchsorted(F_UPPER_BOUNDS, f, side="right")
            f_five_ms_bin = np.searchsorted(F_FIVE_MS_UPPER_BOUNDS, f, side="right")
            fg_bin = np.searchsorted(FG_UPPER_BOUNDS, fg, side="right")
            f_counts += np.bincount(
                group * f_counts.shape[1] + f_bin, minlength=f_counts.size
            ).reshape(f_counts.shape)
            f_five_ms_counts += np.bincount(
                group * f_five_ms_counts.shape[1] + f_five_ms_bin,
                minlength=f_five_ms_counts.size,
            ).reshape(f_five_ms_counts.shape)
            fg_counts += np.bincount(
                group * fg_counts.shape[1] + fg_bin, minlength=fg_counts.size
            ).reshape(fg_counts.shape)
            rows_used += int(keep.sum())
        if (row_group + 1) % 25 == 0 or row_group + 1 == row_groups:
            print(
                f"traffic_period_wind row_groups={row_group + 1}/{row_groups} "
                f"rows_scanned={rows_scanned:,} rows_used={rows_used:,}",
                flush=True,
            )

    frames: list[pd.DataFrame] = []
    period_names = np.array(TRAFFIC_PERIOD_ORDER)
    for variable, counts, upper_bounds in (
        ("f", f_counts, F_UPPER_BOUNDS),
        ("f_5m", f_five_ms_counts, F_FIVE_MS_UPPER_BOUNDS),
        ("fg", fg_counts, FG_UPPER_BOUNDS),
    ):
        group, bin_index = np.nonzero(counts)
        station_index = group // (year_count * period_count)
        remainder = group % (year_count * period_count)
        year = FIRST_YEAR + remainder // period_count
        traffic_period = period_names[remainder % period_count]
        lower_bounds = np.concatenate(([0.0], upper_bounds))
        upper_with_infinity = np.concatenate((upper_bounds, [np.inf]))
        frame = pd.DataFrame(
            {
                "weather_station_id": assigned_stations[station_index],
                "year": year,
                "traffic_period": traffic_period,
                "variable": variable,
                "bin_label": np.array(labels(upper_bounds))[bin_index],
                "bin_lower_ms": lower_bounds[bin_index],
                "bin_upper_ms": upper_with_infinity[bin_index],
                "measurement_count": counts[group, bin_index],
                "total_measurements_in_period": totals[group],
            }
        )
        frame["frequency_pct"] = (
            100 * frame["measurement_count"] / frame["total_measurements_in_period"]
        )
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True).sort_values(
        [
            "weather_station_id",
            "year",
            "traffic_period",
            "variable",
            "bin_lower_ms",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False, compression="zstd")
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


def build_section_scope(accidents_path: Path, annual: pd.DataFrame) -> pd.DataFrame:
    """Return road sections with at least one exact-matched rural accident."""
    columns = ["date", "urban_rural", "registered_road_section"]
    accidents = pd.read_parquet(accidents_path, columns=columns)
    accidents["year"] = pd.to_datetime(accidents["date"], errors="coerce").dt.year
    accidents["road_section"] = normalize_section(
        accidents["registered_road_section"]
    )
    keys = annual[["year", "road_section"]]
    eligible = accidents[
        accidents["year"].isin(YEARS)
        & accidents["urban_rural"].eq("Rural")
    ].merge(keys, on=["year", "road_section"], how="inner", validate="many_to_one")
    return eligible[["road_section"]].drop_duplicates().sort_values("road_section")


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
    accidents = pd.read_parquet(
        accidents_path,
        columns=[
            "nid",
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
            pd.read_parquet(accidents_path, columns=["timestamp"])["timestamp"]
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
            injury_accidents=("nid", "size"),
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

    bin_frames: list[pd.DataFrame] = []
    for variable, source_column, upper_bounds in (
        ("f", "f", F_UPPER_BOUNDS),
        ("f_5m", "f", F_FIVE_MS_UPPER_BOUNDS),
        ("fg", "fg", FG_UPPER_BOUNDS),
    ):
        bin_labels = labels(upper_bounds)
        edges = np.concatenate(([0.0], upper_bounds, [np.inf]))
        values = clean_wind.copy()
        values["variable"] = variable
        values["bin_label"] = pd.cut(
            values[source_column],
            bins=edges,
            labels=bin_labels,
            right=False,
            include_lowest=True,
        ).astype("string")
        grouped = (
            values.groupby(
                ["year", "road_section", "traffic_period", "variable", "bin_label"],
                as_index=False,
                observed=True,
            )
            .agg(
                bin_injury_accidents=("nid", "size"),
                bin_serious_or_fatal_accidents=(
                    "severity_code", lambda series: int(series.le(2).sum())
                ),
                bin_fatal_accidents=(
                    "severity_code", lambda series: int(series.eq(1).sum())
                ),
            )
        )
        bin_frames.append(grouped)
    bin_counts = pd.concat(bin_frames, ignore_index=True)
    return counts, bin_counts, diagnostics


def build_surface_table(path: Path) -> pd.DataFrame:
    surface = pd.read_csv(
        path,
        usecols=["surface_record_datetime", "sveitavegur", "surface_code_1"],
        low_memory=False,
    )
    surface["year"] = pd.to_datetime(
        surface["surface_record_datetime"], errors="coerce"
    ).dt.year
    surface["road_section"] = normalize_section(surface["sveitavegur"])
    surface["surface_code"] = pd.to_numeric(
        surface["surface_code_1"], errors="coerce"
    )
    surface = surface[surface["year"].isin(YEARS)].copy()
    observations = (
        surface.groupby(["year", "road_section"], as_index=False)
        .agg(surface_observations=("surface_code", "count"))
    )
    known = surface[surface["surface_code"].gt(0)].copy()
    known_modes = (
        known.groupby(["year", "road_section"], as_index=False)
        .agg(
            surface_code=("surface_code", mode_smallest),
            known_surface_observations=("surface_code", "size"),
        )
    )
    output = observations.merge(
        known_modes, on=["year", "road_section"], how="left", validate="one_to_one"
    )
    output["surface_label"] = output["surface_code"].map(SURFACE_LABELS)
    output.loc[
        output["surface_code"].notna() & output["surface_label"].isna(),
        "surface_label",
    ] = "Unmapped source code"
    return output


def build_base_table(
    assigned_panel: pd.DataFrame,
    counts: pd.DataFrame,
    surface: pd.DataFrame,
) -> pd.DataFrame:
    base = assigned_panel.merge(
        counts,
        on=["year", "road_section", "traffic_period"],
        how="left",
        validate="one_to_one",
    ).merge(
        surface,
        on=["year", "road_section"],
        how="left",
        validate="many_to_one",
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
    base["surface_assignment_method"] = (
        "modal_nonzero_surface_code_1_from_accident_reports_in_section_year"
    )
    return base.sort_values(
        ["road_section", "year", "traffic_period_order"]
    )


def build_long_table(
    base: pd.DataFrame, wind: pd.DataFrame, bin_counts: pd.DataFrame
) -> pd.DataFrame:
    wind = wind[
        wind["year"].isin(YEARS) & wind["variable"].isin(["f", "f_5m", "fg"])
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


def build_wide_table(base: pd.DataFrame, long: pd.DataFrame) -> pd.DataFrame:
    frequencies = long.dropna(subset=["variable", "bin_label"]).copy()
    frequencies["frequency_column"] = (
        frequencies["variable"]
        + "_frequency_pct_"
        + frequencies["bin_label"]
        .astype(str)
        .str.replace(">=", "ge_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    index = ["road_section", "year", "traffic_period"]
    pivot = frequencies.pivot(
        index=index, columns="frequency_column", values="frequency_pct"
    ).reset_index()
    metadata_columns = [
        "road_section",
        "road_number",
        "section_code",
        "road_name",
        "section_start_name",
        "section_end_name",
        "year",
        "traffic_period",
        "traffic_period_months",
        "period",
        "traffic_reference_name",
        "traffic_reference_daily_volume",
        "traffic_reference_method",
        "other_daily_traffic_derived",
        "weather_station_id",
        "weather_station_name",
        "weather_station_distance_km",
        "section_length_km",
        "adu",
        "sdu",
        "vdu",
        "thousand_vehicle_km",
        "surface_code",
        "surface_label",
        "surface_observations",
        "known_surface_observations",
        "injury_accidents",
        "serious_or_fatal_accidents",
        "fatal_accidents",
        "station_assignment_method",
        "surface_assignment_method",
    ]
    wide = base[metadata_columns].merge(
        pivot, on=index, how="left", validate="one_to_one"
    )
    ordered_bins = (
        long[["variable", "bin_label", "bin_lower_ms"]]
        .drop_duplicates()
        .sort_values(["variable", "bin_lower_ms"])
    )
    frequency_columns = [
        f"{row.variable}_frequency_pct_"
        f"{str(row.bin_label).replace('>=', 'ge_').replace('-', '_')}"
        for row in ordered_bins.itertuples(index=False)
    ]
    other_columns = [column for column in wide if column not in frequency_columns]
    return wide[other_columns + frequency_columns]


def build_readable_bin_table(long: pd.DataFrame, variable: str) -> pd.DataFrame:
    """Create one readable road-section row per wind interval."""
    columns = [
        "road_section",
        "road_number",
        "road_name",
        "year",
        "traffic_period",
        "traffic_period_months",
        "section_length_km",
        "adu",
        "sdu",
        "vdu",
        "traffic_reference_name",
        "traffic_reference_daily_volume",
        "traffic_reference_method",
        "other_daily_traffic_derived",
        "weather_station_id",
        "weather_station_name",
        "weather_station_distance_km",
        "station_assignment_method",
        "surface_label",
        "bin_label",
        "bin_lower_ms",
        "bin_upper_ms",
        "measurement_count",
        "total_measurements_in_period",
        "frequency_pct",
        "bin_injury_accidents",
        "bin_serious_or_fatal_accidents",
        "bin_fatal_accidents",
    ]
    table = long[long["variable"].eq(variable)][columns].copy()
    table = table.rename(columns={"bin_label": "wind_interval_ms"})
    return table.sort_values(
        ["road_section", "year", "traffic_period", "bin_lower_ms"]
    )


def validate_and_summarize(
    base: pd.DataFrame,
    long: pd.DataFrame,
    accident_diagnostics: dict[str, int],
) -> pd.DataFrame:
    if base.duplicated(["road_section", "year", "traffic_period"]).any():
        raise ValueError(
            "Base table contains duplicate road-section/year/traffic-period keys"
        )
    matched_accidents = accident_diagnostics["exact_annual_road_section_matches"]
    matched_serious = accident_diagnostics["exact_matches_serious_or_fatal"]
    if int(base["injury_accidents"].sum()) != matched_accidents:
        raise ValueError("Period injury-accident counts do not match exact matches")
    if int(base["serious_or_fatal_accidents"].sum()) != matched_serious:
        raise ValueError("Period serious/fatal counts do not match exact matches")
    expected_bin_accidents = accident_diagnostics[
        "exact_matches_with_clean_wind_within_20km"
    ]
    expected_bin_serious = accident_diagnostics["clean_wind_serious_or_fatal"]
    for variable in ("f", "fg"):
        subset = long[long["variable"].eq(variable)]
        if int(subset["bin_injury_accidents"].sum()) != expected_bin_accidents:
            raise ValueError(f"{variable} bin injury counts do not reconcile")
        if int(subset["bin_serious_or_fatal_accidents"].sum()) != expected_bin_serious:
            raise ValueError(f"{variable} bin serious/fatal counts do not reconcile")
    f_with_frequency = long[
        long["variable"].eq("f") & long["wind_frequency_available"]
    ]

    period_available = (
        long.groupby(["road_section", "year", "traffic_period"])["frequency_pct"]
        .apply(lambda values: values.notna().any())
    )
    frequency_sums = (
        long.dropna(subset=["variable"])
        .groupby(
            ["road_section", "year", "traffic_period", "variable"]
        )["frequency_pct"]
        .sum(min_count=1)
    )
    bad_sums = frequency_sums.dropna().sub(100).abs().gt(0.02)
    if bad_sums.any():
        raise ValueError("Wind-frequency percentages do not sum to 100 within tolerance")

    section_years = base.drop_duplicates(["road_section", "year"])
    valid_other = section_years["other_daily_traffic_derived"].notna()
    assignment_counts = base["station_assignment_method"].value_counts()

    return pd.DataFrame(
        [
            {"metric": "road_sections", "value": base["road_section"].nunique()},
            {
                "metric": "road_section_years",
                "value": base[["road_section", "year"]].drop_duplicates().shape[0],
            },
            {"metric": "road_section_year_traffic_periods", "value": len(base)},
            {
                "metric": "periods_with_wind_frequency",
                "value": int(period_available.sum()),
            },
            {
                "metric": "periods_assigned_nearest_valid_station_within_20km",
                "value": int(base["weather_station_id"].notna().sum()),
            },
            {
                "metric": "periods_with_nearby_station_but_no_clean_data",
                "value": int(
                    assignment_counts.get(
                        "nearby_stations_but_no_clean_period_data", 0
                    )
                ),
            },
            {
                "metric": "periods_without_station_within_20km",
                "value": int(
                    assignment_counts.get(
                        "no_station_within_20km_of_section_midpoint", 0
                    )
                ),
            },
            {
                "metric": "wind_frequency_coverage_pct",
                "value": round(100 * period_available.mean(), 2),
            },
            {
                "metric": "periods_with_known_surface",
                "value": int(base["surface_code"].notna().sum()),
            },
            {
                "metric": "known_surface_coverage_pct",
                "value": round(100 * base["surface_code"].notna().mean(), 2),
            },
            {"metric": "matched_injury_accidents", "value": matched_accidents},
            {
                "metric": "matched_serious_or_fatal_accidents",
                "value": matched_serious,
            },
            {
                "metric": "matched_accidents_with_clean_wind_within_20km",
                "value": expected_bin_accidents,
            },
            {
                "metric": "matched_accidents_excluded_from_wind_bins",
                "value": accident_diagnostics[
                    "exact_matches_excluded_from_wind_bins"
                ],
            },
            {
                "metric": "matched_accident_wind_bin_coverage_pct",
                "value": round(
                    accident_diagnostics["clean_wind_bin_coverage_pct_x100"] / 100,
                    2,
                ),
            },
            {
                "metric": "wind_bin_serious_or_fatal_accidents",
                "value": expected_bin_serious,
            },
            {
                "metric": "wind_bin_accidents_with_section_period_frequency",
                "value": int(f_with_frequency["bin_injury_accidents"].sum()),
            },
            {
                "metric": "wind_bin_serious_or_fatal_with_section_period_frequency",
                "value": int(
                    f_with_frequency["bin_serious_or_fatal_accidents"].sum()
                ),
            },
            {
                "metric": "section_years_with_valid_derived_other_traffic",
                "value": int(valid_other.sum()),
            },
            {
                "metric": "section_years_with_nonpositive_derived_other_traffic",
                "value": int((~valid_other).sum()),
            },
            {
                "metric": "derived_other_traffic_coverage_pct",
                "value": round(100 * valid_other.mean(), 2),
            },
        ]
    )


def plot_traffic_period_summary(wide: pd.DataFrame, path: Path) -> None:
    """Plot accident counts and official daily traffic by traffic period."""
    order = ["VDU", "SDU", "VHDU"]
    display_labels = [
        "VDU\nDec-Mar",
        "SDU\nJun-Sep",
        "VHDU\nApr-May, Oct-Nov",
    ]
    accidents = (
        wide.groupby("traffic_period", as_index=True)
        .agg(
            injury_accidents=("injury_accidents", "sum"),
            serious_or_fatal_accidents=("serious_or_fatal_accidents", "sum"),
        )
        .reindex(order)
    )
    accidents["minor_injury_accidents"] = (
        accidents["injury_accidents"]
        - accidents["serious_or_fatal_accidents"]
    )
    traffic = (
        wide.groupby("traffic_period")["traffic_reference_daily_volume"]
        .median()
        .reindex(order)
    )

    fig, axes = plt.subplots(2, 1, figsize=(10.5, 8.5), constrained_layout=True)
    x = np.arange(len(order))
    minor = accidents["minor_injury_accidents"].to_numpy()
    serious = accidents["serious_or_fatal_accidents"].to_numpy()
    axes[0].bar(x, minor, color="#287271", label="Minor injury")
    axes[0].bar(
        x,
        serious,
        bottom=minor,
        color="#C7522A",
        label="Serious or fatal",
    )
    for position, total in zip(x, accidents["injury_accidents"], strict=True):
        axes[0].text(
            position,
            total + 6,
            f"n={int(total)}",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    axes[0].set_xticks(x, display_labels)
    axes[0].set_ylabel("Exact-matched accidents")
    axes[0].set_title("Accidents by injury severity")
    axes[0].legend(frameon=False, ncols=2, loc="upper right")
    axes[0].grid(axis="y", alpha=0.2)
    axes[0].set_ylim(0, accidents["injury_accidents"].max() * 1.2)

    traffic_values = traffic.to_numpy(dtype=float)
    axes[1].bar(
        x,
        traffic_values,
        color=["#577590", "#43AA8B", "#F9C74F"],
        width=0.8,
    )
    for position, value in zip(x, traffic_values, strict=True):
        axes[1].text(
            position,
            value + 30,
            f"{value:,.0f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    axes[1].set_xticks(x, display_labels)
    axes[1].set_ylabel("Median vehicles per day")
    axes[1].set_title(
        "Official VDU/SDU and ADU-derived VHDU daily traffic"
    )
    axes[1].grid(axis="y", alpha=0.2)
    axes[1].set_ylim(0, max(traffic_values) * 1.22)

    fig.suptitle(
        "Accidents and traffic by official traffic period\n"
        "Rural injury accidents with exact road-section exposure matches, 2007-2025"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def traffic_period_days(year: int, period: str) -> int:
    """Return the calendar days covered by an official traffic period."""
    return sum(
        calendar.monthrange(int(year), month)[1]
        for month in TRAFFIC_PERIOD_MONTH_NUMBERS[period]
    )


def poisson_rate_interval(
    count: pd.Series, exposure: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """Calculate exact 95% Poisson intervals for a rate per 100 million km."""
    count_values = count.to_numpy(dtype=float)
    exposure_values = exposure.to_numpy(dtype=float)
    lower_counts = np.where(
        count_values > 0,
        0.5 * chi2.ppf(0.025, 2 * count_values),
        0.0,
    )
    upper_counts = 0.5 * chi2.ppf(0.975, 2 * (count_values + 1))
    scale = 100_000_000 / exposure_values
    return pd.Series(lower_counts * scale), pd.Series(upper_counts * scale)


def build_traffic_adjusted_rates(
    wide: pd.DataFrame,
    accidents_path: Path,
    traffic_periods: tuple[str, ...] = ("VDU", "SDU", "VHDU"),
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Estimate rates using wind frequency and period-specific traffic.

    The denominator assumes that official average daily traffic is distributed
    across wind intervals in proportion to the interval's share of 10-minute
    weather observations. This is an estimated comparison, not observed
    traffic in each wind interval.
    """
    key = ["road_section", "year", "traffic_period"]
    unknown_periods = set(traffic_periods) - set(TRAFFIC_PERIOD_MONTH_NUMBERS)
    if unknown_periods:
        raise ValueError(f"Unknown traffic periods: {sorted(unknown_periods)}")
    panel = wide[wide["traffic_period"].isin(traffic_periods)].copy()
    panel = panel.dropna(
        subset=["traffic_reference_daily_volume", "section_length_km"]
    )
    panel = panel[
        panel["traffic_reference_daily_volume"].gt(0)
        & panel["section_length_km"].gt(0)
    ].copy()
    panel["period_days"] = [
        traffic_period_days(year, period)
        for year, period in zip(
            panel["year"], panel["traffic_period"], strict=True
        )
    ]

    accidents = pd.read_parquet(
        accidents_path,
        columns=[
            "nid",
            "timestamp",
            "meidsli",
            "registered_road_section",
            "weather_station_id",
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
    accidents = accidents.merge(
        panel[key + ["weather_station_id"]],
        on=key,
        how="inner",
        validate="many_to_one",
        suffixes=("_accident", "_section"),
    )
    accidents = accidents[
        accidents["within_20km"].fillna(False)
        & accidents["wind_available"].fillna(False)
        & accidents["f"].between(0, 45, inclusive="left")
        & accidents["fg"].between(0, 65, inclusive="left")
    ].copy()

    output: list[pd.DataFrame] = []
    diagnostics: dict[str, object] = {
        "included_traffic_periods": "|".join(traffic_periods),
        "eligible_accidents_before_frequency_coverage": len(accidents),
        "same_station_accidents_before_frequency_coverage": int(
            accidents["weather_station_id_accident"].eq(
                accidents["weather_station_id_section"]
            ).sum()
        ),
    }
    for variable, upper_bounds in [("f", F_UPPER_BOUNDS), ("fg", FG_UPPER_BOUNDS)]:
        bin_labels = labels(upper_bounds)
        frequency_columns = {
            f"{variable}_frequency_pct_"
            f"{label.replace('>=', 'ge_').replace('-', '_')}": label
            for label in bin_labels
        }
        exposure = panel[
            key
            + [
                "traffic_reference_daily_volume",
                "section_length_km",
                "period_days",
            ]
            + list(frequency_columns)
        ].melt(
            id_vars=key
            + [
                "traffic_reference_daily_volume",
                "section_length_km",
                "period_days",
            ],
            value_vars=list(frequency_columns),
            var_name="frequency_column",
            value_name="wind_frequency_pct",
        )
        exposure["wind_bin"] = exposure["frequency_column"].map(frequency_columns)
        exposure["estimated_vehicle_km"] = (
            exposure["traffic_reference_daily_volume"]
            * exposure["section_length_km"]
            * exposure["period_days"]
            * exposure["wind_frequency_pct"]
            / 100
        )
        available_keys = exposure.loc[
            exposure["wind_frequency_pct"].notna(), key
        ].drop_duplicates()
        accident_bins = accidents.merge(
            available_keys,
            on=key,
            how="inner",
            validate="many_to_one",
        )
        diagnostics[f"{variable}_accidents_with_frequency_exposure"] = len(
            accident_bins
        )
        diagnostics[f"{variable}_serious_or_fatal_accidents"] = int(
            accident_bins["meidsli"].le(2).sum()
        )
        diagnostics[f"{variable}_same_station_accidents"] = int(
            accident_bins["weather_station_id_accident"].eq(
                accident_bins["weather_station_id_section"]
            ).sum()
        )
        group_accidents = (
            accident_bins.groupby(key, as_index=False)["nid"]
            .nunique()
            .rename(columns={"nid": "group_accidents"})
        )
        weather_expected = exposure.merge(
            group_accidents,
            on=key,
            how="left",
            validate="many_to_one",
        )
        weather_expected["weather_expected_accidents"] = (
            weather_expected["group_accidents"].fillna(0)
            * weather_expected["wind_frequency_pct"]
            / 100
        )
        exposure_summary = (
            exposure.groupby("wind_bin", as_index=False, observed=False)
            .agg(
                estimated_vehicle_km=("estimated_vehicle_km", "sum"),
                contributing_section_periods=("estimated_vehicle_km", "count"),
            )
            .set_index("wind_bin")
            .reindex(bin_labels)
            .reset_index()
        )
        weather_expected_summary = (
            weather_expected.groupby("wind_bin", as_index=False, observed=False)[
                "weather_expected_accidents"
            ]
            .sum()
            .set_index("wind_bin")
            .reindex(bin_labels)
            .reset_index()
        )

        edges = np.concatenate(([0.0], upper_bounds, [np.inf]))
        accident_bins["wind_bin"] = pd.cut(
            accident_bins[variable],
            bins=edges,
            labels=bin_labels,
            right=False,
            include_lowest=True,
        )
        observed = (
            accident_bins.groupby("wind_bin", as_index=False, observed=False)
            .agg(
                injury_accidents=("nid", "size"),
                serious_or_fatal_accidents=(
                    "meidsli", lambda values: int(values.le(2).sum())
                ),
            )
            .set_index("wind_bin")
            .reindex(bin_labels, fill_value=0)
            .reset_index()
        )
        result = exposure_summary.merge(
            observed, on="wind_bin", how="left", validate="one_to_one"
        ).merge(
            weather_expected_summary,
            on="wind_bin",
            how="left",
            validate="one_to_one",
        )
        result.insert(0, "variable", variable)
        result.insert(2, "bin_order", np.arange(len(result)))
        result["rate_per_100m_vehicle_km"] = (
            result["injury_accidents"] / result["estimated_vehicle_km"] * 100_000_000
        )
        result["weather_only_observed_expected"] = (
            result["injury_accidents"] / result["weather_expected_accidents"]
        )
        result["traffic_weather_expected_accidents"] = (
            result["injury_accidents"].sum()
            * result["estimated_vehicle_km"]
            / result["estimated_vehicle_km"].sum()
        )
        result["traffic_weather_observed_expected"] = (
            result["injury_accidents"]
            / result["traffic_weather_expected_accidents"]
        )
        low, high = poisson_rate_interval(
            result["injury_accidents"], result["estimated_vehicle_km"]
        )
        result["rate_ci_95_low"] = low
        result["rate_ci_95_high"] = high
        result["sparse_bin"] = result["injury_accidents"].lt(20)
        output.append(result)

    rates = pd.concat(output, ignore_index=True)
    return rates, diagnostics


def build_scope_comparison(
    all_periods: pd.DataFrame, sdu_vdu: pd.DataFrame
) -> pd.DataFrame:
    """Compare all-period and official SDU/VDU-only estimates bin by bin."""
    columns = [
        "variable", "wind_bin", "bin_order", "estimated_vehicle_km",
        "injury_accidents", "rate_per_100m_vehicle_km",
        "traffic_weather_observed_expected", "rate_ci_95_low", "rate_ci_95_high",
    ]
    comparison = all_periods[columns].merge(
        sdu_vdu[columns], on=["variable", "wind_bin", "bin_order"],
        how="inner", suffixes=("_all_periods", "_sdu_vdu"),
        validate="one_to_one",
    )
    comparison["vehicle_km_retained_pct"] = (
        100 * comparison["estimated_vehicle_km_sdu_vdu"]
        / comparison["estimated_vehicle_km_all_periods"]
    )
    comparison["accidents_retained_pct"] = (
        100 * comparison["injury_accidents_sdu_vdu"]
        / comparison["injury_accidents_all_periods"].replace(0, np.nan)
    )
    comparison["rate_ratio_sdu_vdu_vs_all"] = (
        comparison["rate_per_100m_vehicle_km_sdu_vdu"]
        / comparison["rate_per_100m_vehicle_km_all_periods"]
    )
    return comparison


def plot_scope_comparison(comparison: pd.DataFrame, path: Path) -> None:
    """Plot direct all-period versus official SDU/VDU-only rates."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), constrained_layout=True)
    settings = [("f", "Mean wind-speed interval, f (m/s)"),
                ("fg", "Maximum wind-gust interval, fg (m/s)")]
    width = 0.38
    for axis, (variable, x_label) in zip(axes, settings, strict=True):
        data = comparison[comparison["variable"].eq(variable)].sort_values("bin_order")
        x = np.arange(len(data))
        axis.bar(
            x - width / 2, data["rate_per_100m_vehicle_km_all_periods"], width,
            label="VDU + SDU + derived VHDU", color="#8A9AA6",
        )
        axis.bar(
            x + width / 2, data["rate_per_100m_vehicle_km_sdu_vdu"], width,
            label="Official VDU + SDU only", color="#287271",
        )
        display = data["wind_bin"].str.replace(">=", "≥", regex=False)
        axis.set_xticks(x, display)
        axis.set_xlabel(x_label)
        axis.set_ylabel("Injury accidents per 100 million vehicle-km")
        axis.grid(axis="y", alpha=0.2)
    axes[0].legend(frameon=False, ncols=2, loc="upper left")
    fig.suptitle(
        "Effect of excluding ADU-derived VHDU traffic\n"
        "Same method; SDU/VDU-only analysis excludes Apr, May, Oct, and Nov"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def plot_traffic_adjusted_rates(
    rates: pd.DataFrame,
    path: Path,
    scope_label: str = "VDU, SDU, and ADU-derived VHDU periods",
) -> None:
    """Plot wind-frequency and seasonal-traffic-adjusted accident rates."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), constrained_layout=True)
    settings = [
        ("f", "Mean wind speed, f (m/s)", "#287271"),
        ("fg", "Maximum wind gust, fg (m/s)", "#C7522A"),
    ]
    for axis, (variable, x_label, color) in zip(axes, settings, strict=True):
        data = rates[rates["variable"].eq(variable)].sort_values("bin_order")
        x = np.arange(len(data))
        rate = data["rate_per_100m_vehicle_km"].to_numpy()
        lower = data["rate_ci_95_low"].to_numpy()
        upper = data["rate_ci_95_high"].to_numpy()
        colors = ["#A7A7A7" if sparse else color for sparse in data["sparse_bin"]]
        axis.bar(
            x,
            rate,
            color=colors,
            yerr=np.vstack([rate - lower, upper - rate]),
            capsize=3,
            error_kw={"elinewidth": 1, "ecolor": "#333333"},
        )
        label_height = max(upper) * 0.025
        for position, point, count in zip(
            x, upper, data["injury_accidents"], strict=True
        ):
            axis.text(
                position,
                point + label_height,
                f"n={int(count)}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
        display_bins = data["wind_bin"].str.replace(">=", "≥", regex=False)
        axis.set_xticks(x, display_bins)
        axis.set_xlabel(x_label.replace("speed,", "speed interval,").replace("gust,", "gust interval,"))
        axis.set_ylabel("Injury accidents per 100 million vehicle-km")
        axis.grid(axis="y", alpha=0.2)
        axis.set_ylim(0, max(upper) * 1.16)
        axis.text(
            0.99,
            0.96,
            "Grey: fewer than 20 accidents",
            transform=axis.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            color="#555555",
        )

    fig.suptitle(
        "Wind-frequency and traffic-adjusted injury accident rates\n"
        f"{scope_label}; exact road-section matches, 2007-2025"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def plot_adjustment_comparison(rates: pd.DataFrame, path: Path) -> None:
    """Compare wind-frequency-only and traffic-plus-frequency adjustment."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), constrained_layout=True)
    settings = [
        ("f", "Mean wind speed, f (m/s)"),
        ("fg", "Maximum wind gust, fg (m/s)"),
    ]
    width = 0.38
    for axis, (variable, x_label) in zip(axes, settings, strict=True):
        data = rates[rates["variable"].eq(variable)].sort_values("bin_order")
        x = np.arange(len(data))
        weather_only = data["weather_only_observed_expected"].to_numpy()
        traffic_weather = data["traffic_weather_observed_expected"].to_numpy()
        axis.bar(
            x - width / 2,
            weather_only,
            width,
            color="#577590",
            label="Wind frequency only",
        )
        axis.bar(
            x + width / 2,
            traffic_weather,
            width,
            color="#C7522A",
            label="Wind frequency + estimated period traffic",
        )
        upper = np.maximum(weather_only, traffic_weather)
        axis.axhline(1, color="#222222", linestyle="--", linewidth=1)
        display_bins = data["wind_bin"].str.replace(">=", "≥", regex=False)
        axis.set_xticks(x, display_bins)
        axis.set_xlabel(x_label.replace("speed,", "speed interval,").replace("gust,", "gust interval,"))
        axis.set_ylabel("Observed / expected accidents")
        axis.grid(axis="y", alpha=0.2)
        axis.set_ylim(0, max(1.5, max(upper) * 1.15))
    axes[0].legend(frameon=False, ncols=2, loc="upper left")
    fig.suptitle(
        "Effect of estimated traffic adjustment"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def write_notes(
    path: Path, coverage: pd.DataFrame, traffic_rate_diagnostics: dict[str, int]
) -> None:
    values = coverage.set_index("metric")["value"]
    notes = f"""Road-section wind table, 2007-2025
=====================================

Unit of the wide table
----------------------
One row represents a road section, calendar year, and official traffic period.
Wind frequency columns give the percentage of cleaned 10-minute observations
in each f or fg interval at the assigned weather station in that year/period.

Traffic periods
---------------
- VDU: December-March.
- SDU: June, July, August, and September.
- VHDU: April, May, October, and November. Its average daily traffic is derived
  as the annual ADU total minus the day-weighted SDU and VDU totals, divided by
  the number of VHDU days. This is a residual estimate, not an official ODU.
Official definitions: https://www.vegagerdin.is/samgongukerfid/vegakerfid/umferdartolur

Scope and coverage
------------------
- Road sections: {int(values['road_sections']):,}
- Road-section/year rows before traffic periods: {int(values['road_section_years']):,}
- Road-section/year/traffic-period rows: {int(values['road_section_year_traffic_periods']):,}
- Rows with wind frequency: {int(values['periods_with_wind_frequency']):,}
  ({float(values['wind_frequency_coverage_pct']):.2f}%)
- Missing because nearby stations have no clean data in the period:
  {int(values['periods_with_nearby_station_but_no_clean_data']):,}
- Missing because no station is within 20 km of the section midpoint:
  {int(values['periods_without_station_within_20km']):,}
- Exact annual-exposure injury accidents represented: {int(values['matched_injury_accidents']):,}
- Serious-or-fatal accidents represented: {int(values['matched_serious_or_fatal_accidents']):,}
- Exact matches with clean wind within 20 km and an actual f/fg bin:
  {int(values['matched_accidents_with_clean_wind_within_20km']):,}
  ({float(values['matched_accident_wind_bin_coverage_pct']):.2f}%)
- Exact matches excluded from wind-bin counts:
  {int(values['matched_accidents_excluded_from_wind_bins']):,}
- Section-years with a valid derived VHDU traffic value:
  {int(values['section_years_with_valid_derived_other_traffic']):,}
  ({float(values['derived_other_traffic_coverage_pct']):.2f}%)

Supporting figure
-----------------
The bar chart shows exact-matched injury accidents by traffic period, stacked
by severity, and the median official daily traffic across the included
road-section/year rows. The accident bars are descriptive counts and are not
traffic-adjusted rates. The VHDU traffic bar is the ADU/SDU/VDU residual.

Annual-traffic comparison figure
-----------------------------------
The traffic-adjusted figure includes
{traffic_rate_diagnostics['f_accidents_with_frequency_exposure']:,}
exact-matched injury accidents with period traffic and local wind-frequency
exposure, including
{traffic_rate_diagnostics['f_serious_or_fatal_accidents']:,} serious-or-fatal accidents.
For each road-section/year/period/bin, estimated vehicle-kilometres equal the
VDU, SDU, or derived VHDU daily volume times section length, calendar days, and the
bin's share of cleaned 10-minute wind observations. Rates are shown per 100
million estimated vehicle-kilometres with exact 95% Poisson intervals.

This estimate assumes traffic is distributed across wind intervals in
proportion to time. It does not use observed traffic under each wind condition.
Only {traffic_rate_diagnostics['f_same_station_accidents']:,} of the included
accidents used the same station as the nearest valid midpoint station assigned
to their road section/year/period; other accident observations are local proxies but
do not use the identical station as the denominator. The figure is therefore a
comparison result, not the primary wind-risk estimate. Grey bars contain fewer
than 20 accidents.

The adjustment-comparison figure uses the same restricted accident subset for
both series. Blue bars show observed/expected after local wind-frequency
standardization only; orange bars additionally use estimated period
vehicle-kilometres. The n labels are the unadjusted accident counts. There is
no meaningful unadjusted observed/expected ratio because expected counts require
an exposure distribution; raw counts are therefore shown as labels rather than
as a third ratio.

Assignment rules
----------------
- For each section/year/period, the assigned weather station is the nearest
  station to the official road-section midpoint that has clean observations in
  that period, within 20 km. Missing midpoints are derived from official road
  geometry. No wider-radius station is silently substituted.
- Accident counts are exact section/year matches and are assigned to VDU, SDU,
  or VHDU from the accident month. The two readable bin tables count each
  accident in its actual matched f or fg interval; they do not repeat period totals.
- Surface is the modal known surface_code_1 among accident reports linked to
  that section and year. It is not an authoritative road-asset inventory.
- ADU, SDU, VDU, section length, and annual vehicle-kilometres come directly
  from the annual Vegagerdin road-section file for that year.

Limitations
-----------
This is a descriptive table. Wind frequency follows the traffic-period months.
The derived VHDU traffic value assumes the annual, SDU, and VDU figures are
mutually consistent; nonpositive residuals are left missing. Traffic is allocated
to wind intervals in the comparison in proportion to wind frequency,
not from observed traffic under each wind condition. A station is still a proxy
for conditions across the road section. When the nearest station lacks period
data, the next-nearest valid station within 20 km is used; otherwise frequency
remains missing. Zero accidents
means no exact matched rural injury accident in that section/year/period, not
proof that no accident occurred.
"""
    path.write_text(notes, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the descriptive 2007-2025 road-section wind table."
    )
    parser.add_argument("-a", "--annual-traffic", type=Path, default=DEFAULT_ANNUAL_TRAFFIC)
    parser.add_argument("-A", "--all-accidents", type=Path, default=DEFAULT_ALL_ACCIDENTS)
    parser.add_argument(
        "-i", "--injury-accidents", type=Path, default=DEFAULT_INJURY_ACCIDENTS
    )
    parser.add_argument("-w", "--weather", type=Path, default=DEFAULT_WEATHER)
    parser.add_argument(
        "-p", "--period-wind-frequency",
        type=Path,
        default=DEFAULT_PERIOD_WIND_FREQUENCY,
    )
    parser.add_argument("-r", "--rebuild-period-wind-frequency", action="store_true")
    parser.add_argument("-m", "--max-weather-row-groups", type=int)
    parser.add_argument(
        "-K", "--cache-only", action="store_true",
        help="Write only the road-period cache required by the annual-traffic comparison.",
    )
    parser.add_argument("-u", "--surface", type=Path, default=DEFAULT_SURFACE)
    parser.add_argument("-s", "--stations", type=Path, default=DEFAULT_STATIONS)
    parser.add_argument(
        "-M", "--section-midpoints", type=Path, default=DEFAULT_SECTION_MIDPOINTS
    )
    parser.add_argument("-o", "--long-output", type=Path, default=DEFAULT_LONG)
    parser.add_argument("-O", "--wide-output", type=Path, default=DEFAULT_WIDE)
    parser.add_argument(
        "-x", "--accident-rows-output", type=Path, default=DEFAULT_ACCIDENT_ROWS
    )
    parser.add_argument(
        "-f", "--mean-wind-table", type=Path, default=DEFAULT_MEAN_WIND_TABLE
    )
    parser.add_argument("-g", "--gust-table", type=Path, default=DEFAULT_GUST_TABLE)
    parser.add_argument("-c", "--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("-n", "--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("-F", "--figure", type=Path, default=DEFAULT_FIGURE)
    parser.add_argument(
        "-t", "--traffic-adjusted-rates",
        type=Path,
        default=DEFAULT_TRAFFIC_ADJUSTED_RATES,
    )
    parser.add_argument(
        "-T", "--traffic-adjusted-figure",
        type=Path,
        default=DEFAULT_TRAFFIC_ADJUSTED_FIGURE,
    )
    parser.add_argument(
        "-C", "--adjustment-comparison-figure",
        type=Path,
        default=DEFAULT_ADJUSTMENT_COMPARISON_FIGURE,
    )
    parser.add_argument("-v", "--sdu-vdu-rates", type=Path, default=DEFAULT_SDU_VDU_RATES)
    parser.add_argument("-V", "--sdu-vdu-figure", type=Path, default=DEFAULT_SDU_VDU_FIGURE)
    parser.add_argument(
        "-q", "--scope-comparison", type=Path, default=DEFAULT_SCOPE_COMPARISON
    )
    parser.add_argument(
        "-Q", "--scope-comparison-figure", type=Path,
        default=DEFAULT_SCOPE_COMPARISON_FIGURE,
    )
    args = parser.parse_args()

    annual = load_annual_traffic(args.annual_traffic)
    section_scope = build_section_scope(args.all_accidents, annual)
    station_candidates = build_station_candidates(
        section_scope, args.section_midpoints, args.stations
    )
    counts, bin_counts, accident_diagnostics = build_accident_counts(
        args.injury_accidents, annual
    )
    surface = build_surface_table(args.surface)
    if args.rebuild_period_wind_frequency or not args.period_wind_frequency.exists():
        wind = build_period_wind_frequency(
            args.weather,
            args.period_wind_frequency,
            station_candidates["weather_station_id"].drop_duplicates().to_numpy(),
            max_row_groups=args.max_weather_row_groups,
        )
    else:
        wind = pd.read_parquet(args.period_wind_frequency)
    assigned_panel = assign_nearest_valid_station(
        annual, section_scope, station_candidates, wind
    )
    base = build_base_table(assigned_panel, counts, surface)
    long = build_long_table(base, wind, bin_counts)
    if args.cache_only:
        args.long_output.parent.mkdir(parents=True, exist_ok=True)
        long.to_parquet(args.long_output, index=False, compression="zstd")
        print(f"road_period_rows={len(long):,}")
        return
    wide = build_wide_table(base, long)
    mean_wind_table = build_readable_bin_table(long, "f")
    gust_table = build_readable_bin_table(long, "fg")
    coverage = validate_and_summarize(base, long, accident_diagnostics)
    traffic_adjusted_rates, traffic_rate_diagnostics = build_traffic_adjusted_rates(
        wide, args.injury_accidents
    )
    sdu_vdu_rates, sdu_vdu_diagnostics = build_traffic_adjusted_rates(
        wide, args.injury_accidents, traffic_periods=("VDU", "SDU")
    )
    scope_comparison = build_scope_comparison(
        traffic_adjusted_rates, sdu_vdu_rates
    )

    for path in [
        args.long_output,
        args.wide_output,
        args.accident_rows_output,
        args.mean_wind_table,
        args.gust_table,
        args.coverage,
        args.notes,
        args.figure,
        args.traffic_adjusted_rates,
        args.traffic_adjusted_figure,
        args.adjustment_comparison_figure,
        args.sdu_vdu_rates,
        args.sdu_vdu_figure,
        args.scope_comparison,
        args.scope_comparison_figure,
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
    long.to_parquet(args.long_output, index=False, compression="zstd")
    wide.to_csv(args.wide_output, index=False)
    wide[wide["injury_accidents"].gt(0)].to_csv(
        args.accident_rows_output, index=False
    )
    mean_wind_table.to_csv(args.mean_wind_table, index=False)
    gust_table.to_csv(args.gust_table, index=False)
    coverage.to_csv(args.coverage, index=False)
    traffic_adjusted_rates.to_csv(args.traffic_adjusted_rates, index=False)
    sdu_vdu_rates.to_csv(args.sdu_vdu_rates, index=False)
    scope_comparison.to_csv(args.scope_comparison, index=False)
    write_notes(args.notes, coverage, traffic_rate_diagnostics)
    plot_traffic_period_summary(wide, args.figure)
    plot_traffic_adjusted_rates(
        traffic_adjusted_rates, args.traffic_adjusted_figure
    )
    plot_adjustment_comparison(
        sdu_vdu_rates, args.adjustment_comparison_figure
    )
    plot_traffic_adjusted_rates(
        sdu_vdu_rates, args.sdu_vdu_figure,
        scope_label="Official VDU and SDU periods only (8 months per year)",
    )
    plot_scope_comparison(scope_comparison, args.scope_comparison_figure)
    print(coverage.to_string(index=False))
    print(
        "traffic_adjusted_accidents="
        f"{traffic_rate_diagnostics['f_accidents_with_frequency_exposure']:,} "
        "same_section_station="
        f"{traffic_rate_diagnostics['f_same_station_accidents']:,}"
    )
    print(
        "sdu_vdu_accidents="
        f"{sdu_vdu_diagnostics['f_accidents_with_frequency_exposure']:,} "
        "excluded_other_accidents="
        f"{traffic_rate_diagnostics['f_accidents_with_frequency_exposure'] - sdu_vdu_diagnostics['f_accidents_with_frequency_exposure']:,}"
    )
    print(f"long_rows={len(long):,} wide_rows={len(wide):,}")


if __name__ == "__main__":
    main()
