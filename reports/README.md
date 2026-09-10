# Reports

`main/` contains the compact tables and figures retained for the thesis.
The primary result is mean-wind O/E. The other results answer narrower
questions about matched non-accident times, accident severity, season,
temperature, wind gust, and the available traffic data.

Key outputs are:

- `figures/weather_oe_annual.png`: all three weather variables for the complete
  year.
- `figures/wind_oe_panels.png`, `figures/gust_oe_panels.png`, and
  `figures/temperature_oe_panels.png`: the four seasonal panels for each
  weather variable.
- `tables/weather_oe.csv`: the plotted values for all four figures.
- `tables/wind_radius.csv`: the upper-wind estimates under
  10, 20, and 30 km weather-station limits.
- `tables/match_quality.csv`: transparent wind and temperature match counts,
  station use, distances, and time differences.
- `tables/year_oe.csv`: supporting O/E comparison that also controls for year
  within weather station and season.
- `tables/matched_weather.csv`: comparisons with matched non-accident
  times for mean wind, gust, and temperature.
- `figures/wind_rate.png` and
  `figures/season_rate.png`: results using annual
  traffic, including the four-season comparison.
- `figures/wind_rate_severity.png`: the
  serious-or-fatal result retained in the appendix because its highest
  interval contains only four accidents.
- `figures/wind_season_oe.png` and
  `figures/wind_vehicle.png`: descriptive mean-wind subgroups.
- `figures/wind_duration.png` and
  `figures/allocated_rate.png`: selected-counter results
  using observed daily traffic.
- `figures/*_flow.png`: accident, weather, and traffic selection.
- `tables/validation.md`: reproducible checks of the retained
  inputs and headline values.

`thesis/` contains the current English thesis source and PDF. `working/`
contains intermediate result tables used to construct or check the retained
outputs; they are not thesis inputs.
