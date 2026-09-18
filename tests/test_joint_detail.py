"""Joint bins, shared observations, station-season standardisation and audits."""
import re
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.tables.joint_detail import atomic_category, display_category, coarse_category, calculate, contrasts
from src.prepare_revision import joint_category


def test_fixed_boundaries_and_exact_coarse_partition():
    wind,temp=np.meshgrid([0,4.999,5,10,14.999,15,44],[-30,-3.001,-3,-.001,0,2.999,3,5.999,6,11.999,12,30])
    atom=atomic_category(wind.ravel(),temp.ravel())
    assert set(atom)==set(range(24))
    assert set(display_category(atom))==set(range(20))
    np.testing.assert_array_equal(coarse_category(atom),joint_category(wind.ravel(),temp.ravel()))
    assert display_category(atomic_category([5]*5,[-3,0,3,6,12])).tolist()==[6,7,7,8,9]
    with pytest.raises(ValueError):atomic_category([np.nan],[0])
    with pytest.raises(ValueError):atomic_category([-1],[0])


def fixture_data():
    # Two different station-season distributions; one event at each atomic cell.
    weather=pd.DataFrame({'weather_station_id':np.repeat([1,2],24),'season':'Winter',
                          'atomic_cell':list(range(24))*2,
                          'frequency':np.r_[np.arange(1,25)/300,np.arange(24,0,-1)/300]})
    wind=np.repeat([1,7,12,18],6);temp=np.tile([-5,-1,1,4,8,15],4)
    events=pd.DataFrame({'id':range(48),'weather_station_id':np.repeat([1,2],24),
                         'season':'Winter','f':np.tile(wind,2),'temperature_c':np.tile(temp,2)})
    return events,weather


def test_joint_expectations_sum_frequencies_not_ratios_or_marginals():
    events,frequency=fixture_data()
    result,atomic,background=calculate(events,frequency)
    assert len(result)==20 and len(atomic)==24
    assert result.observed_accidents.sum()==48
    assert result.expected_accidents.sum()==pytest.approx(48)
    np.testing.assert_allclose(atomic.expected_accidents,2)
    assert result.query('temperature_order==2').observed_accidents.tolist()==[4]*4
    assert result.sample_percent.sum()==pytest.approx(100)
    expected=background.expected_accidents.groupby(background.atomic_cell).sum()
    np.testing.assert_allclose(atomic.expected_accidents,expected)
    broken=frequency.copy();broken.loc[0,'frequency']+=.1
    with pytest.raises(ValueError,match='conserve'):calculate(events,broken)
    with pytest.raises(ValueError,match='Missing'):calculate(events,frequency.iloc[1:])
    with pytest.raises(ValueError,match='Duplicate'):calculate(pd.concat([events,events.iloc[:1]]),frequency)


def test_merged_zero_to_six_cannot_determine_legacy_three_degree_split():
    events,frequency=fixture_data()
    a=events.iloc[[2]].copy();b=a.assign(temperature_c=4)
    da,aa,_=calculate(a,frequency);db,ab,_=calculate(b,frequency)
    np.testing.assert_array_equal(da.observed_accidents,db.observed_accidents)
    assert not np.array_equal(aa.groupby('coarse_cell').observed_accidents.sum(),ab.groupby('coarse_cell').observed_accidents.sum())


def test_sparse_rule_and_contrasts_require_both_cells():
    events,frequency=fixture_data();result,_,_=calculate(events,frequency)
    supported=result.assign(observed_accidents=10,expected_accidents=5.,oe=2.,sparse=False)
    supported.loc[supported.cell.eq(15),'sparse']=True
    c=contrasts(supported)
    assert len(c)==13
    assert c.query("contrast=='High/low wind' and group=='<−3'").oe_ratio.isna().all()
    assert c[c.adequate_support].oe_ratio.eq(1).all()
    assert result['sparse'].all()


def test_fine_joint_grid_uses_joint_station_season_frequencies():
    from src.tables.joint_grid import calculate
    events=pd.DataFrame({'id':[1,2],'weather_station_id':[1,2],
                         'season':['Winter','Winter'],'f':[2.,21.],
                         'temperature_c':[-7.,13.]})
    frequency=pd.DataFrame([(station,'Winter',cell,weight)
                            for station,weights in ((1,{0:.25,10:.75}),
                                                    (2,{0:.5,39:.5}))
                            for cell in range(40)
                            for weight in [weights.get(cell,0.)]],
                           columns=['weather_station_id','season','cell','frequency'])
    result=calculate(events,frequency).set_index('cell')
    assert result.observed_accidents.sum()==2
    assert result.expected_accidents.sum()==pytest.approx(2)
    assert result.loc[0,'expected_accidents']==pytest.approx(.75)
    assert result.loc[10,'expected_accidents']==pytest.approx(.75)
    assert result.loc[39,'expected_accidents']==pytest.approx(.5)
    assert result.loc[39,'oe']==pytest.approx(2)


def test_thesis_citations_resolve_and_no_entries_unused():
    text=Path('reports/thesis/content.tex').read_text()+Path('reports/thesis/draft_en.tex').read_text()
    for path in Path('reports/thesis/generated').glob('*.tex'):
        if str(path.relative_to('reports/thesis')) in text:text+='\n'+path.read_text()
    cited={k.strip() for group in re.findall(r'\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}',text) for k in group.split(',')}
    entries=re.findall(r'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}',text)
    assert len(entries)==len(set(entries))
    assert cited==set(entries)
    assert re.search(r'\\bibitem\[ITA\(2026a\)\]',text)
    assert 'zhan2020' in cited
    assert 'ahmed2012' not in entries and 'itaReport2014' not in entries


def test_real_joint_outputs_conserve_and_reproduce_coarse():
    p=Path('reports/main/tables/joint_wind_temperature_detail.csv')
    audit=Path('reports/working/tables')
    if not p.exists() or not (audit/'joint_atomic_oe.csv').exists() or not (audit/'joint_wind_temperature_oe.csv').exists():
        pytest.skip('Full joint outputs not available locally')
    detail=pd.read_csv(p);atom=pd.read_csv('reports/working/tables/joint_atomic_oe.csv')
    old=pd.read_csv('reports/working/tables/joint_wind_temperature_oe.csv')
    assert len(detail)==20 and detail.observed_accidents.sum()==6259
    assert detail.expected_accidents.sum()==pytest.approx(6259)
    assert detail['sparse'].equals(detail.observed_accidents.lt(10)|detail.expected_accidents.lt(5))
    grouped=atom.groupby('coarse_cell')[['observed_accidents','expected_accidents']].sum()
    np.testing.assert_array_equal(grouped.observed_accidents,old.observed_accidents)
    np.testing.assert_allclose(grouped.expected_accidents,old.expected_accidents,rtol=0,atol=1e-8)
    np.testing.assert_allclose(detail.oe,detail.observed_accidents/detail.expected_accidents)


def test_heatmap_annotations_and_generated_interpretation_match_values():
    p=Path('reports/main/tables/joint_wind_temperature_5x8.csv')
    if not p.exists():pytest.skip('Local 5x8 joint output unavailable')
    from src.figures.joint_detail import make_figure,narrative
    from src.tables.joint_grid import category,check_previous_partition
    import matplotlib.pyplot as plt
    d=pd.read_csv(p);fig=make_figure(d)
    try:
        labels=[t.get_text() for t in fig.axes[0].texts]
        assert len(labels)==54
        for row,label in zip(d.sort_values('cell').itertuples(),labels[:40]):
            assert label==f'{row.oe:.2f}'+('*' if row.sparse else '')+f'\nn={row.observed_accidents}'.replace('\\n','\n')
        for labels_slice,group_column in ((labels[40:45],'wind_order'),(labels[45:53],'temperature_order')):
            for label,(_,group) in zip(labels_slice,d.groupby(group_column)):
                observed=int(group.observed_accidents.sum())
                expected=group.expected_accidents.sum()
                assert label==f'{observed/expected:.2f}\nn={observed}'
        assert labels[-1]=='1.00\nn=6259'
        assert len(fig.axes[0].patches)==58  # 54 cells and four black block outlines
        assert all(p.get_edgecolor()[:3]==(0,0,0) for p in fig.axes[0].patches[-4:])
        assert all(t.get_fontsize()==8 for t in fig.axes[0].texts)
        assert fig.axes[1]._colorbar.mappable.norm(1)==pytest.approx(np.log(1/.62)/np.log(7.63/.62))
        assert fig.get_size_inches()[0]*25.4==pytest.approx(190)
        assert fig.axes[1].get_position().width*190==pytest.approx(8)
        assert [t.get_text() for t in fig.axes[0].get_xticklabels()]==[
            '<−6','[−6, −3]','[−3, 0]','[0, 3]','[3, 6]',
            '[6, 9]','[9, 12]','≥12','All\ntemperatures']
    finally:plt.close(fig)
    assert category([0,4.999,5,19.999,20],[-7,-6,-3,11.999,12]).tolist()==[0,1,10,30,39]
    check_previous_partition(d)
    text,discussion=narrative(d)
    assert '0.93' in text and '2.06' in text and '7.63' in text
    assert '2 observed accidents versus 0.26 expected' in text
    assert 'do not establish interaction' in discussion
    if Path('reports/working/tables/joint_atomic_oe.csv').exists():
        from src.validation.joint_detail import validate_joint_products
        assert validate_joint_products()['sparse_cells']==1


def test_semantic_float_order_and_future_work_length():
    t=Path('reports/thesis/content.tex').read_text()
    labels=['sec:joint-weather','fig:joint-weather-detail','fig:traffic-response',
            'fig:traffic-corrected-wind','fig:traffic-corrected-gust','fig:corrected-injury-groups',
            'sec:temperature-corrected','fig:traffic-corrected-temperature','sec:monthly-vkt-results']
    positions=[t.index(r'\label{'+s+'}') for s in labels]
    assert positions==sorted(positions)
    assert r'\FloatBarrier' in t[t.index(r'\label{fig:traffic-corrected-temperature}'):t.index(r'\label{sec:monthly-vkt-results}')]
    future=t.split(r'\section{Future work}',1)[1].split(r'\chapter{Conclusion}',1)[0]
    # Targeted register and subgroup additions extend the previous 500–650-word section.
    assert 500<=len(future.split())<=850
    assert 'generated/joint_weather_oe.tex' not in t


def test_simultaneous_check_rejects_opposite_time_ties(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from src.tables.joint_detail import verify_simultaneous_records
    events=pd.DataFrame({'id':[1],'weather_station_id':[9],'timestamp':['2020-01-01 12:05:00'],
                         'weather_time_difference_minutes':[5.],'f':[2.],'fg':[4.],'temperature_c':[8.]})
    path=tmp_path/'weather.parquet'
    def write(temps):
        pq.write_table(pa.table({'station':pa.array([9,9],type=pa.int32()),
          'time':pa.array(np.array(['2020-01-01T12:00','2020-01-01T12:10'],dtype='datetime64[us]')),
          'f':pa.array([2.,3.],type=pa.float32()),'fg':pa.array([4.,5.],type=pa.float32()),
          't':pa.array(temps,type=pa.float32())}),path)
    write([1.,8.])
    with pytest.raises(ValueError,match='simultaneous'):verify_simultaneous_records(events,path)
    write([8.,1.])
    result=verify_simultaneous_records(events,path)
    assert len(result)==1 and result.iloc[0].weather_time==pd.Timestamp('2020-01-01 12:00')
