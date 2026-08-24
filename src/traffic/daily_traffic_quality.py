"""Create quality-control outputs for matched daily traffic counter data.

The outputs document counter coverage and agreement with annual ADU. They do
not estimate accident risk and are separate from the daily traffic result.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.traffic import daily_traffic_tools as tools


DEFAULT_INPUT = Path("data/processed/traffic/daily_weather.parquet")
DEFAULT_ANNUAL = Path("data/processed/traffic/annual.csv")
DEFAULT_SUMMARY = Path("reports/working/tables/daily_traffic_diagnostic.csv")
DEFAULT_VALIDATION = Path("archive/generated_diagnostics/daily_traffic_adu_validation.csv")
DEFAULT_ADU_SUMMARY = Path("archive/generated_diagnostics/daily_traffic_adu_summary.csv")
DEFAULT_ADU_FIGURE = Path("reports/working/traffic_validation.png")
DEFAULT_FIGURE = Path("reports/working/daily_traffic_diagnostic.png")
DEFAULT_NOTES = Path("archive/generated_diagnostics/daily_traffic_notes.md")


def write_notes(
    path: Path,
    panel: pd.DataFrame,
    summary: pd.DataFrame,
    adu_summary: pd.DataFrame,
) -> None:
    high_wind = summary[
        summary["variable"].eq("f_daytime_mean") & summary["bin"].eq("20-25")
    ]
    high_text = "not available" if high_wind.empty else f"{high_wind.iloc[0]['traffic_index_median']:.1f}"
    text = f"""# Daily traffic quality control

## Scope

- Counter-days: {len(panel):,}
- Counter sites: {panel['counter_site_id'].nunique():,}
- Counter-days with daytime mean wind: {panel['f_daytime_mean'].notna().sum():,}
- Counter-days recorded as zero traffic: {panel['traffic_volume'].eq(0).sum():,}
- Median traffic index in the 20--25 m/s daytime mean-wind interval: {high_text}

The traffic index compares each counter-day with the median count for the same
counter, year, month, and weekday. It describes participating counter sites;
it is not national traffic exposure or hourly vehicle-kilometres.

## ADU consistency check

```text
{adu_summary.to_string(index=False)}
```

Observed PDF counts and ADU can share permanent counters, so this comparison
checks consistency rather than providing independent validation.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-a", "--annual", type=Path, default=DEFAULT_ANNUAL)
    parser.add_argument("-s", "--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("-v", "--adu-validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("-u", "--adu-summary", type=Path, default=DEFAULT_ADU_SUMMARY)
    parser.add_argument("-f", "--adu-figure", type=Path, default=DEFAULT_ADU_FIGURE)
    parser.add_argument("-o", "--output-figure", type=Path, default=DEFAULT_FIGURE)
    parser.add_argument("-n", "--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("-b", "--bootstrap-replicates", type=int, default=1000)
    args = parser.parse_args()

    panel = pd.read_parquet(args.input)
    summary = tools.build_wind_summary(panel, args.bootstrap_replicates)
    validation, adu_summary = tools.build_adu_validation(panel, args.annual)
    for path in [
        args.summary,
        args.adu_validation,
        args.adu_summary,
        args.adu_figure,
        args.output_figure,
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary, index=False)
    validation.to_csv(args.adu_validation, index=False)
    adu_summary.to_csv(args.adu_summary, index=False)
    tools.plot_wind_summary(summary, args.output_figure)
    tools.plot_adu_validation(validation, args.adu_figure)
    write_notes(args.notes, panel, summary, adu_summary)
    print(adu_summary.to_string(index=False))
    print(f"wrote={args.summary}")


if __name__ == "__main__":
    main()
