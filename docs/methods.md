# Canonical analysis rules

## Weather quality

- Retain wind observations only when `0 <= f <= 40 m/s` and `0 <= fg <= 75 m/s`.
- Do not discard an otherwise valid wind observation because temperature is missing.
- Exclude uninterrupted runs longer than two hours where both `f` and `fg` are exactly zero.

## Accident sample

The prepared accident dataset retains all valid registered accidents. Analysis
samples are then defined explicitly: rural injury accidents have `meidsli < 4`;
serious or fatal accidents have `meidsli <= 2`. Damage-only accidents are not
deleted from the canonical data because they can be used as a comparison group.

## Daily traffic and wind

PDF direction/lane channels (`fastnr`) at the same road-section and `stöð` are
summed to one 24-hour counter-day total. The total is not divided into hourly
traffic. It is compared with mean wind measured from 10:00 to 21:59, using the
transparent assumption that this period contains 95% of daily traffic.

Daily traffic O/E is standardised within counter, year, month and weekday. SDU,
VDU and derived VHDU are retained as seasonal traffic references; they do not
replace observed daily counts.

## Counter coordinates

In the current reproducible pipeline, a PDF `stöð` is checked against the
year-specific Bst/Est range and interpolated along the recorded road geometry.
The output labels this as estimated. The planned preferred method is an
independent match to the Road Administration's official 20 m road-station
points, with this interpolation retained as a fallback and validation method.
