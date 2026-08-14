# Code

Use only these three entry points for normal work:

```bash
python -m src.prepare --stage prepare
python -m src.analyze
python -m src.validate
```

- `prepare.py`: raw source data to local processed files.
- `analyze.py`: processed files to the retained tables and figures.
- `validate.py`: fixed checks for the final primary O/E analysis.

The folders below contain the small steps called by the entry points:

- `accidents/`: build the accident table and attach weather.
- `weather/`: clean wind measurements and calculate local wind frequency.
- `traffic/`: read annual and optional daily traffic data.
- `analysis/`: calculate O/E and supporting traffic analyses.
- `figures/`: create data-flow and descriptive figures.

Every script has `-h` for its own inputs and outputs. `docs/pipeline.md`
describes the relationship between scripts, data, and outputs.
