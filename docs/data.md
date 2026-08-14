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

## Canonical local files

| File | Unit | Key columns used |
|---|---|---|
| `processed/accidents/rural_injury_accidents.parquet` | One rural injury accident | `nid`, time, coordinates, injury code, accident type, road section, station, distance, `f`, `fg`. |
| `processed/weather/weather_10min_clean.parquet` | One station and 10-minute time | station, time, `f`, `fg`, `t`. |
| `processed/weather/stations.csv` | One weather station | station, name, latitude, longitude, start, end. |
| `processed/weather/wind_frequency_station_year_season.parquet` | Station, year, season, and wind interval | wind frequency denominator for O/E. |
| `processed/traffic/annual_road_section_exposure.csv` | Road section and year | road section, length, ADU, SDU, VDU, vehicle-kilometres. |
| `processed/traffic/daily_traffic_weather.parquet` | Counter site and date | count, coordinates, location method, matched station, distance, daytime `f` and `fg`. |

The primary O/E analysis uses the first four files and does not use traffic.
Annual traffic is used for the restricted road-section sensitivity. Daily PDF
traffic is a separate 2019--2024 travel-demand diagnostic.
