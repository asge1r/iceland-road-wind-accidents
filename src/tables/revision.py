"""Reproducible descriptive additions to the three retained thesis analyses.

Reads compact CSVs exported by src.prepare_revision; retains all ranking rows
and denominator exclusions in audit outputs. No causal model is fitted.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from src.prepare_revision import joint_category
from src.tables.thesis import write_table

AUDIT=Path('reports/working/tables')
TEX=Path('reports/thesis/generated')


def joint_oe(accidents, frequency):
    keys=['weather_station_id','season']
    events=accidents.copy()
    if events.id.duplicated().any(): raise ValueError('Duplicate joint accidents')
    events['category']=joint_category(events.f,events.temperature_c)
    counts=events.groupby(keys).size().rename('accidents').reset_index()
    background=frequency.merge(counts,on=keys,how='inner',validate='many_to_one')
    if len(background)!=4*len(counts): raise ValueError('Missing joint frequency cells')
    if background.duplicated([*keys,'category']).any(): raise ValueError('Duplicate joint cells')
    if not np.allclose(background.groupby(keys).frequency.sum(),1): raise ValueError('Joint frequencies do not conserve totals')
    background['expected_accidents']=background.accidents*background.frequency
    observed=events.groupby([*keys,'category']).size().rename('observed_accidents').reset_index()
    background=background.merge(observed,on=[*keys,'category'],how='left',validate='one_to_one')
    background['observed_accidents']=background.observed_accidents.fillna(0).astype(int)
    result=background.groupby('category')[['observed_accidents','expected_accidents']].sum().reset_index()
    result['oe']=result.observed_accidents/result.expected_accidents
    if result.observed_accidents.sum()!=len(events) or not np.isclose(result.expected_accidents.sum(),len(events)):
        raise ValueError('Joint totals do not partition eligible accidents')
    return result,background


def seasonal_summary(accidents, exposure):
    injury=accidents[accidents.urban_rural.eq('Rural')&accidents.meidsli.isin([1,2,3])].copy()
    month=pd.to_datetime(injury.timestamp).dt.month
    injury['period']=np.select([month.isin([12,1,2,3]),month.isin([6,7,8,9])],['Winter','Summer'],default='Other')
    rows=[]
    for period in ['Winter','Summer']:
        part=injury[injury.period.eq(period)]
        x=exposure[exposure.period.eq(period)]
        rows.append(dict(period=period,accidents=len(part),minor=int(part.meidsli.eq(3).sum()),
                         severe=int(part.meidsli.isin([1,2]).sum()),
                         estimated_vehicle_km=x.estimated_vehicle_km.sum(),
                         unmapped_vehicle_km=x.unmapped_vehicle_km.sum()))
    result=pd.DataFrame(rows).set_index('period')
    result['severe_proportion']=result.severe/result.accidents
    for column in ['accidents','minor','severe']:
        result[column+'_per_million_vkt']=result[column]/result.estimated_vehicle_km*1e6
    return result


def road_rates(accidents,exposure):
    x=exposure[exposure.period.eq('All year')&exposure.estimated_vehicle_km.gt(0)].copy()
    injury=accidents[accidents.urban_rural.eq('Rural')&accidents.meidsli.isin([1,2,3])].copy()
    injury['year']=pd.to_datetime(injury.timestamp).dt.year
    injury['road_section']=injury.registered_road_section
    linked=injury.merge(x[['year','road_section','road_number']],on=['year','road_section'],how='left',validate='many_to_one')
    # Only accidents in exposed section-years enter this descriptive rate.
    count=linked.dropna(subset=['road_number']).groupby('road_number').size().rename('accidents')
    roads=x.groupby('road_number').agg(estimated_vehicle_km=('estimated_vehicle_km','sum'),
        section_years=('year','size'),years=('year','nunique'),unmapped_vehicle_km=('unmapped_vehicle_km','sum'))
    roads=roads.join(count).fillna({'accidents':0})
    roads['accidents']=roads.accidents.astype(int)
    roads['rate_per_million_vkt']=roads.accidents/roads.estimated_vehicle_km*1e6
    return roads.sort_values('rate_per_million_vkt',ascending=False).reset_index(),linked



def road_names(path):
    """Use only unique nonempty official names, without guessing conflicts."""
    features = json.loads(Path(path).read_text())['features']
    candidates = {}
    for feature in features:
        p = feature['properties']
        number, name = p.get('NUMVEGUR'), p.get('KAFLIVEGURHEITI')
        if number is not None and name:
            candidates.setdefault(str(number), set()).add(name)
    return {number: next(iter(names)) for number, names in candidates.items() if len(names) == 1}


def main():
    AUDIT.mkdir(parents=True,exist_ok=True);TEX.mkdir(parents=True,exist_ok=True)
    all_events=pd.read_csv('data/analysis/revision_accidents.csv',low_memory=False)
    exposure=pd.read_csv('data/analysis/rural_annual_exposure.csv',low_memory=False)
    urban=[]
    for area,part in all_events.groupby('urban_rural',dropna=False):
        injury=part.meidsli.isin([1,2,3]);severe=part.meidsli.isin([1,2])
        urban.append(dict(area=area,total=len(part),injury=int(injury.sum()),severe=int(severe.sum()),injury_share=injury.mean(),severe_share_among_injury=severe.sum()/injury.sum() if injury.any() else np.nan))
    pd.DataFrame(urban).to_csv(AUDIT/'urban_rural_severity.csv',index=False)
    seasons=seasonal_summary(all_events,exposure)
    seasons.to_csv(AUDIT/'rural_seasonal_rates.csv')
    ratio=seasons.loc['Winter',['accidents_per_million_vkt','minor_per_million_vkt','severe_per_million_vkt']]/seasons.loc['Summer',['accidents_per_million_vkt','minor_per_million_vkt','severe_per_million_vkt']]
    winter, summer = seasons.loc['Winter'], seasons.loc['Summer']
    ratios = pd.DataFrame({'outcome': ['All injury', 'Minor injury', 'Serious or fatal injury'],
        'winter_summer_rate_ratio': ratio.to_numpy()})
    ratios.to_csv(AUDIT/'rural_seasonal_contrasts.csv', index=False)
    sensitivity = (winter.accidents / summer.accidents *
        (summer.estimated_vehicle_km + summer.unmapped_vehicle_km) /
        (winter.estimated_vehicle_km + winter.unmapped_vehicle_km))
    pd.DataFrame([{'mapped_only_ratio': ratio.iloc[0], 'all_unmapped_rural_ratio': sensitivity,
        'summer_winter_severe_share_ratio': summer.severe_proportion / winter.severe_proportion}]).to_csv(
        AUDIT/'rural_seasonal_sensitivity.csv', index=False)
    exposure[['year','road_section','chainage_basis','period','rural_section_length_km',
        'unmapped_section_length_km','eligible']].to_csv(AUDIT/'rural_mapping_audit.csv', index=False)
    print('SEASONS',seasons.to_string(), '\nRATIOS',ratio.to_dict())
    write_table(TEX/'rural_seasonal_rates.tex',
        'Descriptive rural injury accidents and estimated seasonal travel, 2007--2025. Winter or summer average daily traffic is multiplied by mapped rural road length and calendar days. Unmapped portions are excluded.',
        'tab:rural-seasonal-rates','lrr',['Quantity','Winter','Summer'],[
            ['Injury accidents',*[f'{int(seasons.loc[p,"accidents"]):,}' for p in ['Winter','Summer']]],
            ['Serious or fatal injury accidents',*[f'{int(seasons.loc[p,"severe"]):,}' for p in ['Winter','Summer']]],
            ['Estimated driving (billion vehicle-km)',*[f'{seasons.loc[p,"estimated_vehicle_km"]/1e9:.2f}' for p in ['Winter','Summer']]],
            ['Injury accidents per million estimated vehicle-km',*[f'{seasons.loc[p,"accidents_per_million_vkt"]:.3f}' for p in ['Winter','Summer']]]],short_caption='Rural winter and summer counts and estimated travel.')
    roads,linked=road_rates(all_events,exposure)
    names = road_names('data/raw/traffic/reference/roads.geojson')
    roads['road_name'] = roads.road_number.astype(str).map(names)
    display = roads[roads.accidents.ge(20)].head(10)
    if display.road_name.isna().any():
        raise ValueError('Displayed road names must be unambiguous in the official geometry')
    display[['road_number','road_name']].assign(source='roads.geojson: NUMVEGUR / KAFLIVEGURHEITI').to_csv(AUDIT/'road_name_audit.csv', index=False)
    roads.to_csv(AUDIT/'road_injury_rates_unfiltered.csv',index=False)
    linked.to_csv(AUDIT/'road_rate_accident_linkage.csv',index=False)
    exposure.groupby('period').agg(section_years=('eligible','size'),eligible=('eligible','sum'),vkt=('estimated_vehicle_km','sum'),unmapped_vkt=('unmapped_vehicle_km','sum')).to_csv(AUDIT/'rural_exposure_audit.csv')
    print('ROAD TOP',roads.head(12).to_string(index=False));print('ROAD numerator',linked.road_number.notna().sum(),'/',len(linked))
    # The unfiltered ranking is sparse; make the proposed display restriction explicit.
    write_table(TEX/'road_rates.tex',
        'Highest estimated injury-accident rates among roads with at least 20 linked injury accidents, 2007--2025; the complete unfiltered ranking is retained as an audit CSV. Counts include only injury accidents linked to exposed road-section years. Exposure uses annual average daily traffic, mapped rural length and calendar days. Small counts and uncertain road linkage make this a descriptive ranking.',
        'tab:road-rates',r'rL{0.24\textwidth}rrr',['Road', 'Road name','Injury accidents',r'\shortstack{Million estimated\\vehicle-km}',r'\shortstack{Accidents per million\\estimated vehicle-km}'],
        [[int(r.road_number),r.road_name,r.accidents,f'{r.estimated_vehicle_km/1e6:.2f}',f'{r.rate_per_million_vkt:.3f}'] for r in display.itertuples()],short_caption='Highest estimated rates among roads with at least 20 linked injury accidents.')
    events=pd.read_csv('data/analysis/accidents.csv').merge(pd.read_csv('data/analysis/accident_conditions.csv'),on='id',validate='one_to_one')
    eligible=(events.weather_station_dist_km.le(20)&events.weather_time_difference_minutes.le(5)&events.temp_distance_km.le(20)&events.temp_time_diff_min.le(5)&events.f.notna()&events.temperature_c.between(-30,30))
    events=events[eligible].copy()
    if not events.weather_station_id.eq(events.temp_station_id).all(): raise ValueError('Joint events require the same station')
    if not events.weather_time_difference_minutes.eq(events.temp_time_diff_min).all():
        raise ValueError('Joint events have inconsistent observation timing')
    result,groups=joint_oe(events,pd.read_csv('data/analysis/joint_weather_frequency.csv'))
    result.to_csv(AUDIT/'joint_wind_temperature_oe.csv',index=False);groups.to_csv(AUDIT/'joint_station_season_audit.csv',index=False)
    names=[['$<15$','$<3$'],['$<15$',r'$\geq3$'],[r'$\geq15$','$<3$'],[r'$\geq15$',r'$\geq3$']]
    write_table(TEX/'joint_weather_oe.tex',
        'Joint wind and temperature O/E analysis. Expected counts use simultaneous valid wind and temperature observations within station--season groups; the four categories partition the eligible sample.',
        'tab:joint-weather-oe','llrrr',['Mean wind (m/s)',r'Temperature ($^{\circ}$C)','Observed','Expected','O/E'],
        [[*names[r.category],int(r.observed_accidents),f'{r.expected_accidents:.2f}',f'{r.oe:.2f}'] for r in result.itertuples()],short_caption='Joint wind and temperature O/E analysis.')
    print('JOINT',result.to_string(index=False))
    # Diagnostic: each eligible primary accident weights its local station-season
    # strong-wind frequency once. Same period and primary matching for both groups.
    sample=events[pd.to_datetime(events.timestamp).dt.year.between(2019,2024)].copy()
    retained=set(pd.read_csv('data/analysis/vkt_accidents.csv').id)
    sample['counter_linked']=sample.id.isin(retained)
    f=pd.read_csv('data/analysis/weather_frequency.csv');f=f[f.variable.eq('f')]
    f['strong']=f.bin_label.isin(['15-20','20-25','>=25','>=20'])
    freq=f[f.strong].groupby(['station','season']).frequency_pct.sum().rename('strong_wind_frequency_pct')
    sample=sample.join(freq,on=['weather_station_id','season'])
    diagnostic=sample.groupby('counter_linked').agg(accidents=('id','size'),mean_local_strong_wind_frequency_pct=('strong_wind_frequency_pct','mean'))
    diagnostic.to_csv(AUDIT/'counter_wind_composition.csv');print('COUNTER',diagnostic.to_string())

if __name__=='__main__': main()
