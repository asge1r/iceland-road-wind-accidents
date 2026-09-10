"""Tests for accident-to-counter-section assignment."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.traffic.assign_counter_sections import assign, project_road_station


FEATURE = {
    "properties": {"KAFLISTODUPPHAF": 0, "KAFLISTODENDIR": 1000},
    "geometry": {"type": "LineString", "coordinates": [[0, 0], [1000, 0]]},
}


class AssignCounterSectionsTests(unittest.TestCase):
    def test_projection_returns_station_and_road_offset(self) -> None:
        station, offset = project_road_station(FEATURE, 250, 30)
        self.assertAlmostEqual(station, 250)
        self.assertAlmostEqual(offset, 30)

    def test_assigns_section_containing_projected_station(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            accidents = root / "accidents.csv"
            sections = root / "sections.csv"
            roads = root / "roads.geojson"
            output = root / "assigned.csv"
            pd.DataFrame(
                {
                    "id": [1, 2],
                    "timestamp": ["2019-01-01 12:00", "2019-01-01 13:00"],
                    "lat": [0.0, 0.0],
                    "lon": [0.0, 0.0],
                    "meidsli": [3, 2],
                    "urban_rural": ["Rural", "Rural"],
                    "registered_road_section": ["1-a1", "1-a1"],
                }
            ).to_csv(accidents, index=False)
            pd.DataFrame(
                {
                    "year": [2019, 2019],
                    "counter_section_id": ["left", "right"],
                    "road_section": ["1-a1", "1-a1"],
                    "counter_section_start_km": [0.0, 0.5],
                    "counter_section_end_km": [0.5, 1.0],
                    "counter_section_length_km": [0.5, 0.5],
                    "weather_station_id": [1, 2],
                    "weather_station_dist_km": [1.0, 2.0],
                }
            ).to_csv(sections, index=False)
            roads.write_text(
                json.dumps(
                    {
                        "features": [
                            {
                                "properties": {
                                    "NRVEGUR": "1", "NRKAFLI": "a1",
                                    "KAFLISTODUPPHAF": 0, "KAFLISTODENDIR": 1000,
                                },
                                "geometry": FEATURE["geometry"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch(
                "src.traffic.assign_counter_sections.Transformer.from_crs"
            ) as transformer:
                transformer.return_value.transform.side_effect = [(250, 0), (750, 0)]
                assigned, outcomes = assign(accidents, sections, roads, output, 100)

            self.assertEqual(assigned["counter_section_id"].tolist(), ["left", "right"])
            self.assertEqual(outcomes["assigned"], 2)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
