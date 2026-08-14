"""Extract observed daily traffic from the Vegagerðin PDF calendars.

This is the first half of the daily-traffic pipeline.  It reads the PDF files,
keeps the individual direction/lane channels for audit, and writes exactly one
row per physical counter site and date to ``daily_counts.parquet``.  It does
not assign coordinates or weather.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.traffic import pdf_parser


OUT_COUNTS = Path("data/processed/traffic/daily_counts.parquet")
OUT_CHANNELS = Path("archive/generated_diagnostics/daily_traffic_channels_2019_2024.csv")
OUT_METADATA = Path("archive/generated_diagnostics/daily_counter_metadata_2019_2024.csv")
OUT_NOTES = Path("archive/generated_diagnostics/traffic_pdf_2019_2024_notes.txt")


def extract() -> None:
    """Parse available PDF years and write the canonical counter-day count file."""
    parsed_frames: list[pd.DataFrame] = []
    metadata_frames: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    missing_years: list[int] = []

    for year in sorted(pdf_parser.PDF_CANDIDATES):
        path = pdf_parser.resolve_pdf(year)
        if path is None:
            missing_years.append(year)
            continue
        channel_rows, metadata, summary = pdf_parser.parse_year(year, path)
        parsed_frames.append(channel_rows)
        metadata_frames.append(metadata)
        summaries.append(summary)

    if not parsed_frames:
        raise SystemExit("No readable daily-traffic PDF was found in data/raw/traffic/daily_pdf/.")

    channels = pd.concat(parsed_frames, ignore_index=True).sort_values(
        ["year", "station_id", "road_section", "date"]
    )
    counter_days = pdf_parser.build_counter_days(channels)
    count_columns = [
        "date", "year", "counter_site_id", "station_id", "road_section",
        "site_name", "traffic_volume", "directional_channels", "source_fastnr",
    ]
    if counter_days.duplicated(["counter_site_id", "date"]).any():
        raise ValueError("Daily-count output is not unique on physical counter and date.")

    OUT_COUNTS.parent.mkdir(parents=True, exist_ok=True)
    OUT_CHANNELS.parent.mkdir(parents=True, exist_ok=True)
    OUT_METADATA.parent.mkdir(parents=True, exist_ok=True)
    channels.to_csv(OUT_CHANNELS, index=False)
    counter_days[count_columns].to_parquet(OUT_COUNTS, index=False, compression="zstd")
    pd.concat(metadata_frames, ignore_index=True).drop_duplicates().to_csv(
        OUT_METADATA, index=False
    )

    notes = [
        "Daily traffic PDF extraction",
        "============================",
        "Each output row is one physical counter site on one date.",
        "Direction/lane channels are summed; source fastnr values remain available.",
        f"Observed years: {', '.join(str(item['year']) for item in summaries)}",
        f"Unavailable PDF years: {', '.join(map(str, missing_years)) or 'none'}",
        f"Channel rows retained for audit: {len(channels):,}",
        f"Physical counter-day rows: {len(counter_days):,}",
        f"Physical counter sites: {counter_days['counter_site_id'].nunique():,}",
        f"Output: {OUT_COUNTS}",
    ]
    OUT_NOTES.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOTES.write_text("\n".join(notes) + "\n", encoding="utf-8")
    print("\n".join(notes))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    extract()


if __name__ == "__main__":
    main()
