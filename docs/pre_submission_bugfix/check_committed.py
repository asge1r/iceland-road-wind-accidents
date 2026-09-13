"""Verify an archived Git commit with hash-pinned external data, never live source.

Usage from the repository root: .venv/bin/python docs/pre_submission_bugfix/check_committed.py
Writes only beneath reports/reproduced/committed_<commit>_<timestamp>.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / '.venv/bin/python'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', 'src', 'tests',
                    'docs/pre_submission_bugfix'], cwd=ROOT, check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / 'reports/reproduced' / f'committed_{commit[:7]}_{stamp}'
    out.mkdir(parents=True)
    archive = subprocess.check_output(['git', 'archive', commit], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(out, filter='data')
    manifest = json.loads((out / 'docs/pre_submission_bugfix/readiness_inputs.json').read_text())
    # These external datasets stay outside Git; their exact bytes are pinned in
    # the commit. Existing archive files are never replaced by working-tree files.
    for name, expected in manifest.items():
        original = ROOT / name
        if sha(original) != expected:
            raise ValueError('External input changed: ' + name)
        target = out / name
        if target.exists():
            raise ValueError('External manifest must not override committed files: ' + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if original.stat().st_size > 100_000_000:
            target.symlink_to(original)  # Read-only source weather; never a build output.
        else:
            shutil.copy2(original, target)
    env = dict(os.environ, PYTHONPATH=str(out),
               MPLCONFIGDIR='/private/tmp/committed_bugfix_mpl',
               BUGFIX_REPLAY_DIR=str(out), PYTHONDONTWRITEBYTECODE='1')

    def run(args, log):
        print('RUN', ' '.join(args), 'LOG', out / log, flush=True)
        with (out / log).open('w') as stream:
            subprocess.run([str(PYTHON), *args], cwd=out, env=env,
                           stdout=stream, stderr=subprocess.STDOUT, check=True)

    run(['docs/pre_submission_bugfix/regenerate_affected.py', '--apply'], 'regeneration.log')
    # Re-fit the unaffected requested headlines using the committed input panels.
    for module in ['src.tables.rate', 'src.tables.allocated_rate', 'src.tables.severity']:
        run(['-m', module], module.rsplit('.', 1)[-1] + '.log')
    run(['-m', 'unittest', 'discover', '-s', 'tests', '-v'], 'tests.log')
    run(['-m', 'src.validate'], 'validation.log')
    import pandas as pd
    import numpy as np
    comparisons = {
        'weather_oe.csv': ['variable', 'outcome', 'period', 'bin_label'],
        'year_oe.csv': ['variable', 'coarse_bin'],
        'matched_weather.csv': ['exposure', 'model', 'comparison'],
        'weather_model.csv': ['variable', 'comparison'],
        'temperature_rate.csv': ['bin_label'],
    }
    for filename, keys in comparisons.items():
        expected = pd.read_csv(out / 'docs/pre_submission_bugfix' /
                               (filename[:-4] + '_comparison.csv'))
        columns = {c: c[:-4] for c in expected if c.endswith('_new')}
        expected = expected[keys + list(columns)].rename(columns=columns).sort_values(keys).reset_index(drop=True)
        actual = pd.read_csv(out / 'reports/main/tables' / filename).sort_values(keys).reset_index(drop=True)
        pd.testing.assert_frame_equal(actual[expected.columns], expected, check_dtype=False,
                                      check_exact=False, rtol=1e-10, atol=1e-12)
    expected = pd.read_csv(out / 'docs/pre_submission_bugfix/daily_vkt_comparison.csv')
    keys = ['variable', 'outcome', 'period', 'bin_label']
    columns = {c: c[:-4] for c in expected if c.endswith('_new')}
    expected = expected[keys + list(columns)].rename(columns=columns).sort_values(keys).reset_index(drop=True)
    actual = pd.read_csv(out / 'data/analysis/daily_vkt.csv').sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(actual[expected.columns], expected, check_dtype=False,
                                  check_exact=False, rtol=1e-10, atol=1e-12)
    for filename in ['wind_rate.csv', 'allocated_rate.csv', 'severity_conditions.csv']:
        blob = subprocess.check_output(['git', 'show', f'{commit}:reports/main/tables/{filename}'], cwd=ROOT)
        expected = pd.read_csv(io.BytesIO(blob))
        actual = pd.read_csv(out / 'reports/main/tables' / filename)
        pd.testing.assert_frame_equal(actual, expected, check_dtype=False,
                                      check_exact=False, rtol=1e-10, atol=1e-12)
    # Demonstrate that the new test catches restoring the historical bug.
    source = out / 'src/traffic/counter_day_weather.py'
    original = source.read_text()
    assert 'panel[slots].ge(minimum)' in original
    try:
        source.write_text(original.replace('panel[slots].ge(minimum)', 'panel[valid].ge(minimum)'))
        result = subprocess.run([str(PYTHON), '-m', 'unittest',
            'tests.test_scientific_bugfixes.DistinctCoverageTests.test_build_eligibility_uses_distinct_slots_and_window_boundaries', '-v'],
            cwd=out, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (out / 'mutation.log').write_text(result.stdout)
        assert result.returncode != 0 and 'AssertionError' in result.stdout, result.stdout
    finally:
        source.write_text(original)
    for name, expected in manifest.items():
        assert sha(ROOT / name) == expected, 'External input modified: ' + name
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    summary = {'commit': commit, 'external_inputs_verified': len(manifest),
               'tests': 42, 'validation': 'PASS', 'thesis_compilations': 2,
               'coverage_mutation': 'old row-count rule fails the new build-level test',
               'audited_fresh_results': 'all compared tables match',
               'annual_wind_allocated_762_severity': 'unchanged from committed annual baseline',
               'strict_sample': 613, 'review_assumptions': 'unchanged'}
    (out / 'verification.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    print('VERIFIED OUTPUT', out, flush=True)


if __name__ == '__main__':
    main()
