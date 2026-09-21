# Focused final revision

Updated `reports/defense_beamer/defense.tex` and `defense.pdf` in place.
Still **34 main slides + 12 backup slides = 46 pages**.
Build: `make -C reports/defense_beamer` (XeLaTeX, auxiliaries in `build/`).

## Seven requested changes

1. `theme.tex` now puts frame titles in an explicitly left-aligned paragraph bounded by the text width. Long titles can wrap naturally. The font and margins are retained. Renamed the former slide 16 and slide 24 as requested.
2. Swapped 15–16: allocation fraction **q first**, traffic ratio **r second**, results third. Added the labelled 102-minute illustration and the supplied explanations. The r example is now on the r slide. The fixed 1,020-minute denominator and identical allocation fractions for observed and expected daily totals remain correct. The r slide retains C/B definitions, section/day/bin indices, positive-count baseline grouping and 2019–2024 period. Updated the timing order without changing the overall 29-minute outline plus one-minute buffer.
3. Removed slide 8's text column. Enlarged the unmodified four-panel vector figure proportionally to 6.65 cm high and centred it, with only the requested short line below. Spring/Autumn stays in the original figure; its explanation remains in the notes.
4. Applied both supplied wording replacements on slide 11. Seasons, colour meanings and separate severity-specific expected counts remain unchanged.
5. Added the supplied O/E/2007–2025 subtitle on slide 29. Retained the heatmap at its previous 6.1 cm height, all labels and the sparse-cell explanation. Added the requested spoken reminder.
6. Applied the supplied final sentence on slide 31. Kept the causal limitation on slide 32.
7. Replaced slide 34 with the three supplied concise bullets, bold lead-ins and LaTeX degree symbol. No extra closing slide.

The supplied q speaking paragraph is included verbatim in `speaker_notes.md`, not on the slide. No other main slide body or backup content was changed.

## Method and preservation checks

Read `src/traffic/daily_vkt.py::summarise_traffic_response` and `src/traffic/daytime_weather.py`: both daily totals are multiplied by observed_minutes / DAYTIME_MINUTES, with DAYTIME_MINUTES = 17 × 60. No valid-time renormalisation was introduced. The 102-minute example is illustrative.

Hash checks verified **2,158 protected files** unchanged, including thesis sources/PDF, data, analysis code, original figures, presentation-specific figure assets and other presentations. The scientific pipeline and figure exporter were not run. The only main slide bodies changed are 8, 11, 15, 16, 24, 29, 31 and 34. All backup text and six seasonal figure calls are identical to the prior deck.

## Validation

Final XeLaTeX build: zero errors, warnings, overfull/underfull boxes, missing glyphs or unresolved references. Rendered the PDF, visually inspected all modified slides, and checked all 46 page titles for clipping. Figure proportions, labels, counts and scientific values are preserved. See `validation.json`.

No unresolved issue. No staging, commit or push.
