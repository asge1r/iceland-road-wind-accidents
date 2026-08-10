# Analysis result map

## A. Wind-frequency-standardized accident O/E

Main result: `main/wind_gust_accident_risk.png` and the accompanying CSV/TeX
table. Expected accidents are based on local cleaned 10-minute wind frequency
within station, year, and season. This is the thesis-primary result.

Keep traffic variants explicitly labelled as sensitivities:

- `supporting/road_section_wind_adjustment_comparison.png`: same exact
  road-section subset, comparing wind-frequency-only with annual/seasonal
  traffic plus wind exposure.
- `supporting/daily_traffic_adjustment_comparison.png`: restricted 2019-2024
  observed daily-counter sensitivity.

These curves must not be merged into one unlabeled O/E series because their
denominators and represented accident subsets differ.

## B. Road-section table and graphical summary

- `main/road_wind_table.csv`: one row per section/year/traffic period.
- `main/mean_wind_table.csv`: long readable `f` table by wind bin.
- `main/wind_gust_table.csv`: long readable `fg` table by wind bin.
- `supporting/road_section_traffic_period_summary.png`: accidents and typical
  traffic by official traffic period.
- `supporting/road_section_wind_traffic_adjusted.png`: accident rates per
  estimated vehicle-kilometre for `f` and `fg`.

The tables are descriptive road-section products. The O/E figure in Analysis A
remains the inferential headline; Analysis B explains road, traffic, period,
surface, and exposure context.
