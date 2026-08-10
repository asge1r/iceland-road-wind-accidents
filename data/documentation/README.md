# Data Files

Files under `data/raw/{accidents,weather,traffic}/` are unchanged sources.
Canonical analysis inputs are grouped under the same three names in
`data/processed/`. Readable tables and figures belong under `reports/`.

| File | Unit of observation | Coverage | Purpose |
|---|---|---|---|
| `processed/accidents/rural_injury_accidents.parquet` | One rural injury accident | 2007-2024 | Master accident table for analyses A and B |
| `processed/accidents/accidents.csv` | One rural injury accident | 2007-2024 | Readable export of the master accident table |
| `processed/accidents/oe_station_period_bins.parquet` | Station-year-season-wind bin | 2007-2024 | O/E denominator and counts for analysis A |
| `processed/weather/weather_10min_clean.parquet` | Station and 10-minute timestamp | 2007-2025 | Clean wind and temperature observations |
| `processed/traffic/annual_road_section_exposure.csv` | Road section and year | 2000-2025 | ADU, SDU, VDU, length and vehicle-kilometres |
| `processed/traffic/daily_counts.parquet` | Physical counter site and date | 2019-2024 | Daily PDF counts with direction/lane channels summed |
| `processed/traffic/daily_locations.csv` | Physical counter site and year | 2019-2024 | Official or estimated location and its quality fields |
| `processed/traffic/daily_traffic.parquet` | Physical counter site and date | 2019-2024 | Canonical join of daily counts and locations |
| `processed/traffic/daily_traffic_weather.parquet` | Physical counter site and date | 2019-2024 | Canonical daily traffic table with matched daytime weather |
| `processed/traffic/road_section_wind_panel_2007_2024.parquet` | Section-year-period-variable-bin | 2007-2024 | Canonical large table for analysis B |

The daily counter file has one row per physical counter site and date. Separate
PDF `fastnr` lane/direction channels have already been summed; `source_fastnr`
and `directional_channels` preserve that provenance. Distinct sites on the same
road section remain separate. Official coordinates are used for conservative
matches, otherwise the road-section midpoint is included and explicitly marked
by `location_is_estimated`.

There are no daily PDF traffic data for 2025 in the project. Annual traffic and
accident source files for 2025 do not extend the daily traffic series.

The analysis period in the thesis is 2007-2024. Raw 2025 files are retained
only when they are original source material and are not silently mixed into the
analysis-ready files.
