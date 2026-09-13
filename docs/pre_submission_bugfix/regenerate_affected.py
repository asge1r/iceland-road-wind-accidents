"""Regenerate A1–A3 products and their thesis edits; never merge branches.

Run from the repository root with --apply. The default is a usage error so merely
inspecting the helper cannot overwrite live products. A timestamped backup is
made before writing, including the ignored prepared products being replaced.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def run(module):
    print('RUN', module, flush=True)
    subprocess.run([sys.executable, '-m', module], cwd=ROOT, check=True)


def regenerate():
    # Backup only output locations this operation can change; never copy raw weather.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = ROOT / 'reports/reproduced' / ('affected_backup_' + stamp)
    outputs = ['data/analysis', 'reports/main', 'reports/thesis']
    outputs += ['data/processed/weather/' + n for n in [
        'frequency.csv', 'yearly_frequency.csv', 'traffic_frequency.csv', 'temperature_frequency.csv']]
    outputs += ['data/processed/accidents/case_control.csv']
    outputs += ['data/processed/traffic/' + n for n in [
        'counter_day_weather.parquet', 'counter_accidents.csv', 'daily_vkt.csv']]
    for name in outputs:
        src = ROOT / name
        dst = backup / name
        if src.is_dir():
            shutil.copytree(src, dst)
        elif src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print('BACKUP', backup, flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(run, ['src.weather.frequency', 'src.accidents.case_control',
                            'src.traffic.counter_day_weather']))
    run('src.traffic.counter_accidents')
    run('src.traffic.daily_vkt')
    from src import exports_weather as weather
    from src.exports_accidents import export_case_control
    from src.exports_counters import export_daily_vkt
    from src.exports_traffic import export_temperature_rate_input
    analysis = ROOT / 'data/analysis'
    for exporter in [weather.export_frequency, weather.export_yearly_frequency,
                     weather.export_temperature_frequency, export_case_control,
                     export_temperature_rate_input, export_daily_vkt]:
        exporter(analysis)
    import pandas as pd
    from src.export_docs import register_manifest_file
    manifest = pd.read_csv(analysis / 'manifest.csv').set_index('file')
    for name in ['weather_frequency.csv', 'weather_yearly.csv', 'temperature_frequency.csv',
                 'case_control.csv', 'road_temperature.csv', 'daily_vkt.csv']:
        register_manifest_file(analysis, name, manifest.loc[name, 'description'])
    for module in ['src.analysis.oe_analysis', 'src.tables.oe_audit', 'src.tables.year_oe',
                   'src.tables.case_control', 'src.tables.weather_model', 'src.tables.temp_rate']:
        run(module)
    # Render into staging; preserve byte-identical figures and LaTeX tables.
    with tempfile.TemporaryDirectory() as directory:
        staging = Path(directory)
        for module, option in [('src.figures.oe_histo', '--output-directory'),
                               ('src.figures.weather_rate', '--output'),
                               ('src.tables.thesis', '--output')]:
            subprocess.run([sys.executable, '-m', module, option, str(staging)],
                           cwd=ROOT, check=True)
        subprocess.run([sys.executable, '-m', 'src.figures.temp_rate', '--output',
                        str(staging / 'temperature_rate.png')], cwd=ROOT, check=True)
        for path in staging.iterdir():
            target = ROOT / ('reports/thesis/generated' if path.suffix == '.tex'
                             else 'reports/main/figures') / path.name
            if not target.exists() or path.read_bytes() != target.read_bytes():
                shutil.copy2(path, target)
    content = ROOT / 'reports/thesis/content.tex'
    text = content.read_text()
    replacements = [
        ('1,137.0 expected; O/E 0.71)', '1,137.1 expected; O/E 0.71)'),
        ('temperature strata with 21,144', 'temperature strata with 21,139'),
        ('At least 92 of the expected 102\nobservations are required.',
         'At least 92 distinct occupied ten-minute slots out of the expected 102\nare required.'),
        ('and temperature are handled in the same way as mean wind. Temperature is\nmatched independently,',
         'and temperature are handled in the same way as mean wind. Temperature\n'
         'cases and background frequencies both require valid values from $-30$ to\n'
         '$30\\,^{\\circ}\\mathrm{C}$, inclusive. Temperature is matched independently,'),
    ]
    for old, new in replacements:
        if old in text:
            assert text.count(old) == 1, old
            text = text.replace(old, new)
        elif new not in text:
            raise ValueError('Thesis wording changed; inspect before applying: ' + old)
    if text != content.read_text():
        content.write_text(text)
    run('src.validate')
    job = 'Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland'
    for pass_number in [1, 2]:
        with (backup / f'thesis_pass_{pass_number}.log').open('w') as log:
            subprocess.run(['/Library/TeX/texbin/pdflatex', '-interaction=nonstopmode',
                            '-halt-on-error', '-jobname=' + job, 'draft_en.tex'],
                           cwd=ROOT / 'reports/thesis', stdout=log,
                           stderr=subprocess.STDOUT, check=True)
    print('DONE; thesis compiled twice; backup:', backup, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    if Path.cwd().resolve() != ROOT:
        raise SystemExit('Run from the repository root.')
    regenerate()
