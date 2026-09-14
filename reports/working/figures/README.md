# Supporting figures

This directory holds supporting analyses and diagnostics that are not currently
included as figures in the thesis. These are reproducible script outputs;
moving them here does not change their calculations.

| Files | Generator | Interpretation |
| --- | --- | --- |
| `accident_types.png` | `src.figures.accident_profiles` | Overall accident-type distribution. The two thesis profile plots still go to `reports/main/figures/`. |
| `severity_context.png` | `src.figures.estimates`, arguments in `src.analyze.severity_context_tasks` | Subset of the full severity model: time of day, daylight and season. |
| `accident_flow.png`, `weather_flow.png`, `traffic_flow.png` and PDF counterparts | `src.figures.data_flow` | Data-selection diagrams. |
| `traffic_wind.png`, `traffic_wind_period.png` | `src.figures.daily_traffic` | Traffic response grouped by daily mean wind during 10:00–21:59. |
| `allocated_rate.png` | `src.figures.allocated_rate` | Counter-year rate ratios using accident-time wind and full-day weather allocation. |
| `day_rate.png` | `src.figures.counter_rate` | Counter-year rate ratios grouped by full-day mean wind. |
| `daily_season_oe.png` | `src.figures.daily_season_oe` | Seasonal traffic-standardised O/E from the supporting daily-counter panel. |
| `wind_oe_comparison.png` | `src.figures.wind_oe_comparison` | Weather-frequency, annual-traffic and daily-traffic O/E, with different samples and bins. |
| `wind_rate_official.png` | `src.figures.rate`, arguments in `src.analyze.annual_traffic_tasks` | Annual-traffic rate sensitivity analysis using official traffic periods. |

The first twelve existing files (including `traffic_flow.pdf`) were moved here
from `reports/main/figures/` on 14 September 2026. `wind_rate_official.png` was
already here. Missing PDF counterparts are generated on the next data-flow run.

See the [main figure list](../../main/figures/README.md) for the new figures and
the O/E figures updated for the thesis, and [the pipeline](../../../docs/pipeline.md)
for their exact inputs and commands. The numerical input tables have not moved.
