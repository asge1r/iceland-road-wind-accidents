# Data sources

This file is the public inventory of raw inputs. The raw files themselves are
kept outside Git because they are large and may have distribution restrictions.

| Data family | Provider | Raw directory | Main contents |
|---|---|---|---|
| Accidents | Icelandic Transport Authority / national accident register | `data/raw/accidents/` | Accident, injury, vehicle and NID road-link records. |
| Weather | Icelandic Met Office | `data/raw/weather/` | Ten-minute automatic-weather-station observations. |
| Annual traffic | Icelandic Road and Coastal Administration | `data/raw/traffic/annual/` | Annual ÁDU, SDU, VDU and road-section records. |
| Daily traffic | Icelandic Road and Coastal Administration | `data/raw/traffic/daily_pdf/` | Annual PDF calendars of daily counter readings. |
| Road geography | Icelandic Road and Coastal Administration MapServer | `data/raw/traffic/` | Road-section geometry and 20 m road-station points used to locate PDF counters. |
| Urban boundaries | Statistics Iceland | `data/raw/accidents/` | Urban-area polygons used for the rural/urban classification. |

The thesis methods chapter reports the retrieval date, covered years, row count
and retained columns for every source actually used in the final analysis.
