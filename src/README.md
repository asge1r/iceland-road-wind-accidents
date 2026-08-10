# Programs

Run commands from the project root. The complete active result set is rebuilt
with:

```bash
.venv/bin/python -m src.run_analysis
```

To rebuild processed data from authorised raw data and then recreate results:

```bash
.venv/bin/python -m src.run_pipeline --stage all
```

## Prepare data

- `accidents/prepare_accidents.py`: builds the canonical 2007–2024 accident table
  from raw deliveries, source NID road links and urban boundaries. It does not
  delete damage-only accidents; the rural-injury sample is a separate output.
- `weather/clean_weather.py`: applies the documented `f` and `fg` cleaning rules.
- `accidents/classify_urban_rural.py`: shared urban-boundary classification helper.
- `traffic/prepare_annual_traffic.py`: creates the 2000–2025 ADU/SDU/VDU table.
- `traffic/extract_daily_traffic.py`: extracts PDF channels and sums them into
  one physical-counter/day count.
- `traffic/locate_daily_counters.py`: attaches documented counter coordinates to
  those counts without rereading PDFs.
- `traffic/prepare_daily_traffic.py`: compatibility implementation shared by the
  two focused traffic scripts; do not use it for new pipeline commands.
- `accidents/match_accidents_weather.py`: matches accidents to valid 10-minute wind.
- `weather/build_wind_frequency.py`: calculates wind frequency by station, year, and
  season.

## Create tables and figures

- `analysis/calculate_wind_risk.py`: builds the O/E calculation table.
- `analysis/create_wind_risk_report.py`: creates `gust_risk.png`,
  `gust_risk.csv`, coverage, and the weather audit.
- `analysis/build_road_section_wind_table.py`: creates large working tables and the
  retained `traffic_adjustment.png` figure.
- `analysis/analyze_daily_traffic.py`: creates the daily traffic diagnostic.
- `analysis/build_daily_traffic_wind_analysis.py`: creates the transparent
  counter-day wind-response data, the pooled O/E traffic table, the
  VDU/SDU/VHDU table, and the two daily-traffic figures. It uses observed
  daily counts and standardises expected traffic within counter, year, month,
  and weekday.
- `analysis/analyze_daily_counter_availability.py`: checks whether a daily
  traffic record is less likely to be available on windy days, using the same
  counter/year/month/weekday standardisation as the daily traffic analysis.
- `figures/create_crosswind_figure.py`: creates the exploratory,
  frequency-adjusted crosswind figure from its verified summary table.
- `figures/create_data_overview_figures.py`: creates the three data-selection
  figures.
- `figures/create_accident_profile_figure.py`: creates the accident overview.
- `figures/create_counter_weather_distance_figure.py`: creates the daily
  counter-to-weather-station distance quality-control figure.

Diagnostics are written under `archive/generated_diagnostics/`. Experimental
models are not part of the active code set.
