# Variable Definitions

## Weather

- `station`: Icelandic Meteorological Office station number.
- `time`: timestamp of a 10-minute observation.
- `f`: mean wind speed during the observation interval, in metres per second.
- `fg`: maximum wind gust, in metres per second.
- `t`: air temperature, in degrees Celsius.
- `weather_station_dist_km`: straight-line distance between the accident and
  the selected weather station.
- `weather_time_difference_minutes`: absolute time difference between the
  accident and selected observation. Observations are on a 10-minute grid, so
  the selected adjacent observation is at most five minutes away.

Clean wind observations satisfy `0 <= f <= 50`, `0 <= fg <= 75`, and
`fg + 0.5 >= f`. Rows missing `f` or `fg` are excluded from the clean weather
file. Missing temperature does not invalidate an otherwise usable wind row.

## Traffic

- `ADU`: annual average daily traffic.
- `SDU`: average daily traffic in June, July, August, and September.
- `VDU`: average daily traffic from December through March.
- `traffic_volume`: observed vehicles at one physical counter site on one date,
  after available lane/direction channels have been summed.
- `counter_site_id`: physical daily-count site identifier, constructed from
  road section and PDF station ID.
- `source_fastnr`: pipe-separated source channel identifiers contributing to
  the counter-day total.
- `directional_channels`: number of source lane/direction channels summed.
- `location_method`: states whether coordinates are an official single/name
  match, interpolated from the PDF road station, an estimated road-section
  midpoint, or unavailable.
- `location_is_estimated`: true when coordinates are interpolated from a PDF
  road station or are a road-section midpoint rather than an accepted official
  counter coordinate.
- `location_station_range_valid`: true when the PDF `stöð` lies inside the
  Bst/Est interval for the same road section and year in the annual traffic
  workbook.
- `location_station_start_m`, `location_station_end_m`: the year-specific
  Bst and Est bounds, converted to metres.
- `location_station_fraction`: the PDF station's fractional position between
  Bst and Est. It is used to interpolate a point along the road geometry.
- `location_max_offset_along_road_km`: maximum possible distance in kilometres along the
  registered road section between its length-weighted midpoint and an
  unknown counter location. It is half the computed path length for midpoint
  locations, zero for official locations, and not applicable to station-
  interpolated locations.
- `location_max_offset_straight_line_m`: maximum straight-line distance from
  the midpoint to any vertex of the registered road geometry. This is a
  spatial-location uncertainty bound, not the distance to the true counter.
- `road_section`: registered Vegagerdin road-section identifier, such as
  `1-a1`.

ADU, SDU, and VDU are annual or seasonal averages, not observed traffic on an
accident day. Daily PDF traffic is analysed separately because counter coverage
is incomplete and multiple counters can occur on one road section.

### Daily traffic wind-response analysis

- `traffic_period`: `VDU` for December--March, `SDU` for June--September, and
  `VHDU` (spring/autumn daily traffic) for April--May and October--November.
- `estimated_daytime_traffic`: 95% of the recorded 24-hour traffic total. This
  is an explicit approximation so that the daily count can be compared with
  daytime mean wind (10:00--21:59).
- `baseline_mean_daily_traffic`: mean recorded traffic for the same physical
  counter, calendar year, month, and weekday.
- `expected_daytime_traffic`: 95% of `baseline_mean_daily_traffic`.
- `daily_traffic_oe`: estimated daytime traffic divided by expected daytime
  traffic for one counter-day.
- `f_bin`: 3 m/s daytime-mean-wind interval from `0-3` through `30-33` m/s
  in the analysis panel. The main thesis display combines `24-27`, `27-30`,
  and `30-33` into `>=24` m/s; detailed bins are retained as a sensitivity
  output under `reports/working/`.
- `annual_period_daily_traffic`: VDU or SDU where official values are
  available; for `VHDU`, the day-weighted residual derived from ADU, SDU, and
  VDU. It is a reference and is not substituted for observed daily counts.

## Accident And Road Context

- `nid`: accident identifier.
- `meidsli`: original injury-severity code.
- `severity_label`: readable severity category.
- `tegohapps`: accident-type code; meanings are documented in the original
  accident codebook under `data/raw/accidents/`.
- `urban_rural`: spatial classification derived from Statistics Iceland urban
  boundaries, with the documented Westman Islands rule.
- `registered_road_section`: matched registered road section.
- `registered_road_number`: road number taken from the registered section.
- `surface_code_1` to `surface_code_4`: recorded road-surface codes. The source
  source history is retained under `data/raw/traffic/reference/`.

The same Statistics Iceland 2020-2024 urban boundaries are used for accidents
from every study year. Earlier classifications therefore do not reflect urban
expansion through time.
