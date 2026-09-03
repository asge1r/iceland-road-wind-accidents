# Code

Use only these three entry points for normal work:

```bash
python -m src.prepare --stage prepare
python -m src.analyze
python -m src.validate
```

- `prepare.py`: raw source data to temporary local working files and then to
  the named CSV files in `data/analysis/`.
- `analyze.py`: `data/analysis/*.csv` to the retained tables and figures.
- `validate.py`: fixed checks for the final primary O/E analysis.

The folders below contain the small steps called by the entry points:

- `accidents/`: build the accident table and attach weather.
- `weather/`: clean wind measurements and calculate local wind frequency.
- `traffic/`: read annual and optional daily traffic data.
- `analysis/`: prepare the station-season rows used by O/E.
- `figures/`: create data-flow and descriptive figures.

Every executable script has `-h` for its own inputs and outputs. `docs/pipeline.md`
describes the relationship between scripts, data, and outputs.

Only preparation scripts read source deliveries or Parquet working files.
Every script called by `src.analyze` reads `data/analysis/*.csv` or small CSV
results produced earlier in that same run. Optional source checks for daily
traffic are kept outside these entry points.
