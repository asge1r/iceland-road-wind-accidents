"""Regression tests for historical-only stations and time-specific outages."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
import pandas as pd

from src.traffic.counter_sections import add_nearest_weather_station
from src.traffic.station_selection import station_candidates, nearest_valid
from src.traffic.counter_accidents import accident_candidates
from src.accidents.match_weather import select_best
from src.traffic.daytime_weather import build_daytime_weather
from src.traffic.daily_vkt import allocate_daily_exposure, summarise_rates


class StationSelectionTests(unittest.TestCase):
    def test_historical_station_excluded_from_year_assignment(self):
        sections = pd.DataFrame({"counter_section_id": ["a", "b"], "year": [2024, 2023],
                                 "counter_location_lat": 65., "counter_location_lon": -20.})
        stations = pd.DataFrame({"station": [1, 2, 3], "name": ["historical", "active", "too far"],
                                 "lat": [65., 65.01, 66.], "lon": -20.})
        weather = pd.DataFrame({"station": [1, 2, 3], "time": pd.to_datetime([
            "2004-06-01 12:00", "2024-06-01 12:00", "2023-06-01 12:00"]), "f": 1., "fg": 2.})
        with TemporaryDirectory() as directory:
            root = Path(directory)
            stations.to_csv(root/"stations.csv", index=False)
            weather.to_parquet(root/"weather.parquet")
            result = add_nearest_weather_station(sections, root/"stations.csv", root/"weather.parquet", 20)
        self.assertEqual(result.iloc[0].weather_station_id, 2)
        self.assertTrue(pd.isna(result.iloc[1].weather_station_id))
        self.assertFalse(result.iloc[1].weather_station_within_limit)

    def test_invalid_wind_falls_back_but_temperature_does_not_change_wind_station(self):
        values = np.array([[[1, 2, np.nan], [np.nan, 2, 0], [1, -1, 0]],
                           [[10, 20, 3], [10, 20, 3], [np.nan, np.nan, 3]]])
        ids, selected = nearest_valid(np.array([1, 2]), values)
        np.testing.assert_array_equal(ids, [1, 2, -1])
        self.assertTrue(np.isnan(selected[0, 2]))

    def test_accident_and_exposure_use_same_available_station_without_double_counting(self):
        sections = pd.DataFrame({"counter_section_id": ["a"], "counter_location_lat": [65.], "counter_location_lon": [-20.]})
        stations = pd.DataFrame({"station": [1, 2, 3], "lat": [65., 65.01, 66.], "lon": -20.})
        candidates = station_candidates(sections, stations)
        self.assertEqual(candidates.weather_station_id.tolist(), [1, 2])
        times = pd.to_datetime(["2024-01-01 07:00", "2024-01-01 07:10", "2024-01-01 07:20"])
        # Closest station is down at 07:10; distant station also observes 07:00,
        # but it must not add a second copy of exposure there.
        weather = pd.DataFrame({"station": [1, 1, 2, 2], "time": [times[0], times[2], times[0], times[1]],
                                "f": [1., 1., 25., 25.], "fg": [2., 2., 35., 35.], "t": 0.})
        days = pd.DataFrame({"date": [times[0].normalize()], "counter_section_id": ["a"], "year": 2024,
                             "season": "Winter", "traffic_vehicles": 1020, "rural_section_length_km": 1.,
                             "vehicle_km": 1020., "weather_station_id": 1})
        events = pd.DataFrame({"id": [1], "timestamp": [times[1]], "counter_section_id": ["a"],
                               "date": [times[1].normalize()], "meidsli": 3, "season": "Winter"})
        matched = select_best(accident_candidates(events, candidates), weather.rename(
            columns={"station": "weather_station_id", "time": "weather_time"}))
        self.assertEqual(matched.weather_station_id.tolist(), [2])
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sections.to_csv(root/"sections.csv", index=False)
            stations.to_csv(root/"stations.csv", index=False)
            weather.to_parquet(root/"weather.parquet")
            daily_weather = build_daytime_weather(root/"weather.parquet", days, root/"sections.csv", root/"stations.csv")
        wind = daily_weather[daily_weather.variable.eq("f")]
        self.assertEqual(wind.observed_minutes.sum(), 25)
        self.assertEqual(wind[wind.weather_station_id.eq(2)].observed_minutes.sum(), 10)
        allocated = allocate_daily_exposure(days, daily_weather, "f")
        self.assertEqual(allocated.estimated_vehicle_km.sum(), 25)
        cases = events.join(matched.set_index("acc_index")[["weather_station_id", "f", "fg", "t"]]).rename(columns={"t": "temperature"})
        rates, summary = summarise_rates(days, cases, daily_weather)
        self.assertEqual(summary["f_accidents"], 1)
        tail = rates.query("variable == 'f' and period == 'All year' and outcome == 'Minor injury accidents' and bin_label == '>=20'").iloc[0]
        self.assertEqual(tail.estimated_vehicle_km, 10)
        self.assertEqual(tail.rate_per_million_vehicle_km, 100000)
