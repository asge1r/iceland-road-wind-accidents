"""Validate saved detailed joint products without rereading the weather archive."""
from pathlib import Path
import numpy as np
import pandas as pd
from src.tables.joint_detail import contrasts


def validate_joint_products(root=Path('.')):
    tables=root/'reports/main/tables';audit=root/'reports/working/tables'
    d=pd.read_csv(tables/'joint_wind_temperature_detail.csv').sort_values('cell')
    a=pd.read_csv(audit/'joint_atomic_oe.csv')
    old=pd.read_csv(audit/'joint_wind_temperature_oe.csv').sort_values('category')
    if d.cell.tolist()!=list(range(20)):raise ValueError('Joint display cells incomplete')
    if a.atomic_cell.tolist()!=list(range(24)):raise ValueError('Atomic cells incomplete')
    if d.observed_accidents.sum()!=6259:raise ValueError('Joint eligible count changed')
    if not np.isclose(d.expected_accidents.sum(),6259,rtol=0,atol=1e-8):raise ValueError('Expected counts not conserved')
    np.testing.assert_allclose(d.oe,d.observed_accidents/d.expected_accidents,rtol=0,atol=1e-12)
    np.testing.assert_allclose(d.sample_percent,d.observed_accidents/6259*100,rtol=0,atol=1e-12)
    if not d['sparse'].equals(d.observed_accidents.lt(10)|d.expected_accidents.lt(5)):raise ValueError('Sparse flags differ')
    for group,expected in [('cell',d),('coarse_cell',old)]:
        sums=a.groupby(group)[['observed_accidents','expected_accidents']].sum()
        np.testing.assert_array_equal(sums.observed_accidents,expected.observed_accidents)
        np.testing.assert_allclose(sums.expected_accidents,expected.expected_accidents,rtol=0,atol=1e-8)
    actual=pd.read_csv(tables/'joint_wind_temperature_contrasts.csv')
    pd.testing.assert_frame_equal(actual,contrasts(d),check_exact=False,rtol=0,atol=1e-12)
    matches=pd.read_csv(audit/'joint_simultaneous_events.csv')
    if len(matches)!=6259 or matches.id.nunique()!=6259:
        raise ValueError('Simultaneous archive audit is incomplete')
    for left,right in [('f_event','f_archive'),('fg_event','fg_archive'),('temperature_c','t')]:
        np.testing.assert_array_equal(matches[left].to_numpy(dtype='float32'),matches[right].to_numpy(dtype='float32'))
    return {'cells':20,'eligible_accidents':6259,'sparse_cells':int(d['sparse'].sum())}
