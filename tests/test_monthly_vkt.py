import unittest
from pathlib import Path

import pandas as pd

from src.traffic.monthly_vkt import allocate_monthly_exposure


class MonthlyVKTTests(unittest.TestCase):
    def test_all_recorded_days_including_zero_contribute_and_vkt_is_conserved(self) -> None:
        days = pd.DataFrame({
            "date": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "year": [2020] * 3, "season": ["Winter"] * 3,
            "month": [1] * 3, "counter_section_id": ["a"] * 3,
            "weather_station_id": [1] * 3, "traffic_vehicles": [100, 200, 0],
            "rural_section_length_km": [2.0] * 3, "vehicle_km": [200.0, 400.0, 0.0],
        })
        frequency = pd.DataFrame({
            "weather_station_id": [1] * 5, "month": [1] * 5,
            "variable": ["f"] * 5,
            "bin_label": ["0-5", "5-10", "10-15", "15-20", ">=20"],
            "bin_order": range(5), "frequency": [0.5, 0.3, 0.1, 0.08, 0.02],
            "first_year": [2007] * 5, "last_year": [2025] * 5,
            "start_hour": [7] * 5, "end_hour": [24] * 5,
        })
        result = allocate_monthly_exposure(days, frequency, "f")
        self.assertEqual(result["counter_day_key"].nunique(), 3)
        self.assertAlmostEqual(result["estimated_vehicle_km"].sum(), 600.0)
        by_day = result.groupby("date")["estimated_vehicle_km"].sum()
        self.assertEqual(by_day.tolist(), [200.0, 400.0, 0.0])

    def test_current_result_has_694_events_for_both_weather_variables(self) -> None:
        path = Path("data/processed/traffic/monthly_vkt.csv")
        if not path.exists():
            self.skipTest("generated monthly VKT result is unavailable")
        result = pd.read_csv(path)
        all_injury = result[result["outcome"].eq("All injury accidents")]
        self.assertEqual(set(all_injury["variable"]), {"f", "fg"})
        self.assertTrue(all_injury.groupby("variable")["observed_accidents"].sum().eq(694).all())
        self.assertTrue(all_injury.groupby("variable")["analysed_accidents"].first().eq(694).all())
        totals = all_injury.groupby("variable")["estimated_vehicle_km"].sum()
        self.assertAlmostEqual(totals["f"], totals["fg"], places=3)


if __name__ == "__main__":
    unittest.main()
