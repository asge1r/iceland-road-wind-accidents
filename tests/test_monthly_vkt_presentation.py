"""Guard seasonal presentation against averaging rates or changing exposure."""
import unittest
from pathlib import Path

import pandas as pd

from src.tables.monthly_vkt_rate import seasonal_rates


class SeasonalPresentationTests(unittest.TestCase):
    def test_unequal_section_exposure_is_summed_before_dividing(self):
        rows = []
        for variable in ['f', 'fg']:
            for season in ['Winter', 'Spring', 'Summer', 'Fall']:
                for section, observed, exposure in [('a', 1, 100), ('b', 3, 900)]:
                    rows.append(dict(variable=variable, season=season, year=2020,
                                     counter_section_id=section, bin_label='0-5',
                                     bin_order=0, observed_accidents=observed,
                                     estimated_vehicle_km=exposure))
        sections = pd.DataFrame(rows)
        pooled = pd.DataFrame([dict(variable=v, outcome='All injury accidents',
                                   bin_label='0-5', bin_order=0, observed_accidents=16,
                                   estimated_vehicle_km=4000) for v in ['f', 'fg']])
        result = seasonal_rates(sections, pooled)
        self.assertEqual(set(result.period), {'All year', 'Winter', 'Spring', 'Summer', 'Autumn'})
        self.assertTrue(result.rate_per_million_vehicle_km.eq(4000).all())
        pooled.loc[0, 'estimated_vehicle_km'] += 1
        with self.assertRaisesRegex(ValueError, 'do not reproduce'):
            seasonal_rates(sections, pooled)

    def test_current_seasonal_exposure_reconstructs_published_result(self):
        sections = Path('data/analysis/monthly_vkt_section.csv')
        pooled = Path('data/analysis/monthly_vkt.csv')
        if not sections.exists() or not pooled.exists():
            self.skipTest('local monthly VKT outputs unavailable')
        result = seasonal_rates(pd.read_csv(sections), pd.read_csv(pooled))
        totals = result[result.period.ne('All year')].groupby('variable').observed_accidents.sum()
        self.assertEqual(totals.to_dict(), {'f': 694, 'fg': 694})
        self.assertEqual(len(result), 60)


class SeverityDecompositionTests(unittest.TestCase):
    def test_every_component_reconstructs_seasonal_and_published_rates(self):
        import numpy as np
        from src.tables.monthly_vkt_rate import severity_rates
        sections=pd.read_csv('data/analysis/monthly_vkt_section.csv')
        pooled=pd.read_csv('data/analysis/monthly_vkt.csv')
        events=pd.read_csv('data/processed/traffic/counter_accidents.csv')
        split=severity_rates(sections,pooled,events)
        original=seasonal_rates(sections,pooled)
        keys=['variable','period','bin_label','bin_order']
        grouped=split.groupby(keys)
        self.assertTrue(grouped.estimated_vehicle_km.nunique().eq(1).all())
        for column in ['observed_accidents','rate_per_million_vehicle_km']:
            np.testing.assert_allclose(grouped[column].sum().sort_index(),
                original.set_index(keys)[column].sort_index(),rtol=1e-12,atol=1e-12)
        seasonal=split[split.period.ne('All year')].groupby(['variable','outcome','bin_label']).observed_accidents.sum().sort_index()
        annual=split[split.period.eq('All year')].set_index(['variable','outcome','bin_label']).observed_accidents.sort_index()
        pd.testing.assert_series_equal(seasonal,annual)
        for variable in ['f','fg']:
            self.assertEqual(split[split.variable.eq(variable)&split.period.eq('All year')].observed_accidents.sum(),694)
        broken=events.copy();broken.loc[0,'meidsli']=0
        with self.assertRaisesRegex(ValueError,'injury codes'):
            severity_rates(sections,pooled,broken)
        broken=events.iloc[1:]
        with self.assertRaisesRegex(ValueError,'section counts'):
            severity_rates(sections,pooled,broken)

    def test_displayed_seasonal_tails_preserve_shared_exposure_and_totals(self):
        import numpy as np
        from src.tables.monthly_vkt_rate import severity_rates
        from src.figures.weather_rate import combine_seasonal_tails, RATE
        sections = pd.read_csv('data/analysis/monthly_vkt_section.csv')
        pooled = pd.read_csv('data/analysis/monthly_vkt.csv')
        events = pd.read_csv('data/processed/traffic/counter_accidents.csv')
        split = severity_rates(sections, pooled, events).rename(columns={'observed_accidents': 'accidents'})
        original = seasonal_rates(sections, pooled).rename(columns={'observed_accidents': 'accidents'})
        original['outcome'] = 'All injury accidents'
        display = combine_seasonal_tails(split)
        total = combine_seasonal_tails(original)
        keys = ['variable', 'period', 'bin_label', 'bin_order']
        grouped = display.groupby(keys)
        self.assertTrue(grouped.estimated_vehicle_km.nunique().eq(1).all())
        for column in ['accidents', RATE]:
            np.testing.assert_allclose(grouped[column].sum().sort_index(),
                                       total.set_index(keys)[column].sort_index(),
                                       rtol=1e-12, atol=1e-12)
        for variable, tail in [('f', '>=15'), ('fg', '>=20')]:
            for season in ['Winter', 'Spring', 'Summer', 'Autumn']:
                rows = display[display.variable.eq(variable) & display.period.eq(season)]
                self.assertEqual(rows.sort_values('bin_order').iloc[-1].bin_label, tail)
