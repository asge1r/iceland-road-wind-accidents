# Data

The repository contains code, documentation, the thesis draft, and selected
small results. Raw and processed data remain on each researcher's computer.
`data/README.md` gives the exact local paths needed to rebuild the analysis.

## Source data

| Data family | Provider | Local directory | Contents used |
|---|---|---|---|
| Accidents | Icelandic Transport Authority / national accident register | `data/raw/accidents/` | Accident time, coordinates, injury code, accident type, vehicle count, and road link. |
| Weather | [Icelandic Met Office API](https://api.vedur.is/weather/observations/aws/raw/10min) | `data/raw/weather/` | Ten-minute station, time, mean wind (`f`), maximum gust (`fg`), and temperature (`t`). |
| Annual traffic | [Icelandic Road and Coastal Administration](https://www.vegagerdin.is/vegakerfid/umferd-og-slys/umferd) | `data/raw/traffic/annual/` | Road section, start/end station, length, ADU, SDU, VDU, and vehicle-kilometres. |
| Daily traffic | Icelandic Road and Coastal Administration counter PDFs | `data/raw/traffic/daily_pdf/` | Date, road section, reported station (`stöð`), direction/lane channel, and daily count. |
| Road geography | [Road Administration MapServer](https://vegasja.vegagerdin.is/arcgis/rest/services/data/vegakerfi/MapServer) | `data/raw/traffic/reference/` | Road geometry and official start/end stations. |
| Urban boundaries | [Statistics Iceland WFS](https://gis.is/geoserver/Hagstofan/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=Hagstofan:thettbylisstadir&outputFormat=application/json) | `data/raw/accidents/` | Urban-area polygons used to classify accident coordinates. |

## Canonical analysis files

`data/analysis/` is the compact layer for routine inspection, data analysis,
and advisor review. It is generated with `python -m src.export_tables` and is
not committed because it is derived from authorised local data deliveries.

| File | Unit | Key columns used |
|---|---|---|
| `analysis/accidents.csv` | One rural injury accident | identifier, time, injury code, accident-type code, vehicle count, weather-station identifier, match distance/time difference, `f`, and `fg`. Coordinates and detailed matching audit fields remain in `processed/`. |
| `analysis/weather_frequency.csv` | Station, season, wind variable, and wind bin | Tidy wind-bin counts pooled across 2007--2025 and used as the O/E exposure table. `unit` distinguishes m/s variables from the unitless gust factor. |
| `analysis/stations.csv` | One weather station | station, name, latitude, longitude. |
| `analysis/annual_traffic.csv` | Road section and year | road section, length, ADU, SDU, and VDU. |
| `analysis/rate_model.csv` | Road section, year, traffic period, and mean-wind interval | The 24,048 rows that contain information for the conditional Poisson model: estimated vehicle-kilometres and injury-accident counts. All-zero accident strata are not retained because they contribute no information to this conditional model. |
| `analysis/traffic_rate_summary.csv` | Traffic period and mean-wind interval | 18 rows: total estimated vehicle-kilometres and observed accidents for the descriptive accident-per-vehicle-km table. |
| `analysis/selection_summary.csv` | Dataset-selection step | Eight counts used to draw the accident and traffic selection figures. |
| `analysis/daily_traffic.csv` | Counter site and date | daily count, weather-station match, daytime mean `f`, and daytime mean `fg`. |
| `analysis/daily.txt` | One counter followed by daily records | A readable, grouped view of the daily traffic file. |
| `analysis/manifest.csv` | One analysis file | record count, preparation source, and available columns. |

The primary O/E analysis uses `accidents.csv`, `weather_frequency.csv`, and
the generated `oe_station_bins.csv`; it does not use traffic. Mean wind speed
`f` is its primary exposure and maximum gust `fg` is secondary. The daily
traffic script uses `daily_traffic.csv`. The vehicle-kilometre scripts use
`rate_model.csv` and `traffic_rate_summary.csv`. Therefore the ordinary
analysis stage reads only files in `data/analysis/`, not `data/raw/` or
`data/processed/`.
