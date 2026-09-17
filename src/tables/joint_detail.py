"""Fixed descriptive joint O/E cells, with an atomic 3 C split for exact audit.

The requested 0--6 C display cell straddles the legacy 3 C boundary. Preserve
0--3 and 3--6 internally; never infer the legacy partition from merged cells.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from src.weather.frequency import SEASONS, season_index, station_ids
from src.weather.eligibility import valid_temperature
from src.prepare_revision import joint_category
from src.tables.revision import joint_oe

WIND_LABELS = ['0–5', '5–10', '10–15', '≥15']
TEMP_LABELS = ['<−3', '−3–0', '0–6', '6–12', '≥12']
ATOMIC_TO_TEMP = np.array([0, 1, 2, 2, 3, 4])
OUT = Path('reports/main/tables')
AUDIT = Path('reports/working/tables')


def atomic_category(wind, temperature):
    wind, temperature = np.asarray(wind), np.asarray(temperature)
    if not (np.isfinite(wind).all() and np.isfinite(temperature).all() and (wind >= 0).all()):
        raise ValueError('Joint classification requires finite weather and nonnegative wind')
    return np.searchsorted([5, 10, 15], wind, side='right') * 6 + np.searchsorted([-3, 0, 3, 6, 12], temperature, side='right')


def display_category(atom):
    atom = np.asarray(atom)
    return atom // 6 * 5 + ATOMIC_TO_TEMP[atom % 6]


def coarse_category(atom):
    atom = np.asarray(atom)
    return (atom // 6 == 3).astype(int) * 2 + (atom % 6 >= 3).astype(int)


def weather_frequency(path):
    source = pq.ParquetFile(path)
    stations = station_ids(source, source.num_row_groups)
    counts = np.zeros((len(stations) * 4, 24), dtype=np.int64)
    valid_total = 0
    for i, batch in enumerate(source.iter_batches(batch_size=1_000_000, columns=['station','time','f','fg','t'])):
        station,time,wind,gust,temp = [batch.column(c).to_numpy(zero_copy_only=False) for c in ['station','time','f','fg','t']]
        year = time.astype('datetime64[Y]').astype(int) + 1970
        month = time.astype('datetime64[M]').astype(int) % 12 + 1
        # Identical eligibility to the retained coarse simultaneous frequency.
        valid = (valid_temperature(temp) & np.isfinite(wind) & np.isfinite(gust)
                 & (wind >= 0) & (wind < 45) & (gust >= 0) & (gust < 65)
                 & (gust + .5 >= wind) & ~((gust == 0) & (wind > 0))
                 & (year >= 2007) & (year <= 2025))
        group = np.searchsorted(stations, station[valid]) * 4 + season_index(month[valid])
        cat = atomic_category(wind[valid], temp[valid])
        assert len(cat) == valid.sum() and ((cat >= 0) & (cat < 24)).all()
        counts += np.bincount(group * 24 + cat, minlength=counts.size).reshape(counts.shape)
        valid_total += int(valid.sum())
        if i % 30 == 0: print(f'Detailed joint weather batches={i+1}', flush=True)
    assert counts.sum() == valid_total
    result = pd.DataFrame({'weather_station_id':np.repeat(stations,96),
        'season':np.tile(np.repeat(SEASONS,24),len(stations)),
        'atomic_cell':np.tile(np.arange(24),len(stations)*4),
        'measurements':counts.ravel(), 'total_measurements':np.repeat(counts.sum(axis=1),24)})
    result['frequency'] = result.measurements / result.total_measurements.where(result.total_measurements.gt(0))
    return result


def eligible_events():
    events = pd.read_csv('data/analysis/accidents.csv').merge(
        pd.read_csv('data/analysis/accident_conditions.csv'),on='id',validate='one_to_one')
    valid = (events.weather_station_dist_km.le(20)&events.weather_time_difference_minutes.le(5)
             &events.temp_distance_km.le(20)&events.temp_time_diff_min.le(5)
             &events.f.notna()&events.temperature_c.between(-30,30))
    events = events[valid].copy()
    if not (events.weather_station_id.eq(events.temp_station_id).all()
            and events.weather_time_difference_minutes.eq(events.temp_time_diff_min).all()):
        raise ValueError('Joint events must share station and observation time')
    return events


def verify_simultaneous_records(events, path):
    """Confirm f, gust and temperature occur on one eligible archive record.

    Absolute time offsets alone cannot disambiguate the two five-minute ties.
    Check both candidate times against stored float32 values, not just offsets.
    """
    from src.accidents.match_weather import read_candidate_weather
    candidates=[]
    for sign in (-1,1):
        part=events[['id','weather_station_id','f','fg','temperature_c']].copy()
        part['weather_time']=(pd.to_datetime(events.timestamp)+pd.to_timedelta(
            sign*events.weather_time_difference_minutes,unit='m')).dt.round('us')
        candidates.append(part)
    candidates=pd.concat(candidates).drop_duplicates(['id','weather_time'])
    weather=read_candidate_weather(pq.ParquetFile(path),candidates)
    joined=candidates.merge(weather,on=['weather_station_id','weather_time'],suffixes=('_event','_archive'))
    same=np.ones(len(joined),dtype=bool)
    for left,right in [('f_event','f_archive'),('fg_event','fg_archive'),('temperature_c','t')]:
        same &= joined[left].to_numpy(dtype='float32')==joined[right].to_numpy(dtype='float32')
    matched=joined[same].sort_values(['id','weather_time']).drop_duplicates('id')
    if set(matched.id)!=set(events.id):
        raise ValueError('Some joint events have no simultaneous archive record')
    return matched


def calculate(events, frequency):
    keys = ['weather_station_id','season']
    if events.id.duplicated().any(): raise ValueError('Duplicate joint events')
    events = events.copy()
    events['atomic_cell'] = atomic_category(events.f,events.temperature_c)
    groups = events.groupby(keys).size().rename('accidents').reset_index()
    background = frequency.merge(groups,on=keys,how='inner',validate='many_to_one')
    if len(background) != 24*len(groups) or background.duplicated(keys+['atomic_cell']).any():
        raise ValueError('Missing or duplicate atomic frequency cells')
    if not background.groupby(keys).atomic_cell.apply(lambda x:set(x)==set(range(24))).all():
        raise ValueError('Invalid atomic categories')
    if not np.isfinite(background.frequency).all() or (background.frequency<0).any():
        raise ValueError('Invalid joint frequencies')
    if not np.allclose(background.groupby(keys).frequency.sum(),1,rtol=0,atol=1e-12):
        raise ValueError('Joint frequencies do not conserve totals')
    background['expected_accidents'] = background.accidents * background.frequency
    counts = events.groupby(keys+['atomic_cell']).size().rename('observed_accidents').reset_index()
    background = background.merge(counts,on=keys+['atomic_cell'],how='left',validate='one_to_one')
    background['observed_accidents'] = background.observed_accidents.fillna(0).astype(int)
    atomic = background.groupby('atomic_cell')[['observed_accidents','expected_accidents']].sum().reindex(range(24),fill_value=0).reset_index()
    atomic['cell'] = display_category(atomic.atomic_cell)
    atomic['coarse_cell'] = coarse_category(atomic.atomic_cell)
    result = atomic.groupby('cell')[['observed_accidents','expected_accidents']].sum().reindex(range(20),fill_value=0).reset_index()
    result['wind_order'] = result.cell // 5
    result['temperature_order'] = result.cell % 5
    result['wind_bin'] = result.wind_order.map(dict(enumerate(WIND_LABELS)))
    result['temperature_bin'] = result.temperature_order.map(dict(enumerate(TEMP_LABELS)))
    result['oe'] = result.observed_accidents / result.expected_accidents.where(result.expected_accidents.gt(0))
    result['sample_percent'] = result.observed_accidents / len(events) * 100
    result['sparse'] = result.observed_accidents.lt(10) | result.expected_accidents.lt(5)
    if result.observed_accidents.sum()!=len(events) or not np.isclose(result.expected_accidents.sum(),len(events),rtol=0,atol=1e-8):
        raise ValueError('Joint totals differ from eligible sample')
    return result,atomic,background


def contrasts(result):
    cells=result.set_index(['wind_order','temperature_order'])
    rows=[]
    def add(kind, group, high, reference):
        a,b=cells.loc[high],cells.loc[reference]
        adequate=not (a['sparse'] or b['sparse']) and np.isfinite(a.oe) and np.isfinite(b.oe) and b.oe>0
        rows.append(dict(contrast=kind,group=group,numerator_cell=int(a.cell),reference_cell=int(b.cell),
                         adequate_support=adequate,oe_ratio=a.oe/b.oe if adequate else np.nan))
    for t,label in enumerate(TEMP_LABELS):add('High/low wind',label,(3,t),(0,t))
    for w,label in enumerate(WIND_LABELS):
        add('Warm/moderate temperature',label,(w,4),(w,3))
        add('Below-freezing/moderate temperature',label,(w,1),(w,3))
    return pd.DataFrame(rows)


def verify_coarse(events, frequency, atomic):
    legacy=pd.read_csv('data/analysis/joint_weather_frequency.csv')
    grouped=frequency.assign(category=coarse_category(frequency.atomic_cell)).groupby(
        ['weather_station_id','season','category']).measurements.sum().sort_index()
    old=legacy.set_index(['weather_station_id','season','category']).measurements.sort_index()
    if not grouped.index.equals(old.index):raise ValueError("Legacy station-season cells differ")
    np.testing.assert_array_equal(grouped.to_numpy(),old.to_numpy())
    expected,_=joint_oe(events,legacy)
    actual=atomic.groupby('coarse_cell')[['observed_accidents','expected_accidents']].sum()
    np.testing.assert_array_equal(actual.observed_accidents,expected.observed_accidents)
    np.testing.assert_allclose(actual.expected_accidents,expected.expected_accidents,rtol=0,atol=1e-8)
    actual['oe']=actual.observed_accidents/actual.expected_accidents
    return actual


def main():
    OUT.mkdir(parents=True,exist_ok=True);AUDIT.mkdir(parents=True,exist_ok=True)
    events=eligible_events()
    matched=verify_simultaneous_records(events,'data/processed/weather/weather.parquet')
    frequency=weather_frequency('data/processed/weather/weather.parquet')
    if len(events)!=6259:raise ValueError('Eligible joint population changed')
    result,atomic,background=calculate(events,frequency)
    coarse=verify_coarse(events,frequency,atomic)  # Fail before publishing if reconciliation fails.
    result.to_csv(OUT/'joint_wind_temperature_detail.csv',index=False)
    contrasts(result).to_csv(OUT/'joint_wind_temperature_contrasts.csv',index=False)
    matched.to_csv(AUDIT/'joint_simultaneous_events.csv',index=False)
    atomic.to_csv(AUDIT/'joint_atomic_oe.csv',index=False)
    frequency.to_csv(AUDIT/'joint_atomic_frequency.csv',index=False)
    coarse.to_csv(AUDIT/'joint_coarse_reconciliation.csv')
    (AUDIT/'joint_detail_validation.json').write_text(json.dumps(dict(
        eligible_accidents=len(events),observed=int(result.observed_accidents.sum()),
        expected=float(result.expected_accidents.sum()),valid_weather_observations=int(frequency.measurements.sum()),
        cells=20,atomic_cells=24,coarse_reconciled=True,
        note='0–6 C crosses the legacy 3 C boundary; reconciliation uses retained 0–3 and 3–6 atomic cells, never a proportional split.'),indent=2)+'\n')
    print(result.to_string(index=False));print(contrasts(result).to_string(index=False))


if __name__=='__main__':main()
