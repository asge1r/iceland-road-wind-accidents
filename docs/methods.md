# Canonical analysis rules

## Weather quality

The weather-cleaning script never imputes or clips wind values. Its rules are
fixed before analysis and are reported annually in
`archive/generated_diagnostics/weather_cleaning_by_year.csv`.

| Condition | Treatment | Audit category |
|---|---|---|
| Both `f` and `fg` are unavailable throughout a station-year | Exclude from the wind-observation universe | Station-year without wind data |
| `f` or `fg` is missing within a wind-capable station-year | Exclude the record | Missing wind value |
| `f < 0` or `fg < 0` | Exclude the record | Negative wind value |
| `f >= 45 m/s` or `fg >= 65 m/s` | Exclude the record | Upper-threshold value |
| `fg = 0` and `f > 0` | Exclude the record | Inconsistent zero gust |
| `fg + 0.5 < f` | Exclude the record | Gust below mean wind |
| `f = 0` alone, or a short `f = fg = 0` run | Retain | Valid calm wind |
| `f = fg = 0` at uninterrupted 10-minute intervals for at least two hours | Exclude the full run | Frozen zero run |
| Temperature is missing or outside the temperature plausibility range | Retain the wind record; set `t` missing | Temperature not required |

The raw delivery contains station-time records from stations that do not
measure wind, for example precipitation and radiation stations. These are not
interpreted as missing wind observations from the wind-monitoring network.

## Wind variables used in O/E analysis

Mean wind speed (`f`) in 5 m/s intervals is the primary exposure. Maximum gust (`fg`) is a
secondary exposure. The gust factor is `fg / f` and is calculated only when
`f >= 3 m/s`; this avoids an unstable ratio in calm conditions. It is a
descriptive secondary analysis, not a replacement for mean wind speed.

## Accident sample

The prepared accident dataset retains all valid registered accidents. Analysis
samples are then defined explicitly: rural injury accidents have `meidsli < 4`;
serious or fatal accidents have `meidsli <= 2`. Damage-only accidents are not
deleted from the canonical data because they can be used as a comparison group.

## Daily traffic and wind

PDF direction/lane channels (`fastnr`) at the same road-section and `stöð` are
summed to one 24-hour counter-day total. The total is not divided into hourly
traffic. It is compared with mean wind measured from 10:00 to 21:59. This is a
daily association, not an estimate of traffic during that 12-hour window.

Daily traffic O/E is standardised within counter, year, month and weekday. SDU,
VDU and derived VHDU are retained as seasonal traffic references; they do not
replace observed daily counts.

## Counter coordinates

In the current reproducible pipeline, a PDF `stöð` is the primary location
evidence. It is interpolated along the Road Administration's official road
geometry using the official start/end station values from MapServer/6. The
output labels this as estimated because it is an interpolation, not a supplied
counter coordinate. The prior Bst/Est-based interpolation is retained only as
a fallback when a station is not covered by the official geometry. An
independent match to the Road Administration's 20 m road-station points is a
validation method; it does not replace a valid PDF `stöð` location.
