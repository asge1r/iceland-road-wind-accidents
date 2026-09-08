import unittest

import numpy as np
import pandas as pd

from src.analysis_data import season_from_month, traffic_period_from_month
from src.weather.frequency import (
    FG_UPPER_BOUNDS,
    F_UPPER_BOUNDS,
    TEMPERATURE_LABELS,
    TEMPERATURE_UPPER_BOUNDS,
    labels,
    season_index,
)


class DefinitionTests(unittest.TestCase):
    def test_study_seasons_cover_every_month(self) -> None:
        months = pd.Series(range(1, 13))
        self.assertEqual(
            season_from_month(months).tolist(),
            [
                "Winter", "Winter", "Winter", "Spring", "Spring",
                "Summer", "Summer", "Summer", "Summer", "Fall", "Fall",
                "Winter",
            ],
        )
        self.assertEqual(season_index(months.to_numpy()).tolist(), [0, 0, 0, 1, 1, 2, 2, 2, 2, 3, 3, 0])

    def test_traffic_periods_follow_published_definitions(self) -> None:
        months = pd.Series(range(1, 13))
        self.assertEqual(
            traffic_period_from_month(months).tolist(),
            ["VDU", "VDU", "VDU", "VHDU", "VHDU", "SDU", "SDU", "SDU", "SDU", "VHDU", "VHDU", "VDU"],
        )

    def test_fixed_weather_intervals(self) -> None:
        self.assertEqual(labels(F_UPPER_BOUNDS), ["0-5", "5-10", "10-15", "15-20", "20-25", ">=25"])
        self.assertEqual(
            labels(FG_UPPER_BOUNDS),
            ["0-5", "5-10", "10-15", "15-20", "20-25", "25-30", "30-35", ">=35"],
        )
        self.assertEqual(
            TEMPERATURE_LABELS,
            ["<-6", "-6--3", "-3-0", "0-3", "3-6", "6-9", "9-12", "12-15", ">=15"],
        )

    def test_interval_boundaries_are_left_closed(self) -> None:
        values = np.array([0, 5, 10, 15, 20, 25], dtype=float)
        assigned = np.searchsorted(F_UPPER_BOUNDS, values, side="right")
        self.assertEqual(assigned.tolist(), [0, 1, 2, 3, 4, 5])

        temperatures = np.array([-6, -3, 0, 3, 6, 9, 12, 15], dtype=float)
        assigned_temperature = np.searchsorted(
            TEMPERATURE_UPPER_BOUNDS, temperatures, side="right"
        )
        self.assertEqual(assigned_temperature.tolist(), list(range(1, 9)))


if __name__ == "__main__":
    unittest.main()
