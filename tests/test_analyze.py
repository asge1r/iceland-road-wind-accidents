import unittest

from src.analyze import STAGE_ORDER, stage_tasks


class AnalysisPipelineTest(unittest.TestCase):
    def test_complete_stage_order_ends_with_products(self) -> None:
        self.assertEqual(STAGE_ORDER[0], "workflow")
        self.assertEqual(STAGE_ORDER[-1], "products")

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


if __name__ == "__main__":
    unittest.main()
