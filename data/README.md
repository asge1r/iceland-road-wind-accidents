# Local data map

This repository includes `analysis/`, the five compact inputs needed to run
results after cloning. Raw and processed data remain local. To rebuild analysis
inputs, obtain authorised source deliveries and place them in the paths below.
No script alters a file in `data/raw/`.

`src.prepare.traffic.download_road_geometry` is the exception to manual retrieval: it
downloads the public Road Administration MapServer/6 reference file to
`raw/traffic/reference/roads.geojson`. It is then used to locate daily PDF
counters from their reported `stöð` value.

`raw/` contains unchanged sources. `processed/` contains expensive local
preparation caches. The compact versioned inputs are under `analysis/`.
Readable tables and figures are under
`reports/`; superseded intermediates are recoverable under
`archive/data_legacy_2026-07-22/`.

## Analysis A: frequency-standardized O/E

Active inputs: `analysis/accidents.csv` and
`analysis/weather_station_frequency.csv`.

The primary result standardizes within weather station, calendar year, and
meteorological season. It does not use traffic. The separately labelled traffic
sensitivity uses annual/seasonal road-section exposure from Analysis B. Daily
PDF traffic is a further restricted 2019-2024 sensitivity only.

## Analysis B: road-section table and figures

Active inputs: `analysis/annual_traffic.csv`, `analysis/road_wind.csv` and
`analysis/daily_counter_wind.csv`.

The panel unit is road section, year, official traffic period, wind variable,
and wind bin. `f` and `fg` are separate rows. Readable mean-wind and gust tables,
traffic-adjusted rates, and figures are generated under `reports/` from this
same panel.

## 2025 status

Raw 2025 accident, injury, and vehicle files are retained in `raw/accidents/`.
The current canonical accident tables still end in 2024. Do not label an output
2007-2025 until the 2025 files have passed the same coordinate, rural/urban,
road, surface, severity, and weather matching pipeline.
