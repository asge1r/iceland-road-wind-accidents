---
output:
  pdf_document: default
  html_document: default
---
# Analysis pipeline

Run commands from the project root. Raw files are never altered. Every output
under `data/processed/` and `reports/` is reproducible and is deliberately
excluded from Git. Detailed source and variable documentation is in `docs/`.

| Step | Script | Main input | Main output | Purpose |
|---|---|---|---|---|
| Prepare accidents | `src.accidents.prepare_accidents` | `raw/accidents/` | `processed/accidents/all_accidents_enriched.parquet` | Preserve all valid accidents, attach source road link and rural/urban classification. |
| Clean weather | `src.weather.clean_weather` | `raw/weather/weather_10min_raw.parquet` | `processed/weather/weather_10min_clean.parquet` | Keep valid wind; exclude `f > 40`, `fg > 75` and verified frozen all-zero runs. |
| Annual traffic | `src.traffic.prepare_annual_traffic` | `raw/traffic/annual/` | `processed/traffic/annual_road_section_exposure.csv` | Standardise ÁDU, SDU, VDU, Bst and Est. |
| Extract daily traffic | `src.traffic.extract_daily_traffic` | `raw/traffic/daily_pdf/` | `processed/traffic/daily_counts.parquet` | Extract PDF counts and sum direction/lane channels at each physical counter. |
| Locate daily counters | `src.traffic.locate_daily_counters` | daily counts, official road data | `processed/traffic/daily_traffic.parquet` | Interpolate PDF `stöð` along road geometry, retain method and uncertainty. |
| Daily weather | `src.analysis.analyze_daily_traffic` | daily traffic, clean weather, stations | `processed/traffic/daily_traffic_weather.parquet` | Pair each counter-day with the nearest usable weather station within 20 km and calculate 10:00–21:59 weather. |
| Daily wind response | `src.analysis.build_daily_traffic_wind_analysis` | daily traffic/weather, annual traffic | `processed/traffic/daily_traffic_wind_response.parquet` | Calculate observed/expected daily traffic by daytime mean-wind bin. |
| Counter availability | `src.analysis.analyze_daily_counter_availability` | daily weather cache, daily traffic | `processed/traffic/daily_counter_availability.parquet` | Test whether counter records are disproportionately missing in high wind. |
| Accident O/E | `src.analysis.calculate_wind_risk` | accident/weather and station-frequency data | `processed/accidents/oe_station_period_bins.parquet` | Create frequency-adjusted accident O/E inputs. |
| Results | `src.analysis.create_wind_risk_report`, `src.figures.*` | processed analysis data | `reports/main/` | Create only thesis figures and small readable tables. |

## Traffic-period names

- `VDU`: December--March.
- `SDU`: June--September.
- `VHDU`: April--May and October--November. Its daily volume is a transparent
  ADU/SDU/VDU residual, not an official published traffic measure.

## Daily-counter location rule

Daily PDF `stöð` is treated as a metre station along the reported road section.
The current implementation validates PDF `stöð` against that year's Bst/Est and
interpolates the point along the registered road-section geometry. It retains
`location_method`, `location_is_estimated` and uncertainty fields. The next
refactoring step adds official 20 m road-station points as the preferred
independent location source and leaves geometry interpolation as the fallback.
