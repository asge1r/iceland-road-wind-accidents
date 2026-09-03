# Data

The repository contains code, documentation, the thesis draft, and selected
small results. Raw and processed data remain on each researcher's computer.
`data/README.md` gives the exact local paths needed to rebuild the analysis.

## Source data

| Data family | Provider | Local directory | Contents used |
|---|---|---|---|
| Accidents | Icelandic Transport Authority / national accident register | `data/raw/accidents/` | Accident time, coordinates, injury code, accident type, vehicle count, and road link. |
| Weather | [Icelandic Met Office API](https://api.vedur.is/weather/observations/aws/raw/10min) | `data/raw/weather/` | Ten-minute station, time, mean wind (`f`), reported wind gust (`fg`), and temperature (`t`). |
| Annual traffic | [Icelandic Road and Coastal Administration](https://www.vegagerdin.is/vegakerfid/umferd-og-slys/umferd) | `data/raw/traffic/annual/` | Road section, start/end station, length, ADU, SDU, VDU, and vehicle-kilometres. |
| Daily traffic | Icelandic Road and Coastal Administration counter PDFs | `data/raw/traffic/daily_pdf/` | Date, road section, reported station (`stöð`), direction/lane channel, and daily count. |
| Road geography | [Road Administration MapServer](https://vegasja.vegagerdin.is/arcgis/rest/services/data/vegakerfi/MapServer) | `data/raw/traffic/reference/` | Road geometry and official start/end stations. |
| Urban boundaries | [Statistics Iceland WFS](https://gis.is/geoserver/Hagstofan/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=Hagstofan:thettbylisstadir&outputFormat=application/json) | `data/raw/accidents/` | Urban-area polygons used to classify accident coordinates. |

## Analysis files

`data/analysis/` is the readable layer for routine inspection, data analysis,
and advisor review. It is generated with `python -m src.export_tables` and is
not committed because it is derived from authorised local data deliveries.

| File | Unit | Key columns used |
|---|---|---|
| `analysis/accidents.csv` | One rural injury accident | `id`, time, coordinates, outcome fields, road section, hour, weekday, meteorological season, and VDU/SDU/VHDU traffic period. |
| `analysis/accident_conditions.csv` | One rural injury accident | Independent wind and temperature matches, match distances and time differences, solar elevation, and estimated daylight class. |
| `analysis/weather_frequency.csv` | Station, season, variable, and interval | Tidy wind and temperature counts pooled across 2007--2025. `unit` distinguishes m/s and degrees Celsius. |
| `analysis/case_control.csv` | Accident or matched control time | Same-station, same-hour, same-weekday wind and temperature samples within month and year. |
| `analysis/annual_traffic.csv` | Road section and year | road section, length, ADU, SDU, and VDU. |
| `analysis/conditional_poisson_input.csv` | Road section, year, traffic period, and mean-wind interval | Rows with positive estimated vehicle-kilometres from road/year/period groups containing at least one accident. Groups with no accidents do not add a comparison to this model. |
| `analysis/seasonal_poisson_input.csv` | Road section, year, meteorological season, and mean-wind interval | Year-specific estimated vehicle-kilometres and matched injury-accident counts used by the four seasonal models. |
| `analysis/traffic_exposure_full.csv` | Traffic period and mean-wind interval | 18 rows containing estimated vehicle-kilometres from every eligible road section and the associated accidents for the descriptive accident-per-vehicle-km table. It includes more road sections than the conditional-model input. |
| `analysis/selection_summary.csv` | Dataset-selection step | Eight counts used to draw the accident and traffic selection figures. |
| `analysis/daily_traffic.csv` | Counter site and date | Optional large CSV containing the observed daily count, mean-wind summaries, and observation counts in six mean-wind intervals. |
| `analysis/daily_counter_locations.csv` | Counter site and year | Road section and geometry-interpolated coordinates used by selected-counter rate analyses. |
| `analysis/manifest.csv` | One analysis file | record count, available columns, and a short description. |

The accident deliveries call their record key `nid` or `NID`. Preparation
renames that field to `id` but preserves its original values. These values are
stable source record keys used to join the event, road-link, and vehicle files;
they are therefore not replaced by row numbers such as 1, 2, 3, which would
change when records were sorted or filtered. The source field `flokkur2` is not
used by the analysis and is not retained in prepared or analysis files.

The primary O/E analysis joins `accidents.csv` to `accident_conditions.csv` by
`id` and uses `weather_frequency.csv`; it
does not use traffic. It writes the intermediate O/E calculation table to
`reports/working/tables/oe_station_bins.csv`. Mean wind speed
`f` is its primary weather measure and matched-time wind gust `fg` is secondary. The daily
traffic scripts use `daily_traffic.csv`; the direct daily-rate comparison also
uses `daily_counter_locations.csv`. The vehicle-kilometre scripts use
`conditional_poisson_input.csv` and `traffic_exposure_full.csv`. Therefore the ordinary
analysis stage reads only files in `data/analysis/`, not `data/raw/` or
`data/processed/`.
