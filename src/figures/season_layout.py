"""Supervisor layout: a centred All year panel above four seasons."""
import matplotlib.pyplot as plt


def seasonal_figure():
    figure = plt.figure(figsize=(14.5, 13), layout="constrained")
    grid = figure.add_gridspec(3, 4, width_ratios=[1, 3, 3, 1])
    axes = [figure.add_subplot(grid[0, 1:3])]
    axes += [figure.add_subplot(grid[row, columns])
             for row in (1, 2) for columns in (slice(0, 2), slice(2, 4))]
    return figure, axes
