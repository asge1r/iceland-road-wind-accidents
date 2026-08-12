# Canonical data contracts

These are the five small working datasets intended for inspection and ordinary
analysis. Each is flat, one row has one stated unit, and it contains no
provenance or intermediate matching columns. The detailed files in
``processed/{accidents,weather,traffic}/`` are reproducible pipeline caches.

| Dataset | Unit and purpose | Required fields used downstream |
|---|---|---|
| `accidents.csv` | One rural injury accident with matched weather; main accident working table. | `nid`, `timestamp`, year/time, coordinates, `meidsli`, `severity`, accident type, rural/urban, road section, surface, weather station/distance, `f`, `fg`, `t` |
| `weather.parquet` | One weather station and valid 10-minute observation. | `station`, `time`, `f`, `fg`, `t` |
| `stations.csv` | One weather station. | `station`, `name`, `lat`, `lon`, `start`, `ending` |
| `annual_traffic.csv` | One road section and calendar year. | `year`, `road_section`, section length, `adu`, `sdu`, `vdu`, vehicle-km |
| `daily_traffic.csv` | One physical counter and date with daytime weather. | date, year, counter site, road section, PDF `stöð`, traffic volume, coordinates, location method, weather station/distance, daytime `f` and `fg`, month and weekday |

## Derivative outputs

`daily.txt` is a short tab-separated inspection table, retained for easy
inspection and compatibility with the earlier Drive work. Its only columns are
date, road section, PDF `stöð`, daily traffic, coordinates, paired weather
station/distance and daytime `f`/`fg`. It is not a sixth dataset and no script
reads it. `wind_frequency_station_year_season.parquet`,
`road_section_wind_panel_2007_2024.parquet`, `oe_station_period_bins.parquet`,
and `daily_traffic_wind_response.parquet` are analysis-specific derivatives.

## Location quality-control contract

`daily_counter_station_validation.csv` is a validation output. It compares
coordinates calculated from PDF `stöð` and official MapServer/6 geometry with
the nearest official MapServer/4 20 m point on the same road section. It never
overwrites the PDF-`stöð` location rule.
