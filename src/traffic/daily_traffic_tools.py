"""Shared functions for daily-counter weather matching and quality control.

The unit of observation is one counter on one date. This avoids summing
different counters located on the same road section. Weather is represented by
the nearest clean station to the counter location (official where available,
otherwise interpolated from the PDF road station). The 24-hour
daily traffic total is never divided into hourly values. It is paired with
daytime weather summaries (10:00-21:59), so this supports a day-level
supplementary analysis but cannot estimate traffic at each wind hour.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import chi2
from sklearn.neighbors import BallTree

from src.weather.frequency import FG_UPPER_BOUNDS, labels


DEFAULT_DAILY = Path(
    "data/processed/traffic/daily_traffic.parquet"
)
DEFAULT_ANNUAL = Path(
    "data/processed/traffic/annual_road_section_exposure.csv"
)
DEFAULT_MIDPOINTS = Path("data/raw/traffic/reference/road_section_midpoints.csv")
DEFAULT_STATIONS = Path("data/raw/weather/stations.csv")
DEFAULT_WEATHER = Path("data/processed/weather/weather_10min_clean.parquet")
DEFAULT_ACCIDENTS = Path("data/processed/accidents/rural_injury_accidents.parquet")
DEFAULT_WEATHER_CACHE = Path(
    "data/processed/traffic/daily_weather_cache.parquet"
)
DEFAULT_OUTPUT = Path("data/processed/traffic/daily_traffic_weather.parquet")
DEFAULT_SUMMARY = Path("reports/working/tables/daily_traffic_diagnostic.csv")
DEFAULT_COVERAGE = Path("archive/generated_diagnostics/daily_traffic_coverage.csv")
DEFAULT_ADU_VALIDATION = Path(
    "archive/generated_diagnostics/daily_traffic_adu_validation.csv"
)
DEFAULT_ADU_SUMMARY = Path(
    "archive/generated_diagnostics/daily_traffic_adu_summary.csv"
)
DEFAULT_ADU_FIGURE = Path("reports/working/traffic_validation.png")
DEFAULT_FIGURE = Path("reports/working/daily_traffic_diagnostic.png")
DEFAULT_ADJUSTMENT = Path(
    "archive/generated_diagnostics/daily_traffic_adjustment_comparison.csv"
)
DEFAULT_NOTES = Path("archive/generated_diagnostics/daily_traffic_notes.md")

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
    """Read the canonical counter-day file.

    Current files already contain one row per physical counter site and date.
    A compatibility branch still accepts the former direction/lane-channel
    layout and combines its ``fastnr`` rows.
    """
    header = (pd.read_parquet(path).columns if path.suffix == ".parquet" else pd.read_csv(path, nrows=0).columns)
    canonical = "counter_site_id" in header
    if canonical:
        raw = (pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, dtype={"source_fastnr": "string"}))
    else:
        raw = pd.read_csv(
            path,
            usecols=[
                "year",
                "fastnr",
                "station_id",
                "road_section",
                "site_name",
                "date",
                "traffic_volume",
            ],
        )
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

    if canonical:
        if raw.duplicated(["counter_site_id", "date"]).any():
            raise ValueError("Daily traffic is not unique on site + date")
        return raw

    raw["fastnr"] = pd.to_numeric(raw["fastnr"], errors="raise").astype(int)
    if raw.duplicated(["fastnr", "date"]).any():
        raise ValueError("Daily traffic is not unique on fastnr + date")
    keys = ["year", "road_section", "station_id", "date"]
    daily = raw.groupby(keys, as_index=False).agg(
        traffic_volume=("traffic_volume", "sum"),
        directional_channels=("fastnr", "nunique"),
        source_fastnr=(
            "fastnr",
            lambda values: "|".join(str(value) for value in sorted(set(values))),
        ),
        site_name=(
            "site_name",
            lambda values: " | ".join(sorted(set(values.dropna().astype(str)))),
        ),
    )
    daily["counter_site_id"] = (
        daily["road_section"].astype(str)
        + ":"
        + daily["station_id"].astype(str)
    )
    if daily.duplicated(["counter_site_id", "date"]).any():
        raise ValueError("Aggregated daily traffic is not unique on site + date")
    return daily


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

    ``location_lat`` and ``location_lon`` are official counter coordinates
    where a conservative link was possible. Otherwise they are the explicitly
    marked midpoint of the registered road section. This preserves nearly full
    counter coverage without pretending that estimated coordinates are exact.
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
    """Aggregate clean 10-minute weather to station-day, 10:00-21:59."""
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
            & (hour >= 10)
            & (hour < 22)
        )
        if not keep.any():
            continue
        f = table.column("f").to_numpy()[keep].astype(float)
        fg = table.column("fg").to_numpy()[keep].astype(float)
        selected = pd.DataFrame(
            {
                "weather_station_id": station[keep].astype(int),
                "date": timestamp[keep].astype("datetime64[D]"),
                "f_sum": f,
                "fg_sum": fg,
                "observation_count": 1,
            }
        )
        partials.append(
            selected.groupby(
                ["weather_station_id", "date"], as_index=False
            ).agg(
                f_sum=("f_sum", "sum"),
                fg_sum=("fg_sum", "sum"),
                observation_count=("observation_count", "sum"),
            )
        )

    if not partials:
        raise ValueError("No weather observations matched the requested scope")
    weather = pd.concat(partials, ignore_index=True)
    weather = weather.groupby(
        ["weather_station_id", "date"], as_index=False
    ).agg(
        f_sum=("f_sum", "sum"),
        fg_sum=("fg_sum", "sum"),
        observation_count=("observation_count", "sum"),
    )
    weather["f_daytime_mean"] = weather["f_sum"] / weather["observation_count"]
    weather["fg_daytime_mean"] = weather["fg_sum"] / weather["observation_count"]
    weather = weather.drop(columns=["f_sum", "fg_sum"])
    diagnostics = {
        "weather_row_groups_considered": total_groups,
        "weather_row_groups_scanned": scanned,
        "weather_row_groups_skipped_by_station": skipped,
    }
    return weather, diagnostics


def build_weather_cache(
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
    output["weather_match_method"] = (
        "nearest_valid_station_to_counter_or_midpoint_within_20km"
    )
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


def plot_wind_summary(summary: pd.DataFrame, path: Path) -> None:
    """Show the relative number of vehicles counted by daily mean wind.

    Absolute counter volumes cannot be pooled because counters represent roads
    with very different traffic levels. Each counter-day is therefore divided
    by the median for the same counter, year, month, and weekday. A value of 70
    means 30% fewer vehicles were counted than on a typical comparable day; it
    is not a national count of people or vehicles.
    """
    data = summary[summary["variable"].eq("f_daytime_mean")].sort_values(
        "bin_order"
    )
    x = np.arange(len(data))
    sparse = data["counters"].fillna(0).lt(20)
    colors = np.where(sparse, "#A8A8A8", "#287271")

    fig, axis = plt.subplots(figsize=(11.2, 6.6))
    bars = axis.bar(x, data["traffic_index_median"], color=colors, width=0.72)
    lower = data["traffic_index_median"] - data["ci_95_low"]
    upper = data["ci_95_high"] - data["traffic_index_median"]
    axis.errorbar(
        x,
        data["traffic_index_median"],
        yerr=[lower, upper],
        fmt="none",
        ecolor="#202020",
        capsize=3,
    )
    axis.axhline(100, color="#202020", linestyle="--", linewidth=1.2)
    axis.set_xticks(x, data["bin"], rotation=0, ha="center")
    axis.set_ylabel("Vehicles counted relative to a typical day (%)")
    axis.set_xlabel("Daytime mean wind speed, 10:00–21:59 (m/s)")
    axis.set_title("Daily traffic by mean wind speed")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    axis.set_ylim(0, max(112, float(data["ci_95_high"].max()) + 8))
    for bar, row in zip(bars, data.itertuples(index=False), strict=True):
        if pd.isna(row.traffic_index_median):
            continue
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            row.traffic_index_median + 1.5,
            f"n={row.counter_days:,}",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
    fig.subplots_adjust(left=0.10, right=0.98, top=0.92, bottom=0.24)
    fig.text(
        0.5,
        0.035,
        "Baseline: median for the same counter, year, month, and weekday. "
        "Bars show the median across counters; error bars are 95% counter-cluster bootstrap intervals.",
        ha="center",
        fontsize=8.5,
        color="#444444",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


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


def plot_adu_validation(validation: pd.DataFrame, path: Path) -> None:
    data = validation[
        validation["adu"].gt(0)
        & validation["observed_daily_mean"].gt(0)
        & validation["near_complete_year"]
        & validation["single_counter_section"]
    ].copy()
    fig, axis = plt.subplots(figsize=(9, 7.5), constrained_layout=True)
    axis.scatter(
        data["adu"],
        data["observed_daily_mean"],
        color="#287271",
        alpha=0.55,
        s=24,
    )
    low = min(data["adu"].min(), data["observed_daily_mean"].min())
    high = max(data["adu"].max(), data["observed_daily_mean"].max())
    axis.plot([low, high], [low, high], color="#202020", linestyle="--", linewidth=1)
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("Annual average daily traffic, ADU")
    axis.set_ylabel("Mean observed daily PDF traffic")
    axis.set_title("Daily traffic compared with official ADU")
    axis.grid(alpha=0.2)
    median_ratio = data["mean_to_adu_ratio"].median()
    log_correlation = np.log(data["adu"]).corr(
        np.log(data["observed_daily_mean"])
    )
    axis.text(
        0.02,
        0.98,
        f"At least 300 observed days; one counter per road section\n"
        f"n = {len(data):,} counter-years\n"
        f"Median observed / ADU = {median_ratio:.3f}\n"
        f"Log correlation = {log_correlation:.3f}\n"
        "Dashed line: equal values",
        transform=axis.transAxes,
        va="top",
        fontsize=10,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def build_adjustment_comparison(
    panel: pd.DataFrame, accidents_path: Path
) -> pd.DataFrame:
    """Compare day-frequency and observed-traffic accident denominators."""
    section_day = panel.groupby(
        ["road_section", "date"], as_index=False
    ).agg(
        traffic_volume=("traffic_volume", "median"),
        f_daytime_mean=("f_daytime_mean", "first"),
        fg_daytime_mean=("fg_daytime_mean", "first"),
        counters=("counter_site_id", "nunique"),
    )
    accidents = pd.read_parquet(
        accidents_path,
        columns=["nid", "date", "registered_road_section"],
    )
    accidents["date"] = pd.to_datetime(accidents["date"])
    accidents["road_section"] = normalize_section(
        accidents["registered_road_section"]
    )
    accident_counts = accidents.groupby(
        ["road_section", "date"], as_index=False
    ).agg(observed_accidents=("nid", "nunique"))
    section_day = section_day.merge(
        accident_counts,
        on=["road_section", "date"],
        how="left",
        validate="one_to_one",
    )
    section_day["observed_accidents"] = section_day[
        "observed_accidents"
    ].fillna(0)
    section_day["year"] = section_day["date"].dt.year
    section_day["month"] = section_day["date"].dt.month

    frames = []
    for variable, bounds in [
        ("f_daytime_mean", DAILY_F_UPPER_BOUNDS),
        ("fg_daytime_mean", FG_UPPER_BOUNDS),
    ]:
        data = section_day.dropna(
            subset=[variable, "traffic_volume"]
        ).copy()
        if variable == "f_daytime_mean":
            data = data[data[variable].lt(33)]
        data = add_bin(data, variable, bounds)
        categories = [str(value) for value in data["bin"].cat.categories]
        data["bin"] = data["bin"].astype("string")
        strata = ["road_section", "year", "month"]
        totals = data.groupby(strata, as_index=False).agg(
            stratum_accidents=("observed_accidents", "sum"),
            stratum_days=("date", "size"),
            stratum_traffic=("traffic_volume", "sum"),
        )
        data = data.merge(totals, on=strata, how="left", validate="many_to_one")
        data["expected_by_days"] = (
            data["stratum_accidents"] / data["stratum_days"]
        )
        data["expected_by_traffic"] = np.where(
            data["stratum_traffic"].gt(0),
            data["stratum_accidents"]
            * data["traffic_volume"]
            / data["stratum_traffic"],
            np.nan,
        )
        result = data.groupby("bin", as_index=False).agg(
            observed_accidents=("observed_accidents", "sum"),
            expected_by_days=("expected_by_days", "sum"),
            expected_by_traffic=("expected_by_traffic", "sum"),
            road_section_days=("date", "size"),
            observed_traffic=("traffic_volume", "sum"),
            road_sections=("road_section", "nunique"),
        )
        result = pd.DataFrame({"bin": categories}).merge(
            result, on="bin", how="left"
        )
        result["ratio_without_daily_traffic"] = (
            result["observed_accidents"] / result["expected_by_days"]
        )
        result["ratio_with_daily_traffic"] = (
            result["observed_accidents"] / result["expected_by_traffic"]
        )
        count = result["observed_accidents"].fillna(0).to_numpy(dtype=float)
        count_low = np.where(
            count > 0, 0.5 * chi2.ppf(0.025, 2 * count), 0.0
        )
        count_high = 0.5 * chi2.ppf(0.975, 2 * (count + 1))
        for suffix, expected in (
            ("without_daily_traffic", result["expected_by_days"]),
            ("with_daily_traffic", result["expected_by_traffic"]),
        ):
            result[f"ci_95_low_{suffix}"] = count_low / expected
            result[f"ci_95_high_{suffix}"] = count_high / expected
        result["variable"] = variable
        result["bin_order"] = np.arange(len(result))
        frames.append(result)
    return pd.concat(frames, ignore_index=True)


def plot_adjustment_comparison(result: pd.DataFrame, path: Path) -> None:
    data = result[result["variable"].eq("fg_daytime_mean")].sort_values(
        "bin_order"
    )
    x = np.arange(len(data))
    width = 0.38
    fig, axis = plt.subplots(figsize=(13, 7.5), constrained_layout=True)
    bars_without = axis.bar(
        x - width / 2,
        data["ratio_without_daily_traffic"],
        width,
        label="Adjusted for observed section-days",
        color="#287271",
    )
    bars_with = axis.bar(
        x + width / 2,
        data["ratio_with_daily_traffic"],
        width,
        label="Adjusted for observed daily traffic",
        color="#C7522A",
    )
    for positions, ratio, suffix in (
        (x - width / 2, data["ratio_without_daily_traffic"], "without_daily_traffic"),
        (x + width / 2, data["ratio_with_daily_traffic"], "with_daily_traffic"),
    ):
        lower = ratio - data[f"ci_95_low_{suffix}"]
        upper = data[f"ci_95_high_{suffix}"] - ratio
        axis.errorbar(
            positions,
            ratio,
            yerr=[lower, upper],
            fmt="none",
            ecolor="#202020",
            capsize=2,
            linewidth=0.8,
        )
    for position, count, first, second in zip(
        x,
        data["observed_accidents"],
        bars_without,
        bars_with,
        strict=True,
    ):
        axis.text(
            position,
            max(first.get_height(), second.get_height()) + 0.05,
            f"n={int(count)}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    axis.axhline(1, color="#202020", linestyle="--", linewidth=1)
    axis.set_xticks(x, data["bin"], rotation=35, ha="right")
    axis.set_xlabel("Maximum daytime wind-gust interval, fg (m/s; 10:00–21:59)")
    axis.set_ylabel("Observed / expected injury accidents (O/E ratio)")
    represented_accidents = int(data["observed_accidents"].sum())
    axis.set_title(
        "Daily accident comparison with and without traffic exposure\n"
        f"Exact Poisson 95% intervals; same {represented_accidents:,} accidents in both estimates"
    )
    axis.legend(frameon=False)
    axis.grid(axis="y", alpha=0.2)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def write_notes(
    path: Path,
    daily: pd.DataFrame,
    panel: pd.DataFrame,
    coverage: pd.DataFrame,
    adu_summary: pd.DataFrame,
    adjustment: pd.DataFrame,
    elapsed: float,
) -> None:
    high_f = panel[panel["f_daytime_mean"].ge(20)]["traffic_index"].median()
    high_fg = panel[panel["fg_daytime_mean"].ge(30)]["traffic_index"].median()
    represented = int(
        adjustment.loc[
            adjustment["variable"].eq("fg_daytime_mean"), "observed_accidents"
        ].sum()
    )
    adu_table = adu_summary.to_string(index=False)
    coverage_table = coverage.to_string(index=False)
    text = f"""# Daily Traffic Validation

## Scope

- Counter-day rows: {len(daily):,}
- Unique counter sites after summing directional channels: {daily['counter_site_id'].nunique():,}
- Road sections: {daily['road_section'].nunique():,}
- Counter-days with usable weather: {panel['f_daytime_mean'].notna().sum():,}
- Counter-days recorded as zero vehicles: {daily['traffic_volume'].eq(0).sum():,}
- Median traffic index when daytime mean wind is at least 20 m/s: {high_f:.1f}
- Median traffic index when daytime maximum gust is at least 30 m/s: {high_fg:.1f}
- Accidents represented in the daily comparison: {represented:,}
- Runtime: {elapsed:.1f} seconds

The traffic index is 100 times observed vehicle count divided by the median for
the same counter, year, month, and weekday. Thus 70 means 30% fewer vehicles
were counted than on a typical comparable day. It is not a count of people or
national traffic. The uncertainty intervals resample whole counters, and each
counter has equal weight in the plotted median.

## ADU comparison

```text
{adu_table}
```

Agreement with ADU is a consistency check, not independent validation. ADU can
be estimated partly from the same permanent counters, and the PDF counter can
cover only one location or direction within a road section.

## Correct use

Daily counts are useful for testing whether travel demand falls during windy
days and for a restricted daily accident-exposure comparison. ADU,
SDU, and VDU remain preferable for complete road-section context and annual or
seasonal vehicle-kilometres. Daily counts should not be inserted directly into
the primary 10-minute accident-time curve because daily maximum wind, counter
coverage, and accident-time wind have different units and coverage.

## Limitations

- Official counter coordinates are used when a conservative link is available.
  Otherwise weather is assigned from the explicitly marked road-section
  midpoint; three counter sites have no usable location.
- A zero can represent no traffic, a road closure, or a counter fault. Zero
  days are retained in the main behavioural description and must be checked in
  a zero-excluded comparison before making a causal interpretation.
- Several counters can occur on one road section. Counter-day analyses retain
  counters separately; the accident comparison uses the median across counters
  on a section-day rather than summing them.
- Calendar normalization controls counter, year, month, and weekday but not
  holidays, road closures, precipitation, visibility, or other storm effects.
- The daily accident comparison is not the primary 10-minute risk curve and
  should be labelled as a supplementary analysis.

## Coverage

```text
{coverage_table}
```
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate daily traffic against ADU and analyse traffic by wind."
    )
    parser.add_argument("-d", "--daily", type=Path, default=DEFAULT_DAILY)
    parser.add_argument("-a", "--annual", type=Path, default=DEFAULT_ANNUAL)
    parser.add_argument("-m", "--midpoints", type=Path, default=DEFAULT_MIDPOINTS)
    parser.add_argument("-s", "--stations", type=Path, default=DEFAULT_STATIONS)
    parser.add_argument("-w", "--weather", type=Path, default=DEFAULT_WEATHER)
    parser.add_argument("-A", "--accidents", type=Path, default=DEFAULT_ACCIDENTS)
    parser.add_argument("-W", "--weather-cache", type=Path, default=DEFAULT_WEATHER_CACHE)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-S", "--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("-c", "--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("-v", "--adu-validation", type=Path, default=DEFAULT_ADU_VALIDATION)
    parser.add_argument("-u", "--adu-summary", type=Path, default=DEFAULT_ADU_SUMMARY)
    parser.add_argument("-F", "--adu-figure", type=Path, default=DEFAULT_ADU_FIGURE)
    parser.add_argument("-f", "--figure", type=Path, default=DEFAULT_FIGURE)
    parser.add_argument("-j", "--adjustment", type=Path, default=DEFAULT_ADJUSTMENT)
    parser.add_argument("-n", "--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("-y", "--start-year", type=int, default=2019)
    parser.add_argument("-Y", "--end-year", type=int, default=2024)
    parser.add_argument("-b", "--bootstrap-replicates", type=int, default=1000)
    parser.add_argument("-g", "--max-row-groups", type=int)
    parser.add_argument("-r", "--rebuild-weather-cache", action="store_true")
    parser.add_argument("-p", "--plot-only", action="store_true")
    args = parser.parse_args()

    if args.plot_only:
        plot_wind_summary(pd.read_csv(args.summary), args.figure)
        plot_adu_validation(pd.read_csv(args.adu_validation), args.adu_figure)
        print("redrew daily traffic figures")
        return

    started = time.perf_counter()
    daily = read_daily(args.daily, args.start_year, args.end_year)
    diagnostics: dict[str, int] = {}
    cache_usable = args.weather_cache.exists() and not args.rebuild_weather_cache
    if cache_usable:
        weather = pd.read_parquet(args.weather_cache)
        weather["date"] = pd.to_datetime(weather["date"])
        cache_usable = (
            "weather_match_method" in weather.columns
            and weather["weather_match_method"].eq(
                "nearest_valid_station_to_counter_or_midpoint_within_20km"
            ).all()
            and "counter_site_id" in weather.columns
            and weather["date"].dt.year.min() <= args.start_year
            and weather["date"].dt.year.max() >= args.end_year
        )
    if not cache_usable:
        weather, diagnostics = build_weather_cache(
            args.weather,
            daily,
            args.stations,
            args.start_year,
            args.end_year,
            args.max_row_groups,
        )
        if args.max_row_groups is None:
            args.weather_cache.parent.mkdir(parents=True, exist_ok=True)
            weather.to_parquet(args.weather_cache, index=False, compression="zstd")
    weather = weather[
        weather["date"].dt.year.between(args.start_year, args.end_year)
    ].copy()
    excluded_station = weather["weather_station_id"].isin(
        DAILY_WIND_EXCLUDED_STATION_IDS
    )
    diagnostics["counter_days_excluded_station_7475"] = int(excluded_station.sum())
    weather = weather.loc[~excluded_station].copy()
    mapped_counters = set(weather["counter_site_id"].dropna().astype(str))
    panel = daily.merge(
        weather,
        on=["counter_site_id", "road_section", "date"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_weather"),
    )
    panel = add_normalized_traffic(panel)
    panel["has_counter_location_weather_match"] = panel[
        "counter_site_id"
    ].isin(mapped_counters)

    summary = build_wind_summary(panel, args.bootstrap_replicates)
    validation, adu_summary = build_adu_validation(daily, args.annual)
    adjustment = build_adjustment_comparison(panel, args.accidents)
    coverage = pd.DataFrame(
        [
            {
                "counter_days": len(panel),
                "counters": panel["counter_site_id"].nunique(),
                "road_sections": panel["road_section"].nunique(),
                "counter_days_with_location": int(
                    panel["location_lat"].notna().sum()
                ),
                "counter_days_with_official_location": int(
                    (
                        (~panel["location_is_estimated"])
                        & panel["location_lat"].notna()
                    ).sum()
                ),
                "counter_days_with_weather_station_match": int(
                    panel["has_counter_location_weather_match"].sum()
                ),
                "counter_days_with_daytime_wind": int(
                    panel["f_daytime_mean"].notna().sum()
                ),
                "wind_coverage_pct": 100 * panel["f_daytime_mean"].notna().mean(),
                "counter_years_with_exact_adu": int(
                    validation["adu_available"].sum()
                ),
                "counter_years_total": len(validation),
                **diagnostics,
            }
        ]
    )

    for path in [
        args.output,
        args.summary,
        args.coverage,
        args.adu_validation,
        args.adu_summary,
        args.adu_figure,
        args.figure,
        args.adjustment,
        args.notes,
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.output, index=False, compression="zstd")
    summary.to_csv(args.summary, index=False)
    coverage.to_csv(args.coverage, index=False)
    validation.to_csv(args.adu_validation, index=False)
    adu_summary.to_csv(args.adu_summary, index=False)
    adjustment.to_csv(args.adjustment, index=False)
    plot_wind_summary(summary, args.figure)
    plot_adu_validation(validation, args.adu_figure)
    # Retain the audit table, but do not promote the daily O/E comparison to a
    # figure: its daily wind definition is too easy to confuse with the primary
    # accident-time O/E analysis.
    elapsed = time.perf_counter() - started
    write_notes(
        args.notes, daily, panel, coverage, adu_summary, adjustment, elapsed
    )
    print(coverage.to_string(index=False))
    print(adu_summary.to_string(index=False))
    print(f"runtime_seconds={elapsed:.1f}")


if __name__ == "__main__":
    main()
