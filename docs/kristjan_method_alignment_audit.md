> Subsequent figure/readability pass: [final comparison audit](kristjan_figure_method_comparison_audit.md).
> Monthly/same-day roles are unchanged; baseline panels have individual scales,
> purposeful colours are restored, and Table 3.9 raises the total to 19 tables.

# Final Kristján-method alignment audit

## Final scientific hierarchy

The latest instructions resolve the earlier pause: use the current validated
results and Kristján's monthly-frequency method as the main traffic-rate analysis.
Same-day allocation is sensitivity. Historical O/E images are style references,
not authority to replace the validated 6,259-case result with their 6,192-case
snapshot. No scientific result changed.

The primary question remains: “How does rural injury-accident occurrence vary
with weather, particularly strong wind, after accounting as far as possible for
local weather frequency and traffic exposure?” Q1–Q3 are complementary analysis
stages, not artificial separate questions for every model.

## Main figures and denominators

- Figures **4.2–4.4**: baseline wind/gust/temperature, All year + seasons.
  O/E divides event-time observed accidents by expected counts from local
  station-season weather frequency and each injury group's accident totals.
- Figure **4.5**: traffic response, observed/calendar-expected allocated traffic.
- Figures **4.6–4.8**: approximate full-period correction; the same accident
  counts divided by traffic-reweighted expected counts. Grey original/corrected
  comparisons and grouped disjoint injury views serve different purposes.
- Figures **4.9–4.11**: period-specific baseline and counter-era correction,
  retained within the traffic-correction story.
- Figures **4.12–4.14**: MAIN monthly-frequency rates: All year wind/gust,
  seasonal mean wind, seasonal gust. Every denominator is
  sum(daily traffic × rural section length × pooled station-month bin frequency).
  Every numerator uses actual accident-time weather. All eligible counter-days,
  including accident-free days, contribute exposure.
- Figures **4.15–4.18**: SAME-DAY SENSITIVITY: All year three-parameter figure,
  then seasonal wind, gust and temperature. Exposure is
  sum(daily traffic × rural length × observed same-day bin minutes /1,020).
  Missing weather minutes contribute no exposure. This is not the main denominator.

No monthly temperature rate was fabricated. Exact files and definitions:
[method comparison](monthly_vs_sameday_figure_comparison.md).

## Visual presentation and y-axis settings

Source rate style is recovered from Kristján-authored commits bfd799f/c90f735:
light blue #79BCE0 below red #D62728, stacked rates, black count labels, separate
All year vertical panels and four-season 2×2 figures. Blue is minor injury
(code 3), red serious/fatal (codes 1–2). Zero labels are suppressed.

- Main monthly All year wind/gust: **0–1.3** each.
- Main monthly seasonal wind: **0–0.8**; gust: **0–0.5**.
- Same-day sensitivity: same wind/gust settings; temperature All year **0–0.3**,
  seasonal **0–0.6** under the original temperature-only automatic rule.
- Corrected counter-era O/E: **0–6 / 0–6 / 0–2** for wind/gust/temperature.
- Other O/E figures retain their original automatic rules on validated data.
  No manual source setting is claimed for later comparison additions.

The source's wind/gust seasonal upper-bin combinations (≥15/≥20) are retained;
counts and exposure are summed before rates are calculated. Fine All year bins
and scientific tables remain unchanged. O/E severity ratios are grouped, not
stacked, because their expected-count denominators differ. All recovered O/E
reference lines remain. Detailed limits: [figure specification](kristjan_main_figure_spec.md).

This pass retained the source-style rate figures already in the working tree.
Only four O/E assets needed regeneration to move the All year annotation away
from upper-bar counts. No figure family was removed. Superseded five-panel
monthly/same-day assets remain on disk and are not included in the thesis.

## Severity proof

For all **60 fine-bin parameter × period × bin cells**:

- Maximum discrepancy in summed observed counts: **0**.
- Maximum discrepancy in summed rates: **1.1102230246251565e-16**.
- The severity groups share exactly the same exposure within every cell.
- Each parameter's All year counts sum to **694**.

The existing fine-bin test remains; a new test checks every displayed combined
seasonal cell, common exposure and intended wind/gust tail bins. Thus both the
scientific decomposition and the plotted aggregation are verified.

## Results structure

4.1 Study Sample and Coverage
4.2 Weather-Frequency Baseline
4.3 Traffic Response and Approximate O/E Correction
    Traffic behaviour; full-period correction; period/counter-era comparison
4.4 Counter-Based Accident Rates
    Main monthly All year wind/gust; seasonal wind; seasonal gust
4.5 Same-Day Weather Allocation Sensitivity
    All year and seasonal wind/gust/temperature
4.6 Secondary Robustness Checks
    Matched-time, older annual/allocated models and secondary weather checks

Methods now explain why typical station-month weather stabilises the allocation
while preserving actual daily traffic variation, and why same-day allocation is
more sensitive to individual storm days, weather completeness and within-day
assumptions. Neither is causal. Simplified Abstract/Ágrip retained; no numeric
bundle added. Table 3.3 remains the cleaned accident example. Tables 4.3/4.4
preserve exact evidence, and prose interprets rather than narrates every bar.

## Validation and delivery

- **79 tests passed; 1 skipped; 18 subtests passed.**
- `git diff --check` passed.
- Four successful sequential real-figure LaTeX builds; the final two follow
  the last layout correction.
- **71 pages, 23 figures, 18 tables.**
- No undefined references/citations, duplicate labels or overfull boxes.
- Seven pre-existing underfull-box notices remain; these are spacing notices.
- All figure/table labels are referenced in text.
- All main figure assets visually inspected and checked in the compiled thesis;
  the previously stranded seasonal paragraph is now with its figure.
- All **75 scientific CSVs** match the starting SHA-256 snapshot.
- No reader-facing Fall, no zero-count bar labels, All year panel wording retained.
- Named delivery PDF updated from the final compiled draft. No commit or push.

## Scientific values preserved

Baseline wind/gust O/E 2.15 / 3.34; approximate correction 2.71 / 4.20.
Monthly: 694 accidents, 533,649 eligible section-days and 5,630,267,210
estimated vehicle-km. Upper wind: 11 accidents, .667 per million vehicle-km,
5.83× baseline; upper gust: 11, .866, 7.78×. Composition diagnostic 3.39 / 4.84.
Values are unchanged; displayed decimal rounding is intentional.

## Remaining supervisor questions

1. Full 24-hour counts allocated with 07:00–24:00 weather, while numerator
   accidents are daytime: confirm this exposure convention.
2. Nearest weather observation may cross midnight within ±5 minutes: confirm
   this convention; traffic date stays the accident date.
3. Agree future scope for road/base-rate composition work; none was added here.

The primary monthly-versus-same-day choice is resolved by the user's latest
instructions and is no longer a pending approval question. The historical O/E
input discrepancy remains documented for provenance, not used to change results.
