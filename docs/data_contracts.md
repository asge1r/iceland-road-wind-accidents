# Canonical data contracts

Only these five processed datasets are inputs to the active analyses. All other
files are raw inputs, reusable caches, diagnostics or display outputs.

| Dataset | Unit and purpose | Required fields used downstream |
|---|---|---|
| `accidents/all_accidents_enriched.parquet` | One valid registered accident; full source population. | `nid`, `timestamp`, `meidsli`, coordinates, `tegohapps`, `flokkur2`, `urban_rural`, `registered_road_section` |
| `accidents/rural_injury_accidents.parquet` | One rural accident with injuries and matched wind; main accident-analysis input. | `nid`, `timestamp`, `meidsli`, weather station ID/distance/time difference, `f`, `fg`, `t`, `registered_road_section` |
| `weather/weather_10min_clean.parquet` | One weather station and 10-minute observation after quality control. | `station`, `time`, `f`, `fg`, `t` |
| `traffic/annual_road_section_exposure.csv` | One road section and calendar year; annual traffic context. | `year`, `road_section`, Bst, Est, section length, `adu`, `sdu`, `vdu`, vehicle-km |
| `traffic/daily_traffic_weather.parquet` | One physical counter and date; daily traffic/wind sensitivity input. | date, year, counter site, road section, `station_id`, summed traffic, coordinates, location method, weather station/distance, `f_daytime_mean` |

## Derivative outputs

`wind_frequency_station_year_season.parquet`, `road_section_wind_panel_2007_2024.parquet`,
`oe_station_period_bins.parquet`, and `daily_traffic_wind_response.parquet` are
analysis-specific derivatives. They are recreated from the five contracts; they
are not alternative source datasets.

## Location quality-control contract

`daily_counter_station_validation.csv` is a validation output. It compares
coordinates calculated from PDF `stöð` and official MapServer/6 geometry with
the nearest official MapServer/4 20 m point on the same road section. It never
overwrites the PDF-`stöð` location rule.
