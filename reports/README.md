# Reports

`main/` contains the compact tables and figures retained for the thesis.
The primary result is mean-wind O/E. The other results answer narrower
questions about matched non-accident times, accident severity, season,
temperature, wind gust, and the available traffic data.

Key outputs are:

- `figures/mean_wind_oe.png` and `tables/mean_wind_oe.csv`: the primary result
  and its plotted values.
- `tables/mean_wind_radius_sensitivity.csv`: the upper-wind estimates under
  10, 20, and 30 km weather-station limits.
- `tables/case_control_weather.csv`: comparisons with matched non-accident
  times for mean wind, gust, and temperature.
- `figures/conditional_poisson_rate_ratio_by_wind.png` and
  `figures/seasonal_poisson_rate_ratio_by_wind.png`: results using annual
  traffic, including the four-season comparison.
- `figures/conditional_poisson_rate_ratio_serious_fatal_by_wind.png`: the
  serious-or-fatal result retained in the appendix because its highest
  interval contains only four accidents.
- `figures/gust_oe.png`: matched-time wind-gust O/E.
- `figures/temperature_oe.png`: exploratory temperature O/E.
- `figures/mean_wind_by_season_oe.png` and
  `figures/mean_wind_by_vehicle_group_oe.png`: descriptive mean-wind subgroups.
- `figures/daily_traffic_by_high_wind_duration.png` and
  `figures/daily_allocated_rate_ratio_by_wind.png`: selected-counter results
  using observed daily traffic.
- `figures/*_flow.png`: accident, weather, and traffic selection.
- `tables/final_analysis_validation.md`: reproducible checks of the retained
  inputs and headline values.

`thesis/` contains the current English thesis source and PDF. `working/`
contains intermediate result tables used to construct or check the retained
outputs; they are not thesis inputs.
