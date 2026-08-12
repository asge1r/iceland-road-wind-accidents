"""Parse Vegagerðin daily-traffic PDF calendars into counter-day records.

This module deliberately does one job only: extract traffic counts and combine
the direction/lane channels for each physical counter and day.  Coordinates
and weather are added by later, separate pipeline steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import zlib

import pandas as pd


PDF_CANDIDATES = {
    2019: "r_cross_umferd_2019.pdf",
    2020: "r_cross_umferd_2020_fastir.pdf",
    2021: "r_cross_umferd_2021_fastir.pdf",
    2022: "r_cross_umferd_2022_fastir-1.pdf",
    2023: "r_cross_umferd_2023_fastir.pdf",
    2024: "r_cross_umferd_2024_fastir.pdf",
}
PDF_DIRECTORY = Path("data/raw/traffic/daily_pdf")
MONTH_CENTRES = [134, 187, 235, 287, 339, 392, 444, 496, 549, 601, 653, 710]


@dataclass(frozen=True)
class TextItem:
    x: float
    y: float
    text: str


def resolve_pdf(year: int) -> Path | None:
    """Return the expected local PDF for a year, or ``None`` when unavailable."""
    path = PDF_DIRECTORY / PDF_CANDIDATES[year]
    return path if path.exists() else None


def _unescape(value: str) -> str:
    replacement = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "(": "(", ")": ")", "\\": "\\"}
    output, position = [], 0
    while position < len(value):
        if value[position] == "\\" and position + 1 < len(value):
            output.append(replacement.get(value[position + 1], value[position + 1]))
            position += 2
        else:
            output.append(value[position])
            position += 1
    return "".join(output)


def _page_streams(path: Path) -> list[str]:
    streams: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", path.read_bytes(), re.S):
        try:
            text = zlib.decompress(match.group(1)).decode("latin1", errors="ignore")
        except Exception:
            continue
        if "Umfe" in text and "TJ" in text:
            streams.append(text)
    return streams


def _text_items(stream: str) -> list[TextItem]:
    items: list[TextItem] = []
    for block_match in re.finditer(r"BT(.*?)ET", stream, re.S):
        block = block_match.group(1)
        matrix = re.search(r"1 0 0 1 ([0-9.\-]+) ([0-9.\-]+) Tm", block)
        if not matrix:
            continue
        pieces: list[str] = []
        for array in re.finditer(r"\[(.*?)\]\s*TJ", block, re.S):
            pieces.extend(_unescape(item.group(1)) for item in re.finditer(r"\((.*?)\)", array.group(1), re.S))
        pieces.extend(_unescape(item.group(1)) for item in re.finditer(r"\((.*?)\)\s*Tj", block, re.S))
        text = "".join(pieces).strip()
        if text:
            items.append(TextItem(float(matrix.group(1)), float(matrix.group(2)), text))
    return items


def _metadata(items: list[TextItem], year: int, source: Path, page: int) -> dict[str, object]:
    metadata: dict[str, object] = {"year": year, "pdf_source": str(source), "pdf_page": page, "fastnr": "", "station_id": "", "road_section": "", "site_name": ""}
    for item in items:
        match = re.search(r"fastnr\.\s*(\d+)\s+stöð\s+(\d+)", item.text)
        if match:
            metadata["fastnr"], metadata["station_id"] = match.groups()
        if item.y > 500 and re.fullmatch(r"\d+[a-z]?-[0-9a-z]+", item.text):
            metadata["road_section"] = item.text
        if item.x > 300 and item.y > 500 and "Umferð" not in item.text:
            metadata["site_name"] = item.text
    return metadata


def _month(x: float) -> int | None:
    index = min(range(12), key=lambda item: abs(x - MONTH_CENTRES[item]))
    return index + 1 if abs(x - MONTH_CENTRES[index]) <= 22 else None


def _parse_page(stream: str, year: int, source: Path, page: int) -> tuple[pd.DataFrame, dict[str, object]]:
    items = _text_items(stream)
    metadata = _metadata(items, year, source, page)
    rows: list[dict[str, object]] = []
    for day_item in (item for item in items if 70 < item.x < 100 and 30 < item.y < 460 and re.fullmatch(r"\d{2}", item.text)):
        day = int(day_item.text)
        for item in (candidate for candidate in items if abs(candidate.y - day_item.y) < 0.4):
            month = _month(item.x)
            if not (105 <= item.x <= 735 and month and re.fullmatch(r"\d+", item.text)):
                continue
            try:
                traffic_date = date(year, month, day)
            except ValueError:
                continue
            rows.append({**metadata, "date": traffic_date.isoformat(), "traffic_volume": int(item.text)})
    return pd.DataFrame(rows), metadata


def parse_year(year: int, path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Parse one PDF into its source channels, page metadata and audit summary."""
    streams = _page_streams(path)
    if not streams:
        raise ValueError(f"No readable daily-traffic table pages found in {path}")
    parsed, metadata = [], []
    for page, stream in enumerate(streams, start=1):
        rows, details = _parse_page(stream, year, path, page)
        metadata.append(details)
        if not rows.empty:
            parsed.append(rows)
    if not parsed:
        raise ValueError(f"No daily counts were parsed from {path}")
    channels = pd.concat(parsed, ignore_index=True).drop_duplicates(
        ["year", "fastnr", "station_id", "road_section", "date"], keep="last"
    ).sort_values(["year", "station_id", "road_section", "date"])
    meta = pd.DataFrame(metadata).drop_duplicates(["year", "fastnr", "station_id", "road_section"], keep="last")
    return channels, meta, {"year": year, "input_pdf": str(path), "readable_pages": len(streams), "rows": len(channels)}


def build_counter_days(channels: pd.DataFrame) -> pd.DataFrame:
    """Sum direction/lane channels to one physical counter-site day."""
    data = channels.copy()
    data["road_section"] = data["road_section"].astype("string").str.strip().str.lower()
    data["date"] = pd.to_datetime(data["date"])
    data["fastnr"] = pd.to_numeric(data["fastnr"], errors="raise").astype(int)
    data["station_id"] = pd.to_numeric(data["station_id"], errors="raise").astype(int)
    daily = data.groupby(["year", "road_section", "station_id", "date"], as_index=False).agg(
        site_name=("site_name", lambda values: " | ".join(sorted(set(values.dropna().astype(str))))),
        traffic_volume=("traffic_volume", "sum"), directional_channels=("fastnr", "nunique"),
        source_fastnr=("fastnr", lambda values: "|".join(str(value) for value in sorted(set(values)))),
    )
    daily["counter_site_id"] = daily["road_section"].astype(str) + ":" + daily["station_id"].astype(str)
    if daily.duplicated(["counter_site_id", "date"]).any():
        raise ValueError("Counter-day output is not unique on physical counter and date")
    return daily
