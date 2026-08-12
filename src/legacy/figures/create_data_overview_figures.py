"""Create simple thesis figures showing retained and excluded source data."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


OUT = Path("reports/main/figures")
KEEP = "#5F8F78"
DROP = "#C96A5B"
OTHER = "#D6A84B"
TEXT = "#263238"


def fmt_count(value: int) -> str:
    return f"{value:,}"


def donut(axis, values, labels, colors, title, center_text, legend_y=-0.28):
    total = sum(values)
    legend_labels = [
        f"{label}: {fmt_count(value)} ({100 * value / total:.1f}%)"
        for label, value in zip(labels, values, strict=True)
    ]
    axis.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.34, "edgecolor": "white", "linewidth": 2},
    )
    axis.text(0, 0.06, center_text, ha="center", va="center", fontsize=11, weight="bold", color=TEXT)
    axis.text(0, -0.15, f"n = {fmt_count(total)}", ha="center", va="center", fontsize=10, color=TEXT)
    axis.set_title(title, fontsize=12, weight="bold", pad=12, color=TEXT)
    axis.legend(legend_labels, loc="lower center", bbox_to_anchor=(0.5, legend_y), frameon=False, fontsize=9)


def accident_figure():
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.3), constrained_layout=True)
    donut(
        axes[0], [95_640, 16_487, 6_120],
        ["Urban accidents (outside rural scope)", "Rural damage-only (available)", "Rural injury (primary outcome)"],
        [DROP, OTHER, KEEP], "Available accident records", "All accidents\n2007–2024",
    )
    donut(
        axes[1], [141, 1_262, 4_717],
        ["Fatal (code 1)", "Serious (code 2)", "Minor injury (code 3)"],
        [DROP, OTHER, KEEP], "Injury severity", "Rural injury\naccidents",
    )
    donut(
        axes[2], [5_914, 206], ["Valid wind match ≤20 km", "No valid wind match ≤20 km"],
        [KEEP, DROP], "Primary wind O/E sample", "Rural injury\naccidents",
    )
    fig.suptitle("Accident data selection", fontsize=17, weight="bold", color=TEXT)
    fig.savefig(OUT / "accident_selection.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def weather_figure():
    raw = 226_580_952
    retained = 214_043_666
    excluded = raw - retained
    fig, axis = plt.subplots(figsize=(8, 6))
    fig.subplots_adjust(top=0.84, bottom=0.22)
    donut(axis, [retained, excluded], ["Valid wind retained", "Wind observation excluded"], [KEEP, DROP], "", "Raw weather\nobservations", legend_y=-0.16)
    fig.suptitle("Weather observations retained", fontsize=17, weight="bold", color=TEXT)
    fig.savefig(OUT / "weather_selection.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def traffic_figure():
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.2))
    fig.subplots_adjust(top=0.82, bottom=0.28, wspace=0.28)
    donut(
        axes[0], [16_257, 17_500], ["Study years 2007–2024", "Outside study years"],
        [KEEP, DROP], "Annual road-section data", "Road-section-\nyear rows", legend_y=-0.18,
    )
    donut(
        axes[1], [44_070, 4_701], ["Usable nearby wind", "No usable wind within 20 km"],
        [KEEP, DROP], "Main table coverage", "Road-section-\nyear-periods", legend_y=-0.18,
    )
    donut(
        axes[2], [764_847, 9_427], ["Usable daytime wind", "No usable daytime wind"],
        [KEEP, DROP], "Daily counter sensitivity", "Physical\ncounter-days", legend_y=-0.18,
    )
    fig.suptitle("Traffic data selection", fontsize=17, weight="bold", color=TEXT)
    fig.savefig(OUT / "traffic_selection.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    accident_figure()
    weather_figure()
    traffic_figure()


if __name__ == "__main__":
    main()
