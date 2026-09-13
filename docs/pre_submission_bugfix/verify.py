"""Validate fresh-output invariants and preservation of the protected snapshot."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
OUT=ROOT/'reports/reproduced/pre_submission_bugfix';DOC=ROOT/'docs/pre_submission_bugfix'
from src.traffic.counter_day_weather import VARIABLES
from src.analysis.oe_analysis import load_data, station_frequency_scenario, VARIABLES as OE_VARIABLES

checks={}
for name in ['weather_frequency.csv','weather_yearly.csv']:
    old=pd.read_csv(OUT/'before/analysis'/name);new=pd.read_csv(OUT/'data/analysis'/name)
    wind=lambda f:f[f.variable.ne('temperature')].reset_index(drop=True)
    pd.testing.assert_frame_equal(wind(old),wind(new),check_exact=True)
    keys=['station','season','variable']+(['year'] if 'year' in new else [])
    counts=new.groupby(keys).measurement_count.sum()
    totals=new.groupby(keys).total_measurements_in_period.first()
    pd.testing.assert_series_equal(counts,totals,check_names=False)
    checks[name]='wind/gust unchanged; bin counts conserve all eligible observations'

# Recompute every primary panel's stratum expectations, including severity subsets.
acc,freq=load_data(OUT/'data/analysis/accidents.csv',OUT/'data/analysis/accident_conditions.csv',OUT/'data/analysis/weather_frequency.csv',None,None)
coverage=[]
for spec in OE_VARIABLES:
    for sample in ['Injury accidents','Severe or fatal']:
        for season in ['All seasons','Winter','Spring','Summer','Fall']:
            result,detail,cov=station_frequency_scenario(acc,freq,spec,20,sample,season)
            totals=detail.groupby(['weather_station_id','season']).expected_accidents.sum()
            expected=detail.groupby(['weather_station_id','season']).group_accidents.first()
            assert np.allclose(totals,expected,rtol=0,atol=1e-10)
            assert result.observed_accidents.sum()==cov['analysed_accidents']
            assert cov['eligible_accidents']==cov['analysed_accidents']
            coverage.append(dict(sample=sample,season=season,**cov))
pd.DataFrame(coverage).to_csv(DOC/'oe_coverage_checks.csv',index=False)
assert len(coverage)==30
checks['oe_strata']='all 30 panels: eligible=analysed; expected counts conserve each contributing station-season'
panel=pd.read_parquet(OUT/'data/processed/traffic/counter_day_weather.parquet')
for variable in VARIABLES:
    assert panel[f'{variable}_distinct_slots'].between(0,102).all()
    assert panel[f'{variable}_coverage_ok'].equals(panel[f'{variable}_distinct_slots'].ge(92))
checks['strict_coverage']='all variable-specific coverage flags equal distinct_slots >= 92; maximum 102'

from src.tables.weather_model import prepare
pd.testing.assert_frame_equal(
    prepare(pd.read_csv(OUT/'before/analysis/case_control.csv')).reset_index(drop=True),
    prepare(pd.read_csv(OUT/'data/analysis/case_control.csv')).reset_index(drop=True),check_exact=True)
checks['joint_input']='complete-case wind/temperature input exactly identical'
trace=pd.read_csv(DOC/'extra_temperature_controls_frozen_run_trace.csv',parse_dates=['time','start','end'])
intervals=pd.read_csv(ROOT/'archive/generated_diagnostics/weather_frozen_zero_intervals.csv',parse_dates=['start','end'])
for row in trace.itertuples():
    hit=intervals[intervals.station.eq(row.station)&intervals.start.eq(row.start)&intervals.end.eq(row.end)]
    assert len(hit)==1 and row.start<=row.time<=row.end
checks['control_QC']='all five raw observations fall inside independently re-read archived frozen intervals'
manifest=json.loads((OUT/'protected_before.json').read_text())
failures=[]
for name,expected in manifest.items():
    p=ROOT/name
    if p.stat().st_mtime_ns!=expected['mtime_ns'] or hashlib.file_digest(p.open('rb'),'sha256').hexdigest()!=expected['sha256']:
        failures.append(name)
assert not failures,failures
checks['protected_snapshot']=f'All {len(manifest)} initial analysis/prepared/result/thesis files have identical SHA-256 and nanosecond mtimes'
(DOC/'verification.json').write_text(json.dumps(checks,indent=2))
shutil_manifest=DOC/'protected_before.json'
shutil_manifest.write_text(json.dumps(manifest,indent=2))
print(json.dumps(checks,indent=2))
