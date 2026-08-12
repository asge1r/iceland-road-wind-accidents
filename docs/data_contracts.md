# Canonical data contracts

The versioned analysis inputs are the five files in `data/analysis/`. Each is
flat, has one stated unit, and contains no raw observations. `src.run_analysis`
uses only these files (plus calculation caches it creates locally). The detailed
files in `processed/{accidents,weather,traffic}/` are local pipeline caches.

| Dataset | Unit and purpose | Required fields used downstream |
|---|---|---|
| `accidents.csv` | One rural injury accident with matched weather. | `nid`, timestamp, injury code, accident type, road section, surface, weather station/distance/time difference, `f`, `fg`, `t` |
| `weather_station_frequency.csv` | Weather station, year, season, wind variable and interval. | station, year, season, variable, bin and 10-minute measurement frequency |
| `annual_traffic.csv` | One road section and calendar year. | year, road section, section length, `adu`, `sdu`, `vdu`, vehicle-km |
| `daily_counter_wind.csv` | Counter, traffic period and mean-wind interval. | counter, wind bin, number of days, summed observed and expected daytime traffic |
| `road_wind.csv` | Wind variable and interval for the traffic-adjusted sensitivity. | wind bin, estimated vehicle-km, injury counts, weather-only and traffic-adjusted O/E |

## Derivative outputs

`data/processed/daily.txt` is a short tab-separated inspection table, retained for easy
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
