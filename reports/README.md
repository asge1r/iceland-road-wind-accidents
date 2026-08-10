# Results

`main/` contains the complete active result set. Every active figure is in
English and has a CSV table or documented source data behind it.

## Data overview

- `accident_selection.png`: available accident records, injury severity, and
  primary wind-match coverage.
- `weather_selection.png`: retained and excluded 10-minute wind observations.
- `traffic_selection.png`: annual and daily traffic coverage.
- `accidents.png`: accident-type distribution.
- `vehicles.png`: registered vehicles involved per accident.
- `severity.png`: accident-type composition by injury severity.
- `accidents.csv`: the values behind these descriptive figures.

## Main wind result

- `gust_risk.png` and `gust_risk.csv`: wind-frequency-adjusted observed/expected
  accident occurrence by 3 m/s maximum-gust interval.
- `gust_coverage.csv`: accident coverage at 10, 20, and 30 km.
- `weather_audit.csv`: weather cleaning and accident matching audit.

## Road and traffic results

- `road_table.csv`: road section, year, traffic period, wind frequency,
  traffic, road length, and accident counts.
- `mean_wind.csv`: readable mean-wind subtable.
- `gust.csv`: readable maximum-gust subtable.
- `road_coverage.csv`: coverage and exclusions for the road table.
- `traffic_adjustment.png` and `traffic_adjustment.csv`: SDU/VDU-only
  same-subset comparison with and without estimated period traffic adjustment.
- `daily_traffic.png` and `daily_traffic.csv`: observed daily traffic relative
  to a typical day at the same counter, year, month, and weekday.
- `traffic_validation.png`: clean comparison of annualized daily counter
  traffic with official ADU.
- `crosswind.png` and `crosswind.csv`: exploratory comparison below and above
  9 m/s crosswind, frequency-adjusted within weather station and week but not
  adjusted for traffic.

Thesis drafts are not part of the shared results package. Diagnostics and
superseded outputs are under the local `archive/`, not in the active result
folder.
