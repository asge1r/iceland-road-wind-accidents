# Data and analysis pipeline

This is the active workflow. It separates conversion of large source deliveries
from routine analysis. Routine analysis reads only named CSV files in
`data/analysis/`.

## Data layers

| Layer | Purpose | Used by `src/analyze.py`? |
|---|---|---:|
| `data/raw/` | Unchanged authorised data deliveries and downloaded references. | No |
| `data/processed/` | Temporary local working files used only to transform source data. The 10-minute weather record contains 226.6 million rows, so this layer may use Parquet for efficient local processing. | No |
| `data/analysis/` | Named, inspectable CSV inputs for all ordinary analysis. | Yes |
| `reports/` | Generated tables and figures. | Output only |

`data/processed/` is not a second analysis database. It can be recreated from
`data/raw/` by rerunning `python -m src.prepare`.

## Pipeline at a glance

1. `src/accidents/`, `src/weather/`, and `src/traffic/` prepare one source at a
   time from unchanged deliveries.
2. Matching modules link prepared accidents, weather, roads, and traffic.
3. `src/export_tables.py` selects only the variables needed for analysis and
   writes the canonical CSV files in `data/analysis/`.
4. `src/tables/` reads those CSV files and writes numerical result tables.
5. `src/figures/` reads completed CSV tables and draws figures.

The boundary is deliberate: scripts run by `src/analyze.py` never read raw data or
the 226.6-million-row weather file.

## File-format and script rules

The format boundary is intentional:

- Source-specific preparation may read unchanged deliveries and local Parquet
  working files. Parquet is retained for the 226.6-million-row weather record
  and preparation joins for which CSV would be unnecessarily large and slow.
- `data/analysis/` contains only selected, documented CSV files. These are the
  inputs to the statistical analysis and are the files intended for direct
  inspection by the researcher and supervisor.
- Analysis scripts write CSV result tables. Figure scripts read completed CSV
  tables and write figures. No script combines data preparation, table
  production and figure production.

Parquet is therefore an implementation format inside preparation, not an
analytical data source. No reported result starts directly from a Parquet file.

Two scripts are deliberately outside the routine workflow:
`src/traffic/validate_counters.py` checks interpolated counter positions against
the official MapServer points, and `src/traffic/download_roads.py` downloads that
official reference. They are source-level quality control, not analysis.

## Source identifiers

| ID | Source website or delivery | Information used |
|---|---|---|
| ACC | Samgöngustofa accident-register delivery | Accident ID, date/time, coordinates, injury code, accident type, road link, and involved vehicles. |
| IMO | Icelandic Meteorological Office ten-minute observations | Station ID, time, mean wind `f`, reported wind gust `fg`, and temperature `t`. |
| VGD-A | Vegagerðin annual-traffic workbooks | Road-section length, ADU, SDU, and VDU. |
| VGD-D | Vegagerðin daily-counter PDF files | Counter ID, date, direction/lane channel, and daily count. |
| VGD-R | Vegagerðin MapServer | Road geometry and official road-station positions used to locate counters. |
| SI | Statistics Iceland urban-area polygons | Urban/rural classification of accident coordinates. |

**IRCA** was an internal abbreviation for *Icelandic Road and Coastal
Administration*, the English name for Vegagerðin. It is removed from this
pipeline because VGD-A, VGD-D, and VGD-R state exactly which Vegagerðin source
is meant.

## Preparation scripts

`python -m src.prepare --stage prepare` runs the rows below in dependency order. Daily
traffic runs only with `--daily-traffic`. Script paths are relative to `src/`;
data paths are relative to `data/`. Within each cell, a shared directory is
shown once in italics and the filenames beneath it belong to that directory.
This keeps the table short without making the file locations ambiguous.

| Script | Input | Output | Description |
|---|---|---|---|
| `accidents/build.py` | *raw/accidents/*<br>`accidents_*.txt`<br>`vehicles_*.txt`<br>`road_links_2007_2025.txt`<br>`urban_boundaries_2020_2024.geojson` | *processed/accidents/*<br>`all.csv` | Joins the accident sources and retains the fields needed for selection and matching. |
| `weather/clean.py` | *raw/weather/*<br>`weather_10min_raw.parquet` | *processed/weather/*<br>`weather.parquet` | Applies the fixed ten-minute weather-quality rules. |
| `weather/frequency.py` | *processed/weather/*<br>`weather.parquet`<br>*raw/weather/*<br>`stations.csv` | *processed/weather/*<br>`frequency.csv` | Counts wind and temperature observations by station, season and interval. |
| `traffic/annual.py` | *raw/traffic/annual/*<br>`*.xls*` | *processed/traffic/*<br>`annual.csv` | Standardises road section, length, ADU, SDU and VDU. |
| `accidents/match_weather.py` | *processed/accidents/*<br>`all.csv`<br>*processed/weather/*<br>`weather.parquet`<br>*raw/weather/*<br>`stations.csv` | *processed/accidents/*<br>`rural_injury.csv` | Independently matches wind and temperature within 20 km and five minutes; retains wind matches to 30 km for sensitivity. |
| `accidents/case_control.py` | *processed/accidents/*<br>`rural_injury.csv`<br>*processed/weather/*<br>`weather.parquet` | *processed/accidents/*<br>`case_control.csv` | Selects same-hour, same-weekday control times in each accident month for wind and temperature. |
| `traffic/build_road_period.py` | *processed/traffic/*<br>`annual.csv`<br>*processed/accidents/*<br>`rural_injury.csv`<br>*processed/weather/*<br>`weather.parquet`<br>*raw/weather/*<br>`stations.csv`<br>*raw/traffic/reference/*<br>`road_section_midpoints.csv`, `road_sections.parquet` | *processed/*<br>`weather/road_period_frequency.csv`<br>`traffic/road_period.csv` | Builds road-period mean-wind exposure; road geometry is a fallback for missing midpoints. |
| `traffic/rate_weather.py` | *processed/*<br>`traffic/road_period.csv`<br>`accidents/rural_injury.csv`<br>`weather/weather.parquet`<br>*raw/weather/*<br>`stations.csv` | *processed/accidents/*<br>`rate.csv` | Aligns accident wind with the road-exposure station. |
| `traffic/daily.py` | *raw/traffic/daily_pdf/*<br>`*.pdf` | *processed/traffic/*<br>`daily_raw.csv` | Parses one daily count per counter channel and date. |
| `traffic/download_roads.py` | VGD-R MapServer layer 6 | *raw/traffic/reference/*<br>`roads.geojson` | Downloads the unchanged public road reference. |
| `traffic/locate_counters.py` | *processed/traffic/*<br>`daily_raw.csv`<br>*raw/traffic/reference/*<br>`roads.geojson` | *processed/traffic/*<br>`daily.csv` | Combines directional channels and locates counters. |
| `traffic/daily_weather.py` | *processed/*<br>`traffic/daily.csv`<br>`weather/weather.parquet`<br>*raw/weather/*<br>`stations.csv` | *processed/traffic/*<br>`daily_match.parquet`<br>`daily_weather.csv` | Matches counter-days to daytime and full-day wind; the compact Parquet join avoids a large CSV. |
| `export_tables.py` | *processed/*<br>`accidents/rural_injury.csv`<br>`accidents/rate.csv`<br>`accidents/case_control.csv`<br>`weather/frequency.csv`<br>`traffic/annual.csv`<br>`traffic/road_period.csv`<br>`traffic/daily_weather.csv`<br>`traffic/locations.csv` | *analysis/*<br>ten data CSV files listed below | Selects only the variables used by ordinary analysis. |

The road-period preparation contains only the 5 m/s mean-wind intervals used
by the traffic model. Gust and duplicate mean-wind classifications are not
carried through that working table.

## Code organisation

- Executable modules parse options and coordinate one clearly named task.
- Larger helper modules contain related calculations but do not create extra
  analysis routes: `traffic/road_period.py` prepares road-period exposure,
  `traffic/daily_tools.py` supports counter-weather matching and its
  quality checks, and `tables/oe.py` calculates the retained O/E tables.
- Preparation code does not draw thesis figures. Table code writes numerical
  results, and figure code reads those completed results.
- Legacy standalone accident classification and unused daily accident-adjustment
  code have been removed from the active modules.

`data/raw/weather/stations.csv` is the externally supplied station-reference
source. It is not generated by the pipeline and is retained unchanged.

## CSV files used in analysis

| File | Unit | Main content | Used by |
|---|---|---|---|
| `accidents.csv` | One rural injury accident | ID, time, coordinates, outcome, road section, season and traffic period. | Study population and descriptions |
| `accident_conditions.csv` | One rural injury accident | Independent wind and temperature matches plus estimated solar elevation and daylight class. | Environmental descriptions and O/E join |
| `weather_frequency.csv` | Station × season × variable × interval | Pooled 2007–2025 wind and temperature counts and frequencies. | Exposure denominator |
| `case_control.csv` | Accident/control time within matched stratum | Exposure, station, case indicator, time, and wind or temperature value. | Conditional logistic models |
| `annual_traffic.csv` | Road section × year | Length, ADU, SDU, VDU. | Traffic-data quality table |
| `conditional_poisson_input.csv` | Road × year × traffic period × `f` interval | Vehicle-km and accident counts for strata informing the conditional Poisson model. | Rate-ratio model |
| `traffic_exposure_full.csv` | Traffic period × `f` interval | Total vehicle-km and accident counts; 18 rows. | Accident-per-km table |
| `daily_traffic.csv` | Counter × date | Daily traffic, wind summaries, and full-day counts in six `f` intervals, 2019–2024. | Selected-counter analyses |
| `daily_counter_locations.csv` | Counter × year | Road section and estimated counter coordinates. | Selected-counter rate analyses |
| `selection_summary.csv` | Dataset × selection step | Eight retained-record counts. | Selection figures |

`manifest.csv` records the row count, columns and purpose of every analysis file.
The derived O/E calculation rows are written separately to
`reports/working/tables/oe_station_bins.csv`; they are results, not canonical
analysis inputs.

## Analysis scripts

`src/analyze.py` reads the named CSV files in `analysis/`. Table scripts write
numerical results; figure scripts read those results and write images.

| Script | Input | Output | Description |
|---|---|---|---|
| `analysis/build_oe.py` | `analysis/accidents.csv`<br>`analysis/accident_conditions.csv`<br>`analysis/weather_frequency.csv` | `reports/working/tables/oe_station_bins.csv` | Builds station-season observed and expected accident totals. |
| `tables/oe.py` | `reports/working/tables/oe_station_bins.csv`<br>`analysis/accidents.csv`<br>`analysis/accident_conditions.csv` | `reports/main/tables/oe_results.csv`<br>`mean_wind_oe.csv`<br>`gust_oe.csv`<br>`gust_factor_oe.csv`<br>`temperature_oe.csv`<br>`weather_match_coverage.csv` | Calculates clustered-bootstrap intervals and exports the retained O/E tables. |
| `tables/radius_sensitivity.py` | `reports/main/tables/oe_results.csv` | `reports/main/tables/mean_wind_radius_sensitivity.csv` | Selects the primary upper mean-wind estimates under 10, 20 and 30 km station limits. |
| `figures/oe.py` | `reports/main/tables/oe_results.csv` | `reports/main/figures/mean_wind_oe.png`<br>`gust_oe.png`<br>`gust_factor_oe.png`<br>`temperature_oe.png`<br>four subgroup figures | Draws the O/E figures from the completed result table. |
| `figures/gust_factor.py` | `analysis/weather_frequency.csv` | `reports/main/figures/gust_factor_distribution.png` | Draws the descriptive gust-factor distribution. |
| `tables/annual_traffic_quality.py` | `analysis/annual_traffic.csv` | `reports/main/tables/annual_traffic_quality.csv` | Audits nonpositive and unusual published seasonal traffic values. |
| `tables/daily_traffic.py` | `analysis/daily_traffic.csv` | `reports/main/tables/daily_traffic_by_wind.csv`<br>`daily_traffic_period_summary.csv` | Calculates traffic relative to the typical day at the same counter. |
| `tables/daily_wind_duration.py` | `analysis/daily_traffic.csv` | `reports/main/tables/daily_traffic_by_high_wind_duration.csv` | Compares traffic with the calendar expectation by hours with `f >= 15 m/s`. |
| `figures/daily_wind_duration.py` | `reports/main/tables/daily_traffic_by_high_wind_duration.csv` | `reports/main/figures/daily_traffic_by_high_wind_duration.png` | Draws the sustained-wind traffic comparison. |
| `tables/daily_allocated_rate.py` | *analysis/*<br>`accidents.csv`<br>`accident_conditions.csv`<br>`daily_traffic.csv`<br>`daily_counter_locations.csv` | `reports/main/tables/daily_allocated_rate_ratio_by_wind.csv` | Allocates observed daily traffic by within-day wind frequency and fits a counter--year model using accident-time `f`. |
| `figures/daily_allocated_rate.py` | `reports/main/tables/daily_allocated_rate_ratio_by_wind.csv` | `reports/main/figures/daily_allocated_rate_ratio_by_wind.png` | Draws the allocated daily-counter rate ratios. |
| `tables/daily_counter_rate.py` | *analysis/*<br>`accidents.csv`<br>`daily_traffic.csv`<br>`daily_counter_locations.csv` | `reports/main/tables/daily_counter_rate_ratio_by_wind.csv`<br>`daily_counter_rate_ratio_coarse_by_wind.csv` | Fits the detailed and preferred coarse full-day observed-traffic sensitivities within counter and year. |
| `tables/daily_counter_radius.py` | *analysis/*<br>`accidents.csv`<br>`daily_traffic.csv`<br>`daily_counter_locations.csv` | `reports/main/tables/daily_counter_radius_sensitivity.csv` | Repeats both non-reference coarse estimates at 5, 10 and 20 km. |
| `figures/daily_counter_rate.py` | `reports/main/tables/daily_counter_rate_ratio_coarse_by_wind.csv` | `reports/main/figures/daily_counter_rate_ratio_coarse_by_wind.png` | Draws the preferred observed-traffic sensitivity with 95% intervals. |
| `tables/traffic_sensitivity.py` | Main and official-period rate tables<br>`analysis/daily_traffic.csv`<br>`reports/main/tables/annual_traffic_quality.csv` | `reports/main/tables/traffic_sensitivity.csv` | Consolidates period-scope, zero-counter-day and annual-traffic quality checks. |
| `figures/daily_traffic.py` | `reports/main/tables/daily_traffic_by_wind.csv` | `reports/main/figures/daily_traffic_by_wind.png` | Draws the supporting daily-traffic result. |
| `tables/rate.py` | `analysis/conditional_poisson_input.csv` | `reports/main/tables/conditional_poisson_rate_ratio_by_wind.csv` | Estimates the road-, year- and period-stratified rate ratio. |
| `figures/rate.py` | Conditional Poisson rate table | `reports/main/figures/conditional_poisson_rate_ratio_by_wind.png` | Draws the stratified rate-ratio figure. |
| `figures/data_flow.py` | Selection and weather-cleaning summaries | Three data-selection figures | Draws accident, weather and traffic selection figures. |
| `figures/accident_profiles.py` | `analysis/accidents.csv` | Descriptive figures | Draws accident-type, vehicle-count and severity descriptions. |
| `tables/conditions.py` | `analysis/accidents.csv`<br>`analysis/accident_conditions.csv` | `reports/main/tables/accident_conditions_summary.csv`<br>`temperature_coverage.csv` | Summarises hour, traffic period, daylight and temperature. |
| `figures/conditions.py` | `reports/main/tables/accident_conditions_summary.csv` | `reports/main/figures/accident_conditions_overview.png` | Draws the consolidated raw-count description of accident conditions. |
| `tables/case_control.py` | `analysis/case_control.csv` | `reports/main/tables/case_control_weather.csv` | Fits continuous and categorical conditional logistic models. |
| `tables/high_wind_profile.py` | `analysis/accidents.csv`<br>`analysis/accident_conditions.csv` | `reports/main/tables/high_wind_accident_profile.csv` | Compares the primary sample with accidents at mean wind at least 15 m/s. |
| `validate.py` | Canonical analysis CSVs and retained result tables | `reports/main/tables/final_analysis_validation.md` | Checks row counts, scope and headline results. |

Run results after preparation with `python -m src.analyze`. The optional
daily-counter analysis is skipped automatically when `daily_traffic.csv` is
unavailable; the selection figures are always drawn.

## Fixed definitions

- Mean wind `f`: 0–5, 5–10, 10–15, 15–20, 20–25, and at least 25 m/s.
- Matched-time wind gust `fg`: 0–5, 5–10, ..., 30–35, and at least 35 m/s.
- Gust factor: `fg/f` where `f >= 3 m/s`; intervals are 0–1.2, 1.2–1.4, 1.4–1.6, 1.6–1.8, 1.8–2.0, and at least 2.0.
- Temperature: below −9, 3°C intervals from −9 to 18, and at least 18°C.
- Winter: December–March; spring: April–May; summer: June–September; autumn: October–November.
- Primary accident-weather match: nearest valid observation, within five minutes and within 20 km.
