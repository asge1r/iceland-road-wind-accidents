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
| Raw weather observations | 226,580,952 |
| Clean weather observations retained | 211,497,897 |
| Weather observations excluded by fixed rules | 15,083,055 |
| Rate-analysis accidents with shared station within 20 km and 5 minutes | 4,958 |
| Daily counter-days | 774,274 |
| Daily counter-days with daytime wind | 738,424 (95.37%) |

## Primary O/E result

| Mean wind-speed interval | Observed | Expected | O/E | 95% interval |
|---|---:|---:|---:|---:|
| >=25 m/s | 16 | 6.4 | 2.49 | 0.86--5.37 |

Observed counts sum to 6,192. Expected counts are rounded to one decimal in this table.
The >=25 m/s O/E interval includes one; this sparse upper bin is descriptive rather than a separate precise result.

## Stratified vehicle-kilometre result

The shared-station rate model retains 4,958 accidents. At >=25 m/s, the within-stratum time-proportional rate ratio is 4.49 (95% CI 2.75--7.34).

## Weather-station distance comparison for fg >=35 m/s (secondary analysis)

| Maximum distance | Matched accidents | O/E | 95% interval |
|---|---:|---:|---:|
| 10 km | 4,858 | 6.12 | 3.58--9.26 |
| 20 km | 6,192 | 5.06 | 2.94--7.57 |
| 30 km | 6,399 | 5.00 | 2.95--7.45 |

## Scope decision

Single-vehicle, run-off-road, rollover, fall, or other accidents account for 4,348 of 6,414 study accidents (67.8%).
This supports the relevance of wind conditions to vehicle control. A separate O/E curve for this group would be an exploratory appendix analysis, not a replacement for the fixed all-injury primary result.

## Decision

The primary analysis is internally consistent and ready to freeze: `f`, a 20 km weather-station limit, a 5-minute time limit, and wind-frequency-adjusted O/E as the main result. Gust and daily traffic remain secondary analyses.
