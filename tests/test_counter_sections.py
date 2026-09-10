import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.traffic.counter_sections import (
    add_counter_section_lengths,
    group_counter_sites,
)


class CounterSectionTests(unittest.TestCase):
    def test_grouping_uses_complete_span(self) -> None:
        source = pd.DataFrame(
            {
                "year": [2024, 2024, 2024],
                "road_section": ["1-a1"] * 3,
                "station_id": [1000, 1015, 1030],
                "site_name": ["site"] * 3,
                "source_fastnr": ["1", "2", "3"],
            }
        )
        result = group_counter_sites(source, tolerance_m=20)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["source_fastnr"], "1|2")
        self.assertEqual(result.iloc[0]["source_station_max_m"], 1015)
        self.assertEqual(result.iloc[1]["source_fastnr"], "3")

    def test_counter_sections_partition_annual_length(self) -> None:
        sites = pd.DataFrame(
            {
                "year": [2024, 2024, 2024],
                "road_section": ["1-a1"] * 3,
                "counter_station_m": [2000.0, 5000.0, 6000.0],
            }
        )
        annual = pd.DataFrame(
            {
                "year": [2024],
                "road_section": ["1-a1"],
                "section_length_km": [10.0],
            }
        )
        path = self.enterContext(TemporaryDirectory())
        annual_path = Path(path) / "annual.csv"
        annual.to_csv(annual_path, index=False)
        result = add_counter_section_lengths(sites, annual_path)
        self.assertAlmostEqual(result["counter_section_length_km"].sum(), 10.0)
        self.assertEqual(
            result["counter_section_length_km"].round(2).tolist(),
            [3.5, 2.0, 4.5],
        )


if __name__ == "__main__":
    unittest.main()
