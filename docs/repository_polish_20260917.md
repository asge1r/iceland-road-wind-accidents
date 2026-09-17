# Repository and final document polish — 17 September 2026

## Scope and baseline

Started on `main` at `5add049`, with substantial earlier authorized thesis revisions already uncommitted. Remote: `https://github.com/asge1r/iceland-road-wind-accidents.git`. This pass preserves that scientific baseline. The publication includes its necessary source, tests, current figure assets, generated fragments and seven current numerical CSV snapshots; differences from Git HEAD therefore include earlier revisions, not new calculations in this pass. Unrelated diagnostics, old audit drafts, the local data manifest, `reports/thesis/draft_en.pdf` and `src/figures/presentation.py` remain unstaged.

## Cleanup and storage

Removed 227 reproducible cache/build files, totalling 3,269,203 bytes (3.12 MiB): Python/test caches, stray presentation navigation files and the failed previous presentation build. Tests and document builds regenerate some ignored products, so this is the gross removal, not a claim of equivalent final disk reduction. Narrow ignores cover tool caches, presentation build/ and stray Beamer auxiliary files. No institutional inputs, current figures/CSV outputs, source documents, archives, reproduced snapshots, virtual environment or Git objects were removed.

Initial total allocation was about 23.65 GiB. Data occupy about 15.34 GiB and are required source/intermediate evidence. Archive occupies about 5.82 GiB, including about 4.17 GiB of archived Git metadata: useful history without verified redundancy, retained. Reproduced snapshots occupy about 1.46 GiB; working evidence about 76 MiB; both retained. The virtual environment occupies about 550 MiB and remains useful for the validated Python 3.13 runtime. Active `.git` occupies about 415 MiB (mostly loose objects), separately from working-tree data. No history rewriting or aggressive garbage collection was attempted.

Disposable: caches and document build products. Useful history: archive, reproduced snapshots and working audits. Required evidence: institutional inputs, prepared analysis inputs, current numerical outputs and generated documents. Git-history storage: active `.git` and the separately archived former Git metadata. Larger cleanup needs a later provenance/recoverability review.

### Deleted paths

- `.pytest_cache` — 5 files, 22,329 bytes; reproducible and untracked/ignored.
- `tests/__pycache__` — 51 files, 417,314 bytes; reproducible and untracked/ignored.
- `docs/pre_submission_bugfix/__pycache__` — 3 files, 23,064 bytes; reproducible and untracked/ignored.
- `reports/working/section32_redesign_20260917/before/tests/__pycache__` — 1 files, 36,421 bytes; reproducible and untracked/ignored.
- `src/__pycache__` — 14 files, 99,455 bytes; reproducible and untracked/ignored.
- `src/traffic/__pycache__` — 31 files, 287,423 bytes; reproducible and untracked/ignored.
- `src/tables/__pycache__` — 50 files, 353,592 bytes; reproducible and untracked/ignored.
- `src/analysis/__pycache__` — 7 files, 92,709 bytes; reproducible and untracked/ignored.
- `src/accidents/__pycache__` — 6 files, 55,666 bytes; reproducible and untracked/ignored.
- `src/figures/__pycache__` — 30 files, 186,045 bytes; reproducible and untracked/ignored.
- `src/weather/__pycache__` — 6 files, 57,906 bytes; reproducible and untracked/ignored.
- `src/validation/__pycache__` — 11 files, 104,990 bytes; reproducible and untracked/ignored.
- `reports/presentation/defense_slides.nav` — 1 files, 2,225 bytes; reproducible and untracked/ignored.
- `reports/presentation/defense_slides.snm` — 1 files, 0 bytes; reproducible and untracked/ignored.
- `reports/presentation/build/defense_slides.xdv` — 1 files, 142,972 bytes; reproducible and untracked/ignored.
- `reports/presentation/build/defense_slides.pdf` — 1 files, 1,263,171 bytes; reproducible and untracked/ignored.
- `reports/presentation/build/defense_slides.out` — 1 files, 81 bytes; reproducible and untracked/ignored.
- `reports/presentation/build/defense_slides.toc` — 1 files, 0 bytes; reproducible and untracked/ignored.
- `reports/presentation/build/defense_slides.fdb_latexmk` — 1 files, 30,098 bytes; reproducible and untracked/ignored.
- `reports/presentation/build/defense_slides.nav` — 1 files, 2,225 bytes; reproducible and untracked/ignored.
- `reports/presentation/build/defense_slides.fls` — 1 files, 36,001 bytes; reproducible and untracked/ignored.
- `reports/presentation/build/defense_slides.snm` — 1 files, 0 bytes; reproducible and untracked/ignored.
- `reports/presentation/build/defense_slides.aux` — 1 files, 4,000 bytes; reproducible and untracked/ignored.
- `reports/presentation/build/defense_slides.log` — 1 files, 51,516 bytes; reproducible and untracked/ignored.

### Thirty largest files (active `.git` excluded)

| File | MiB | Git status | Decision |
|---|---:|---|---|
| `data/raw/weather/weather_10min_raw.parquet` | 2322.2 | ignored | Retained |
| `data/processed/weather/weather.parquet` | 1635.7 | ignored | Retained |
| `archive/cleanup_2026-07-28/data/case_crossover_control_times_api.sqlite` | 668.4 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/pack/pack-9e224f57ec31c6ff68a33037d24ab91da49b9979.pack` | 667.4 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/pack/tmp_pack_mJm7n8` | 667.4 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/pack/tmp_pack_HumpJw` | 575.9 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/82/03b00b08434da0246e5cefb4c9f68747cda0c3` | 356.8 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/5a/58e08700fd83f03f4883dc809450c1bcd0f719` | 262.6 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/a5/5b3ccc1322b9d6dd46c604e894a0c187d04bc9` | 220.3 | ignored | Retained |
| `archive/cleanup_2026-07-28/data/wind_direction_accident_days_api.sqlite` | 213.2 | ignored | Retained |
| `archive/legacy_outputs/2026-07-29_renamed_traffic/daily_counter_traffic_2019_2024.csv` | 212.7 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/48/5fe853281d733067de18d10e1b217a49c4f591` | 212.3 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/pack/tmp_pack_HYeh3U` | 187.1 | ignored | Retained |
| `data/processed/traffic/daily_weather.csv` | 161.0 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/lfs/objects/92/a5/92a500d08c7a8518da70f5a224eada6234f2ac73fc1a0c737cd53008686b3737` | 150.4 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/pack/pack-0233106a5580a1c6f4ff4825d27a9f698c322c7f.pack` | 148.0 | ignored | Retained |
| `archive/generated_diagnostics/daily_traffic_channels_2019_2024.csv` | 141.6 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/36/55dd9200c4d4eef4985ababe05f486314d2ab8` | 140.0 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/pack/tmp_pack_HQpIpo` | 120.4 | ignored | Retained |
| `data/processed/traffic/daily.csv` | 98.3 | ignored | Retained |
| `reports/reproduced/committed_8ddd3e7_20260913T225030Z/data/processed/traffic/daily_raw.csv` | 81.5 | ignored | Retained |
| `reports/reproduced/committed_01afd71_20260913T224403Z/data/processed/traffic/daily_raw.csv` | 81.5 | ignored | Retained |
| `data/processed/traffic/daily_raw.csv` | 81.5 | ignored | Retained |
| `archive/git_metadata_before_github_switch_20260810/objects/48/tmp_obj_GliyjC` | 69.4 | ignored | Retained |
| `reports/reproduced/committed_8ddd3e7_20260913T225030Z/data/raw/traffic/reference/roads.geojson` | 64.5 | ignored | Retained |
| `reports/reproduced/committed_01afd71_20260913T224403Z/data/raw/traffic/reference/roads.geojson` | 64.5 | ignored | Retained |
| `data/raw/traffic/reference/roads.geojson` | 64.5 | ignored | Retained |
| `reports/reproduced/pre_submission_bugfix/data/analysis/daily_traffic.csv` | 58.8 | ignored | Retained |
| `reports/reproduced/pre_submission_bugfix/before/analysis/daily_traffic.csv` | 58.8 | ignored | Retained |
| `reports/reproduced/committed_8ddd3e7_20260913T225030Z/reports/reproduced/affected_backup_20260913T225036433679Z/data/analysis/daily_traffic.csv` | 58.8 | ignored | Retained |

### Thirty largest recorded directories

Overlapping directory sizes must not be added. Status applies to contents, not directories themselves.

| Directory | MiB | Classification |
|---|---:|---|
| `.` | 24222.3 | Mixed repository contents |
| `data` | 15709.3 | Source/intermediate evidence |
| `data/raw` | 13396.6 | Source/intermediate evidence |
| `data/raw/weather` | 13207.3 | Source/intermediate evidence |
| `data/raw/weather/supplied` | 10885.0 | Source/intermediate evidence |
| `archive` | 5955.2 | Preserved history/evidence |
| `archive/git_metadata_before_github_switch_20260810` | 4269.1 | Git history |
| `archive/git_metadata_before_github_switch_20260810/objects` | 4117.5 | Git history |
| `archive/git_metadata_before_github_switch_20260810/objects/pack` | 2366.4 | Git history |
| `data/processed` | 2173.2 | Source/intermediate evidence |
| `data/processed/weather` | 1680.5 | Source/intermediate evidence |
| `reports` | 1588.1 | Preserved history/evidence |
| `reports/reproduced` | 1494.8 | Preserved history/evidence |
| `archive/cleanup_2026-07-28` | 900.3 | Preserved history/evidence |
| `archive/cleanup_2026-07-28/data` | 896.0 | Preserved history/evidence |
| `reports/reproduced/committed_8ddd3e7_20260913T225030Z` | 593.6 | Preserved history/evidence |
| `reports/reproduced/committed_01afd71_20260913T224403Z` | 593.6 | Preserved history/evidence |
| `.venv` | 550.5 | Installed environment |
| `.venv/lib` | 550.3 | Installed environment |
| `.venv/lib/python3.13/site-packages` | 550.3 | Installed environment |
| `.venv/lib/python3.13` | 550.3 | Installed environment |
| `data/processed/traffic` | 473.1 | Source/intermediate evidence |
| `.git` | 414.6 | Git history |
| `.git/objects` | 414.3 | Git history |
| `reports/reproduced/committed_8ddd3e7_20260913T225030Z/data` | 366.8 | Preserved history/evidence |
| `reports/reproduced/committed_01afd71_20260913T224403Z/data` | 366.8 | Preserved history/evidence |
| `archive/git_metadata_before_github_switch_20260810/objects/82` | 356.8 | Git history |
| `reports/reproduced/pre_submission_bugfix` | 305.7 | Preserved history/evidence |
| `archive/git_metadata_before_github_switch_20260810/objects/48` | 283.0 | Git history |
| `archive/git_metadata_before_github_switch_20260810/objects/5a` | 262.8 | Git history |

## Section 3.2 and reproducibility

Rewrote the section as a conceptual source-to-results workflow. It identifies the four supplying institutions and distinguishes accident/person/vehicle deliveries and dictionary documentation; describes standardisation, rural classification, weather validity and the 20 km/five-minute linkage; explains station–season expected counts, approximate traffic reweighting and daily VKT allocated using pooled station–month frequencies; separates prepared-input analysis from raw-source preparation; states the restricted-input boundary; and links exact commands, dependencies, generated outputs and validation. The five-stage diagram now matches that explanation and checks real module paths. The command paragraph stays together on one page. The unchanged cleaned-file examples follow it.

Corrected the documented/default road-link input extension to the supplied `.txt`, and documented `--include-2025` for accident preparation. No preparation or numerical analysis was rerun. Removed trailing whitespace from the bundled public-domain `placeins.sty` dependency without changing its TeX commands. README now describes only the three retained analyses and the actual reproduction boundary. Added a pinned test-runner dependency and isolated document build instructions. The workflow test now checks conceptual stage labels and real entry-point existence instead of requiring script paths in the figure.

Scientific source text outside Section 3.2 is byte-for-byte identical to the start of this pass. The whole current thesis was reviewed for abstract–methods–results–conclusion alignment, denominator definitions, causal limitations, captions/order and references. No further scientific rewrite was justified. The only retained `case-crossover` occurrence in current thesis prose/source is a cited article's actual bibliography title. No Q1/Q2/Q3 labels or removed-method claims remain in the active thesis or slides. Figure 4.6, its interval labels, condensed Results paragraphs and detailed contrasts are unchanged.

## Presentation

Retained 19 slides and repaired missing figure names, the supervisor name to match the thesis, terminology, pooled-frequency explanation, sparse-cell/underreporting limitations, conclusion and workflow/future-work backups. XeLaTeX prefers Noto Sans, then DejaVu Sans, then bundled Latin Modern Sans. Fixed the frame rule width and joint-slide layout. Missing figures fail the build. `make -C reports/presentation` uses latexmk/XeLaTeX with all auxiliaries in ignored `build/`, then copies the final PDF alongside its source, following the thesis PDF convention.

## Validation and visual review

- Full suite: **121 passed, 1 skipped, 18 subtests passed** (10.42 s).
- `python -m src.validate`: primary analyses and detailed joint O/E validation passed, including 20 cells, coarse reconciliation and contrasts.
- `python -m src.validation.register_sources`: counts, injury codes, ID inclusion and temporal coverage passed.
- SHA-256 checks: **1,460 existing CSV files unchanged** against the start-of-pass snapshot; joint figure assets unchanged. No numerical outputs recalculated in this pass.
- Fresh thesis build: **48 pages**, with no warnings, undefined references/citations or overfull boxes. All **22 bibliography keys are cited**, and all citations have entries.
- Fresh XeLaTeX presentation build: **19 slides**, no warnings, overfull boxes or missing characters.
- Isolated staged-repository builds also passed for both documents, without local institutional inputs or unstaged files. PDF text matches the reviewed deliverables on every page.
- Reviewed the staged diff and exact 135-file manifest. Whitespace checks passed; no institutional/raw files, credentials, virtual environment, caches or auxiliary files are staged. Seven staged CSV snapshots match the initial SHA-256 hashes.
- Rendered and visually inspected every thesis page and every slide; inspected Section 3.2 and Figure 4.6 individually at readable scale. Figure order and page boundaries are coherent. Thesis length increased from 47 to 48 pages because of Section 3.2.

Detailed local evidence is preserved under `reports/working/repository_polish_20260917/`: initial status/remotes/disk inventory, reference searches, file hashes, exact deletion inventory, validation/build/test logs and commit manifest. Rendered review images are disposable files under `/private/tmp/`.

## Intentional publication manifest

Each line names one changed/deleted path to stage. “Existing revision” means it was already changed at the start of this cleanup; “this pass” means this request changed it. Generated scientific values are frozen against the initial snapshot. Removed retired fragments were already absent at the start, are no longer referenced and remain recoverable from Git.

- `.gitignore` — update; current thesis source, workflow or reproducibility documentation (this pass).
- `README.md` — update; current thesis source, workflow or reproducibility documentation (this pass).
- `docs/deadline_review_20260917.md` — add; current thesis source, workflow or reproducibility documentation (existing revision).
- `docs/joint_weather_revision_20260917.md` — add; current thesis source, workflow or reproducibility documentation (existing revision).
- `docs/pipeline.md` — update; current thesis source, workflow or reproducibility documentation (this pass).
- `docs/repository_polish_20260917.md` — add; current thesis source, workflow or reproducibility documentation (this pass).
- `reports/main/figures/accident_map.pdf` — add; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/accident_map.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/annual_accident_counts.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/annual_accident_counts.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/conditions.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/conditions.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/gust_oe_panels.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/gust_oe_panels.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/joint_wind_temperature_detail.pdf` — add; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/joint_wind_temperature_detail.png` — add; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/monthly_f_traffic_rate_panels.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/monthly_f_traffic_rate_panels.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/monthly_fg_traffic_rate_panels.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/monthly_fg_traffic_rate_panels.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/monthly_temperature_traffic_rate_panels.pdf` — add; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/monthly_temperature_traffic_rate_panels.png` — add; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/monthly_weather_rate_annual.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/monthly_weather_rate_annual.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/temperature_oe_panels.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/temperature_oe_panels.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/traffic_weather_response.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/traffic_weather_response.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/weather_coverage.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/weather_coverage.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/weather_oe_traffic_corrected.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/weather_oe_traffic_corrected.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/weather_oe_traffic_corrected_f.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/weather_oe_traffic_corrected_f.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/weather_oe_traffic_corrected_fg.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/weather_oe_traffic_corrected_fg.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/weather_oe_traffic_corrected_temperature.pdf` — add; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/weather_oe_traffic_corrected_temperature.png` — add; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/wind_oe_panels.pdf` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/figures/wind_oe_panels.png` — update; current thesis/presentation figure asset (existing revision / supporting publication).
- `reports/main/tables/conditions.csv` — update; validated current numerical snapshot; unchanged this pass (existing revision).
- `reports/main/tables/joint_wind_temperature_contrasts.csv` — add; validated current numerical snapshot; unchanged this pass (existing revision).
- `reports/main/tables/joint_wind_temperature_detail.csv` — add; validated current numerical snapshot; unchanged this pass (existing revision).
- `reports/main/tables/monthly_vkt_discrepancy.csv` — update; validated current numerical snapshot; unchanged this pass (existing revision).
- `reports/main/tables/monthly_vkt_rate.csv` — update; validated current numerical snapshot; unchanged this pass (existing revision).
- `reports/main/tables/monthly_vkt_seasonal.csv` — update; validated current numerical snapshot; unchanged this pass (existing revision).
- `reports/main/tables/weather_oe_traffic_corrected.csv` — update; validated current numerical snapshot; unchanged this pass (existing revision).
- `reports/presentation/Makefile` — add; reviewed Beamer deliverable or isolated build support (this pass).
- `reports/presentation/README.md` — add; reviewed Beamer deliverable or isolated build support (this pass).
- `reports/presentation/defense_slides.pdf` — add; reviewed Beamer deliverable or isolated build support (existing revision / supporting publication).
- `reports/presentation/defense_slides.tex` — add; reviewed Beamer deliverable or isolated build support (this pass).
- `reports/thesis/Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf` — update; reviewed final thesis PDF (this pass).
- `reports/thesis/TEMPLATE.md` — update; current thesis source, workflow or reproducibility documentation (this pass).
- `reports/thesis/appendices.tex` — update; current thesis source, workflow or reproducibility documentation (existing revision).
- `reports/thesis/content.tex` — update; current thesis source, workflow or reproducibility documentation (this pass).
- `reports/thesis/draft_en.tex` — update; current thesis source, workflow or reproducibility documentation (existing revision).
- `reports/thesis/generated/accident_sample.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/adu_quality.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/allocation_check.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/cleaned_accident_example.tex` — update; current generated table or Results prose (existing revision).
- `reports/thesis/generated/counter_locations.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/coverage.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/daily_exclusions.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/daily_radius.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/daily_rate.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/daily_sample.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/daily_selection.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/data_trimming.tex` — update; current generated table or Results prose (existing revision).
- `reports/thesis/generated/estimated_rate.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/evidence.tex` — update; current generated table or Results prose (existing revision).
- `reports/thesis/generated/exact_data.tex` — add; current generated table or Results prose (existing revision).
- `reports/thesis/generated/gust_seasonal_results.tex` — add; current generated table or Results prose (existing revision).
- `reports/thesis/generated/joint_detail_discussion.tex` — add; current generated table or Results prose (existing revision).
- `reports/thesis/generated/joint_detail_results.tex` — add; current generated table or Results prose (existing revision).
- `reports/thesis/generated/joint_weather_oe.tex` — add; current generated table or Results prose (existing revision).
- `reports/thesis/generated/match_quality.tex` — update; current generated table or Results prose (existing revision).
- `reports/thesis/generated/matched_time_summary.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/mean_wind_seasonal_results.tex` — add; current generated table or Results prose (existing revision).
- `reports/thesis/generated/monthly_vkt_rate.tex` — update; current generated table or Results prose (existing revision).
- `reports/thesis/generated/monthly_vkt_selection.tex` — update; current generated table or Results prose (existing revision).
- `reports/thesis/generated/road_rates.tex` — add; current generated table or Results prose (existing revision).
- `reports/thesis/generated/rural_seasonal_rates.tex` — add; current generated table or Results prose (existing revision).
- `reports/thesis/generated/severity_conditions.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/temperature_oe_results.tex` — add; current generated table or Results prose (existing revision).
- `reports/thesis/generated/traffic_methods.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/traffic_quality.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/traffic_response_results.tex` — add; current generated table or Results prose (existing revision).
- `reports/thesis/generated/traffic_scope.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/generated/weather_cleaning.tex` — update; current generated table or Results prose (existing revision).
- `reports/thesis/generated/windy_group_examples.tex` — update; current generated table or Results prose (existing revision).
- `reports/thesis/generated/year_oe.tex` — delete; remove unreferenced retired generated fragment (existing revision / supporting publication).
- `reports/thesis/pipeline_analysis.tex` — update; current thesis source, workflow or reproducibility documentation (existing revision).
- `reports/thesis/pipeline_prepare.tex` — update; current thesis source, workflow or reproducibility documentation (this pass).
- `reports/thesis/placeins.sty` — add; required public-domain float-barrier package, whitespace normalised (this pass).
- `requirements-dev.txt` — add; current thesis source, workflow or reproducibility documentation (this pass).
- `src/accidents/build.py` — update; retained analysis, rendering or validation dependency (this pass).
- `src/analysis_data.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/accident_map.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/accident_profiles.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/annual_coverage.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/conditions.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/counter_map.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/joint_detail.py` — add; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/monthly_vkt_rate.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/oe_histo.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/thesis_style.py` — add; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/traffic_corrected_oe.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/traffic_weather_response.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/figures/weather_rate.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/prepare_revision.py` — add; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/cleaned_example.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/conditions.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/exact_data.py` — add; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/headline_summary.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/joint_detail.py` — add; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/monthly_vkt_discrepancy.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/monthly_vkt_rate.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/pipeline.py` — update; retained analysis, rendering or validation dependency (this pass).
- `src/tables/results_context.py` — add; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/revision.py` — add; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/thesis.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/thesis_alignment.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/tables/traffic_corrected_oe.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/thesis_pipeline.py` — add; retained analysis, rendering or validation dependency (existing revision).
- `src/traffic/monthly_vkt.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/validation/cli.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `src/validation/joint_detail.py` — add; retained analysis, rendering or validation dependency (existing revision).
- `src/validation/register_sources.py` — add; retained analysis, rendering or validation dependency (existing revision).
- `src/validation/traffic.py` — update; retained analysis, rendering or validation dependency (existing revision).
- `tests/test_descriptive_temperature.py` — add; calculation or document consistency validation (existing revision).
- `tests/test_final_submission_polish.py` — add; calculation or document consistency validation (this pass).
- `tests/test_joint_detail.py` — add; calculation or document consistency validation (existing revision).
- `tests/test_monthly_vkt.py` — update; calculation or document consistency validation (existing revision).
- `tests/test_monthly_vkt_presentation.py` — update; calculation or document consistency validation (existing revision).
- `tests/test_thesis_revision.py` — add; calculation or document consistency validation (existing revision).
