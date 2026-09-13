"""Regression tests for the pre-submission eligibility and coverage fixes."""
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.weather.eligibility import valid_temperature
from src.weather.frequency import accumulate, make_yearly_table, make_pooled_table
from src.traffic.counter_day_weather import aggregate_weather, distinct_slot_mask, EXPECTED_OBSERVATIONS
from src.analysis.oe_analysis import VARIABLES, station_frequency_scenario
from src.accidents.case_control import build_candidates, read_weather, assemble


class EligibilityTests(unittest.TestCase):
    def test_inclusive_domain_and_nonfinite(self):
        values = np.array([-30.0001, -30, 30, 30.0001, np.nan, -np.inf, np.inf])
        np.testing.assert_array_equal(valid_temperature(values), [False, True, True, False, False, False, False])

    def test_frequency_boundaries_and_expected_conservation(self):
        values = [-30.0001, -30, -6.0001, -6, -3, 0, 3, 6, 9, 12, 15, 30, 30.0001]
        data = pd.DataFrame({'station':10, 'time':pd.date_range('2024-01-01', periods=len(values), freq='10min'),
                             'f':1., 'fg':2., 't':values})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'weather.parquet'
            data.to_parquet(path)
            source=pq.ParquetFile(path)
            arrays=accumulate(source, 1, np.array([10]))
        yearly=make_yearly_table(np.array([10]), *arrays[:5])
        temp=yearly[yearly.variable.eq('temperature')].set_index('bin_label')
        self.assertEqual(temp.measurement_count.sum(), 11)
        self.assertEqual(temp.loc['<-6','measurement_count'], 2)
        self.assertEqual(temp.loc['-6--3','measurement_count'], 1)
        self.assertEqual(temp.loc['>=15','measurement_count'], 2)
        accidents=pd.DataFrame({'id':range(len(values)), 'season':'Winter','year':2024,
            'meidsli':3,'temp_station_id':10,'temp_distance_km':1.,'temp_time_diff_min':0.,'temperature_c':values})
        spec=next(s for s in VARIABLES if s.variable=='temperature')
        for background in [yearly,make_pooled_table(yearly)]:
            background=background.rename(columns={'station':'weather_station_id'})
            # Analysis load_data normally combines the two warm tail bins.
            background.loc[background.variable.eq('temperature') & background.bin_label.isin(['12-15','>=15']), 'bin_label']='>=12'
            keys=['weather_station_id','season','variable','bin_label'] + (['year'] if 'year' in background else [])
            background=background.groupby(keys,as_index=False).agg(measurement_count=('measurement_count','sum'),
                total_measurements_in_period=('total_measurements_in_period','first'),frequency_pct=('frequency_pct','sum'))
            result,details,coverage=station_frequency_scenario(accidents,background,spec,20,'Injury accidents','All seasons')
            self.assertEqual(coverage['analysed_accidents'],11)
            self.assertAlmostEqual(result.expected_accidents.sum(),11)
            self.assertEqual(result.observed_accidents.sum(),11)


class DistinctCoverageTests(unittest.TestCase):
    def test_window_endpoints_and_expected_slots(self):
        times=pd.date_range('2024-01-01 07:00', '2024-01-01 23:50',freq='10min').to_numpy()
        self.assertEqual(EXPECTED_OBSERVATIONS,102)
        self.assertEqual(distinct_slot_mask(times).bit_count(),102)
        self.assertEqual(distinct_slot_mask(pd.to_datetime(['2024-01-01 06:59:59','2024-01-02 00:00:00']).to_numpy()),0)
        self.assertEqual(distinct_slot_mask(pd.to_datetime(['2024-01-01 07:00:00','2024-01-01 07:09:59','2024-01-01 23:59:59']).to_numpy()).bit_count(),2)

    def test_duplicates_across_row_groups_cannot_pass_coverage(self):
        times=pd.date_range('2024-01-01 07:00',periods=52,freq='10min')
        frame=pd.DataFrame({'station':1,'time':times,'f':1.,'fg':2.,'t':0.})
        frame=pd.concat([frame,frame],ignore_index=True)
        frame.loc[frame.time.eq(times[0]),'t']=31
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'weather.parquet'
            pq.write_table(pa.Table.from_pandas(frame),path,row_group_size=30)
            result=aggregate_weather(path,np.array([1])).iloc[0]
        self.assertEqual(result.f_valid_observations,104)
        self.assertEqual(result.f_distinct_slots,52)
        self.assertEqual(result.fg_distinct_slots,52)
        self.assertEqual(result.temperature_distinct_slots,51)
        self.assertLess(result.f_distinct_slots,92)


class ControlReproductionTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('BUGFIX_REPLAY_DIR'), 'Set BUGFIX_REPLAY_DIR for full canonical-source replay')
    def test_current_output_exactly_reproduces_canonical_inputs(self):
        root=Path(__file__).resolve().parents[1]
        output=Path(os.environ['BUGFIX_REPLAY_DIR'])
        accidents=pd.read_csv(root/'data/processed/accidents/rural_injury.csv',low_memory=False)
        accidents['timestamp']=pd.to_datetime(accidents.timestamp)
        candidates=build_candidates(accidents)
        weather=read_weather(root/'data/processed/weather/weather.parquet',candidates)
        rebuilt=assemble(accidents,candidates,weather).reset_index(drop=True)
        self.assertEqual(
            rebuilt.to_csv(index=False),
            (output/'data/analysis/case_control.csv').read_text(),
        )
        # Input order must not change a nearest-time tie choice.
        shuffled=assemble(accidents,candidates.sample(frac=1,random_state=42),weather.sample(frac=1,random_state=42)).reset_index(drop=True)
        pd.testing.assert_frame_equal(rebuilt,shuffled,check_exact=True)
