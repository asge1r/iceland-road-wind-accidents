import unittest

import src.analysis_data as analysis_data
import src.exports_accidents as accident_exports
import src.exports_counters as counter_exports
import src.exports_traffic as traffic_exports
import src.exports_weather as weather_exports
import src.traffic.daily_tools as daily_tools
import src.traffic.road_period as road_period
from src.traffic import counter_summary, counter_weather, road_accidents, road_panel, road_weather


class ModuleBoundaryTests(unittest.TestCase):
    def test_analysis_export_entry_point_delegates_by_source(self) -> None:
        self.assertIs(
            analysis_data.export_accident_tables,
            accident_exports.export_accident_tables,
        )
        self.assertIs(analysis_data.export_frequency, weather_exports.export_frequency)
        self.assertIs(analysis_data.export_rate_tables, traffic_exports.export_rate_tables)
        self.assertIs(
            analysis_data.export_daily_traffic,
            counter_exports.export_daily_traffic,
        )

    def test_road_period_public_helpers_keep_their_owners(self) -> None:
        self.assertIs(
            road_period.build_station_candidates,
            road_weather.build_station_candidates,
        )
        self.assertIs(
            road_period.build_accident_counts,
            road_accidents.build_accident_counts,
        )
        self.assertIs(road_period.build_long_table, road_panel.build_long_table)

    def test_daily_helpers_separate_matching_and_summaries(self) -> None:
        self.assertIs(
            daily_tools.build_weather_match_data,
            counter_weather.build_weather_match_data,
        )
        self.assertIs(
            daily_tools.build_wind_summary,
            counter_summary.build_wind_summary,
        )
        self.assertIs(
            daily_tools.build_adu_validation,
            counter_summary.build_adu_validation,
        )


if __name__ == "__main__":
    unittest.main()
