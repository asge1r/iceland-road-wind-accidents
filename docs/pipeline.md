# Data and analysis pipeline

This is the active workflow. It separates conversion of large source deliveries
from routine analysis. Routine analysis reads only named CSV files in
`data/analysis/`.

## Data layers

| Layer | Purpose | Used by `src.analyze`? |
|---|---|---:|
| `data/raw/` | Unchanged authorised data deliveries and downloaded references. | No |
| `data/processed/` | Temporary local working files used only to transform source data. The 10-minute weather record contains 226.6 million rows, so this layer may use Parquet for efficient local processing. | No |
| `data/analysis/` | Named, inspectable CSV inputs for all ordinary analysis. | Yes |
| `reports/` | Generated tables and figures. | Output only |

`data/processed/` is not a second analysis database. It can be recreated from
`data/raw/` by rerunning `src.prepare`.

## Input rule

There are only two kinds of active script:

1. **Preparation scripts** listed in the first table below may read raw files
   or efficient local Parquet working files because they create the compact
   CSV tables.
2. **Analysis and figure scripts** run by `src.analyze` read only CSV files in
   `data/analysis/` or small CSV tables produced earlier in the analysis.

Two scripts are deliberately outside the routine workflow:
`src.traffic.validate_counters` checks interpolated counter positions against
the official MapServer points, and `src.traffic.download_roads` downloads that
official reference. They are source-level quality control, not analysis.

## Source identifiers

| ID | Source website or delivery | Information used |
|---|---|---|
| ACC | Samgöngustofa accident-register delivery | Accident ID, date/time, coordinates, injury code, accident type, road link, and involved vehicles. |
| IMO | Icelandic Meteorological Office ten-minute observations | Station ID, time, mean wind `f`, maximum gust `fg`, and temperature `t`. |
| VGD-A | Vegagerðin annual-traffic workbooks | Road-section length, ADU, SDU, and VDU. |
| VGD-D | Vegagerðin daily-counter PDF files | Counter ID, date, direction/lane channel, and daily count. |
| VGD-R | Vegagerðin MapServer | Road geometry and official road-station positions used to locate counters. |
| SI | Statistics Iceland urban-area polygons | Urban/rural classification of accident coordinates. |

**IRCA** was an internal abbreviation for *Icelandic Road and Coastal
Administration*, the English name for Vegagerðin. It is removed from this
pipeline because VGD-A, VGD-D, and VGD-R state exactly which Vegagerðin source
is meant.

## Preparation scripts: exact inputs and outputs

`src.prepare --stage prepare` runs rows 1--7 below in that order. Rows 8--12
run only with `--daily-traffic`; row 13 then creates the analysis CSV files.
Each path is relative to the project root.

| # | Script | Exact default input files | Exact files written | Purpose |
|---:|---|---|---|---|
| 1 | `src.accidents.build` | `data/raw/accidents/accidents_2007_2024.txt`; with `--include-2025`, `data/raw/accidents/accidents_2025.txt`; `data/raw/accidents/road_links_2007_2025.txt`; `data/raw/accidents/vehicles_2007_2024.txt`; `data/raw/accidents/vehicles_2025.txt`; `data/raw/accidents/urban_boundaries_2020_2024.geojson` | `data/processed/accidents/all_accidents_enriched.parquet`; `data/processed/accidents/rural_injury_accidents_base.parquet` | One enriched record per accident ID and the pre-weather rural injury subset. |
| 2 | `src.weather.clean` | `data/raw/weather/weather_10min_raw.parquet` | `data/processed/weather/weather_10min_clean.parquet`; `archive/generated_diagnostics/weather_cleaning_by_year.csv`; `archive/generated_diagnostics/weather_station_year_coverage.csv`; `archive/generated_diagnostics/weather_frozen_zero_intervals.csv` | Applies the fixed wind-quality rules and records all exclusions. |
| 3 | `src.traffic.annual` | `data/raw/traffic/annual/*.xls` and `*.xlsx` | `data/processed/traffic/annual_road_section_exposure.csv`; `archive/generated_diagnostics/annual_traffic_notes.txt` | Standardises road section, length, ADU, SDU, and VDU. |
| 4 | `src.accidents.match_weather` | `data/processed/accidents/all_accidents_enriched.parquet`; `data/processed/weather/weather_10min_clean.parquet`; `data/raw/weather/stations.csv` | `data/processed/accidents/rural_injury_accidents.parquet`; `archive/generated_diagnostics/oe/accident_weather_coverage.csv`; `archive/generated_diagnostics/accident_weather_coverage_by_year.csv`; `archive/generated_diagnostics/accident_weather_notes.txt` | Matches every rural injury accident to the nearest valid 10-minute weather observation. |
| 5 | `src.weather.frequency` | `data/processed/weather/weather_10min_clean.parquet`; `data/raw/weather/stations.csv` | `data/processed/weather/wind_frequency_station_year_season.parquet`; `archive/generated_diagnostics/wind_frequency_readable.csv`; `archive/generated_diagnostics/wind_frequency_notes.txt`; `reports/main/tables/gust_factor_distribution.csv`; `reports/main/figures/gust_factor_distribution.png` | Counts `f`, `fg`, and gust-factor bins by station, year, and season. |
| 6 | `src.traffic.build_road_period_cache` (uses `src.traffic.road_period`) | `data/processed/traffic/annual_road_section_exposure.csv`; `data/processed/accidents/rural_injury_accidents.parquet`; `data/processed/weather/weather_10min_clean.parquet`; `data/raw/weather/stations.csv`; `data/raw/traffic/reference/road_section_midpoints.csv` | `data/processed/weather/wind_frequency_road_period_2007_2025.parquet` if absent; `data/processed/traffic/road_section_wind_panel_2007_2025.parquet` | Assigns one nearby weather station to each road-section/year/traffic-period and distributes annual traffic over wind intervals. |
| 7 | `src.traffic.match_rate_accident_weather` | `data/processed/traffic/road_section_wind_panel_2007_2025.parquet`; `data/processed/accidents/rural_injury_accidents.parquet`; `data/processed/weather/weather_10min_clean.parquet`; `data/raw/weather/stations.csv` | `data/processed/accidents/rate_accidents_weather.parquet`; `reports/working/tables/rate_accident_weather_audit.csv` | Re-matches rate-model accidents to the same station used for their road-exposure denominator. |
| 8 | `src.traffic.daily` | `data/raw/traffic/daily_pdf/*.pdf` | `data/processed/traffic/daily_counts.parquet`; `archive/generated_diagnostics/daily_traffic_channels_2019_2024.csv`; `archive/generated_diagnostics/daily_counter_metadata_2019_2024.csv`; `archive/generated_diagnostics/traffic_pdf_2019_2024_notes.txt` | Parses PDFs and sums direction/lane channels to one counter-day. |
| 9 | `src.traffic.download_roads` | Vegagerðin MapServer query | `data/raw/traffic/reference/roads.geojson` | Downloads the immutable road-geometry reference used for counter locations. |
| 10 | `src.traffic.locate_counters` | `data/processed/traffic/daily_counts.parquet`; `data/raw/traffic/reference/roads.geojson` | `data/processed/traffic/daily_traffic.parquet`; `data/processed/traffic/daily_locations.csv` | Locates the PDF counter station along the official road geometry. |
| 11 | `src.traffic.daily_weather_match` | `data/processed/traffic/daily_traffic.parquet`; `data/processed/weather/weather_10min_clean.parquet`; `data/raw/weather/stations.csv` | `data/processed/traffic/daily_weather_cache.parquet`; `data/processed/traffic/daily_traffic_weather.parquet`; `archive/generated_diagnostics/daily_traffic_coverage.csv` | Attaches one nearby valid daytime-weather record to each counter-day and records match coverage. |
| 12 | `src.traffic.daily_traffic_quality` | `data/processed/traffic/daily_traffic_weather.parquet`; `data/processed/traffic/annual_road_section_exposure.csv` | `reports/working/tables/daily_traffic_diagnostic.csv`; `archive/generated_diagnostics/daily_traffic_adu_validation.csv`; `archive/generated_diagnostics/daily_traffic_adu_summary.csv`; `archive/generated_diagnostics/daily_traffic_notes.md`; `reports/working/traffic_validation.png`; `reports/working/daily_traffic_diagnostic.png` | Checks the matched counter data against annual ADU and documents the counter sample. |
| 13 | `src.export_tables` | The outputs of rows 3--7, optional row 11, and `data/raw/weather/stations.csv` | `data/analysis/accidents.csv`; `data/analysis/weather_frequency.csv`; `data/analysis/stations.csv`; `data/analysis/annual_traffic.csv`; `data/analysis/rate_model.csv`; `data/analysis/traffic_rate_summary.csv`; `data/analysis/selection_summary.csv`; optionally `data/analysis/daily_traffic.csv` and `data/analysis/daily.txt`; plus `data/analysis/README.md` and `data/analysis/manifest.csv` | Reduces and documents all ordinary analysis inputs. |

`data/raw/weather/stations.csv` is the externally supplied station-reference
source. It is not generated by the pipeline and is retained unchanged.

## CSV files used in analysis

| File | Unit | Main content | Used by |
|---|---|---|---|
| `accidents.csv` | One rural injury accident | ID, time, injury code, accident type, vehicle count, weather-match quality, `f`, `fg`. | O/E and descriptions |
| `weather_frequency.csv` | Station × season × variable × interval | Pooled 2007–2025 wind counts and frequencies. | O/E denominator |
| `stations.csv` | One station | Station ID, name, latitude, longitude. | Inspection/reference |
| `annual_traffic.csv` | Road section × year | Length, ADU, SDU, VDU. | Inspection/reference |
| `rate_model.csv` | Road × year × traffic period × `f` interval | Vehicle-km and accident counts for strata informing the conditional Poisson model. | Rate-ratio model |
| `traffic_rate_summary.csv` | Traffic period × `f` interval | Total vehicle-km and accident counts; 18 rows. | Accident-per-km table |
| `daily_traffic.csv` | Counter × date | Daily traffic, weather-station distance, and daytime `f`/`fg`, 2019–2024. | Daily traffic result |
| `selection_summary.csv` | Dataset × selection step | Eight retained-record counts. | Selection figures |
| `oe_station_bins.csv` | Station × season × O/E scenario × interval | Derived O/E calculation rows. | O/E figures and bootstrap |

`daily.txt` is the grouped, human-readable version of `daily_traffic.csv`.
`manifest.csv` records the origin and columns of every CSV file.

## Analysis scripts: exact inputs and outputs

`src.analyze` runs the following scripts. Unlike preparation, every data input
in this table is a CSV in `data/analysis/` or a result/audit CSV produced by an
earlier row.

| # | Script | Exact files read | Exact files written |
|---:|---|---|---|
| 1 | `src.analysis.build_oe` | `data/analysis/accidents.csv`; `data/analysis/weather_frequency.csv` | `data/analysis/oe_station_bins.csv`; `archive/generated_diagnostics/oe/detailed_results.csv`; `archive/generated_diagnostics/oe/coverage.csv`; `archive/generated_diagnostics/oe/calculation_notes.txt` |
| 2 | `src.analysis.report_oe` | `data/analysis/oe_station_bins.csv`; `archive/generated_diagnostics/oe/coverage.csv`; `archive/generated_diagnostics/oe/accident_weather_coverage.csv`; `data/analysis/accidents.csv`; `archive/generated_diagnostics/weather_cleaning_by_year.csv` | `reports/main/tables/mean_wind_oe.csv`; `reports/main/tables/gust_oe.csv`; `reports/main/tables/gust_factor_oe.csv`; `reports/main/tables/weather_match_coverage.csv`; `reports/main/tables/weather_cleaning_audit.csv`; `reports/main/figures/mean_wind_oe.png`; `reports/main/figures/gust_oe.png`; `reports/main/figures/gust_factor_oe.png`; `reports/main/figures/mean_wind_by_season_oe.png`; `reports/main/figures/mean_wind_by_vehicle_group_oe.png`; `reports/main/figures/gust_by_season_oe.png`; `reports/main/figures/gust_by_vehicle_group_oe.png`; `reports/working/tables/mean_wind_subgroups.csv`; `archive/generated_diagnostics/mean_wind_risk.tex`; `archive/generated_diagnostics/gust_sensitivity.csv`; `archive/generated_diagnostics/gust_bins.csv`; `archive/generated_diagnostics/mean_wind_method.md`; `archive/generated_diagnostics/wind_gust_distribution_and_standardization.csv`; `archive/generated_diagnostics/wind_gust_distribution_and_standardization.png`; `archive/generated_diagnostics/oe/bootstrap_notes.txt` |
| 3 | `src.analysis.estimated_crash_rate` | `data/analysis/traffic_rate_summary.csv` | `reports/working/tables/estimated_crash_rate_by_wind.csv`; `reports/working/tables/estimated_crash_rate_by_wind_audit.csv`; `reports/working/figures/estimated_crash_rate_by_wind.png` |
| 4 | `src.analysis.stratified_crash_rate` | `data/analysis/rate_model.csv` | `reports/main/tables/stratified_crash_rate_ratio_by_wind.csv`; `reports/main/figures/stratified_crash_rate_ratio_by_wind.png` |
| 5 | `src.analysis.stratified_crash_rate --traffic-period official` | `data/analysis/rate_model.csv` | `reports/working/tables/stratified_crash_rate_ratio_official_traffic.csv`; `reports/working/figures/stratified_crash_rate_ratio_official_traffic.png` |
| 6 | `src.analysis.compare_traffic_scopes` | The CSV outputs of rows 4 and 5 | `reports/working/tables/traffic_scope_comparison.csv` |
| 7 | `src.analysis.daily_traffic_response` | `data/analysis/daily_traffic.csv` | `reports/main/tables/daily_traffic_by_wind.csv`; `reports/main/tables/daily_traffic_period_summary.csv`; `reports/main/figures/daily_traffic_by_wind.png`; `archive/generated_diagnostics/daily_traffic_wind_analysis_notes.md` |
| 8 | `src.figures.data_flow` | `data/analysis/selection_summary.csv`; `reports/main/tables/weather_cleaning_audit.csv` | `reports/main/figures/accident_flow.png`; `reports/main/figures/weather_flow.png`; `reports/main/figures/traffic_flow.png` |
| 9 | `src.figures.accident_profiles` | `data/analysis/accidents.csv` | `reports/main/tables/accident_characteristics.csv`; `reports/main/figures/accident_types.png`; `reports/main/figures/vehicles_per_accident.png`; `reports/main/figures/accident_types_by_severity.png` |
| 10 | `src.validate` | `data/analysis/accidents.csv`; `data/analysis/rate_model.csv`; optional `data/analysis/daily_traffic.csv`; `archive/generated_diagnostics/weather_cleaning_by_year.csv`; `reports/main/tables/mean_wind_oe.csv`; `reports/main/tables/weather_match_coverage.csv`; `archive/generated_diagnostics/gust_sensitivity.csv`; `reports/main/tables/stratified_crash_rate_ratio_by_wind.csv`; `reports/main/tables/accident_characteristics.csv` | `reports/main/tables/final_analysis_validation.md` |

Run results after preparation with `python -m src.analyze`. The optional
daily-counter analysis (row 7) is skipped automatically when
`daily_traffic.csv` is unavailable; the selection figures in row 8 are always
drawn.

## Fixed definitions

- Mean wind `f`: 0–5, 5–10, 10–15, 15–20, 20–25, and at least 25 m/s.
- Maximum gust `fg`: 0–5, 5–10, ..., 30–35, and at least 35 m/s.
- Gust factor: `fg/f` where `f >= 3 m/s`; intervals are 0–1.2, 1.2–1.4, 1.4–1.6, 1.6–1.8, 1.8–2.0, and at least 2.0.
- Winter: December–March; spring: April–May; summer: June–September; autumn: October–November.
- Primary accident-weather match: nearest valid observation, within five minutes and within 20 km.
