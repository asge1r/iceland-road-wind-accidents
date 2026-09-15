# Four-item alignment review

## 1. Historical road-section model

Removed its detailed conditional-Poisson Methods subsection, Results claim,
model-specific limitation and six appendix rows (four rate-model comparisons,
two seasonal-average exclusions). No result from that model remains cited.
Removed its unused ADU/VDU/SDU/VHDU abbreviation entries. Kept the brief Data
paragraph explaining possible full-period approximation using seasonal averages.

The former Methods text is preserved in `docs/legacy_road_section_method.md`;
all analysis code and numerical CSVs remain unchanged. The separate allocated
daily-counter model and two zero-counter-day sensitivity rows remain because
they still support cited results. The table generator now explicitly selects
those daily-traffic rows instead of bringing the road-section rows back.

## 2. Wind cleaning table

Table 3.5 now says “Cleaning-rule shares”. The alternative-source branch uses
“Rows assessed for wind cleaning”. No occurrence of quality remains in the
rendered table. No rule, denominator or number changed.

## 3. Temperature display notation

The supervisor source `c90f735:src/figures/weather_rate.py`, linked to the README
rate figures, formats finite temperature intervals as `[−6, −3]`, `[−3, 0]`,
`[0, 3]`, etc., with a comma followed by a space. The open tails are `<−6`
and `≥12` (the descriptive figure retains its existing ≥15 tail).

The O/E formatter previously omitted the space: `[−6,−3]`. It now matches the
supervisor format. Regenerated the temperature O/E seasonal figure, both
period O/E figures and the corrected counter-period figure. Checked the
remaining temperature axes: descriptive conditions, traffic response, and
same-day annual/seasonal rates already use the matching formatter. Monthly
main rate figures do not contain temperature axes. Numerical bin membership
and the explanatory lower-inclusive/upper-exclusive convention are unchanged.

## 4. Source inventory and unresolved target

Traffic and Roads are combined in Table 3.1 because both come from IRCA and
form the same traffic/road source family. Coverage distinguishes the units:

| Quantity | Canonical source | Verified count |
|---|---|---:|
| Mapped road-section geometries, unique IDKAFLI | `data/raw/traffic/reference/roads.geojson` | 1,226 |
| Rows containing seasonal traffic averages (section-years, 2000–2025) | `data/processed/traffic/annual.csv` | 33,757 |
| Distinct historical traffic section identifiers, 2000–2025 | Same, unique road_section | 1,741 |
| Distinct traffic section identifiers, 2007–2025 | Same, restricted years | 1,722 |
| Daily directional channel records | `data/processed/traffic/daily_raw.csv`, sum directional_channels | 1,033,659 |
| Aggregated daily site records | Same, row count | 774,274 |

Thus 1,226 counts the mapped inventory, not historical traffic section
identifiers, section-years, directional channels, or accident-to-road links.
The table retains 1,226, now explicitly labelled “mapped road sections”, and
labels the 33,757 observations as section-year records of seasonal averages.

The supplied supervisor instruction gives the road-section count only as
“xx,xxx road sections” (attachment `2b07ac29-74f7-4b21-9874-5c49edb20cd4`,
line 131). No exact alternative count is supplied there. Its intended numerical
target therefore remains unresolved; none was invented or substituted.

The geometry downloader (`src/traffic/download_roads.py`) reads MapServer layer 6
with `where=1=1`, pagination and a final source-count check; the cached count
is not inferred from the first page of results.

## Validation

79 tests passed, 1 skipped, 18 subtests passed. `git diff --check` passed.
Final two real compilation passes succeeded: 67 pages, no undefined references
or citations, duplicate labels, or overfull boxes. Ten nonblocking underfull
spacing warnings remain. All figures and tables retain prose references.
All 75 scientific CSVs match pre-review hashes. No commit or push.
