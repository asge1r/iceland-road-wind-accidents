# Alignment with Kristján's analysis instructions, 14 September 2026

## Decision and implementation plan

Kristján's latest description maps to three thesis-facing analyses. The broad
2007–2025 weather-frequency O/E remains the primary descriptive analysis. A
second figure applies the observed 2019–2024 daily-counter traffic response to
that O/E denominator as an explicitly approximate extrapolation. A third,
separate rate uses observed daily traffic, rural road length, and pooled
calendar-month weather frequencies for all eligible counter-days in 2019–2024.

The matched-time, annual conditional Poisson, allocated 762-case, former
613-case, severity, daylight, and interaction analyses answer useful secondary
questions. They should be presented as supporting or appendix material rather
than as alternative definitions of the new rate.

The repository state immediately before this pass is preserved by the tag
`pre-kristjan-alignment-20260914` at commit
`3da8958573869dc01b4c1783938d428d8bdf1247`.

## Reproduced 2019–2024 selection

The selection was rebuilt from the canonical accident, counter-section,
counter-day, station, and weather files. The result exactly reproduces the
specified sequence. The full SHA-256 hashes of the sorted retained accident-ID
sets are in `reports/main/tables/monthly_vkt_selection.csv`.

| Step | Removed | Remaining | Rule |
|---|---:|---:|---|
| All injury accidents, 2007–2025 | — | 17,045 | `meidsli` 1, 2, or 3 |
| Restrict to 2019–2024 | 11,849 | 5,196 | Accident calendar year |
| Exclude urban/unclassified | 3,333 | 1,863 | Rural only |
| Require a counter section for road/year | 994 | 869 | Exact normalized registered road and year |
| Require successful road location | 21 | 848 | Five lacked road geometry, 15 were more than 100 m from the road, and one projected outside the counter sections |
| Exclude 00:00–07:00 | 67 | 781 | Event time 07:00–24:00 |
| Require usable wind and gust | 4 | 777 | Station distance from counter-section location at most 20 km; match at most five minutes; valid mean wind and gust |
| Require daily traffic record | 83 | **694** | Exact section/date; all 83 lacked a corresponding counter-day record and none had a recorded zero count |

The final ID-set hash is
`3b39b09f6bdad9b7701a449aa922fc2ff461ad2dd2d0af7fc4cf23be71531874`.
This population is distinct from the broad 767-case daily sample, the
762-case allocated model, and the former 613-case coverage-threshold analysis.

## Exact methods and roles

| Method | Scientific question | Sample | Denominator and weather measure | Traffic source | Accident weather | Main assumption | Role |
|---|---|---:|---|---|---|---|---|
| Primary weather O/E | Are accidents over-represented when a weather state occurs? | 6,259 | Station × season weather-time frequency, 2007–2025 | None | Matched 10-minute observation | Valid local records represent time in each state | Main |
| Rough traffic-corrected O/E | How would primary O/E change if the observed daily traffic response generalised? | 6,259 | Primary frequency multiplied by a 2019–2024 bin-specific daily-traffic multiplier and renormalised | Daily counters | Matched 10-minute observation | Counter traffic response extrapolates to the broad sample | Main sensitivity, labelled approximate |
| Monthly-frequency daily-counter rate | What is the accident rate per estimated VKT when observed daily traffic is allocated by typical monthly weather? | **694** | \(\sum_{jd} C_{jd}L_jp_{j,m(d),b}\), with pooled 2007–2025 07:00–24:00 station/month frequencies | Every positive counter-day, 2019–2024 | Matched event-time observation | Typical station/month weather fractions allocate the full daily count | Main traffic analysis |
| Annual conditional Poisson | How do wind-bin RRs compare within road/year/traffic-period strata? | 5,125 | Annual estimated VKT panel; wind frequency within stratum | VDU, SDU, derived VHDU | Accident-time observation | Period traffic and length describe relative opportunity; their common factor cancels within stratum | Supporting |
| Allocated daily model | What is the traffic-standardised pattern using the earlier allocation panel? | 762 | Allocated daily exposure under its documented coarse bins | Daily counters | Daily-analysis definition | Its allocation approximates within-period exposure | Supporting/appendix |
| Former strict same-day O/E | What did the older coverage-threshold same-day design show? | 613 | Same-day allocated VKT with coverage restriction | Daily counters | Event-time observation | Full daily count allocated to observed same-day weather | Repository/historical; superseded |
| Current same-day rural VKT rate | What rate follows from timestamp-specific same-day weather coverage? | 694 | Daily VKT distributed over observed 07:00–24:00 timestamps; unmatched time excluded | Daily counters | Event-time observation | Traffic is uniform during the window | Supporting |
| Matched-time case-crossover | Does the weather contrast persist against matched calendar times? | 6,257 strata | No VKT denominator; conditional comparison with matched control times | None | Case and control observations | Time matching controls recurring calendar patterns | Supporting robustness |

## New monthly-frequency VKT rate

For bin \(b\),

\[
R_b=\frac{O_b}{\sum_j\sum_d C_{jd}L_jp_{j,m(d),b}}10^6.
\]

All 533,649 recorded nonnegative rural counter-section days contribute,
including 4,219 recorded zero-count days and days without an accident. Sections
with no rural length and 169 days lacking a valid station-month frequency are
ineligible. Zero-count days
add no VKT. Total rural exposure is 5,630,267,210 VKT. The wind and gust
allocations each reconstruct this total to numerical precision. Section length
comes from the counter-section definition for that year. Monthly frequencies
use the nominal station assigned to the section; numerator bins use the nearest
valid event-time station within 20 km and five minutes. The bin boundaries are
identical to primary O/E.

| Measure | Lowest bin: O / VKT / rate per million | Upper bin: O / VKT / rate per million | Upper/lowest rate ratio |
|---|---|---|---:|
| Mean wind | 0–5: 344 / 3,011,454,848 / 0.114 | ≥20: 11 / 16,503,739 / 0.667 | **5.83** |
| Gust | 0–5: 205 / 1,840,903,464 / 0.111 | ≥30: 11 / 12,695,874 / 0.866 | **7.78** |

These are descriptive rates. The 11 events in each upper bin make the ratios
sensitive to a small number of accidents.

## Rough traffic correction

The correction does not use a full-day mean, a 10:00–21:59 mean, or a duration
threshold. For each counter-section/year/month/weekday, the code calculates
mean daily traffic. It then assigns each day's traffic total and its expected
total uniformly to the valid same-day 07:00–24:00 ten-minute weather-bin
minutes. The bin multiplier is pooled observed allocated vehicles divided by
pooled expected allocated vehicles. Thus the weather bins are the same numeric
bins as primary O/E, but the measures are not fully compatible: the accident
uses one event-time observation, while the traffic response repeats a daily
total across the day's observed weather composition and has no hourly traffic.

Applying those multipliers to the full primary sample gives:

| Measure | Bin | Observed | Weather-time expected / O/E | Corrected expected / O/E |
|---|---|---:|---:|---:|
| Mean wind | ≥20 m/s | 68 | 31.60 / 2.15 | 25.05 / **2.71** |
| Gust | ≥30 m/s | 61 | 18.25 / 3.34 | 14.54 / **4.20** |

This is consistent with the interpretation that lower traffic during stormier
counter-days can make weather-time O/E understate a per-vehicle contrast if the
counter pattern generalises. It remains an extrapolated, model-based sensitivity
analysis rather than a directly observed traffic-adjusted O/E.

## Why the magnitudes differ

The earlier shorthand comparison of about 3× versus 9× and 6× versus 12× mixed
different samples and denominator designs. Under the newly specified monthly
method, the corresponding raw rate ratios are 5.83 and 7.78, while the rough
full-sample corrected O/E values are 2.71 and 4.20.

Within counter-section × year × season strata, allocating each stratum's total
accidents in proportion to monthly-frequency VKT gives upper-bin O/E 3.39 for
mean wind and 4.84 for gust. This attenuation relative to the raw rate ratios
shows that road/year/season baseline composition contributes to the gap. It
does not explain all of it.

Exposure itself is not dominated by one counter section. In the upper wind bin,
the largest section supplies 2.6% of exposure and the largest five 10.5%; for
upper gust the shares are 4.0% and 13.3%. Accident counts are sparse and more
concentrated: one section supplies 2 of the 11 upper-bin accidents and the five
largest contributors supply 6 of 11. The upper-bin exposure HHI is 0.0058 for
wind and 0.0078 for gust, compared with 0.0025 and 0.0024 in the respective
lowest bins. Geographic selectivity, differing samples, monthly rather than
same-day weather allocation, road-length weighting, and sparse counts therefore
all contribute. The evidence does not justify attributing the full difference
to traffic volume alone.

The exposure-weighted all-bin baseline accident rate of contributing sections
is 0.138 per million VKT in the upper mean-wind bin versus 0.121 in the calm
bin; for gust the corresponding values are 0.126 and 0.121. Together with the
within-stratum attenuation, this classifies baseline road-risk/exposure
weighting as **(a) a supported explanation for part of the discrepancy**. Sparse
counts and the non-identical denominators leave the size of that contribution
uncertain, so it is not a complete causal explanation.

## Minimum thesis restructuring

| Former role | Aligned role |
|---|---|
| Q1 weather-frequency O/E | Q1 primary weather-frequency O/E |
| Q2 matched-time analysis | Supporting robustness analysis |
| Q3 broad collection of traffic analyses | Split into Q2 approximate correction and Q3 monthly-frequency VKT rate |
| Annual conditional Poisson | Supporting annual analysis |
| Allocated 762-case model | Supporting daily analysis/appendix |
| Former 613-case strict design | Historical repository output, superseded |
| Current 694-case same-day timestamp allocation | Supporting sensitivity to monthly allocation |
| Severity, daylight, seasonal interaction | Supporting/appendix |

This is the minimum change that makes the research questions, Methods, Results,
Discussion, and Conclusion tell the same story. Primary O/E remains first;
existing analyses are retained and relabelled rather than deleted.

## Scientific assumptions retained for supervisor discussion

1. The full 24-hour daily counter total is allocated using 07:00–24:00 weather.
   This is internally coherent as an explicit proportional-allocation model but
   assumes no usable hourly traffic profile. It should be discussed with the
   supervisor because it sets the estimand of the main traffic analysis.
2. Accident weather can match across midnight when it is within five minutes.
   This is internally consistent with nearest-time matching, but the calendar
   day used for traffic remains the accident date. It is acceptable as a stated
   boundary convention and should be confirmed with the supervisor.
3. Pooled calendar-month frequencies treat the 2007–2025 station record as the
   typical within-month distribution applied to 2019–2024 traffic days. This is
   the method Kristján specified; it sacrifices day-specific weather for a
   stable denominator.

## Output and code map

- Selection logic and hashes: `src/tables/counter_selection_audit.py` →
  `reports/main/tables/monthly_vkt_selection.csv`.
- Pooled monthly weather: `src/weather/monthly_frequency.py` →
  `data/analysis/weather_monthly.csv`.
- Monthly VKT construction: `src/traffic/monthly_vkt.py` →
  `data/analysis/monthly_vkt.csv` and `data/analysis/monthly_vkt_section.csv`.
- Main rate table and figure: `src/tables/monthly_vkt_rate.py` and
  `src/figures/monthly_vkt_rate.py` → `reports/main/tables/monthly_vkt_rate.csv`
  and `reports/main/figures/monthly_vkt_rate.png`.
- Discrepancy audit: `src/tables/monthly_vkt_discrepancy.py` →
  `reports/main/tables/monthly_vkt_discrepancy.csv`.
- Rough correction: `src/tables/traffic_corrected_oe.py` and
  `src/figures/traffic_corrected_oe.py` →
  `reports/main/tables/weather_oe_traffic_corrected.csv` and
  `reports/main/figures/weather_oe_traffic_corrected.png`.
- Regression and arithmetic checks: `tests/test_monthly_vkt.py`,
  `tests/test_traffic_corrected_oe.py`, and `src/validation/traffic.py`.

Historical scripts and outputs remain in place. Their thesis role changes where
the latest method supersedes them; their records are not deleted.
