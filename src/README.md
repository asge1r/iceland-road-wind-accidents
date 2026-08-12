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
- `traffic/download_road_geometry.py`: downloads the official road-section geometry
  and start/end stations used for the primary PDF-`stöð` location rule.
- `traffic/locate_daily_counters_from_station.py`: applies the direct official
  PDF-`stöð` location rule. A counter without a valid official section is kept
  but explicitly labelled `location_unavailable`; it is not silently relocated.
- `traffic/validate_station_locations.py`: independently checks calculated
  PDF-`stöð` coordinates against the official 20 m road-point layer.
- `traffic/daily_pdf_parser.py`: the narrowly scoped PDF parsing helper used by
  `extract_daily_traffic.py`; it contains no location or weather analysis.
- `accidents/match_accidents_weather.py`: matches accidents to valid 10-minute wind.
- `weather/build_wind_frequency.py`: calculates wind frequency by station, year, and
  season.
- `export_working_tables.py`: exports the five small working tables documented in
  `docs/data_contracts.md`; it does not perform any statistical analysis.
- `export_replication_bundle.py`: exports the small Git-tracked result bundle.
- `reproduce_results.py`: redraws core figures from that bundle without raw data.

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
