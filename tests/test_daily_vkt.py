"""Tests for same-day counter-section vehicle-kilometre allocation."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.traffic.daily_vkt import allocate_same_day_exposure


class DailyVehicleKilometreTests(unittest.TestCase):
    def test_allocation_reconstructs_each_daily_total(self) -> None:
        days = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "year": [2024, 2024],
                "season": ["Winter", "Winter"],
                "counter_section_id": ["a", "a"],
                "weather_station_id": [1, 1],
                "traffic_vehicles": [100, 50],
                "vehicle_km": [1_000.0, 500.0],
                "f_valid_observations": [100, 100],
                "f_coverage_ok": [True, True],
                "f_bin_0-5_count": [100, 0],
                "f_bin_5-10_count": [0, 0],
                "f_bin_10-15_count": [0, 0],
                "f_bin_15-20_count": [0, 0],
                "f_bin_>=20_count": [0, 100],
            }
        )
        result = allocate_same_day_exposure(
            days, "f", ["0-5", "5-10", "10-15", "15-20", ">=20"]
        )
        totals = result.groupby("date")["estimated_vehicle_km"].sum()
        np.testing.assert_allclose(totals.to_numpy(), [1_000.0, 500.0])

    def test_windy_day_uses_its_own_observed_traffic(self) -> None:
        days = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "year": [2024, 2024],
                "season": ["Winter", "Winter"],
                "counter_section_id": ["a", "a"],
                "weather_station_id": [1, 1],
                "traffic_vehicles": [1_000, 100],
                "vehicle_km": [1_000.0, 100.0],
                "f_valid_observations": [100, 100],
                "f_coverage_ok": [True, True],
                "f_bin_0-5_count": [100, 0],
                "f_bin_5-10_count": [0, 0],
                "f_bin_10-15_count": [0, 0],
                "f_bin_15-20_count": [0, 0],
                "f_bin_>=20_count": [0, 100],
            }
        )
        result = allocate_same_day_exposure(
            days, "f", ["0-5", "5-10", "10-15", "15-20", ">=20"]
        )
        exposure = result.groupby("bin_label", observed=True)[
            "estimated_vehicle_km"
        ].sum()
        self.assertEqual(exposure["0-5"], 1_000.0)
        self.assertEqual(exposure[">=20"], 100.0)


if __name__ == "__main__":
    unittest.main()
