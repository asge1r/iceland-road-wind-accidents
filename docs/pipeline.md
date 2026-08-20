# Data pipeline

## Purpose and principles

This document records the route from an authorised source delivery to a
statistical result. It distinguishes three data layers:

1. `data/raw/` contains unchanged source deliveries. No script writes to it.
2. `data/processed/` and `data/cache/` contain large, reproducible local
   intermediates needed to avoid repeatedly scanning raw weather data.
3. `data/analysis/` contains the compact canonical datasets for inspection,
   analysis and supervisor review.

The core O/E scripts read the canonical accident and weather-frequency files.
The daily-traffic script reads the canonical daily and annual traffic files.
Large `processed/` tables remain necessary only to prepare these files and to
build the road-section annual-traffic rate comparison. No cache file is
edited by hand.

`src/traffic/build_road_period_cache.py` is the active entry point for the
road-period cache. Older diagnostics and helper routines are retained under
`src/legacy/` for traceability and are not part of the ordinary pipeline.

## Source identifiers

The source websites and the data delivered from each source are documented in
[`data.md`](data.md). The short identifiers below are used in the pipeline
table.

| Identifier | Source | Data used |
|---|---|---|
| ACC | Icelandic Transport Authority accident register | Accident time, coordinates, injury code, accident type and road link. |
| IMO | Icelandic Met Office 10-minute observations | Station, timestamp, mean wind (`f`), maximum gust (`fg`) and temperature (`t`). |
| IRCA-annual | Icelandic Road and Coastal Administration annual workbooks | Road section, length, ADU, SDU and VDU. |
| IRCA-daily | Icelandic Road and Coastal Administration daily-counter PDFs | Date, road section, reported station and daily direction/lane count. |
| IRCA-roads | Icelandic Road and Coastal Administration MapServer | Official road geometry and road-station ranges. |
| SI | Statistics Iceland urban-area boundaries | Urban polygons used for the rural/urban classification. |

## Preparation pipeline

| Stage | Script | Input | Output | Why this step is needed |
|---|---|---|---|---|
| Accident preparation | `src.accidents.build` | ACC accident and road-link deliveries; SI urban boundaries | `processed/accidents/all_accidents_enriched.parquet` and `rural_injury_accidents_base.parquet` | Standardises names and types, creates coordinates and time, joins supplied road links, and defines the rural injury sample without deleting the wider accident record. |
| Wind cleaning | `src.weather.clean` | IMO raw 10-minute weather | `processed/weather/weather_10min_clean.parquet`; annual audit CSVs | Applies the fixed quality rules without clipping or imputing wind. The audit reports each exclusion. |
| Annual traffic | `src.traffic.annual` | IRCA-annual workbooks | `processed/traffic/annual_road_section_exposure.csv` | Standardises the road-section ADU, SDU and VDU values used in the annual-traffic comparison. |
| Accident-weather match | `src.accidents.match_weather` | Prepared accidents, clean weather, station metadata | `processed/accidents/rural_injury_accidents.parquet` | Matches each eligible accident to the nearest valid 10-minute weather observation and records distance and time difference. |
| Wind-frequency denominator | `src.weather.frequency` | Clean weather and station metadata | `processed/weather/wind_frequency_station_year_season.parquet` | Counts wind intervals within station, calendar year and season: the denominator for the O/E calculation. |
| Road-period cache | `src.traffic.build_road_period_cache` | Annual traffic, injury-accident data, clean weather, stations and road references | `processed/traffic/road_section_wind_panel_2007_2025.parquet` | Creates the road-section × year × traffic-period × wind-bin exposure cache for every annual-traffic road section with a qualifying weather station. Road-surface history is not used. |
| Rate-accident weather match | `src.traffic.match_rate_accident_weather` | Road-period cache, rural injury accidents, clean weather and station metadata | `processed/accidents/rate_accidents_weather.parquet` | Re-matches each retained accident to the exact station used to allocate vehicle-kilometres for its road section, year and traffic period. Requires that this shared station is within 20 km of the accident. |
| Daily counter preparation* | `src.traffic.daily`, `src.traffic.download_roads`, `src.traffic.locate_counters`, `src.analysis.match_daily_weather` | IRCA-daily PDFs, IRCA-roads geometry, clean weather and station metadata | `processed/traffic/daily_traffic_weather.parquet` | Sums direction/lane channels to a 24-hour counter-day total, locates a counter from its reported road station, and joins daytime weather. |
| Canonical export | `src.export_tables` | Prepared local cache files above | `analysis/accidents.csv`, `weather_frequency.csv`, `stations.csv`, `annual_traffic.csv`, `daily_traffic.csv`, `daily.txt`, `manifest.csv` | Produces the small, stable files used for routine inspection and the core analysis steps. |

*The daily-counter workflow covers 2019–2024 and is a travel-demand description, not part of the primary O/E result.

Run the preparation steps from the repository root:

```bash
python -m src.prepare --stage prepare
python -m src.prepare --stage prepare --daily-traffic
```

The second command is needed only after the six local daily-PDF files have
been supplied. `src.prepare` runs `src.export_tables` as its final step.
Without the PDFs, run `python -m src.analyze --skip-daily-traffic` to rebuild
the primary O/E and annual-traffic results without the daily-counter figure.

## Statistical and reporting pipeline

| Stage | Script | Canonical input | Output | Why this step is needed |
|---|---|---|---|---|
| Frequency-standardised O/E | `src.analysis.build_oe` | `analysis/accidents.csv`, `analysis/weather_frequency.csv` | Detailed O/E calculation and coverage tables | Within each station-year-season group, compares observed accidents in each wind interval with the count expected from local wind frequency. Mean wind `f` in 5 m/s bins is the primary exposure; gust `fg` and gust factor `fg/f` are secondary. |
| Main O/E report | `src.analysis.report_oe` | O/E calculation output | Main mean-wind figure and table; supporting gust, gust-factor, season and vehicle-group figures | Produces a readable presentation of observed, expected and O/E values, with station-clustered uncertainty. |
| Estimated crash rate | `src.analysis.estimated_crash_rate` | Road-period exposure cache and rate-accident weather match | Estimated injury-accident rate by 5 m/s mean-wind interval | Estimates vehicle-km from road length, period-specific annual traffic and the local frequency of each wind interval. Each retained accident uses the same weather station as its exposure stratum. |
| Daily-traffic description* | `src.analysis.daily_traffic_response` and `src.analysis.daily_traffic_wind_weights` | `analysis/daily_traffic.csv`, `analysis/annual_traffic.csv` | Daily traffic-by-wind figure and 5 m/s traffic-allocation factors | Examines whether traffic volume changes with daytime mean wind. The factors describe, but do not directly measure, traffic at each 10-minute wind observation. |
| Stratified crash-rate model | `src.analysis.stratified_crash_rate` | Road-period cache, rate-accident weather match and daily traffic factors | Within-stratum rate-ratio table and figure | Conditional Poisson model compares wind intervals within the same road section, year and traffic period, with log estimated vehicle-km as offset. It reports a time-proportional allocation and a counter-informed allocation. |
| Pooled traffic-adjusted O/E (working check) | `src.analysis.traffic_adjusted_observed_expected` | Road-period cache, rate-accident weather match and daily traffic factors | Working O/E figure and table | Shows the intuitive observed/expected comparison after allocating estimated vehicle-km across wind intervals. It is not a principal result because it pools road sections, years and traffic periods. |
| Quality validation | `src.validate` | Canonical analysis data and final result tables | `reports/main/tables/final_analysis_validation.md` | Checks that fixed sample counts and principal O/E totals have not changed silently. |

The primary thesis result is the 2007–2025 rural injury-accident O/E analysis
using mean wind speed `f`, a 20 km station-distance limit and a maximum
five-minute time difference. Gust results, annual traffic and daily traffic
are reported as secondary analyses.

## Traffic periods

- `VDU`: December–March.
- `SDU`: June–September.
- `VHDU`: April–May and October–November, derived from ADU, SDU and VDU.
