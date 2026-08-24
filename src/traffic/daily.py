"""Extract observed daily traffic from the Vegagerðin PDF calendars.

This is the first half of the daily-traffic pipeline.  It reads the PDF files,
keeps the individual direction/lane channels for audit, and writes exactly one
row per physical counter site and date to ``daily_raw.parquet``.  It does
not assign coordinates or weather.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.traffic import pdf_parser


OUT_COUNTS = Path("data/processed/traffic/daily_raw.parquet")
OUT_CHANNELS = Path("archive/generated_diagnostics/daily_traffic_channels_2019_2024.csv")
OUT_METADATA = Path("archive/generated_diagnostics/daily_counter_metadata_2019_2024.csv")
OUT_NOTES = Path("archive/generated_diagnostics/traffic_pdf_2019_2024_notes.txt")


def extract(
    pdf_directory: Path,
    counts_output: Path,
    channels_output: Path,
    metadata_output: Path,
    notes_output: Path,
) -> None:
    """Parse available PDF years and write the canonical counter-day count file."""
    parsed_frames: list[pd.DataFrame] = []
    metadata_frames: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    missing_years: list[int] = []

    for year in sorted(pdf_parser.PDF_CANDIDATES):
        path = pdf_parser.resolve_pdf(year, pdf_directory)
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

    counts_output.parent.mkdir(parents=True, exist_ok=True)
    channels_output.parent.mkdir(parents=True, exist_ok=True)
    metadata_output.parent.mkdir(parents=True, exist_ok=True)
    channels.to_csv(channels_output, index=False)
    counter_days[count_columns].to_parquet(counts_output, index=False, compression="zstd")
    pd.concat(metadata_frames, ignore_index=True).drop_duplicates().to_csv(
        metadata_output, index=False
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
        f"Output: {counts_output}",
    ]
    notes_output.parent.mkdir(parents=True, exist_ok=True)
    notes_output.write_text("\n".join(notes) + "\n", encoding="utf-8")
    print("\n".join(notes))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input-directory", type=Path, default=pdf_parser.PDF_DIRECTORY)
    parser.add_argument("-o", "--output", type=Path, default=OUT_COUNTS)
    parser.add_argument("-c", "--channels-output", type=Path, default=OUT_CHANNELS)
    parser.add_argument("-m", "--metadata-output", type=Path, default=OUT_METADATA)
    parser.add_argument("-n", "--notes-output", type=Path, default=OUT_NOTES)
    args = parser.parse_args()
    extract(
        args.input_directory,
        args.output,
        args.channels_output,
        args.metadata_output,
        args.notes_output,
    )


if __name__ == "__main__":
    main()
