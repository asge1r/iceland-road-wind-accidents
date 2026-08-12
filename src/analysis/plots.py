"""Small plotting helpers for the compact analysis-data workflow."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_daily_wind(results: pd.DataFrame, path: Path) -> None:
    """Plot observed/expected daily traffic by daytime mean-wind interval."""
    data = results.copy()
    x = np.arange(len(data))
    values = data["relative_traffic_pct"].to_numpy(float)
    low = values - data["relative_traffic_ci_95_low_pct"].to_numpy(float)
    high = data["relative_traffic_ci_95_high_pct"].to_numpy(float) - values
    fig, axis = plt.subplots(figsize=(11.4, 6.6))
    bars = axis.bar(x, values, width=.72, color="#287271")
    axis.errorbar(x, values, yerr=[low, high], fmt="none", ecolor="#202020", capsize=3)
    axis.axhline(100, color="#202020", linestyle="--", linewidth=1.2)
    axis.set_xticks(x, data["f_bin"].astype(str).str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Daytime mean wind speed, 10:00–21:59 (m/s)")
    axis.set_ylabel("Daily traffic relative to expected (%)")
    axis.set_title("Daily traffic relative to expected traffic by mean wind speed")
    axis.grid(axis="y", alpha=.2); axis.set_axisbelow(True)
    ymax = max(112, float(data["relative_traffic_ci_95_high_pct"].max()) * 1.12)
    axis.set_ylim(0, ymax)
    for bar, row in zip(bars, data.itertuples(index=False), strict=True):
        axis.text(bar.get_x() + bar.get_width()/2, min(ymax - 2, row.relative_traffic_pct + 1.5), f"n={row.counter_days:,}", ha="center", va="bottom", fontsize=8.5)
    fig.text(.5, .035, "Expected traffic: mean for the same counter, year, month, and weekday. Error bars are 95% counter-cluster bootstrap intervals.", ha="center", fontsize=8.3, color="#444444")
    fig.subplots_adjust(left=.11, right=.98, top=.91, bottom=.20)
    path.parent.mkdir(parents=True, exist_ok=True); fig.savefig(path, dpi=240); plt.close(fig)


def plot_road_adjustment(rates: pd.DataFrame, path: Path) -> None:
    """Compare frequency-only and traffic-adjusted O/E by wind interval."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), constrained_layout=True)
    for axis, (variable, label) in zip(axes, [("f", "Mean wind speed, f (m/s)"), ("fg", "Maximum wind gust, fg (m/s)")], strict=True):
        data = rates[rates["variable"].eq(variable)].sort_values("bin_order")
        x = np.arange(len(data)); width = .38
        axis.bar(x-width/2, data["weather_only_observed_expected"], width, color="#577590", label="Wind frequency only")
        axis.bar(x+width/2, data["traffic_weather_observed_expected"], width, color="#C7522A", label="Wind frequency + estimated period traffic")
        axis.axhline(1, color="#222222", linestyle="--", linewidth=1)
        axis.set_xticks(x, data["wind_bin"].astype(str).str.replace(">=", "≥", regex=False))
        axis.set_xlabel(label); axis.set_ylabel("Observed / expected accidents"); axis.grid(axis="y", alpha=.2)
        axis.set_ylim(0, max(1.5, data[["weather_only_observed_expected", "traffic_weather_observed_expected"]].max().max()*1.15))
    axes[0].legend(frameon=False, ncols=2, loc="upper left"); fig.suptitle("Effect of estimated traffic adjustment")
    path.parent.mkdir(parents=True, exist_ok=True); fig.savefig(path, dpi=240); plt.close(fig)
