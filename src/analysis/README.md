# Analysis code

These are the only scripts used after cloning to recreate reported results:

```bash
python -m src.run_analysis
```

They read only the five CSV files in `data/analysis/`. They write tables and
figures under `reports/`, and one local calculation cache under `data/cache/`.

- `calculate_wind_risk.py`: station/year/season frequency-standardized O/E.
- `create_wind_risk_report.py`: clustered bootstrap intervals and gust O/E figure.
- `render_daily_wind.py`: daily traffic O/E and counter-cluster bootstrap.
- `render_road_wind.py`: traffic-adjusted road-wind sensitivity figure.
