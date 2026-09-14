"""Geometric rural-length checks, independent of the real road delivery."""

import unittest

from shapely.geometry import box, Polygon

from src.traffic.rural_lengths import clipped_lengths


def feature(start=0, end=2000):
    return {"properties": {"KAFLISTODUPPHAF": start, "KAFLISTODENDIR": end},
            "geometry": {"type": "LineString", "coordinates": [[0, 0], [1000, 0]]}}


class RuralLengthTests(unittest.TestCase):
    def test_clips_urban_portions_and_preserves_official_length_scale(self):
        rural, unknown = clipped_lengths([feature()], 0, 2000, box(250, -10, 750, 10))
        self.assertAlmostEqual(rural, 1.)
        self.assertEqual(unknown, 0)

    def test_subsections_partition_rural_length(self):
        urban = box(250, -10, 750, 10)
        first, _ = clipped_lengths([feature()], 0, 800, urban)
        second, _ = clipped_lengths([feature()], 800, 2000, urban)
        self.assertAlmostEqual(first, .5)
        self.assertAlmostEqual(first + second, 1.)

    def test_overlapping_features_not_double_counted_and_gaps_not_rural(self):
        road = feature()
        rural, unknown = clipped_lengths([road, road], 0, 3000, box(250, -10, 750, 10))
        self.assertAlmostEqual(rural, 1.)
        self.assertAlmostEqual(unknown, 1.)

    def test_polygon_holes_are_rural(self):
        urban = Polygon([(0, -10), (1000, -10), (1000, 10), (0, 10)],
                        holes=[[(250, -5), (750, -5), (750, 5), (250, 5)]])
        rural, unknown = clipped_lengths([feature()], 0, 2000, urban)
        self.assertAlmostEqual(rural, 1.)
        self.assertEqual(unknown, 0)

    def test_multiline_gaps_are_not_bridged(self):
        road = feature()
        road["geometry"] = {"type": "MultiLineString", "coordinates": [
            [[0, 0], [250, 0]], [[750, 0], [1000, 0]]]}
        rural, unknown = clipped_lengths([road], 0, 2000, box(300, -10, 700, 10))
        self.assertAlmostEqual(rural, 2.)
        self.assertEqual(unknown, 0)
