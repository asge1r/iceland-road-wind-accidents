import unittest

import numpy as np
import pandas as pd

from src.tables.daily_season_oe import calculate


class DailySeasonOETests(unittest.TestCase):
    def test_expected_counts_reconstruct_each_season(self) -> None:
        rows = []
        for counter, season in enumerate(
            ["Winter", "Spring", "Summer", "Fall"], start=1
        ):
            for wind_bin, accidents, vehicles in [
                ("0-10", 2, 80.0), ("10-15", 1, 15.0), (">=15", 1, 5.0)
            ]:
                rows.append(
                    {
                        "stratum": f"{counter}-2020-{season}",
                        "counter_id": counter,
                        "season": season,
                        "wind_bin": wind_bin,
                        "observed_accidents": accidents,
                        "allocated_vehicles": vehicles,
                    }
                )
        result = calculate(pd.DataFrame(rows), replicates=100, seed=12)
        totals = result.groupby("season", observed=True).agg(
            observed=("observed_accidents", "sum"),
            expected=("traffic_expected_accidents", "sum"),
        )
        self.assertTrue(np.allclose(totals["observed"], totals["expected"]))
        high = result[result["wind_bin"].astype(str).eq(">=15")]
        self.assertTrue(np.allclose(high["traffic_standardised_oe"], 5.0))
        self.assertTrue(high["bootstrap_valid_replicates"].between(1, 100).all())


if __name__ == "__main__":
    unittest.main()
