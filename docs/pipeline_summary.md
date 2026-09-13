# Pipeline summary and repository audit

> Historical audit, completed before the approved live correction on 13 September 2026.
> Old annual values and pending-action statements below describe that earlier state.
> See [the completed live correction](annual_live_correction.md) for current results and verification.

Audited 13 September 2026 against the local source, prepared data, analysis CSVs,
retained results, tests and current thesis includes. This is a pipeline audit;
no scientific results, source data, thesis text or executable code were changed.

**Meeting takeaway:** the primary weather O/E can be traced and reproduced from
the analysis CSVs. The complete raw-to-final workflow is not yet reproducible
with the two advertised commands alone. In particular, the annual denominator
cache disagrees with the current weather-frequency layer. Passing the current
validation does not establish that all results use the latest prepared inputs.

## Clean pipeline table

Path shorthand: **R** = `data/raw`, **P** = `data/processed`, **A** =
`data/analysis`, **T** = `reports/main/tables`, **F** = `reports/main/figures`,
**W** = `reports/working/tables`, **G** = `reports/thesis/generated`.
Module names below are relative to `src`. Helpers are grouped with their owner.

| Stage | Script/module | Main input(s) | What it does | Main output(s) | Used by | Thesis analysis/result supported | Notes / assumptions |
|---|---|---|---|---|---|---|---|
| Source weather | `weather.download_weather` | Official index, R/weather/supplied/{stod,f_*,fj_*,fv_*}.txt | Downloads/caches deliveries, types study-period records, combines files, hashes sources | R/weather/{weather_10min_raw.parquet,weather_10min_raw_audit.csv,stations.csv} | Weather cleaning, station matching | Weather provenance | Separate prerequisite; absent from `prepare`; raw Parquet already excludes invalid keys/out-of-period dates |
| Clean accidents | `accidents.build` + `urban`, `types` | Accident and vehicle deliveries, road links, urban polygons | Harmonises fields, transforms coordinates, assigns urban/rural, links roads and counts vehicles | P/accidents/all.csv | Rural selection and counter-section assignment | Study population | Entry point adds `--include-2025`; raw parsing drops invalid time/coordinates |
| Rural/injury selection | `accidents.match_weather.load_accidents` | P/accidents/all.csv | Selects Rural, injury code <4 and study dates | In-memory selection | Weather matching | 6,414 rural injury accidents | No separate persisted pre-match rural table; selection and matching share a command |
| Clean weather | `weather.clean` | R/weather/weather_10min_raw.parquet | Applies fixed wind QC and missing-temperature handling | P/weather/weather.parquet; cleaning.csv, station_coverage.csv, frozen_zero.csv | All matching/frequency branches | Common observation layer | 230,458,950 retained rows; frozen-zero scan assumes chronological contiguous station records |
| Accident-weather match | `accidents.match_weather` | Selected accidents, clean weather, stations.csv | Selects nearest valid wind observation; independently selects temperature | P/accidents/rural_injury.csv | Exports, controls, annual matching | 6,259 primary matched accidents | File also retains unmatched events and wind candidates out to 30 km; analysis applies 20 km |
| Weather denominators | `weather.frequency` | P/weather/weather.parquet | Counts weather intervals by station/year/season and pools years | P/weather/{frequency,yearly_frequency,traffic_frequency,temperature_frequency}.csv | Exports, annual seasonal input | Primary and year-adjusted O/E | Broad prepared bins are deliberately collapsed for O/E |
| Matched-time preparation | `accidents.case_control` | P/accidents/rural_injury.csv + clean weather | Builds case/control times at same station, year/month, weekday and clock time | P/accidents/case_control.csv | Export and conditional logistic models | Matched-time comparison | Requires a valid case and at least one control; 6,257 cases per exposure in current result |
| Annual traffic | `traffic.annual` | R/traffic/annual/*.xls, *.xlsx | Parses road/year length and published ADU/SDU/VDU | P/traffic/annual.csv | Road panels, quality checks | Annual denominator | Multiple source editions selected by filename/order; record the actual chosen delivery |
| Annual exposure | `traffic.build_road_period` + `road_common`, `road_weather`, `road_panel`, `road_accidents`, `road_period` | Annual traffic, rural accidents, station register, road midpoints/fallback geometry, clean weather | Assigns station per road/year/period, derives VHDU, expands wind exposure | P/traffic/road_period.csv; P/weather/road_period_frequency.csv | Same-station match and rate exports | Annual vehicle-km analyses | Existing frequency cache reused unless explicitly rebuilt; confirmed inconsistency below |
| Annual accident match | `traffic.rate_weather` | Road-period panel, rural accidents, clean weather, station register | Rematches accidents to denominator station | P/accidents/rate.csv; W/rate_accident_weather_audit.csv | Annual exports | 4,933 annual-model accidents | Same station plus accident-to-station ≤20 km and ≤5 minutes |
| Daily traffic sources | `traffic.daily` + `pdf_parser`; `traffic.download_roads` | Six 2019–2024 PDFs; public road service | Parses directional channels into counter-days; obtains geometry | P/traffic/daily_raw.csv; R/traffic/reference/roads.geojson | Both daily branches | Observed daily traffic | PDF layout-specific parser; missing years can be skipped with a note |
| Counter sections | `traffic.counter_sections` + `road_common` | Daily raw, annual road lengths, road geometry, stations | Defines physical counter sections and representative lengths | P/traffic/counter_sections.csv | Strict daily vehicle-km branch | Road length for same-day exposure | Different unit from counter site; do not substitute locations.csv |
| Section accident assignment | `traffic.assign_counter_sections` | P/accidents/all.csv, counter sections, road geometry | Repeats rural/injury selection; assigns accidents along roads to counter sections | P/accidents/accidents-near-counter.csv | Strict same-day matching | 848 assigned accidents | Uses explicit injury codes 1,2,3 |
| Same-day weather exposure | `traffic.counter_day_weather` | Daily raw, counter sections, clean weather | Sums channels and counts actual 07:00–24:00 weather on each date | P/traffic/counter_day_weather.parquet | Counter accidents and daily_vkt | Strict daily denominator | ≥90% of 102 expected observations, independently by weather variable |
| Same-day accident match | `traffic.counter_accidents` | Assigned accidents, counter-day panel, clean weather | Keeps daytime accidents with positive traffic and matches the assigned station | P/traffic/counter_accidents.csv | daily_vkt | 615 matches before coverage eligibility | Reuses primary matching helpers; station distance here is counter-to-station |
| Same-day rates | `traffic.daily_vkt` | Counter-day exposure and counter accidents | Allocates daily vehicle-km by observed weather fractions, counts accidents and calculates rates | P/traffic/daily_vkt.csv | Export, weather-rate figures | 613 accidents; minor and serious/fatal rates | This is already a result table in the preparation layer; no regression is fitted |
| Counter-site locations | `traffic.locate_counters` | Daily raw, road geometry | Locates sites on road geometry | P/traffic/{daily,locations}.csv | Site/day weather, broad daily model | Allocated and full-day-mean branches | Distinct from strict counter sections |
| Counter-site weather | `traffic.daily_weather` + `counter_weather`, `daily_common`, `daily_tools` | Located daily counts, stations, clean weather | Matches counter-days, calculates daytime/full-day/active-window summaries | P/traffic/daily_weather.csv; daily_match.parquet | Daily export, accident_wind | Traffic reduction and daily allocation | Cache checks method/date span, not input fingerprints; excludes station 7475 |
| Counter accident wind | `traffic.accident_wind` | Rural accidents, locations, daily_weather, clean weather, stations | Links exact road/year counter and rematches accident-time wind to its station | P/traffic/accident_wind.csv | A/counter_wind.csv | 762 allocated-model sample | 864 initial matched candidates; three separate distance tests downstream |
| Counter location audit | `traffic.validate_counters` | P/traffic/{daily,locations}.csv; official 20 m road-point service | Checks estimated coordinates against reference points | P/traffic/daily_counter_station_validation.csv | A/counter_check.csv, thesis table generator | Independent location check | Not called by prepare, yet thesis generation requires its export |
| Analysis CSV export | `export_tables` → `analysis_data`; `exports_accidents`, `exports_weather`, `exports_traffic`, `exports_counters`, `export_common`, `export_docs` | Prepared products and raw weather audit | Builds readable data contracts, calendar/solar fields, annual exposure/count panels and manifest | A/*.csv, README.md, manifest.csv | Routine analysis | Canonical analysis inputs | More than a format conversion; optional outputs can survive from older runs |
| Primary O/E | `analysis.oe_analysis`; `tables.oe_audit` | A/{accidents,accident_conditions,weather_frequency}.csv | Computes observed and expected counts within station/season; checks reconstruction | T/{weather_oe,weather_oe_audit}.csv | O/E figures, comparison, validation, thesis | Figures 4.2–4.4 | Current primary O/E is descriptive, without bootstrap CIs |
| Year-adjusted O/E | `tables.year_oe` | Same accident inputs; A/weather_yearly.csv | Adds year to station/season standardisation | T/year_oe.csv | G/year_oe.tex | Requested year-adjusted comparison | Missing from analyze; currently not included in thesis body |
| Matched-time models | `tables.case_control`, `wind_season`, `weather_model` | A/case_control.csv | Fits categorical/continuous, seasonal and joint conditional logistic models | T/{matched_weather,wind_season,weather_model}.csv | Estimate figures, validation, evidence | OR 1.61 and supporting models | Conditional matched sets, not the traffic samples |
| Annual rates | `tables.rate`, `temp_rate`, `season_rate`; `analysis.traffic_rate` | A/{road_rate,road_temperature,road_seasons}.csv | Fits conditional rate models and outcome/period variants | T/wind_rate*.csv, temperature_rate.csv, season_rate*.csv; W/wind_rate_official.csv | Rate figures, comparison, validation | RR 2.27 at 20–25 vs 0–5 m/s | Time-proportional annual traffic allocation |
| Annual descriptive checks | `tables.annual_quality`, `estimated_rate` | A/{annual_traffic,road_exposure}.csv | Checks traffic values and calculates absolute rates over all valid exposure | T/{annual_quality,absolute_rate}.csv; W/estimated_crash_rate_by_wind_audit.csv | Thesis and traffic checks | Descriptive accidents per vehicle-km | road_exposure includes zero-accident strata; road_rate does not |
| Daily traffic response | `tables.daily_traffic`, `wind_duration` | A/daily_traffic.csv | Calendar-adjusts traffic and summarises wind level/duration | T/{traffic_wind,traffic_period,wind_duration}.csv | Traffic/duration figures and checks | Traffic reduction in strong wind | 10:00–21:59 mean differs from full-day duration |
| Allocated daily model | `tables.allocated_rate`; shared `analysis.traffic_rate` | A/{accidents,counter_wind,daily_traffic}.csv | Allocates each daily total among accident-time wind bins; fits counter/year model | T/allocated_rate*.csv; W/allocated_rate*_audit.csv | Figure, validation, sample comparison | 762 accidents; RR 3.62 | Full-day headline; serious/fatal and 07–24 sensitivity variants |
| Broad daily sensitivity | `tables.counter_rate`, `counter_radius` | A/{accidents,daily_traffic,counter_locations}.csv | Assigns nearest counter on exact road/year; bins full-day mean wind | T/{day_rate,day_rate_coarse,counter_radius}.csv; W/day_rate*_audit.csv | Figure, appendix, validation | 767 broad daily accidents | Different exposure and eligibility from 762 |
| Daily selection/audits | `tables.daily_sample`, `daily_adu`, `traffic_checks`, `allocation_check` | Daily/accident/location CSVs; annual and daily result tables | Describes retained/excluded samples; compares traffic sources and allocation direction | T/{daily_sample,daily_exclusions,daily_map,counter_adu,traffic_checks,allocation_check}.csv | Counter map, appendix, validation | Sample representativeness and traffic assumptions | Some checks recompute traffic summaries; direction check is not a corrected RR |
| Seasonal daily panel | `tables.daily_season_panel`; `analysis.traffic_daily_panel` | A/{accidents,counter_wind,daily_traffic}.csv | Constructs one counter/year/season/bin panel | A/daily_season_panel.csv | All seasonal daily calculations | Consistent seasonal daily sample | Created during analyze, not prepare |
| Seasonal daily models | `tables.daily_season_rate`, `daily_season_interaction`, `daily_highwind_season_interaction`, `daily_season_oe`; `analysis.traffic_daily` | A/daily_season_panel.csv | Fits seasonal rates, interaction tests, counter bootstrap O/E | W/daily_season_rate.csv, daily_*interaction.csv; T/daily_season_oe.csv | Figure, method comparison, validation | Seasonal traffic support | Shared computation; fixed bootstrap seed |
| Cross-method comparison | `tables.wind_oe_comparison`, `season_method_comparison` | Main O/E, annual/daily panels; seasonal result tables | Compares separate samples/denominators | T/wind_oe_comparison.csv; W/season_method_comparison.csv | Comparison figure and audit | Context across methods | Seasonal script still reads obsolete W/oe_scenarios.csv |
| Population/environment | `tables.annual_coverage`, `match_quality`, `conditions`, `severity`, `daylight`, `wind_profile`; `analysis.solar` | A/accidents.csv, accident_conditions.csv | Describes coverage/conditions; fits severity and daylight models | T/{weather_coverage,match_quality,conditions,temperature_coverage,severity_conditions,daylight,wind_profile}.csv | Descriptive figures, thesis, validation | Coverage and supporting associations | Severity models severity among recorded accidents |
| Figures | `figures.oe_histo`, `rate`, `temp_rate`, `vehicle_rate`, `season_rate`, `allocated_rate`, `counter_rate`, `weather_rate`, `daily_traffic`, `wind_duration`, `daily_season_oe`, `wind_oe_comparison`, `estimates`, `annual_coverage`, `conditions`, `counter_map`; `common` | Completed corresponding numerical tables; A/daily_vkt.csv for weather rates | Plots estimates and counts | F/*.png | Thesis and supervisor review | Numerical result visualisations | Mostly clean modelling/plotting separation |
| Selection/maps | `figures.data_flow`, `accident_profiles`, `accident_map` | A/{selection_summary,weather_cleaning,accidents,accident_conditions}.csv | Draws selection, profiles and maps | F/*_flow.png, accident_types*.png, vehicles_per_accident.png, accident_map.png | Thesis/descriptions | Population and coverage | Descriptive aggregation inside figures is appropriate |
| Validation | `validate` → `validation.{cli,audit,weather,traffic,models,report,common}`; `checks` compatibility shim | Analysis inputs and main/working result tables | Checks contracts, counts, model values and conservation | T/validation.md | Final review | Retained result consistency | Requires daily results despite optional-daily messaging; no source-freshness check |
| Optional QC sensitivity | `validation.zero_runs` | Raw weather and analysis inputs | Recomputes zero-run sensitivity separately | T/zero_run_check.csv | Optional diagnostic | Weather QC support | Not part of analyze or current thesis includes |
| Reporting | `tables.pipeline`, `tables.thesis` | docs/pipeline.md; analysis and main/working tables | Renders pipeline and numerical LaTeX tables | reports/thesis/pipeline_*.tex; G/*.tex | draft_en.tex → content.tex/appendices.tex | Presentation of retained results | Generates more tables than current thesis includes; does not compile PDF |

The reading order is source → accident cleaning → rural/injury selection →
weather cleaning → matching → primary O/E → matched-time → annual traffic →
two daily-counter branches → numerical tables/figures → validation/reporting.
Execution order differs: preparation must construct denominators before fitting
any model; analyze currently executes annual/daily models before matched-time.

## Canonical datasets and boundaries

| Layer | Authoritative file(s) | Distinguish from |
|---|---|---|
| Source deliveries | R/accidents/{accidents_2007_2024.txt,accidents_2025.txt,vehicles_2007_2024.txt,vehicles_2025.txt,road_links_2007_2025.csv,urban_boundaries_2020_2024.geojson}; R/weather/supplied/*.txt; chosen R/traffic/annual workbooks and six daily PDFs | Raw weather Parquet and stations.csv are generated source adapters, not original deliveries |
| Reference geometry | R/traffic/reference/{road_section_midpoints.csv,road_sections.parquet,roads.geojson}; R/weather/supplied/stod.txt | Public roads.geojson download does not create the annual midpoint/fallback files |
| Clean weather | P/weather/weather.parquet (230,458,950 rows); cleaning.csv for its audit | Raw Parquet has 232,459,562 rows; cleaning_old/new are not alternative authorities |
| Clean all accidents | P/accidents/all.csv (126,607 rows) | Already parsed/filtered; not the untouched register |
| Study event population | A/accidents.csv (6,414 unique IDs) | P/accidents/rural_injury.csv contains event and match fields together; there is no independent saved pre-match rural file |
| Matched accident weather | P/accidents/rural_injury.csv during preparation; A/accident_conditions.csv during analysis | Both A/accidents and conditions retain all 6,414 IDs; only 6,259 satisfy primary matching eligibility |
| Primary O/E input | A/{accidents,accident_conditions,weather_frequency}.csv | temperature_matches.csv is an inspection projection; temperature_frequency.csv is not the primary denominator entry point |
| Year O/E input | Same accident inputs + A/weather_yearly.csv | weather_frequency pools years; weather_yearly retains them |
| Matched-time input | A/case_control.csv (82,193 rows) | P/accidents/case_control.csv is the wider prepared copy; IDs repeat intentionally over exposures/control times |
| Annual conditional model | A/road_rate.csv (19,832 rows); temperature/season variants in road_temperature.csv and road_seasons.csv | P/accidents/rate.csv holds individual rematched events; A/road_exposure.csv is an 18-row all-exposure descriptive aggregate |
| Allocated daily model | A/{accidents,counter_wind,daily_traffic}.csv; optional locations for sample audit | daily_traffic has 774,274 site-days; counter_wind has 864 candidates, not 762 final events |
| Seasonal daily input | A/daily_season_panel.csv (1,912 rows) | Generated by analyze; its existence after prepare can reflect an older analysis run |
| Strict same-day input | P/traffic/counter_day_weather.parquet + counter_accidents.csv | A/daily_vkt.csv (200 rows) is the exported result of these inputs, not an individual-level model panel |
| Final numerical results | T/weather_oe.csv, matched_weather.csv, wind_rate.csv, allocated_rate.csv and other named T tables; A/daily_vkt.csv for same-day rates | G/*.tex and F/*.png are rendered views; W contains both required current inputs and obsolete outputs |

Keep the existing physical layout before the meeting. Conceptually distinguish
**deliveries → source adapters → clean/prepared → matched → analysis contracts →
numerical results → presentation**, with audits attached to their producing stage.
The main boundary exceptions are the result-valued daily_vkt in A, the
analysis-created daily_season_panel in A, and active diagnostics written into
archive. These need labels/ownership more urgently than file moves.

## Exact headline lineage

1. **Figure 4.2, mean wind O/E:** accident deliveries → `accidents.build` →
   P/accidents/all.csv; weather delivery → `weather.download_weather` → raw
   Parquet → `weather.clean` → clean Parquet; these meet in
   `accidents.match_weather` → rural_injury.csv → `export_tables` →
   A/accidents.csv + accident_conditions.csv. Clean weather →
   `weather.frequency` → P/weather/frequency.csv → export →
   A/weather_frequency.csv. The three A inputs → `analysis.oe_analysis` →
   T/weather_oe.csv (`variable=f`) → `figures.oe_histo` →
   F/wind_oe_panels.png → content.tex, `fig:wind-oe-panels`.
2. **Figure 4.3, gust O/E:** same chain, `variable=fg` →
   F/gust_oe_panels.png → `fig:gust-oe-panels`. Gust is from the accident-time
   matched observation, not a daily maximum.
3. **Figure 4.4, temperature O/E:** same chain with the independent temperature
   match columns and `variable=temperature` → F/temperature_oe_panels.png →
   `fig:temperature-oe-panels`.
4. **Requested “Table 4.2 year-adjusted O/E”:** clean weather →
   `weather.frequency` → P/weather/yearly_frequency.csv → export →
   A/weather_yearly.csv; with A/accidents.csv + accident_conditions.csv →
   `tables.year_oe` → T/year_oe.csv → `tables.thesis` → G/year_oe.tex.
   **This generated table is not included in current content.tex/appendices.tex.**
   The current Table 4.2 is G/traffic_methods.tex (“Traffic inputs for the
   supporting vehicle-kilometre analyses”), confirmed by current source and
   local LaTeX table listing. Do not identify results by an old table number.
5. **Matched-time OR 1.61:** rural_injury.csv + clean weather →
   `accidents.case_control` → P/accidents/case_control.csv → export →
   A/case_control.csv → `tables.case_control` → T/matched_weather.csv;
   select `exposure=mean_wind`, `model=categorical`, `comparison=>=15`,
   `reference=0-5`. This supplies the text and G/evidence.tex through
   `tables.thesis`.
6. **Annual RR 2.27:** annual workbooks → `traffic.annual` → annual.csv;
   road/station references + clean-weather frequency cache →
   `traffic.build_road_period` → road_period.csv;
   rural_injury.csv + that panel + clean weather → `traffic.rate_weather` →
   P/accidents/rate.csv; these prepared products → `exports_traffic` →
   A/road_rate.csv → `tables.rate` → T/wind_rate.csv, `bin_label=20-25`,
   `time_proportional_rate_ratio=2.274766` (reference 0–5; 4,933 accidents) →
   `figures.rate` → F/wind_rate.png and `tables.thesis` → G/evidence.tex.
   The number is confirmed in the retained table; the cache inconsistency
   prevents certifying a fresh-weather rebuild of it.
7. **Allocated daily RR 3.62:** PDFs → `traffic.daily` → daily_raw.csv →
   `locate_counters` → daily.csv/locations.csv → `daily_weather` →
   daily_weather.csv; rural accidents + locations/day station + clean weather
   → `accident_wind` → accident_wind.csv. Exports create
   A/daily_traffic.csv + counter_wind.csv; with A/accidents.csv →
   `tables.allocated_rate` → T/allocated_rate.csv, `wind_bin=>=15`,
   `rate_ratio=3.622311` (reference 0–10; 762 accidents, 47 high-wind) →
   `figures.allocated_rate` → F/allocated_rate.png. The prose headline is
   manually present in content.tex; not every prose number is automatically
   substituted by the table generator.
8. **613-accident same-day vehicle-km result:** daily_raw.csv + annual lengths,
   roads and stations → `counter_sections` → counter_sections.csv;
   all.csv + sections/roads → `assign_counter_sections` →
   accidents-near-counter.csv (848); daily_raw + sections + clean weather →
   `counter_day_weather` → counter_day_weather.parquet;
   assigned accidents + day panel + clean weather → `counter_accidents` →
   counter_accidents.csv (615); both → `daily_vkt` → P/traffic/daily_vkt.csv
   (613 coverage-eligible accidents per weather variable) → export →
   A/daily_vkt.csv → `figures.weather_rate` → F/weather_rate_annual.png and
   F/{f,fg,temperature}_traffic_rate_panels.png; `tables.thesis` → G/evidence.tex.
   Current thesis uses the generated evidence table and prose; these rate
   figures are retained products, not current direct figure includes.

## Definitions, duplication and sample meanings

| Rule | Actual implementation / owner(s) | Audit conclusion |
|---|---|---|
| Rural injury | `accidents.match_weather.load_accidents`: Rural and meidsli <4; `traffic.assign_counter_sections`: Rural and isin([1,2,3]) | Equivalent on the present study file (only codes 1,2,3); not equivalent on unexpected zero/negative codes. Test the valid code domain rather than changing selection before review |
| Serious/fatal | `analysis.oe_analysis`, `exports_traffic`, `tables.severity`, `allocated_rate`, `daily_sample`: ≤2; `traffic.daily_vkt`: isin([1,2]) | Same current domain. Minor=3. O/E serious/fatal bars are a subset of all injury; daily_vkt minor and serious/fatal are disjoint |
| Weather distance | `accidents.match_weather.PRIMARY_DISTANCE_KM=20`; literals/defaults in O/E, case_control, rate_weather, exports_traffic, allocated_rate, daily_sample, traffic_daily_panel, counter modules | Numerically consistent limit, but endpoints differ: accident–station, road midpoint–station, counter–station, accident–counter. Strict daily branch must not be described as applying all three allocated-model distances |
| Time difference | match_weather.TIME_TOLERANCE_MINUTES, case_control.MAX_TIME_MINUTES, oe_analysis.PRIMARY_MAX_TIME_DIFFERENCE_MINUTES; repeated ≤5 in rate_weather, counter_accidents, accident_wind, allocated_rate and exporters | Consistent inclusive five minutes; floor/ceil candidates; primary selection has explicit distance/time/station/time tie ordering |
| Seasons | export_common; weather.frequency.season_index; traffic_daily_panel.season_from_month; exports_traffic local map | Identical months: Winter Dec–Mar, Spring Apr–May, Summer Jun–Sep, Fall Oct–Nov; display Fall as Autumn. Winter is within calendar year, not a cross-year winter identifier |
| Traffic periods | export_common.PERIOD_MONTHS; traffic.road_common; rate_weather.PERIOD_BY_MONTH; tables.daily_traffic | VDU Dec–Mar, SDU Jun–Sep, VHDU Apr/May/Oct/Nov. Repeated definitions agree |
| Wind bins | weather.frequency has both prepared and OE_* constants; analysis.oe_analysis repeats O/E bounds; tables.counter_rate and allocated_rate define other model bounds | O/E f: 0,5,10,15,20,∞; gust: 0,5,…,30,∞. Annual f keeps 20–25 and ≥25. Allocated/seasonal coarse: 0–10,10–15,≥15. These differences are intentional, not inconsistent science |
| Temperature bins | weather.frequency has broad and OE_* arrays; oe_analysis repeats O/E thresholds; counter_day_weather imports OE arrays | O/E: <−6,−6–−3,−3–0,0–3,3–6,6–9,9–12,≥12°C. Prepared/annual/matched-time versions may split 12–15 and ≥15. Left-closed intervals throughout |
| Wind QC | weather.clean.classify, scan_frozen_runs | Drop missing paired wind, negative wind, f≥45, fg≥65, fg=0 with f>0, fg+0.5<f, and continuous f=fg=0 runs spanning ≥2 hours. No clipping/imputation. Downstream exports repeat subsets of these checks and trust cleaning for the rest |
| Temperature QC | weather.clean allows −60…50°C; match_weather, rate_weather, counter_accidents use −30…30°C; weather.frequency counts all finite cleaned t | Bounds are not one rule. Denominator versus match eligibility differs in code; investigate impact before calling this fully consistent. This audit did not scan all 230 million temperatures to quantify it |
| VHDU | traffic.road_panel.build_base_table; repeated in tables.annual_quality | (ADU×days_in_year − SDU×summer_days − VDU×winter_days) / remaining_days; leap-year aware. Nonpositive residual excluded, not imputed |
| 07:00–24:00 | counter_day_weather.START_HOUR=7; counter_accidents hour≥7; counter_weather active summaries; allocated_rate --time-window 07-24 | Means 07:00 through 23:59 on the date. Strict same-day coverage ≥90% of 102; allocated sensitivity ≥77 observations (about 75%). Same clock window, different eligibility |
| 10:00–21:59 | traffic.counter_weather.aggregate_daily_weather: hour≥10 and <22 | Exported as A/daily_traffic.f_mean. It is neither full-day mean nor the 07–24 allocation window |
| 767 broad daily | tables.counter_rate; W/day_rate_audit.csv → G/daily_selection.tex | 1,863 study-period accidents → 864 exact road/year candidates → 863 within counter radius → 767 with positive traffic and valid full-day mean wind |
| 762 allocated | tables.allocated_rate; duplicated eligibility in daily_sample.selected_ids and analysis.traffic_daily_panel | 864 candidates → 764 within all three distance limits → 762 with same-station, positive daily traffic, ≥108 full-day observations and valid accident wind. Audit identifies actual filters; do not treat 767→762 as one directly logged filter chain |
| 613 same-day | assign_counter_sections → counter_accidents → daily_vkt | Separate section-based branch: 848 assignments → 615 daytime weather matches → 613 after variable-specific exposure coverage; not simply the 07–24 subset of the 762 model |

Seeds are explicit in the active bootstrap implementations (`daily_traffic`,
`wind_duration`, `traffic_daily.calculate_seasonal_oe`, `wind_oe_comparison`,
`traffic_checks`). The primary O/E does not currently bootstrap. The analyze
`--bootstrap-reps` option reaches seasonal daily O/E and the comparison, not
every bootstrap-owning script; its primary-weather argument is unused.

## Entry points and confirmed fragilities

`python -m src.prepare --stage prepare` executes, in order:

```text
accidents.build --include-2025
weather.clean
traffic.annual
accidents.match_weather
accidents.case_control
weather.frequency
traffic.build_road_period
traffic.rate_weather
[only with --daily-traffic:
 traffic.daily → traffic.download_roads → traffic.counter_sections
 → traffic.assign_counter_sections → traffic.counter_day_weather
 → traffic.counter_accidents → traffic.daily_vkt → traffic.locate_counters
 → traffic.daily_weather → traffic.accident_wind]
export_tables
```

It requires the raw weather Parquet, station CSV and source audit to have been
created already. It does not run the weather downloader, counter-coordinate
validation, models, figure generation, or PDF compilation. `--stage all` runs
this preparation and then analyze; it is not a fresh-clone bootstrap command.

`python -m src.analyze` executes workflow → weather-frequency →
traffic-adjusted (annual then available daily) → supporting (descriptions,
matched-time, severity/daylight) → products (cross-method comparisons,
validation, LaTeX tables, final comparison figure). Repeated `--stage` options
run in the order supplied; dependencies are not automatically scheduled.

### High-priority findings

1. **Annual frequency cache is inconsistent with the current weather layer.**
   `traffic.build_road_period.main` reads P/weather/road_period_frequency.csv
   whenever it exists. Its local modification date is 26 August; clean weather
   is dated 9 September. More decisively, aggregation of the current
   P/weather/traffic_frequency.csv from seasons to VDU/SDU/VHDU finds **18,033
   different measurement counts among 61,800 shared station/year/period/bin
   keys**. Both producers count the same six f bins from clean weather.
   Example: station 1350, 2011 SDU, 5–10 m/s has 7,568 cached observations
   versus 7,465 in the current seasonal layer. This establishes disagreement
   between prepared denominators, not the magnitude of a corrected RR.
   A full fresh-weather annual refit was not performed. Preserve the reported
   2.27 and explicitly flag its provenance pending an isolated comparison.
2. **Products still depends on an obsolete, ungenerated table.**
   `tables.season_method_comparison.WEATHER` points to W/oe_scenarios.csv;
   `analysis.traffic_daily.compare_season_methods` expects its old columns and
   20–25/≥25 labels. No active analyze task produces it. A fresh clone lacks
   this ignored file; the local run can silently reuse it. Current and old
   high-wind observed totals agree, but that is not a freshness guarantee for
   expectations. A path-only replacement is insufficient: adapt the schema
   and ≥20 bin deliberately.
3. **Two reporting prerequisites are omitted.** `tables.year_oe` is absent
   from analyze even though `tables.thesis` reads its output. Counter-location
   validation is absent from prepare; export creates counter_check only if its
   prepared source exists, while `tables.thesis` reads it unconditionally.
4. **Optional daily support is incomplete.** `--skip-daily-traffic` and the
   presence test for daily_traffic.csv omit daily model tasks, but products
   still calls validation and thesis generation with unconditional daily
   reads. A missing daily_vkt.csv can also silently skip its figure while
   validation later requires the file. Existing ignored/retained outputs can
   mask this gap. These switches do not promise a complete daily-free rebuild.
5. **Freshness is not part of the CSV contract.** Manifest records filenames,
   row counts, columns and purpose, not input hashes, code revision, settings
   or run ID. Optional exports do not remove/invalidate older outputs.
   daily_match.parquet can pass method/date checks after upstream weather or
   geometry changes; daily_season_panel can be registered without being
   rebuilt. A successful run can combine generations of data.

### Responsibilities and lower-priority risks

| Finding | Evidence and practical consequence | Priority |
|---|---|---|
| Export is also scientific preparation | exports_traffic calculates vehicle-km, selects informative strata, rematches keys and bins outcomes; exports_accidents derives calendar/solar fields | Document this ownership now; do not describe export as a pure copy |
| Unused legacy calculations inside preparation | build_road_period computes accident counts/bin counts before outputting only exposure columns; rate_weather later supplies the actual same-station numerator | Simplify after review; avoid changing denominator work now |
| Result in preparation layer | daily_vkt calculates rates, exports them into A, and analyze only plots them | Make this explicit; otherwise “run analyses” is wrongly assumed to recompute these rates |
| Repeated daily selection | allocated_rate, daily_sample and traffic_daily_panel have separate masks/joins; allocated uses a left event join while seasonal uses inner | Consolidate only with ID-set equivalence tests; current validated counts agree |
| Legitimate result-to-result reads | Figures, traffic checks and thesis tables read completed T/W results | Keep these dependencies; distinguish the obsolete oe_scenarios read from valid downstream reporting |
| Silent input losses | build.read_accident_file drops invalid keys/time/coordinates; build keeps last duplicate accident/road link; match_weather keeps first station/time duplicate; road midpoints without usable geometry drop out | Add stagewise reason/count audits and conflict assertions; current unique output IDs do not prove source conflicts were absent |
| O/E missing-denominator loss | station_frequency_scenario inner-joins frequency; analyse checks sums against analysed count, not eligible count, and discards returned coverage details | Retain eligible vs analysed counts and require explained exclusions; current 6,259 total is checked by validation |
| Join coverage | Many joins already validate cardinality; counter_day_weather's expansion checks unique daily_row after range filtering | Add anti-join/exclusion counts rather than blindly applying one-to-one to intentional expansions |
| Ordering assumptions | clean.scan_frozen_runs relies on station/time continuity; raw combine preserves source row order without a global uniqueness/sortedness assertion | Assert ordering and conflicting station/time duplicates before frozen-run QC; no current-data corruption established here |
| Repeated thresholds | Seasons, distances, valid temperature ranges, count thresholds 108/77/102 and bin lists have several owners | Centralise named rules with boundary tests after meeting; preserve distinct sample rules |
| Active archive outputs | match_weather, annual and daily preparation write diagnostics beneath archive/generated_diagnostics | Archive is not wholly obsolete; do not delete it wholesale |
| Dependencies | Direct Python packages pinned; no complete environment/source lock; annual XLSX is parsed with stdlib ZIP/XML and PDF parser is custom | No missing openpyxl/PDF library inferred. Record Python, transitive packages and TeX versions for exact environment reproduction |
| Incomplete validation scope | Current checks validate counts/headlines, not source freshness, current thesis includes or the year_oe dependency | Passing checks are useful regression evidence, not an end-to-end reproduction certificate |
| Documentation drift | README still describes station-cluster uncertainty for primary O/E; current code/result/validation calls it descriptive without CIs | Correct the repository description independently of methodology; no thesis rewrite needed |

## Stale/legacy inventory: do not delete automatically

“Safe to archive” means no active source reference was found and current
replacements are identifiable; retain a dated copy. “Keep” can mean required
for the current pipeline despite a poor location. No files were moved/deleted.

| File(s) / family | Decision | Reason |
|---|---|---|
| P/accidents/rural_injury_new_weather.csv | Safe to archive | Byte-identical to current rural_injury.csv |
| P/weather/cleaning_new.csv | Safe to archive | Byte-identical to current cleaning.csv |
| P/accidents/rural_injury_new.csv; P/weather/{cleaning_old,frozen_zero_new,station_coverage_new,temperature_audit}.csv | Uncertain | Old/new names are misleading; preserve QC provenance until the corresponding generation is established |
| P/weather/road_period_frequency.csv | Keep, flagged | Active annual denominator cache, confirmed disagreement; never silently delete to force a changed result |
| P/traffic/daily_match.parquet | Keep, freshness unverified | Active site-weather cache; does not fingerprint upstream inputs |
| W/oe_scenarios.csv | Keep until dependency repaired | Looks legacy but products actively reads it; cannot archive yet |
| W/{day_rate_audit,wind_rate_official,daily_season_rate,daily_season_interaction,daily_highwind_season_interaction}.csv | Keep | Active thesis, comparison or validation inputs |
| T/year_oe.csv; G/year_oe.tex | Keep / unused presentation | Numerically reproducible; generator requires CSV, but current thesis does not include generated table |
| T/zero_run_check.csv | Keep as optional diagnostic | Separate zero-run sensitivity, not regenerated by analyze or included in current thesis |
| reports/thesis/content_before_polish.tex, content_before_primary12.tex; *.bak_2026-09-11, appendices.tex.bak_before_trim*; G/year_oe.tex.bak_2026-09-11 | Safe to archive | Backup sources are not loaded by draft_en.tex |
| G/{accident_sample,daily_rate,daily_exclusions,daily_radius,allocation_check,estimated_rate,coverage,severity_conditions}.tex and other generated tables | Check include graph before archiving | Some are included, others still regenerated but unused; “generated” alone does not indicate stale. In particular coverage, estimated_rate, severity_conditions and daily_radius are current includes |
| W/traffic_adjusted_oe_superseded.csv and matching working figure | Safe to archive | Explicitly superseded; no active source consumer |
| W/conditional_poisson_rate_ratio_{sdu,vdu,vhdu}.csv; rate_ratio_{one_vehicle,two_plus_vehicles,summer_sdu,winter_vdu}.csv and matching figures | Safe to archive | Older naming; current models use wind_rate*.csv/season_rate*.csv |
| W/daily_season_oe.csv and reports/working/figures/daily_season_oe.png | Safe to archive | Current canonical products are in reports/main |
| W/oe_*new_weather.csv, oe_old_vs_new_weather.csv, temp_bad_periods.csv, suspicious_temperature_station_months.csv | Keep as historical diagnostics | Useful for understanding QC changes; not canonical analysis inputs |
| reports/reproduced/{reference_snapshot,figures}/ | Safe to archive | Historical comparison imagery; no current thesis references |
| archive/cleanup_2026-07-28, cleanup_2026-08-26, legacy_outputs/2026-07-29_renamed_traffic, data_legacy_2026-07-22, superseded_code | Keep archived | Already separated historical CSVs, Parquets, code and figures; not routine inputs |
| archive/generated_diagnostics | Keep selectively | Mixes active outputs and obsolete figures/names; blanket deletion is unsafe |
| archive/git_metadata_before_github_switch_20260810 | Keep | Historical repository metadata, outside analysis cleanup scope |
| reports/thesis/*.aux, *.log, *.out, *.toc, *.lof, *.lot, *.bbl, *.blg | Safe to delete if desired | Rebuildable LaTeX auxiliaries; present bibliography is embedded in content.tex. Deletion not necessary for review |
| Retained PNGs and thesis PDF | Keep | Not every retained figure is currently included; keep review products until their intended scope is agreed |

## Terminal commands

Run Python commands from the repository root. These are operator instructions,
not commands executed as a full rebuild during this audit. Full regeneration
overwrites outputs and may expose the annual cache discrepancy; use a separate
checkout/data copy for that investigation.

```bash
# Environment (first setup; authorised source deliveries must be present)
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# Source-weather adapter: required once before prepare unless all three
# raw Parquet, stations.csv and raw audit are already supplied locally.
# Contacts the official delivery index even when text files are cached.
.venv/bin/python -m src.weather.download_weather

# Prepare all data, including both daily-counter branches
.venv/bin/python -m src.prepare --stage prepare --daily-traffic

# Additional reporting prerequisite omitted by prepare (network reference check)
.venv/bin/python -m src.traffic.validate_counters
.venv/bin/python -m src.export_tables

# Run analyses on an existing COMPLETE local snapshot
# First supply the result currently omitted by analyze.
.venv/bin/python -m src.tables.year_oe
.venv/bin/python -m src.analyze

# Regenerate thesis numerical tables and the three main O/E figures
# from existing completed result tables (does not refit models)
.venv/bin/python -m src.tables.pipeline
.venv/bin/python -m src.tables.thesis
.venv/bin/python -m src.figures.oe_histo

# Validate the complete local results and run tests
.venv/bin/python -m src.validate
.venv/bin/python -m unittest discover -s tests

# Compile the current thesis (pdflatex is installed locally; latexmk not on PATH)
cd reports/thesis
pdflatex -interaction=nonstopmode -halt-on-error -jobname=Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland draft_en.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland draft_en.tex
```

For all figures/models, use the full analyze command above. `--stage products`
alone regenerates validation/LaTeX/comparison products, not all figures.
For primary/annual/supporting work without daily data, explicitly select
`--stage weather-frequency --stage annual-traffic --stage supporting` and omit
products; the current all-results daily-free route is incomplete.

**Fresh-clone limitation:** there is currently no honest one-command full
rebuild to every retained product. Even with all source deliveries and the
extra commands, products needs the ungenerated W/oe_scenarios.csv. Repair its
consumer first, or retain a clearly identified historical snapshot for local
reproduction. Do not fabricate a replacement file merely to make the run pass.

After review, investigate cache refresh in isolation using the existing flags:

```bash
# In an isolated copy, after clean weather and core preparations exist:
.venv/bin/python -m src.traffic.build_road_period --rebuild-period-wind-frequency
.venv/bin/python -m src.traffic.rate_weather
.venv/bin/python -m src.traffic.daily_weather --rebuild-weather-match
.venv/bin/python -m src.traffic.accident_wind
.venv/bin/python -m src.export_tables
# Then refit affected analyses, compare counts/estimates and review differences.
```

## Validation performed for this audit

- All **36 unit tests passed** (`unittest discover -s tests`). These include
  definitions, input contracts, O/E, daily exposure, counter assignments,
  stage selection and module boundaries; they do not exercise a clean full run.
- `src.validate --output /private/tmp/pipeline_audit_validation.md` passed
  against the existing local analysis/result snapshot. Tracked validation was
  not overwritten.
- Recalculated all **200 primary O/E rows** and **13 year-adjusted O/E rows**
  into `/private/tmp`; pandas frame comparison passed against retained CSVs.
- Checked raw/clean Parquet metadata counts; study/condition/counter-wind ID
  uniqueness; current severity code domain; retained 2.27/3.62 table rows;
  767/762 and 848→615→613 audit chains; current figure/table includes.
- Compared annual cached counts with current seasonal counts aggregated to
  the identical traffic periods; found the 18,033 shared-key disagreements.
- No complete raw preparation, new source download, annual/matched-time refit,
  bootstrap rerun or thesis compilation was performed. Their current outputs
  were inspected; freshness and end-to-end reproducibility remain qualified.

## Review priorities

### Top five strengths

1. Readable analysis CSV contracts separate routine analysis from enormous
   weather data; the manifest makes inputs inspectable.
2. Primary O/E has a single calculation owner, conservation checks and plotting
   from completed values; both primary and year-adjusted tables reproduced.
3. Same-station matching explicitly connects numerator and denominator in
   annual and allocated daily comparisons.
4. Daily exposure allocation includes conservation checks; the seasonal daily
   models share a panel and rate-fitting implementation.
5. Fixed seeds, pinned direct dependencies, tests and headline validation
   provide useful regression evidence; the tested snapshot passes.

### Top five risks/confusions

1. Annual weather cache disagrees with the current prepared weather layer.
2. Complete products depends on obsolete oe_scenarios and omitted year/counter
   audit steps, so the advertised fresh-clone workflow is incomplete.
3. Optional daily skipping does not propagate to validation and LaTeX generation.
4. Three daily samples, two weather windows and several legitimate bin schemes
   are easy to conflate; the requested Table 4.2 reference is outdated.
5. Manifests lack provenance; working/archive directories mix live dependencies,
   diagnostic history and look-alike outputs.

### Top five improvements and timing

| Improvement | Safe before supervisor review | After meeting / isolated verification |
|---|---|---|
| Use this pipeline map and canonical-file list | **Done:** documentation only; use named outputs and sample definitions in discussion | Link/update older README/data/pipeline descriptions consistently |
| State the annual-cache discrepancy explicitly | Preserve the current numbers and show the count comparison; distinguish validated snapshot from fresh rebuild | Rebuild cache and affected models in isolation, quantify changes and review any scientific consequences |
| Make the result dependency graph complete | Use the documented extra commands only on a complete snapshot; acknowledge fresh-clone limitation | Wire year_oe/counter audit, adapt seasonal comparison to current O/E, and test full/daily-free execution |
| Give derived outputs provenance and expiry rules | Preserve a dated snapshot and clearly label the canonical CSVs | Add source/code/settings fingerprints, cache invalidation, atomic exports and explicit unavailable-output state |
| Unify repeated definitions and eligibility audits | Explain current differences; avoid moving/renaming data before review | Share tested constants/selectors, add temperature-boundary and eligibility-loss audits, then archive confirmed legacy files with approval |

Broad refactoring or renaming is not needed to make the project understandable
tomorrow. The substantive priority is to disclose and resolve input provenance,
while preserving the current result snapshot for comparison.
