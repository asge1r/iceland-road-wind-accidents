# Final analysis validation

All checks below passed against the current local canonical files.

## Fixed primary analysis

- Population: 6,120 rural injury accidents, 2007--2024.
- Primary weather match: 5,912 accidents within 20 km and 5 minutes.
- Primary exposure: maximum wind gust (`fg`) in 3 m/s intervals.
- Standardisation: weather station, calendar year, and season.
- Uncertainty: 5,000 weather-station-clustered bootstrap samples.

## Data checks

| Check | Result |
|---|---:|
| Unique accident identifiers | 6,120 / 6,120 |
| Clean weather observations scanned | 211,497,897 |
| `f` range | 0.000 to 44.990 m/s |
| `fg` range | 0.000 to 64.990 m/s |
| Invalid `f`, invalid `fg`, or `fg + 0.5 < f` | 0, 0, 0 |
| Daily counter-days | 774,274 |
| Daily counter-days with daytime wind | 738,424 (95.37%) |

## Primary O/E result

| Gust interval | Observed | Expected | O/E | 95% interval |
|---|---:|---:|---:|---:|
| >=36 m/s | 25 | 4.1 | 6.09 | 3.65--8.94 |

Observed counts sum to 5,912. Expected counts are rounded to one decimal in this table and therefore sum to 5,912.1.

## Distance sensitivity for fg >=36 m/s

| Maximum distance | Matched accidents | O/E | 95% interval |
|---|---:|---:|---:|
| 10 km | 4,622 | 7.27 | 4.38--10.63 |
| 20 km | 5,912 | 6.09 | 3.65--8.94 |
| 30 km | 6,109 | 5.99 | 3.54--8.87 |

## Scope decision

Single-vehicle, run-off-road, rollover, fall, or other accidents account for 4,184 of 6,120 study accidents (68.4%).
This supports the physical relevance of wind gusts. A separate O/E curve for this group would be an exploratory appendix analysis, not a replacement for the fixed all-injury primary result.

## Decision

The primary analysis is internally consistent and ready to freeze: `fg`, a 20 km weather-station limit, a 5-minute time limit, and wind-frequency-adjusted O/E as the main result. Daily traffic remains a supporting analysis.
