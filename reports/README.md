# Reports

`main/` contains the small tables and figures cited in the thesis. The primary
result is mean-wind O/E; gust and traffic figures are supporting results.

- `figures/mean_wind_oe.png`: primary mean-wind O/E result.
- `tables/mean_wind_oe.csv`: values behind the primary figure.
- `tables/mean_wind_radius_sensitivity.csv`: primary upper-wind O/E estimates
  under the 10, 20, and 30 km station limits.
- `tables/case_control_weather.csv`: time-stratified supporting estimates
  summarised in the main-text evidence table.
- `figures/conditional_poisson_rate_ratio_by_wind.png`: main-text supporting
  road-section/year/traffic-period rate-ratio model.
- `figures/gust_oe.png`: supporting matched-time wind-gust O/E result.
- `figures/mean_wind_by_season_oe.png` and
  `figures/mean_wind_by_vehicle_group_oe.png`: descriptive mean-wind subgroup
  figures; corresponding gust figures use the `gust_` prefix.
- `tables/final_analysis_validation.md`: fixed analysis checks.
- `tables/annual_traffic_quality.csv`: inspectable checks of the annual traffic
  input and the positive-exposure exclusions used by the supplementary model.
- `tables/traffic_sensitivity.csv`: official-period, zero-counter-day, and
  annual-traffic quality sensitivities reported together.
- `tables/daily_traffic_by_high_wind_duration.csv` and its matching figure:
  observed daily traffic by hours with mean wind at least 15 m/s.
- `tables/daily_allocated_rate_ratio_by_wind.csv` and its matching figure:
  selected-counter rate ratios using observed daily traffic allocated by
  within-day wind frequency.
- `tables/daily_counter_rate_ratio_by_wind.csv`: detailed six-bin observed
  full-day traffic sensitivity within counter and year.
- `tables/daily_counter_rate_ratio_coarse_by_wind.csv` and
  `figures/daily_counter_rate_ratio_coarse_by_wind.png`: preferred inferential
  version using stable combined upper-wind categories.
- `tables/daily_counter_radius_sensitivity.csv`: 5, 10 and 20 km checks for
  both non-reference coarse categories.
- `figures/*_flow.png`: simple accident, weather, and traffic data-flow figures.
- `figures/daily_traffic_by_wind.png`: appendix daily-traffic diagnostic.

`thesis/` contains the current English thesis draft and PDF. Files outside
these folders are local working material and are not part of the main report.

`working/` contains figures and tables retained for internal checking but not
cited in the main thesis.
