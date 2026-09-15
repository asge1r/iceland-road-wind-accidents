> Current status: the final method-alignment instructions confirm monthly allocation
> as MAIN and same-day as SENSITIVITY, while preserving validated scientific results.
> This historical audit is superseded by [the final method audit](kristjan_method_alignment_audit.md),
> [figure specification](kristjan_main_figure_spec.md) and
> [method comparison](monthly_vs_sameday_figure_comparison.md).

# Kristján-first main story audit — PAUSED FOR REVIEW

## Status and reason

The pass is not finalised. User instruction §21 says: “If Kristján’s original
figure appears inconsistent with current validated data: STOP.” Side-by-side
review discovered differing historical O/E counts after the initial style and
text edits. No further thesis or figure edits were made after discovery.
The in-progress draft is reviewable, but the named delivery PDF remains the
previous pass's PDF and has not been overwritten.

## A. Primary question and theory

Proposed and applied to the draft: “How does rural injury-accident occurrence
vary with weather, particularly strong wind, after accounting as far as possible
for local weather frequency and traffic exposure?” Q1–Q3 are three stages,
not competing research questions: weather-frequency baseline, approximate
traffic correction, counter-based accident rates. The traffic decline motivates
correction before corrected estimates are presented. Abstract and Ágrip now
explicitly state the observed traffic decline; each retains one headline O/E.

## B–C. Intended main analyses and actual source figures

The latest user-provided formula specifies monthly allocation as the main rate.
Kristján-authored commits `bfd799f` and `c90f735` actually contain same-day
rate figures. Later commit `43a8a91` introduces the monthly implementation.
Therefore old Figures 4.9–4.10 match the newly specified monthly formula;
old 4.14–4.16 derive from his same-day work but use a later Codex layout.
They do not have interchangeable denominators. Monthly rates now use the
recovered original visual style; same-day remains an explicit allocation
comparison inside the rate section. Confirm his present primary-method intent.

Exact code, formulas, bins, populations, reference lines and source files are in
[kristjan_source_of_truth_mapping.md](kristjan_source_of_truth_mapping.md).

## D. Restored rate settings

- Actual light blue **#79BCE0** and red **#D62728**; black positive counts
  inside blue and above red. Blue means code 3; red codes 1–2.
- All year rate wind/gust 0–1.3; temperature 0–0.3.
- Seasonal rate wind 0–0.8; gust 0–0.5; temperature 0–0.6 from the original
  temperature-only automatic rule. Annual and seasonal axes are separate.
- Original seasonal upper-tail bins restored: wind ≥15, gust ≥20. Counts and
  exposure are combined; original scientific CSVs and fine-bin results unchanged.
- Corrected counter-era O/E fixed 0–6, 0–6, 0–2, ticks 1, 1, .2.
- Baseline and period O/E scripts retain the original automatic rule. Their
  actual source limits differ from current-data limits because of the discovered
  data discrepancy; these limits cannot be declared fully restored.
- All year and season labels simplified; zero counts suppressed. Original
  annual vertical panels and 2×2 seasonal layouts restored.

## E. Replaced Codex presentation

The two monthly five-panel images are replaced in the draft by one pooled
wind/gust figure and two seasonal figures. The three same-day five-panel
images are replaced by the original annual figure and three seasonal figures.
Files from earlier passes are retained on disk. No useful analysis was deleted.
The full-period original-versus-corrected comparison additions remain labelled
method comparisons; they are not represented as Kristján-authored originals.

## F. Current draft Results hierarchy

4.1 Study sample and coverage
4.2 Weather-frequency baseline
4.3 Traffic behaviour and the baseline limitation
4.4 Approximate traffic correction, including period and counter-era comparisons
4.5 Counter-based accident rates, then same-day allocation comparison
4.6 Secondary robustness checks

### Current draft figure inventory

| Figure | Label / family | Printed page |
|---|---|---|
| 3.1 | `fig:accident-map` | 7 |
| 3.2 | `fig:accident-conditions` | 11 |
| 4.1 | `fig:annual-coverage` | 20 |
| 4.2 | `fig:wind-oe-panels` | 22 |
| 4.3 | `fig:gust-oe-panels` | 23 |
| 4.4 | `fig:temperature-oe-panels` | 24 |
| 4.5 | `fig:traffic-response` | 26 |
| 4.6 | `fig:traffic-corrected-wind` | 27 |
| 4.7 | `fig:traffic-corrected-gust` | 28 |
| 4.8 | `fig:corrected-injury-groups` | 29 |
| 4.9 | `fig:oe-early-period` | 31 |
| 4.10 | `fig:oe-counter-period` | 32 |
| 4.11 | `fig:corrected-counter-period` | 33 |
| 4.12 | `fig:monthly-vkt-annual` | 35 |
| 4.13 | `fig:monthly-vkt-wind` | 37 |
| 4.14 | `fig:monthly-vkt-gust` | 38 |
| 4.15 | `fig:same-day-annual` | 40 |
| 4.16 | `fig:same-day-wind` | 41 |
| 4.17 | `fig:same-day-gust` | 42 |
| 4.18 | `fig:same-day-temperature` | 43 |
| A.1 | `fig:vehicles-per-accident` | 53 |
| A.2 | `fig:accident-types-severity` | 54 |
| A.3 | `fig:counter-coverage` | 56 |

## G. Older robustness checks

Matched-time, annual road-section conditional Poisson, the older allocated
762-accident daily model, and secondary severity/weather checks remain secondary.
The same-day family is explicitly attributed to the recovered source workflow,
not dismissed as an unrelated older user model. Dangerous-road/base-rate work
remains future work; no new scientific analysis was conducted.

## H. Discrepancy requiring review

The source baseline uses 6,192 matched accidents, versus the validated 6,259.
At mean wind ≥20 it shows 77 accidents and O/E 2.18, versus 68 and 2.15.
At gust ≥30 it shows 68 and 3.46, versus 61 and 3.34. Period and corrected
counter-era outputs also differ. Commit `3da8958` is the historical reconciliation
that replaced these outputs; its manifest indicates changed input snapshots.
The exact upstream cause remains unverified. Same-day source counts/rates and
traffic-response percentages match current outputs in the visual comparison.

## Validation completed before / while stopping

- Tests: **78 passed, 1 skipped; 18 subtests passed**.
- `git diff --check`: passed.
- Already-running sequential real-figure LaTeX builds both finished successfully.
- Current working draft: **71 pages, 23 figures, 18 tables**.
- No undefined citations/references, duplicate-label warnings or overfull boxes.
- Seven underfull-box notices remain.
- All 41 figure/table labels have textual references.
- All **75 scientific CSVs** match the pre-edit SHA-256 snapshot.
- Source rate scales checked against actual stack maxima; no clipping.
- All eleven recovered source figure assets inspected side by side. Full final
  PDF visual sign-off is **not complete**, because §21 stopped finalisation.
- A remaining visual issue: the prior right-hand “All year” text approaches
  upper count annotations in corrected O/E; fix after discrepancy review.
- No commit or push. Previous named delivery PDF is preserved; `draft_en.pdf`
  contains the in-progress 71-page version.

## I. Questions to resolve

1. Confirm the reconciled 6,259-accident O/E inputs as the source for reproducing
   Kristján's visual design, rather than reinstating the saved 6,192-case output.
   Trace upstream matching/weather differences if the reconciliation is disputed.
2. Confirm monthly allocation as the main rate calculation versus his actual
   same-day figure calculation; the latest supplied instructions specify monthly.
3. Confirm full 24-hour traffic allocation using 07:00–24:00 weather.
4. Confirm weather matches across midnight within ±5 minutes.

The pause follows the user's explicit scientific-safety instruction, not an
inferred approval requirement. Validated results have not changed.
