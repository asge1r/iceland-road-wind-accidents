import unittest

import numpy as np
import pandas as pd

from src.tables.wind_oe_comparison import standardised_oe


class WindOeComparisonTest(unittest.TestCase):
    def test_expected_counts_reconstruct_strata(self) -> None:
        data = pd.DataFrame([
            ("a", "a|2020", "0-10", 80.0, 3),
            ("a", "a|2020", ">=15", 20.0, 1),
            ("b", "b|2020", "0-10", 50.0, 1),
            ("b", "b|2020", ">=15", 50.0, 1),
        ], columns=[
            "site", "stratum", "wind_bin", "exposure", "observed_accidents"
        ])
        result = standardised_oe(
            data,
            stratum="stratum",
            cluster="site",
            exposure="exposure",
            bins=["0-10", ">=15"],
            replicates=100,
            seed=1,
        )
        self.assertEqual(int(result["observed_accidents"].sum()), 6)
        self.assertTrue(np.isclose(result["expected_accidents"].sum(), 6))
        self.assertTrue(result["ci_95_low"].notna().all())


if __name__ == "__main__":
    unittest.main()
