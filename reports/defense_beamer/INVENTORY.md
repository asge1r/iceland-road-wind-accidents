# Availability checked before slide construction

Scientific authority: submitted 48-page thesis in `reports/thesis/`, with figure
numbers verified through its LaTeX references. The PPTX is the content/style starting
point, not the scientific authority. All paths below are relative to repository root.

| Method | Variable | Figure | Available panels | Sample and years | New analysis needed? |
|---|---|---|---|---|---|
| Weather-frequency O/E | Mean wind | 4.3, `reports/main/figures/wind_oe_panels.pdf` | All year + four seasons | 6,259 rural linked injury accidents, 2007–2025 | No |
| Weather-frequency O/E | Gust | 4.4, `reports/main/figures/gust_oe_panels.pdf` | All year + four seasons | Same 6,259, 2007–2025 | No |
| Weather-frequency O/E | Temperature | 4.5, `reports/main/figures/temperature_oe_panels.pdf` | All year + four seasons | Same 6,259, independently matched temperature, 2007–2025 | No |
| Corrected O/E | Mean wind | 4.8, `reports/main/figures/weather_oe_traffic_corrected_f.pdf` | All year only | Same 6,259, 2007–2025; response from 2019–2024 | No for annual; seasonal unavailable |
| Corrected O/E | Gust | 4.9, `reports/main/figures/weather_oe_traffic_corrected_fg.pdf` | All year only | Same 6,259, 2007–2025; response from 2019–2024 | No for annual; seasonal unavailable |
| Corrected O/E | Temperature | 4.11, `reports/main/figures/weather_oe_traffic_corrected_temperature.pdf` | All year only | Same 6,259, 2007–2025; response from 2019–2024 | No for annual; seasonal unavailable |
| Estimated VKT | Mean wind | 4.14, `reports/main/figures/monthly_f_traffic_rate_panels.pdf` | All year + four seasons | 694 counter-linked accidents, 2019–2024 | No |
| Estimated VKT | Gust | 4.15, `reports/main/figures/monthly_fg_traffic_rate_panels.pdf` | All year + four seasons | Same 694, 2019–2024 | No |
| Estimated VKT | Temperature | 4.13, `reports/main/figures/monthly_temperature_traffic_rate_panels.pdf` | All year + four seasons | Same 694, 2019–2024 | No |

O/E numerical source: `reports/main/tables/weather_oe.csv` (all five periods).
Corrected numerical source: `reports/main/tables/weather_oe_traffic_corrected.csv`
contains only `All year`. Its figure generator explicitly rejects other periods.
No seasonal corrected panels will be invented or computed.

VKT sources: retained `data/analysis/monthly_vkt.csv`, `monthly_vkt_section.csv`
and the existing 694 eligible records in `data/analysis/vkt_accidents.csv`, using
the thesis figure generator's existing display decomposition and tail grouping.
No new weather allocation, exposure estimation or accident selection is required.
The VKT weather denominator uses station–calendar-month frequencies pooled over
2007–2025, although the accident/count period is 2019–2024.

The original O/E and VKT panels have different seasonal scales. Every panel's
original limits and tick values must be preserved in any presentation-only export.
