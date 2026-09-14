"""Tests for rural traffic allocated using actual same-day daytime weather."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.traffic.daily_vkt import allocate_daily_exposure, summarise_rates
from src.traffic.daytime_weather import build_daytime_weather
from src.traffic.counter_days import build_counter_days
from src.weather.monthly_frequency import build, VARIABLES
from src.traffic.counter_accidents import accident_candidates
from src.analyze import stage_tasks, task


def background():
    rows = []
    for variable, (_, labels) in VARIABLES.items():
        for day, order in [("2024-01-01", 0), ("2024-01-02", len(labels)-1)]:
            rows.append({
                "weather_station_id": 1, "date": pd.Timestamp(day), "variable": variable,
                "bin_label": labels[order], "bin_order": order,
                "observed_minutes": 1020,
                "counter_section_id": "a",
            })
    return pd.DataFrame(rows)


def days():
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "year": 2024, "season": "Winter", "counter_section_id": "a",
        "weather_station_id": 1, "traffic_vehicles": [1000, 500],
        "vehicle_km": [2000., 1000.],
        "rural_section_length_km": 2.,
    })


def reference_files(root):
    pd.DataFrame({"counter_section_id": ["a"], "counter_location_lat": [65.],
                  "counter_location_lon": [-20.]}).to_csv(root/"sections.csv", index=False)
    pd.DataFrame({"station": [1], "lat": [65.], "lon": [-20.]}).to_csv(root/"stations.csv", index=False)
    return root/"sections.csv", root/"stations.csv"


class DailyVehicleKilometreTests(unittest.TestCase):
    def test_rate_figures_do_not_require_other_daily_analysis_inputs(self):
        self.assertEqual(stage_tasks("daily-traffic", 100, False, True),
                         [task("src.figures.weather_rate")])

    def test_calm_and_stormy_days_keep_their_actual_traffic(self):
        result = allocate_daily_exposure(days(), background(), "f")
        np.testing.assert_allclose(
            result.groupby("date").estimated_vehicle_km.sum(), [2000, 1000])
        totals = result.groupby("bin_label").estimated_vehicle_km.sum()
        self.assertEqual(totals["0-5"], 2000)
        self.assertEqual(totals[">=20"], 1000)
        upper_day = result[result.date.eq(pd.Timestamp("2024-01-02")) & result.bin_label.eq(">=20")]
        self.assertEqual(upper_day.estimated_vehicle_km.iloc[0], 1000)
        swapped = days()
        swapped["vehicle_km"] = [1000, 2000]
        swapped["traffic_vehicles"] = [500, 1000]
        changed = allocate_daily_exposure(swapped, background(), "f")
        self.assertEqual(changed.loc[changed.bin_label.eq(">=20"), "estimated_vehicle_km"].sum(), 2000)

    def test_rate_uses_actual_accident_bin_and_accident_free_days(self):
        accidents = pd.DataFrame({
            "id": [1], "date": pd.to_datetime(["2024-01-02"]), "season": "Winter",
            "counter_section_id": "a", "weather_station_id": 1,
            "meidsli": 3, "f": 25., "fg": 35., "temperature": 15.,
        })
        result, summary = summarise_rates(days(), accidents, background())
        self.assertEqual(len(result), 200)
        upper = result.query("variable == 'f' and period == 'All year' and outcome == 'Minor injury accidents' and bin_label == '>=20'").iloc[0]
        self.assertEqual(upper.accidents, 1)
        self.assertEqual(upper.estimated_vehicle_km, 1000)
        self.assertAlmostEqual(upper.rate_per_million_vehicle_km, 1e6/1000)
        # Both outcome groups have the same exposure.
        self.assertEqual(result.query("variable == 'f' and period == 'All year' and outcome == 'Severe/fatal accidents' and bin_label == '>=20'").estimated_vehicle_km.iloc[0], 1000)
        self.assertEqual(summary["f_accidents"], 1)
        zero = result.query("variable == 'f' and bin_label == '5-10'")
        self.assertTrue(zero.rate_per_million_vehicle_km.isna().all())

    def test_missing_day_is_not_treated_as_calm(self):
        data = days()
        data.loc[1, "date"] = pd.Timestamp("2024-02-01")
        result = allocate_daily_exposure(data, background(), "f")
        self.assertEqual(result.date.nunique(), 1)
        self.assertEqual(result.estimated_vehicle_km.sum(), 2000)
        partial = background()
        partial["observed_minutes"] = 510
        result = allocate_daily_exposure(days(), partial, "f")
        np.testing.assert_allclose(result.groupby("date").estimated_vehicle_km.sum(), [1000, 500])
        # Half a day's observations must not receive a full day's traffic.
        partial["observed_minutes"] = 1025
        with self.assertRaises(ValueError):
            allocate_daily_exposure(days(), partial, "f")

    def test_duplicate_days_rejected(self):
        with self.assertRaises(ValueError):
            allocate_daily_exposure(pd.concat([days(), days()]), background(), "f")

    def test_stale_full_road_vehicle_km_rejected(self):
        source = days()
        source["rural_section_length_km"] = 1.
        with self.assertRaisesRegex(ValueError, "rural lengths"):
            allocate_daily_exposure(source, background(), "f")

    def test_missing_weather_removes_accident_and_exposure_together(self):
        accidents = pd.DataFrame({
            "id": [1], "date": pd.to_datetime(["2024-01-02"]), "season": "Winter",
            "counter_section_id": "a", "weather_station_id": 1,
            "meidsli": 3, "f": 25., "fg": 35., "temperature": 15.,
        })
        observed = background()
        observed = observed[observed.date.eq(pd.Timestamp("2024-01-01"))]
        result, summary = summarise_rates(days(), accidents, observed)
        self.assertEqual(summary["f_excluded_accidents_no_daytime_weather"], 1)
        self.assertEqual(result.accidents.sum(), 0)
        annual = result.query("variable == 'f' and period == 'All year' and outcome == 'Minor injury accidents'")
        self.assertEqual(annual.estimated_vehicle_km.sum(), 2000)

    def test_weather_window_boundaries_missing_variables_and_off_grid(self):
        times = pd.date_range("2024-01-01 07:00", "2024-01-02 00:00", freq="10min")
        data = pd.DataFrame({"station": 1, "time": times, "f": 0., "fg": 0., "t": 0.})
        data.loc[data.index[-1], ["f", "fg"]] = [25, 35]
        data.loc[1, "t"] = np.nan
        extra = pd.DataFrame({"station": 1, "time": pd.to_datetime(["2024-01-01 06:50", "2024-01-01 08:01"]),
                              "f": 25., "fg": 35., "t": 0.})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weather.parquet"
            pd.concat([data, extra]).sort_values("time").to_parquet(path, row_group_size=1)
            sections, stations = reference_files(Path(directory))
            result = build_daytime_weather(path, days(), sections, stations)
        wind = result[result.variable.eq("f")].set_index("bin_label")
        self.assertEqual(wind.observed_minutes.sum(), 1020)
        self.assertEqual(wind.loc[">=20", "observed_minutes"], 5)
        self.assertEqual(wind.loc["0-5", "observed_minutes"], 1015)
        self.assertEqual(result.loc[result.variable.eq("temperature"), "observed_minutes"].sum(), 1010)
        self.assertEqual(result.date.unique().tolist(), [pd.Timestamp("2024-01-01")])

    def test_duplicate_weather_rejected(self):
        data = pd.DataFrame({"station": [1, 1], "time": pd.to_datetime(["2024-01-01 07:00"]*2),
                             "f": 0., "fg": 0., "t": 0.})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weather.parquet"
            data.to_parquet(path, row_group_size=1)
            sections, stations = reference_files(Path(directory))
            with self.assertRaises(ValueError):
                build_daytime_weather(path, days(), sections, stations)

    def test_daytime_monthly_counts_pool_years_and_keep_empty_bins(self):
        data = pd.DataFrame({
            "station": 1,
            "time": pd.to_datetime([
                "2007-01-01 07:00", "2025-01-01 23:50",
                "2024-02-01 07:00", "2024-01-01 06:50",
                "2024-01-02 00:00", "2026-01-01 07:00",
                "2024-01-01 07:01",
            ]),
            "f": [0, 20, 5, 25, 25, 25, 25],
            "fg": [0, 30, 10, 35, 35, 35, 35],
            "t": [-30, 12, np.nan, 31, 31, 31, 31],
        })
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weather.parquet"
            data.to_parquet(path, row_group_size=1)
            result = build(path)
        jan = result.query("month == 1 and variable == 'f'").set_index("bin_label")
        self.assertEqual(jan.measurement_count.sum(), 2)
        self.assertEqual(jan.loc[">=20", "frequency"], .5)
        self.assertEqual(jan.loc["5-10", "measurement_count"], 0)
        feb = result.query("month == 2 and variable == 'temperature'")
        self.assertTrue(feb.frequency.isna().all())
        self.assertEqual(feb.measurement_count.sum(), 0)

    def test_counter_channels_in_section_are_summed(self):
        daily = pd.DataFrame({
            "date": ["2024-01-01"]*2, "year": 2024, "road_section": "1-a",
            "station_id": [100, 110], "traffic_volume": [100, 50],
        })
        sections = pd.DataFrame({
            "year": [2024], "road_section": ["1-a"], "counter_section_id": ["a"],
            "source_station_min_m": [100], "source_station_max_m": [110],
            "counter_section_length_km": [2], "weather_station_id": [1],
            "counter_section_start_km": [0], "counter_section_end_km": [2],
            "weather_station_dist_km": [2],
        })
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            daily.to_csv(root/"daily.csv", index=False)
            sections.to_csv(root/"sections.csv", index=False)
            with patch("src.traffic.counter_days.add_rural_lengths") as clip:
                clip.return_value = sections.assign(rural_section_length_km=1.5, unmapped_section_length_km=0.)
                result = build_counter_days(root/"daily.csv", root/"sections.csv")
        self.assertEqual(result.traffic_vehicles.tolist(), [150])
        self.assertEqual(result.vehicle_km.tolist(), [225])

    def test_event_weather_uses_nearest_time_not_monthly_average(self):
        events = pd.DataFrame({
            "timestamp": pd.to_datetime(["2024-01-01 13:14"]),
            "weather_station_id": [1], "weather_station_dist_km": [2.],
            "counter_section_id": ["a"],
        })
        candidates = events[["counter_section_id", "weather_station_id", "weather_station_dist_km"]]
        result = accident_candidates(events, candidates)
        self.assertEqual(result.weather_time.tolist(), [pd.Timestamp("2024-01-01 13:10")])
        self.assertEqual(result.weather_time_difference_minutes.tolist(), [4.])

if __name__ == "__main__":
    unittest.main()
