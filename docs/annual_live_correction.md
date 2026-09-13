# Completed annual-traffic provenance correction

13 September 2026. Approved live correction, based on the isolated provenance experiment.

The live annual chain now reproduces the approved fresh results exactly. The main
all-injury conclusion is unchanged in direction. The serious/fatal 20–25 m/s
interval now includes 1, and the thesis explicitly avoids describing it as clear
evidence of an elevated rate. No claim was strengthened for the sparse ≥25 m/s bin.

## Backup and control

Before any live correction, **385 files** were independently copied to
[`archive/annual_provenance_correction_20260913T181844Z/`](../archive/annual_provenance_correction_20260913T181844Z/).
The backup includes all overwritten prepared products, analysis exports,
main/working outputs, thesis sources/PDF, validation report, code, and documents.
`manifest.json` records old SHA-256 hashes, sizes and modification times.
`old_headlines.json` records the original numerical tables;
`old_annual_sample_ids.csv` records the original IDs and likelihood eligibility.
All 385 backup copies were verified again after regeneration.

**48 pre-existing files changed in content; 337 backed-up files remained identical.**
The other 30 prepared files retained their original hashes and modification times.
Primary O/E, matched-time, and daily-counter inputs and outputs were preserved.
Nonannual rows/columns in mixed comparison tables and selection summaries match
exactly. The only Python source change is the approved annual sample expectation
in `src/validation/traffic.py`, from 4933 to 5125. No analysis definition or fitting
method changed.

## Cause and reconstruction

The live annual cache had survived the September weather-source replacement.
It exactly matched the August 26 archived cache, and its station-year totals
matched the earlier cleaning audit. The current cleaned source contains
230,458,950 observations, versus 211,497,897 in the earlier audit. Rebuilding
with the historical frequency function on the current input reproduced the
fresh counts, ruling out a changed period/bin algorithm. The relevant cleaning
rules were unchanged; the current raw and cleaned data contain no station/time
duplicates. Source availability changes altered eligible station assignments.
See the [isolated provenance report](annual_traffic_provenance.md) for the traced
source, code, and station-year evidence. Individual old-provider observations
cannot be reconstructed because the superseded raw delivery was not retained.

The explicit rebuild used `src.traffic.build_road_period
--rebuild-period-wind-frequency`, followed by `src.traffic.rate_weather` and the
existing annual exporters. The current canonical traffic export was independently
recreated and exactly matched `data/analysis/annual_traffic.csv`.
`src.analyze --stage annual-traffic` regenerated all current wind, vehicle-count,
serious/fatal, temperature, seasonal, and official VDU+SDU models and figures.
The annual quality audit, descriptive rates, traffic sensitivities, allocation
check, mixed wind O/E and seasonal comparisons, and traffic-flow figure were
also regenerated. `annual_quality.csv` was reproduced without a content change.

The thesis-table generator wrote all 19 tables to a staging directory; only the
seven changed annual-dependent tables were copied into the live generated directory.
The other 12 generated tables matched exactly. Validation was then regenerated.
Commands, scripts and logs are retained in the backup's `regeneration/` directory.

## Authoritative samples and exposure

| Stage | Old | Fresh |
|---|---:|---:|
| Frequency rows | 63,340 | 68,046 |
| Road-section/year/traffic-period strata | 68,946 | 68,946 |
| Strata with usable weather | 60,595 | 61,442 |
| Strata with positive eligible exposure | 59,011 | 59,874 |
| Annual exported accident sample | **4,933** | **5,125** |
| Conditional likelihood accidents | **4,928** | **5,122** |
| Exported accident-containing strata | 3,988 | 4,135 |
| Informative likelihood strata | 3,984 | 4,133 |
| Serious/fatal exported sample | 1,055 | 1,088 |
| Official VDU+SDU exported sample | 3,424 | 3,548 |
| Temperature exported sample | 4,921 | 5,118 |
| Seasonal exported sample | 4,933 | 5,125 |

The model's existing `model_accidents` field describes the pre-fit retained
sample. Statsmodels excludes strata with no outcome variation from the conditional
likelihood: five accidents in four old strata, versus three accidents in two
fresh strata. The thesis distinguishes these counts once in the Results section;
coverage and sample tables use the authoritative exported sample of 5,125.

The rebuilt cache matches **all 68,046 corresponding counts** obtained independently
from the current prepared weather-frequency layer: **zero mismatches or missing
keys** after the documented season-to-traffic-period aggregation and station
selection. The old/fresh comparison still reproduces 18,033 differing shared
counts, 1,540 old-only keys, and 6,246 fresh-only keys. Total eligible estimated
vehicle-kilometres changes from 45.910 to 46.106 billion.

## Accident IDs: 197 additions and 5 removals

There are **4,928 shared IDs**. The original inclusion rules are unchanged:

| Old exclusion reason for newly included accidents | Added IDs |
|---|---:|
| No eligible road-period exposure | 48 |
| Assigned denominator station more than 20 km from accident | 12 |
| No clean observation within five minutes at the assigned station | 137 |
| **Total added** | **197** |

All **five removals** lack a clean observation within five minutes at their newly
assigned denominator station. Among shared IDs, 520 change station, 519 change
matched wind, and 209 change wind bin. This explains why a net gain of 192 accidents
does not imply an increase in every wind-bin count.

[Old IDs](../archive/annual_provenance_correction_20260913T181844Z/old_annual_sample_ids.csv),
[fresh IDs](../archive/annual_provenance_correction_20260913T181844Z/verification/fresh_annual_sample_ids.csv),
and the [complete row-level selection trace](../archive/annual_provenance_correction_20260913T181844Z/verification/all_accident_selection_transitions.csv)
are retained. Both endpoints of that trace were checked against the live rebuild
and its dated backup.

## Main conditional Poisson estimates

All contrasts use 0–5 m/s as reference; parentheses are 95% CIs.

| Mean wind | Old accidents | Fresh accidents | Old RR | Fresh RR |
|---|---:|---:|---|---|
| 0–5 | 2,424 | 2,539 | 1.00 (reference) | 1.00 (reference) |
| 5–10 | 1,684 | 1,755 | 1.09 (1.02–1.16) | 1.10 (1.03–1.17) |
| 10–15 | 578 | 584 | 1.13 (1.03–1.24) | 1.14 (1.04–1.25) |
| 15–20 | 184 | 186 | **1.63 (1.39–1.90)** | **1.67 (1.44–1.95)** |
| 20–25 | 45 | 44 | **2.27 (1.68–3.07)** | **2.34 (1.72–3.17)** |
| ≥25 | 18 | 17 | **4.95 (3.07–7.98)** | **5.16 (3.15–8.44)** |

The serious/fatal 20–25 estimate changes from **2.23 (1.14–4.37)**, based on
nine accidents, to **1.88 (0.88–4.02)**, based on seven. Its fresh 15–20 estimate
is 2.04 (1.49–2.79); its ≥25 estimate is 5.51 (1.97–15.40), still based on only
four accidents. Official VDU+SDU upper-bin RRs are 1.70 (1.41–2.04),
2.03 (1.38–2.96), and 2.84 (1.34–6.04), based on 132, 28, and seven accidents.
All four all-injury seasonal ≥15 versus 0–10 m/s estimates remain above one.

Every category in all eight current annual model tables is recorded in
[annual_model_comparison.csv](annual_live_correction/annual_model_comparison.csv).

## Descriptive absolute rates

Rates are accidents per 100 million estimated vehicle-kilometres, over all
eligible road-period exposure, including strata without accidents.

| Wind | Old rate | Fresh rate |
|---|---:|---:|
| 0–5 | 8.5 | 9.0 |
| 5–10 | 13.0 | 12.8 |
| 10–15 | 16.6 | 16.7 |
| 15–20 | 27.7 | 30.0 |
| 20–25 | 40.5 | 46.3 |
| ≥25 | **58.6** | **98.9** |

The highest-bin exposure falls from approximately 30.735 million to 17.194 million
vehicle-kilometres, while accidents fall from 18 to 17. That denominator change
explains the much larger absolute rate. It does not justify stronger claims from
this sparse interval. Full exposure values and comparisons are in
[absolute_rate_comparison.csv](annual_live_correction/absolute_rate_comparison.csv).

## Every thesis prose and table change

The [exact before/after source diff](annual_live_correction/thesis_changes.diff)
contains every altered sentence and every generated numerical table row.
The prose changes are confined to `content.tex`:

1. Annual road-period coverage: “60,595 have nearby usable wind data” becomes
   “61,442 have nearby usable wind data.” The total remains 68,946.
2. The traffic-methods sample sentence now says its analysis retains 5,125
   accidents, replacing 4,933; the linkage and stratum definitions are unchanged.
3. The descriptive-versus-conditional comparison sentence changes the 20–25 RR
   from 2.27 to 2.34.
4. The old sentence combining 4,933 accidents with 3,984 fitted groups is replaced
   by: “The annual analysis retains 5,125 accidents. The conditional Poisson fit
   uses 5,122 of these in 4,133 informative road-section–year–traffic-period groups.”
5. The sentence listing three upper-bin all-injury RRs/CIs now gives
   1.67 (1.44–1.95), 2.34 (1.72–3.17), and 5.16 (3.15–8.44).
6. The uppermost estimate sentence changes 18 accidents to 17 and retains its
   warning about imprecision.
7. The serious-or-fatal sample sentence changes 1,055 to 1,088.
8. The serious-or-fatal 15–20 and 20–25 RR sentence changes to
   2.04 (1.49–2.79) and 1.88 (0.88–4.02). A sentence is added: “The latter
   interval includes one and does not provide clear evidence of an elevated rate
   in that bin.”
9. The serious-or-fatal ≥25 sentence changes to 5.51 (1.97–15.40), retaining
   the four-accident count and cautious interpretation.

| Generated file | Thesis table | Changed content |
|---|---|---|
| `coverage.tex` | **4.1** | Annual sample 4,933 → 5,125 |
| `traffic_methods.tex` | 4.2 | Annual sample 4,933 → 5,125 |
| `estimated_rate.tex` | 4.3 | All six annual accident counts and absolute rates |
| `evidence.tex` | **4.4** | Annual RR 2.27 (1.68–3.07) → 2.34 (1.72–3.17) |
| `traffic_quality.tex` | A.5 | Four all-period/official-period annual rows; nonannual rows unchanged |
| `traffic_scope.tex` | Generated supporting table, not included | Three upper-bin all-period and official-period rows |
| `allocation_check.tex` | Generated supporting table, not included | Annual and illustrative RRs; daily-traffic percentages unchanged |

No table was added to the thesis or appendix. The appendix source and scope are
unchanged. The abstract, Discussion, Limitations, and Conclusion contain no affected
annual numbers/claims and remain byte-for-byte unchanged. The main all-injury
scientific conclusion remains unchanged. `docs/methods.md` also now reports
5,125 linked annual accidents; the two prior audit reports are explicitly labelled
as historical, with links to this completed correction.

## Verification and remaining occurrences

- All **36 tests passed** (`python -m unittest discover -s tests`).
- `python -m src.validate` passed and regenerated the live validation report.
- `git diff --check` passed.
- `pdflatex` completed **twice**; the final PDF has **45 pages**.
- No undefined references/citations, duplicate labels, or overfull boxes.
- Nine underfull-box notices remain, matching the previous build's nine notices;
  none is a newly introduced layout warning.
- The cache, prepared annual exposure/rematch, four exported annual panels, and
  nine annual result tables exactly reproduce the approved isolated rebuild.
- All unrelated backed-up outputs and all other prepared inputs were preserved.

The full textual repository search included ignored raw-data and archive files,
excluding Git metadata, the virtual environment, Python bytecode, and the search's
own output. The search covered the requested old strings; files and matching-line
counts are classified in
[stale_number_classification.csv](annual_live_correction/stale_number_classification.csv).
Old annual values remain only as explicitly historical audits, before/after
comparisons, backups, and legacy working diagnostics. Unrelated numeric matches
include raw observations, coordinates, frequency/exposure decimals, nonannual
model values, and the TeX constant 72.27 points per inch. There are no remaining
stale annual headlines or sample sizes in the active thesis or authoritative
annual results. The legacy annual working files are explicitly listed in
[ANNUAL_PROVENANCE_STATUS.md](../reports/working/ANNUAL_PROVENANCE_STATUS.md);
none is consumed by the current code or active thesis, and none was promoted.

No correction or build failure remains unresolved. The pre-existing cache lifecycle
still requires an explicit rebuild when weather inputs change; adding automatic
invalidation would be a separate workflow change. The nine existing underfull
notices and inability to reconstruct superseded individual provider records are
recorded above and do not prevent this verified correction.

## Exact changed live files

The following 48 pre-existing files changed in content, including ignored local
analysis/preparation/working outputs omitted by a normal Git diff. Old and fresh
hashes are in [changed_live_files.csv](annual_live_correction/changed_live_files.csv).

- `data/analysis/manifest.csv`
- `data/analysis/road_exposure.csv`
- `data/analysis/road_rate.csv`
- `data/analysis/road_seasons.csv`
- `data/analysis/road_temperature.csv`
- `data/analysis/selection_summary.csv`
- `data/processed/accidents/rate.csv`
- `data/processed/traffic/road_period.csv`
- `data/processed/weather/road_period_frequency.csv`
- `docs/annual_traffic_provenance.md`
- `docs/methods.md`
- `docs/pipeline_summary.md`
- `reports/main/figures/season_rate.png`
- `reports/main/figures/season_rate_severity.png`
- `reports/main/figures/temperature_rate.png`
- `reports/main/figures/traffic_flow.pdf`
- `reports/main/figures/traffic_flow.png`
- `reports/main/figures/wind_oe_comparison.png`
- `reports/main/figures/wind_rate.png`
- `reports/main/figures/wind_rate_severity.png`
- `reports/main/figures/wind_rate_vehicle.png`
- `reports/main/tables/absolute_rate.csv`
- `reports/main/tables/allocation_check.csv`
- `reports/main/tables/season_rate.csv`
- `reports/main/tables/season_rate_severity.csv`
- `reports/main/tables/temperature_rate.csv`
- `reports/main/tables/traffic_checks.csv`
- `reports/main/tables/validation.md`
- `reports/main/tables/wind_oe_comparison.csv`
- `reports/main/tables/wind_rate.csv`
- `reports/main/tables/wind_rate_multiple.csv`
- `reports/main/tables/wind_rate_one.csv`
- `reports/main/tables/wind_rate_severity.csv`
- `reports/thesis/Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf`
- `reports/thesis/content.tex`
- `reports/thesis/generated/allocation_check.tex`
- `reports/thesis/generated/coverage.tex`
- `reports/thesis/generated/estimated_rate.tex`
- `reports/thesis/generated/evidence.tex`
- `reports/thesis/generated/traffic_methods.tex`
- `reports/thesis/generated/traffic_quality.tex`
- `reports/thesis/generated/traffic_scope.tex`
- `reports/working/figures/wind_rate_official.png`
- `reports/working/tables/estimated_crash_rate_by_wind_audit.csv`
- `reports/working/tables/rate_accident_weather_audit.csv`
- `reports/working/tables/season_method_comparison.csv`
- `reports/working/tables/wind_rate_official.csv`
- `src/validation/traffic.py`

New audit deliverables are this report, `docs/annual_live_correction/` (file manifest,
verification JSON, model and absolute-rate comparisons, selection/likelihood/bin
comparisons, stale-number classifications, and exact thesis diff), and
`reports/working/ANNUAL_PROVENANCE_STATUS.md`. The dated backup also holds old
files, row-level IDs/traces, commands, and logs. The two prior provenance documents
already existed before this correction, although they were not yet Git-tracked.

New evidence files (in addition to this report and the working-status note):

- `docs/annual_live_correction/absolute_rate_comparison.csv`
- `docs/annual_live_correction/accident_bin_transitions.csv`
- `docs/annual_live_correction/annual_model_comparison.csv`
- `docs/annual_live_correction/changed_live_files.csv`
- `docs/annual_live_correction/conditional_likelihood_counts.csv`
- `docs/annual_live_correction/selection_reason_counts.csv`
- `docs/annual_live_correction/stale_number_classification.csv`
- `docs/annual_live_correction/thesis_changes.diff`
- `docs/annual_live_correction/verification.json`

The PDF build additionally created `.aux`, `.log`, `.toc`, `.lof`, and `.lot`
files with the same stem as the final PDF. No existing auxiliary files were
removed. The authoritative PDF is
[Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf](../reports/thesis/Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf).
