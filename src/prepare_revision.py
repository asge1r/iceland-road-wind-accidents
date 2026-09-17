"""Prepare compact CSV inputs for the retained thesis's descriptive additions.

Read the cleaned joint weather archive once, clip annual road lengths with the
same urban geometry as accident classification, and export actual file examples.
Run before src.tables.revision; no analysis or figures are fitted here.
"""
from pathlib import Path
import calendar
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from src.weather.frequency import SEASONS, season_index, station_ids
from src.weather.eligibility import valid_temperature
from src.traffic.rural_lengths import add_rural_lengths

OUT = Path('data/analysis')


def joint_category(wind, temperature):
    return (np.asarray(wind) >= 15).astype(int) * 2 + (np.asarray(temperature) >= 3).astype(int)


def joint_frequency(path):
    source = pq.ParquetFile(path)
    stations = station_ids(source, source.num_row_groups)
    counts = np.zeros((len(stations) * 4, 4), dtype=np.int64)
    for index, batch in enumerate(source.iter_batches(batch_size=1_000_000, columns=['station','time','f','fg','t'])):
        station, time, wind, gust, temp = [batch.column(c).to_numpy(zero_copy_only=False) for c in ['station','time','f','fg','t']]
        year = time.astype('datetime64[Y]').astype(int) + 1970
        month = time.astype('datetime64[M]').astype(int) % 12 + 1
        valid = (valid_temperature(temp) & np.isfinite(wind) & np.isfinite(gust)
                 & (wind >= 0) & (wind < 45) & (gust >= 0) & (gust < 65)
                 & (gust + .5 >= wind) & ~((gust == 0) & (wind > 0))
                 & (year >= 2007) & (year <= 2025))
        group = np.searchsorted(stations, station[valid]) * 4 + season_index(month[valid])
        cat = joint_category(wind[valid], temp[valid])
        counts += np.bincount(group * 4 + cat, minlength=counts.size).reshape(counts.shape)
        if index % 30 == 0: print(f'joint batches={index+1}', flush=True)
    result = pd.DataFrame({'weather_station_id':np.repeat(stations,16),
        'season':np.tile(np.repeat(SEASONS,4),len(stations)),
        'category':np.tile(np.arange(4),len(stations)*4),
        'measurements':counts.ravel(),
        'total_measurements':np.repeat(counts.sum(axis=1),4)})
    result['frequency'] = result.measurements / result.total_measurements.where(result.total_measurements.gt(0))
    return result


def resolve_chainage(data):
    """Recover omitted starts only from the same registered section/start name.

    The 2007 workbook supplies lengths but omits station-distance columns.
    Use the nearest prior and subsequent recorded starts if they agree. Record
    the evidence year; conflicting/unknown origins remain unmapped.
    """
    result = data.copy()
    result['chainage_basis'] = 'published'
    missing = result.section_start_station_km.isna() & result.section_end_station_km.isna()
    for index, row in result[missing].iterrows():
        candidates = result[result.road_section.eq(row.road_section)
            & result.section_start_name.eq(row.section_start_name)
            & result.section_start_station_km.notna()
            & result.chainage_basis.eq('published')]
        before = candidates[candidates.year.lt(row.year)].sort_values('year').tail(1)
        after = candidates[candidates.year.gt(row.year)].sort_values('year').head(1)
        adjacent = pd.concat([before, after])
        if adjacent.empty or adjacent.section_start_station_km.nunique() != 1:
            result.loc[index, 'chainage_basis'] = 'unresolved'
            continue
        start = adjacent.section_start_station_km.iloc[0]
        result.loc[index, 'section_start_station_km'] = start
        result.loc[index, 'section_end_station_km'] = start + row.section_length_km
        years = ','.join(map(str, adjacent.year.astype(int)))
        result.loc[index, 'chainage_basis'] = 'same section and start name: ' + years
    return result


def annual_rural_exposure(data):
    data = resolve_chainage(data)
    data = data[data.year.between(2007,2025)].copy()
    if data.duplicated(['year','road_section']).any(): raise ValueError('Duplicate annual road section')
    data['counter_section_start_km'] = data.section_start_station_km
    data['counter_section_end_km'] = data.section_end_station_km
    data['counter_section_length_km'] = data.section_length_km
    data = add_rural_lengths(data,Path('data/raw/traffic/reference/roads.geojson'),
                            Path('data/raw/accidents/urban_boundaries_2020_2024.geojson'))
    unresolved = data.rural_section_length_km.isna() & data.section_length_km.gt(0)
    data.loc[unresolved, 'unmapped_section_length_km'] = data.loc[unresolved, 'section_length_km']
    data.loc[unresolved, 'rural_section_length_km'] = 0.0
    frames=[]
    for season, field in [('Winter','vdu'),('Summer','sdu'),('All year','adu')]:
        part=data.copy();part['period']=season;part['daily_traffic']=part[field]
        part['days']=[(121+calendar.isleap(y) if season=='Winter' else 122 if season=='Summer' else 365+calendar.isleap(y)) for y in part.year]
        part['eligible']=part.daily_traffic.ge(0)&part.rural_section_length_km.notna()
        part['estimated_vehicle_km']=(part.daily_traffic*part.rural_section_length_km*part.days).where(part.eligible)
        part['unmapped_vehicle_km']=(part.daily_traffic*part.unmapped_section_length_km*part.days).where(part.eligible)
        frames.append(part)
    return pd.concat(frames,ignore_index=True)


REVISION_FILES = {
    'vkt_accidents.csv': 'Event-time records for the 694 eligible VKT accidents.',
    'revision_accidents.csv': 'Cleaned register for descriptive urban/rural and seasonal checks.',
    'rural_annual_exposure.csv': 'Annual and seasonal rural road exposure with mapping exclusions.',
    'joint_weather_frequency.csv': 'Simultaneous joint wind-temperature station-season frequencies.',
    'cleaned_accident_rows.csv': 'First two stored cleaned accident records.',
    'cleaned_weather_rows.csv': 'First two stored cleaned weather records.',
}


def register_inputs(output=OUT):
    from src.export_docs import register_manifest_file
    for filename, description in REVISION_FILES.items():
        register_manifest_file(output, filename, description)


def export_vkt_events():
    events = pd.read_csv('data/processed/traffic/counter_accidents.csv')
    events.to_csv(OUT / 'vkt_accidents.csv', index=False)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    export_vkt_events()
    all_accidents=pd.read_csv('data/processed/accidents/all.csv',low_memory=False)
    all_accidents.to_csv(OUT/'revision_accidents.csv',index=False)
    all_accidents.head(2).to_csv(OUT/'cleaned_accident_rows.csv',index=False)
    weather=Path('data/processed/weather/weather.parquet')
    next(pq.ParquetFile(weather).iter_batches(batch_size=2)).to_pandas().to_csv(OUT/'cleaned_weather_rows.csv',index=False)
    annual_rural_exposure(pd.read_csv('data/processed/traffic/annual.csv',low_memory=False)).to_csv(OUT/'rural_annual_exposure.csv',index=False)
    print('annual rural lengths exported',flush=True)
    joint_frequency(weather).to_csv(OUT/'joint_weather_frequency.csv',index=False)
    register_inputs()
    print('joint frequencies exported',flush=True)

if __name__=='__main__': main()
