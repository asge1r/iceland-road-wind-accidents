# Reports

`main/` contains the small tables and figures cited in the thesis. The primary
result is mean-wind O/E; gust and traffic figures are supporting results.

- `figures/mean_wind_oe.png`: primary mean-wind O/E result.
- `tables/mean_wind_oe.csv`: values behind the primary figure.
- `figures/gust_oe.png`: supporting maximum-gust O/E result.
- `figures/gust_factor_distribution.png`: descriptive distribution of `fg/f`
  in clean weather observations.
- `figures/mean_wind_by_season_oe.png` and
  `figures/mean_wind_by_vehicle_group_oe.png`: descriptive mean-wind subgroup
  figures; corresponding gust figures use the `gust_` prefix.
- `tables/final_analysis_validation.md`: fixed analysis checks.
- `figures/*_flow.png`: simple accident, weather, and traffic data-flow figures.
- `figures/daily_traffic_by_wind.png`: appendix daily-traffic diagnostic.
- `figures/stratified_crash_rate_ratio_by_wind.png`: appendix annual-traffic
  comparison. Its table also records the alternative counter-informed allocation.

`thesis/` contains the current English thesis draft and PDF. Files outside
these folders are local working material and are not part of the main report.

`working/` contains figures and tables retained for internal checking but not
cited in the main thesis. `docs/supervisor_review_checklist.md` maps the
advisor's requested checks to the relevant data, code, figures and thesis text.
