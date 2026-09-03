# Final analysis validation

All checks below passed against the current local canonical files.

## Fixed primary analysis

- Population: 6,414 rural injury accidents, 2007--2025.
- Primary weather match: 6,192 accidents within 20 km and 5 minutes.
- Primary exposure: mean wind speed (`f`) in 5 m/s intervals.
- Standardisation: weather station and season; weather frequency is pooled across 2007--2025.
- Uncertainty: 5,000 weather-station-clustered bootstrap samples.

## Data checks

| Check | Result |
|---|---:|
| Unique accident identifiers | 6,414 / 6,414 |
| Temperature matches within 20 km and 5 minutes | 5,707 / 6,414 |
| Raw weather observations | 226,580,952 |
| Clean weather observations retained | 211,497,897 |
| Weather observations excluded by fixed rules | 15,083,055 |
| Clean weather retention, all delivered rows | 93.34% |
| Rate-analysis accidents with shared station within 20 km and 5 minutes | 4,958 |
| Daily counter-days | 774,274 |
| Daily counter-days with daytime wind | 738,424 (95.37%) |

## Primary O/E result

| Mean wind-speed interval | Observed | Expected | O/E | 95% interval |
|---|---:|---:|---:|---:|
| >=25 m/s | 16 | 6.4 | 2.49 | 0.86--5.37 |

Observed counts sum to 6,192. Expected counts are rounded to one decimal in this table.
The >=25 m/s O/E interval includes one; this sparse upper bin is descriptive rather than a separate precise result.

## Weather-station distance check

At 20--25 m/s, O/E remains above one under 10, 20, and 30 km weather-station limits.

## Stratified vehicle-kilometre result

The shared-station rate model retains 4,958 accidents. At >=25 m/s, the within-stratum time-proportional rate ratio is 4.49 (95% CI 2.75--7.34).
The serious/fatal version retains 1,054 accidents. Its 15--20 m/s rate ratio is 1.90.
The seasonal model uses coarse 0--10, 10--15, and >=15 m/s intervals; all four >=15 m/s estimates are above one.

## Time-stratified case-crossover result

At mean wind >=15 m/s versus 0--5 m/s, the matched odds ratio is 1.61 (95% CI 1.39--1.87).

## Results using traffic data

Restricting the 20--25 m/s rate model to official VDU and SDU gives RR 1.93. Excluding zero counter-days changes the corresponding daily-traffic percentage by less than two percentage points.
The sustained-wind table contains 733,080 sufficiently complete counter-days. Traffic is 88.9% of its calendar expectation on days with at least six hours at f >=15 m/s.
The allocated daily-counter model retains 760 accidents. Its >=15 versus 0--10 m/s rate ratio is 3.38 (95% CI 2.46--4.62). The within-day denominator is estimated, not observed hourly traffic.
The serious/fatal daily model retains 164 accidents; its upper rate ratio is 4.16. Restricting the all-injury allocation to 07:00--24:00 gives 3.50, versus 3.38 for the full day.
The appendix full-day-mean check retains 767 accidents. At >=15 m/s versus 0--10 m/s, RR is 2.42 (95% CI 1.38--4.24), based on 14 upper-category accidents.
The 5, 10, and 20 km counter-assignment table confirms that both non-reference coarse estimates are generated reproducibly and retain valid confidence-interval ordering.

## Weather-station distance comparison for fg >=35 m/s (secondary analysis)

| Maximum distance | Matched accidents | O/E | 95% interval |
|---|---:|---:|---:|
| 10 km | 4,858 | 6.12 | 3.58--9.26 |
| 20 km | 6,192 | 5.06 | 2.94--7.57 |
| 30 km | 6,399 | 5.00 | 2.95--7.45 |

## Annual-traffic quality

The 2007--2025 annual-traffic input contains 22,982 road-section/year rows. Nonpositive published VDU values occur in 1,509 rows, and nonpositive derived VHDU residuals occur in 552 rows. These rows are excluded from the corresponding positive vehicle-kilometre exposure; they are not replaced or imputed.

## Study-population decision

Single-vehicle, run-off-road, rollover, fall, or other accidents account for 4,348 of 6,414 study accidents (67.8%).
This supports the relevance of wind conditions to vehicle control. A separate O/E curve for this group would be an exploratory appendix analysis, not a replacement for the fixed all-injury primary result.

## Decision

The primary analysis is internally consistent and ready to freeze: `f`, a 20 km weather-station limit, a 5-minute time limit, and wind-frequency-adjusted O/E as the main result. Gust and daily traffic remain secondary analyses.
