# Final deadline review — 17 September 2026

This pass continues from the validated 46-page version. It does not rerun the
joint-weather calculation or change any existing numerical CSV output. The final
PDF has 47 pages following the register limitation and targeted Future work additions.

## Figure 4.6

The temperature ticks are now `<−3`, `[−3, 0)`, `[0, 6)`, `[6, 12)`, `≥12`,
with a mathematical minus sign and the unchanged axis title “Temperature interval
(°C)”. They match the computational lower-inclusive, upper-exclusive boundaries,
within the existing temperature quality limits. No categories or values changed.

The requested two Results paragraphs replace the detailed lists. Numbers remain
generated from the existing joint table: supported upper-wind O/E ranges from
1.12 at 0–6°C to 2.15 immediately below freezing; corresponding high/low-wind
contrasts range from 1.25 to 2.45. The maximum cell remains O/E 2.59, O=7,
E=2.70 and is the only sparse cell. All detailed contrasts remain unchanged in
`reports/main/tables/joint_wind_temperature_contrasts.csv`, the validation outputs
and `docs/joint_weather_revision_20260917.md`. Joint Methods and Discussion
interpretation are unchanged. No formal interaction, relative risk or causal
interpretation was added.

## Exact register wording

Section 5.3 now begins:

> The accident register does not capture every traffic injury. Because it is based primarily on police-reported accidents, minor injuries are particularly susceptible to underreporting; health institutions and insurers record additional cases that do not enter the official register (ITA, 2026b).

Source verified on 17 September 2026: [Samgöngustofa, Um slysaskrá](https://www.samgongustofa.is/umferd/tolfraedi/umferdarslys/um-slysaskra/).
The page identifies police reports as the register's basis and explicitly
explains that health institutions and insurers record additional minor injuries.
The thesis neither quantifies underreporting nor assumes it is weather-independent.
The 2026 label follows the existing institutional web-source convention; the
new entry records its access date and does not claim a verified publication date.

Section 3.1.2 adds only:

> These events come from the official register, which is based primarily on police reports (ITA, 2026b).

The existing statistics source is ITA (2026a), key `samgongustofaAccidents`;
the new register description is ITA (2026b), key `samgongustofaRegister`.

## Delivered extracts and independent audit

The filename equivalents are in `data/raw/accidents/`. Reproduce the read-only
audit with `.venv/bin/python -m src.validation.register_sources`; it writes
`reports/working/deadline_review_20260917/register_sources.json`.

| Extract | Rows | Unique accident IDs | Injury codes |
|---|---:|---:|---|
| injuries_2007_2024.txt | 23,131 | 16,143 | 19,557 minor; 3,361 serious; 213 deaths |
| vehicles_2007_2024.txt | 215,982 | 118,249 | Not applicable |
| injuries_2025.txt | 1,241 | 902 | 1,049 minor; 182 serious; 10 deaths |
| vehicles_2025.txt | 15,613 | 8,360 | Not applicable |

All 16,143 accident IDs in the older person extract occur in the older vehicle
extract; the same inclusion holds for the separate 2025 deliveries. Linking to
accident dates confirms 2007–2024 for the older matched records and 2025 for the
newer records. Three vehicle rows, representing two IDs, have no corresponding
record in the older accident extract: their dates cannot be independently
verified. This is an input-linkage issue for future subgroup work, not a change
to any current sample or result. No source records were deleted or altered.

The thesis now says that the 2007–2024 extracts alone exclude 2025, and extending
the subgroup proposals to 2025 would require harmonising the separate deliveries
already present. It does not incorrectly claim that all available person/vehicle
data stop in 2024. The main series remains 2007–2025.

Delivered person fields include age, sex, position, class and injury code;
vehicle fields contain accident ID, vehicle number and class. These may support
composition studies, subject to coding/completeness audits. Vehicle-specific
risk cannot be estimated without vehicle-class traffic exposure. The current
extracts contain no confirmed tourism/nationality indicator and do not contain
police weather, surface, cause or speed fields. A database schema does not imply
those fields were delivered or complete; zero null cells also does not establish
valid or complete coding.

Future work prioritises single-vehicle, departure, overturning and loss-of-control
mechanisms; then passenger-car, van, heavy-goods, bus and motorcycle composition;
then road-surface evidence around freezing, warm-end composition and data-quality
audits. No new subgroup result is presented. Its targeted additions extend the
section to 682 words. A local samepage group keeps the temperature-proposal
paragraph together; there is no global float or page-layout change.

## Dictionary metadata

`accident_codebook.xls` is the supplied dictionary equivalent. Its first worksheet
is titled *Töflulýsingar í slysaskrá*, and further sheets describe `InSkyrsla`,
`InOkutaeki`, `InAdilar`, code-table definitions and code data. The notes explain
police and registry field origins. Schema entries include reported weather,
road surface, recorded cause, and `Raunhradi` (“actual speed according to the
party”). Vehicle-class code definitions cover the proposed comparisons.

Workbook content does not establish a publication/version date. OLE properties
identify an individual author/editor, an abbreviated company field and file
creation/save timestamps, not a reliable institutional publication statement.
Consequently the thesis describes the titled document as accompanying table
descriptions in prose. No invented 2021 institutional bibliography entry or
public URL was added. Neither ITA (2015) nor Ahmed et al. was restored.

## Whole-thesis checks

- The Introduction's weather-occurrence/exposure question is answered by the unchanged Conclusion. Abstracts and all main numerical results are unchanged.
- The three analyses consistently distinguish local weather-time O/E, approximate traffic reweighting, and estimated VKT. The primary 2007–2025 and counter-linked 2019–2024 populations remain distinct.
- Results describe observed patterns; behavioural, avoidance, road-condition and vehicle-composition explanations remain hypotheses. Injury-group comparisons are descriptive, not severity tests.
- All 170 existing CSV files in the initial report snapshot remain byte-identical, including the joint detail and contrasts, atomic/coarse validation products and unrelated results.
- All 22 bibliography entries are cited; every citation resolves. Figure and table references resolve, and Figures 4.7–4.11 remain in their semantic subsections. Figure 4.11 precedes Section 4.4.
- No obsolete matched-time or same-day-VKT analysis language remains. The sole case-crossover occurrence is the correct title of the retained Zhan reference, not a thesis method.
- Visually inspected Figure 4.6, correction figures, Limitations, Future work, Conclusion and Bibliography. Current rendered pages 34–41 are pixel-identical to the previously reviewed pages, including the whole VKT section and Discussion interpretation.
- The heatmap's 20 annotations and retained prose values match the generated data. No clipping or overfull boxes; the sparse-cell marker remains visible.
- Figure-only regeneration and nine joint tests passed. The complete project suite passed: **121 tests, 18 subtests, one skip** (7.35 s). Primary and detailed-joint validation passed. The separate register-source audit passed its requested counts, injury-code and inclusion checks, with the unmatched-row caveat documented above.
- Clean LaTeX rebuild: **47 pages, zero warnings**, no undefined references/citations, duplicate labels or overfull boxes.
- The protected `reports/thesis/draft_en.pdf`, `src/figures/presentation.py`, prior numerical revision report and all unrelated working-tree changes were preserved. Nothing staged, committed or pushed.

No remaining submission-blocking inconsistency was found. The two unmatched
vehicle IDs require investigation before future vehicle-level subgroup analysis;
uncertain dictionary publication metadata has been handled without inventing it.

## Exact changed or added files

- `docs/deadline_review_20260917.md`
- `reports/main/figures/joint_wind_temperature_detail.pdf`
- `reports/main/figures/joint_wind_temperature_detail.png`
- `reports/thesis/Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf`
- `reports/thesis/content.tex`
- `reports/thesis/generated/joint_detail_results.tex`
- `src/figures/joint_detail.py`
- `src/validation/register_sources.py`
- `tests/test_joint_detail.py`

Build log: `reports/thesis/draft_en.log`. Read-only source audit, initial hashes/status, tests, validation, page inventory and preservation evidence: `reports/working/deadline_review_20260917/`. Clean build and rendered pages: `/private/tmp/thesis-deadline-final-20260917/`.

Final PDF SHA-256: `8ded9edd16ce988ad9e3edc7866c3243e8dc379067359d8bac0814f391b72da3`.
