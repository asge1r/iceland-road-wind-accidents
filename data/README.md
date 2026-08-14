# Local data map

This repository intentionally does not include raw or processed data. To run
the pipeline after cloning, obtain the authorised source deliveries and place
them in the paths below. No script alters a file in `data/raw/`; generated
files are written under `data/processed/` or `archive/` and are ignored by Git.

`src.traffic.download_roads` is the exception to manual retrieval: it
downloads the public Road Administration MapServer/6 reference file to
`raw/traffic/reference/roads.geojson`. It is then used to locate daily PDF
counters from their reported `stöð` value.

`raw/` contains unchanged sources. `processed/` contains only canonical analysis
inputs or expensive reusable caches. Readable tables and figures are under
`reports/`; superseded intermediates are recoverable under
`archive/data_legacy_2026-07-22/`.

## Analysis A: frequency-standardized O/E

Primary inputs:

- `processed/accidents/rural_injury_accidents.parquet`
- `processed/weather/wind_frequency_station_year_season.parquet`
- `processed/accidents/oe_station_period_bins.parquet`

The primary result standardizes within weather station, calendar year, and
meteorological season. It does not use traffic. The separately labelled traffic
sensitivity uses annual/seasonal road-section exposure from Analysis B. Daily
PDF traffic is a further restricted 2019-2024 sensitivity only.

## Analysis B: road-section table and figures

Primary inputs/output:

- `processed/traffic/annual_road_section_exposure.csv`
- `processed/weather/wind_frequency_road_period_2007_2024.parquet`
- `processed/traffic/road_section_wind_panel_2007_2024.parquet`

The panel unit is road section, year, official traffic period, wind variable,
and wind bin. `f` and `fg` are separate rows. Readable mean-wind and gust tables,
traffic-adjusted rates, and figures are generated under `reports/` from this
same panel.

## 2025 status

Raw 2025 accident, injury, and vehicle files are retained in `raw/accidents/`.
The current canonical accident tables still end in 2024. Do not label an output
2007-2025 until the 2025 files have passed the same coordinate, rural/urban,
road, surface, severity, and weather matching pipeline.

## Local rebuild order

From the project root, run:

```bash
.venv/bin/python -m src.prepare --stage prepare
.venv/bin/python -m src.analyze
```

The first command needs the accident, weather, annual-traffic and station
source deliveries. The daily-PDF workflow is optional and deliberately
separate because those PDFs are not available in every local copy:

```bash
.venv/bin/python -m src.prepare --stage prepare --daily-traffic
```

Git supplies the documented methods; each authorised user supplies the data
locally and regenerates the processed tables and figures.
