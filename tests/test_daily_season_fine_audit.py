import unittest

import pandas as pd


class DailySeasonFineAuditTests(unittest.TestCase):
    def test_current_audit_documents_sparse_upper_bins(self) -> None:
        result = pd.read_csv("reports/main/tables/daily_season_fine_audit.csv")
        upper = result[result["wind_bin"].isin(["20-25", ">=25"])].pivot(
            index="season", columns="wind_bin", values="observed_accidents"
        )
        self.assertEqual(
            upper.to_dict("index"),
            {
                "Winter": {"20-25": 2, ">=25": 1},
                "Spring": {"20-25": 1, ">=25": 3},
                "Summer": {"20-25": 1, ">=25": 1},
                "Fall": {"20-25": 2, ">=25": 0},
            },
        )
        self.assertTrue(
            result[result["wind_bin"].isin(["20-25", ">=25"])]
            ["fewer_than_10_accidents"]
            .all()
        )


if __name__ == "__main__":
    unittest.main()
