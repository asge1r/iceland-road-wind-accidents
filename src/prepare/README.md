# Preparation code

These programs run only when authorised raw data are available locally. They
never alter `data/raw/`. Their job is to clean, match and aggregate raw inputs
into local caches, then run `export_analysis_data.py` to write the five small
versioned files in `data/analysis/`.

Run the whole preparation sequence with:

```bash
python -m src.run_prepare --stage prepare
```

The only large component is `match_daily_traffic_weather.py`: it matches every
daily counter-day to 10-minute weather before aggregation. It is deliberately
kept outside `src/analysis/`; the regular result workflow never reads it or its
large output.
