# Isolated annual-traffic provenance check

> Historical audit, completed before the approved live correction on 13 September 2026.
> Old annual values and pending-action statements below describe that earlier state.
> See [the completed live correction](annual_live_correction.md) for current results and verification.

13 September 2026. Code revision: `ee74db42d873f0d74a386fd036ac7fbd88534e4a`.

**The old annual denominator was retained after the weather source changed.**
Refreshing it from current cleaned weather changes the reported all-injury
20–25 versus 0–5 m/s RR from **2.27 (1.68–3.07)** to **2.34 (1.72–3.17)**.
The associated analysis sample changes from **4,933 to 5,125 accidents**.
The all-injury high-wind conclusion remains supported, but absolute rates and
some serious/fatal inferences change enough that this is not an immaterial
update to the complete annual analysis.

**Live files were preserved.** SHA-256 hashes and modification times of all
296 protected files were checked before and after execution, with no changes.
Protection covered `data/processed`, `data/analysis`, `reports/main`,
`reports/thesis`, and Python source files; the live validation snapshot was
included. Only this report and its compact evidence directory were added to
the repository. No authoritative outputs were promoted from the experiment.

## Isolation and experimental control

The full isolated workspace is
`/private/tmp/annual_provenance_2ke2sn62/`. Its `fresh/` and `old_replay/`
directories contain separate prepared files, exported annual inputs, model
results and logs. Large weather/source files and repository code were read
through links; every producing command ran with an isolated working directory.
No source acquisition or cleaning was rerun. Both branches used the identical
current clean-weather Parquet, accident population, annual traffic,
station register, road references, model code and settings.

The **only experimental change** was whether the annual frequency cache was
reused or rebuilt. Each branch executed:

```text
traffic.build_road_period
  fresh only: --rebuild-period-wind-frequency
→ traffic.rate_weather (including new accident matching to assigned stations)
→ exports_traffic.export_rate_tables
  + export_temperature_rate_input + export_season_rate_input
→ tables.rate (conditional Poisson)
→ tables.estimated_rate (descriptive absolute rates)
```

The old-cache replay reproduced all eight checked live products, within
floating-point tolerance: road-period exposure, individual rate-weather
matches, all four exported annual analysis CSVs, the wind RR table and the
absolute-rate table. This makes the old snapshot a tested control, rather than
an assumed historical baseline. See [replay verification](annual_traffic_provenance/old_replay_vs_live.csv).

The fresh branch additionally fitted the existing serious/fatal, vehicle-count,
official-period, temperature and seasonal annual models to establish the
scope of changes. These remained isolated too.

## A. Exact cause of the discrepancy

The evidence establishes this sequence:

1. **The live cache is the archived older cache.** The 63,340-row CSV at
   `data/processed/weather/road_period_frequency.csv` is table-identical to
   `archive/cleanup_2026-08-26/previous_parquet_working_files/road_period_frequency.parquet`.
   Its measurement totals also match the old station/year cleaning audit for
   **all 4,216 station/year groups represented in the cache**, with zero
   mismatches. Thus this is demonstrably an old-weather denominator, not
   merely a file with an old modification date.
2. **The underlying weather data changed.** The old machine-readable cleaning
   audit records 226,580,952 raw rows and 211,497,897 retained rows. The current
   official-delivery adapter and cleaning audit record 232,459,562 raw rows and
   230,458,950 retained rows. The September source-delivery audit identifies
   the actual `f_`, `fj_`, and `fv_` files and their SHA-256 hashes. Commit
   `1dcc9dc` documents the ingestion change from a supplied raw Parquet to the
   official text deliveries. The local replacement products are dated
   September 9; the annual cache was not refreshed with them.
3. **The wind-QC rule implementation did not change between the compared
   code generations.** Every function in `weather.clean` at August commit
   `dc06530` has the same syntax tree as its current counterpart. The file
   diff changes only default audit output paths. The rules, thresholds,
   frozen-zero processing and execution logic are identical. Different QC
   exclusion counts reflect the different input data, not a changed threshold.
4. **The counting/grouping refactor is not responsible.** I executed the
   historical `build_period_wind_frequency` function on the current full
   clean-weather file. Its `f_5m` output reproduces all **68,046** fresh rows.
   Traffic-period grouping and the six wind intervals are unchanged. Independently,
   summing current `traffic_frequency.csv` seasons into VDU/SDU/VHDU also
   reproduces every fresh count, with zero missing keys or count differences.
5. **The stale cache survives because of the entry-point logic.**
   `src/traffic/build_road_period.py` reads an existing cache unless
   `--rebuild-period-wind-frequency` is supplied. `src.prepare` does not pass
   this flag after rebuilding weather. No source fingerprint invalidates it.

| Possible explanation | Finding |
|---|---|
| Stale cache | **Confirmed.** Exact match to archived cache and old cleaning totals; old replay reproduces live annual outputs |
| Changed weather QC rules | **Ruled out for the compared versions.** Identical cleaning functions/constants; actual exclusion counts changed with the source |
| Changed station coverage | **Confirmed consequence of changed data.** Wind-positive station/year groups increase from 4,303 to 4,597; 426 appear and 132 disappear, with 4,171 shared. Distinct wind stations change from 334 to 329, so the change is not simply “more stations” |
| Changed seasons/traffic periods/bins | **Ruled out.** Historical algorithm and independent current seasonal aggregation both reproduce fresh counts |
| Changed source weather delivery | **Confirmed.** Different raw/clean counts and station/year coverage, supported by old/current audits and recorded official delivery |
| Duplicate cache rows | **Ruled out.** Both caches have unique station/year/period/bin keys |
| Duplicates in current weather | **Ruled out.** Full scans of raw and cleaned station/time columns find strictly increasing timestamps within each station, including across row groups: no repeated or backwards keys |

The old raw/clean weather files themselves were not found among the local
data/archive files inventoried. Therefore individual historical observations
cannot be paired with current observations to attribute every changed bin
count to a particular provider correction, timestamp addition, or upstream
historical transformation. This report does **not** claim that unavailable
row-level history was recovered. The established cause is the unrefreshed
old-source denominator; no further provider-level explanation is inferred.

Selected QC audit totals (the rules are unchanged):

| Count | Old source | Current source |
|---|---:|---:|
| Raw rows | 226,580,952 | 232,459,562 |
| No-wind station/year exclusions | 11,810,743 | 0 |
| Missing paired wind exclusions | 427,778 | 261,519 |
| Negative-wind exclusions | 255,858 | 0 |
| Upper-threshold exclusions | 44,791 | 8,766 |
| Zero gust with positive mean wind | 76 | 255,188 |
| Gust-below-mean exclusions | 2,192 | 2,057 |
| Frozen-zero exclusions | 2,541,617 | 1,473,082 |
| Retained wind rows | 211,497,897 | 230,458,950 |

These are exclusive cleaning categories. They demonstrate changed input
content; they are not a row-by-row reconciliation of the old and new delivery.
[Machine-readable QC totals](annual_traffic_provenance/source_qc_counts.csv).

## B. Old versus fresh coverage and sample sizes

| Stage/count | Old/live | Fresh |
|---|---:|---:|
| Nonzero station/year/period/bin frequency rows | 63,340 | 68,046 |
| Weather observations represented in road-candidate cache | 207,792,101 | 227,083,410 |
| Stations represented in that cache | 325 | 322 |
| Station/year/traffic-period groups | 12,497 | 13,444 |
| Road/year/traffic-period strata, before weather eligibility | 68,946 | 68,946 |
| Road-period/bin exposure rows | 413,676 | 413,676 |
| Road-period strata assigned usable weather | 60,595 | 61,442 |
| Strata with usable weather, positive traffic and positive length | 59,011 | 59,874 |
| Accidents with eligible annual road-period exposure | 5,414 | 5,464 |
| Those within 20 km of assigned station | 5,220 | 5,273 |
| Clean accident-weather matches / exported wind-model sample | **4,933** | **5,125** |
| Exported road_rate.csv rows | 19,832 | 20,405 |
| Exported accident-containing strata | 3,988 | 4,135 |
| Strata actually retained by ConditionalPoisson | 3,984 | 4,133 |
| Rows actually retained by ConditionalPoisson | 19,828 | 20,403 |
| Accidents represented in the conditional likelihood | **4,928** | **5,122** |

The original **18,033 differences are confirmed** among the same **61,800
shared frequency keys**. In addition, 1,540 old keys disappear and 6,246 fresh
keys appear. The original shared-key statistic did not describe those changes
in coverage.

For road-period station assignment, 8,870 strata change: 1,006 gain a station,
159 lose one, and 7,705 switch between available stations. Both branches use
the current station coordinates and road references. The assignment changes
are driven by the cache's changed station/period availability, not a separate
metadata update within this experiment.

**Accident-ID reconciliation:** 4,928 exported IDs are shared; 197 enter and
five leave, giving a net gain of 192. Of the shared events, 520 change assigned
station, 519 change measured mean wind, and 209 change wind interval. Among
the 197 additions, 48 previously lacked eligible road-period exposure, 12 had
an assigned station farther than 20 km, and 137 lacked a clean observation
within five minutes at the old assigned station. All five removals lack a
clean time-matched observation at the fresh assigned station.

The full ID sets, added/removed records, bin transitions and per-ID exclusion
reasons are retained only in the isolated workspace's `comparison/` directory.
Compact [selection counts](annual_traffic_provenance/selection_reason_counts.csv)
and [stage comparisons](annual_traffic_provenance/stage_comparison.json) are
included with this report.

**Sample-label qualification:** the existing `tables.rate.fit_model` records
`model_accidents` from the input frame, but reports `model_strata` and
`model_rows` after the library drops no-variance groups. In the old fit four
single-bin strata contain five accidents; in the fresh fit two such strata
contain three accidents. This explains the difference between exported and
likelihood samples. The fit and its estimates were left unchanged; the report
distinguishes the two counts instead of calling 4,933/5,125 the exact
likelihood sample. [Verified likelihood counts](annual_traffic_provenance/conditional_likelihood_counts.csv).

## C. Old versus fresh estimates and exposure

All conditional RRs use the existing 0–5 m/s reference, log vehicle-km offset,
road/year/traffic-period groups, optimizer and confidence-interval method.

| Mean wind, m/s | Old accidents | Fresh accidents | Old RR (95% CI) | Fresh RR (95% CI) | RR change |
|---|---:|---:|---|---|---:|
| 0–5 | 2,424 | 2,539 | 1.00 (reference) | 1.00 (reference) | — |
| 5–10 | 1,684 | 1,755 | 1.09 (1.02–1.16) | 1.10 (1.03–1.17) | +0.53% |
| 10–15 | 578 | 584 | 1.13 (1.03–1.24) | 1.14 (1.04–1.25) | +0.70% |
| **15–20** | **184** | **186** | **1.63 (1.39–1.90)** | **1.67 (1.44–1.95)** | **+2.99%** |
| **20–25** | **45** | **44** | **2.27 (1.68–3.07)** | **2.34 (1.72–3.17)** | **+2.76%** |
| **≥25** | **18** | **17** | **4.95 (3.07–7.98)** | **5.16 (3.15–8.44)** | **+4.20%** |

Accident counts in this table follow the existing exported-result convention.
The uninformative strata discussed above are all in 0–5 m/s; upper-bin counts
are also actual likelihood counts. Full precision is retained in the
[RR comparison CSV](annual_traffic_provenance/wind_rate_comparison.csv).

Descriptive exposure uses **all eligible road-period strata**, whereas the
conditional model input retains accident-containing strata. These are distinct
denominators; large changes in a sparse all-road tail need not cause equally
large conditional-RR changes.

| Mean wind, m/s | Old all-road vehicle-km, millions | Fresh all-road vehicle-km, millions | Change | Old rate per 100m vehicle-km | Fresh rate per 100m vehicle-km |
|---|---:|---:|---:|---:|---:|
| 0–5 | 28,671.355 | 28,161.598 | −1.78% | 8.45 | 9.02 |
| 5–10 | 12,944.635 | 13,723.377 | +6.02% | 13.01 | 12.79 |
| 10–15 | 3,486.195 | 3,488.377 | +0.06% | 16.58 | 16.74 |
| 15–20 | 665.420 | 620.200 | −6.80% | 27.65 | 29.99 |
| 20–25 | 111.235 | 95.104 | −14.50% | 40.46 | 46.27 |
| ≥25 | 30.735 | 17.194 | −44.06% | 58.57 | 98.87 |

Here “100m” means **100 million**, not metres. Total descriptive exposure is
45.910 → 46.106 billion vehicle-km (+0.43%). The ≥25 m/s descriptive rate rises
68.83%; its crude rate ratio against 0–5 rises from 6.93 to 10.97. Thus the
descriptive absolute-rate table must change, even though the adjusted headline
is fairly stable. [Full absolute-rate comparison](annual_traffic_provenance/absolute_rate_comparison.csv).

| Mean wind, m/s | Old model-input vehicle-km, millions | Fresh model-input vehicle-km, millions | Change |
|---|---:|---:|---:|
| 0–5 | 5,259.354 | 5,440.010 | +3.43% |
| 5–10 | 3,401.727 | 3,487.557 | +2.52% |
| 10–15 | 1,113.763 | 1,110.604 | −0.28% |
| 15–20 | 215.714 | 213.017 | −1.25% |
| 20–25 | 32.007 | 31.595 | −1.29% |
| ≥25 | 4.803 | 4.510 | −6.10% |

[Model-input exposure comparison](annual_traffic_provenance/model_vkt_comparison.csv).
These changes combine refreshed frequencies, changed available strata and
station reassignment; they are not a fixed-sample denominator-only adjustment.

## D. Does the scientific conclusion change?

**Main all-injury conclusion: no reversal.** All three upper-wind conditional
estimates remain above one with 95% intervals excluding one, and increase by
about 3–4%. Seasonal all-injury ≥15 m/s estimates remain above one in all four
seasons. These results continue to support an association between high wind
and elevated injury-accident rates under the same traffic-allocation assumptions.
This does not turn the observational comparison into a causal estimate.

**The complete annual result set does change substantively.** In addition to
the absolute-rate changes, the serious/fatal 20–25 m/s interval crosses one:

| Serious/fatal wind interval | Old accidents | Fresh accidents | Old RR (95% CI) | Fresh RR (95% CI) |
|---|---:|---:|---|---|
| 15–20 | 45 | 45 | 1.92 (1.40–2.64) | 2.04 (1.49–2.79) |
| 20–25 | 9 | 7 | 2.23 (1.14–4.37) | **1.88 (0.88–4.02)** |
| ≥25 | 4 | 4 | 4.91 (1.76–13.64) | 5.51 (1.97–15.40) |

The serious/fatal exported sample becomes 1,088 instead of 1,055. In seasonal
serious/fatal fits, the autumn ≥15 interval changes from 1.90 (1.02–3.54) to
1.88 (0.98–3.60), and the spring 10–15 interval's lower bound moves just above
one (0.925 → 1.005). These small sparse-cell boundary crossings warrant
careful wording, not a claim that the underlying effect suddenly appeared or
disappeared. [Serious/fatal comparison](annual_traffic_provenance/wind_rate_severity_comparison.csv),
[seasonal comparison](annual_traffic_provenance/season_rate_severity_comparison.csv).

Other checked effects: the official VDU/SDU-only 20–25 estimate becomes
2.03 (1.38–2.96), versus 1.82 (1.23–2.70); its sample grows 3,424 → 3,548.
The one-vehicle and multiple-vehicle coarse upper RRs remain elevated.
The temperature-model input changes 4,921 → 5,118 accidents because its road
station assignment also depends on the annual wind-availability panel.
All corresponding comparison CSVs are retained beside this report.

No arbitrary numerical “materiality threshold” was applied. The headline is
robust in direction and similar in magnitude; the sample, descriptive tail
and sparse subgroup results require a coherent reporting update.

## E. Should live outputs be regenerated?

**Yes, after review and approval, regenerate the annual dependency chain as
one consistent set.** The fresh branch agrees with current cleaned weather,
the historical counting algorithm and the independent current seasonal
frequency layer. Keeping the old cache would knowingly mix weather generations.

Preserve the old snapshot as the comparison baseline. Do not copy just the new
headline RR into the thesis: the numerator IDs, station assignments, absolute
rates, sensitivity fits and sample labels also change. The current validation
code explicitly expects 4,933 annual accidents in its cross-method check;
that expectation needs a reviewed update, rather than being bypassed.

The separate `products` dependency on legacy `oe_scenarios.csv` identified in
the pipeline audit remains. This annual check did not refactor or repair it.

## F. Exact regeneration scope if approved

Paths below are repository-relative. This is a dependency inventory, not an
instruction to overwrite files during this verification task.

| Layer | Files requiring regeneration / review | Producer |
|---|---|---|
| Denominator | `data/processed/weather/road_period_frequency.csv` | `src.traffic.build_road_period --rebuild-period-wind-frequency` |
| Road exposure | `data/processed/traffic/road_period.csv` | Same command |
| Matched numerator | `data/processed/accidents/rate.csv`; `reports/working/tables/rate_accident_weather_audit.csv` | `src.traffic.rate_weather` |
| Annual analysis contracts | `data/analysis/road_rate.csv`, `road_exposure.csv`, `road_temperature.csv`, `road_seasons.csv` | `src.exports_traffic` annual exporters |
| Counts/inventory | `data/analysis/selection_summary.csv`, `manifest.csv` | Selection export and manifest writer; preserve unrelated entries |
| Main wind models | `reports/main/tables/wind_rate.csv`, `wind_rate_severity.csv`, `wind_rate_one.csv`, `wind_rate_multiple.csv` | `src.tables.rate` with existing outcome/coarse variants |
| Annual temperature/season models | `reports/main/tables/temperature_rate.csv`, `season_rate.csv`, `season_rate_severity.csv` | `src.tables.temp_rate`, `src.tables.season_rate` variants |
| Official-period sensitivity | `reports/working/tables/wind_rate_official.csv` | `src.tables.rate --traffic-period official` |
| Descriptive rates | `reports/main/tables/absolute_rate.csv`; `reports/working/tables/estimated_crash_rate_by_wind_audit.csv` | `src.tables.estimated_rate` |
| Downstream comparison/checks | `reports/main/tables/traffic_checks.csv`, `allocation_check.csv`, `wind_oe_comparison.csv`; `reports/working/tables/season_method_comparison.csv` | Corresponding `src.tables` modules; annual components change, daily/primary inputs remain fixed |
| Figures | `reports/main/figures/wind_rate.png`, `wind_rate_severity.png`, `wind_rate_vehicle.png`, `temperature_rate.png`, `season_rate.png`, `season_rate_severity.png`, `wind_oe_comparison.png`, `traffic_flow.png`, `traffic_flow.pdf`; `reports/working/figures/wind_rate_official.png` | Corresponding figure modules, including `figures.data_flow` for changed annual coverage |
| Validation | Reviewed annual sample expectation in `src/validation/traffic.py`; then `reports/main/tables/validation.md` | Update baseline only from verified results, retain conservation checks, run validation/tests |
| Generated thesis views | `reports/thesis/generated/coverage.tex`, `traffic_methods.tex`, `estimated_rate.tex`, `traffic_scope.tex`, `traffic_quality.tex`, `allocation_check.tex`, `evidence.tex` | `src.tables.thesis`; some retained generated views are not currently included |
| Prose/PDF | Affected numerical passages in `reports/thesis/content.tex`; `reports/thesis/Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf` | Targeted numeric/interpretive update, then compile; rebuildable TeX auxiliaries follow |

The source deliveries, current clean weather, primary O/E inputs/results,
matched-time inputs/results and daily-counter inputs/results have no dependency
on this annual cache and do not need regeneration for this correction.
`annual_quality.csv` also describes unchanged annual traffic source values.
Mixed comparison tables do need regeneration because they contain annual
results. No broad data re-preparation or thesis rewrite is required.

## G. Thesis numbers and wording that would change

The current `content.tex` and generated tables would need these targeted edits:

- Usable annual road-period weather coverage: **60,595 → 61,442** out of the
  same 68,946 strata (current content.tex around line 335).
- Annual analysis sample: **4,933 → 5,125**; clarify the fit uses **4,133
  informative strata representing 5,122 accidents**. The previous wording
  combines a pre-fit accident count with a post-drop stratum count.
- Main annual estimates: **1.63 (1.39–1.90) → 1.67 (1.44–1.95)**,
  **2.27 (1.68–3.07) → 2.34 (1.72–3.17)**, and
  **4.95 (3.07–7.98) → 5.16 (3.15–8.44)**. Uppermost accidents:
  **18 → 17**; 20–25 accidents: **45 → 44** (around lines 787–795).
- Serious/fatal sample: **1,055 → 1,088**, with the three updated estimates
  in section D. At 20–25 m/s the CI now includes one; wording must reflect
  the uncertainty of seven events (around lines 799–804).
- Descriptive Table 4.3 (`estimated_rate.tex`): update all six counts and
  rates; at ≥25 m/s **58.6 → 98.9** per 100 million estimated vehicle-km.
- Generated coverage, traffic-input, evidence and sensitivity tables need the
  corresponding new samples/estimates. The official-period comparisons change
  too. Review generated seasonal sensitivity values even where current prose
  states only that all four all-injury estimates exceed one; that statement
  still holds.

The main conclusion can remain that high wind is associated with elevated
all-injury accident rates under time-proportional annual traffic allocation.
It would be inaccurate to say “nothing changes”: the absolute tail and some
serious/fatal uncertainty statements change. Primary O/E, matched-time OR
1.61, allocated daily RR 3.62 and the 613-accident same-day result are outside
this dependency chain and are not revised by this experiment.

## Verification and retained evidence

- Full current clean-weather scan: **230,458,950 rows**, 720 row groups;
  **227,083,410** observations contribute to candidate-road station counts.
- Historical counting algorithm on the same complete source: exact matching
  keys/counts; numerical frequency agreement within floating-point tolerance.
- Fresh cache versus current seasonal aggregation: **68,046 shared rows;
  zero differing counts and zero unmatched keys**.
- Old-cache control reproduces the eight live stages checked above.
- Export conservation and join/uniqueness assertions passed; individual
  rematched IDs reconstruct the exported counts in both branches.
- Actual conditional-likelihood counts verified against the library's grouped
  response arrays, not inferred from the result CSV's sample label.
- No source/key duplicates found in complete current raw/clean timestamp scans.
- No live validation snapshot was regenerated or relaxed. Fresh headline and
  sensitivity model fits completed; the only routine model warnings were the
  documented no-variance group drops.
- Final protection check: **296 files unchanged in content and modification
  time**. [Protection check](annual_traffic_provenance/protected_files_check.json).

Current clean-weather SHA-256:
`dab4b873702ade2cda78f759d3656cef5a0f57ef392a0ff8648a78e6318a6b18`.
Old cache SHA-256:
`34563bbd24c1faee5caf8959c4a52d8555ecdf6a9a53fd0f923bfff2c0286819`.

[Verification metadata](annual_traffic_provenance/verification.json) records
the code revision, hashes, historical algorithm check and full key-scan counts.
Compact aggregate evidence is under `docs/annual_traffic_provenance/`.
The temporary workspace preserves the complete frequency/assignment/ID
comparisons, snapshots, source-history diffs, commands and scripts:
`run_chain.py`, `compare.py`, `check_weather_keys.py`, `trace_changes.py`, and
`check_variants.py`. It also contains every fresh analysis input and fitted
annual result. These are review artifacts, not authoritative replacements.
