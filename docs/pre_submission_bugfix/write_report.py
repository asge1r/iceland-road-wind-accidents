"""Render the review report from the retained comparison tables."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'docs/pre_submission_bugfix';O=ROOT/'reports/reproduced/pre_submission_bugfix'

def table(frame, columns, labels=None, digits=6):
    frame=frame[columns]
    def fmt(x):
        if isinstance(x,float):return f'{x:.{digits}f}'
        return str(x).replace('|','/')
    return '\n'.join(['| '+' | '.join(labels or columns)+' |','| '+' | '.join(['---']*len(columns))+' |']+['| '+' | '.join(fmt(x) for x in row)+' |' for row in frame.itertuples(index=False,name=None)])

oe=pd.read_csv(D/'weather_oe_comparison.csv');temp=oe[oe.variable.eq('temperature')&oe.period.eq('All year')].sort_values(['outcome','bin_order_old'])
year=pd.read_csv(D/'year_oe_comparison.csv');year=year[year.variable.eq('temperature')].sort_values('bin_order_old')
matched=pd.read_csv(D/'matched_weather_comparison.csv');matched=matched[matched.exposure.eq('temperature')]
annual=pd.read_csv(D/'temperature_rate_comparison.csv').sort_values('bin_lower_c_old')
vkt=pd.read_csv(D/'daily_vkt_all_injury_comparison.csv');wind=vkt[vkt.variable.eq('f')]
cross=pd.read_csv(D/'midnight_primary.csv')
text='''# Pre-submission scientific bugfix report

13 September 2026. Authoritative scope: [analysis_theory_audit.md](analysis_theory_audit.md).
Review branch: `fix/pre-submission-scientific-bugs`. No merge or live thesis/result update.

## 1. Executive summary

The three authorised A issues are corrected in isolated products. The primary wind O/E, gust O/E, matched wind model, joint model, annual wind models, 762 allocated-counter model and severity-composition model retain their reported results. Temperature frequency estimates and temperature-only matched models change slightly. Correct distinct-slot coverage excludes two denominator days, but no additional accidents: **848 assignments → 615 matches → 613 retained**, unchanged for wind, gust and temperature.

The fresh results are in `reports/reproduced/pre_submission_bugfix/`; their baseline is the actual live working snapshot, including the user's pre-existing annual corrections, **not git HEAD**. Complete before/after numeric comparisons are versioned beside this report. Raw/prepared/live analysis products, live figures, thesis sources, generated thesis tables and PDF were protected; initial SHA-256 and nanosecond-mtime checks are retained in [protected_before.json](pre_submission_bugfix/protected_before.json).

This is a bounded correction, not a blanket endorsement of every audit finding. In particular, dense off-grid weather still affects record-weighted exposure fractions. The coverage fix does not choose an undocumented policy for collapsing multiple values within an interval. That remaining methodological choice is explicit below.

| Headline | Before | Fresh | Finding |
| --- | --- | --- | --- |
| Primary mean wind ≥20 m/s O/E | 2.152151 (2.15) | 2.152151 (2.15) | Unchanged |
| Severe/fatal mean wind ≥20 O/E | 1.870671 (1.87) | 1.870671 (1.87) | Unchanged; exact figures in CSV |
| Gust ≥30 O/E | 3.343546 (3.34) | 3.343546 (3.34) | Unchanged; exact figures in CSV |
| Temperature O/E | See every bin below | Slight changes | Cases unchanged |
| Matched wind ≥15 vs 0–5 OR | 1.608910 (1.61) | 1.608910 (1.61) | Unchanged |
| Joint adjusted wind ≥15 OR | 1.681441 (1.68) | 1.681441 (1.68) | Joint complete-case input identical |
| Annual wind and subgroup models | Live corrected snapshot | Same | Re-fitted; no numeric change at 1e-10 relative tolerance |
| Annual temperature model | 5,118 model accidents | 5,118 | Tiny denominator-driven changes; all two-decimal RRs unchanged |
| Allocated daily model | 762 accidents; RR 3.62 | Same | Re-fitted, including severe/fatal subset |
| Strict same-day VKT | 613 accidents | 613 | Denominator loses 100,505.79 VKT |
| Severity composition | 6,259 accidents; 1,424 severe/fatal | Same | Re-fitted, unchanged |
| Severe/fatal temperature O/E | All-year cold tail 0.91; spring 0–3°C 0.83 | 0.92; 0.82 | Two rounding changes; full values below/in CSV |

## 2. Classification and code changes

| Finding | Classification | Action |
| --- | --- | --- |
| A1 numerator/background temperature eligibility mismatch | A: correctness | Apply documented inclusive −30 to 30°C analysis rule to frequencies and O/E case eligibility |
| A2 five unregenerable temperature controls | A: reproducibility | Rebuild from current cleaned weather; remove five rows naturally through source matching |
| A3 row count masquerading as ten-minute coverage | A: correctness | Require ≥92 distinct occupied slots out of 102, separately by variable |
| Full 24-hour Q allocated with 07–24 weather | B: modelling assumption | Unchanged; methodological note below |
| ±5-minute match crossing midnight | B: modelling assumption | Unchanged; enumerate retained cases below |
| Three-core thesis hierarchy | C: presentation | Report only; thesis untouched |
| Broad constants, provenance framework, preparation ownership, general join safeguards | D: architecture | Defer; only narrow replay/invariant evidence added |

No requested classification was overturned. Dense within-slot weighting is an additional unresolved modelling choice exposed by A3, not an excuse to leave the coverage bug in place.

Production edits are confined to six files:

- `src/weather/eligibility.py`: one small owner of inclusive temperature analysis bounds and finite-value eligibility; cleaned archival limits remain broader.
- `src/weather/frequency.py`: exclude analysis-ineligible temperatures before all pooled/yearly/temperature counts. Wind/gust counts remain exact.
- `src/accidents/match_weather.py`: import the same temperature bounds; existing match behaviour unchanged.
- `src/analysis/oe_analysis.py`: apply the shared temperature predicate explicitly to cases, including the year-adjusted engine.
- `src/accidents/case_control.py`: use the shared control-temperature predicate; no fallback to excluded raw weather.
- `src/traffic/counter_day_weather.py`: add a distinct-slot mask, union masks across parquet row groups, retain auditable `*_distinct_slots` counts, and use them for eligibility. Existing record bin counts remain available for allocation.

The [fix-only diff summary](pre_submission_bugfix/diff_summary.md) lists files and changed areas. No module moves, renames, broad threshold centralisation, model/reference changes, or unrelated refactors. `src/validation/traffic.py` and the existing thesis/annual-result diffs were already dirty and are not part of this fix.

## 3. A1 — temperature eligibility and results

The current thesis, `reports/thesis/content.tex:251–252`, explicitly states that the nearest valid temperature is between −30 and 30°C. The matcher and historical case-control implementation already apply these inclusive bounds (visible in the history including `241c6c4`). Cleaning's −60 to 50°C archival range is not itself a bug. The error was counting background values that the analysis would refuse at an accident time.

The entire current 230,458,950-row clean source was scanned again. **11,807 finite observations outside the analysis range** are excluded from temperature frequency counts, including **8,289 in contributing primary station-season strata**. Primary temperature cases remain 6,259; severe/fatal cases remain 1,424. Year-adjusted cases remain 6,259. The O/E bins remain left-closed/right-open at interior edges; −30 and 30 are included in their tail bins. Expected counts conserve the eligible case total in every contributing stratum and panel.

The source also feeds annual temperature exposure through `export_temperature_rate_input`; that dependency was regenerated and the temperature rate model re-fitted. Annual wind inputs were not rebuilt under a different cadence assumption.

### All-year temperature O/E, every bin and both outcomes

'''
text+=table(temp,['outcome','bin_label','observed_accidents_old','expected_accidents_old','expected_accidents_new','relative_accident_frequency_old','relative_accident_frequency_new'],['Outcome','Bin °C','O (unchanged)','E before','E fresh','O/E before','O/E fresh'])
text+='''

All 80 seasonal/all-year temperature rows, and all wind/gust rows, are included in [weather_oe_comparison.csv](pre_submission_bugfix/weather_oe_comparison.csv). This includes changed expected counts and background counts, even where rounded O/E is unchanged. [oe_coverage_checks.csv](pre_submission_bugfix/oe_coverage_checks.csv) records eligible/analysed samples and expected/observed reconstruction for all 30 panels. Annual accident-match coverage is unchanged because its input matches are unchanged; its table was regenerated.

### Year-adjusted temperature O/E

'''
text+=table(year,['coarse_bin','observed_accidents_old','expected_accidents_old','expected_accidents_new','observed_expected_ratio_old','observed_expected_ratio_new'],['Bin °C','O','E before','E fresh','O/E before','O/E fresh'],digits=8)
text+='''

Full comparison: [year_oe_comparison.csv](pre_submission_bugfix/year_oe_comparison.csv). Only 24 out-of-range records occur in contributing station-year-season background bins, explaining the smaller change than in the pooled analysis.

### Annual temperature rate model

'''
text+=table(annual,['bin_label','observed_accidents_old','time_proportional_rate_ratio_old','time_proportional_rate_ratio_new'],['Bin °C','Accidents','RR before','RR fresh'],digits=8)
text+='''

Complete confidence intervals, p-values and sample accounting: [temperature_rate_comparison.csv](pre_submission_bugfix/temperature_rate_comparison.csv). The sample remains 5,118 model accidents, 4,128 strata and 30,606 rows. No displayed two-decimal RR changes.

## 4. A2 — five temperature controls and model replay

The five rows are identifiable in the raw source and occur inside archived frozen-wind intervals. Their `f=fg=0` source records were removed by common wind QC. They are absent from current cleaned weather, with no current observation within ±5 minutes. They were rechecked against the raw parquet, not manually reinserted into the fresh sample.

'''
trace=pd.read_csv(D/'extra_temperature_controls_frozen_run_trace.csv')
text+=table(trace,['stratum_id','station','control_target','time','t','start','end'],['Accident ID','Station','Control target','Raw weather time','Temperature','Frozen interval start','Frozen interval end'],digits=2)
text+='''

Evidence: [raw/QC trace](pre_submission_bugfix/extra_temperature_controls_frozen_run_trace.csv), [raw rows](pre_submission_bugfix/extra_temperature_controls_raw_weather.csv), and [removed control rows](pre_submission_bugfix/control_row_changes.csv).

**Root cause established:** stale/prepared temperature-source availability inconsistent with the declared current common cleaned source. It is not a nearest-time tie, station-selection change, or temperature-domain boundary. Temperature may physically remain valid while wind is frozen, but no independent temperature-source policy is documented. **Provenance limit:** neither code history nor the retained audit records identifies the exact historical run/operation that inserted or preserved these rows. An earlier cleaning state or temperature-specific source can explain them; naming one as proven would overstate the evidence.

Fresh data have **82,188 rows versus 82,193**, with **6,257 cases and 21,139 controls per variable**. Temperature loses five controls; its five affected sets' control-count metadata updates. Wind/gust values and cases are unchanged. The joint wide complete-case input is exactly unchanged: these five targets never had corresponding wind controls, so they had already been excluded by its complete-case pivot.

### Re-fitted temperature matched models

'''
text+=table(matched,['model','comparison','odds_ratio_old','odds_ratio_new'],['Model','Comparison (reference 0–3°C for categories)','OR before','OR fresh'])
text+='''

Reference-category OR remains 1 by definition. Full CIs, p-values and samples: [matched_weather_comparison.csv](pre_submission_bugfix/matched_weather_comparison.csv). The continuous effect remains per 5°C; it changes from 0.924331 to 0.924159. Wind OR remains 1.608910 and joint adjusted wind OR remains 1.681441. [weather_model_comparison.csv](pre_submission_bugfix/weather_model_comparison.csv) contains every adjusted wind/temperature coefficient comparison.

## 5. A3 — distinct-slot coverage, source diagnosis and strict VKT

Coverage now counts occupied half-open ten-minute intervals `[07:00,07:10), …, [23:50,24:00)` on the station/date. A 07:09 reading occupies the 07:00 slot. 07:00 is included; next-date 00:00 belongs outside the prior day's window. There are exactly 102 possible slots and `ceil(.9 × 102)=92` are required. Union across row groups prevents duplicates or chunk splits from inflating coverage.

The two excluded section-days are both 2019-06-11 at station 6300:

| Counter-section ID | Raw-count coverage before | Distinct slots | VKT removed |
| --- | --- | --- | --- |
| `2019:1-d2:8614-8614` | 491 | 52 | 95,845.20 |
| `2019:305-01:204-204` | 491 | 52 | 4,660.59 |

Raw weather on that date contains 516 distinct timestamps, with zero duplicate station/time keys; 491 survive cleaning. The same weather source is legitimately reused for two different road sections. This is dense sampling, not a duplicate merge of the same traffic exposure. No duplicate station/time keys were found in the June station-6300 clean subset. On June 12 there are 985 distinct observations occupying only 102 intervals. Removing duplicate keys upstream would therefore not fix this case. Upstream resampling would require a policy for multiple valid values, which was not silently selected.

[coverage_changed_days.csv](pre_submission_bugfix/coverage_changed_days.csv) gives every changed panel row. The positive-traffic, coverage-eligible denominator falls from **549,452 to 549,450 wind/gust section-days**, and **549,391 to 549,389 temperature section-days**. The full pre-eligibility panel remains 653,646 rows. Its all-traffic coverage flags, including zero-traffic days, are 554,181 for wind/gust and 554,120 for temperature.

The section geometry construction and assignment were rebuilt from current daily counts, annual lengths, roads and station inputs; all 848 assignments remain. Rematching produces 615 rows. Existing insufficient-coverage exclusions remain IDs **6664643** (2021-12-05, 84 slots) and **7572591** (2024-12-16, 46 slots). Neither newly excluded denominator date has a matched accident. Final IDs, bins and severity counts are unchanged at 613 for each variable; exact retained and excluded ID files are provided for f, fg and temperature in the companion directory.

### All-injury wind rates per 100 million estimated VKT

'''
text+=table(wind,['bin_label','accidents_old','estimated_vehicle_km_old','estimated_vehicle_km_new','rate_per_100m_vehicle_km_old','rate_per_100m_vehicle_km_new'],['Wind m/s','Accidents (unchanged)','VKT before','VKT fresh','Rate before','Rate fresh'])
text+='''

Wind/gust total estimated VKT changes from **7,337,474,559.87825 to 7,337,374,054.08825**; temperature changes from **7,337,152,718.86825 to 7,337,052,213.07825**. Allocated bins reconstruct every eligible daily VKT total; maximum error is **5.82×10⁻¹¹ VKT**. Every retained event has positive exposure in its same-date/section/variable/bin. Minor and severe/fatal counts are disjoint and sum to 613; their shared denominator is counted once when constructing all-injury rates.

Full wind/gust/temperature and severity/season comparisons: [daily_vkt_comparison.csv](pre_submission_bugfix/daily_vkt_comparison.csv); all-injury rates for every variable: [daily_vkt_all_injury_comparison.csv](pre_submission_bugfix/daily_vkt_all_injury_comparison.csv); conservation/sample summary: [strict_summary.json](pre_submission_bugfix/strict_summary.json).

**Exposure weighting diagnosis:** total daily VKT was not multiplied by the excess row count, because bin fractions renormalise to one. However, periods with dense readings receive disproportionate weight within a day. The selected fix changes coverage eligibility only. [cadence_weighting_diagnostic.csv](pre_submission_bugfix/cadence_weighting_diagnostic.csv) compares existing row fractions with equal occupied-slot weighting (averaging bin indicators within a slot) as a diagnostic, not as promoted results. Choosing exact-grid-only readings, a representative reading, or duration/slot weighting also changes bin allocations on retained dense days and potentially O/E backgrounds. This remains a supervisor decision; the fixed products must still be described as record-weighted approximations, not exact duration-weighted weather exposure.

## 6. B assumptions investigated, deliberately unchanged

### Full-day traffic versus the 07–24 weather window

The code computes `V = Q_24h × L`, `V_b = V × n_b(07–24)/n(07–24)`, and `rate_b = daytime accidents_b / V_b`. It conserves the full daily traffic exposure, renormalising over available daytime weather.

As a synthetic allocation over clock time, all Q is assigned inside 07–24 and none outside. But the calculation need not assert that **actual** night traffic is zero: another interpretation is that observed daytime weather composition is used as a proxy for the entire day's traffic-weather distribution. Either interpretation leaves the numerator/denominator time mismatch: daytime accidents divided by estimated full-day VKT are not an observed daytime accident rate.

This matches the operational method described in the authoritative audit and current thesis (Q explicitly defined as 24-hour count). The available repository contains no independent statement from Kristján establishing his intended interpretation beyond that operational specification; agreement with his personal intended estimand cannot be independently confirmed.

Alternatives include measured hourly allocation; restricting Q to observed daytime counts; an explicitly assumed daytime traffic share; or using full-day weather and full-day accidents. Multiplying by 17/24 assumes a particular traffic time profile, not a known correction. A constant share rescales all strict rates; shares varying by date/section/weather can also alter relative patterns and samples. These changes would affect the strict VKT branch; they do not automatically alter the separate primary O/E, matched-time, annual or 762 allocated models. None was implemented.

### Midnight nearest-observation matching

All retained primary near-midnight cases were replayed at their retained station. Four use next-day midnight observations:

'''
text+=table(cross,['id','timestamp','weather_station_id','weather_time','weather_time_difference_minutes_replayed'],['Accident ID','Accident time','Station','Matched time (00:00)','Difference minutes'],digits=0)
text+='''

Only **6131900**, a severe/fatal accident, belongs to the final strict VKT sample; it crosses for f, fg and temperature, all by four minutes. The other primary matches cross by 1–3 minutes. There are no additional retained primary crossings in the replay. Current primary wind and temperature matches use the same station/time; the strict branch's stored times were checked directly. [midnight_primary.csv](pre_submission_bugfix/midnight_primary.csv) and [midnight_strict.csv](pre_submission_bugfix/midnight_strict.csv) retain the details.

All satisfy the documented ≤5-minute tolerance. A calendar-date boundary does not itself make a nearby observation scientifically unusable. Requiring the exposure proxy to stay strictly within its date/window would define a different eligibility rule. The thesis explicitly restricts accident timestamps and denominator dates, but does not explicitly require the matched observation's date to equal the accident date. Therefore no matching rule or case was changed.

## 7. Tests, validation and preservation

**41 tests passed: all 36 existing tests plus five targeted tests**, including the normally opt-in full-source case-control replay. New tests cover inclusive lower/upper bounds, just-outside and nonfinite values, all temperature interval endpoints, pooled/year-adjusted expected-count conservation, 102 expected slots and boundary times, variable-specific duplicate coverage across parquet row groups, exact CSV reproduction from canonical inputs and invariance to candidate/weather ordering. Existing daily-VKT tests verify daily exposure conservation; the fresh full-panel audit repeats conservation and same-bin support for all three variables.

The exact-reproduction test compares serialized CSV bytes, avoiding pandas' default decimal-parser rounding differences; it does not weaken to approximate equality. The initial test-development parser mismatch was corrected before the final passing suite.

The normal `src.validate` command **passes using the isolated analysis/results tree**. Its first run identified an omitted unchanged working-table dependency in the isolation copy; copying those supporting inputs allowed the full validation to run without any change to its rules. Additional targeted validation checks all coverage flags against distinct slots, frequency-count conservation, eligible=analysed O/E samples, and station-season expected totals. See [verification.json](pre_submission_bugfix/verification.json), the [isolated validation report](pre_submission_bugfix/validation.md), and [canonical input hashes and package versions](pre_submission_bugfix/canonical_input_hashes.json). No validation thresholds were changed to accommodate the new results.

Unchanged headline annual wind/subgroup, allocated daily/severity, matched wind/gust, joint, wind-season and severity-composition models were re-fitted. Unaffected supporting tables were copied as baseline dependencies; they were not all re-fitted or regenerated from raw sources. [all_table_comparison.csv](pre_submission_bugfix/all_table_comparison.csv) explicitly distinguishes re-fitted tables from preserved baseline dependencies. [changed_numeric_cells.csv](pre_submission_bugfix/changed_numeric_cells.csv) enumerates changed numeric cells with row and column identifiers. No copied dependency is presented as an independent raw-source validation.

Preservation verification covers all 187 initial files under live prepared data, analysis data, main reports and thesis: identical SHA-256 and nanosecond modification times. Live protected files still have the user's pre-existing differences from HEAD; those differences were neither reverted nor included in this correction. `git diff --check` passes for the final working tree.

Commands and complete logs are retained under `reports/reproduced/pre_submission_bugfix/`. Replay helpers are versioned under `docs/pre_submission_bugfix/`: `initialize.py` refuses to overwrite an existing baseline; `recompute.py` rebuilds the approved prepared inputs, affected exports, models and figures using absolute canonical inputs and an isolated working directory; `check_unchanged.py` re-fits supporting headline models; `diagnose.py`, `cadence_diagnostic.py`, `compare.py`, and `verify.py` reproduce source traces and checks. Run from the repository root with `.venv/bin/python`; the full-source test uses `BUGFIX_REPLAY_DIR=reports/reproduced/pre_submission_bugfix .venv/bin/python -m unittest discover -s tests -v`.

## 8. Thesis edits that would be needed, and unresolved judgment

No live thesis was edited. If these fixes are accepted:

1. Change temperature matched controls **21,144 → 21,139** (all strata/cases unchanged), including any total that uses the old 82,193 combined rows.
2. Regenerate temperature O/E tables/figures and annual temperature model products from the fresh tables. At two decimals, severe/fatal all-year `<−6°C` O/E is **0.91 → 0.92**, and severe/fatal spring `0–3°C` is **0.83 → 0.82**. All-year severe/fatal cold expected count changes **51.4 → 51.3** at one decimal. Other full-precision changes are in the comparison CSVs. The explicitly quoted all-injury 3–6°C expected count changes **1,137.0 → 1,137.1** at one decimal; warm-tail 493.8 and O/E 1.60 remain. See [rounded_oe_changes.csv](pre_submission_bugfix/rounded_oe_changes.csv) for every change at these display precisions.
3. Replace the strict coverage wording with **distinct occupied ten-minute slots**. Update denominator totals/day counts and regenerate strict rates/figures; the 848/615/613 accident flow and high-wind rate remain unchanged.
4. Do not change the numerical wind headlines, joint adjusted wind, annual wind, or 762 allocated result. Temperature matched and annual temperature point estimates retain their two-decimal display, although full-precision estimates/CIs/p-values should come from the fresh products.
5. The three-core thesis hierarchy and misleading closed-interval temperature figure labels are presentation findings only in this task. Address them in a separately authorised thesis edit.

Supervisor judgment remains necessary for interpreting full-day traffic allocated with daytime weather, whether to impose same-date observation matching, and a consistent cadence/within-slot weather weighting policy. The historical operation responsible for the five stale controls remains undocumented; their current-source incompatibility and correct removal are established. Broader freshness infrastructure and missing-background join safeguards remain deferred under the requested narrow scope.
'''
# Replace headline approximate placeholders with actual values, avoiding transcription errors.
for variable,outcome,bin_label,placeholder in [('f','Severe/fatal accidents','>=20','1.870671'),('fg','All injury accidents','>=30','3.343546')]:
    value=oe.loc[oe.variable.eq(variable)&oe.outcome.eq(outcome)&oe.period.eq('All year')&oe.bin_label.eq(bin_label),'relative_accident_frequency_new'].iloc[0]
    text=text.replace(placeholder,f'{value:.6f}')
(ROOT/'docs/pre_submission_bugfix_report.md').write_text(text)
