"""Layout checks for the daily-traffic rate figures."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.figures.weather_rate import (
    OUTCOMES, PERIODS, VARIABLES, RATE, display_interval, draw, make_figures,
    combine_seasonal_tails,
)


def sample():
    return pd.DataFrame([
        {
            "variable": variable, "outcome": outcome, "period": period,
            "bin_label": label, "bin_order": order, "accidents": 5,
            "estimated_vehicle_km": 1000,
            RATE: .1 if period == "Summer" else .03,
        }
        for variable in VARIABLES
        for outcome in OUTCOMES
        for period in PERIODS
        for order, label in enumerate(["0-5", "5-10"])
    ])


class WeatherRateFigureTests(unittest.TestCase):
    def test_zero_height_segments_have_no_count_labels(self):
        data = sample()
        zero = ((data.outcome.eq(OUTCOMES[0]) & data.bin_label.eq("0-5"))
                | (data.outcome.eq(OUTCOMES[1]) & data.bin_label.eq("5-10")))
        data.loc[zero, ["accidents", RATE]] = 0
        figure, axis = plt.subplots()
        try:
            draw(axis, data, "temperature", "Summer")
            counts = [text for text in axis.texts if hasattr(text, "xy")]
            self.assertEqual(len(counts), 2)
            self.assertTrue(all(text.get_text() == "5" for text in counts))
        finally:
            plt.close(figure)

    def test_seasonal_tails_sum_counts_and_exposure_not_rates(self):
        data = pd.DataFrame([
            {"variable": variable, "period": period, "outcome": outcome,
             "bin_label": label, "bin_order": order, "accidents": order+1,
             "estimated_vehicle_km": 1e6 * (order+2), RATE: (order+1)/(order+2)}
            for variable, labels in [("f", ["15-20", ">=20"]), ("fg", ["20-25", "25-30", ">=30"])]
            for period in ["All year", "Summer"] for outcome in OUTCOMES
            for order, label in enumerate(labels)
        ])
        merged = combine_seasonal_tails(data)
        pd.testing.assert_frame_equal(
            data[data.period.eq("All year")].reset_index(drop=True),
            merged[merged.period.eq("All year")].reset_index(drop=True), check_dtype=False)
        for variable, label, count, exposure in [("f", ">=15", 3, 5e6), ("fg", ">=20", 6, 9e6)]:
            rows = merged[merged.period.eq("Summer") & merged.variable.eq(variable)]
            self.assertEqual(rows.bin_label.tolist(), [label]*2)
            self.assertTrue(rows.accidents.eq(count).all())
            self.assertTrue(rows.estimated_vehicle_km.eq(exposure).all())
            self.assertTrue(rows[RATE].eq(count/exposure*1e6).all())

    def test_wind_intervals_use_en_dash(self):
        self.assertEqual(display_interval("0-5"), "0–5")
        self.assertEqual(display_interval("10-15"), "10–15")

    def test_temperature_brackets(self):
        self.assertEqual(display_interval("-6--3", True), "[−6, −3]")
        self.assertEqual(display_interval("0-3", True), "[0, 3]")
        self.assertEqual(display_interval(">=12", True), "≥12")

    def test_annual_and_seasonal_wind_bars_stack(self):
        figure, axes = plt.subplots(1, 2)
        try:
            draw(axes[0], sample(), "f", "All year")
            draw(axes[1], sample(), "f", "Summer")
            self.assertEqual(len(axes[0].containers), 2)
            self.assertEqual(len(axes[1].containers), 2)
            for blue, red in zip(*axes[1].containers, strict=True):
                self.assertAlmostEqual(red.get_y(), blue.get_height())
            for blue, red in zip(*axes[0].containers, strict=True):
                self.assertAlmostEqual(blue.get_x() + blue.get_width()/2,
                                       red.get_x() + red.get_width()/2)
                self.assertEqual(blue.get_width(), red.get_width())
                self.assertAlmostEqual(red.get_y(), blue.get_height())
                self.assertGreater(axes[0].get_ylim()[1], red.get_y() + red.get_height())
            # First two annotations belong to blue segments, next two to red.
            for annotation, bar in zip(axes[0].texts[:2], axes[0].containers[0], strict=True):
                self.assertEqual(annotation.xy, (bar.get_x() + bar.get_width()/2, bar.get_height()/2))
                self.assertEqual(annotation.get_position(), (0, 0))
                self.assertEqual(annotation.get_va(), "center")
            for annotation, bar in zip(axes[0].texts[2:4], axes[0].containers[1], strict=True):
                self.assertEqual(annotation.xy, (bar.get_x() + bar.get_width()/2, bar.get_y() + bar.get_height()))
                self.assertEqual(annotation.get_position(), (0, 4))
            self.assertIn("Summer", [t.get_text() for t in axes[1].texts])
            self.assertEqual(axes[1].xaxis.get_major_ticks()[0].tick1line.get_markersize(), 0)
        finally:
            plt.close(figure)

    def test_panel_specific_limits_labels_and_grid_spacing(self):
        figures = []
        try:
            with tempfile.TemporaryDirectory() as directory:
                with patch("matplotlib.figure.Figure.savefig"), patch(
                    "src.figures.weather_rate.plt.close", side_effect=figures.append,
                ):
                    paths = make_figures(sample(), Path(directory))
            self.assertEqual(len(paths), 4)
            for axis in figures[0].axes:
                self.assertEqual(axis.get_ylim(), (0, .08))
                self.assertIn("All year", [t.get_text() for t in axis.texts])
                self.assertFalse(any("Jan" in t.get_text() for t in axis.texts))
                self.assertNotIn(", f", axis.get_xlabel())
            self.assertEqual(figures[1]._supxlabel.get_text(), "Mean wind (m/s)")
            self.assertEqual(figures[1]._supxlabel.get_position()[0], .5)
            self.assertTrue(all(not axis.get_xlabel() for axis in figures[1].axes))
            self.assertEqual(figures[2]._supxlabel.get_text(), "Wind gust (m/s)")
            self.assertEqual(figures[2]._supxlabel.get_position()[0], .5)
            self.assertTrue(all(not axis.get_xlabel() for axis in figures[2].axes))
            self.assertEqual(figures[3]._supxlabel.get_text(), "Temperature (°C)")
            self.assertEqual(figures[3]._supxlabel.get_position()[0], .5)
            for axis in figures[3].axes[1:]:
                self.assertEqual(axis.get_xlabel(), "")
                spacing = np.diff(axis.get_yticks())
                np.testing.assert_allclose(spacing, spacing[0])
                self.assertTrue(any(t.get_text() in PERIODS for t in axis.texts))
            for figure in figures[1:]:
                # The denser Summer sample has larger rates and its own limit.
                self.assertGreater(figure.axes[3].get_ylim()[1], figure.axes[1].get_ylim()[1])
                for axis in figure.axes:
                    self.assertTrue(all(t.get_rotation() == 0 for t in axis.get_xticklabels()))
                    tallest = max(bar.get_y() + bar.get_height() for bar in axis.patches)
                    self.assertGreaterEqual(tallest / axis.get_ylim()[1], .75)
                    self.assertLessEqual(tallest / axis.get_ylim()[1], .85)
            for figure in figures[1:]:
                self.assertEqual(len(figure.axes), 5)
                for axis in figure.axes[1:]:
                    self.assertEqual(axis.get_ylim()[0], 0)
                    tallest = max(bar.get_y() + bar.get_height() for bar in axis.patches)
                    self.assertGreater(axis.get_ylim()[1], tallest)
                    self.assertEqual(len(axis.containers), 2)
                    for blue, red in zip(*axis.containers, strict=True):
                        self.assertAlmostEqual(red.get_y(), blue.get_height())
        finally:
            for figure in figures:
                plt.close(figure)


if __name__ == "__main__":
    unittest.main()
