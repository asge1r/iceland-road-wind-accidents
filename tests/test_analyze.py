import unittest
from unittest.mock import patch
from argparse import Namespace

from src.analyze import STAGE_ORDER, main, period_oe_task, stage_tasks


class AnalysisPipelineTest(unittest.TestCase):
    def test_complete_stage_order_ends_with_products(self) -> None:
        self.assertEqual(STAGE_ORDER[0], "workflow")
        self.assertEqual(STAGE_ORDER[-1], "products")
        self.assertEqual(
            STAGE_ORDER,
            (
                "workflow",
                "weather-frequency",
                "traffic-adjusted",
                "supporting",
                "products",
            ),
        )

    def test_seasonal_daily_tasks_share_one_panel(self) -> None:
        modules = [task.module for task in stage_tasks("daily-traffic", 5000, True)]
        panel = modules.index("src.tables.daily_season_panel")
        for module in [
            "src.tables.daily_season_rate",
            "src.tables.daily_season_interaction",
            "src.tables.daily_highwind_season_interaction",
            "src.tables.daily_season_oe",
        ]:
            self.assertLess(panel, modules.index(module))

    def test_products_validate_before_generating_thesis_tables(self) -> None:
        modules = [task.module for task in stage_tasks("products", 5000, True)]
        self.assertLess(modules.index("src.validate"), modules.index("src.tables.thesis"))
        self.assertLess(
            modules.index("src.tables.thesis"),
            modules.index("src.figures.wind_oe_comparison"),
        )

    def test_daily_stage_can_be_disabled(self) -> None:
        self.assertEqual(stage_tasks("daily-traffic", 5000, False), [])

    def test_public_traffic_stage_keeps_annual_tasks_without_daily_data(self) -> None:
        modules = [
            selected.module
            for selected in stage_tasks("traffic-adjusted", 5000, False)
        ]
        self.assertIn("src.tables.annual_quality", modules)
        self.assertNotIn("src.tables.daily_season_panel", modules)

    def test_counter_response_enables_traffic_correction_outputs(self) -> None:
        modules = [
            selected.module
            for selected in stage_tasks(
                "daily-traffic", 5000, False, True, True
            )
        ]
        self.assertEqual(
            modules,
            [
                "src.figures.weather_rate",
                "src.analysis.oe_analysis",
                "src.tables.traffic_corrected_oe",
                "src.figures.traffic_corrected_oe",
                "src.figures.traffic_weather_response",
            ],
        )

    def test_traffic_correction_rebuilds_missing_oe_dependency(self) -> None:
        # Only compact traffic response is present: no previously generated O/E.
        args = Namespace(
            bootstrap_reps=5000, stage=["daily-traffic"],
            skip_daily_traffic=False, dry_run=True,
        )
        with patch("src.analyze.parse_args", return_value=args), patch(
            "src.analyze.Path.exists",
            lambda path: str(path) == "data/analysis/traffic_weather_response.csv",
        ), patch("src.analyze.run") as run:
            main()
        tasks = [call.args[0] for call in run.call_args_list]
        self.assertEqual(tasks[0], period_oe_task(2019, 2024))
        self.assertEqual(tasks[1].module, "src.tables.traffic_corrected_oe")


if __name__ == "__main__":
    unittest.main()
