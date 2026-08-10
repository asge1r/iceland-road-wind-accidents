"""Attach documented coordinates to the extracted daily traffic counter-days.

This is the second half of the daily-traffic pipeline. It reads the immutable
counter-day counts, applies the current PDF-``stöð`` location rule, and writes
the coordinate-enriched daily counter table. It never re-parses the PDFs.
"""

from __future__ import annotations

import argparse

import pandas as pd

from src.traffic import prepare_daily_traffic as legacy


def locate() -> None:
    """Apply the location rule to existing canonical daily count records."""
    if not legacy.OUT_COUNTS.exists():
        raise FileNotFoundError(
            f"Missing {legacy.OUT_COUNTS}. Run src.traffic.extract_daily_traffic first."
        )
    located = legacy.add_counter_locations(pd.read_parquet(legacy.OUT_COUNTS))
    count_columns = [
        "date", "year", "counter_site_id", "station_id", "road_section",
        "site_name", "traffic_volume", "directional_channels", "source_fastnr",
    ]
    location_columns = [column for column in located.columns if column not in count_columns]
    if located.duplicated(["counter_site_id", "date"]).any():
        raise ValueError("Located daily-traffic output is not unique on physical counter and date.")

    legacy.OUT_LOCATIONS.parent.mkdir(parents=True, exist_ok=True)
    located[["year", "counter_site_id", *location_columns]].drop_duplicates(
        ["year", "counter_site_id"]
    ).to_csv(legacy.OUT_LOCATIONS, index=False)
    located.to_parquet(legacy.OUT_LONG_MULTI, index=False, compression="zstd")
    validation = legacy.write_station_interpolation_validation(located)
    print(
        f"Wrote {len(located):,} located counter-days to {legacy.OUT_LONG_MULTI}; "
        f"location validation rows: {len(validation):,}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    locate()


if __name__ == "__main__":
    main()
