# Code layout

The code has three intentionally separate layers.

```text
src/prepare/   raw data -> local processed caches -> data/analysis/
src/analysis/  data/analysis/ -> tables and figures
src/legacy/    earlier cache-heavy or exploratory scripts; not active
```

## For a clone

Run the complete result workflow directly from the five versioned CSV files:

```bash
.venv/bin/python -m src.run_analysis
```

`run_analysis` calls only four small scripts in `src/analysis/`. It never reads
`data/raw/` or `data/processed/`.

## When raw data are available locally

```bash
.venv/bin/python -m src.run_prepare --stage all
```

This regenerates local caches and then the five files in `data/analysis/`.
Read `src/prepare/README.md` for the raw-data steps and
`data/analysis/README.md` for the precise analysis inputs.

`src/legacy/` is deliberately outside both commands.
