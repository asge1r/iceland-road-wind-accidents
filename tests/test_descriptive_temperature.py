"""The descriptive figure shares the retained temperature bins and population."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.tables.conditions import build_tables, TEMPERATURE_LABELS
from src.weather.frequency import OE_TEMPERATURE_LABELS


def test_descriptive_boundaries_combine_upper_tail_and_preserve_severity():
    temperatures=[-7,-6,-3,0,3,6,9,12,15,20,np.nan]
    events=pd.DataFrame({'id':range(11),'year':2020,'hour':12,'season':'Summer',
                         'traffic_period':'SDU','meidsli':[3,1,3,2,3,1,3,2,3,1,3]})
    conditions=pd.DataFrame({'id':range(11),'temperature_c':temperatures,
                            'solar_elevation_deg':30.,'daylight_class':'Daylight'})
    result,_=build_tables(events,conditions)
    temp=result[result.dimension.eq('temperature_interval_c')].set_index('category')
    assert temp.index.tolist()==OE_TEMPERATURE_LABELS==TEMPERATURE_LABELS
    assert temp.accidents.tolist()==[1,1,1,1,1,1,1,3]
    assert temp.loc['>=12',['minor_injury','serious_or_fatal']].tolist()==[1,2]
    assert temp.accidents.eq(temp.minor_injury+temp.serious_or_fatal).all()
    for dimension in ['hour','season','daylight_class']:
        assert result[result.dimension.eq(dimension)].accidents.sum()==11


def test_current_descriptive_temperature_matches_retained_population():
    source=Path('data/analysis/accidents.csv')
    if not source.exists():pytest.skip('Local inputs unavailable')
    events=pd.read_csv(source)
    conditions=pd.read_csv('data/analysis/accident_conditions.csv')
    result,_=build_tables(events,conditions)
    temp=result[result.dimension.eq('temperature_interval_c')].set_index('category')
    assert temp.accidents.sum()==6259
    assert temp.loc['>=12',['accidents','minor_injury','serious_or_fatal']].tolist()==[789,563,226]
    assert temp.accidents.eq(temp.minor_injury+temp.serious_or_fatal).all()
    merged=events.merge(conditions,on='id',validate='one_to_one')
    high=merged[merged.temperature_c.ge(12)]
    assert len(high)==789
    assert high.meidsli.le(2).sum()==226


def test_requested_table_locations_and_natural_numbering():
    text=Path('reports/thesis/content.tex').read_text()
    all_year=text.split(r'\subsection{All year rates}',1)[1].split(r'\subsection{Mean wind by season}',1)[0]
    comparison=text.split(r'\subsection{Comparison with traffic-corrected O/E}',1)[1].split(r'\subsection{Descriptive full-period',1)[0]
    assert text.count(r'\input{generated/monthly_vkt_rate.tex}')==1
    assert r'\setcounter{table}' not in text
    assert all_year.index('monthly_vkt_rate.tex')<all_year.index('monthly_weather_rate_annual.pdf')
    assert 'evidence.tex' in comparison
    assert text.index('monthly_vkt_rate.tex') < text.index('evidence.tex')
