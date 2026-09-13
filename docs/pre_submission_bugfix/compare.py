"""Compare the fresh products with the actual live snapshot, not git HEAD."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
OUT=ROOT/'reports/reproduced/pre_submission_bugfix';DOC=ROOT/'docs/pre_submission_bugfix'
from src.traffic.daily_vkt import allocate_same_day_exposure
from src.traffic.counter_day_weather import VARIABLES

specs={
 'weather_oe.csv':['variable','outcome','period','bin_label'],
 'year_oe.csv':['variable','coarse_bin'],
 'matched_weather.csv':['exposure','model','comparison'],
 'weather_model.csv':['variable','comparison'],
 'temperature_rate.csv':['bin_label'],
}
for name,keys in specs.items():
    old=pd.read_csv(OUT/'before/tables'/name);new=pd.read_csv(OUT/'reports/main/tables'/name)
    merged=old.merge(new,on=keys,how='outer',suffixes=('_old','_new'),validate='one_to_one')
    merged.to_csv(DOC/(name.removesuffix('.csv')+'_comparison.csv'),index=False)
old=pd.read_csv(OUT/'before/analysis/daily_vkt.csv');new=pd.read_csv(OUT/'data/analysis/daily_vkt.csv')
keys=['variable','outcome','period','bin_label']
old.merge(new,on=keys,suffixes=('_old','_new'),validate='one_to_one').to_csv(DOC/'daily_vkt_comparison.csv',index=False)
for frame,kind in [(old,'old'),(new,'new')]:
    annual=frame[frame.period.eq('All year')].groupby(['variable','bin_label'],sort=False).agg(accidents=('accidents','sum'),estimated_vehicle_km=('estimated_vehicle_km','first')).reset_index()
    annual['rate_per_100m_vehicle_km']=annual.accidents/annual.estimated_vehicle_km*1e8
    if kind=='old': annual_old=annual
    else: annual_old.merge(annual,on=['variable','bin_label'],suffixes=('_old','_new')).to_csv(DOC/'daily_vkt_all_injury_comparison.csv',index=False)

oldpanel=pd.read_parquet(ROOT/'data/processed/traffic/counter_day_weather.parquet')
newpanel=pd.read_parquet(OUT/'data/processed/traffic/counter_day_weather.parquet')
keys=['counter_section_id','date']
panel=oldpanel.merge(newpanel,on=keys,suffixes=('_old','_new'),validate='one_to_one')
changed=np.zeros(len(panel),bool)
for variable in VARIABLES: changed |= panel[f'{variable}_coverage_ok_old'].ne(panel[f'{variable}_coverage_ok_new'])
panel[changed].to_csv(DOC/'coverage_changed_days.csv',index=False)
acc=pd.read_csv(OUT/'data/processed/traffic/counter_accidents.csv',parse_dates=['date','timestamp','weather_time'])
summary={};retained=[]
for variable,(_,labels) in VARIABLES.items():
    exposure=allocate_same_day_exposure(newpanel,variable,labels)
    days=exposure[keys].drop_duplicates()
    events=acc.merge(days,on=keys,validate='many_to_one')
    column='temperature' if variable=='temperature' else variable
    events=events[events[column].notna()]
    olddays=oldpanel[oldpanel.traffic_vehicles.gt(0)&oldpanel[f'{variable}_coverage_ok']][keys]
    oldevents=acc.merge(olddays,on=keys,validate='many_to_one')
    oldevents=oldevents[oldevents[column].notna()]
    assert set(oldevents.id)==set(events.id)
    events.assign(variable=variable).to_csv(DOC/f'{variable}_retained_ids.csv',index=False)
    acc[~acc.id.isin(events.id)].assign(variable=variable).to_csv(DOC/f'{variable}_excluded_ids.csv',index=False)
    reconstructed=exposure.groupby(keys).estimated_vehicle_km.sum()
    expected=newpanel.set_index(keys).vehicle_km.reindex(reconstructed.index)
    assert np.allclose(reconstructed,expected,rtol=1e-10,atol=1e-6)
    # Every event's bin must have actual same-day allocated support.
    bounds=VARIABLES[variable][0]
    events['bin_label']=np.array(labels)[np.searchsorted(bounds,events[column].to_numpy(),side='right')]
    support=events.merge(exposure[keys+['bin_label']],on=keys+['bin_label'],how='left',indicator=True,validate='many_to_one')
    assert support._merge.eq('both').all()
    cross=events[events.timestamp.dt.normalize().ne(events.weather_time.dt.normalize())]
    retained.append(cross.assign(variable=variable))
    summary[variable]={'matched':len(acc),'retained':len(events),'positive_coverage_days':len(days),'total_vkt':float(exposure.estimated_vehicle_km.sum()),'max_conservation_error':float(abs(reconstructed-expected).max()),'midnight_crossings':len(cross)}
pd.concat(retained).to_csv(DOC/'midnight_strict.csv',index=False)
(DOC/'strict_summary.json').write_text(json.dumps(summary,indent=2))

# Every retained table: exact numerical comparison plus changed numeric cells.
summary_rows=[];cells=[]
for p in sorted((OUT/'before/tables').glob('*.csv')):
    q=OUT/'reports/main/tables'/p.name
    if not q.exists():continue
    a=pd.read_csv(p);b=pd.read_csv(q)
    if a.shape!=b.shape or list(a.columns)!=list(b.columns):
        summary_rows.append({'table':p.name,'comparison':'shape/columns differ','changed_numeric_cells':None});continue
    n=0
    for col in a.select_dtypes(include='number').columns:
        av=a[col].to_numpy();bv=b[col].to_numpy()
        different=~np.isclose(av,bv,rtol=1e-10,atol=1e-12,equal_nan=True)
        for i in np.flatnonzero(different):
            cells.append({'table':p.name,'row':int(i),'column':col,'old':av[i],'new':bv[i]});n+=1
    summary_rows.append({'table':p.name,'comparison':'changed' if n else 'equal within 1e-10 relative/1e-12 absolute','changed_numeric_cells':n})
refitted={'absolute_rate.csv','allocated_rate.csv','allocated_rate_severity.csv','matched_weather.csv','season_rate.csv','season_rate_severity.csv','severity_conditions.csv','temperature_rate.csv','weather_coverage.csv','weather_model.csv','weather_oe.csv','weather_oe_audit.csv','wind_rate.csv','wind_rate_multiple.csv','wind_rate_one.csv','wind_rate_severity.csv','wind_season.csv','year_oe.csv'}
for row in summary_rows:
    row['verification_scope']='fresh calculation from canonical analysis inputs' if row['table'] in refitted else 'preserved unchanged baseline dependency; not re-fitted'
pd.DataFrame(summary_rows).to_csv(DOC/'all_table_comparison.csv',index=False)
pd.DataFrame(cells).to_csv(DOC/'changed_numeric_cells.csv',index=False)
print(json.dumps(summary,indent=2))
