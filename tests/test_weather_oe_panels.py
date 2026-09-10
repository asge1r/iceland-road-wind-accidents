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
        all_injury = result[result["outcome"].str.startswith("All injury")]
        serious = result[result["outcome"].str.startswith("Serious/fatal")]
        self.assertEqual(
            set(all_injury["analysed_accidents"]), {6259, 2055, 795, 2300, 1109}
        )
        self.assertEqual(
            set(serious["analysed_accidents"]), {1424, 378, 196, 636, 214}
        )


if __name__ == "__main__":
    unittest.main()
