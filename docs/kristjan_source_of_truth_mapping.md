> Current status: the final method-alignment instructions confirm monthly allocation
> as MAIN and same-day as SENSITIVITY, while preserving validated scientific results.
> This historical audit is superseded by [the final method audit](kristjan_method_alignment_audit.md),
> [figure specification](kristjan_main_figure_spec.md) and
> [method comparison](monthly_vs_sameday_figure_comparison.md).

# Kristján source-of-truth mapping

## Evidence recovered before changing figures

This mapping was written before any figure edits in this pass. The starting
uncommitted changes were inspected and preserved. Source authority is the
actual git objects, not the previous Codex alignment notes.

- `bfd799fed3db4fd97de9876ade32302cf8929db2`, author Kristján Jónasson,
  14 September: same-day allocation calculation and four rate figure assets.
- `c90f735efa2b433523d5e53688753ce72ffdd2a8`, author Kristján Jónasson,
  14 September: two period-specific O/E figures, corrected counter-era O/E,
  traffic response; retains the preceding same-day rate generator.
- `43a8a91`, author asge1r: subsequent monthly-frequency calculation and
  `src/figures/monthly_vkt_rate.py`. The current uncommitted five-panel monthly
  and same-day designs are later Codex presentations, not Kristján originals.
- Inspected current scripts, scientific tables, `docs/pipeline.md`,
  `docs/kristjan_20260914_analysis_alignment.md`, `docs/kristjan_figure_alignment.md`
  and `docs/kristjan_next_meeting_brief.md`. The latter three are interpretive
  records and cannot establish original visual choices.

## Common definitions

Seasons: Winter December–March; Spring April–May; Summer June–September;
Autumn October–November. All year pools the study period. Blue is minor
injury (code 3); red is serious or fatal injury (codes 1–2). Groups are disjoint.
Wind bins: 0–5, 5–10, 10–15, 15–20, ≥20 m/s. Gust: 0–5 through 25–30,
then ≥30 m/s. Temperature: <−6, −6–−3, −3–0, 0–3, 3–6, 6–9, 9–12, ≥12°C.
Rate seasonal wind tails combine to ≥15; gust tails to ≥20. All year retains
fine bins; temperature retains its bins. Combine counts and exposure, not rates.

## Original family, science and placement

Paths in the figure column are under `reports/main/figures/`; original versions
refer to commit `c90f735`, unless stated otherwise.

| Source figure(s) | Script / data | Definition, numerator and denominator | Parameters / periods / grouping | Main-thesis placement |
|---|---|---|---|---|
| `wind_oe_panels.png`, `gust_oe_panels.png`, `temperature_oe_panels.png` | `src/figures/oe_histo.py`; `src/analysis/oe_analysis.py`; `reports/main/tables/weather_oe.csv` | O_gb / E_gb; actual accident-time counts; E sums injury-specific station-season accident totals × local bin frequency | Three parameters, All year + four seasons; grouped disjoint blue/red; fine bins; O/E=1 line | Weather-frequency baseline |
| `weather_oe_2007_2018.png`, `weather_oe_2019_2024.png` | Same scripts; corresponding result CSVs | Same O/E, restricting both accidents and background years to displayed period | Three parameters vertically; All year; grouped disjoint injury bars; fine bins; O/E=1 | Baseline period comparison within correction discussion |
| `traffic_weather_response.png` | `src/figures/traffic_weather_response.py`; `src/traffic/daily_vkt.py`; `data/analysis/traffic_weather_response.csv` | 100 × allocated observed vehicles / allocated calendar-expected vehicles; daily totals allocated by observed weather minutes; expected traffic within section/year/month/weekday | Three parameters, All year 2019–2024; no injury grouping; fine bins; 100% reference | Traffic behaviour before correction |
| `weather_oe_traffic_corrected_2019_2024.png` | `src/figures/traffic_corrected_oe.py`; `src/tables/traffic_corrected_oe.py`; corresponding CSV | O/E after local frequencies × traffic multiplier and within-stratum renormalisation; same observed counts | Three parameters, All year 2019–2024; grouped disjoint injury bars; fine bins; O/E=1 | Approximate correction, counter-era comparison |
| `weather_rate_annual.png` | `src/figures/weather_rate.py`; `src/traffic/daily_vkt.py`; `data/analysis/daily_vkt.csv` | 10^6 O_b / sum(C_jd L_j observed bin minutes /1020); event-time daytime numerator; missing weather minutes excluded | Three vertical parameter panels; All year 2019–2024; blue minor bottom/red serious-fatal top, common exposure; fine bins; no ratio reference line | Explicit same-day allocation comparison |
| `f_traffic_rate_panels.png`, `fg_traffic_rate_panels.png`, `temperature_traffic_rate_panels.png` | Same scripts and data | Same same-day formula; season-specific counts and exposure | One parameter per figure; 2×2 four-season panels; stacked disjoint groups; combined wind/gust seasonal tails; no ratio reference | Explicit same-day allocation comparison |
| Monthly main rate: no Kristján-authored source image recovered | `src/traffic/monthly_vkt.py`; `src/weather/monthly_frequency.py`; `data/analysis/monthly_vkt.csv`, `monthly_vkt_section.csv`; presentation severity counts checked against eligible event records | 10^6 O_b / sum(C_jd L_j p_station,month,b); actual daytime accident weather; all eligible counter-days, including accident-free days; pooled 2007–2025 station/month 07–24 frequencies allocate full daily counts | Wind and gust only; 2019–2024; shared exposure across disjoint groups; original rate layout/style ported without substituting same-day exposure | Main counter-based rate, as explicitly specified in latest user instructions |

## Recovered axes and colour

`weather_rate.py` in Kristján's commit explicitly sets:

| Figure | All year y range | Seasonal y range | Shared axes |
|---|---|---|---|
| Same-day mean wind | 0–1.3 | 0–0.8 | Four seasonal panels share; All year separate |
| Same-day gust | 0–1.3 | 0–0.5 | Four seasonal panels share; All year separate |
| Same-day temperature | 0–0.3 | 0–0.6 with current data | Four seasonal panels share; All year separate |
| Monthly wind, source-style port | 0–1.3 | 0–0.8 | Same source convention |
| Monthly gust, source-style port | 0–1.3 | 0–0.5 | Same source convention |

Temperature seasonal source rule is ceil(1.2 × tallest seasonal stack /0.1) ×0.1;
it is **not** a recovered manual 0.6 setting. Annual temperature tick step .05;
other rate steps .1. Source dimensions: annual 10.2×12 inches (three rows);
seasonal 14.5×9.5 inches (2×2). Monthly annual has two parameter rows, preserving
source panel dimensions. This port is explicitly distinguished from original art.

The source rate blue is **#79BCE0**, red **#D62728**, with black bold counts
inside blue and above red. The original grouped O/E used darker #0072B2 and
#B22222; the user's latest explicit light-blue/stable-colour request authorises
using the recovered rate colours throughout injury figures.

Other source axis choices:
- Baseline O/E: source automatic max(1.5, 1.18×maximum group O/E), shared only
  across each parameter's five panels. Current limits: wind 8.6738466329,
  gust 14.3574954971, temperature 2.5752950343. No manual fixed limit recovered.
- Original period O/E: shared across its three parameters; 2007–2018 upper
  limit 4.0524999516; 2019–2024 4.9436401482, from the same source rule.
- Corrected counter-era O/E: manual wind 0–6, gust 0–6, temperature 0–2;
  ticks 1, 1, .2. No harmonisation across parameters is warranted.
- Full-period corrected comparison images are subsequent additions; their
  limits must not be attributed to Kristján.

## The old 4.9–4.10 versus 4.14–4.16 question

The old 4.9–4.10 monthly science implements the formula explicitly specified
in the new request. The old 4.14–4.16 derive from Kristján's actual same-day
work but the five-panel layout is a later Codex redesign. His original layout
was four assets: annual three-parameter figure plus three seasonal figures.
Original annual image shows upper rates about .926 and 1.178, matching current
same-day data; these cannot be relabelled as monthly .667 and .866.

The provided new instruction explicitly selects monthly allocation as the main
rate method. Therefore use that science with the recovered rate presentation,
and retain the actual same-day family clearly labelled. Repository authorship
alone cannot prove which method he now wants as primary; flag this at review.

## Research-question recommendation recorded before edits

One primary question: “How does rural injury-accident occurrence vary with
weather, particularly strong wind, after accounting as far as possible for
local weather frequency and traffic exposure?” Three analysis stages:
weather-frequency baseline; approximate traffic correction; counter-based
accident rates. Q1/Q2/Q3 may remain compact stage identifiers, not three
competing research questions. Traffic behaviour precedes corrected O/E in Results.

## Scientific verification before restoration

Current same-day tallest annual stacks: wind .925786, gust 1.178339,
temperature .250538. Tallest combined seasonal stacks: wind .738997,
gust .387496, temperature .498729. Monthly tallest annual stacks .666516,
.866423; combined seasonal .680933, .362180. All fit recovered source limits.
The rate-scale arithmetic check found no discrepancy in these rate families.
The later side-by-side review found a baseline O/E discrepancy, documented below.
No data or estimand is altered to fit an axis. Historical analysis CSVs are ignored by git, so matching source images
and reproducible current inputs, rather than a nonexistent historical CSV blob,
provide the comparison evidence.

## STOP: historical O/E discrepancy found during side-by-side review

Section 21 of the user's source-of-truth instructions requires stopping when
an original figure conflicts with current validated data. Finalisation is paused.
The mapping above records planned placement and edits made before discovery;
it is not confirmation that the full pass is complete.

| Figure / all-injury interval | Kristján saved source c90f735 | Current validated table |
|---|---|---|
| Baseline mean wind ≥20 | 77 observed; 35.3675 expected; O/E 2.18 | 68; 31.5963; O/E 2.15 |
| Baseline gust ≥30 | 68 observed; 19.6259 expected; O/E 3.46 | 61; 18.2471; O/E 3.34 |
| Baseline total matched sample | 6,192 | 6,259 |
| 2007–2018 mean wind ≥20 | 51; O/E 2.13 | 46; O/E 2.15 |
| 2019–2024 mean wind ≥20 | 24; O/E 2.36 | 20; O/E 2.12 |

Temperature and corrected counter-era O/E also show source/current count
changes. These are historical differences, not results changed in this pass.
The exact output transition is commit `3da8958` ("Reconcile traffic analysis
outputs after upstream integration"). It updates O/E CSVs and figures without
changing `oe_analysis.py`; the accompanying manifest changes weather-yearly rows
from 284,683 to 343,131 and weather-cleaning provenance. This supports an input
snapshot/reconciliation difference as the likely cause. It does not establish
which upstream record differences explain every changed accident bin.

The actual source automatic O/E upper limits, calculated from its saved CSVs,
are wind 8.2983990527, gust 14.5089801244, temperature 3.0196573964.
Source period figures shared limits are 4.1280423213 (2007–2018) and
5.4573923663 (2019–2024). The earlier current-data numbers in this mapping
are evaluations of the original rule on current data, **not restored original
limits**. Do not silently substitute these datasets to make the plots match.

All eleven recovered source assets were inspected side by side. Same-day
annual and seasonal figures match current counts and bar heights; traffic
response percentages and 0–120% scale match. The O/E families differ.
Comparison sheets are in `/private/tmp/source_review/`.
