"""Tests for the compact O/E panel audit."""

from __future__ import annotations

import unittest

import pandas as pd

from src.tables.oe_audit import build


class OEAuditTests(unittest.TestCase):
    def test_panel_totals_reconstruct(self) -> None:
        source = pd.DataFrame(
            {
                "variable": ["f", "f"],
                "outcome": ["Minor", "Minor"],
                "period": ["All year", "All year"],
                "observed_accidents": [7, 3],
                "expected_accidents": [6.0, 4.0],
                "analysed_accidents": [10, 10],
                "contributing_stations": [2, 2],
                "sparse_bin": [False, True],
            }
        )
        result = build(source).iloc[0]
        self.assertEqual(result.observed_total, 10)
        self.assertEqual(result.expected_total, 10)
        self.assertEqual(result.sparse_intervals, 1)


if __name__ == "__main__":
    unittest.main()
