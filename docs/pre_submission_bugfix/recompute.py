"""Replay the approved A fixes; outputs only beneath reports/reproduced.

Run from repository root: .venv/bin/python docs/pre_submission_bugfix/recompute.py
Requires the before snapshot created for the report; never writes live products.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/reproduced/pre_submission_bugfix'
ENV = dict(os.environ, PYTHONPATH=str(ROOT), MPLCONFIGDIR='/private/tmp/bugfix_mpl')
PYTHON = str(ROOT / '.venv/bin/python')


def run(module, *args):
    print('RUN', module, *args, flush=True)
    subprocess.run([PYTHON, '-m', module, *map(str,args)], cwd=OUT, env=ENV, check=True)


def prepare_frequency():
    run('src.weather.frequency', '-i', ROOT/'data/processed/weather/weather.parquet')
    sys.path.insert(0,str(ROOT))
    from src import exports_weather
    exports_weather.ROOT = OUT/'data/processed'
    for fn in [exports_weather.export_frequency, exports_weather.export_yearly_frequency,
               exports_weather.export_temperature_frequency]:
        fn(OUT/'data/analysis')
    from src import exports_traffic
    from src.export_common import read_table
    exports_traffic.read_table = lambda path: read_table(
        OUT/path if str(path) == 'data/processed/weather/yearly_frequency.csv' else ROOT/path
    )
    exports_traffic.export_temperature_rate_input(OUT/'data/analysis')


def prepare_controls():
    run('src.accidents.case_control', '-a', ROOT/'data/processed/accidents/rural_injury.csv',
        '-w', ROOT/'data/processed/weather/weather.parquet')
    shutil.copy2(OUT/'data/processed/accidents/case_control.csv', OUT/'data/analysis/case_control.csv')


def prepare_strict():
    run('src.traffic.counter_sections', '-i', ROOT/'data/processed/traffic/daily_raw.csv',
        '-a', ROOT/'data/processed/traffic/annual.csv', '-r', ROOT/'data/raw/traffic/reference/roads.geojson',
        '-s', ROOT/'data/raw/weather/stations.csv', '-w', ROOT/'data/processed/weather/weather.parquet')
    run('src.traffic.assign_counter_sections', '-i', ROOT/'data/processed/accidents/all.csv',
        '-r', ROOT/'data/raw/traffic/reference/roads.geojson')
    run('src.traffic.counter_day_weather', '-d', ROOT/'data/processed/traffic/daily_raw.csv',
        '-w', ROOT/'data/processed/weather/weather.parquet')
    run('src.traffic.counter_accidents', '-w', ROOT/'data/processed/weather/weather.parquet')
    run('src.traffic.daily_vkt')
    shutil.copy2(OUT/'data/processed/traffic/daily_vkt.csv', OUT/'data/analysis/daily_vkt.csv')


if __name__ == '__main__':
    if not (OUT/'protected_before.json').exists():
        raise SystemExit('Create an isolated baseline snapshot before running this replay.')
    stage = sys.argv[1] if len(sys.argv)>1 else 'all'
    if stage in ['frequency','all']: prepare_frequency()
    if stage in ['controls','all']: prepare_controls()
    if stage in ['strict','all']: prepare_strict()
    if stage in ['models','all']:
        for module in ['src.analysis.oe_analysis','src.tables.oe_audit','src.tables.year_oe',
                       'src.tables.annual_coverage','src.tables.temp_rate','src.figures.temp_rate','src.tables.case_control','src.tables.weather_model',
                       'src.tables.wind_season','src.tables.severity',
                       'src.figures.oe_histo','src.figures.weather_rate']:
            run(module)
