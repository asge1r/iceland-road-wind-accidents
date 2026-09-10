import unittest

import pandas as pd

from src.tables.weather_oe_panels import OUTCOMES, PERIODS, VARIABLES, select_panels


class WeatherOEPanelTests(unittest.TestCase):
    def test_current_results_have_every_requested_panel(self) -> None:
        result = select_panels(pd.read_csv("reports/main/tables/oe_results.csv"))
        scenarios = result.groupby(
            ["variable", "outcome", "period"], observed=True
        ).size()
        self.assertEqual(len(scenarios), len(VARIABLES) * len(OUTCOMES) * len(PERIODS))
        totals = result.groupby(
            ["variable", "outcome", "period"], observed=True
        )["observed_accidents"].sum()
        self.assertTrue(totals.gt(0).all())
        self.assertTrue(result["bootstrap_reps"].eq(5000).all())
        sample_sizes = result.groupby(
            ["variable", "outcome", "period"], observed=True
        )["analysed_accidents"].nunique()
        self.assertTrue(sample_sizes.eq(1).all())
        paired = result.groupby(
            ["variable", "outcome", "period"], observed=True
        )["analysed_accidents"].first().unstack("outcome")
        self.assertTrue(
            paired["Serious/fatal subset (meiðsli ≤ 2)"].le(
                paired["All injury accidents (meiðsli ≤ 3)"]
            ).all()
        )


if __name__ == "__main__":
    unittest.main()
