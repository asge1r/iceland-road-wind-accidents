# Analysis rules

## Weather quality

The weather-cleaning script never imputes or clips wind values. Its rules are
fixed before analysis and are reported annually in
`data/analysis/weather_cleaning.csv`.

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

The primary mean-wind result is also recalculated with a 24-hour all-zero
threshold and with all all-zero runs retained. The generated comparison is
`reports/main/tables/zero_run_check.csv`; this raw-data check is run with
`python -m src.validation.zero_runs` and does not overwrite the main inputs.

## Weather variables used in O/E analysis

Accident-time mean wind speed (`f`) in 5 m/s intervals is the primary weather
measure. It is the ten-minute mean matched within five minutes of the accident,
not an instantaneous value. The `fg`
reported in the ten-minute observation matched to the accident time is a
secondary wind-gust measure; it is not a daily maximum.
Temperature is matched independently and compared with its local seasonal
frequency. Its narrower intervals around freezing are exploratory.

## Evidence hierarchy

The primary result is station-and-season-standardised mean-wind O/E for the
20 km, five-minute wind match. The time-stratified case-crossover model is the
first supporting analysis: each accident is compared with the other occurrences
of the same weekday and clock time in the same month and year, using the same
weather station and match limits. The conditional Poisson road-section model is
the second supporting analysis and uses estimated vehicle-kilometres. A stricter
selected-counter model uses observed daily counts. Results under 5, 10 and
20 km assignment limits are reported explicitly. Daily counters
also describe whether traffic changes with wind at selected sites. These
analyses estimate different quantities and are compared by direction, not by
the numerical size of their estimates.

Temperature, hour, daylight, matched-time wind gust, and subgroup results
answer supporting research questions. They remain exploratory or descriptive
and do not replace the primary mean-wind result.
Temperature O/E uses the intervals below −6, −6 to −3, −3 to 0, 0 to 3,
3 to 6, 6 to 9, 9 to 12, 12 to 15, and at least 15°C. The case-crossover
model uses the same categories for stability.

The joint matched-time model includes categorical mean wind and temperature
together. A separate model describes the odds that a recorded injury accident
is serious or fatal using wind, temperature, daylight, time of day, and season.
That model concerns severity among accidents and does not estimate whether an
accident occurs. The daylight comparison uses the same location, month,
weekday, and clock time; only strata whose solar-elevation class changes within
those matched dates inform the comparison. It is not a rate per vehicle.

A matched-time season comparison groups mean wind as 0--10, 10--15, and at
least 15 m/s. It adds wind-by-season interaction terms to the conditional
logistic model and compares that model with a common-wind-association model
using a six-degree-of-freedom likelihood-ratio test. This is the formal
assessment of seasonal differences; separate seasonal plots are supporting
descriptions.

## Accident sample

The prepared accident dataset retains all valid registered accidents. The
compact `data/analysis/accidents.csv` file then contains the defined thesis
population: rural injury accidents with `meidsli < 4`. Serious or fatal
accidents have `meidsli <= 2`. Damage-only accidents remain in the reproducible
prepared accident file but are not copied into the thesis analysis CSV.

## Daily traffic and wind

PDF direction/lane channels (`fastnr`) at the same road-section and `stöð` are
summed to one 24-hour counter-day total. The total is not divided into hourly
traffic. It is compared with mean wind measured from 10:00 to 21:59. This is a
daily association, not an estimate of traffic during that 12-hour window.

Daily traffic O/E is standardised within counter, year, month and weekday. SDU,
VDU and derived VHDU are retained as seasonal traffic references; they do not
replace observed daily counts.

The active pooled traffic O/E uses the arithmetic mean within each calendar
stratum. This makes expected counts sum to observed counts within a complete
stratum. Medians remain appropriate in separate counter-quality descriptions,
but are not the denominator of this pooled O/E calculation.

The sustained-wind analysis counts hours per sufficiently complete day with
`f >= 15 m/s` and compares observed traffic with the same counter, year, month,
and weekday expectation. The allocated daily-rate model assigns the observed
24-hour total to 0--10, 10--15, and at least 15 m/s in proportion to the
counter station's valid ten-minute observations. Accidents are classified by
`f` from that same station at the accident time; the station must be within
20 km of both the accident and counter, and the assigned counter must be within
20 km of the accident. Strata are counter and year.
This uses an estimated within-day traffic split, not observed hourly traffic. It is
supporting because it covers selected counters in 2019--2024 and cannot show
that an accident vehicle passed the assigned counter. The former full-day-mean
model is retained only as an appendix day-level check.

The traffic-allocation direction check applies the observed daily traffic
percentage for each full-day mean-wind interval to the corresponding annual
model rate ratio. It is explicitly illustrative: daily mean categories do not
measure traffic during individual ten-minute wind intervals, and the daily
data cover only selected counters in 2019--2024.

## Counter coordinates

In the current reproducible pipeline, a PDF `stöð` is the primary location
evidence. It is interpolated along the Road Administration's official road
geometry using the official start/end station values from MapServer/6. The
output labels this as estimated because it is an interpolation, not a supplied
counter coordinate. A site-year not covered by the official station range and
geometry remains unresolved; no midpoint is silently substituted. An
independent match to the Road Administration's 20 m road-station points is a
validation method; it does not replace a valid PDF `stöð` location.
