# Project rules

This is a master's thesis on mean wind speed, wind gusts, rural injury
accidents, and road traffic in Iceland, 2007–2025. Keep the project simple,
inspectable, reproducible, and suitable for a supervisor to run locally.

## Data and pipeline

- Use `/` in documentation, tables, and prose for paths, for example
  `src/tables/oe.py`. Use dotted names only in literal Python commands, for
  example `python -m src.tables.oe`.
- Preserve `data/raw/` unchanged. Preparation scripts may read raw data and
  local Parquet working files in `data/processed/`.
- `data/analysis/` is the canonical analysis layer. Its CSV files are the only
  inputs for ordinary analysis and thesis figures. Keep them small, readable,
  documented in `data/analysis/manifest.csv`, and limited to variables used.
- Parquet is allowed only where the raw ten-minute weather data or a necessary
  local preparation join is too large for CSV. Do not call it a cache in user-
  facing text. It must be reproducible from raw data.
- `src/prepare.py` is the raw-to-analysis entry point. `src/analyze.py` is the
  analysis-to-results entry point. Keep their order explicit and deterministic.
- A preparation script writes data, a table script writes tables, and a figure
  script writes figures. Do not put plotting code in `src/tables/` or
  preparation scripts. Figure scripts read completed CSV tables.
- Keep source-level quality-control helpers outside the routine analysis flow
  unless their output is a documented thesis input.

## Research definitions

- The primary result is O/E for mean wind speed `f`, using rural injury
  accidents, a 20 km weather-station radius, and a five-minute time match.
- Wind gust `fg` and gust factor `fg / f` are secondary descriptive analyses;
  they must not replace `f` as the primary exposure.
- Mean-wind intervals are 0–5, 5–10, 10–15, 15–20, 20–25, and >=25 m/s.
  Gust intervals are 0–5 through 30–35 and >=35 m/s.
- Seasons are VDU/winter (December–March), spring (April–May), SDU/summer
  (June–September), and autumn (October–November). VHDU is April–May plus
  October–November.
- Daily counter traffic is a supplementary day-level analysis. Never infer
  hourly traffic from a daily count. Its comparison day is the same counter,
  year, month, and weekday.
- Traffic-based vehicle-kilometre results are estimated exposure, not a
  complete traffic denominator. State this clearly in code outputs and thesis
  prose.

## Python scripts

- Every executable script must support `-h` and `--help`, short and long
  options, sensible default paths, and normally `-o`/`--output` for its main
  output.
- Use `matplotlib` for figures. Create English figures with readable labels,
  units on axes, informative titles, and `n=` inside or above bars where it
  aids interpretation. Do not use error-bar whiskers unless they are directly
  needed for the result.
- Prefer small, single-purpose modules and simple names. Do not retain unused
  alternative flows, duplicate outputs, or legacy diagnostics in the active
  pipeline.
- Analysis code must validate required CSV columns and fail clearly when an
  input is absent or malformed.
- Keep Python comments only when they explain a non-obvious decision.

## Working practice

- Do not alter raw data, delete material outputs, commit, or push unless the
  user explicitly asks.
- Before reporting a code change, run the relevant `-h` check, `compileall`,
  and the smallest applicable end-to-end command. Run `git diff --check`.
- Keep `docs/pipeline.md`, `data/analysis/manifest.csv`, and the thesis
  pipeline table consistent whenever active inputs, outputs, or scripts change.
- Write thesis text and all figures in professional, plain English. Explain
  work to the user in Icelandic unless they request another language.
