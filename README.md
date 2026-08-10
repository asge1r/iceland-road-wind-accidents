# Wind and Rural Road Accidents

This project evaluates whether rural injury accidents are disproportionately
common in high winds. The primary result is a wind-frequency-standardized
observed/expected curve with weather-station-clustered bootstrap confidence
intervals.

## Repository scope

This GitHub repository contains code and documentation only. Raw data, derived
data and generated figures remain local and are excluded by `.gitignore`.
Someone with the authorised source files can recreate every processed dataset
by following [`pipeline.md`](pipeline.md).

## Directory structure

- `data/raw/{accidents,weather,traffic}/`: unchanged source and reference data.
- `data/processed/{accidents,weather,traffic}/`: the small set of canonical
  cleaned and joined inputs used by the analyses.
- `docs/`: source inventory, variables and fixed analysis rules.
- `archive/`: local diagnostics and superseded material; not version controlled.
- `src/`: documented preparation, matching and analysis programs.
- `reports/main/`: supervisor-ready and thesis-ready outputs.
- `reports/thesis/`: the current English thesis draft.

## Core Data

- `data/raw/weather/weather_10min_raw.parquet`: raw continuous 10-minute weather observations.
- `data/processed/weather/weather_10min_clean.parquet`: cleaned `f`, `fg`, and `t`, with
  `0 <= f <= 40 m/s`, `0 <= fg <= 75 m/s`, and frozen all-zero sensor runs removed.
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
- `reports/main/traffic_adjustment.png`: direct
  same-subset comparison of wind-frequency-only and wind-plus-traffic
  adjustment.

## Rebuild the results

```bash
.venv/bin/python -m src.run_analysis
```

This command recreates the retained results from existing processed data. To
rebuild data from authorised raw files and then recreate the results, run:

```bash
.venv/bin/python -m src.run_pipeline --stage all
```

See `data/README.md` for the required local source files and `docs/` for source
and variable definitions.

## Primary Assumptions

- Rural injury accidents, 2007-2024.
- Nearest valid 10-minute weather observation within 20 km.
- Expected accidents standardized by weather station, calendar year, and season.
- Maximum wind gust (`fg`) is the primary exposure.
- Results describe associations and are not causal estimates.
