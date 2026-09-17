"""Tracked, common thesis figure style; changes presentation only."""
from pathlib import Path
import math
import matplotlib.pyplot as plt

PANEL_TITLE_SIZE = 16
GRID_COLOUR = '#BBBBBB'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12,
                     'axes.labelsize': 14, 'legend.fontsize': 12,
                     'xtick.major.size': 0, 'ytick.major.size': 0,
                     'xtick.minor.size': 0, 'ytick.minor.size': 0,
                     'grid.linewidth': 1.0, 'grid.color': GRID_COLOUR})


def panel_limit(maximum: float) -> float:
    """Leave room above positive count labels and round the scale upwards."""
    if not math.isfinite(maximum) or maximum <= 0:
        return 1.
    target = maximum * 1.20
    step = 10 ** math.floor(math.log10(maximum))
    limit = math.ceil(target / step) * step
    if limit > maximum * 4 / 3 + 1e-12:
        step /= 5
        limit = math.ceil(target / step) * step
    return limit


def style_figure(figure):
    for axis in figure.axes:
        axis.tick_params(axis='both', which='both', length=0)
        axis.set_axisbelow(True)
        for line in [*axis.get_xgridlines(), *axis.get_ygridlines()]:
            line.set_linewidth(1.0)
            line.set_color(GRID_COLOUR)
            line.set_alpha(1.0)


def save_figure(figure, output, **kwargs):
    style_figure(figure)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, **kwargs)
    if output.suffix != '.pdf':
        figure.savefig(output.with_suffix('.pdf'), **kwargs)
