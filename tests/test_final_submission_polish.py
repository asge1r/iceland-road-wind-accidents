"""Guard exact source excerpts, the current workflow and retained VKT validation."""
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.tables import exact_data, pipeline
from src.validation.traffic import validate_monthly_vkt


def test_exact_csv_preserves_all_columns_order_strings_and_escaping(tmp_path):
    path = tmp_path/'cleaned.csv'
    records = [['id', 'empty', 'numeric', 'a_b', 'text'],
               ['0003', '', '1.23000000000000001', 'a&b', 'x%_{y}'],
               ['0001', 'NA', '-0.000', 'c#d', 'unchanged'],
               ['0002', '', '9', 'later', 'third row']]
    with path.open('w', newline='') as stream:
        csv.writer(stream).writerows(records)
    headers, rows = exact_data.csv_excerpt(path)
    assert headers == records[0]
    assert rows == records[1:3]
    rendered = exact_data.render_table(headers, rows, 'Caption', 'Short', 'tab:test')
    for value in [*headers, *rows[0], *rows[1]]:
        assert r'\texttt{'+exact_data.escape(value)+'}' in rendered
    assert 'third row' not in rendered
    assert rendered.count(r'\begin{tabular}') == 1


def test_exact_parquet_float32_shortest_round_trip(tmp_path):
    path = tmp_path/'weather.parquet'
    table = pa.table({'station':pa.array([9,8,7], type=pa.int32()),
                      'f':pa.array([7.28,7.13,1.], type=pa.float32()),
                      'name':['a','b','c']})
    pq.write_table(table,path)
    headers,rows=exact_data.parquet_excerpt(path)
    assert headers == table.column_names
    expected=table.column('f').to_numpy()
    assert [row[0] for row in rows] == ['9','8']
    assert [row[1] for row in rows] == ['7.28','7.13']
    assert [row[2] for row in rows] == ['a','b']
    for actual,source in zip(rows,expected[:2]):
        assert np.float32(actual[1]).tobytes() == source.tobytes()


@pytest.mark.parametrize('dtype',[np.float32,np.float64])
def test_shortest_float_preserves_original_dtype_bits(dtype):
    values=[dtype(7.28),dtype(-0.),dtype(.1),np.nextafter(dtype(0),dtype(1)),
            np.finfo(dtype).max,np.nextafter(dtype(1),dtype(2)),dtype(-1e-20)]
    for value in values:
        text=exact_data.shortest_float(value)
        assert dtype(text).tobytes()==value.tobytes()
    # Widening float32 first would incorrectly force a longer decimal.
    assert exact_data.shortest_float(np.float32(7.28))=='7.28'
    assert exact_data.shortest_float(np.float64(np.float32(7.28)))!='7.28'


def test_parquet_timestamps_omit_only_unnecessary_fractional_digits(tmp_path):
    stamps=np.array(['2011-06-01T20:30:00.000000','2011-06-01T20:40:00.000123'],dtype='datetime64[us]')
    path=tmp_path/'times.parquet'
    pq.write_table(pa.table({'time':pa.array(stamps)}),path)
    headers,rows=exact_data.parquet_excerpt(path)
    assert headers==['time']
    assert rows==[['2011-06-01T20:30:00'],['2011-06-01T20:40:00.000123']]
    for row,original in zip(rows,stamps):
        assert np.datetime64(row[0],'us').tobytes()==original.tobytes()


def test_local_exact_excerpts_match_cleaned_sources_in_full(tmp_path):
    if not exact_data.ACCIDENTS.exists() or not exact_data.WEATHER.exists():
        pytest.skip('Local cleaned sources unavailable')
    output,audit=tmp_path/'exact.tex',tmp_path/'exact.json'
    exact_data.generate(output=output,audit=audit)
    manifest=json.loads(audit.read_text())
    with exact_data.ACCIDENTS.open(newline='') as stream:
        source=csv.reader(stream)
        expected=[next(source) for _ in range(3)]
    assert manifest['accidents']['headers']==expected[0]
    assert manifest['accidents']['rows']==expected[1:]
    source=pq.ParquetFile(exact_data.WEATHER)
    batch=next(source.iter_batches(batch_size=2))
    assert manifest['weather']['headers']==batch.schema.names
    for j,field in enumerate(batch.schema):
        column=batch.column(j)
        values=column.to_numpy(zero_copy_only=False)
        for i,value in enumerate(values):
            actual=manifest['weather']['rows'][i][j]
            if pa.types.is_floating(field.type):
                assert values.dtype.type(actual).tobytes()==value.tobytes()
            elif pa.types.is_timestamp(field.type):
                assert np.datetime64(actual,field.type.unit)==value
            else:
                assert actual==str(value)
    text=output.read_text()
    for kind in manifest.values():
        assert [i for a,b in kind['blocks'] for i in range(a,b)]==list(range(len(kind['headers'])))
        for header in kind['headers']:
            assert exact_data.header_cell(header) in text
        for value in [*kind['rows'][0],*kind['rows'][1]]:
            assert r'\texttt{'+exact_data.escape(value)+'}' in text
    assert manifest['accidents']['blocks']==[[0,5],[5,9]]
    assert manifest['weather']['blocks']==[[0,5]]
    assert 'landscape' not in text
    assert text.count(r'\begin{table}')==2
    assert text.count(r'\begin{tabular}')==3
    assert 'Same records, remaining columns.' in text
    assert r'\shortstack' not in text


def test_workflow_regenerates_current_summary_into_empty_directory(tmp_path):
    pipeline.generate(tmp_path)
    overview=(tmp_path/'pipeline_analysis.tex').read_text()
    figure=(tmp_path/'pipeline_prepare.tex').read_text()
    assert r'\begin{table}' not in overview
    assert figure.count(r'\node[stage')==5
    assert figure.count(r'\draw[->]')==4
    assert 'Run as:' not in figure and 'landscape' not in figure
    assert r'\label{fig:reproducible-workflow}' in figure
    for path in pipeline.SCRIPTS:
        assert Path(path).is_file()
        assert '__main__' in Path(path).read_text()
    for stage in ['Weather-frequency O/E','approximate traffic-corrected O/E','monthly-frequency VKT','validation']:
        assert stage in figure
    content=Path('reports/thesis/content.tex').read_text()
    assert 'tab:analysis-pipeline' not in content
    assert r'\label{sec:analysis}' in content
    from src.thesis_pipeline import MODULES
    assert 'src.tables.pipeline' in MODULES and 'src.tables.exact_data' in MODULES


@pytest.fixture
def vkt():
    from src.traffic.monthly_vkt import OUTCOMES, ALLOCATION_METHOD
    from src.weather.monthly_frequency import VARIABLES
    rows=[]
    for variable,(_,labels) in VARIABLES.items():
        for outcome in OUTCOMES:
            total={'All injury accidents':694,'Minor injury accidents':500,
                   'Serious or fatal injury accidents':194}[outcome]
            for i,label in enumerate(labels):
                count=total if i==0 else 0
                exposure=5630267210.07299/len(labels)
                rows.append(dict(variable=variable,outcome=outcome,bin_label=label,bin_order=i,
                                 observed_accidents=count,estimated_vehicle_km=exposure,
                                 rate_per_million_vehicle_km=count/exposure*1e6,
                                 counter_days=533649,counter_sections=1598,
                                 analysed_accidents=total,allocation_method=ALLOCATION_METHOD))
    return pd.DataFrame(rows)


def test_vkt_validator_accepts_temperature_and_complete_conserved_sample(vkt):
    assert set(validate_monthly_vkt(vkt).variable)=={'f','fg','temperature'}


@pytest.mark.parametrize('fault', ['missing_temperature','missing_outcome_bin','bad_bin_order',
    'counter_days','outcome_sample','rate','shared_denominator','unequal_total',
    'wrong_source_total','noninteger_count','severity_partition'])
def test_vkt_validator_rejects_broken_invariants(vkt,fault):
    if fault=='missing_temperature':
        vkt=vkt[vkt.variable.ne('temperature')].copy()
    elif fault=='missing_outcome_bin':
        vkt=vkt.drop(vkt.index[-1])
    elif fault=='bad_bin_order':
        vkt.loc[vkt.index[-1],'bin_order']=0
    elif fault=='counter_days':
        vkt.loc[0,'counter_days']-=1
    elif fault=='outcome_sample':
        vkt.loc[0,'analysed_accidents']-=1
    elif fault=='rate':
        vkt.loc[0,'rate_per_million_vehicle_km']+=.01
    elif fault=='shared_denominator':
        vkt.loc[0,'estimated_vehicle_km']*=1.1
    elif fault=='unequal_total':
        vkt.loc[vkt.variable.eq('temperature'),'estimated_vehicle_km']*=1.1
    elif fault=='wrong_source_total':
        vkt.estimated_vehicle_km*=1.1
    elif fault=='noninteger_count':
        vkt.observed_accidents=vkt.observed_accidents.astype(float)
        vkt.loc[0,'observed_accidents']+=.5
    elif fault=='severity_partition':
        # Preserve every outcome's total, but break the per-bin partition.
        mask=vkt.variable.eq('temperature') & vkt.outcome.eq('Minor injury accidents')
        indices=vkt[mask].index[:2]
        vkt.loc[indices,'observed_accidents']=[499,1]
    if fault!='rate':
        vkt.rate_per_million_vehicle_km=vkt.observed_accidents/vkt.estimated_vehicle_km*1e6
    with pytest.raises(ValueError):validate_monthly_vkt(vkt)


def test_road_names_only_use_unique_official_values(tmp_path):
    from src.tables.revision import road_names
    path=tmp_path/'roads.json'
    path.write_text(json.dumps({'features':[
        {'properties':{'NUMVEGUR':1,'KAFLIVEGURHEITI':'A'}},
        {'properties':{'NUMVEGUR':1,'KAFLIVEGURHEITI':'A'}},
        {'properties':{'NUMVEGUR':2,'KAFLIVEGURHEITI':'B'}},
        {'properties':{'NUMVEGUR':2,'KAFLIVEGURHEITI':'C'}}]}))
    assert road_names(path)=={'1':'A'}


def test_actual_temperature_plot_axes_use_square_brackets():
    import matplotlib.pyplot as plt
    from src.figures.oe_histo import draw_panel, OUTCOMES as OE_OUTCOMES
    from src.figures.weather_rate import draw, OUTCOMES as RATE_OUTCOMES, RATE
    labels=['<-6','-6--3','-3-0','0-3','3-6','6-9','9-12','>=12']
    expected=['<−6','[−6, −3]','[−3, 0]','[0, 3]','[3, 6]','[6, 9]','[9, 12]','≥12']
    figure,axes=plt.subplots(1,2)
    try:
        oe=pd.DataFrame([dict(variable='temperature',period='All year',outcome=outcome,
                             bin_label=label,bin_order=i,observed_accidents=2,
                             relative_accident_frequency=1.)
                         for outcome in OE_OUTCOMES for i,label in enumerate(labels)])
        rates=pd.DataFrame([dict(variable='temperature',period='All year',outcome=outcome,
                                bin_label=label,bin_order=i,accidents=2,
                                estimated_vehicle_km=2e6,**{RATE:1.})
                            for outcome in RATE_OUTCOMES for i,label in enumerate(labels)])
        draw_panel(axes[0],oe,'temperature','All year','All year')
        draw(axes[1],rates,'temperature','All year')
        for axis in axes:
            assert [label.get_text() for label in axis.get_xticklabels()]==expected
    finally:
        plt.close(figure)
