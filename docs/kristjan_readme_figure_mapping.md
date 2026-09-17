# Kristján README figure mapping — 16 September 2026

The actual source specification is `reports/main/figures/README.md`. All eleven
listed images remain in the thesis. No historical bitmap was substituted for
current results. PNG previews retain the README paths; the thesis now embeds their vector PDF counterparts.
Numbers below follow the revised thesis: splitting the coverage figure and
moving period checks to Appendix A.3 changes their numbering.

## Latest clarity-pass override — 16 September 2026

The final clarity instruction supersedes the recovered y-axis limits listed
in the historical comparison below: O/E and VKT panels now use independent,
rounded zero-based limits with approximately 75–85% tallest-bar occupancy.
Scientific values, bins, seasonal aggregation and light-blue/red colours are
unchanged. The response figure retains its percentage scale. Figures 4.7 and
4.8 remain separate. See `docs/final_clarity_figure_efficiency_audit.md` for
validation and the monthly/same-day wording changes.

## Figure-by-figure comparison

“Same” compares the scientific construction with the README specification and
its generating code, not an old bitmap's numerical values. The latest explicit
comment overrides the old seasonal layout. Blue/red denote disjoint minor
injury / serious or fatal injury throughout O/E and rate plots.

| README figure | Current thesis figure | Same scientific quantity? | Same denominator? | Same bins? | Same season layout? | Same y-axis? | Same colours? | Action required / implemented |
|---|---|---|---|---|---|---|---|---|
| `weather_oe_2007_2018.png` | A.3 | Yes, period O/E | Yes, period station-season weather frequency | Yes | Yes, All year × three parameters | Retained recovered automatic limits | Light blue/red | Kept in the period-sensitivity appendix |
| `weather_oe_2019_2024.png` | A.4 | Yes, period O/E | Yes, period station-season weather frequency | Yes | Yes, All year × three parameters | Retained recovered automatic limits | Light blue/red | Kept in the period-sensitivity appendix |
| `traffic_weather_response.png` | 4.6 | Yes, observed/expected daily traffic | Yes, counter-section/year/month/weekday expected traffic | Yes | Yes, All year × three parameters | Retained 0–120% | Original response blue | Kept before correction; percentage labels retain one decimal |
| `weather_oe_traffic_corrected_2019_2024.png` | A.5 | Yes, counter-era corrected O/E | Yes, traffic-reweighted period weather frequency | Yes | Yes, All year × three parameters | Retained 6 / 6 / 2 | Light blue/red | Kept in the period-sensitivity appendix |
| `weather_rate_annual.png` | 4.13 | Yes, same-day traffic rates | Yes, same-day covered exposure, not monthly exposure | Yes, fine bins | Yes, All year × three parameters | Retained 1.3 / 1.3 / 0.3 | Light blue/red | Kept and explicitly identified as sensitivity |
| `f_traffic_rate_panels.png` | 4.14 | Yes, same-day wind rates | Yes | Seasonal ≥15 tail retained; All year fine bins added | Updated: centred All year above four seasons | All year 1.3; seasons 0.8 retained | Light blue/red | Regenerated presentation only |
| `fg_traffic_rate_panels.png` | 4.15 | Yes, same-day gust rates | Yes | Seasonal ≥20 tail retained; All year fine bins added | Updated as requested | All year 1.3; seasons 0.5 retained | Light blue/red | Regenerated presentation only |
| `temperature_traffic_rate_panels.png` | 4.16 | Yes, same-day temperature rates | Yes | Yes; bracketed display | Updated as requested | All year 0.3; seasonal automatic limits now independent | Light blue/red | Regenerated presentation; no common seasonal axis imposed |
| `wind_oe_panels.png` | 4.3 | Yes, weather-only O/E | Yes, pooled station-season weather frequency | Yes, five wind bins | Updated as requested | Existing panel-specific readability limits retained | Light blue/red | Centred wider All year, four seasons below |
| `gust_oe_panels.png` | 4.4 | Yes, weather-only O/E | Yes | Yes, seven gust bins | Updated as requested | Existing panel-specific limits retained | Light blue/red | Same layout update |
| `temperature_oe_panels.png` | 4.5 | Yes, weather-only O/E | Yes | Yes, eight temperature bins | Updated as requested | Existing panel-specific limits retained | Light blue/red | Same layout update; bracket convention explained |

## Source data and method checks

- **Weather-only and period O/E:** `src/figures/oe_histo.py` reads
  `reports/main/tables/weather_oe.csv`, `weather_oe_2007_2018.csv` and
  `weather_oe_2019_2024.csv`. Numerator: qualifying rural injury accidents in
  each interval, station and season. Denominator: accident-group totals weighted
  by background weather proportions at the same station and season. Full-period
  data cover 2007–2025; period figures restrict accidents and background to the
  named period. `disjoint_outcomes()` subtracts serious/fatal counts and expected
  counts from all-injury counts before dividing, never subtracting O/E ratios.
- **Corrected O/E:** `src/figures/traffic_corrected_oe.py` reads
  `reports/main/tables/weather_oe_traffic_corrected_2019_2024.csv` for the README
  figure. Accident numerator unchanged; expected counts use traffic-reweighted
  weather frequency. The full-period correction remains a separate main result.
- **Traffic response:** `src/figures/traffic_weather_response.py` reads
  `data/analysis/traffic_weather_response.csv`. Numerator is allocated
  observed daily traffic; denominator is allocated calendar-expected traffic.
  Positive daily counts, 2019–2024, are allocated by observed daytime weather.
  This is a percentage comparison, not an injury-severity plot.
- **Same-day rates:** `src/figures/weather_rate.py` reads
  `data/analysis/daily_vkt.csv`. Accident bins use actual event-time weather in
  the 694-accident eligible sample, 2019–2024. Exposure sums daily traffic ×
  rural road length × observed bin minutes / 1,020. Missing weather time does
  not contribute exposure. Both injury groups share exposure. Seasonal tails
  sum counts and exposure before division; annual bins are left untouched.
- **Main monthly rates (additional, not in the README):**
  `src/figures/monthly_vkt_rate.py`, `src/tables/monthly_vkt_rate.py`,
  `data/analysis/monthly_vkt.csv`, `data/analysis/monthly_vkt_section.csv` and
  `data/processed/traffic/counter_accidents.csv`. Numerator: the same eligible
  694 accidents classified by event-time weather. Denominator: daily traffic ×
  rural road length × pooled 2007–2025 station-month daytime weather frequency.
  Every eligible recorded day contributes, including accident-free days;
  533,649 counter-section days and 5,630,267,210 estimated vehicle-km remain
  unchanged. Figures 4.10–4.12 use the supervisor's rate renderer and palette;
  4.11–4.12 receive the new five-panel layout. A same-day bitmap was not used
  to illustrate the monthly denominator.

## Common display and sample conventions

- Study seasons remain winter December–March, spring April–May, summer
  June–September and autumn October–November. Internal Fall values are unchanged.
- Mean wind bins: 0–5, 5–10, 10–15, 15–20, ≥20 m/s; gust adds 20–25,
  25–30, ≥30. Seasonal rate tails alone combine to ≥15 / ≥20 respectively.
- Analytical temperature bins: <−6, −6 to −3, −3 to 0, 0 to 3, 3 to 6,
  6 to 9, 9 to 12, ≥12 °C. Square brackets display endpoints; the text
  explicitly defines lower-inclusive, upper-exclusive finite bins.
- O/E uses grouped bars; rates use stacked components sharing exposure.
  Positive counts remain; zeros have no count label. Plot titles identify
  parameters or seasons, and pooled panels say exactly “All year”.
- Severity colours are `#79BCE0` and `#D62728`; response blue is `#4C9ED9`.
  The original-versus-corrected main plots retain their separate outline/teal
  comparison semantics because those bars represent methods, not injury groups.
- `src/figures/season_layout.py` uses a centred six-unit top panel above
  four-unit seasonal panels (nominal width ratio 1.5), with independent axes.
  Constrained layout accommodates tick labels and the legend.

## Historical provenance and limits

Earlier supervisor-authored figures and their source commits were traced in
`docs/kristjan_source_of_truth_mapping.md` and
`docs/kristjan_figure_method_comparison_audit.md`. Some historical images used an
older accident delivery. Those old numbers are not interchangeable with the
validated current delivery. This pass preserves current scientific CSV files
and implements the latest explicit layout instruction on top of the recovered
styles. All eleven README figures were visually inspected in the revised set.
