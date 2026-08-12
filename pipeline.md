# Pipeline

There are two deliberately separate commands. Neither alters `data/raw/`.

```text
authorised raw data -> src/prepare/ -> local processed caches -> data/analysis/
data/analysis/       -> src/analysis/ -> reports/main/
```

## A. Rebuild the analysis inputs locally

Run only when the authorised raw data are available:

```bash
python -m src.run_prepare --stage prepare
```

| Step | Program | Main output | Why it exists |
|---|---|---|---|
| Accident preparation | `prepare.accidents.prepare_accidents` | accident cache | Standardise source accidents; attach road and rural/urban information. |
| Weather cleaning | `prepare.weather.clean_weather` | weather cache | Exclude wind spikes and frozen zero runs. |
| Annual traffic | `prepare.traffic.prepare_annual_traffic` | annual traffic cache | Standardise ÁDU, SDU and VDU. |
| Daily traffic and locations | `prepare.traffic.*` | daily traffic cache | Extract PDFs and locate PDF `stöð` on official geometry. |
| Daily weather matching | `prepare.match_daily_traffic_weather` | daily traffic/weather cache | Pair each counter-day with daytime weather. |
| Accident/weather matching | `prepare.accidents.match_accidents_weather` | injury accident cache | Attach the nearest valid 10-minute wind observation. |
| Wind-frequency aggregation | `prepare.weather.build_wind_frequency` | frequency cache | Aggregate 10-minute weather by station, year, season and wind bin. |
| Analysis export | `prepare.export_analysis_data` | `data/analysis/*.csv` | Create the five small versioned analysis inputs. |

## B. Produce results from a clone

```bash
python -m src.run_analysis
```

| Program | Reads from `data/analysis/` | Produces |
|---|---|---|
| `analysis.calculate_wind_risk` | accidents; weather-station frequency | O/E calculation cache. |
| `analysis.create_wind_risk_report` | accidents; O/E cache | gust O/E table, bootstrap intervals and figure. |
| `analysis.render_daily_wind` | daily counter wind | daily traffic O/E table and figure. |
| `analysis.render_road_wind` | road wind | traffic-adjustment figure. |

`annual_traffic.csv` is retained as the compact published traffic context and
is the input used when `road_wind.csv` is rebuilt in preparation. The four
result programs do not read raw data or `data/processed/`.

## Daily-counter location rule

Daily PDF `stöð` is treated as a metre station along the reported road section.
Preparation accepts it only inside the official start/end station range and
interpolates the point along registered geometry. Official 20 m road-station
points provide an independent validation; they never overwrite a valid PDF
`stöð` location.
