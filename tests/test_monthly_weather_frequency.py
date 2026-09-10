"""Tests for the O/E-bin station-calendar-month frequency table."""

from __future__ import annotations

import unittest

import numpy as np

from src.weather.frequency import make_monthly_table


class MonthlyWeatherFrequencyTests(unittest.TestCase):
    def test_uses_calendar_month_and_oe_upper_bins(self) -> None:
        wind_totals = np.zeros(12, dtype=np.int64)
        wind_totals[0] = 10
        f_counts = np.zeros((12, 5), dtype=np.int64)
        f_counts[0] = [2, 3, 4, 1, 0]
        fg_counts = np.zeros((12, 7), dtype=np.int64)
        fg_counts[0] = [1, 2, 3, 1, 1, 1, 1]
        temperature_totals = np.zeros(12, dtype=np.int64)
        temperature_totals[0] = 10
        temperature_counts = np.zeros((12, 8), dtype=np.int64)
        temperature_counts[0] = [1, 1, 2, 2, 1, 1, 1, 1]

        table = make_monthly_table(
            np.array([123]), wind_totals, f_counts, fg_counts,
            temperature_totals, temperature_counts,
        )

        self.assertEqual(set(table["month"]), {1})
        self.assertEqual(
            table[table["variable"].eq("f")]["bin_label"].tolist(),
            ["0-5", "5-10", "10-15", "15-20"],
        )
        self.assertEqual(
            table[table["variable"].eq("fg")]["bin_label"].tolist(),
            ["0-5", "5-10", "10-15", "15-20", "20-25", "25-30", ">=30"],
        )
        self.assertEqual(
            table[table["variable"].eq("temperature")]["bin_label"].tolist(),
            ["<-6", "-6--3", "-3-0", "0-3", "3-6", "6-9", "9-12", ">=12"],
        )


if __name__ == "__main__":
    unittest.main()
