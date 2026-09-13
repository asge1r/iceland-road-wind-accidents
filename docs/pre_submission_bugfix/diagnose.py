"""Write durable source traces and before/after diagnostics for the fix report."""
from pathlib import Path
import json
import shutil
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'reports/reproduced/pre_submission_bugfix'
DOC=ROOT/'docs/pre_submission_bugfix'
from src.accidents.case_control import read_weather
from src.traffic.counter_accidents import accident_candidates
from src.accidents.match_weather import read_candidate_weather, select_best

# The authoritative audit's raw/QC trace is retained alongside independent replays.
AUDIT=Path('/private/tmp/analysis_theory_audit_hpjsv0_a')
for name in ['extra_temperature_controls_frozen_run_trace.csv','extra_temperature_controls_raw_weather.csv','cadence_trace.json']:
    if not (DOC/name).exists() and (AUDIT/name).exists():
        shutil.copy2(AUDIT/name,DOC/name)

before=pd.read_csv(OUT/'before/analysis/case_control.csv')
after=pd.read_csv(OUT/'data/analysis/case_control.csv')
keys=['exposure','stratum_id','case','timestamp','station_id','value']
diff=before.merge(after[keys],on=keys,how='outer',indicator=True)
diff[diff._merge.ne('both')].to_csv(DOC/'control_row_changes.csv',index=False)
assert len(diff[diff._merge.eq('left_only')])==5 and not diff._merge.eq('right_only').any()
trace=pd.read_csv(DOC/'extra_temperature_controls_frozen_run_trace.csv',parse_dates=['time','start','end'])
candidates=trace.rename(columns={'station':'station_id','time':'weather_time'})
raw=read_weather(ROOT/'data/raw/weather/weather_10min_raw.parquet',candidates)
pd.testing.assert_frame_equal(raw.sort_values('station_id').reset_index(drop=True),
    candidates[['station_id','weather_time','f','fg','t']].sort_values('station_id').reset_index(drop=True),check_dtype=False)

# Every possible near-midnight primary match, replayed at its retained station.
acc=pd.read_csv(ROOT/'data/processed/accidents/rural_injury.csv',low_memory=False)
acc.timestamp=pd.to_datetime(acc.timestamp)
minutes=acc.timestamp.dt.hour*60+acc.timestamp.dt.minute
near=acc[(minutes.ge(1435)|minutes.le(5)) & acc.weather_station_dist_km.le(20) & acc.f.notna()].reset_index(drop=True)
cand=accident_candidates(near)
weather=read_candidate_weather(pq.ParquetFile(ROOT/'data/processed/weather/weather.parquet'),cand)
matched=select_best(cand,weather)
replayed=near.merge(matched[['acc_index','weather_time','weather_time_difference_minutes']],left_index=True,right_on='acc_index',suffixes=('','_replayed'))
cross=replayed[replayed.timestamp.dt.normalize().ne(replayed.weather_time.dt.normalize())]
cross[['id','timestamp','weather_station_id','weather_time','weather_time_difference_minutes_replayed','meidsli']].to_csv(DOC/'midnight_primary.csv',index=False)
print('Primary crossing matches',len(cross),flush=True)
