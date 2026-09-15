> Current status: the final method-alignment instructions confirm monthly allocation
> as MAIN and same-day as SENSITIVITY, while preserving validated scientific results.
> This historical audit is superseded by [the final method audit](kristjan_method_alignment_audit.md),
> [figure specification](kristjan_main_figure_spec.md) and
> [method comparison](monthly_vs_sameday_figure_comparison.md).

# Kristján-style figures and theory alignment

## Current scope and interpretation

This updates the supervisor figure inventory after the reader-clarity pass.
The starting working tree was preserved. Sources inspected include the active
thesis, current generators and CSVs, `kristjan_20260914_analysis_alignment.md`,
`kristjan_next_meeting_brief.md`, the preceding figure inventory and
`final_reader_clarity_audit.md`. The style reference is the repository's
supervisor-aligned Q1 and same-day figure families; no unprovided external
original artwork was claimed as inspected.

The user's comment that Q3 should concern Figures 4.14–4.16 is implemented by
placing these figures inside Q3 and explaining their alternative exposure
allocation. The explicit pasted specification retains monthly allocation as
the main method and same-day allocation as sensitivity. Promoting same-day
allocation to the primary Q3 definition would be a separate decision: its
rates cannot be assigned the monthly method's validated headline numbers.

## Question → method → numerator → denominator → role

| Family / current figures | Intended question | Numerator | Denominator and weather | Grouping / role |
|---|---|---|---|---|
| Q1, 4.2–4.4 | Are accidents over-represented relative to local weather time? | Actual matched event-time counts | Station × season frequency times each injury group's accident totals; no traffic | Disjoint blue/red; All year + seasons; primary Q1 |
| Q2 comparison, 4.5–4.6 | Does accounting for lower traffic explain the strong-wind pattern? | Same all-injury counts as Q1 | Q1 frequency versus frequency × counter traffic response, renormalised within stratum | Neutral outline/filled method comparison; All year; main Q2 sensitivity |
| Q2 injury view, 4.7 | Is the corrected pattern present in both injury groups? | Minor and serious/fatal event counts | Each group's own traffic-reweighted expected counts | Disjoint grouped blue/red; All year; Q2 |
| Traffic response, 4.8 | How does traffic change with weather? | Pooled observed traffic allocated by weather minutes | Pooled calendar-expected traffic allocated by the same weather minutes | No injury grouping; All year; Q2 mechanism |
| Period comparison, 4.9–4.11 | Does the counter era or correction within it alter interpretation? | Event counts restricted to 2007–2018 or 2019–2024 | Same-period station-season weather frequency; correction additionally applied within 2019–2024 | Disjoint grouped blue/red; three parameters; All year; Q2 period sensitivity |
| Monthly rates, 4.12–4.13 | What rates follow from daily traffic allocated by typical monthly weather? | Eligible actual accident-time wind/gust counts | Sum daily traffic × rural length × pooled station-month weather frequency | Shared exposure; disjoint stacked components; All year + seasons; Q3 main |
| Same-day rates, 4.14–4.16 | What changes if exposure follows weather observed on the actual day? | Actual accident-time counts in the linked sample | Sum daily traffic × rural length × observed bin minutes / 1020; missing weather time excluded | Shared exposure; disjoint stacks; three parameters; All year + seasons; Q3 allocation sensitivity |
| Other checks | Does the wind association persist under other conditioning? | Their documented accident populations | Matched calendar controls or separate annual/allocated exposure models | §4.5 and appendix; not alternative Q2/Q3 definitions |

## Source and output mapping

- Q1: `reports/main/tables/weather_oe.csv` → `src/figures/oe_histo.py` →
  `wind_oe_panels.png`, `gust_oe_panels.png`, `temperature_oe_panels.png`.
- Q2: `weather_oe_traffic_corrected.csv` → `traffic_corrected_oe.py` →
  `weather_oe_traffic_corrected_f.png`, `_fg.png`, and the combined injury view.
- Traffic response: `data/analysis/traffic_weather_response.csv` →
  `traffic_weather_response.py` → `traffic_weather_response.png`.
- Period sensitivity: `weather_oe_2007_2018.csv`, `weather_oe_2019_2024.csv`,
  `weather_oe_traffic_corrected_2019_2024.csv` → the corresponding three PNGs.
  The original and corrected period outputs were reproduced in the preceding
  alignment pass and remain unchanged.
- Monthly rates: `data/analysis/monthly_vkt.csv`, `monthly_vkt_section.csv`,
  and existing `data/processed/traffic/counter_accidents.csv` →
  `src/tables/monthly_vkt_rate.py::severity_rates` →
  `monthly_vkt_f_panels.png`, `monthly_vkt_fg_panels.png`.
- Same-day rates: `data/analysis/daily_vkt.csv` → `weather_rate.py` →
  `f_same_day_vkt_panels.png`, `fg_same_day_vkt_panels.png`,
  `temperature_same_day_vkt_panels.png`.

All image paths above are under `reports/main/figures/`. No new analysis CSV
was written. The severity split is computed for presentation from unchanged
eligible event records and stored exposure.

## Stable colour meaning and decomposition proof

Blue means minor injury only (code 3); red means serious or fatal injury
(codes 1–2). The groups do not overlap. All injury is their combined total.
Q1/Q2 expected counts are calculated separately by injury group; their O/E
bars are grouped and must not be stacked. Rate components share exposure,
so stacked bars are appropriate and follow the existing same-day rate family.

The old all-blue monthly figures (old 4.9–4.10, now 4.12–4.13) were changed
to blue/red stacks. Q2's blue method styling was changed to grey outline/filled
bars. Traffic-response bars, year-by-year all-injury counts and the vehicle-count
profile now use grey. The accident map uses grey/gold for ordinary/strong-wind
locations. These colours no longer imply injury categories.

`severity_rates` checks unique event IDs and valid injury codes, reproduces
stored counts in every section-year-season-bin, and uses the same stored
exposure for both injury components. It also reproduces the existing published
All year injury-specific rates. Across **60 parameter × period × bin cells**:

- Maximum count-sum discrepancy: **0**.
- Maximum rate-sum discrepancy: **1.1102230246251565e-16**.
- Seasonal component counts reconstruct All year counts for each parameter,
  injury group and bin.
- Each parameter retains **694** total All year accidents.
- Mean wind ≥20: **8 minor + 3 serious/fatal = 11**; rates approximately
  0.484739 + 0.181777 = the unchanged 0.667 per million vehicle-km headline.
- Gust ≥30: **7 minor + 4 serious/fatal = 11**; rates approximately
  0.551360 + 0.315063 = the unchanged 0.866 headline.

Automated tests check all cells, shared exposure, seasonal sums and rejection
of invalid or missing event records. The decomposition is descriptive; it is
not a severity model or evidence of a causal severity difference.

## All 21 figures: visual and semantic audit

Every row below was visually inspected in the compiled PDF. For every
count-labelled figure, zero count labels are absent; axis zeros remain.
Rate labels that cannot fit legibly or would collide are omitted. “Four seasons”
means Winter, Spring, Summer, Autumn, in that order after All year. O/E axes
state observed/expected accidents; rate axes use vehicle-km. No pooled panel
is labelled Annual, Overall, Fall or All year with a month suffix.

| Current figure / page (old number) | Purpose / parameter | Years | Seasons | Colour meaning / layout | Counts | Reference line | Axes / in-image titles |
|---|---|---|---|---|---|---|---|
| 3.1, p. 7 (was 3.1) | Data geography; mean wind highlight | 2007–2025 | No seasonal panels | Grey / gold; neither severity colour | Legend counts; no bar labels | None | Longitude / latitude; no in-image title |
| 3.2, p. 11 (was 3.2) | Descriptive hour, season, daylight, temperature | 2007–2025 | Season categories, not panels | Blue minor; red serious/fatal; stacked | Positive total counts | None | Accidents; short descriptive panel titles |
| 4.1, p. 20 (was 4.1) | Coverage; wind/temperature matches | 2007–2025 | Year-by-year, not pooled weather bins | Grey all injury and coverage | No bar-count labels | None | Accidents / matched accidents (%); rural accidents by year / weather-match coverage |
| 4.2, p. 22 (was 4.2) | Q1 mean wind | 2007–2025 | All year + four seasons | Blue minor; red serious/fatal; grouped | Positive component counts | O/E = 1 | Mean wind (m/s); O/E; simple season titles |
| 4.3, p. 23 (was 4.3) | Q1 gust | 2007–2025 | All year + four seasons | Blue minor; red serious/fatal; grouped | Positive component counts | O/E = 1 | Wind gust (m/s); O/E; simple season titles |
| 4.4, p. 24 (was 4.4) | Q1 temperature | 2007–2025 | All year + four seasons | Blue minor; red serious/fatal; grouped | Positive component counts | O/E = 1 | Temperature (°C); O/E; simple season titles |
| 4.5, p. 25 (was 4.5) | Q2 method comparison; mean wind | 2007–2025 | All year | Grey outline original / filled corrected; all injury | Upper-bin O/E change; no count duplication | O/E = 1 | Mean wind (m/s); O/E; Mean wind / All year |
| 4.6, p. 26 (was 4.6) | Q2 method comparison; gust | 2007–2025 | All year | Grey outline original / filled corrected; all injury | Upper-bin O/E change; no count duplication | O/E = 1 | Wind gust (m/s); O/E; Wind gust / All year |
| 4.7, p. 27 (was 4.7) | Q2 injury view; wind/gust | 2007–2025 | All year | Blue minor; red serious/fatal; grouped | Positive component counts | O/E = 1 | Weather units / O/E; parameter / All year |
| 4.8, p. 28 (was 4.8) | Q2 traffic response; wind/gust/temperature | 2019–2024 | All year | Grey traffic, no severity encoding | Percentage changes, one decimal | 100% | Observed/expected traffic (%); parameter / All year |
| 4.9, p. 30 (was 4.11) | Q2 earlier-period sensitivity; three parameters | 2007–2018 | All year | Blue minor; red serious/fatal; grouped | Positive component counts | O/E = 1 | Weather units / O/E; parameter / All year |
| 4.10, p. 31 (was 4.12) | Q2 counter-era sensitivity; three parameters | 2019–2024 | All year | Blue minor; red serious/fatal; grouped | Positive component counts | O/E = 1 | Weather units / O/E; parameter / All year |
| 4.11, p. 32 (was 4.13) | Q2 counter-era correction; three parameters | 2019–2024 | All year | Blue minor; red serious/fatal; grouped | Positive component counts | O/E = 1 | Weather units / O/E; parameter / All year |
| 4.12, p. 34 (was 4.9) | Q3 monthly-allocation mean wind | 2019–2024 | All year + four seasons | Blue minor; red serious/fatal; stacked | Readable positive component counts | None: absolute rate | Mean wind (m/s); accidents per million vehicle-km; season titles |
| 4.13, p. 35 (was 4.10) | Q3 monthly-allocation gust | 2019–2024 | All year + four seasons | Blue minor; red serious/fatal; stacked | Readable positive component counts | None: absolute rate | Wind gust (m/s); accidents per million vehicle-km; season titles |
| 4.14, p. 37 (was 4.14) | Q3 same-day sensitivity; mean wind | 2019–2024 | All year + four seasons | Blue minor; red serious/fatal; stacked | Readable positive component counts | None: absolute rate | Mean wind (m/s); accidents per million vehicle-km; season titles |
| 4.15, p. 38 (was 4.15) | Q3 same-day sensitivity; gust | 2019–2024 | All year + four seasons | Blue minor; red serious/fatal; stacked | Readable positive component counts | None: absolute rate | Wind gust (m/s); accidents per million vehicle-km; season titles |
| 4.16, p. 39 (was 4.16) | Q3 same-day sensitivity; temperature | 2019–2024 | All year + four seasons | Blue minor; red serious/fatal; stacked | Readable positive component counts | None: absolute rate | Temperature (°C); accidents per million vehicle-km; season titles |
| A.1, p. 49 (was A.1) | Other support; involved vehicles | 2007–2025 | No season panels | Grey all-injury counts | Positive counts and shares | None | Vehicles / accidents; Vehicles involved in rural injury accidents |
| A.2, p. 50 (was A.2) | Other support; accident composition | 2007–2025 | No season panels | Blue minor; red serious/fatal; grouped | No count labels | None | Share within severity group (%); Accident types by injury severity |
| A.3, p. 52 (was A.3) | Other support; linkage coverage | 2019–2024 | No season panels | Grey/gold/teal/black linkage categories; no severity encoding | Legend counts; no bars | None | Longitude / latitude; Daily-counter coverage |

## Final Results hierarchy and renumbering

- **4.1 Study Sample and Coverage** — coverage and unchanged selection Table 4.2.
- **4.2 Q1** — mean wind, gust, temperature.
- **4.3 Q2** — 4.3.1 Main Correction (direct comparison and injury view),
  4.3.2 Traffic Response, 4.3.3 Period Sensitivity.
- **4.4 Q3** — mean-wind seasonal rates, gust seasonal rates, and
  4.4.3 Same-Day Weather Allocation Sensitivity.
- **4.5 Other Supporting Analyses** — matched-time, secondary weather/severity/
  daylight checks and distinct annual/allocated traffic models.

Old **4.11–4.13 are now 4.9–4.11**, inside Q2's period sensitivity.
Old monthly **4.9–4.10 are now 4.12–4.13**. Same-day **4.14–4.16 keep their
numbers**, but now belong to Q3's allocation sensitivity. No figure was removed.

The old pooled `monthly_vkt_rate.png` remains superseded by the complete
All year + seasons monthly figures. The old `weather_rate_annual.png` and
three `*_traffic_rate_panels.png` layouts remain superseded by the three
same-day figures containing their full parameter/season content. Those older
layouts were not reintroduced as duplicate figures; no result family is omitted.

## Theory, tables and outstanding supervisor questions

Methods now state the question, numerator, denominator, weather definition,
injury groups and seasonal aggregation for each main family. The same-day
formula explicitly uses observed bin minutes / 1020, with missing weather time
excluded; monthly allocation conserves full daily exposure using station-month
fractions. Accident-free eligible counter-days contribute to both methods.
Q2's 2019–2024 response is still an approximate extrapolation to 2007–2025,
not measured hourly risk. The period sensitivity restricts both accidents and
weather before comparing the counter-era correction.

Table 4.3 remains a compact all-injury rate table. Table 4.4 retains the main
wind/gust Q1/Q2/Q3 summary and its different-denominators warning. Table 3.3
remains the coarsened cleaned-record example. All tables retain their numbers;
Table 4.2 remains in §4.1. The simplified Abstract and Ágrip were not changed.
VKT retains its technical definition, vehicle-kilometres travelled, and compact
axes/tables use vehicle-km.

The composition diagnostic remains 3.39 / 4.84 and supports only a partial
composition explanation. The full-day traffic / 07–24 allocation and
cross-midnight matching conventions still need supervisor confirmation.
Dangerous-road/baseline-composition analysis remains deferred to the next meeting.
Whether same-day allocation should replace monthly allocation as the primary
Q3 definition was queried; this pass follows the explicit monthly-main,
same-day-sensitivity specification rather than silently swapping headline rates.

## Validation and final deliverable

- **78 tests passed, 1 optional replay test skipped, 18 subtests passed**.
- All **75 existing scientific CSVs** checked against the start of this pass
  are byte-for-byte unchanged; no new scientific analysis or CSV was created.
- Counts remain **21 figures and 18 tables**, all referenced explicitly before
  their appearance in the expanded source.
- Final real-figure PDF: **67 pages**. Three final sequential builds succeeded;
  the final two have no undefined references/citations, duplicate labels,
  overfull boxes, fatal errors or rerun warnings.
- **Seven underfull-box notices** remain in source tables/bibliography; no
  clipped or malformed table/figure was found in visual review.
- An intermediate build read a source file during an edit and failed. All
  subsequent builds ran against stable sources and completed successfully.
- `git diff --check` passed. No commit or push was made.

The named thesis PDF is copied from and byte-identical to the final `draft_en.pdf`.
This document supersedes the prior audits' figure locations and page counts.
