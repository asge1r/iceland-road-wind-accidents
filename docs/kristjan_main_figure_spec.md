> Final readability update: only baseline Figures 4.2–4.4 now use panel-specific
> zero-based scales. This replaces the three shared baseline limits below.
> All final panel values, old→new limits and ratios are in
> [the axis audit](figure_axis_readability_audit.md). Other recovered rate limits
> remain unchanged. Colour changes are in [the palette audit](figure_color_semantics_audit.md).

# Main figure specification — final method alignment

## Authority

The main traffic-rate science is monthly-frequency allocation, explicitly
confirmed by the latest user instructions. Rate layout, spacing, stacking,
seasonal binning and scale settings are recovered from `weather_rate.py` in
Kristján-authored commit `c90f735`, originating in `bfd799f`. They are ported to
unchanged monthly data. No monthly temperature result is invented.

All y minima are zero. Light blue #79BCE0 means minor injury (code 3); red
#D62728 means serious or fatal injury (codes 1–2). Rate stacks share exposure.
Black positive counts sit inside blue and above red; zero counts are unlabelled.
Panels use All year, Winter, Spring, Summer, Autumn; the calendar definitions
are Dec–Mar, Apr–May, Jun–Sep, Oct–Nov. Rate axes have no ratio reference line.

| Figure | Parameter / panels | y min–max | Source / status |
|---|---|---|---|
| 4.2 | Baseline wind; All year + four seasons | 0–8.6738466329 | Original O/E rule max(1.5,1.18×largest group O/E) on validated data; shared within parameter |
| 4.3 | Baseline gust; All year + four seasons | 0–14.3574954971 | Same original rule; no cross-parameter harmonisation |
| 4.4 | Baseline temperature; All year + four seasons | 0–2.5752950343 | Same original rule |
| 4.5 | Traffic response; three parameters, All year | 0–120% | c90f735 source rule; 100% reference |
| 4.6 | Original/corrected wind; All year | 0–3.6639563315 | Later comparison addition: 1.35×largest displayed O/E; not attributed to Kristján |
| 4.7 | Original/corrected gust; All year | 0–5.6634592659 | Same later comparison rule |
| 4.8 | Corrected wind/gust injury groups; All year | 0–5.2692200678 | Later full-period extension; grouped, O/E=1 reference |
| 4.9 | Original 2007–2018; three parameters, All year | 0–4.0524999516 | Original shared-within-figure O/E rule on validated data |
| 4.10 | Original 2019–2024; three parameters, All year | 0–4.9436401482 | Same original rule |
| 4.11 | Corrected counter-era wind/gust/temperature; All year | 0–6 / 0–6 / 0–2 | Manual c90f735 limits; tick steps 1 / 1 / .2 |
| 4.12 | Monthly wind/gust; All year, two vertical panels | 0–1.3 / 0–1.3 | Source rate ANNUAL_Y_MAX; ticks .1; separate axes |
| 4.13 | Monthly wind; four seasons, 2×2 | 0–0.8 in each panel | Source rate SEASONAL_Y_MAX; ticks .1 |
| 4.14 | Monthly gust; four seasons, 2×2 | 0–0.5 in each panel | Source rate SEASONAL_Y_MAX; ticks .1 |
| 4.15 | Same-day sensitivity; wind/gust/temperature, All year | 0–1.3 / 0–1.3 / 0–0.3 | Original annual settings; temperature ticks .05 |
| 4.16 | Same-day wind sensitivity; four seasons | 0–0.8 | Original seasonal wind setting |
| 4.17 | Same-day gust sensitivity; four seasons | 0–0.5 | Original seasonal gust setting |
| 4.18 | Same-day temperature sensitivity; four seasons | 0–0.6 | Source temperature-only automatic rule ceil(1.2×max stack/.1)×.1 |

O/E injury bars are grouped, not stacked; their group-specific expected counts
are different denominators. They retain the O/E=1 line. The original/corrected
all-injury method comparisons use neutral grey rather than severity colours.

## Rate bins and source dimensions

All year wind: 0–5, 5–10, 10–15, 15–20, ≥20 m/s. Gust: five-unit bins through
25–30 then ≥30. Seasonal wind combines ≥15; seasonal gust combines ≥20.
Counts and exposure are summed before division, never rates averaged.
Annual source panel size is 10.2×4 inches per row; seasonal figure 14.5×9.5
inches. Four seasonal axes share only the parameter-specific seasonal range.
The monthly annual figure omits temperature, giving two original-sized rows.

## Historical O/E discrepancy

Kristján's saved older O/E images use a different input snapshot (6,192 versus
validated 6,259 accidents). The latest instruction explicitly preserves the
validated numbers. Their saved automatic y maxima are consequently not imposed
on the current data. The original automatic rule is preserved, while manual
rate and corrected-period settings are retained exactly. See the source mapping
for the recorded historical discrepancy. This is not a new scientific change.
