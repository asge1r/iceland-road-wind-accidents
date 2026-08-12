# Data sources

This file is the public inventory of raw inputs. The raw files themselves are
kept outside Git because they are large and may have distribution restrictions.

| Data family | Provider | Raw directory | Main contents |
|---|---|---|---|
| Accidents | Icelandic Transport Authority / national accident register | `data/raw/accidents/` | Accident, injury, vehicle and NID road-link records supplied for this project. |
| Weather | [Icelandic Met Office API](https://api.vedur.is/weather/observations/aws/raw/10min) | `data/raw/weather/` | Ten-minute automatic-weather-station observations. |
| Annual traffic | [Icelandic Road and Coastal Administration traffic publications](https://www.vegagerdin.is/vegakerfid/umferd-og-slys/umferd) | `data/raw/traffic/annual/` | Annual ÁDU, SDU, VDU and road-section records. |
| Daily traffic | Icelandic Road and Coastal Administration annual counter PDFs | `data/raw/traffic/daily_pdf/` | Annual PDF calendars of daily counter readings. |
| Road geography | [Road Administration MapServer](https://vegasja.vegagerdin.is/arcgis/rest/services/data/vegakerfi/MapServer) | `data/raw/traffic/reference/` | MapServer/6 road-section geometry and official start/end stations; used to interpolate PDF `stöð` positions. Counter locations and 20 m points are validation sources. |
| Urban boundaries | [Statistics Iceland WFS](https://gis.is/geoserver/Hagstofan/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=Hagstofan:thettbylisstadir&outputFormat=application/json) | `data/raw/accidents/` | Urban-area polygons used for the rural/urban classification. |

## Current source and output scope

| Dataset | Rows / files | Years | Columns retained in the canonical step |
|---|---:|---|---|
| Accident delivery | 236,494 source rows; 118,247 valid coordinate/time accident records | 2007--2024 | `nid`, timestamp, coordinates, `meidsli`, `tegohapps`, `flokkur2`, location text |
| Weather delivery | 226,580,952 ten-minute rows; 211,511,015 after wind cleaning | 2007--2024 | station, time, `f`, `fg`, `t` |
| Annual traffic output | 33,757 road-section/year rows | 2000--2025 | road section, Bst, Est, length, ÁDU, SDU, VDU, vehicle-km |
| Daily traffic output | 774,274 counter-day rows across 476 sites | 2019--2024 | date, counter site, `stöð`, road section, summed count, channels, coordinates and location method |

The standard analysis period is accidents and weather from 2007--2024, annual
traffic from 2000--2025, and observed daily traffic from 2019--2024. The
thesis methods chapter reports the retrieval date for each source.
