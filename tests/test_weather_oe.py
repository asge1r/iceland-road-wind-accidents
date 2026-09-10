import unittest
from pathlib import Path

import pandas as pd

from src.analysis.oe_analysis import OUTCOMES, PERIODS, VARIABLES
from src.figures.oe_histo import interval_label


class WeatherOETests(unittest.TestCase):
    def test_interval_labels_use_brackets(self) -> None:
        self.assertEqual(interval_label("-6--3", bracketed=True), "[−6,−3]")
        self.assertEqual(interval_label("0-5"), "0-5")
        self.assertEqual(interval_label(">=20"), "≥20")

    def test_current_results_have_every_requested_panel(self) -> None:
        result = pd.read_csv("reports/main/tables/weather_oe.csv")
        scenarios = result.groupby(
            ["variable", "outcome", "period"], observed=True
        ).size()
        self.assertEqual(
            len(scenarios), len(VARIABLES) * len(OUTCOMES) * len(PERIODS)
        )
        totals = result.groupby(
            ["variable", "outcome", "period"], observed=True
        )["observed_accidents"].sum()
        self.assertTrue(totals.gt(0).all())
        sample_sizes = result.groupby(
            ["variable", "outcome", "period"], observed=True
        )["analysed_accidents"].nunique()
        self.assertTrue(sample_sizes.eq(1).all())
        self.assertEqual(
            set(result["outcome"]),
            {
                "Minor injury accidents",
                "Severe/fatal accidents",
            },
        )
        bins = (
            result[["variable", "bin_label", "bin_order"]]
            .drop_duplicates()
            .sort_values(["variable", "bin_order"])
            .groupby("variable")["bin_label"]
            .apply(list)
        )
        self.assertEqual(bins["f"][-1], ">=20")
        self.assertEqual(bins["fg"][-1], ">=30")
        self.assertEqual(bins["temperature"][-1], ">=12")

    def test_four_weather_figures_exist(self) -> None:
        directory = Path("reports/main/figures")
        expected = {
            "weather_oe_annual.png",
            "wind_oe_panels.png",
            "gust_oe_panels.png",
            "temperature_oe_panels.png",
        }
        self.assertTrue(all((directory / name).is_file() for name in expected))


if __name__ == "__main__":
    unittest.main()
