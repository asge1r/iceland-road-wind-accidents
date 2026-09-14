import unittest
from pathlib import Path

import pandas as pd

from src.tables.traffic_corrected_oe import adjust_frequency


class TrafficCorrectedOETests(unittest.TestCase):
    def test_current_result_reconstructs_every_analysis_sample(self) -> None:
        path = Path(
            "reports/main/tables/weather_oe_traffic_corrected.csv"
        )
        if not path.exists():
            self.skipTest("generated traffic-corrected O/E table is unavailable")
        result = pd.read_csv(path)
        totals = result.groupby(["variable", "outcome"]).agg(
            observed=("observed_accidents", "sum"),
            time_expected=("time_expected_accidents", "sum"),
            corrected_expected=("traffic_corrected_expected_accidents", "sum"),
            analysed=("analysed_accidents", "first"),
        )
        self.assertTrue(totals["observed"].eq(totals["analysed"]).all())
        self.assertTrue(
            (totals["time_expected"] - totals["analysed"]).abs().lt(1e-6).all()
        )
        self.assertTrue(
            (totals["corrected_expected"] - totals["analysed"])
            .abs()
            .lt(1e-6)
            .all()
        )
        self.assertTrue(
            (
                result["traffic_corrected_oe"]
                - result["observed_accidents"]
                / result["traffic_corrected_expected_accidents"]
            )
            .abs()
            .lt(1e-10)
            .all()
        )

    def test_multipliers_are_normalized_within_weather_stratum(self) -> None:
        frequency = pd.DataFrame(
            {
                "weather_station_id": [1, 1],
                "season": ["Winter", "Winter"],
                "variable": ["f", "f"],
                "bin_label": ["0-5", "5-10"],
                "frequency_pct": [50.0, 50.0],
            }
        )
        response = pd.DataFrame(
            {
                "variable": ["f", "f"],
                "bin_label": ["0-5", "5-10"],
                "traffic_multiplier": [0.5, 1.5],
            }
        )
        adjusted = adjust_frequency(frequency, response).set_index("bin_label")
        self.assertEqual(adjusted.loc["0-5", "frequency_pct"], 25)
        self.assertEqual(adjusted.loc["5-10", "frequency_pct"], 75)
        self.assertAlmostEqual(adjusted["frequency_pct"].sum(), 100)

    def test_invalid_multiplier_is_rejected(self) -> None:
        frequency = pd.DataFrame(
            {
                "weather_station_id": [1],
                "season": ["Winter"],
                "variable": ["f"],
                "bin_label": ["0-5"],
                "frequency_pct": [100.0],
            }
        )
        response = pd.DataFrame(
            {
                "variable": ["f"],
                "bin_label": ["0-5"],
                "traffic_multiplier": [0.0],
            }
        )
        with self.assertRaisesRegex(ValueError, "invalid traffic multipliers"):
            adjust_frequency(frequency, response)


if __name__ == "__main__":
    unittest.main()
