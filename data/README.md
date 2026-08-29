# Local data map

The repository contains code and documentation, not authorised data. Put source
deliveries in `data/raw/`; do not edit them after receipt. `src/prepare.py` writes
intermediate preparation files to `data/processed/` and the named, readable analysis inputs to
`data/analysis/`.

## Required source files

| Source family | Required local path | Used by |
|---|---|---|
| Accident register | `raw/accidents/accidents_2007_2024.txt`; `accidents_2025.txt`; `road_links_2007_2025.csv`; `vehicles_2007_2024.txt`; `vehicles_2025.txt` | `src/accidents/build.py` |
| Urban boundaries | `raw/accidents/urban_boundaries_2020_2024.geojson` | `src/accidents/build.py` |
| Ten-minute weather | `raw/weather/weather_10min_raw.parquet` | `src/weather/clean.py` |
| Station reference | `raw/weather/stations.csv` | Weather and traffic matching scripts |
| Annual traffic | `raw/traffic/annual/*.xls` and `*.xlsx` | `src/traffic/annual.py` |
| Road-section midpoints | `raw/traffic/reference/road_section_midpoints.csv` | `src/traffic/build_road_period.py` |
| Road geometry fallback | `raw/traffic/reference/road_sections.parquet` | `src/traffic/build_road_period.py`, only when a required midpoint is absent |
| Daily traffic, optional | `raw/traffic/daily_pdf/*.pdf` | Daily-counter preparation |
| Road geometry, optional | `raw/traffic/reference/roads.geojson` | Daily-counter locations |

`src/traffic/download_roads.py` obtains the public `roads.geojson` reference from
the Vegagerðin MapServer. It is the one documented exception to manual source
placement.

## Rebuild commands

```bash
.venv/bin/python -m src.prepare --stage prepare
.venv/bin/python -m src.analyze
```

Add daily traffic only when its PDF deliveries are present:

```bash
.venv/bin/python -m src.prepare --stage prepare --daily-traffic
```

The first command creates the CSV files described in
[`../docs/pipeline.md`](../docs/pipeline.md). The second command reads those
CSV files and creates tables and figures. If daily PDFs are absent,
`src/analyze.py` skips the optional daily-counter result automatically.

## What to inspect

Use `data/analysis/` for normal work:

- `accidents.csv`, `accident_conditions.csv`, and `weather_frequency.csv` for O/E results;
- `case_control.csv` for the time-stratified conditional logistic models;
- `conditional_poisson_input.csv` and `traffic_exposure_full.csv` for annual-traffic results;
- `daily_traffic.csv` for the sustained-wind and allocated daily-counter results;
- `daily_counter_locations.csv` for selected-counter rate analyses;
- `manifest.csv` for each file's record count, columns and description.

The large clean-weather Parquet file and optional daily matching Parquet files
in `processed/` are only intermediate preparation material. They are not read
by `src/analyze.py`.
