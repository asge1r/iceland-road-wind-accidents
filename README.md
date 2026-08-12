# Wind and Rural Road Accidents

This project evaluates whether rural injury accidents are disproportionately
common in high winds. The primary result is a wind-frequency-standardized
observed/expected curve with weather-station-clustered bootstrap confidence
intervals.

## Repository scope

This GitHub repository contains code, documentation, and five compact
analysis-ready CSV inputs under `data/analysis/`. Raw data, large processed
caches and generated figures remain local and are excluded by `.gitignore`.
Someone with authorised source files can recreate the analysis inputs through
[`pipeline.md`](pipeline.md). The five input contracts are defined in
[`data/analysis/README.md`](data/analysis/README.md).

## Directory structure

- `data/raw/{accidents,weather,traffic}/`: unchanged local source and reference data.
- `data/processed/{accidents,weather,traffic}/`: local, non-versioned preparation caches.
- `data/analysis/`: five compact versioned inputs used by every active result script.
- `docs/`: source inventory, variables and fixed analysis rules.
- `archive/`: local diagnostics and superseded material; not version controlled.
- `src/prepare/`: raw-data cleaning and matching; run only with local source deliveries.
- `src/analysis/`: compact-data results code; this is what a clone runs.
- `src/legacy/`: retained prior/exploratory scripts, excluded from the active workflow.
- `reports/main/`: supervisor-ready and thesis-ready outputs.
- `reports/thesis/`: the current English thesis draft.

## Active analysis data

The five inputs and their units are documented in
[`data/analysis/README.md`](data/analysis/README.md). They are compact
aggregations of the local raw-data workflow, not copied result tables.

## Rebuild the results

After cloning, create a Python environment and install the project dependencies.

```bash
.venv/bin/python -m src.run_analysis
```

This command works directly after cloning and uses only `data/analysis/`. To
rebuild the five analysis inputs from authorised raw files and then recreate
results, run:

```bash
.venv/bin/python -m src.run_prepare --stage all
```

See `data/README.md` for the required local source files and `docs/` for source
and variable definitions.

A clone already contains the five analysis inputs and can redraw results. With
authorised raw deliveries it can also rebuild those inputs. Three broad data
families alone (accidents, weather and traffic) are not enough: the accident
work also needs supplied road links and urban boundaries, while daily traffic
needs the six PDFs and station metadata.

## Primary Assumptions

- Rural injury accidents, 2007-2024.
- Nearest valid 10-minute weather observation within 20 km.
- Expected accidents standardized by weather station, calendar year, and season.
- Maximum wind gust (`fg`) is the primary exposure.
- Results describe associations and are not causal estimates.
