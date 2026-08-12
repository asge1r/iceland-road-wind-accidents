# Analysis-ready inputs

These five CSV files are the only versioned data inputs used by
`python -m src.run_analysis`. They are compact derivatives of local, unchanged
raw deliveries. `src.export_analysis_data` documents and regenerates them from
the local processed caches; it is not needed by a person who only wants to run
the analysis and figures.

| File | Unit | Role |
|---|---|---|
| `accidents.csv` | One rural injury accident | Accident O/E calculation. |
| `weather_station_frequency.csv` | Weather station, year, season, wind variable and bin | 10-minute wind-frequency denominator. |
| `annual_traffic.csv` | Road section and year | Published ADU/SDU/VDU context. |
| `daily_counter_wind.csv` | Counter, traffic period and mean-wind bin | Daily traffic observed/expected and counter bootstrap. |
| `road_wind.csv` | Wind variable and bin | Traffic-adjusted road-wind sensitivity. |

They contain no raw 10-minute observations, original daily PDF records, or
personal-level vehicle records. Intermediate calculation caches are recreated
locally under `data/cache/` and are not version controlled.
