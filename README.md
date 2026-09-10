# Meteorological Conditions and Rural Injury Accidents in Iceland

*Analysis of Accident Frequency and Traffic, 2007–2025*

This project examines rural injury accidents in relation to mean wind, gust,
temperature, season, hour, daylight, and available traffic data. The primary
result compares accident counts with the
local frequency of each accident-time ten-minute mean-wind interval. Its
uncertainty intervals account
for accidents and weather observations grouped at the same weather station.
Supporting analyses cover matched-time wind and temperature, adjusted injury
severity, daylight, a formal seasonal comparison, accident type, and the
available annual and daily traffic data.

## Repository scope

This GitHub repository contains the analysis code, documentation, thesis draft,
and the small tables and figures needed to inspect the reported results. Raw
data, processed data, analysis CSV files, and working diagnostics
remain local and are excluded by `.gitignore`.

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
- `reports/main/`: retained tables and figures used in the thesis.
- `reports/thesis/`: the current English thesis draft.

## Working data

- `data/raw/weather/weather_10min_raw.parquet` contains 232.5 million raw
  ten-minute weather rows assembled from the supplied IMO station files.
- `data/processed/weather/weather.parquet` contains 230.5 million cleaned
  ten-minute observations. It is used to create the compact analysis CSVs and
  is never read by `src.analyze`.
- `data/analysis/accidents.csv`, `accident_conditions.csv`, and
  `weather_frequency.csv` are the complete inputs to the primary O/E analysis.
- `data/analysis/road_rate.csv` is the compact input to the
  within-road/year/period rate model.
- `data/analysis/road_exposure.csv` is an 18-row estimated vehicle-kilometre table for the
  descriptive accidents-per-vehicle-km result.
- `data/analysis/daily_traffic.csv` is the optional, larger analysis CSV for
  daily counters; `counter_locations.csv` supplies their locations.
- `reports/main/figures/wind_rate.png`: estimated
  within-road-section injury-accident rate ratios by 5 m/s mean-wind interval.
  It reports time-proportional annual-traffic allocation across local wind
  frequency intervals.
- `reports/main/figures/wind_oe_comparison.png`: the primary weather-frequency
  O/E beside annual-traffic and daily-traffic standardisations. The three
  panels retain separate samples and denominator definitions.

## Rebuild the results

After cloning, create a Python environment, install the dependencies, and
place the authorised raw deliveries in the paths in
[`data/README.md`](data/README.md). The public road geometry is downloaded by
the pipeline. The six daily-traffic PDFs (2019--2024) are optional and are
needed for all daily-counter comparisons.

```bash
.venv/bin/python -m src.prepare --stage prepare
.venv/bin/python -m src.analyze
```

For a focused rebuild, select one or more named analysis stages. This avoids
rerunning unrelated 5,000-replicate bootstrap calculations:

```bash
.venv/bin/python -m src.analyze --stage weather-frequency
.venv/bin/python -m src.analyze --stage traffic-adjusted --stage products
.venv/bin/python -m src.analyze --stage supporting --stage products
```

The available stages and their exact scripts are documented in
[`docs/pipeline.md`](docs/pipeline.md). Running without `--stage` still rebuilds
the complete result set in dependency order.

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

Run the focused definition and analysis-input checks with:

```bash
.venv/bin/python -m unittest discover -s tests
```

Without data, a clone can inspect every documented script and fixed analysis
decision. With the authorised raw deliveries it can rebuild the same local
processed files, tables, and figures. The accident workflow also requires its
supplied road-link and urban-boundary reference files; daily traffic requires
the six PDFs and weather-station metadata.

## Main analysis choices

- Rural injury accidents, 2007-2025.
- Nearest valid 10-minute weather observation within 20 km.
- Expected accidents adjusted for weather station and season, with weather frequency pooled across 2007--2025.
- Mean wind speed (`f`) is primary; wind gust (`fg`) from the observation
  matched to the accident time is secondary.
- Results describe associations and are not causal estimates.
