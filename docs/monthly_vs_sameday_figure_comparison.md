# Monthly versus same-day traffic-rate figures

## Decision

The latest user instruction explicitly selects Kristján's **monthly-frequency
method as the main traffic-rate analysis**. Same-day allocation is sensitivity.
This supersedes the pending method-choice question in earlier audit documents.
Visual similarity does not determine the scientific denominator.

| Property | Main monthly figures 4.12–4.14 | Same-day sensitivity figures 4.15–4.18 |
|---|---|---|
| Denominator in bin b | Sum over section/date of daily count × rural length × pooled station/calendar-month bin frequency | Sum over section/date of daily count × rural length × observed same-day bin minutes / 1,020 |
| Numerator | Actual accident-time weather classifies the eligible injury accidents | Actual accident-time weather classifies the eligible injury accidents |
| Period / population | 2019–2024; 694 linked accidents; 533,649 eligible section-days | 2019–2024; 694 linked accidents; eligible weather-covered traffic days |
| Weather allocation | Typical 07:00–24:00 monthly distribution pooled across 2007–2025, at assigned station | Actual 07:00–24:00 observations, nearest qualifying station per timestamp; missing minutes excluded |
| Accident-free days | Contribute exposure | Contribute exposure when eligible |
| Parameters | Mean wind, gust; no validated monthly temperature result | Mean wind, gust, temperature |
| All year bins | Wind 0–5 through 15–20 then ≥20; gust 0–5 through 25–30 then ≥30 | Same wind/gust bins; temperature <−6, −6–−3, −3–0, 0–3, 3–6, 6–9, 9–12, ≥12°C |
| Seasonal display | Wind tail ≥15; gust tail ≥20; sum counts/exposure before division | Same wind/gust combination; temperature unchanged |
| Seasons | Winter Dec–Mar; Spring Apr–May; Summer Jun–Sep; Autumn Oct–Nov | Same |
| Severity | Disjoint minor code 3 below serious/fatal codes 1–2; common bin exposure | Same |
| All year axes | Wind 0–1.3, gust 0–1.3 | Wind/gust 0–1.3; temperature 0–0.3 |
| Seasonal axes | Wind 0–0.8; gust 0–0.5 | Wind 0–0.8; gust 0–0.5; temperature 0–0.6 |
| Analysis scripts | `src/traffic/monthly_vkt.py`, `src/weather/monthly_frequency.py` | `src/traffic/daily_vkt.py` |
| Figure scripts | `src/figures/monthly_vkt_rate.py`, reusing the source-style renderer in `weather_rate.py` | `src/figures/weather_rate.py` |
| Scientific inputs | `data/analysis/monthly_vkt.csv`, `monthly_vkt_section.csv`; existing eligible event records for severity | `data/analysis/daily_vkt.csv` |
| Kristján's main method? | Yes, exactly the monthly formula specified by the user | No; alternative allocation sensitivity |
| Kristján's visual design? | Source-style port: annual vertical panels, 2×2 seasonal panels, light blue/red stacks, original rate scales | Recovered original figure family from Kristján-authored commits bfd799f/c90f735 |

Rates plotted per million vehicle-km multiply O/exposure by 10^6. Within either
method, both severity components use the same denominator. Exposure is never
summed across severity components to define the all-injury denominator.

## Historical numbering

Earlier monthly Figures 4.9–4.10 were Codex five-panel layouts of monthly science;
earlier same-day 4.14–4.16 were five-panel layouts derived from the other method.
The final monthly family is 4.12–4.14; same-day is 4.15–4.18. The former
five-panel assets remain on disk but are not included in the thesis.

## Why distinguish the methods?

Monthly allocation retains actual day-to-day traffic variation while using a
stable station-month weather distribution. Same-day allocation responds directly
to individual storm days and is more sensitive to weather completeness and
within-day traffic assumptions. Neither method measures hourly exposure or
establishes causality. Methods and captions explicitly state these distinctions.

## Proof and unchanged science

Across 60 fine-bin parameter × period × bin cells, summed severity counts match
all injury exactly; maximum rate discrepancy is 1.1102230246251565e-16.
Tests also verify every displayed combined seasonal cell and common exposure.
All 75 scientific CSVs are unchanged from this pass's starting snapshot.

Mean wind ≥20 retains 11 accidents, .667 per million vehicle-km and 5.83× baseline;
gust ≥30 retains 11, .866 and 7.78×. These are monthly results and are never
assigned to the same-day denominator. Temperature appears only in sensitivity.
