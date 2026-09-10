import unittest

import pandas as pd

from src.analysis.oe_wind import (
    ALL_YEAR,
    WIND_LABELS,
    analyse,
    eligible_events,
    expected_by_station_season,
)


class WindObservedExpectedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5, 6, 7, 8],
                "meidsli": [2, 3, 1, 3, 2, 3, 2, 3],
                "season": [
                    "Winter", "Winter", "Spring", "Spring",
                    "Summer", "Summer", "Fall", "Fall",
                ],
                "weather_station_id": [10, 10, 10, 10, 20, 20, 20, 20],
                "weather_station_dist_km": [5.0] * 8,
                "weather_time_difference_minutes": [2.0] * 8,
                "f": [2.0, 7.0, 12.0, 17.0, 22.0, 27.0, 2.0, 7.0],
            }
        )
        shares = [40, 30, 15, 8, 5, 2]
        rows = []
        for station, season in [
            (10, "Winter"),
            (10, "Spring"),
            (20, "Summer"),
            (20, "Fall"),
        ]:
            for label, count in zip(WIND_LABELS, shares, strict=True):
                rows.append(
                    {
                        "station": station,
                        "season": season,
                        "variable": "f",
                        "bin_label": label,
                        "measurement_count": count,
                        "total_measurements_in_period": 100,
                    }
                )
        self.frequency = pd.DataFrame(rows)
        self.eligible = eligible_events(self.events, 20.0, 5.0)

    def test_expected_counts_preserve_total_accidents(self) -> None:
        detail = expected_by_station_season(self.eligible, self.frequency)
        self.assertEqual(detail["observed_accidents"].sum(), len(self.events))
        self.assertAlmostEqual(detail["expected_accidents"].sum(), len(self.events))

    def test_output_contains_two_outcomes_and_five_periods(self) -> None:
        output = analyse(self.eligible, self.frequency, 20, 1234)
        self.assertEqual(len(output), 2 * 5 * len(WIND_LABELS))
        self.assertEqual(
            set(output["outcome"]), {"Injury accidents", "Serious or fatal"}
        )
        self.assertEqual(
            set(output["period"]),
            {ALL_YEAR, "Winter", "Spring", "Summer", "Fall"},
        )

    def test_weather_match_limits_are_applied(self) -> None:
        events = self.events.copy()
        events.loc[0, "weather_station_dist_km"] = 21.0
        events.loc[1, "weather_time_difference_minutes"] = 6.0
        selected = eligible_events(events, 20.0, 5.0)
        self.assertEqual(set(selected["id"]), set(range(3, 9)))


if __name__ == "__main__":
    unittest.main()
