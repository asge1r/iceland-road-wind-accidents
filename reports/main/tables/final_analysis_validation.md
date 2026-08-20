# Final analysis validation

All checks below passed against the current local canonical files.

## Fixed primary analysis

- Population: 6,414 rural injury accidents, 2007--2025.
- Primary weather match: 6,192 accidents within 20 km and 5 minutes.
- Primary exposure: mean wind speed (`f`) in 5 m/s intervals.
- Standardisation: weather station, calendar year, and season.
- Uncertainty: 5,000 weather-station-clustered bootstrap samples.

## Data checks

| Check | Result |
|---|---:|
| Unique accident identifiers | 6,414 / 6,414 |
| Clean weather observations scanned | 211,497,897 |
| `f` range | 0.000 to 44.990 m/s |
| `fg` range | 0.000 to 64.990 m/s |
| Invalid `f`, invalid `fg`, or `fg + 0.5 < f` | 0, 0, 0 |
| Daily counter-days | 774,274 |
| Daily counter-days with daytime wind | 738,424 (95.37%) |
| Rate-analysis accidents with shared station within 20 km and 5 minutes | 4,958 |

## Primary O/E result

| Mean wind-speed interval | Observed | Expected | O/E | 95% interval |
|---|---:|---:|---:|---:|
| >=25 m/s | 16 | 5.9 | 2.70 | 0.97--5.49 |

Observed counts sum to 6,192. Expected counts are rounded to one decimal in this table.

## Stratified vehicle-kilometre result

The shared-station rate model retains 4,958 accidents. At >=25 m/s, the within-stratum time-proportional rate ratio is 4.52 (95% CI 2.77--7.37).

## Distance sensitivity for fg >=36 m/s (secondary analysis)

| Maximum distance | Matched accidents | O/E | 95% interval |
|---|---:|---:|---:|
| 10 km | 4,858 | 7.14 | 4.35--10.43 |
| 20 km | 6,192 | 5.99 | 3.62--8.80 |
| 30 km | 6,399 | 5.89 | 3.54--8.68 |

## Scope decision

Single-vehicle, run-off-road, rollover, fall, or other accidents account for 4,348 of 6,414 study accidents (67.8%).
This supports the relevance of wind conditions to vehicle control. A separate O/E curve for this group would be an exploratory appendix analysis, not a replacement for the fixed all-injury primary result.

## Decision

The primary analysis is internally consistent and ready to freeze: `f`, a 20 km weather-station limit, a 5-minute time limit, and wind-frequency-adjusted O/E as the main result. Gust and daily traffic remain secondary analyses.
