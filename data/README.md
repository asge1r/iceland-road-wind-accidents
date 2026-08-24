# Local data map

The repository contains code and documentation, not authorised data. Put source
deliveries in `data/raw/`; do not edit them after receipt. `src.prepare` writes
temporary files to `data/processed/` and the named, readable analysis inputs to
`data/analysis/`.

## Required source files

| Source family | Required local path | Used by |
|---|---|---|
| Accident register | `raw/accidents/accidents_2007_2024.txt`; `accidents_2025.txt`; `road_links_2007_2025.txt`; `vehicles_2007_2024.txt`; `vehicles_2025.txt` | `src.accidents.build` |
| Urban boundaries | `raw/accidents/urban_boundaries_2020_2024.geojson` | `src.accidents.build` |
| Ten-minute weather | `raw/weather/weather_10min_raw.parquet` | `src.weather.clean` |
| Station reference | `raw/weather/stations.csv` | Weather matching and frequency scripts |
| Annual traffic | `raw/traffic/annual/*.xls` and `*.xlsx` | `src.traffic.annual` |
| Road-section midpoints | `raw/traffic/reference/road_section_midpoints.csv` | Annual-traffic preparation |
| Daily traffic, optional | `raw/traffic/daily_pdf/*.pdf` | Daily-counter preparation |
| Road geometry, optional | `raw/traffic/reference/roads.geojson` | Daily-counter locations |

`src.traffic.download_roads` obtains the public `roads.geojson` reference from
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
`src.analyze` skips the optional daily-counter result automatically.

## What to inspect

Use `data/analysis/` for normal work:

- `accidents.csv` and `weather_frequency.csv` for the primary O/E result;
- `rate_model.csv` and `traffic_rate_summary.csv` for annual-traffic results;
- `daily_traffic.csv` and `daily.txt` for the optional daily-counter result;
- `manifest.csv` for each file's source and columns.

The large weather and road-period Parquet files in `processed/` are only
temporary preparation material. They are not read by `src.analyze`.
