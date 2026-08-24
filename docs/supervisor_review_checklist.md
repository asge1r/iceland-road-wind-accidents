# Supervisor review checklist

This checklist links the agreed thesis requirements to the files that implement
them. It is intended to make review quick: the main result, the inputs and the
steps that create it can each be checked without opening large cache files.

| Review point | Implemented approach | Where to inspect |
|---|---|---|
| Main exposure | Mean wind speed (`f`) is the primary exposure, grouped into 5 m/s intervals. Maximum gust (`fg`) and gust factor (`fg/f`) are secondary. | `docs/methods.md`; `reports/main/figures/mean_wind_oe.png`; `reports/main/figures/gust_oe.png` |
| Study question | Questions ask for the size of the association, expressed as observed/expected (O/E), rather than only whether an association exists. | `reports/thesis/draft_en.tex`, Research questions |
| Accident study population | Rural accidents with injuries (`meidsli < 4`), 2007–2025. The full accident record remains available; damage-only records are not deleted. | `data/analysis/accidents.csv`; `docs/methods.md` |
| Weather quality | Wind is never clipped or imputed. Missing, negative, implausibly high, inconsistent and frozen-zero measurements are excluded and audited. Temperature is not required. | `src/weather/clean.py`; `docs/methods.md`; `reports/main/tables/weather_cleaning_audit.csv` |
| Accident-weather linkage | Each accident uses the nearest valid 10-minute observation from its assigned station; the primary limit is 20 km and five minutes. | `src/accidents/match_weather.py`; `reports/main/tables/weather_match_coverage.csv` |
| O/E denominator | Expected accidents are calculated within station and season from local 10-minute wind frequency pooled across 2007--2025. | `src/weather/frequency.py`; `src/analysis/build_oe.py`; `docs/pipeline.md` |
| Compact data for review | Routine inspection and every ordinary analysis use named CSV files in `data/analysis/`. Raw deliveries and temporary preparation files are separate. | `data/analysis/README.md`; `data/analysis/manifest.csv`; `docs/data.md` |
| Data sources and pipeline | Source websites are listed with short identifiers, followed by a one-row-per-step pipeline table. | `reports/thesis/draft_en.tex`, Tables 1–2; `docs/pipeline.md` |
| Transparent source example | The thesis shows real early rows from the accident delivery, including source field names. | `reports/thesis/draft_en.tex`, Accident register subsection |
| Readable main presentation | The primary figure uses six 5 m/s bins, sample sizes inside bars and no error-bar whiskers. | `reports/main/figures/mean_wind_oe.png` |
| Subgroup descriptions | Mean-wind and gust figures are provided for season and one versus two-or-more vehicles. | `reports/main/figures/mean_wind_by_season_oe.png`; `reports/main/figures/mean_wind_by_vehicle_group_oe.png`; corresponding gust figures |
| Traffic | The conditional rate model compares wind intervals within road section, year and traffic period. It uses a shared weather station for accident and exposure; daily counter data provide a separate allocation check. Neither replaces the primary weather-frequency denominator. | `reports/main/figures/stratified_crash_rate_ratio_by_wind.png`; `reports/main/figures/daily_traffic_by_wind.png`; `docs/pipeline.md` |
| Reproducible run | `python -m src.prepare` builds prepared inputs; `python -m src.analyze` creates tables, figures and validation. Both commands provide `-h`. | `README.md`; `docs/pipeline.md`; `src/prepare.py`; `src/analyze.py` |

## Deliberate scope limits

- Daylight and road surface are not shown as O/E subgroups. A valid O/E
  denominator would require classifying every background 10-minute weather
  observation by daylight and by actual road condition. The available road
  surface data describe road construction, not wet, icy or snowy conditions at
  the time of an accident.
- The thesis now uses the University of Iceland template structure. The local
  implementation and official source are documented in `reports/thesis/TEMPLATE.md`.
- A discussion of the plotted weather patterns with a meteorologist is an
  external expert-review step, rather than a data-processing step.
