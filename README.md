# Wind and Rural Road Accidents

This project evaluates whether rural injury accidents are disproportionately
common in high winds. The primary result is a wind-frequency-standardized
observed/expected curve with weather-station-clustered bootstrap confidence
intervals.

## Repository scope

This GitHub repository contains **code and documentation only**. Raw data,
processed data, diagnostics, and generated figures stay on each researcher's
computer and are excluded by `.gitignore`. This prevents large copies of the
same data from being committed, while keeping the entire transformation from
the authorised source deliveries transparent and reproducible.

## Directory structure

- `data/raw/{accidents,weather,traffic}/`: unchanged source and reference data
  downloaded or supplied locally; never committed.
- `data/processed/{accidents,weather,traffic}/`: reproducible local cleaning
  products and analysis caches; never committed.
- `docs/`: source inventory, variables and fixed analysis rules.
- `archive/`: local diagnostics and superseded material; not version controlled.
- `src/`: documented preparation, matching and analysis programs.
- `reports/main/`: supervisor-ready and thesis-ready outputs.
- `reports/thesis/`: the current English thesis draft.

## Core Data

- `data/raw/weather/weather_10min_raw.parquet`: raw continuous 10-minute weather observations.
- `data/processed/weather/weather_10min_clean.parquet`: cleaned `f`, `fg`, and `t`, with
  `0 <= f < 45 m/s`, `0 <= fg < 65 m/s`, and frozen all-zero sensor runs removed.
- `data/processed/accidents/rural_injury_accidents.parquet`: all 6,120 study
  accidents with location, road, weather and nullable annual-traffic fields.
- `data/processed/accidents/accidents.csv`: readable CSV export of the same
  6,120 accidents.
- `data/processed/weather/wind_frequency_station_year_season.parquet`: wind
  frequency denominator for analysis A.
- `data/processed/accidents/oe_station_period_bins.parquet`: canonical
  station-period O/E input for analysis A and its clustered bootstrap.
- `data/processed/traffic/road_section_wind_panel_2007_2024.parquet`: canonical
  long table for analysis B
  by road section, year, official traffic period, wind variable, and 3 m/s
  interval. VDU uses December-March; SDU uses June-September; the four remaining
  months use a day-weighted traffic residual derived from ADU, SDU, and VDU.
- `reports/main/figures/traffic_sensitivity.png`: direct
  same-subset comparison of wind-frequency-only and wind-plus-traffic
  adjustment.

## Rebuild the results

After cloning, create a Python environment, install the dependencies, and
place the authorised raw deliveries in the paths in
[`data/README.md`](data/README.md). The public road geometry is downloaded by
the pipeline. The six daily-traffic PDFs (2019--2024) are optional and are
only needed for the daily-traffic sensitivity analysis.

```bash
.venv/bin/python -m src.prepare --stage prepare
.venv/bin/python -m src.analyze
```

Or, after raw preparation has completed, run both stages in one command:

```bash
.venv/bin/python -m src.prepare --stage all
```

See `data/README.md` for the required local source files and `docs/` for source
and variable definitions.

To include the optional daily-traffic analysis, add the PDFs locally and use:

```bash
.venv/bin/python -m src.prepare --stage prepare --daily-traffic
```

Without data, a clone can inspect every documented script and fixed analysis
decision. With the authorised raw deliveries it can rebuild the same local
processed files, tables, and figures. The accident workflow also requires its
supplied road-link and urban-boundary reference files; daily traffic requires
the six PDFs and weather-station metadata.

## Primary Assumptions

- Rural injury accidents, 2007-2024.
- Nearest valid 10-minute weather observation within 20 km.
- Expected accidents standardized by weather station, calendar year, and season.
- Maximum wind gust (`fg`) is the primary exposure.
- Results describe associations and are not causal estimates.
