# Wind and Rural Road Accidents

This project evaluates whether rural injury accidents are disproportionately
common in high winds. The primary result is a wind-frequency-standardized
observed/expected curve with weather-station-clustered bootstrap confidence
intervals.

## Repository scope

This GitHub repository contains the analysis code, documentation, thesis draft,
and the small tables and figures needed to inspect the reported results. Raw
data, processed data, canonical analysis CSV files, and working diagnostics
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
- `reports/main/`: supervisor-ready and thesis-ready outputs.
- `reports/thesis/`: the current English thesis draft.

## Working data

- `data/raw/weather/weather_10min_raw.parquet`: raw continuous 10-minute weather observations.
- `data/processed/weather/weather.parquet` is the only very large
  temporary file: the 211.5 million cleaned 10-minute observations. It is used
  while creating the CSV frequency table, never by `src.analyze`.
- `data/analysis/accidents.csv` and `weather_frequency.csv` are the complete
  inputs to the primary O/E analysis.
- `data/analysis/conditional_poisson_input.csv` is the compact, positive-exposure input to the
  within-road/year/period rate model.
- `data/analysis/traffic_exposure_full.csv` is an 18-row exposure table for the
  descriptive accidents-per-vehicle-km result.
- `data/analysis/daily_traffic.csv` and `daily_counter_locations.csv` are the
  compact inputs for the sustained-wind and allocated daily-counter analyses.
- `reports/main/figures/conditional_poisson_rate_ratio_by_wind.png`: estimated
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

## Supervisor reproduction checklist

Use this short sequence when reviewing the project locally:

1. Confirm that the authorised source files are present in the locations listed
   in `data/README.md`; preparation does not alter files in `data/raw/`.
2. Run `.venv/bin/python -m src.prepare --stage prepare` to rebuild the
   processed layer and the documented CSV files in `data/analysis/`.
3. Inspect `data/analysis/manifest.csv` and the ten canonical data CSVs. These
   are the only data inputs used by routine analysis scripts.
4. Run `.venv/bin/python -m src.analyze` to regenerate the retained result
   tables and figures.
5. Run `.venv/bin/python -m src.validate` and inspect
   `reports/main/tables/final_analysis_validation.md` for the fixed sample,
   coverage, primary estimate, and supporting estimates.
6. From `reports/thesis/`, run `pdflatex -interaction=nonstopmode
   -halt-on-error draft_en.tex` twice to rebuild `draft_en.pdf`.
7. Use `docs/pipeline.md` or the two four-column thesis pipeline tables to trace
   every reported output back to its script and exact input files.

The headline audit trail is: 6,414 rural injury accidents; 6,192 primary wind
matches; mean-wind O/E as the primary result; case-crossover and estimated
vehicle-kilometre models as supporting analyses; daily counters as a separate
traffic diagnostic.

## Supervisor meeting walkthrough

Use 20--25 minutes and keep the discussion tied to inspectable outputs:

1. **Question and sample (3 minutes):** state the primary research question,
   then show the 6,414-to-6,192 selection in Figure 3.1 and Table 4.1.
2. **Data and pipeline (5 minutes):** show the two four-column pipeline tables,
   `data/analysis/manifest.csv`, and one compact analysis CSV. Emphasise that
   routine analysis does not read the large weather Parquet file.
3. **Primary result (5 minutes):** show Figure 4.2 and explain the 20--25 m/s
   estimate, its clustered interval, and why the sparse ≥25 m/s interval is not
   the main conclusion.
4. **Independent checks (5 minutes):** show the 10/20/30 km sensitivity and the
   compact evidence table. Keep case-crossover, estimated vehicle-kilometres,
   and daily traffic distinct because they estimate different quantities.
5. **Limitations and decisions (4 minutes):** state plainly that complete
   hourly traffic and road-surface conditions are unavailable, counter
   locations are geometry-interpolated estimates, and the analysis is
   associative rather than causal.
6. **Ask for decisions (3 minutes):** confirm whether the current balance of
   one primary result and three supporting checks is appropriate, which
   appendix figures should remain, and whether the title-page examiner and
   committee fields must be completed before submission.

Before submission, confirm the examiner, committee, ISBN/printing requirements,
month, degree title, faculty wording, and repository-access statement with the
University of Iceland template owner. These administrative fields are not
invented in the draft.

## Primary Assumptions

- Rural injury accidents, 2007-2025.
- Nearest valid 10-minute weather observation within 20 km.
- Expected accidents standardized by weather station and season, with weather frequency pooled across 2007--2025.
- Mean wind speed (`f`) is primary; wind gust (`fg`) from the observation
  matched to the accident time is secondary.
- Results describe associations and are not causal estimates.
