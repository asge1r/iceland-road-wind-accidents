> Current status: the final method-alignment instructions confirm monthly allocation
> as MAIN and same-day as SENSITIVITY, while preserving validated scientific results.
> This historical audit is superseded by [the final method audit](kristjan_method_alignment_audit.md),
> [figure specification](kristjan_main_figure_spec.md) and
> [method comparison](monthly_vs_sameday_figure_comparison.md).

# Final reader-clarity and supervisor-alignment audit

## Scope

This pass started from the existing, uncommitted supervisor-alignment work.
It preserves Q1 → Q2 → Q3 → Supporting Analyses and every existing thesis
figure family. No analysis was added or refitted. Earlier changes were retained.
This audit supersedes the prior figure-alignment audit's page-count and
validation summary; its figure-family inventory remains applicable.

## 1. Abstract

The English Abstract was rewritten as three paragraphs: question and approach,
main finding, and interpretation/limits. It is approximately 217 words. The
only numerical finding is O/E 2.15 at mean wind ≥20 m/s. Q2 and Q3 are explained
qualitatively, without their sample/exposure/rate/count bundles or unexplained
Q1/Q2/Q3 labels. Selective counters, missing hourly traffic and the distinction
between association and causation remain explicit.

## 2. Ágrip

Ágrip was composed independently around the research question, comparison,
main finding and limits. It uses descriptions such as “áætlaðan akstur” and
“hversu oft viðkomandi veður kom fyrir” instead of repeated technical denominator
terms. The sole numerical finding is the main ratio, 2,15. The English Abstract
and Ágrip now each have their own page; Ágrip occupies the previously blank
facing page without adding a page to the document.

## 3. VKT and reader-facing units

- The abbreviation is **VKT — Vehicle-kilometres travelled**.
- VKT remains in the detailed Q3 Methods definition immediately before the
  exposure equation, and in technical identifiers and filenames.
- The Q3 Methods and Results headings are **Q3: Traffic-Based Accident Rates**;
  the research-question label uses the same plain terminology.
- Figures 4.9–4.10 and 4.14–4.16 use **accidents per million vehicle-km** on
  their rate axes and in their captions.
- Table 4.3 uses **Million vehicle-km** and **Accidents per million vehicle-km**,
  with wrapped headers. Three decimal places remain useful for its small rates.
- Table 4.4 describes its denominator as estimated distance travelled. Coverage,
  selection and data-trimming table labels use traffic-based rate terminology.
- Results prose uses accident rates or estimated vehicle-kilometres deliberately.
  The large exposure total is displayed as approximately **5.63 billion**;
  the calculation is unchanged. No abbreviation “VK” was introduced.

## 4. Count labels

The changes are implemented in plotting code, not image editing.

| Figures | Treatment |
|---|---|
| 4.2–4.4 | `oe_histo.add_counts` skips nonpositive counts and retains positive counts; existing collision separation remains |
| 4.5–4.6 | Accident-count labels removed; the upper-bin O/E change is the annotation |
| 4.7, 4.11–4.13 | Shared O/E renderer also suppresses zero counts |
| 4.9–4.10 | Positive counts retained; zero counts produce no visible annotation |
| 4.14–4.16 | Zero counts/heights skipped; rendered labels that do not fit inside a small segment or collide with another count are omitted |
| 4.8 | Percentage changes retained at one decimal; these are the traffic result, not accident counts |

All other included figures were checked for count-label applicability. None
requires a zero accident-count annotation. Axis tick labels of zero are retained.
No bar height, source count, exposure or bin definition changed.

## 5. Results prose

- **Q1 mean wind:** retained the all-injury headline and sparse-cell warning;
  removed the observed/expected bundle and separate numerical narration of
  both severity groups.
- **Q1 gust:** retained its headline and relationship to mean wind; removed
  repeated observed and expected counts.
- **Temperature:** describes the non-monotonic shape and uncertainty without
  narrating individual interval estimates.
- **Q2:** retains the changes 2.15 → 2.71 and 3.34 → 4.20 once in prose;
  removed old/new expected-count narration. The unchanged numerator and
  approximate denominator reweighting remain clear.
- **Q3:** states the sample/exposure scale once, then the upper-bin relative
  contrasts and the 11-accident caveat. Absolute rates and interval exposures
  remain in Table 4.3. Seasonal introductions explain interpretation rather
  than repeating the denominator construction or headline rate.
- **Supporting checks:** numerical detail remains in the matched-time and
  appendix tables; prose explains what each check contributes.
- **Discussion:** removed the opening Q1/Q2/Q3 numerical bundle and repetition
  of the composition diagnostic. Interpretation of traffic, selection, road
  composition, sparse bins and distinct estimands remains.
- **Conclusion:** answers the research question with one O/E headline, qualitative
  traffic findings and the need for hourly traffic. It does not repeat Q3's
  sample, absolute rate, relative rate and count together.

The composition diagnostic 3.39 / 4.84 remains in Results. The chapter was
reread for paragraph purpose, repetition, primary/supporting status and terms
that could be explained more simply.

## 6. Table 4.4 and other tables

Table 4.4, printed page 30, now contains six rows: mean wind and gust for each
of Q1, Q2 and Q3. Columns identify parameter, method, comparison, estimate and
denominator. Its caption explicitly distinguishes O/E from the Q3 rate ratio
and states that these are not repeated estimates of one parameter. The
matched-time row was removed from this main summary; its results remain in
Table 4.5 and the Supporting Analyses section.

`src/tables/headline_summary.py` derives the display from existing validated
CSV rows and is also called by the thesis table generator. Table 4.3 values
are unchanged; only headers changed. Coverage/data-trimming/selection labels
were simplified. Table 4.2 remains in §4.1, page 18.

Table 3.3 remains the cleaned-record example in §3.1.2, page 7. It was reviewed
and retained: source identifier omitted, time rounded to the hour, coordinates
to 0.1 degree, and only useful accident-level fields before weather matching.
The one-line numerical O/E example remains after the equation. The old worked
O/E table was not restored.

## 7. Titles and terminology

All 21 included figure titles were audited. Existing parameter/season titles
were retained. Figure 4.1 now uses “Weather-match coverage” instead of the
matching-rule sentence. The appendix counter map uses “Daily-counter coverage”.
The severity-profile legend uses “Minor injury” and “Serious or fatal injury”
without implementation codes. Q1's caption also omits the injury-code notation.
Figure 4.8 now explicitly labels its pooled panels **All year**.

Pooled/seasonal panels use **All year, Winter, Spring, Summer, Autumn** as
applicable. No month suffix or reader-facing Fall remains. Internal Fall
categories were not changed. Annual labels describing actual year-by-year
coverage or annual traffic methods are retained in those distinct contexts.

## 8. Captions

Figures 4.9–4.10 and 4.14–4.16 were shortened. Each retains the population/period,
rate units, essential exposure distinction, label meaning and relevant limit.
Repeated exposure totals, full weather-pool dates and identical methodological
lists were removed where the Methods already explain them. The temperature
same-day caption no longer discusses wind/gust tail merging. Q2 captions now
explain the O/E-change annotations instead of absent count labels.

## 9. Supporting figures

Figures 4.11–4.16 remain in the main Results chapter under Supporting Analyses.
Their introductions identify period restriction or same-day weather allocation
as the purpose of the check. Captions mark supporting/sensitivity status.
No useful supervisor graph was removed, combined away or moved to an appendix.
The supporting analyses do not redefine Q1, Q2 or Q3.

## 10–11. Counts, sequence and pages

**21 figures, 18 tables, 65 PDF pages.** All 39 objects have a labelled,
explicit textual reference before their appearance. The page reduction follows
prose editing; no figure was removed or reduced to meet a page target.

| Results figure | Printed page | Content |
|---|---:|---|
| 4.1 | 18 | Coverage |
| 4.2 | 20 | Q1 mean wind, All year and seasons |
| 4.3 | 21 | Q1 gust, All year and seasons |
| 4.4 | 22 | Q1 temperature, All year and seasons |
| 4.5 | 23 | Q2 original/corrected mean wind |
| 4.6 | 24 | Q2 original/corrected gust |
| 4.7 | 25 | Corrected O/E by injury group |
| 4.8 | 26 | Traffic response |
| 4.9 | 28 | Q3 mean wind, All year and seasons |
| 4.10 | 29 | Q3 gust, All year and seasons |
| 4.11 | 31 | Supporting 2007–2018 original O/E |
| 4.12 | 32 | Supporting 2019–2024 original O/E |
| 4.13 | 33 | Supporting 2019–2024 corrected O/E |
| 4.14 | 35 | Supporting same-day mean-wind rates |
| 4.15 | 36 | Supporting same-day gust rates |
| 4.16 | 37 | Supporting same-day temperature rates |

Q2's direct comparisons remain on separate pages, keeping their following
explanation together. All Results figures were visually reviewed at A4 page
size, including count spacing, captions, zero-count suppression and units.
The final changed abstract/Q2/traffic-response pages were rechecked after the
last build. Tables 3.3, 4.2, 4.3 and 4.4 were checked for readability and layout.

## 12–13. Tests and compilation

- `.venv/bin/python -m pytest tests -q`: **77 passed, 1 skipped, 18 subtests passed**.
  The skip is the optional canonical-source replay. New checks protect zero
  suppression and the direct Q2 comparison without changing bar heights.
- `git diff --check`: passed.
- Two final sequential real-figure `pdflatex -interaction=nonstopmode
  -halt-on-error draft_en.tex` builds completed successfully.
- Final log: no fatal errors, undefined citations/references, duplicate labels,
  overfull boxes or rerun warnings.
- **Seven underfull-box notices** remain in source-summary tables and a
  bibliography entry. They do not produce clipping or malformed tables.
- During intermediate verification, an overlapping build read an incomplete
  auxiliary file and failed. Both processes finished before subsequent clean,
  sequential builds; the final builds and PDF do not have this error.

## 14. Scientific preservation and review state

SHA-256 checks against the start of this pass confirm that all **75 CSVs**
under `data/analysis/` and `reports/main/tables/` are byte-for-byte unchanged.
Only affected presentation outputs were regenerated. No scientific value,
analysis population, denominator, internal season category or numerical bin
was changed.

Preserved headline values: Q1 2.15 / 3.34; Q2 2.71 / 4.20; Q3 694 accidents,
533,649 eligible counter-section days and 5,630,267,210 estimated vehicle-km;
upper wind/gust counts 11 / 11 and relative rates 5.83 / 7.78; composition
O/E 3.39 / 4.84. The display rounding of the total to 5.63 billion does not
change this total.

The named thesis PDF is updated from the final build. No commit or push was
made. Supervisor decisions about full-day traffic allocation, cross-midnight
matching and the next dangerous-road/composition question remain pending as
before this editorial pass.
