"""Scientific invariants for the retained thesis additions."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.prepare_revision import joint_category
from src.tables.revision import joint_oe, seasonal_summary, road_rates
from src.tables.headline_summary import relative_contrasts
from src.traffic.monthly_vkt import allocate_monthly_exposure, _bin_values


def test_joint_boundaries_and_correlated_background_are_not_marginal_products():
    assert joint_category([14,14,15,15],[2,3,2,3]).tolist()==[0,1,2,3]
    # Correlated weather: products of the marginals would give 25% per cell.
    frequency=pd.DataFrame({'weather_station_id':[1]*4,'season':['Winter']*4,
        'category':range(4),'frequency':[.4,.1,.1,.4]})
    events=pd.DataFrame({'id':range(10),'weather_station_id':[1]*10,'season':['Winter']*10,
        'f':[0]*5+[20]*5,'temperature_c':[0]*5+[10]*5})
    result,cells=joint_oe(events,frequency)
    np.testing.assert_allclose(result.expected_accidents,[4,1,1,4])
    assert result.observed_accidents.tolist()==[5,0,0,5]
    assert cells.expected_accidents.sum()==len(events)
    with pytest.raises(ValueError,match='conserve'):
        joint_oe(events,frequency.assign(frequency=.1))


def test_temperature_negative_and_exact_boundaries():
    bins=_bin_values(pd.Series([-20,-6,-3,0,3,6,9,12,20,np.nan]),'temperature')
    assert list(bins[:-1])==['<-6','-6--3','-3-0','0-3','3-6','6-9','9-12','>=12','>=12']
    assert pd.isna(bins.iloc[-1])


def test_temperature_allocation_conserves_each_day_including_no_accident_days():
    labels=['<-6','-6--3','-3-0','0-3','3-6','6-9','9-12','>=12']
    days=pd.DataFrame({'date':['2020-01-01','2020-01-02','2020-01-03'],'year':[2020]*3,
        'season':['Winter']*3,'month':[1]*3,'counter_section_id':['a']*3,
        'weather_station_id':[1]*3,'traffic_vehicles':[100,200,0],
        'rural_section_length_km':[2.]*3,'vehicle_km':[200.,400.,0.]})
    freq=pd.DataFrame({'weather_station_id':[1]*8,'month':[1]*8,'variable':['temperature']*8,
        'bin_label':labels,'bin_order':range(8),'frequency':[.05,.05,.1,.1,.2,.2,.2,.1],
        'first_year':[2007]*8,'last_year':[2025]*8,'start_hour':[7]*8,'end_hour':[24]*8})
    result=allocate_monthly_exposure(days,freq,'temperature')
    np.testing.assert_allclose(result.groupby('date').estimated_vehicle_km.sum(),[200,400,0])
    assert result.counter_day_key.nunique()==3


def test_seasonal_rate_and_severity_have_distinct_denominators():
    events=pd.DataFrame({'urban_rural':['Rural']*5,'meidsli':[3,1,3,3,2],
        'timestamp':['2020-01-01']*2+['2020-06-01']*3})
    exposure=pd.DataFrame({'period':['Winter','Summer'],'estimated_vehicle_km':[10.,30.],'unmapped_vehicle_km':[0.,0.]})
    result=seasonal_summary(events,exposure)
    assert result.loc['Winter','severe_proportion']==.5
    assert result.loc['Summer','severe_proportion']==pytest.approx(1/3)
    assert result.loc['Winter','accidents_per_million_vkt']/result.loc['Summer','accidents_per_million_vkt']==2


def test_road_rates_exclude_unlinked_events_and_keep_zero_accident_roads():
    events=pd.DataFrame({'id':[1,2,3],'urban_rural':['Rural']*3,'meidsli':[3]*3,
        'timestamp':['2020-01-01']*3,'registered_road_section':['1-a','1-a','9-z']})
    exposure=pd.DataFrame({'period':['All year']*3,'year':[2020]*3,'road_section':['1-a','1-b','2-a'],
        'road_number':[1,1,2],'estimated_vehicle_km':[100.,900.,1000.],'unmapped_vehicle_km':[0.]*3})
    rates,linked=road_rates(events,exposure)
    assert rates.accidents.tolist()==[2,0]
    assert rates.rate_per_million_vkt.tolist()==[2000.,0.]
    assert linked.road_number.isna().sum()==1


def test_relative_contrasts_use_actual_reference_not_one():
    rows=[]
    for variable,high in [('f','>=20'),('fg','>=30')]:
        for label,value in [('0-5',.5),(high,2.)]:
            rows.append(dict(variable=variable,outcome='All injury accidents',period='All year',bin_label=label,
                             relative_accident_frequency=value,traffic_corrected_oe=value*2,rate_per_million_vehicle_km=value/10))
    data=pd.DataFrame(rows)
    result=relative_contrasts(data,data,data)
    np.testing.assert_allclose(result.relative_contrast,4.)


def test_real_joint_and_seasonal_counts():
    path=Path('reports/working/tables/joint_wind_temperature_oe.csv')
    if not path.exists():pytest.skip('local revision outputs unavailable')
    joint=pd.read_csv(path)
    assert joint.observed_accidents.sum()==6259
    assert joint.expected_accidents.sum()==pytest.approx(6259)
    seasons=pd.read_csv('reports/working/tables/rural_seasonal_rates.csv').set_index('period')
    assert seasons.loc['Summer',['minor','severe','accidents']].tolist()==[1717,670,2387]
    assert seasons.loc['Winter',['minor','severe','accidents']].tolist()==[1699,384,2083]
    ratio=seasons.loc['Winter','accidents_per_million_vkt']/seasons.loc['Summer','accidents_per_million_vkt']
    assert round(ratio,2)==1.92
    assert round(seasons.loc['Winter','estimated_vehicle_km']/1e9,2)==6.32
    assert round(seasons.loc['Summer','estimated_vehicle_km']/1e9,2)==13.89
    for outcome, expected in [('minor',2.17),('severe',1.26)]:
        assert round(seasons.loc['Winter',outcome+'_per_million_vkt']/seasons.loc['Summer',outcome+'_per_million_vkt'],2)==expected
    sensitivity=(seasons.loc['Winter','accidents']/seasons.loc['Summer','accidents'] *
        (seasons.loc['Summer','estimated_vehicle_km']+seasons.loc['Summer','unmapped_vehicle_km']) /
        (seasons.loc['Winter','estimated_vehicle_km']+seasons.loc['Winter','unmapped_vehicle_km']))
    assert round(sensitivity,2)==1.91


def test_thesis_grid_and_tick_style_preserves_labels_and_values():
    import matplotlib.pyplot as plt
    from src.figures.thesis_style import style_figure
    fig,ax=plt.subplots()
    try:
        ax.bar([2007,2008],[4,5]);ax.set_xticks([2007,2008]);ax.grid(axis='y')
        style_figure(fig)
        assert [p.get_height() for p in ax.patches]==[4,5]
        assert [t.get_text() for t in ax.get_xticklabels()]==['2007','2008']
        assert all(l.get_linewidth()==1 for l in ax.get_ygridlines())
        assert all(t.tick1line.get_markersize()==0 for t in ax.xaxis.get_major_ticks()+ax.yaxis.get_major_ticks())
    finally:plt.close(fig)


def test_missing_2007_chainage_uses_documented_origin_and_preserves_length():
    from src.prepare_revision import resolve_chainage
    data=pd.DataFrame({'year':[2006,2007,2008],'road_section':['1-a']*3,
        'section_start_name':['Known junction']*3,
        'section_start_station_km':[3.,np.nan,3.],
        'section_end_station_km':[7.,np.nan,8.], 'section_length_km':[4.,4.5,5.]})
    result=resolve_chainage(data)
    assert result.loc[1,'section_start_station_km']==3
    assert result.loc[1,'section_end_station_km']==7.5
    assert result.loc[1,'chainage_basis']=='same section and start name: 2006,2008'
    data.loc[2,'section_start_station_km']=4
    result=resolve_chainage(data)
    assert pd.isna(result.loc[1,'section_start_station_km'])
    assert result.loc[1,'chainage_basis']=='unresolved'
