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
- `data/processed/{accidents,weather,traffic}/`: reproducible local working
  products used only during preparation; never committed.
- `data/analysis/`: the readable CSV inputs used by every routine analysis
  script; never committed because they derive from authorised local data.
- `docs/`: source inventory, variables and fixed analysis rules.
- `archive/`: local diagnostics and superseded material; not version controlled.
- `src/`: documented preparation, matching and analysis programs.
- `reports/main/`: supervisor-ready and thesis-ready outputs.
- `reports/thesis/`: the current English thesis draft.

## Working data

- `data/raw/weather/weather_10min_raw.parquet`: raw continuous 10-minute weather observations.
- `data/processed/weather/weather.parquet` is the only very large
  temporary file: the 211.5 million cleaned 10-minute observations. It is used
  while creating the CSV frequency table, never by `src.analyze`.
- `data/analysis/accidents.csv` and `weather_frequency.csv` are the complete
  inputs to the primary O/E analysis.
- `data/analysis/rate_model.csv` is the 1.2 MB, 24,048-row input to the
  within-road/year/period rate model.
- `data/analysis/traffic_rate_summary.csv` is an 18-row exposure table for the
  descriptive accidents-per-vehicle-km result.
- `data/analysis/daily_traffic.csv` is the optional counter-day traffic input.
- `reports/main/figures/stratified_crash_rate_ratio_by_wind.png`: estimated
  within-road-section injury-accident rate ratios by 5 m/s mean-wind interval.
  It reports time-proportional annual-traffic allocation across local wind
  frequency intervals.

## Rebuild the results

After cloning, create a Python environment, install the dependencies, and
place the authorised raw deliveries in the paths in
[`data/README.md`](data/README.md). The public road geometry is downloaded by
the pipeline. The six daily-traffic PDFs (2019--2024) are optional and are
only needed for the daily-traffic description.

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

To rebuild the daily-traffic figure as well, add the PDFs locally and use:

```bash
.venv/bin/python -m src.prepare --stage prepare --daily-traffic
```

If the PDFs are unavailable, the primary wind and annual-traffic results can
still be rebuilt after preparation with:

```bash
.venv/bin/python -m src.analyze --skip-daily-traffic
```

Without data, a clone can inspect every documented script and fixed analysis
decision. With the authorised raw deliveries it can rebuild the same local
processed files, tables, and figures. The accident workflow also requires its
supplied road-link and urban-boundary reference files; daily traffic requires
the six PDFs and weather-station metadata.

## Primary Assumptions

- Rural injury accidents, 2007-2025.
- Nearest valid 10-minute weather observation within 20 km.
- Expected accidents standardized by weather station and season, with weather frequency pooled across 2007--2025.
- Mean wind speed (`f`) is the primary exposure; maximum wind gust (`fg`) is secondary.
- Results describe associations and are not causal estimates.
