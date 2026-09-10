import unittest

import numpy as np
import pandas as pd

from src.analysis.oe_analysis import VARIABLES, station_frequency_scenario


class OEAnalysisTests(unittest.TestCase):
    def test_all_weather_variables_use_the_same_expected_count_engine(self) -> None:
        accidents = pd.DataFrame(
            {
                "id": [1, 2],
                "season": ["Winter", "Winter"],
                "meidsli": [3, 3],
                "vehicle_group": ["1 vehicle", "2 or more vehicles"],
                "accident_family": ["Other", "Other"],
                "weather_station_id": [10, 10],
                "weather_station_dist_km": [2.0, 2.0],
                "weather_time_difference_minutes": [1.0, 1.0],
                "f": [1.0, 6.0],
                "fg": [2.0, 7.0],
                "temp_station_id": [10, 10],
                "temp_distance_km": [2.0, 2.0],
                "temp_time_diff_min": [1.0, 1.0],
                "temperature_c": [-4.0, 4.0],
            }
        )
        rows = []
        for spec in VARIABLES:
            total = 100 * len(spec.bin_labels)
            rows.extend(
                {
                    "weather_station_id": 10,
                    "season": "Winter",
                    "variable": spec.variable,
                    "bin_label": label,
                    "measurement_count": 100,
                    "total_measurements_in_period": total,
                    "frequency_pct": 100 / len(spec.bin_labels),
                }
                for label in spec.bin_labels
            )
        frequency = pd.DataFrame(rows)

        for spec in VARIABLES:
            with self.subTest(variable=spec.variable):
                result, _, coverage = station_frequency_scenario(
                    accidents,
                    frequency,
                    spec,
                    radius=20,
                    severity="Injury accidents",
                    analysis_season="All seasons",
                )
                self.assertEqual(int(result["observed_accidents"].sum()), 2)
                self.assertTrue(np.isclose(result["expected_accidents"].sum(), 2))
                self.assertEqual(coverage["analysed_accidents"], 2)


if __name__ == "__main__":
    unittest.main()
