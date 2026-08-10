"""Extract and standardize daily traffic counts from Vegagerdin PDF files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import unicodedata
import zlib

import numpy as np
import pandas as pd
from pyproj import Transformer

PDF_CANDIDATES = {
    2019: [
        Path("data/raw/traffic/daily_pdf/r_cross_umferd_2019.pdf"),
        Path("/Users/asgeirmagnusson/Desktop/r_cross_umferd_2019.pdf"),
    ],
    2020: [
        Path("data/raw/traffic/daily_pdf/r_cross_umferd_2020_fastir.pdf"),
        Path("/Users/asgeirmagnusson/Desktop/r_cross_umferd_2020_fastir.pdf"),
    ],
    2021: [
        Path("data/raw/traffic/daily_pdf/r_cross_umferd_2021_fastir.pdf"),
        Path("/Users/asgeirmagnusson/Desktop/r_cross_umferd_2021_fastir.pdf"),
    ],
    2022: [
        Path("data/raw/traffic/daily_pdf/r_cross_umferd_2022_fastir-1.pdf"),
        Path("/Users/asgeirmagnusson/Desktop/r_cross_umferd_2022_fastir-1.pdf"),
    ],
    2023: [
        Path("data/raw/traffic/daily_pdf/r_cross_umferd_2023_fastir.pdf"),
        Path("/Users/asgeirmagnusson/Desktop/r_cross_umferd_2023_fastir.pdf"),
    ],
    2024: [
        Path("data/raw/traffic/daily_pdf/r_cross_umferd_2024_fastir.pdf"),
        Path("/Users/asgeirmagnusson/Desktop/r_cross_umferd_2024_fastir.pdf"),
    ],
}

OUT_LONG_2024 = Path("archive/generated_diagnostics/traffic_pdf_2024_daily_long.csv")
OUT_TOTAL_2024 = Path("archive/generated_diagnostics/traffic_pdf_2024_daily_total.csv")
OUT_REPEAT_2024 = Path("archive/generated_diagnostics/traffic_pdf_2024_repeated_2007_2024.csv")
OUT_META_2024 = Path("archive/generated_diagnostics/traffic_pdf_2024_counter_metadata.csv")
OUT_NOTES_2024 = Path("archive/generated_diagnostics/traffic_pdf_2024_notes.txt")

OUT_CHANNEL_MULTI = Path(
    "archive/generated_diagnostics/daily_traffic_channels_2019_2024.csv"
)
OUT_COUNTS = Path("data/processed/traffic/daily_counts.parquet")
OUT_LOCATIONS = Path("data/processed/traffic/daily_locations.csv")
OUT_LONG_MULTI = Path("data/processed/traffic/daily_traffic.parquet")
OUT_TOTAL_MULTI = Path("archive/generated_diagnostics/daily_traffic_total_2019_2024.csv")
OUT_META_MULTI = Path("archive/generated_diagnostics/daily_counter_metadata_2019_2024.csv")
OUT_NOTES_MULTI = Path("archive/generated_diagnostics/traffic_pdf_2019_2024_notes.txt")
OUT_STATION_VALIDATION = Path(
    "archive/generated_diagnostics/daily_traffic_station_location_validation.csv"
)
COUNTER_LOCATIONS = Path("data/raw/traffic/reference/counter_locations.csv")
SECTION_MIDPOINTS = Path("data/raw/traffic/reference/road_section_midpoints.csv")
SECTION_GEOMETRIES = Path(
    "data/raw/traffic/reference/road_section_geometries.csv"
)
ANNUAL_TRAFFIC = Path("data/processed/traffic/annual_road_section_exposure.csv")

MONTH_VALUE_CENTERS = [134, 187, 235, 287, 339, 392, 444, 496, 549, 601, 653, 710]
MONTHS = list(range(1, 13))


@dataclass(frozen=True)
class TextItem:
    x: float
    y: float
    text: str


def pdf_unescape(value: str) -> str:
    out: list[str] = []
    i = 0
    escape_map = {
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "b": "\b",
        "f": "\f",
        "(": "(",
        ")": ")",
        "\\": "\\",
    }
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            out.append(escape_map.get(value[i + 1], value[i + 1]))
            i += 2
        else:
            out.append(value[i])
            i += 1
    return "".join(out)


def resolve_pdf(year: int) -> Path | None:
    for path in PDF_CANDIDATES[year]:
        if path.exists():
            return path
    return None


def iter_page_streams(path: Path) -> list[str]:
    data = path.read_bytes()
    streams: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            text = zlib.decompress(match.group(1)).decode("latin1", errors="ignore")
        except Exception:
            continue
        if "Umfe" in text and "TJ" in text:
            streams.append(text)
    return streams


def extract_text_items(stream: str) -> list[TextItem]:
    items: list[TextItem] = []
    for block_match in re.finditer(r"BT(.*?)ET", stream, re.S):
        block = block_match.group(1)
        tm = re.search(r"1 0 0 1 ([0-9.\-]+) ([0-9.\-]+) Tm", block)
        if not tm:
            continue

        parts: list[str] = []
        for arr in re.finditer(r"\[(.*?)\]\s*TJ", block, re.S):
            parts.extend(pdf_unescape(s.group(1)) for s in re.finditer(r"\((.*?)\)", arr.group(1), re.S))
        parts.extend(pdf_unescape(s.group(1)) for s in re.finditer(r"\((.*?)\)\s*Tj", block, re.S))

        text = "".join(parts).strip()
        if text:
            items.append(TextItem(float(tm.group(1)), float(tm.group(2)), text))
    return items


def parse_metadata(items: list[TextItem], page_number: int, year: int, source: Path) -> dict[str, object]:
    fastnr = ""
    station_id = ""
    road_section = ""
    site_name = ""

    for item in items:
        if "fastnr" in item.text:
            m = re.search(r"fastnr\.\s*(\d+)\s+stöð\s+(\d+)", item.text)
            if m:
                fastnr, station_id = m.group(1), m.group(2)
        if item.y > 500 and re.fullmatch(r"\d+[a-z]?-[0-9a-z]+", item.text):
            road_section = item.text
        if item.x > 300 and item.y > 500 and "Umferð" not in item.text:
            site_name = item.text

    return {
        "year": year,
        "pdf_source": str(source),
        "pdf_page": page_number,
        "fastnr": fastnr,
        "station_id": station_id,
        "road_section": road_section,
        "site_name": site_name,
    }


def nearest_month(x: float) -> int | None:
    idx = min(range(12), key=lambda i: abs(x - MONTH_VALUE_CENTERS[i]))
    if abs(x - MONTH_VALUE_CENTERS[idx]) > 22:
        return None
    return MONTHS[idx]


def parse_page(stream: str, page_number: int, year: int, source: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    items = extract_text_items(stream)
    metadata = parse_metadata(items, page_number, year, source)
    rows: list[dict[str, object]] = []

    day_items = [
        item
        for item in items
        if 70 < item.x < 100 and 30 < item.y < 460 and re.fullmatch(r"\d{2}", item.text)
    ]

    for day_item in day_items:
        day = int(day_item.text)
        if not 1 <= day <= 31:
            continue
        same_row = [item for item in items if abs(item.y - day_item.y) < 0.4]
        for item in same_row:
            if item.x < 105 or item.x > 735:
                continue
            if not re.fullmatch(r"\d+", item.text):
                continue
            month = nearest_month(item.x)
            if month is None:
                continue
            try:
                traffic_date = date(year, month, day)
            except ValueError:
                continue
            rows.append(
                {
                    **metadata,
                    "date": traffic_date.isoformat(),
                    "month": traffic_date.month,
                    "day": traffic_date.day,
                    "traffic_volume": int(item.text),
                }
            )

    return pd.DataFrame(rows), metadata


def parse_year(year: int, path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    page_streams = iter_page_streams(path)
    if not page_streams:
        raise SystemExit(f"No readable table pages found in {path}")

    frames: list[pd.DataFrame] = []
    metadata_rows: list[dict[str, object]] = []
    for page_number, stream in enumerate(page_streams, start=1):
        page_df, metadata = parse_page(stream, page_number, year, path)
        metadata_rows.append(metadata)
        if not page_df.empty:
            frames.append(page_df)

    long_df = pd.concat(frames, ignore_index=True)
    long_df = long_df.drop_duplicates(
        subset=["year", "fastnr", "station_id", "road_section", "date"],
        keep="last",
    )
    long_df = long_df.sort_values(["year", "station_id", "road_section", "date"])
    metadata_df = pd.DataFrame(metadata_rows).drop_duplicates(
        subset=["year", "fastnr", "station_id", "road_section"],
        keep="last",
    )

    summary = {
        "year": year,
        "input_pdf": str(path),
        "readable_pages": len(page_streams),
        "rows": len(long_df),
        "unique_station_ids": long_df["station_id"].nunique(),
        "unique_road_sections": long_df["road_section"].nunique(),
        "date_min": long_df["date"].min(),
        "date_max": long_df["date"].max(),
    }
    return long_df, metadata_df, summary


def build_daily_total(long_df: pd.DataFrame) -> pd.DataFrame:
    return (
        long_df.groupby("date", as_index=False)
        .agg(
            traffic_volume_total=("traffic_volume", "sum"),
            traffic_counters_observed=("fastnr", "nunique"),
            traffic_stations_observed=("station_id", "nunique"),
            traffic_volume_mean=("traffic_volume", "mean"),
        )
        .sort_values("date")
    )


def normalize_name(value: object) -> str:
    """Return a conservative, direction-neutral counter-place label."""
    text = unicodedata.normalize("NFKD", str(value)).encode(
        "ascii", "ignore"
    ).decode()
    text = text.lower().replace("hringvegur", " ")
    text = re.sub(
        r"\b(akrein|akr|til|fra|austurs|vesturs|nordurs|sudurs|haegri|vinstri|"
        r"reykjavikur|rvk|samanlogd|umferd|vegur|vedurstod)\b",
        " ",
        text,
    )
    return " ".join(re.findall(r"[a-z0-9]+", text))


def name_similarity(left: str, right: str) -> float:
    """Combine sequence similarity and token overlap."""
    sequence = SequenceMatcher(None, left, right).ratio()
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    union = left_tokens | right_tokens
    token_score = len(left_tokens & right_tokens) / len(union) if union else 0
    return 0.7 * sequence + 0.3 * token_score


def build_counter_days(channel_rows: pd.DataFrame) -> pd.DataFrame:
    """Combine direction/lane channels into one readable counter-site day."""
    data = channel_rows.copy()
    data["road_section"] = (
        data["road_section"].astype("string").str.strip().str.lower()
    )
    data["date"] = pd.to_datetime(data["date"])
    data["fastnr"] = pd.to_numeric(data["fastnr"], errors="raise").astype(int)
    data["station_id"] = pd.to_numeric(
        data["station_id"], errors="raise"
    ).astype(int)
    keys = ["year", "road_section", "station_id", "date"]
    daily = data.groupby(keys, as_index=False).agg(
        site_name=(
            "site_name",
            lambda values: " | ".join(sorted(set(values.dropna().astype(str)))),
        ),
        traffic_volume=("traffic_volume", "sum"),
        directional_channels=("fastnr", "nunique"),
        source_fastnr=(
            "fastnr",
            lambda values: "|".join(str(value) for value in sorted(set(values))),
        ),
    )
    daily["counter_site_id"] = (
        daily["road_section"].astype(str)
        + ":"
        + daily["station_id"].astype(str)
    )
    if daily.duplicated(["counter_site_id", "date"]).any():
        raise ValueError("Counter-day output is not unique on site and date")
    return daily


def load_station_ranges(annual_path: Path = ANNUAL_TRAFFIC) -> dict[tuple[int, str], tuple[float, float]]:
    """Return year-specific Bst/Est ranges from the annual traffic workbooks."""
    annual = pd.read_csv(
        annual_path,
        usecols=[
            "year",
            "road_section",
            "section_start_station_km",
            "section_end_station_km",
        ],
        low_memory=False,
    )
    annual["road_section"] = (
        annual["road_section"].astype("string").str.strip().str.lower()
    )
    annual["start_m"] = pd.to_numeric(
        annual["section_start_station_km"], errors="coerce"
    ) * 1000
    annual["end_m"] = pd.to_numeric(
        annual["section_end_station_km"], errors="coerce"
    ) * 1000
    annual = annual.dropna(subset=["year", "road_section", "start_m", "end_m"])
    annual = annual[annual["end_m"].gt(annual["start_m"])]
    annual = annual.drop_duplicates(["year", "road_section"], keep="last")
    return {
        (int(row.year), str(row.road_section)): (float(row.start_m), float(row.end_m))
        for row in annual.itertuples(index=False)
    }


def point_on_polyline(paths_json: str, fraction: float) -> tuple[float, float] | None:
    """Return a point at a fraction of an EPSG:3057 road polyline length."""
    paths = json.loads(paths_json)
    vertices = np.asarray(
        [point[:2] for path in paths for point in path], dtype=float
    )
    if len(vertices) < 2 or not 0 <= fraction <= 1:
        return None
    lengths = np.sqrt(np.square(np.diff(vertices, axis=0)).sum(axis=1))
    total = float(lengths.sum())
    if not total:
        return None
    target = fraction * total
    cumulative = np.r_[0.0, np.cumsum(lengths)]
    index = min(int(np.searchsorted(cumulative, target, side="right") - 1), len(lengths) - 1)
    segment_fraction = (target - cumulative[index]) / lengths[index] if lengths[index] else 0
    point = vertices[index] + segment_fraction * (vertices[index + 1] - vertices[index])
    return float(point[0]), float(point[1])


def station_interpolation(
    year: int,
    road_section: str,
    station_id: float,
    ranges: dict[tuple[int, str], tuple[float, float]],
    geometries: pd.DataFrame,
) -> dict[str, float] | None:
    """Interpolate a PDF road-station coordinate when its annual range is valid.

    Annual Bst/Est are expressed in kilometres; PDF `stöð` is expressed in
    metres. The interpolation is only accepted when the station lies inside
    the year-specific Bst/Est range and a road geometry is available.
    """
    bounds = ranges.get((int(year), str(road_section)))
    if bounds is None or road_section not in geometries.index:
        return None
    start_m, end_m = bounds
    if not start_m <= station_id <= end_m:
        return None
    fraction = (station_id - start_m) / (end_m - start_m)
    point = point_on_polyline(geometries.loc[road_section, "paths_json"], fraction)
    if point is None:
        return None
    return {
        "x": point[0],
        "y": point[1],
        "start_m": start_m,
        "end_m": end_m,
        "fraction": fraction,
    }


def add_counter_locations(
    daily: pd.DataFrame,
    counter_path: Path = COUNTER_LOCATIONS,
    midpoint_path: Path = SECTION_MIDPOINTS,
    geometry_path: Path = SECTION_GEOMETRIES,
    annual_path: Path = ANNUAL_TRAFFIC,
) -> pd.DataFrame:
    """Add trusted official coordinates or an explicitly marked midpoint."""
    sites = daily[
        ["year", "counter_site_id", "road_section", "station_id", "site_name"]
    ].drop_duplicates(["year", "counter_site_id"])
    station_ranges = load_station_ranges(annual_path)
    official = pd.read_csv(counter_path)
    official["road_section"] = (
        official["road_number"].astype("string").str.strip().str.lower()
        + "-"
        + official["road_section_code"].astype("string").str.strip().str.lower()
    )
    official["official_counter_name"] = (
        official["counter_name"].fillna("").astype(str)
    )
    official["normalized_name"] = official["official_counter_name"].map(
        normalize_name
    )
    midpoint = pd.read_csv(
        midpoint_path,
        usecols=[
            "road_section",
            "midpoint_x_3057",
            "midpoint_y_3057",
            "midpoint_lon",
            "midpoint_lat",
            "computed_path_length_m",
        ],
    ).drop_duplicates("road_section")
    midpoint["road_section"] = (
        midpoint["road_section"].astype("string").str.strip().str.lower()
    )
    midpoint = midpoint.set_index("road_section")
    geometries = pd.read_csv(
        geometry_path, usecols=["road_section", "paths_json"]
    ).drop_duplicates("road_section")
    geometries["road_section"] = (
        geometries["road_section"].astype("string").str.strip().str.lower()
    )
    geometries = geometries.set_index("road_section")
    to_wgs84 = Transformer.from_crs("EPSG:3057", "EPSG:4326", always_xy=True)

    rows: list[dict[str, object]] = []
    for site in sites.itertuples(index=False):
        candidates = official[
            official["road_section"].eq(site.road_section)
        ].copy()
        accepted = None
        method = ""
        score = np.nan
        margin = np.nan
        if not candidates.empty:
            site_label = normalize_name(site.site_name)
            candidates["score"] = candidates["normalized_name"].map(
                lambda label: name_similarity(site_label, label)
            )
            candidates = candidates.sort_values("score", ascending=False)
            best = candidates.iloc[0]
            second = (
                float(candidates.iloc[1]["score"]) if len(candidates) > 1 else 0
            )
            score = float(best["score"])
            margin = score - second
            if len(candidates) == 1:
                accepted = best
                method = "official_single_on_section"
            elif score >= 0.45 and margin >= 0.08:
                accepted = best
                method = "official_name_match"

        interpolated = station_interpolation(
            year=int(site.year),
            road_section=str(site.road_section),
            station_id=float(site.station_id),
            ranges=station_ranges,
            geometries=geometries,
        )

        # The PDF road station (stöð) is the site-specific location evidence.
        # Prefer its validated interpolation whenever Bst/Est and the registered
        # geometry support it. A lone current official counter on a road section
        # can represent a different historical location, so it must not displace
        # the PDF station merely because it is the only registry candidate.
        if interpolated is not None:
            x = interpolated["x"]
            y = interpolated["y"]
            lon, lat = to_wgs84.transform(x, y)
            official_name = None
            method = "station_interpolated_from_pdf_station"
            estimated = True
            # A station interpolation is more precise than a section midpoint,
            # but its historical coordinate error is not a known distance bound.
            max_along_road_m = np.nan
            max_straight_line_m = np.nan
            station_start_m = interpolated["start_m"]
            station_end_m = interpolated["end_m"]
            station_fraction = interpolated["fraction"]
            station_range_valid = True
        elif accepted is not None:
            x = float(accepted["x_3057"])
            y = float(accepted["y_3057"])
            lon, lat = to_wgs84.transform(x, y)
            official_name = accepted["official_counter_name"]
            estimated = False
            max_along_road_m = 0.0
            max_straight_line_m = 0.0
            station_start_m = interpolated["start_m"] if interpolated else np.nan
            station_end_m = interpolated["end_m"] if interpolated else np.nan
            station_fraction = interpolated["fraction"] if interpolated else np.nan
            station_range_valid = interpolated is not None
        elif site.road_section in midpoint.index:
            fallback = midpoint.loc[site.road_section]
            x = float(fallback["midpoint_x_3057"])
            y = float(fallback["midpoint_y_3057"])
            lon = float(fallback["midpoint_lon"])
            lat = float(fallback["midpoint_lat"])
            official_name = None
            method = (
                "section_midpoint_ambiguous_official_counters"
                if not candidates.empty
                else "section_midpoint_no_official_counter"
            )
            estimated = True
            max_along_road_m = float(fallback["computed_path_length_m"]) / 2
            max_straight_line_m = np.nan
            if site.road_section in geometries.index:
                paths = json.loads(
                    geometries.loc[site.road_section, "paths_json"]
                )
                vertices = np.asarray(
                    [point[:2] for path in paths for point in path],
                    dtype=float,
                )
                if len(vertices):
                    offsets = vertices - np.array([x, y], dtype=float)
                    max_straight_line_m = float(
                        np.sqrt(np.square(offsets).sum(axis=1)).max()
                    )
            station_start_m = np.nan
            station_end_m = np.nan
            station_fraction = np.nan
            station_range_valid = False
        else:
            x = y = lon = lat = np.nan
            official_name = None
            method = "location_unavailable"
            estimated = True
            max_along_road_m = np.nan
            max_straight_line_m = np.nan
            station_start_m = np.nan
            station_end_m = np.nan
            station_fraction = np.nan
            station_range_valid = False

        rows.append(
            {
                "year": site.year,
                "counter_site_id": site.counter_site_id,
                "location_x_3057": x,
                "location_y_3057": y,
                "location_lon": lon,
                "location_lat": lat,
                "location_method": method,
                "location_is_estimated": estimated,
                "location_max_offset_along_road_km": max_along_road_m / 1000,
                "location_max_offset_straight_line_m": max_straight_line_m,
                "location_station_range_valid": station_range_valid,
                "location_station_start_m": station_start_m,
                "location_station_end_m": station_end_m,
                "location_station_fraction": station_fraction,
                "official_counter_name": official_name,
                "counter_name_score": score,
                "counter_name_margin": margin,
            }
        )
    locations = pd.DataFrame(rows)
    output = daily.merge(
        locations,
        on=["year", "counter_site_id"],
        how="left",
        validate="many_to_one",
    )
    columns = [
        "date",
        "year",
        "counter_site_id",
        "station_id",
        "road_section",
        "site_name",
        "traffic_volume",
        "directional_channels",
        "source_fastnr",
        "location_x_3057",
        "location_y_3057",
        "location_lon",
        "location_lat",
        "location_method",
        "location_is_estimated",
        "location_max_offset_along_road_km",
        "location_max_offset_straight_line_m",
        "location_station_range_valid",
        "location_station_start_m",
        "location_station_end_m",
        "location_station_fraction",
        "official_counter_name",
        "counter_name_score",
        "counter_name_margin",
    ]
    return output[columns].sort_values(["counter_site_id", "date"])


def write_station_interpolation_validation(
    counter_days: pd.DataFrame,
    geometry_path: Path = SECTION_GEOMETRIES,
    annual_path: Path = ANNUAL_TRAFFIC,
) -> pd.DataFrame:
    """Validate station interpolation against independently assigned official points."""
    geometries = pd.read_csv(
        geometry_path, usecols=["road_section", "paths_json"]
    ).drop_duplicates("road_section")
    geometries["road_section"] = (
        geometries["road_section"].astype("string").str.strip().str.lower()
    )
    geometries = geometries.set_index("road_section")
    ranges = load_station_ranges(annual_path)
    sites = counter_days[
        [
            "year",
            "counter_site_id",
            "road_section",
            "station_id",
            "location_x_3057",
            "location_y_3057",
            "location_method",
            "counter_name_score",
            "counter_name_margin",
        ]
    ].drop_duplicates(["year", "counter_site_id"])
    # A name match identifies the physical counter independently of its road
    # section. Keep this validation set even though the operational hierarchy
    # now prefers the PDF road station. A lone current counter on a section can
    # be a different historical counter, so it is not a clean reference.
    sites = sites[
        sites["counter_name_score"].ge(0.45)
        & sites["counter_name_margin"].ge(0.08)
    ]
    rows: list[dict[str, object]] = []
    for site in sites.itertuples(index=False):
        candidate = station_interpolation(
            year=int(site.year),
            road_section=str(site.road_section),
            station_id=float(site.station_id),
            ranges=ranges,
            geometries=geometries,
        )
        if candidate is None:
            continue
        error_m = float(
            np.hypot(
                candidate["x"] - float(site.location_x_3057),
                candidate["y"] - float(site.location_y_3057),
            )
        )
        rows.append(
            {
                "year": int(site.year),
                "counter_site_id": site.counter_site_id,
                "road_section": site.road_section,
                "station_id_m": float(site.station_id),
                "official_match_method": site.location_method,
                "station_interpolation_error_m": error_m,
                "station_start_m": candidate["start_m"],
                "station_end_m": candidate["end_m"],
                "station_fraction": candidate["fraction"],
            }
        )
    validation = pd.DataFrame(rows)
    if not validation.empty:
        validation = validation.sort_values(
            ["station_interpolation_error_m", "counter_site_id"]
        )
    OUT_STATION_VALIDATION.parent.mkdir(parents=True, exist_ok=True)
    validation.to_csv(OUT_STATION_VALIDATION, index=False)
    return validation


def build_repeated_pattern(total_2024: pd.DataFrame, start_year: int = 2007, end_year: int = 2024) -> pd.DataFrame:
    base = total_2024.copy()
    base["date"] = pd.to_datetime(base["date"])
    base["month"] = base["date"].dt.month
    base["day"] = base["date"].dt.day

    frames: list[pd.DataFrame] = []
    for year in range(start_year, end_year + 1):
        tmp = base.copy()
        repeated_dates = []
        keep = []
        for _, row in tmp.iterrows():
            try:
                repeated_dates.append(date(year, int(row["month"]), int(row["day"])).isoformat())
                keep.append(True)
            except ValueError:
                repeated_dates.append("")
                keep.append(False)
        tmp["date"] = repeated_dates
        tmp = tmp[keep].copy()
        tmp["year"] = year
        tmp["exposure_pattern_year"] = 2024
        frames.append(tmp.drop(columns=["month", "day"]))
    return pd.concat(frames, ignore_index=True).sort_values("date")


def write_2024_compatibility_outputs(long_df: pd.DataFrame, meta_df: pd.DataFrame, summaries: list[dict[str, object]]) -> None:
    long_2024 = long_df[long_df["year"] == 2024].copy()
    if long_2024.empty:
        return

    long_2024.to_csv(OUT_LONG_2024, index=False)
    meta_2024 = meta_df[meta_df["year"] == 2024].copy()
    meta_2024.to_csv(OUT_META_2024, index=False)

    total_2024 = build_daily_total(long_2024)
    total_2024.to_csv(OUT_TOTAL_2024, index=False)

    repeated = build_repeated_pattern(total_2024)
    repeated.to_csv(OUT_REPEAT_2024, index=False)

    summary = next(s for s in summaries if s["year"] == 2024)
    notes = [
        "Vegagerdin PDF 2024 Traffic Exposure Parse Notes",
        "================================================",
        f"Input PDF: {summary['input_pdf']}",
        f"Readable table pages: {summary['readable_pages']:,}",
        f"Counter-level daily rows parsed: {len(long_2024):,}",
        f"Unique station IDs: {long_2024['station_id'].nunique():,}",
        f"Unique road sections: {long_2024['road_section'].nunique():,}",
        f"Date range: {long_2024['date'].min()} to {long_2024['date'].max()}",
        f"Daily-total rows: {len(total_2024):,}",
        f"Repeated-pattern rows, 2007-2024: {len(repeated):,}",
        "",
        "Important limitation:",
        "The repeated-pattern file assumes the 2024 day/month traffic pattern applies to every year.",
        "It is retained for backward-compatible sensitivity checks, not as observed historical exposure.",
        "",
        f"Output long file: {OUT_LONG_2024}",
        f"Output daily-total file: {OUT_TOTAL_2024}",
        f"Output repeated-pattern file: {OUT_REPEAT_2024}",
        f"Output metadata file: {OUT_META_2024}",
    ]
    OUT_NOTES_2024.write_text("\n".join(notes) + "\n", encoding="utf-8")


def rebuild_locations_only() -> None:
    """Reapply the documented location hierarchy without parsing PDFs again."""
    if not OUT_COUNTS.exists():
        raise FileNotFoundError(f"Missing canonical daily counts: {OUT_COUNTS}")
    counter_days = add_counter_locations(pd.read_parquet(OUT_COUNTS))
    count_columns = [
        "date", "year", "counter_site_id", "station_id", "road_section", "site_name",
        "traffic_volume", "directional_channels", "source_fastnr",
    ]
    location_columns = [column for column in counter_days.columns if column not in count_columns]
    counter_days[["year", "counter_site_id", *location_columns]].drop_duplicates(
        ["year", "counter_site_id"]
    ).to_csv(OUT_LOCATIONS, index=False)
    counter_days.to_parquet(OUT_LONG_MULTI, index=False, compression="zstd")
    validation = write_station_interpolation_validation(counter_days)
    print(
        "Rebuilt locations only:",
        f"counter-days={len(counter_days):,}",
        f"PDF-station site-years={counter_days.loc[counter_days['location_method'].eq('station_interpolated_from_pdf_station'), ['year', 'counter_site_id']].drop_duplicates().shape[0]:,}",
        f"validation_rows={len(validation):,}",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare daily PDF traffic counts and locations.")
    parser.add_argument(
        "--locations-only",
        action="store_true",
        help="Reapply location rules to daily_counts.parquet without re-parsing PDFs.",
    )
    args = parser.parse_args()
    if args.locations_only:
        rebuild_locations_only()
        return
    OUT_LONG_MULTI.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOTES_MULTI.parent.mkdir(parents=True, exist_ok=True)

    parsed_frames: list[pd.DataFrame] = []
    parsed_meta: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    missing_years: list[int] = []

    for year in sorted(PDF_CANDIDATES):
        path = resolve_pdf(year)
        if path is None:
            missing_years.append(year)
            continue
        long_df, meta_df, summary = parse_year(year, path)
        parsed_frames.append(long_df)
        parsed_meta.append(meta_df)
        summaries.append(summary)

    if not parsed_frames:
        candidates = ", ".join(str(p) for paths in PDF_CANDIDATES.values() for p in paths)
        raise SystemExit(f"Missing all traffic PDF inputs. Checked: {candidates}")

    long_all = pd.concat(parsed_frames, ignore_index=True).sort_values(
        ["year", "station_id", "road_section", "date"]
    )
    meta_all = pd.concat(parsed_meta, ignore_index=True).sort_values(["year", "station_id", "road_section"])

    OUT_CHANNEL_MULTI.parent.mkdir(parents=True, exist_ok=True)
    long_all.to_csv(OUT_CHANNEL_MULTI, index=False)
    counter_days = add_counter_locations(build_counter_days(long_all))
    count_columns = [
        "date", "year", "counter_site_id", "station_id", "road_section", "site_name",
        "traffic_volume", "directional_channels", "source_fastnr",
    ]
    counter_days[count_columns].to_parquet(OUT_COUNTS, index=False, compression="zstd")
    location_columns = [column for column in counter_days.columns if column not in count_columns]
    counter_days[["year", "counter_site_id", *location_columns]].drop_duplicates(
        ["year", "counter_site_id"]
    ).to_csv(OUT_LOCATIONS, index=False)
    counter_days.to_parquet(OUT_LONG_MULTI, index=False, compression="zstd")
    station_validation = write_station_interpolation_validation(counter_days)
    meta_all.to_csv(OUT_META_MULTI, index=False)

    total_all = build_daily_total(long_all)
    total_all.to_csv(OUT_TOTAL_MULTI, index=False)

    write_2024_compatibility_outputs(long_all, meta_all, summaries)

    notes = [
        "Vegagerdin PDF 2019-2024 Traffic Exposure Parse Notes",
        "=====================================================",
        "Observed annual PDF traffic reports parsed into a common counter-day format.",
        "",
    ]
    for summary in summaries:
        notes.extend(
            [
                f"Year {summary['year']}:",
                f"  Input PDF: {summary['input_pdf']}",
                f"  Readable table pages: {summary['readable_pages']:,}",
                f"  Counter-level daily rows parsed: {summary['rows']:,}",
                f"  Unique station IDs: {summary['unique_station_ids']:,}",
                f"  Unique road sections: {summary['unique_road_sections']:,}",
                f"  Date range: {summary['date_min']} to {summary['date_max']}",
                "",
            ]
        )
    if missing_years:
        notes.extend(
            [
                f"Missing years not parsed: {', '.join(str(y) for y in missing_years)}",
                "",
            ]
        )
    notes.extend(
        [
            f"Combined direction/lane-channel rows: {len(long_all):,}",
            f"Combined physical counter-day rows: {len(counter_days):,}",
            f"Combined daily-total rows: {len(total_all):,}",
            f"Combined physical counter sites: {counter_days['counter_site_id'].nunique():,}",
            f"Combined unique road sections: {long_all['road_section'].nunique():,}",
            f"Combined date range: {long_all['date'].min()} to {long_all['date'].max()}",
            f"Counter sites with official coordinates: "
            f"{counter_days.loc[~counter_days['location_is_estimated'], 'counter_site_id'].nunique():,}",
            f"Counter sites with a residual road-section midpoint in at least one year: "
            f"{counter_days.loc[counter_days['location_method'].str.startswith('section_midpoint'), 'counter_site_id'].nunique():,}",
            f"Counter-site years using PDF-station interpolation: "
            f"{counter_days.loc[counter_days['location_method'].eq('station_interpolated_from_pdf_station'), ['year', 'counter_site_id']].drop_duplicates().shape[0]:,}",
            f"Independent name-match validation rows for station interpolation: {len(station_validation):,}",
            f"Median station-interpolation error (m): "
            f"{station_validation['station_interpolation_error_m'].median():.1f}" if len(station_validation) else "Median station-interpolation error (m): n/a",
            "",
            "Interpretation:",
            "The canonical daily_traffic.parquet has one row per physical counter site and date.",
            "Direction/lane channels have been summed; source fastnr values and their count remain visible.",
            "Official counter coordinates are used only for conservative links. Otherwise the PDF road",
            "station (stöð) is interpolated between the year-specific Bst and Est values along the",
            "registered road geometry and location_is_estimated is true. A road-section midpoint is used",
            "only when this interpolation is unavailable.",
            "",
            f"Output daily counts: {OUT_COUNTS}",
            f"Output counter locations: {OUT_LOCATIONS}",
            f"Output canonical counter-day file: {OUT_LONG_MULTI}",
            f"Archived direction/lane-channel file: {OUT_CHANNEL_MULTI}",
            f"Output daily-total file: {OUT_TOTAL_MULTI}",
            f"Output metadata file: {OUT_META_MULTI}",
            f"Station-interpolation validation file: {OUT_STATION_VALIDATION}",
        ]
    )
    OUT_NOTES_MULTI.write_text("\n".join(notes) + "\n", encoding="utf-8")
    print("\n".join(notes))


if __name__ == "__main__":
    main()
