"""Protect sparse-bin readability without changing plotted estimates."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from src.figures.oe_histo import add_counts
from src.figures.traffic_corrected_oe import draw


def test_oe_omits_zero_counts_and_keeps_positive_counts():
    figure, axis = plt.subplots()
    try:
        bars = axis.bar([0, 1], [0, 2.15])
        add_counts(axis, bars, np.array([0, 68]))
        assert [text.get_text() for text in axis.texts] == ['68']
        assert [bar.get_height() for bar in bars] == [0, 2.15]
    finally:
        plt.close(figure)


def test_q2_emphasises_change_without_repeated_count_labels():
    figure, axis = plt.subplots()
    try:
        draw(axis, pd.DataFrame({'bin_order':[0], 'bin_label':['>=20'],
             'time_oe':[2.15], 'traffic_corrected_oe':[2.71], 'observed_accidents':[68]}), 'f')
        text = [label.get_text() for label in axis.texts]
        assert any('2.15 → 2.71' in label for label in text)
        assert not any('68' in label for label in text)
        assert [bar.get_height() for bar in axis.patches] == [2.15, 2.71]
    finally:
        plt.close(figure)
