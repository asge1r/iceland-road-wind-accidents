"""Shared functions for daily-counter weather matching and quality control.

The unit of observation is one counter on one date. This avoids summing
different counters located on the same road section. Weather is represented by
the nearest clean station to the counter location interpolated from the PDF
road station and official road geometry. The 24-hour
daily traffic total is never divided into hourly values. It is paired with
daytime weather summaries (10:00-21:59), so this supports a day-level
supplementary analysis but cannot estimate traffic at each wind hour.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.neighbors import BallTree

from src.weather.frequency import FG_UPPER_BOUNDS, labels


EARTH_RADIUS_KM = 6371.0088
# The daily traffic diagnostic is descriptive, so it retains its sparse upper
# mean-wind tail through 33 m/s. The primary O/E analysis retains its separate
# 24+ m/s mean-wind specification from weather.frequency.
DAILY_F_UPPER_BOUNDS = np.arange(3, 34, 3, dtype=float)
# Station 7475 (Reykjavík búveðurstöð reits) has a documented implausible
# high-wind tail in the daily diagnostic (mean wind up to 49.6 m/s). It is
# therefore not used as a weather proxy for the descriptive traffic analysis.
DAILY_WIND_EXCLUDED_STATION_IDS = {7475}


def normalize_section(values: pd.Series) -> pd.Series:
    """Normalize registered road-section identifiers."""
    return values.astype("string").str.strip().str.lower()


def read_daily(path: Path, start_year: int, end_year: int) -> pd.DataFrame:
    """Read one CSV row per physical counter site and date."""
    raw = pd.read_csv(path, dtype={"source_fastnr": "string"}, low_memory=False)
    required = {
        "date", "year", "counter_site_id", "station_id", "road_section",
        "traffic_volume",
    }
    missing = required - set(raw)
    if missing:
        raise ValueError(f"Daily counter data are missing columns: {sorted(missing)}")
    raw = raw[raw["year"].between(start_year, end_year)].copy()
    raw["date"] = pd.to_datetime(raw["date"])
    raw["road_section"] = normalize_section(raw["road_section"])
    raw["station_id"] = pd.to_numeric(
        raw["station_id"], errors="raise"
    ).astype(int)
    raw["traffic_volume"] = pd.to_numeric(
        raw["traffic_volume"], errors="raise"
    ).astype(float)
    if raw["traffic_volume"].lt(0).any():
        raise ValueError("Daily traffic contains negative values")

    if raw.duplicated(["counter_site_id", "date"]).any():
        raise ValueError("Daily traffic is not unique on site + date")
    return raw


def weather_station_ids(weather_file: pq.ParquetFile) -> set[int]:
    """Read station identifiers, using row-group statistics when possible."""
    result: set[int] = set()
    station_index = weather_file.schema_arrow.names.index("station")
    for row_group in range(weather_file.metadata.num_row_groups):
        statistics = weather_file.metadata.row_group(row_group).column(
            station_index
        ).statistics
        if statistics and statistics.has_min_max and statistics.min == statistics.max:
            result.add(int(statistics.min))
        else:
            values = weather_file.read_row_group(
                row_group, columns=["station"]
            ).column("station")
            result.update(int(value) for value in values.unique().to_pylist())
    return result


def build_counter_station_map(
    daily: pd.DataFrame,
    stations_path: Path,
    valid_station_ids: set[int],
    max_distance_km: float = 20,
    candidates_per_counter: int = 10,
) -> pd.DataFrame:
    """Return nearby usable stations for each physical traffic counter.

    ``location_lat`` and ``location_lon`` are estimates interpolated from the
    PDF road station and official road-section geometry. They are not treated
    as surveyed counter coordinates.
    """
    required = {
        "counter_site_id",
        "road_section",
        "location_lat",
        "location_lon",
        "location_method",
        "location_is_estimated",
    }
    missing = required - set(daily)
    if missing:
        raise ValueError(
            f"Canonical daily traffic is missing location columns: {sorted(missing)}"
        )
    counters = daily[
        [
            "counter_site_id",
            "road_section",
            "location_lat",
            "location_lon",
            "location_method",
            "location_is_estimated",
        ]
    ].drop_duplicates("counter_site_id")
    counters = counters.dropna(subset=["location_lat", "location_lon"])

    stations = pd.read_csv(
        stations_path, usecols=["station", "name", "lat", "lon"]
    )
    stations["station"] = pd.to_numeric(stations["station"], errors="coerce")
    stations = stations[
        stations["station"].isin(valid_station_ids)
        & stations["lat"].notna()
        & stations["lon"].notna()
    ].drop_duplicates("station")
    stations["station"] = stations["station"].astype(int)

    tree = BallTree(np.radians(stations[["lat", "lon"]]), metric="haversine")
    candidate_count = min(candidates_per_counter, len(stations))
    distance, station_index = tree.query(
        np.radians(counters[["location_lat", "location_lon"]]),
        k=candidate_count,
    )
    rows = []
    for counter_position, counter in counters.reset_index(drop=True).iterrows():
        for rank in range(candidate_count):
            distance_km = distance[counter_position, rank] * EARTH_RADIUS_KM
            if distance_km > max_distance_km:
                continue
            station = stations.iloc[station_index[counter_position, rank]]
            rows.append(
                {
                    "counter_site_id": counter["counter_site_id"],
                    "road_section": counter["road_section"],
                    "counter_location_lat": counter["location_lat"],
                    "counter_location_lon": counter["location_lon"],
                    "counter_location_method": counter["location_method"],
                    "counter_location_is_estimated": counter[
                        "location_is_estimated"
                    ],
                    "weather_station_id": int(station["station"]),
                    "weather_station_name": station["name"],
                    "weather_station_dist_km": distance_km,
                    "weather_candidate_rank": rank + 1,
                }
            )
    return pd.DataFrame(rows)


def row_group_can_contain_station(
    weather_file: pq.ParquetFile, row_group: int, needed: np.ndarray
) -> bool:
    station_index = weather_file.schema_arrow.names.index("station")
    statistics = weather_file.metadata.row_group(row_group).column(
        station_index
    ).statistics
    if not statistics or not statistics.has_min_max:
        return True
    return bool(
        np.any((needed >= int(statistics.min)) & (needed <= int(statistics.max)))
    )


def aggregate_daily_weather(
    weather_file: pq.ParquetFile,
    needed_stations: np.ndarray,
    start_year: int,
    end_year: int,
    max_row_groups: int | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Aggregate clean 10-minute weather to full-day and daytime station means."""
    partials: list[pd.DataFrame] = []
    scanned = 0
    skipped = 0
    total_groups = weather_file.metadata.num_row_groups
    if max_row_groups is not None:
        total_groups = min(total_groups, max_row_groups)

    for row_group in range(total_groups):
        if not row_group_can_contain_station(
            weather_file, row_group, needed_stations
        ):
            skipped += 1
            continue
        scanned += 1
        table = weather_file.read_row_group(
            row_group, columns=["station", "time", "f", "fg"]
        )
        station = table.column("station").to_numpy()
        timestamp = table.column("time").to_numpy().astype("datetime64[us]")
        year = timestamp.astype("datetime64[Y]").astype(np.int64) + 1970
        hour = timestamp.astype("datetime64[h]").astype(np.int64) % 24
        keep = (
            np.isin(station, needed_stations)
            & (year >= start_year)
            & (year <= end_year)
        )
        if not keep.any():
            continue
        f = table.column("f").to_numpy()[keep].astype(float)
        fg = table.column("fg").to_numpy()[keep].astype(float)
        daytime = (hour[keep] >= 10) & (hour[keep] < 22)
        selected = pd.DataFrame(
            {
                "weather_station_id": station[keep].astype(int),
                "date": timestamp[keep].astype("datetime64[D]"),
                "f_full_sum": f,
                "fg_full_sum": fg,
                "full_observation_count": 1,
                "f_daytime_sum": np.where(daytime, f, 0.0),
                "fg_daytime_sum": np.where(daytime, fg, 0.0),
                "daytime_observation_count": daytime.astype(int),
                "f_full_bin_0_5_count": (f < 5).astype(int),
                "f_full_bin_5_10_count": ((f >= 5) & (f < 10)).astype(int),
                "f_full_bin_10_15_count": ((f >= 10) & (f < 15)).astype(int),
                "f_full_bin_15_20_count": ((f >= 15) & (f < 20)).astype(int),
                "f_full_bin_20_25_count": ((f >= 20) & (f < 25)).astype(int),
                "f_full_bin_ge25_count": (f >= 25).astype(int),
            }
        )
        bin_columns = [column for column in selected if column.startswith("f_full_bin_")]
        aggregations = {
            "f_full_sum": ("f_full_sum", "sum"),
            "fg_full_sum": ("fg_full_sum", "sum"),
            "full_observation_count": ("full_observation_count", "sum"),
            "f_daytime_sum": ("f_daytime_sum", "sum"),
            "fg_daytime_sum": ("fg_daytime_sum", "sum"),
            "daytime_observation_count": ("daytime_observation_count", "sum"),
            **{column: (column, "sum") for column in bin_columns},
        }
        partials.append(
            selected.groupby(
                ["weather_station_id", "date"], as_index=False
            ).agg(**aggregations)
        )

    if not partials:
        raise ValueError("No weather observations matched the requested scope")
    weather = pd.concat(partials, ignore_index=True)
    sum_columns = [
        column for column in weather
        if column not in {"weather_station_id", "date"}
    ]
    weather = weather.groupby(
        ["weather_station_id", "date"], as_index=False
    )[sum_columns].sum()
    weather["f_full_day_mean"] = weather["f_full_sum"] / weather["full_observation_count"]
    weather["fg_full_day_mean"] = weather["fg_full_sum"] / weather["full_observation_count"]
    weather["f_daytime_mean"] = weather["f_daytime_sum"] / weather["daytime_observation_count"]
    weather["fg_daytime_mean"] = weather["fg_daytime_sum"] / weather["daytime_observation_count"]
    weather = weather.drop(
        columns=["f_full_sum", "fg_full_sum", "f_daytime_sum", "fg_daytime_sum"]
    )
    diagnostics = {
        "weather_row_groups_considered": total_groups,
        "weather_row_groups_scanned": scanned,
        "weather_row_groups_skipped_by_station": skipped,
    }
    return weather, diagnostics


def build_weather_match_data(
    weather_path: Path,
    daily: pd.DataFrame,
    stations_path: Path,
    start_year: int,
    end_year: int,
    max_row_groups: int | None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build reusable counter-site-day weather from the 10-minute file."""
    weather_file = pq.ParquetFile(weather_path)
    station_map = build_counter_station_map(
        daily, stations_path, weather_station_ids(weather_file)
    )
    needed = np.sort(station_map["weather_station_id"].unique())
    weather, diagnostics = aggregate_daily_weather(
        weather_file, needed, start_year, end_year, max_row_groups
    )
    weather = weather[weather["daytime_observation_count"].gt(0)].copy()
    output = station_map.merge(
        weather, on="weather_station_id", how="left", validate="many_to_many"
    )
    output = output.dropna(subset=["date"]).sort_values(
        [
            "counter_site_id",
            "date",
            "weather_station_dist_km",
            "weather_station_id",
        ]
    )
    output = output.drop_duplicates(["counter_site_id", "date"], keep="first")
    output["weather_match_method"] = "nearest_valid_station_to_interpolated_counter_within_20km"
    if output.duplicated(["counter_site_id", "date"]).any():
        raise ValueError("Daily weather is not unique on counter_site_id + date")
    output["date"] = pd.to_datetime(output["date"])
    diagnostics.update(
        {
            "counter_sites_with_station_within_20km": station_map[
                "counter_site_id"
            ].nunique(),
            "counter_station_candidates": len(station_map),
            "assigned_weather_stations": station_map[
                "weather_station_id"
            ].nunique(),
        }
    )
    return output, diagnostics


def add_normalized_traffic(panel: pd.DataFrame) -> pd.DataFrame:
    """Normalize traffic within counter, year, month, and weekday."""
    panel = panel.copy()
    panel["weekday"] = panel["date"].dt.weekday
    panel["month"] = panel["date"].dt.month
    panel["year"] = panel["date"].dt.year
    baseline_columns = ["counter_site_id", "year", "month", "weekday"]
    baseline = panel.groupby(baseline_columns, as_index=False).agg(
        typical_traffic=("traffic_volume", "median"),
        baseline_days=("traffic_volume", "size"),
    )
    panel = panel.merge(
        baseline, on=baseline_columns, how="left", validate="many_to_one"
    )
    panel["traffic_index"] = np.where(
        panel["typical_traffic"].gt(0),
        100 * panel["traffic_volume"] / panel["typical_traffic"],
        np.nan,
    )
    return panel


def add_bin(data: pd.DataFrame, variable: str, upper_bounds: list[int]) -> pd.DataFrame:
    output = data.copy()
    output["bin"] = pd.cut(
        output[variable],
        bins=[0, *upper_bounds, np.inf],
        labels=labels(upper_bounds),
        right=False,
        include_lowest=True,
        ordered=True,
    )
    return output


def cluster_bootstrap_counter_medians(
    counter_bins: pd.DataFrame,
    bins: list[str],
    replicates: int,
    seed: int = 20260721,
) -> pd.DataFrame:
    """Bootstrap equal-weighted counter medians by resampling counters."""
    wide = counter_bins.pivot(
        index="counter_site_id", columns="bin", values="counter_median_traffic_index"
    ).reindex(columns=bins)
    values = wide.to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    boot = np.full((replicates, len(bins)), np.nan)
    for replicate in range(replicates):
        sampled = rng.integers(0, len(values), len(values))
        with np.errstate(all="ignore"):
            boot[replicate] = np.nanmedian(values[sampled], axis=0)
    return pd.DataFrame(
        {
            "bin": bins,
            "ci_95_low": np.nanpercentile(boot, 2.5, axis=0),
            "ci_95_high": np.nanpercentile(boot, 97.5, axis=0),
        }
    )


def build_wind_summary(panel: pd.DataFrame, replicates: int) -> pd.DataFrame:
    """Summarize normalized traffic by wind with counter-cluster intervals."""
    frames: list[pd.DataFrame] = []
    specs = [
        ("f_daytime_mean", DAILY_F_UPPER_BOUNDS),
        ("fg_daytime_mean", FG_UPPER_BOUNDS),
    ]
    for variable, upper_bounds in specs:
        data = panel.dropna(subset=[variable, "traffic_index"]).copy()
        if variable == "f_daytime_mean":
            # The display ends at 33 m/s. After the station-quality screen,
            # the remaining >=33 m/s tail has only five counter-days.
            data = data[data[variable].lt(33)]
        data = add_bin(data, variable, upper_bounds)
        categories = [
            str(value)
            for value in data["bin"].cat.categories
            if data["bin"].eq(value).any()
        ]
        data["bin"] = data["bin"].astype("string")
        counter_bins = data.groupby(["counter_site_id", "bin"], as_index=False).agg(
            counter_median_traffic_index=("traffic_index", "median"),
            counter_days=("date", "size"),
        )
        summary = counter_bins.groupby("bin", as_index=False).agg(
            traffic_index_median=("counter_median_traffic_index", "median"),
            traffic_index_mean=("counter_median_traffic_index", "mean"),
            counters=("counter_site_id", "nunique"),
            counter_days=("counter_days", "sum"),
        )
        nonzero_counter_bins = (
            data[data["traffic_volume"].gt(0)]
            .groupby(["counter_site_id", "bin"], as_index=False)
            .agg(nonzero_counter_median_traffic_index=("traffic_index", "median"))
        )
        nonzero_summary = nonzero_counter_bins.groupby(
            "bin", as_index=False
        ).agg(
            traffic_index_median_excluding_zero=(
                "nonzero_counter_median_traffic_index",
                "median",
            )
        )
        zero_days = (
            data.assign(is_zero=data["traffic_volume"].eq(0))
            .groupby("bin", as_index=False)
            .agg(zero_counter_days=("is_zero", "sum"))
        )
        summary = summary.merge(nonzero_summary, on="bin", how="left").merge(
            zero_days, on="bin", how="left"
        )
        summary = pd.DataFrame({"bin": categories}).merge(
            summary, on="bin", how="left"
        )
        intervals = cluster_bootstrap_counter_medians(
            counter_bins, categories, replicates
        )
        summary = summary.merge(intervals, on="bin", how="left")
        summary["variable"] = variable
        summary["bin_order"] = np.arange(len(summary))
        frames.append(summary)
    return pd.concat(frames, ignore_index=True)


def build_adu_validation(
    daily: pd.DataFrame, annual_path: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare observed counter-year means with exact road-section ADU."""
    annual = pd.read_csv(
        annual_path, usecols=["year", "road_section", "adu", "sdu", "vdu"]
    )
    annual["road_section"] = normalize_section(annual["road_section"])
    if annual.duplicated(["year", "road_section"]).any():
        raise ValueError("Annual traffic is not unique on year + road_section")

    counter_year = daily.groupby(
        ["counter_site_id", "year", "road_section"], as_index=False
    ).agg(
        observed_days=("date", "nunique"),
        observed_daily_mean=("traffic_volume", "mean"),
        observed_daily_median=("traffic_volume", "median"),
        observed_daily_sum=("traffic_volume", "sum"),
    )
    section_counts = counter_year.groupby(
        ["year", "road_section"], as_index=False
    ).agg(counters_on_section=("counter_site_id", "nunique"))
    result = counter_year.merge(
        section_counts, on=["year", "road_section"], how="left"
    ).merge(
        annual,
        on=["year", "road_section"],
        how="left",
        validate="many_to_one",
    )
    result["mean_to_adu_ratio"] = result["observed_daily_mean"] / result["adu"]
    result["median_to_adu_ratio"] = result["observed_daily_median"] / result["adu"]
    result["adu_available"] = result["adu"].notna()
    result["near_complete_year"] = result["observed_days"].ge(300)
    result["single_counter_section"] = result["counters_on_section"].eq(1)

    summaries = []
    scopes = {
        "all_exact_matches": result[result["adu_available"]],
        "at_least_300_days": result[
            result["adu_available"] & result["near_complete_year"]
        ],
        "at_least_300_days_single_counter_section": result[
            result["adu_available"]
            & result["near_complete_year"]
            & result["single_counter_section"]
        ],
    }
    for name, data in scopes.items():
        valid = data[
            data["adu"].gt(0) & data["observed_daily_mean"].gt(0)
        ]
        summaries.append(
            {
                "scope": name,
                "counter_years": len(valid),
                "counters": valid["counter_site_id"].nunique(),
                "road_sections": valid["road_section"].nunique(),
                "median_mean_to_adu_ratio": valid["mean_to_adu_ratio"].median(),
                "p10_mean_to_adu_ratio": valid["mean_to_adu_ratio"].quantile(0.10),
                "p90_mean_to_adu_ratio": valid["mean_to_adu_ratio"].quantile(0.90),
                "pearson_log_correlation": np.log(valid["adu"]).corr(
                    np.log(valid["observed_daily_mean"])
                ),
            }
        )
    return result, pd.DataFrame(summaries)
