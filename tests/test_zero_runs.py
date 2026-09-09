import unittest

import numpy as np
import pandas as pd

from src.validation.zero_runs import adjusted_frequency, split_runs


class ZeroRunValidationTests(unittest.TestCase):
    def test_split_runs_uses_elapsed_threshold(self) -> None:
        start = np.datetime64("2025-01-01T00:00")
        runs = {1: [(start, start + np.timedelta64(110, "m")),
                    (start, start + np.timedelta64(120, "m"))]}
        excluded, returned = split_runs(runs, 2)
        self.assertEqual(excluded[1], [runs[1][1]])
        self.assertEqual(returned[1], [runs[1][0]])

    def test_no_exclusion_returns_every_run(self) -> None:
        runs = {1: [(np.datetime64("2025-01-01T00:00"),
                     np.datetime64("2025-01-01T02:00"))]}
        excluded, returned = split_runs(runs, None)
        self.assertEqual(excluded, {})
        self.assertEqual(returned, runs)

    def test_adjusted_frequency_adds_zeros_to_lowest_bin_and_total(self) -> None:
        base = pd.DataFrame({
            "station": [1, 1], "season": ["winter", "winter"],
            "variable": ["f", "f"], "bin_label": ["0-5", "5-10"],
            "bin_lower_value": [0.0, 5.0], "measurement_count": [10, 5],
            "total_measurements_in_period": [15, 15], "frequency_pct": [0, 0],
        })
        returned = pd.DataFrame({
            "station": [1], "season": ["winter"], "returned_zero_rows": [3],
        })
        result = adjusted_frequency(base, returned)
        low = result[result["bin_label"].eq("0-5")].iloc[0]
        self.assertEqual(low["measurement_count"], 13)
        self.assertEqual(low["total_measurements_in_period"], 18)


if __name__ == "__main__":
    unittest.main()
