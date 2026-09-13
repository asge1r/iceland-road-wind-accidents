# Fix-only diff summary

This summary excludes the pre-existing unstaged thesis, annual-result, methods and validation changes.

| Production area | Change |
| --- | --- |
| `src/weather/eligibility.py` | New 15-line shared temperature rule |
| `src/weather/frequency.py` | Filter temperature denominator using the shared rule |
| `src/accidents/match_weather.py` | Import existing bounds from their shared owner |
| `src/accidents/case_control.py` | Share temperature eligibility; regenerate stale controls in isolation |
| `src/analysis/oe_analysis.py` | Explicitly enforce temperature case eligibility |
| `src/traffic/counter_day_weather.py` | Distinct-slot mask, cross-row-group union, auditable slot counts and eligibility |
| `tests/test_scientific_bugfixes.py` | Five targeted tests including complete canonical-source reproduction |
| `docs/pre_submission_bugfix_report.md` | Complete scientific report and thesis-impact list |
| `docs/pre_submission_bugfix/` | Before/after evidence, source hashes, exact IDs, replay scripts and validation record |

No unrelated refactors, module moves, model-assumption changes or live product edits. Most added lines below are comparison data and ID/hash manifests, not production code. All added documentation also includes this summary and the isolated validation record.

```text
 .../pre_submission_bugfix/all_table_comparison.csv |  41 ++
 docs/pre_submission_bugfix/cadence_diagnostic.py   |  29 +
 .../cadence_source_check.json                      |   6 +
 docs/pre_submission_bugfix/cadence_trace.json      |  47 ++
 .../cadence_weighting_diagnostic.csv               | 161 +++++
 .../canonical_input_hashes.json                    |  21 +
 .../changed_numeric_cells.csv                      | 277 ++++++++
 docs/pre_submission_bugfix/check_unchanged.py      |  16 +
 docs/pre_submission_bugfix/compare.py              |  87 +++
 docs/pre_submission_bugfix/control_row_changes.csv |   6 +
 .../coverage_changed_days.csv                      |   3 +
 .../daily_vkt_all_injury_comparison.csv            |  21 +
 .../pre_submission_bugfix/daily_vkt_comparison.csv | 201 ++++++
 docs/pre_submission_bugfix/diagnose.py             |  47 ++
 ...extra_temperature_controls_frozen_run_trace.csv |   6 +
 .../extra_temperature_controls_raw_weather.csv     |   6 +
 docs/pre_submission_bugfix/f_excluded_ids.csv      |   3 +
 docs/pre_submission_bugfix/f_retained_ids.csv      | 614 +++++++++++++++++
 docs/pre_submission_bugfix/fg_excluded_ids.csv     |   3 +
 docs/pre_submission_bugfix/fg_retained_ids.csv     | 614 +++++++++++++++++
 docs/pre_submission_bugfix/initialize.py           |  25 +
 .../matched_weather_comparison.csv                 |  20 +
 docs/pre_submission_bugfix/midnight_primary.csv    |   5 +
 docs/pre_submission_bugfix/midnight_strict.csv     |   4 +
 docs/pre_submission_bugfix/oe_coverage_checks.csv  |  31 +
 docs/pre_submission_bugfix/protected_before.json   | 750 +++++++++++++++++++++
 docs/pre_submission_bugfix/recompute.py            |  70 ++
 docs/pre_submission_bugfix/rounded_oe_changes.csv  |  11 +
 docs/pre_submission_bugfix/strict_summary.json     |  26 +
 .../temperature_excluded_ids.csv                   |   3 +
 .../temperature_rate_comparison.csv                |  10 +
 .../temperature_retained_ids.csv                   | 614 +++++++++++++++++
 docs/pre_submission_bugfix/verification.json       |   9 +
 docs/pre_submission_bugfix/verify.py               |  68 ++
 .../weather_model_comparison.csv                   |  12 +
 .../weather_oe_comparison.csv                      | 201 ++++++
 docs/pre_submission_bugfix/write_report.py         | 210 ++++++
 docs/pre_submission_bugfix/year_oe_comparison.csv  |  14 +
 docs/pre_submission_bugfix_report.md               | 234 +++++++
 src/accidents/case_control.py                      |   6 +-
 src/accidents/match_weather.py                     |   4 +-
 src/analysis/oe_analysis.py                        |   3 +
 src/traffic/counter_day_weather.py                 |  43 +-
 src/weather/eligibility.py                         |  15 +
 src/weather/frequency.py                           |   4 +-
 tests/test_scientific_bugfixes.py                  |  95 +++
 46 files changed, 4686 insertions(+), 10 deletions(-)
```
