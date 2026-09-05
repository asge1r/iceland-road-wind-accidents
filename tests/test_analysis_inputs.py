from pathlib import Path
import unittest

import pandas as pd


ANALYSIS = Path("data/analysis")


@unittest.skipUnless(ANALYSIS.exists(), "local analysis data are unavailable")
class AnalysisInputTests(unittest.TestCase):
    def test_event_and_condition_ids_match_one_to_one(self) -> None:
        events = pd.read_csv(ANALYSIS / "accidents.csv", usecols=["id"])
        conditions = pd.read_csv(ANALYSIS / "accident_conditions.csv", usecols=["id"])
        self.assertTrue(events["id"].is_unique)
        self.assertTrue(conditions["id"].is_unique)
        self.assertEqual(set(events["id"]), set(conditions["id"]))

    def test_primary_columns_are_present(self) -> None:
        required = {
            "id", "weather_station_id", "weather_station_dist_km",
            "weather_time_difference_minutes", "f", "fg", "temp_station_id",
            "temp_distance_km", "temp_time_diff_min", "temperature_c",
            "solar_elevation_deg", "daylight_class",
        }
        columns = set(pd.read_csv(ANALYSIS / "accident_conditions.csv", nrows=0).columns)
        self.assertTrue(required <= columns)

    def test_manifest_matches_the_analysis_directory(self) -> None:
        manifest = pd.read_csv(ANALYSIS / "manifest.csv")
        listed = set(manifest["file"])
        actual = {path.name for path in ANALYSIS.glob("*.csv")} | {"README.md"}
        self.assertEqual(listed, actual)

    def test_daily_accident_and_denominator_stations_agree(self) -> None:
        daily_path = ANALYSIS / "daily_traffic.csv"
        wind_path = ANALYSIS / "counter_wind.csv"
        if not daily_path.exists() or not wind_path.exists():
            self.skipTest("optional daily-counter inputs are unavailable")
        daily = pd.read_csv(
            daily_path,
            usecols=["date", "counter_id", "weather_station_id"],
            dtype={"counter_id": "string"},
        )
        wind = pd.read_csv(
            wind_path,
            usecols=["id", "date", "counter_id", "counter_weather_station_id"],
            dtype={"counter_id": "string"},
        )
        self.assertTrue(wind["id"].is_unique)
        self.assertFalse(daily.duplicated(["date", "counter_id"]).any())
        # Unmatched candidates remain in counter_wind.csv so the selection loss
        # is visible. Station agreement applies to rows with an assigned station.
        eligible = wind[wind["counter_weather_station_id"].notna()].copy()
        matched = eligible.merge(daily, on=["date", "counter_id"], how="left", validate="many_to_one")
        self.assertTrue(matched["weather_station_id"].notna().all())
        self.assertTrue(matched["counter_weather_station_id"].eq(matched["weather_station_id"]).all())


if __name__ == "__main__":
    unittest.main()
