# Joint weather revision — 17 September 2026

Completed the detailed descriptive joint analysis, reference cleanup, Results
interpretation, figure ordering and expanded Future work. This report covers this
revision only. Pre-existing working-tree changes were preserved. Nothing was
staged, committed or pushed.

## Verification

- Final PDF: 46 pages. Clean three-pass LaTeX rebuild: zero warnings, undefined references/citations, duplicate labels or overfull boxes.
- Complete project suite: `MPLCONFIGDIR=/private/tmp/matplotlib .venv/bin/python -m pytest tests -q`: 121 passed, 1 skipped, 18 subtests passed (7.60 s).
- Primary validation and detailed-joint validation both passed.
- Clean pipeline built all outputs in an initially empty reports tree. All 22 pre-existing CSV outputs rebuilt byte-for-byte unchanged, including the coarse joint results.
- All 16 referenced generated LaTeX fragments matched the clean build. All 20 annotations in the rendered PDF matched the generated data.
- All 21 bibliography entries are cited and every citation resolves. ITA (2015) and Ahmed et al. (2012) removed; ITA (2026) and Zhan et al. (2020) retained.
- Future work contains 546 whitespace-delimited words and covers all seven requested topics.
- Visually inspected PDF pages 25–46: annual counts, all Results figures and text, Discussion, Future work, Conclusion and Bibliography. Heatmap annotations also inspected in grayscale at final page size.
- New Figure 4.6 replaces the coarse Table 4.2. The former Figures 4.7–4.10 are now 4.8–4.11. Figures 4.8 and 4.9 follow Section 4.3.2, Figure 4.10 precedes Section 4.3.3, and Figure 4.11 precedes Section 4.4.
- Local placeins v2.2 is included and allowlisted in `.gitignore`; barriers are local, with no global forced placement.
- Initial unrestricted pytest discovery entered archived repository copies and failed collection on duplicate module names. The documented complete `tests/` suite passed. Arrow emitted harmless sandbox CPU-cache detection messages during the pipeline; validation initially used a fallback Matplotlib cache directory. These did not affect results and are not LaTeX warnings.

## Scientific interpretation and reconciliation

The eligible sample remains 6,259 accidents. All were checked against a single
archive observation containing their wind, gust and temperature, explicitly
resolving potential opposite-sign five-minute ties. The simultaneous background
contains 230,447,085 valid observations, each assigned exactly once. Expected
counts use actual joint station–season frequencies, never products of marginals.
Both observed and expected cell totals equal 6,259 (floating-point tolerance
1e-8 for expected counts).

The requested 0–6°C display bin crosses the old 3°C boundary. It is mathematically
impossible to recover the old split from those 20 displayed totals alone. The
pipeline retains 24 atomic cells with separate 0–3 and 3–6°C components.
Aggregating these reproduces both the 20 display cells and the original four
cells. Exact station–season observation counts reconcile as well. No proportional
split or revised interpretation was used to conceal a discrepancy.

O/E means occurrence relative to local weather-time frequency, not a vehicle-based
rate or causal risk. High/low-wind contrasts vary descriptively across temperature
groups; no formal interaction or p-value is estimated. The largest O/E is the
only sparse cell and is not interpreted as a strong combined effect. Behavioural
adaptation, avoidance, closures, vehicle composition and physical weather effects
cannot be separated with these data; Discussion treats them as hypotheses.

## All 20 cells

Intervals are half-open at the upper endpoint within the existing quality limits.
The CSV retains full precision; E, O/E and percentages below are rounded to six decimals.

| Wind (m/s) | Temperature (°C) | Observed | Expected | O/E | Sample (%) | Sparse |
|---|---|---:|---:|---:|---:|---|
| 0–5 | <−3 | 292 | 393.953121 | 0.741205 | 4.665282 | No |
| 0–5 | −3–0 | 418 | 386.866137 | 1.080477 | 6.678383 | No |
| 0–5 | 0–6 | 1001 | 1116.922914 | 0.896212 | 15.992970 | No |
| 0–5 | 6–12 | 959 | 1138.393526 | 0.842415 | 15.321936 | No |
| 0–5 | ≥12 | 486 | 302.979512 | 1.604069 | 7.764819 | No |
| 5–10 | <−3 | 194 | 197.977350 | 0.979910 | 3.099537 | No |
| 5–10 | −3–0 | 300 | 252.368297 | 1.188739 | 4.793098 | No |
| 5–10 | 0–6 | 689 | 776.085594 | 0.887789 | 11.008148 | No |
| 5–10 | 6–12 | 677 | 677.969311 | 0.998570 | 10.816424 | No |
| 5–10 | ≥12 | 263 | 164.446998 | 1.599299 | 4.201949 | No |
| 10–15 | <−3 | 98 | 70.838317 | 1.383432 | 1.565745 | No |
| 10–15 | −3–0 | 156 | 105.321827 | 1.481174 | 2.492411 | No |
| 10–15 | 0–6 | 242 | 283.876280 | 0.852484 | 3.866432 | No |
| 10–15 | 6–12 | 166 | 186.525543 | 0.889959 | 2.652181 | No |
| 10–15 | ≥12 | 33 | 23.639467 | 1.395971 | 0.527241 | No |
| ≥15 | <−3 | 42 | 23.130590 | 1.815777 | 0.671034 | No |
| ≥15 | −3–0 | 74 | 34.464182 | 2.147157 | 1.182297 | No |
| ≥15 | 0–6 | 93 | 82.830882 | 1.122770 | 1.485860 | No |
| ≥15 | 6–12 | 69 | 37.709679 | 1.829769 | 1.102413 | No |
| ≥15 | ≥12 | 7 | 2.700474 | 2.592137 | 0.111839 | Yes* |

*Only sparse cell: wind ≥15 m/s, temperature ≥12°C, O=7, E=2.700474. Sparse means O<10 or E<5.

## Descriptive contrasts

High/low wind compares ≥15 with 0–5 m/s. Warm/moderate temperature compares ≥12 with 6–12°C; below-freezing/moderate compares −3–0 with 6–12°C. Both cells must have O≥10 and E≥5. These are O/E ratios, not relative risks or interaction estimates.

| Contrast | Stratum | O/E ratio |
|---|---|---:|
| High/low wind | <−3 | 2.449764 |
| High/low wind | −3–0 | 1.987230 |
| High/low wind | 0–6 | 1.252794 |
| High/low wind | 6–12 | 2.172051 |
| High/low wind | ≥12 | Withheld: sparse cell |
| Warm/moderate temperature | 0–5 | 1.904131 |
| Below-freezing/moderate temperature | 0–5 | 1.282595 |
| Warm/moderate temperature | 5–10 | 1.601589 |
| Below-freezing/moderate temperature | 5–10 | 1.190441 |
| Warm/moderate temperature | 10–15 | 1.568579 |
| Below-freezing/moderate temperature | 10–15 | 1.664318 |
| Warm/moderate temperature | ≥15 | Withheld: sparse cell |
| Below-freezing/moderate temperature | ≥15 | 1.173458 |

## Coarse reconciliation

Order: low-wind/cold, low-wind/warm, high-wind/cold, high-wind/warm; cutoffs 15 m/s and 3°C.

| Category | Observed | Expected | O/E |
|---|---:|---:|---:|
| 0 | 2621 | 2485.931192 | 1.054333 |
| 1 | 3353 | 3592.233002 | 0.933403 |
| 2 | 170 | 101.646331 | 1.672466 |
| 3 | 115 | 79.189475 | 1.452213 |

## Files changed or added in this revision

- `.gitignore`
- `docs/joint_weather_revision_20260917.md`
- `docs/pipeline.md`
- `reports/main/figures/joint_wind_temperature_detail.pdf`
- `reports/main/figures/joint_wind_temperature_detail.png`
- `reports/main/tables/joint_wind_temperature_contrasts.csv`
- `reports/main/tables/joint_wind_temperature_detail.csv`
- `reports/thesis/Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf`
- `reports/thesis/content.tex`
- `reports/thesis/draft_en.tex`
- `reports/thesis/generated/gust_seasonal_results.tex`
- `reports/thesis/generated/joint_detail_discussion.tex`
- `reports/thesis/generated/joint_detail_results.tex`
- `reports/thesis/generated/mean_wind_seasonal_results.tex`
- `reports/thesis/generated/temperature_oe_results.tex`
- `reports/thesis/generated/traffic_response_results.tex`
- `reports/thesis/placeins.sty`
- `reports/working/tables/joint_atomic_frequency.csv`
- `reports/working/tables/joint_atomic_oe.csv`
- `reports/working/tables/joint_coarse_reconciliation.csv`
- `reports/working/tables/joint_detail_validation.json`
- `reports/working/tables/joint_simultaneous_events.csv`
- `src/figures/joint_detail.py`
- `src/tables/joint_detail.py`
- `src/tables/results_context.py`
- `src/thesis_pipeline.py`
- `src/validation/cli.py`
- `src/validation/joint_detail.py`
- `tests/test_joint_detail.py`

The ignored audit directory `reports/working/joint_detail_20260917/` contains initial hashes/status, logs, preservation checks and the file manifest. Clean build and rendered pages are in `/private/tmp/thesis-joint-clean-20260917/`. Protected `draft_en.pdf` and `src/figures/presentation.py` were not edited.

Final PDF SHA-256: `5d397fc585e0f38f14ace781c4df59d35c913d4351aab1a2c5e151368e4f2c18`.
