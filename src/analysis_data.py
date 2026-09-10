"""Build the documented analysis CSVs used by tables and figures."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.export_common import ROOT, season_from_month, traffic_period_from_month
from src.export_docs import register_manifest_file, write_manifest, write_readme
from src.exports_accidents import (
    export_accident_tables,
    export_case_control,
    export_temperature_matches,
)
from src.exports_counters import (
    export_counter_sections,
    export_daily_weather_rate,
    export_counter_validation,
    export_daily_traffic,
    export_selection_summary,
)
from src.exports_traffic import (
    export_annual_traffic,
    export_rate_tables,
    export_season_rate_input,
    export_temperature_rate_input,
)
from src.exports_weather import (
    export_frequency,
    export_monthly_frequency,
    export_weather_source_audit,
    export_temperature_frequency,
    export_weather_cleaning,
    export_yearly_frequency,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/analysis"),
        help="Output directory.",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, int, list[str], str]] = []
    entries.extend(export_accident_tables(args.output))
    records, columns = export_temperature_matches(args.output)
    entries.append(
        (
            "temperature_matches.csv", records, columns,
            "One row per accident with the selected temperature observation and source.",
        )
    )
    for filename, description, exporter in [
        (
            "weather_frequency.csv",
            "Station-season wind and temperature frequencies used as O/E denominators.",
            export_frequency,
        ),
        (
            "weather_yearly.csv",
            "Station-year-season mean-wind and temperature frequencies used for the year-adjusted O/E check.",
            export_yearly_frequency,
        ),
        (
            "weather_monthly.csv",
            "Pooled station-calendar-month frequencies in the O/E plotting bins.",
            export_monthly_frequency,
        ),
        (
            "weather_cleaning.csv",
            "Annual and total counts from the fixed weather-quality rules.",
            export_weather_cleaning,
        ),
        (
            "annual_traffic.csv",
            "Annual road-section traffic volumes and lengths.",
            export_annual_traffic,
        ),
        (
            "case_control.csv",
            "Time-stratified mean-wind, gust, and temperature samples.",
            export_case_control,
        ),
        (
            "temperature_frequency.csv",
            "Combined station-year-season temperature counts used for the updated denominator.",
            export_temperature_frequency,
        ),
        (
            "weather_source_audit.csv",
            "Official source-file hashes, row checks and date coverage.",
            export_weather_source_audit,
        ),
    ]:
        records, columns = exporter(args.output)
        entries.append((filename, records, columns, description))
    entries.extend(export_rate_tables(args.output))
    entries.append(export_temperature_rate_input(args.output))
    entries.append(export_season_rate_input(args.output))
    records, columns = export_selection_summary(args.output)
    entries.append(
        (
            "selection_summary.csv",
            records,
            columns,
            "Counts used in data-selection figures.",
        )
    )
    daily_entries = export_daily_traffic(args.output)
    entries.extend(daily_entries)
    counter_sections = export_counter_sections(args.output)
    if counter_sections is not None:
        entries.append(counter_sections)
    daily_weather_rate = export_daily_weather_rate(args.output)
    if daily_weather_rate is not None:
        entries.append(daily_weather_rate)
    counter_validation = ROOT / "traffic/daily_counter_station_validation.csv"
    if counter_validation.exists():
        records, columns = export_counter_validation(args.output)
        entries.append(
            (
                "counter_check.csv", records, columns,
                "Estimated counter coordinates compared with official 20 m road-station points.",
            )
        )
    write_readme(args.output, bool(daily_entries))
    entries.append(
        (
            "README.md",
            0,
            ["file descriptions", "rebuild instruction"],
            "Description of the analysis data layer.",
        )
    )
    entries.append(
        (
            "manifest.csv",
            len(entries) + 1,
            ["file", "records", "columns", "description"],
            "Inventory of the analysis data files.",
        )
    )
    write_manifest(args.output, entries)
    register_manifest_file(
        args.output,
        "daily_season_panel.csv",
        "Canonical counter-year-season input for seasonal allocated-traffic analyses.",
    )
    print(f"Wrote {len(entries)} analysis-layer files to {args.output}")


if __name__ == "__main__":
    main()
