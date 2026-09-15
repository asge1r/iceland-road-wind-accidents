# Final figure readability and method-comparison pass

## Scope and outcome

The direct user clarification targets y-axis changes at **Figures 4.2–4.4**.
Only those figures' y limits changed. Previously recovered manual rate and
corrected-period limits are preserved. No figure family was removed, and
monthly-frequency science remains MAIN; same-day allocation remains SENSITIVITY.

## Text and table added

**Table 3.9**, `tab:allocation-comparison`, in the Q3 Methods compares traffic
and road input, weather allocation, accident classification, accident-free
days, absence of hourly traffic, advantage, limitation and role. It is explicitly
referenced in its preceding paragraph. This adds one table: **19 total**.

The accompanying paragraph explains why typical station-month weather provides
stable allocation with only daily traffic totals, while retaining day-to-day
traffic variation and depending less on individual storm days or missing
within-day observations. It also states the useful advantage of realised
same-day weather and the associated within-day allocation assumption.

Discussion adds one short paragraph: monthly allocation is preferred for the
available daily totals; same-day is a useful sensitivity; agreement supports
the direction; different exposure allocations explain why magnitudes differ;
neither observes hourly traffic. No numerical bundle was added.

The denominator remains exactly sum(C_jd × L_j × p_station,month,bin), and the
numerator remains actual accident-time weather. Same-day uses observed bin
minutes/1,020 and excludes unobserved time. Neither method is described as causal.

## Axis changes

Every baseline panel starts at zero and now shows its own y ticks. No manual
baseline panel limits were recovered from a0d4468, ee74db4 or c90f735; the new
limits implement the explicit panel-readability instruction using the existing
validated bars. Limits are clean rounded values above maximum O/E/.86.

Panel order below: All year, Winter, Spring, Summer, Autumn.

| Figure | Old common upper limit | New per-panel upper limits |
|---|---:|---|
| 4.2 mean wind | 8.673847 | 2.6, 2.2, 8.6, 3.4, 4.2 |
| 4.3 gust | 14.357495 | 4.2, 3.0, 16.0, 9.2, 6.0 |
| 4.4 temperature | 2.575295 | 2.0, 1.6, 2.6, 2.0, 2.2 |

Tallest bars now occupy **76.0–85.7%** of panel height. Counts and O/E=1
remain visible; no axes are broken or truncated. Some unchanged source rate
panels have low occupancy; these are explicitly flagged, rather than overriding
the user's instruction to retain the already-fixed rate scales.

The [axis audit](figure_axis_readability_audit.md) records all **63 thesis bar
panels**, including horizontal composition panels, with maxima, limits, ratios,
flags and dispositions. The [main figure specification](kristjan_main_figure_spec.md)
links the final panel values and preserves their source history.

## Palette changes

- **4.1:** grey counts → original slate #547A99; grey coverage line → repository
  traffic teal #287271. The coverage line still explicitly combines identical
  wind/temperature percentages.
- **4.5, traffic response** (earlier numbered 4.8): grey → Kristján's original
  #4C9ED9 from c90f735. The 100% line stays grey.
- **4.6–4.7, method comparison** (earlier numbered 4.5–4.6): grey → teal
  #287271, original outlined and corrected filled. No supervisor original
  exists for these later comparison additions, so this deliberate use of the
  existing repository traffic palette is documented rather than misattributed.
- **A.1:** grey → original green/slate/gold category palette from HEAD.
- Current **4.8** already uses the intended injury palette and is unchanged.

Light blue #79BCE0 always means minor injury; red #D62728 always means
serious/fatal in injury plots. Distinct original slate/traffic-blue swatches
have explicitly labelled count/traffic roles. No corrected estimate uses red.
Remaining grey marks are reference lines, grids or deliberately de-emphasised
map populations. The [colour audit](figure_color_semantics_audit.md) lists all
23 figures and their series semantics.

## Validation

- `python -m pytest tests -q`: **79 passed, 1 skipped; 18 subtests passed**.
- `git diff --check`: passed.
- Four successful sequential real-figure builds; the final two follow the
  table's ragged-right formatting refinement.
- Final thesis: **71 pages, 23 figures, 19 tables**.
- No undefined references/citations, duplicate labels, overfull boxes or broken floats.
- Seven existing underfull spacing notices remain; the new table adds none.
- Every Results figure visually inspected in the compiled PDF; main monthly
  and same-day figures compared. The new table and changed scales/palettes
  were inspected directly. No visible Fall, zero-count labels or clipped labels.
- All 42 figure/table labels have prose references.
- All 75 scientific CSVs match the starting SHA-256 snapshot. No scientific
  number, selection, bin calculation or denominator changed.
- Named delivery PDF updated from the final compiled draft.
- No reset, commit or push.

## Remaining supervisor questions

The full 24-hour count / 07:00–24:00 weather convention and cross-midnight
±5-minute matching remain explicit assumptions for discussion. The choice of
monthly main versus same-day sensitivity is resolved. Future road-composition
work remains future work.
