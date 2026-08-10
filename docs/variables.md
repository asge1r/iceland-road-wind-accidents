# Canonical processed datasets

| Dataset | Unit | Essential fields |
|---|---|---|
| `accidents/all_accidents_enriched.parquet` | one accident | `nid`, `timestamp`, coordinates, `meidsli`, accident type, road section, rural/urban status |
| `accidents/rural_injury_accidents_base.parquet` | one rural injury accident | Pre-weather subset created from the canonical accident table. |
| `accidents/rural_injury_accidents.parquet` | one rural injury accident | Canonical analysis input: accident fields plus matched weather station, time difference, distance, `f`, `fg`, `t` |
| `weather/weather_10min_clean.parquet` | one station and ten-minute timestamp | `station`, `time`, `f`, `fg`, `t` |
| `traffic/annual_road_section_exposure.csv` | one road section and year | road section, Bst, Est, length, ÁDU, SDU, VDU |
| `traffic/daily_traffic.parquet` | one physical counter and date | counter site, road section, `stöð`, summed traffic, coordinates, location method and uncertainty |
| `traffic/daily_traffic_weather.parquet` | one physical counter and date | daily traffic fields plus daytime weather station, distance and mean wind |
| `traffic/daily_traffic_wind_response.parquet` | one wind bin and analysis stratum | observed and expected traffic, O/E and confidence interval |
