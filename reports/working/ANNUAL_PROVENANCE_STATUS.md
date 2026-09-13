# Annual output status after 13 September 2026 correction

The current annual denominator and all current model variants were regenerated
from canonical cleaned weather and traffic. See
[the correction report](../../docs/annual_live_correction.md) for the verified
results, exact file inventory, and backup.

The authoritative annual model tables are `reports/main/tables/wind_rate*.csv`,
`temperature_rate.csv`, and `season_rate*.csv`; descriptive rates are in
`absolute_rate.csv`. Current working outputs are `tables/wind_rate_official.csv`,
`tables/rate_accident_weather_audit.csv`,
`tables/estimated_crash_rate_by_wind_audit.csv`, and the annual columns of
`tables/season_method_comparison.csv`. Their dependent figures and generated
thesis tables were regenerated as well.

The following pre-existing working files are historical diagnostics, not current
annual results. None is read by current Python source or the active thesis.
They retain their original values and files for historical comparison:

- `tables/conditional_poisson_rate_ratio_sdu.csv`
- `tables/conditional_poisson_rate_ratio_vdu.csv`
- `tables/conditional_poisson_rate_ratio_vhdu.csv`
- `tables/rate_ratio_summer_sdu.csv`
- `tables/rate_ratio_winter_vdu.csv`
- `tables/rate_ratio_one_vehicle.csv`
- `tables/rate_ratio_two_plus_vehicles.csv`
- `tables/estimated_crash_rate_by_wind.csv`
- `tables/road_wind_full.csv`
- `tables/traffic_adjusted_oe_audit.csv`
- `tables/traffic_adjusted_oe_superseded.csv`
- `tables/traffic_adjusted_observed_expected_by_wind.csv`
- Corresponding pre-existing figures with those stems under `figures/`.

These historical variants are not replacements for the current all-period,
official VDU+SDU, seasonal, outcome-specific, or temperature analyses. No historical
model definition was reintroduced into the current analysis.
