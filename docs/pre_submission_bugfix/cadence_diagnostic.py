"""Investigate observation cadence without changing the exposure weighting rule."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.traffic.counter_day_weather import VARIABLES
DOC=ROOT/'docs/pre_submission_bugfix'
frame=pq.read_table(ROOT/'data/processed/weather/weather.parquet',filters=[('station','=',6300),('time','>=',pd.Timestamp('2019-06-01')),('time','<',pd.Timestamp('2019-07-01'))],columns=['station','time','f','fg','t']).to_pandas()
frame=frame[frame.time.dt.hour.ge(7)].copy();frame['slot']=frame.time.dt.floor('10min');frame['date']=frame.time.dt.normalize()
rows=[]
for date,group in frame.groupby('date'):
    if not group.time.dt.minute.mod(10).ne(0).any():continue
    for variable,(bounds,labels) in VARIABLES.items():
        g=group.rename(columns={'t':'temperature'}).copy();g=g[np.isfinite(g[variable])]
        if variable=='temperature':g=g[g[variable].between(-30,30)]
        g['bin']=np.array(labels)[np.searchsorted(bounds,g[variable],side='right')]
        g['slot_weight']=1/g.groupby('slot')['slot'].transform('size')
        for label in labels:
            selected=g[g.bin.eq(label)]
            rows.append({'date':date,'variable':variable,'bin':label,'rows':len(g),'unique_times':g.time.nunique(),'distinct_slots':g.slot.nunique(),
                         'row_fraction':len(selected)/len(g),'equal_slot_fraction_diagnostic_only':selected.slot_weight.sum()/g.slot.nunique()})
pd.DataFrame(rows).to_csv(DOC/'cadence_weighting_diagnostic.csv',index=False)
# Independently verify duplicate keys and raw density on the problematic date.
raw=pq.read_table(ROOT/'data/raw/weather/weather_10min_raw.parquet',filters=[('station','=',6300),('time','>=',pd.Timestamp('2019-06-11 07:00')),('time','<',pd.Timestamp('2019-06-12'))],columns=['station','time','f','fg','t']).to_pandas()
summary={'raw_rows_2019_06_11':len(raw),'raw_unique_timestamps':raw.time.nunique(),'raw_duplicate_keys':int(raw.duplicated(['station','time']).sum()),'clean_june_duplicate_keys':int(frame.duplicated(['station','time']).sum())}
(DOC/'cadence_source_check.json').write_text(json.dumps(summary,indent=2));print(summary)
