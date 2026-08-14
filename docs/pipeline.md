# Pipeline

Run commands from the project root. Raw files are never changed.

```bash
python -m src.prepare --stage prepare
python -m src.analyze
python -m src.validate
```

`src.prepare` creates local processed data. `src.analyze` creates the retained
tables and figures. `src.validate` checks the fixed primary analysis and writes
`reports/main/tables/final_analysis_validation.md`.

| Step | Script | Input | Output |
|---|---|---|---|
| Accident data | `accidents.build` | Raw accident files, road links, urban polygons | Clean accident records and rural injury subset. |
| Weather cleaning | `weather.clean` | Raw 10-minute weather | Clean weather observations and cleaning audit. |
| Annual traffic | `traffic.annual` | Annual traffic workbooks | Annual road-section traffic table. |
| Accident-weather match | `accidents.match_weather` | Accident and clean weather data | Rural injury accidents with nearest valid wind observation. |
| Wind frequency | `weather.frequency` | Clean weather and station metadata | Station-year-season wind frequencies. |
| O/E calculation | `analysis.build_oe` | Accident-weather matches and frequencies | O/E input table and sensitivity results. |
| O/E report | `analysis.report_oe` | O/E input table | Main O/E figure, short table, coverage, and audit. |
| Traffic sensitivity | `analysis.traffic_sensitivity` | Annual traffic, roads, weather, accidents | Restricted road-section sensitivity. |
| Daily traffic | `traffic.daily`, `traffic.locate_counters`, `analysis.match_daily_weather` | Optional daily PDFs, roads, clean weather | Counter-day traffic with daytime wind. |

The daily PDF workflow is optional. It is not used in the primary O/E result.

## Traffic periods

- `VDU`: December--March.
- `SDU`: June--September.
- `VHDU`: April--May and October--November; derived transparently from ADU,
  SDU, and VDU rather than published directly.
