# Data and analysis pipeline

The final thesis workflow separates source-data preparation from routine
analysis of named CSV files. These scripts can be rerun from the required local
source deliveries or prepared data. Source deliveries are not included in Git;
a clean checkout alone cannot reproduce them.

## Three retained analyses

1. **Weather-frequency O/E analysis**, 2007–2025: accident occurrence relative
   to local station–season weather frequency.
2. **Approximate traffic-corrected O/E analysis**, 2007–2025: the same population,
   with frequencies reweighted and renormalised using the 2019–2024 relative
   daily traffic response.
3. **Vehicle-kilometres travelled (VKT) analysis**, 2019–2024: observed daily
   traffic × rural section length, allocated by pooled 2007–2025 station–month
   weather frequency during 07:00–24:00, in the counter-linked sample.

All three include mean wind, gust and temperature. They have different
exposure denominators and are not estimates of one identical parameter.
The joint wind–temperature description belongs to analysis 1. Seasonal rural
travel, severity proportions and road rankings are descriptive supplements.

## Rebuild final thesis products

From the repository root:

```bash
export MPLCONFIGDIR=/private/tmp/matplotlib
.venv/bin/python -m src.thesis_pipeline
.venv/bin/python -m src.validate
.venv/bin/python -m pytest tests -q
```

`src.thesis_pipeline` lists the retained table and figure commands in dependency
order and reads prepared inputs. The legacy `src.analyze` entry point exposes
historical analyses for audit; it is **not** the final thesis build command.
Historical supporting models and alternative exposure allocations are not
required thesis products.

The retained build regenerates `src.tables.counter_selection_audit` from the
prepared accident, road, counter-day and cleaned weather files; its output is
not a pre-existing report dependency. It also regenerates both workflow TeX
files and the exact-data excerpts. A new output tree therefore needs prepared
data and source code, but no old thesis tables or figures.

`src.validate` retains additional historical repository checks outside the
thesis scope. Its monthly VKT check treats wind, gust and temperature equally:
complete variable/outcome/bin combinations, sample counts, disjoint outcomes,
shared denominators, rate arithmetic and common source VKT. Conservation uses
an absolute tolerance of 0.001 vehicle-km with zero relative tolerance.

## Thesis workflow and exact data excerpts

`src/tables/pipeline.py` is the canonical generator for the compact conceptual
workflow figure. The conceptual boxes name all three retained analyses; exact entry points are listed here:

| Script file | Supported invocation from the repository root |
|---|---|
| `src/accidents/match_weather.py` | `python -m src.accidents.match_weather` |
| `src/analysis/oe_analysis.py` | `python -m src.analysis.oe_analysis` |
| `src/traffic/monthly_vkt.py` | `python -m src.traffic.monthly_vkt` |
| `src/tables/traffic_corrected_oe.py` | `python -m src.tables.traffic_corrected_oe` |
| `src/tables/monthly_vkt_rate.py` | `python -m src.tables.monthly_vkt_rate` |

The module checks that each source file has a module entry point. Paths identify
files; direct `python path/to/file.py` execution is not promised. The generator
no longer parses obsolete Markdown headings. Both the retained build and the
legacy workflow stage call it. `pipeline_prepare.tex` contains the five-box
TikZ figure; `pipeline_analysis.tex` is an empty retirement stub for the former
summary table and is no longer included in the thesis.

`src/tables/exact_data.py` reads the first two stored records directly from
`data/processed/accidents/all.csv` and
`data/processed/weather/weather.parquet`, preserving every column and order.
The accident CSV is read as strings, without pandas type conversion. Parquet
has typed binary values, not stored text strings. Arrow reports `station` as
int32, `time` as timestamp[us], and `f`, `fg` and `t` as float32. NumPy values
retain their original dtype. Unique positional and scientific formatting
produce shortest round-trip representations; the shorter candidate is used
and reparsing to the original dtype must reproduce identical bytes. No
intermediate conversion to Python float is made. Timestamps omit fractional
seconds only when their stored value equals a whole second.

Both excerpts use portrait tables with 11 pt monospace values. The accident
table has two stacked blocks (columns 1–5 and 6–9), labelled as the same records;
the weather table shows all five columns together. Full headers fit without
fragmentation. CSV field strings, rendered Parquet values, schema dtypes and
column blocks are audited in `reports/working/tables/exact_data_excerpts.json`.
Tests compare both first records with the source and verify float32/float64
round trips bit for bit, including negative zero and boundary values.
The older selected-column `cleaned_rows.tex` is unused and no longer generated;
it is preserved as an existing untracked file.

Section 3.2 shows processing architecture in Figure 3.3 instead of repeating
the analysis strategy. The cleaned accident and weather excerpts become
Tables 3.8 and 3.9 through automatic LaTeX numbering.
Figure 3.2 reuses the canonical eight temperature bins ending
in >=12 °C; its descriptive counts retain all 6,259 matched accidents.

## Preparation scripts

<style>
.pipeline-table table {
  width: calc(100% + 9mm);
  table-layout: fixed;
  border-collapse: collapse;
  border-top: 1px solid #999;
  border-bottom: 1px solid #999;
}
.pipeline-table th,
.pipeline-table td {
  vertical-align: top;
  text-align: left;
  padding: 0.4em 3mm 0.4em 0;
  overflow-wrap: anywhere;
}
.pipeline-table th:last-child,
.pipeline-table td:last-child {
  padding-right: 0;
}
.pipeline-table col:nth-child(1) { width: 19% !important; }
.pipeline-table col:nth-child(2) { width: 31% !important; }
.pipeline-table col:nth-child(3) { width: 27% !important; }
.pipeline-table col:nth-child(4) { width: 23% !important; }
.pipeline-table thead,
.pipeline-table tbody tr:not(:last-child) {
  border-bottom: 1px solid #999;
}
</style>

`python -m src.prepare --stage prepare` runs the rows below in dependency order. Daily
traffic runs only with `--daily-traffic`. Script paths are relative to `src/`;
data paths are relative to `data/`. Within each cell, a shared directory is
shown once in italics and the filenames beneath it belong to that directory.
This keeps the table short without making the file locations ambiguous.

<div class="pipeline-table">

| Script | Input | Output | Description |
|---|---|---|---|
| `accidents/build.py` | *raw/accidents/*<br>`accidents_*.txt`<br>`vehicles_*.txt`<br>`road_links_2007_2025.csv`<br>`urban_boundaries_2020_2024.geojson` | *processed/accidents/*<br>`all.csv` | Joins accident, vehicle, road-link, and boundary data. |
| `weather/download_weather.py` | *official supplied URL/*<br>`stod.txt`, `f_*.txt`, `fj_*.txt`, `fv_*.txt` | *raw/weather/*<br>`stations.csv`<br>`weather_10min_raw.parquet`<br>`weather_10min_raw_audit.csv` | Downloads the complete official station-file delivery and combines study-period rows without filtering. |
| `weather/clean.py` | *raw/weather/*<br>`weather_10min_raw.parquet` | *processed/weather/*<br>`weather.parquet`<br>`cleaning.csv` | Applies the fixed weather-quality rules and records annual counts. |
| `weather/frequency.py` | *processed/weather/*<br>`weather.parquet` | *processed/weather/*<br>`frequency.csv`<br>`yearly_frequency.csv`<br>`temperature_frequency.csv`<br>`traffic_frequency.csv` | Counts station-season and station-year-season mean-wind, gust, and temperature frequencies for O/E and annual-traffic models. |
| `traffic/annual.py` | *raw/traffic/annual/*<br>`*.xls*` | *processed/traffic/*<br>`annual.csv` | Standardises road section, length, ADU, SDU and VDU. |
| `accidents/match_weather.py` | *processed/accidents/*<br>`all.csv`<br>*processed/weather/*<br>`weather.parquet`<br>*raw/weather/*<br>`stations.csv` | *processed/accidents/*<br>`rural_injury.csv` | Matches wind and temperature independently within the stated time and distance limits. |
| `accidents/case_control.py` | *processed/accidents/*<br>`rural_injury.csv`<br>*processed/weather/*<br>`weather.parquet` | *processed/accidents/*<br>`case_control.csv` | Selects matched non-accident weather times from the same clean weather source. |
| `traffic/build_road_period.py` | *processed/traffic/*<br>`annual.csv`<br>*processed/accidents/*<br>`rural_injury.csv`<br>*processed/weather/*<br>`weather.parquet`<br>*raw/weather/*<br>`stations.csv`<br>*raw/traffic/reference/*<br>`road_section_midpoints.csv`, `road_sections.parquet` | *processed/*<br>`weather/road_period_frequency.csv`<br>`traffic/road_period.csv` | Builds road-period mean-wind and traffic rows. |
| `traffic/rate_weather.py` | *processed/*<br>`traffic/road_period.csv`<br>`accidents/rural_injury.csv`<br>`weather/weather.parquet`<br>*raw/weather/*<br>`stations.csv` | *processed/accidents/*<br>`rate.csv` | Aligns accident wind and temperature with the road-exposure station. |
| `traffic/daily.py` | *raw/traffic/daily_pdf/*<br>`*.pdf` | *processed/traffic/*<br>`daily_raw.csv` | Parses daily lane/channel counts and sums channels with identical road section and `stöð`. |
| `traffic/download_roads.py` | VGD-R MapServer layer 6 | *raw/traffic/reference/*<br>`roads.geojson` | Downloads the unchanged public road reference. |
| `traffic/counter_sections.py` | *processed/traffic/*<br>`daily_raw.csv`, `annual.csv`<br>*raw/traffic/reference/*<br>`roads.geojson`<br>*raw/weather/*<br>`stations.csv`<br>*processed/weather/*<br>`weather.parquet` | *processed/traffic/*<br>`counter_sections.csv` | Combines channels within a 20 m complete span, divides annual road sections at counter midpoints, and attaches a nominal nearest station with actual valid daytime observations in that year (within 20 km). |
| `traffic/assign_counter_sections.py` | *processed/accidents/*<br>`all.csv`<br>*processed/traffic/*<br>`counter_sections.csv`<br>*raw/traffic/reference/*<br>`roads.geojson` | *processed/accidents/*<br>`accidents-near-counter.csv` | Selects 2019--2024 rural injury accidents, projects them to their registered road geometry, and retains those within 100 m of the road and a valid counter-section. |
| `traffic/counter_days.py` | *processed/traffic/*<br>`daily_raw.csv`, `counter_sections.csv`<br>*raw/traffic/reference/*<br>`roads.geojson`<br>*raw/accidents/*<br>`urban_boundaries_2020_2024.geojson` | *processed/traffic/*<br>`counter_days.csv` | Sums channels per counter-section/day and multiplies actual daily vehicles by the rural road length, using geometric urban clipping (2019–2024, station within 20 km). Unmapped lengths are excluded and reported. |
| `weather/monthly_frequency.py` (optional diagnostic) | *processed/weather/*<br>`weather.parquet` | *processed/weather/*<br>`monthly_frequency.csv` | Pools 07:00–24:00 ten-minute observations by station and calendar month across 2007–2025, in the O/E bins. Retained for inspection, not used by analysis #2. |
| `traffic/counter_accidents.py` | *processed/accidents/*<br>`accidents-near-counter.csv`<br>*processed/traffic/*<br>`counter_days.csv`, `counter_sections.csv`<br>*processed/weather/*<br>`weather.parquet`<br>*raw/weather/*<br>`stations.csv`<br>*raw/traffic/reference/*<br>`roads.geojson`<br>*raw/accidents/*<br>`urban_boundaries_2020_2024.geojson` | *processed/traffic/*<br>`counter_accidents.csv` | Requires rural daytime accidents and positive traffic. Selects the nearest station to the counter-section within 20 km that has valid observations within five minutes of the accident. |
| `traffic/daily_vkt.py` | *processed/traffic/*<br>`counter_days.csv`, `counter_sections.csv`<br>`counter_accidents.csv`<br>*processed/weather/*<br>`weather.parquet`<br>*raw/weather/*<br>`stations.csv` | *processed/traffic/*<br>`daily_vkt.csv`<br>`traffic_weather_response.csv` | Uses `daytime_weather.py` and the shared `station_selection.py` rule to choose the nearest available station at every timestamp. Allocates rural daily vehicle-km uniformly over 07:00–24:00 for direct rates, and compares observed daily traffic with its counter-section/year/month/weekday expectation for the O/E traffic correction. |
| `traffic/locate_counters.py` | *processed/traffic/*<br>`daily_raw.csv`<br>*raw/traffic/reference/*<br>`roads.geojson` | *processed/traffic/*<br>`daily.csv` | Locates the exact-`stöð` counter records along official road geometry. |
| `traffic/daily_weather.py` | *processed/*<br>`traffic/daily.csv`<br>`weather/weather.parquet`<br>*raw/weather/*<br>`stations.csv` | *processed/traffic/*<br>`daily_match.parquet`<br>`daily_weather.csv` | Matches counter-days to a nearby weather station. |
| `traffic/accident_wind.py` | *processed/*<br>`accidents/rural_injury.csv`<br>`traffic/daily_weather.csv`<br>`traffic/locations.csv`<br>`weather/weather.parquet`<br>*raw/weather/*<br>`stations.csv` | *processed/traffic/*<br>`accident_wind.csv` | Matches accidents to the assigned counter-day station. |
| `export_tables.py` | *processed/*<br>`accidents/rural_injury.csv`<br>`accidents/rate.csv`<br>`accidents/case_control.csv`<br>`weather/frequency.csv`<br>`weather/yearly_frequency.csv`<br>`weather/traffic_frequency.csv`<br>`weather/monthly_frequency.csv`<br>`weather/cleaning.csv`<br>`traffic/annual.csv`<br>`traffic/road_period.csv`<br>`traffic/daily_weather.csv`<br>`traffic/accident_wind.csv`<br>`traffic/locations.csv`<br>`traffic/daily_vkt.csv`<br>`traffic/traffic_weather_response.csv` | *analysis/*<br>analysis CSV files listed below | Selects only the variables used by ordinary analysis. |

</div>

The road-period preparation contains only the 5 m/s mean-wind intervals used
by the traffic model. Gust and duplicate mean-wind classifications are not
carried through that working table.

## Source and preparation dependencies

| Source | Local delivery | Preparation command |
|---|---|---|
| Samgöngustofa | `data/raw/accidents/accidents_*.txt`, `vehicles_*.txt`, `road_links_2007_2025.txt` | `python -m src.accidents.build --include-2025` |
| Statistics Iceland | `data/raw/accidents/urban_boundaries_2020_2024.geojson` | Same accident build; road clipping uses the same polygons and Vestmannaeyjar exclusion. |
| IMO | `data/raw/weather/weather_10min_raw.parquet`, `stations.csv` | `python -m src.weather.clean`, then `python -m src.weather.frequency` |
| Vegagerðin seasonal traffic | `data/raw/traffic/annual/*.xls*` | `python -m src.traffic.annual` |
| Vegagerðin daily counters | `data/raw/traffic/daily_pdf/*.pdf` | `python -m src.traffic.daily` |
| Vegagerðin road geometry | `data/raw/traffic/reference/roads.geojson` | Counter-section and rural-length construction. |

Run `python -m src.accidents.match_weather` after accident and weather cleaning.
It writes `data/processed/accidents/rural_injury.csv`. The broad analysis export
`python -m src.export_tables` writes named CSVs under `data/analysis/`, also
retaining historical datasets that do not enter the final thesis.

Daily-counter preparation runs in this dependency order:

```bash
python -m src.traffic.counter_sections
python -m src.traffic.assign_counter_sections
python -m src.traffic.counter_days
python -m src.traffic.counter_accidents
python -m src.weather.monthly_frequency
python -m src.traffic.monthly_vkt
```

Counter sections use registered geometry and nominal nearest stations with
valid observations in the counter year. Counter-days include nonnegative
observed traffic and rural length. Event-time weather uses the nearest
qualifying station within 20 km of the counter section and five minutes of the
accident, with fallback during outages. All 694 eligible events have temperature,
wind and gust. Monthly frequencies use the assigned station and pool individual
ten-minute observations, with a separate validity denominator for temperature.
Each variable retains 533,649 counter-days and conserves 5,630,267,210.073 VKT.

For the traffic-response input, `python -m src.traffic.daily_vkt` remains the
preparation implementation writing `traffic_weather_response.csv`. It compares
allocated observed daily counts with each counter-section/year/month/weekday
mean among positive-count days, using observed daytime weather minutes. Its
additional historical rate output is unused by the final thesis. Export using
`python -m src.export_tables` after preparation. A focused VKT export is:

```bash
python -c "from pathlib import Path; from src.exports_counters import export_monthly_vkt, export_monthly_vkt_section; export_monthly_vkt(Path('data/analysis')); export_monthly_vkt_section(Path('data/analysis'))"
```

## New descriptive inputs and calculations

```bash
python -m src.prepare_revision
python -m src.tables.revision
```

Preparation scans the cleaned weather archive once and exports compact CSVs:

- `joint_weather_frequency.csv`: simultaneous valid wind/temperature counts
  for four categories by station–season; thresholds 15 m/s and 3°C. Joint
  frequencies are used directly, never products of marginal frequencies.
- `rural_annual_exposure.csv`: 2007–2025 official station-distance road lengths
  clipped to rural geometry. Winter: VDU × length × (121 + leap-year indicator)
  days. Summer: SDU × length × 122 days. Annual: ADU × length × calendar-year
  days. Unmapped lengths are excluded and retained for sensitivity analysis.
- `vkt_accidents.csv`: the 694 eligible event-time records used by the VKT
  figure decomposition and counter-composition diagnostic.
- `revision_accidents.csv`: cleaned register rows for urban/rural and seasonal
  comparisons. `cleaned_accident_rows.csv` and `cleaned_weather_rows.csv`:
  first two stored records, without artificial example values.

`src.tables.revision` writes joint O/E, urban/rural severity proportions,
seasonal rural rates, road-level rates and a counter-linked wind-composition
diagnostic. Audit CSVs go to `reports/working/tables/`; generated LaTeX goes to
`reports/thesis/generated/`. Joint observed and station-season expected totals
are conserved.

The seasonal calculation reproduces 6.32/13.89 billion VKT (winter/summer),
1.92 overall, 2.17 minor and 1.26 serious/fatal rate ratios. Treating all
unmapped lengths as rural changes the overall ratio to 1.91. The 2007 workbook
omits station distances: `resolve_chainage` recovers origins only from the
same section and named starting point in neighbouring available records,
requiring agreement if both earlier and later starts exist. Each evidence year
is stored in `chainage_basis`. Published lengths are retained and unresolved
origins remain excluded. This recovery is tested explicitly.

Road rates include only accidents linked to positive-exposure section-years.
The unfiltered ranking includes zero-accident roads and is retained as an audit
CSV. Its highest rates are dominated by one-accident roads; the thesis table
explicitly proposes at least 20 linked accidents for display (about 22%
count-only Poisson relative standard error). This is not a significance test;
historical mapping and denominator uncertainty remain limitations.

Road names are joined only when the local official road geometry contains one
unique `KAFLIVEGURHEITI` for the road's `NUMVEGUR`. All ten displayed roads have
an unambiguous name; `road_name_audit.csv` records the mapping and source fields.
Names describe the available geometry, not a reconstructed historical naming
series. Names do not alter the numerical ranking or road-number linkage.

`src.tables.headline_summary` divides each method's upper-bin metric by its
actual 0–5 m/s metric and writes `primary_relative_contrasts.csv`. The low-bin
O/E is never assumed to equal one.

## Figures and document

Retained charts use `src/figures/thesis_style.py`: 1 pt grey grids, zero tick
lengths, labels retained, and PNG/PDF outputs. Annual plots label every year.
The untracked `presentation.py` is not used.

Figure families: `wind_oe_panels`, `gust_oe_panels`, `temperature_oe_panels`,
`traffic_weather_response`, `weather_oe_traffic_corrected*`,
`monthly_weather_rate_annual`, `monthly_f_traffic_rate_panels`,
`monthly_fg_traffic_rate_panels`, `monthly_temperature_traffic_rate_panels`,
plus the accident map, conditions and annual coverage charts.

Build twice with `pdflatex` from `reports/thesis`, directing output to a separate
build directory to preserve the protected untracked `draft_en.pdf`. Copy the
result to `Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf`
and the log to `reports/thesis/draft_en.log` for checking.

## Fixed definitions and limitations

- Mean wind: 0–5, 5–10, 10–15, 15–20, ≥20 m/s. Gust: 5 m/s intervals through ≥30.
- Temperature: <−6, −6 to −3, −3 to 0, 0–3, 3–6, 6–9, 9–12, ≥12°C.
- Seasonal wind display pools ≥15 m/s; gust pools ≥20 m/s. Counts and exposure
  are summed before division.
- Winter: December–March; spring: April–May; summer: June–September;
  autumn: October–November.
- Primary weather matching: nearest qualifying observation within 20 km and
  five minutes. Hourly traffic is not observed or reconstructed.
- Station observations and fixed 2020–2024 urban boundaries are proxies for
  historical conditions. Results are associations, not causal effects.

## Detailed joint weather-frequency description

`src.tables.joint_detail`, run after `src.tables.revision` by the thesis pipeline,
uses the same 6,259 eligible joint accidents and station–season standardisation
as the retained coarse joint analysis. Each accident's wind, gust and temperature
are verified against a single matching archive observation, including potential
opposite-sign five-minute ties. The archive is then scanned for simultaneous
quality-controlled observations; separate marginal frequencies are never multiplied.

The fixed display uses wind [0,5), [5,10), [10,15), [15,45) m/s and temperature
[-30,-3), [-3,0), [0,6), [6,12), [12,30] °C, where the outer bounds are inherited
quality limits. The 0–6°C display interval crosses the old 3°C boundary, so a
24-cell internal partition retains 0–3 and 3–6°C separately. These atomic counts
and expectations reproduce both the 20 display cells and the original four cells;
the 20 displayed totals alone cannot recover that split. Exact station–season
weather counts and the original observed/expected totals must reconcile before
new outputs are published.

Main outputs are `joint_wind_temperature_detail.csv` (all 20 O, E, O/E, percentages
and sparse flags) and `joint_wind_temperature_contrasts.csv`. A contrast is reported
only when both cells have O ≥10 and E ≥5. Atomic frequencies, atomic O/E,
coarse reconciliation, simultaneous accident matches and a JSON validation record
are saved in `reports/working/tables/`. The old four-cell CSV remains available.
`src.validation.joint_detail`, invoked by `src.validate` when the detailed outputs
exist, verifies the persisted totals, ratios, sparse flags and reconciliation.

`src.tables.joint_grid` rescans the same simultaneous weather archive at the
five mean-wind intervals of Figure 4.3 and eight temperature intervals of
Figure 4.5. Rerun `src.accidents.match_weather` whenever `weather.parquet`
changes so that `rural_injury.csv` is matched against the same archive. The
grid script verifies that wind and temperature occur in one ten-minute
observation, saves `joint_wind_temperature_5x8.csv`, and reconciles its
observed cells against the earlier 4-by-5 table. The 19-cm Figure 4.6 is generated by
`src.figures.joint_detail` from this 5-by-8 table; its marginal row and column
pool observed and expected counts before taking their ratio. Its generated
Results and Discussion prose reads the same 5-by-8 table. `src.tables.results_context` generates the additional
Results comparisons from existing temperature O/E, traffic-response and seasonal
VKT outputs. This extends the descriptive weather-frequency analysis; it is not
a fourth method, a vehicle-based rate, or a formal interaction model.

Local `\FloatBarrier` commands keep the correction figure families within their
subsections. `reports/thesis/placeins.sty` is the unmodified public-domain
placeins v2.2 package from https://mirrors.ctan.org/macros/latex/contrib/placeins/placeins.sty,
vendored locally because the minimal TeX installation lacks it. Only the new joint
figure uses a local `[H]` placement; existing figures retain normal float rules.
