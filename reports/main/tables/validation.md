# Final analysis validation

All checks below passed against the current local analysis files.

## Fixed primary analysis

- Population: 6,414 rural injury accidents, 2007--2025.
- Primary weather match: 6,259 accidents within 20 km and 5 minutes.
- Primary weather measure: accident-time ten-minute mean wind speed (`f`) in 5 m/s intervals.
- Standardisation: weather station and season; weather frequency is pooled across 2007--2025.
- The O/E table is descriptive; formal uncertainty is assessed in the matched-time and traffic models.

## Data checks

| Check | Result |
|---|---:|
| Unique accident identifiers | 6,414 / 6,414 |
| Temperature matches within 20 km and 5 minutes | 6,259 / 6,414 |
| Raw weather observations | 232,459,562 |
| Clean weather observations retained | 230,458,950 |
| Weather observations excluded by fixed rules | 2,000,612 |
| Clean weather retention, all delivered rows | 99.14% |
| Rate-analysis accidents with shared station within 20 km and 5 minutes | 4,933 |
| Daily counter-days | 774,274 |
| Daily counter-days with daytime wind | 763,171 (98.57%) |

## Primary O/E result

| Mean wind >=20 m/s | Observed | Expected | O/E |
|---|---:|---:|---:|
| All injury (meidsli <=3) | 68 | 31.6 | 2.15 |
| Severe/fatal | 12 | 6.4 | 1.87 |

The all-injury row reconstructs all 6,259 matched accidents; serious/fatal accidents are its meidsli <=2 subset. Expected counts are rounded to one decimal.
The O/E values are descriptive and are not presented with confidence intervals.

## Stratified vehicle-kilometre result

The shared-station rate model retains 4,933 accidents. At >=25 m/s, the within-stratum time-proportional rate ratio is 4.95 (95% CI 3.07--7.98).
The serious/fatal version retains 1,055 accidents. Its 15--20 m/s rate ratio is 1.92.
The seasonal model uses coarse 0--10, 10--15, and >=15 m/s intervals; all four >=15 m/s estimates are above one.
The serious-or-fatal seasonal model uses the same intervals; its spring upper category contains only six accidents and is interpreted cautiously.

## Time-stratified case-crossover result

At mean wind >=15 m/s versus 0--5 m/s, the matched odds ratio is 1.61 (95% CI 1.38--1.87).
At gust >=30 m/s versus 0--10 m/s, the matched odds ratio is 2.74 (95% CI 1.96--3.85).
The formal wind-by-season likelihood-ratio test gives chi-square 14.30 on 6 degrees of freedom (p=0.026).

## Additional environmental comparisons

The joint matched-time model retains 6,257 accidents with both wind and temperature. Its adjusted >=15 versus 0--5 m/s wind odds ratio is 1.68 (95% CI 1.44--1.96).
The matched daylight comparison uses all 6,414 accidents, but only 985 strata change daylight class within the matched month and hour.
The severity-composition model contains 6,259 complete accidents and 1,424 serious-or-fatal outcomes. It estimates severity among recorded accidents, not accident occurrence.

## Results using traffic data

Restricting the 20--25 m/s rate model to official VDU and SDU gives RR 1.82. Excluding zero counter-days changes the corresponding daily-traffic percentage by less than two percentage points.
The illustrative denominator direction check changes the 20--25 m/s annual-model RR from 2.27 to 3.32 when the observed daily traffic percentage is applied mechanically. This is not a corrected estimate because full-day traffic does not identify traffic in ten-minute wind intervals.
The sustained-wind table contains 759,037 sufficiently complete counter-days. Traffic is 86.8% of its calendar expectation on days with at least six hours at f >=15 m/s.
The allocated daily-counter model retains 762 accidents. Its >=15 versus 0--10 m/s rate ratio is 3.62 (95% CI 2.65--4.94). The within-day traffic split is estimated, not observed hourly traffic.
The counter-section vehicle-kilometre table partitions 613 linked daytime accidents into non-overlapping minor-injury and severe/fatal groups for wind, gust, and temperature. Daily totals are observed and allocated using actual 07:00--24:00 weather on the same date; traffic within each ten-minute interval remains estimated.
The temperature vehicle-kilometre model retains 4,921 accidents. Relative to 0--3 degrees C, its below--6 estimate is 0.79 and its 3--6 estimate is 0.60.
The coarse >=15 m/s estimates are 1.42 for one-vehicle accidents and 2.37 for accidents involving two or more vehicles. These are separate subgroup estimates, not a formal test of their difference.
This retained sample is 40.9% of the 2019--2024 rural injury accidents. The generated appendix audit compares its severity, vehicle-count, season, and road-section composition with retained and excluded accidents.
The serious/fatal daily model retains 164 accidents; its upper rate ratio is 4.53. Restricting the all-injury allocation to 07:00--24:00 gives 3.74, versus 3.62 for the full day.
The shared seasonal daily panel reconstructs expected accidents within every counter-year-season group. Its full interaction test gives p=0.050; the secondary >=15 m/s interaction gives p=0.032. Both are retained, and the seasonal O/E uses 5,000 whole-counter bootstrap samples.
The main comparison figure retains separate denominators: annual-traffic O/E is 1.98 at 20--25 m/s, and daily-traffic O/E is 2.36 at >=15 m/s.
The appendix full-day-mean check retains 767 accidents. At >=15 m/s versus 0--10 m/s, RR is 2.73 (95% CI 1.55--4.78), based on 14 upper-category accidents.
The 5, 10, and 20 km counter-assignment table confirms that both non-reference coarse estimates are generated reproducibly and retain valid confidence-interval ordering.


## Annual-traffic quality

The 2007--2025 annual-traffic input contains 22,982 road-section/year rows. Nonpositive published VDU values occur in 1,509 rows, and nonpositive derived VHDU residuals occur in 552 rows. These rows are excluded from the corresponding estimated vehicle-kilometres; they are not replaced or imputed.

## Study-population decision

Single-vehicle, run-off-road, rollover, fall, or other accidents account for 4,348 of 6,414 study accidents (67.8%).
This supports the relevance of wind conditions to vehicle control. The separate appendix O/E curve for this group is exploratory and does not replace the fixed all-injury primary result.

## Decision

The primary analysis is internally consistent and ready to freeze: `f`, a 20 km weather-station limit, a 5-minute time limit, and wind-frequency-adjusted O/E as the main result. Gust, temperature, and traffic remain supporting analyses.
