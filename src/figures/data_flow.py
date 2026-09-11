"""Draw source-to-analysis selection flow figures."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd


OUT = Path("reports/main/figures")
SELECTION = Path("data/analysis/selection_summary.csv")
WEATHER_AUDIT = Path("data/analysis/weather_cleaning.csv")

# Thesis-style palette
TEXT = "#222222"
MUTED = "#666666"
BORDER = "#4D4D4D"
BOX_FILL = "#F7F7F7"
ARROW = "#3A3A3A"


def count(value: int) -> str:
    return f"{int(value):,}"


def add_box(
    axis,
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    value: int,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.015,rounding_size=0.025",
        facecolor=BOX_FILL,
        edgecolor=BORDER,
        linewidth=1.0,
    )
    axis.add_patch(patch)

    axis.text(
        x + width / 2,
        y + height * 0.63,
        label,
        ha="center",
        va="center",
        fontsize=9.7,
        fontweight="semibold",
        color=TEXT,
        linespacing=1.05,
    )

    axis.text(
        x + width / 2,
        y + height * 0.28,
        f"n = {count(value)}",
        ha="center",
        va="center",
        fontsize=9.3,
        color=TEXT,
    )


def draw_horizontal_flow(
    axis,
    boxes: list[tuple[str, int]],
    exclusions: list[str],
) -> None:
    axis.set_xlim(0, 12)
    axis.set_ylim(0, 2.35)
    axis.axis("off")

    box_width = 2.35
    box_height = 0.90
    y = 1.05

    x_positions = [0.15, 3.25, 6.35, 9.45]

    for i, ((label, value), x) in enumerate(zip(boxes, x_positions)):
        add_box(
            axis=axis,
            x=x,
            y=y,
            width=box_width,
            height=box_height,
            label=label,
            value=value,
        )

        if i < len(boxes) - 1:
            next_x = x_positions[i + 1]

            axis.annotate(
                "",
                xy=(next_x - 0.08, y + box_height / 2),
                xytext=(x + box_width + 0.08, y + box_height / 2),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=ARROW,
                    lw=1.15,
                    mutation_scale=10,
                    shrinkA=0,
                    shrinkB=0,
                ),
            )

            midpoint = (x + box_width + next_x) / 2

            axis.text(
                midpoint,
                y - 0.16,
                exclusions[i],
                ha="center",
                va="top",
                fontsize=7.8,
                color=MUTED,
                linespacing=1.12,
            )


def accident_figure() -> None:
    summary = pd.read_csv(SELECTION).set_index(
        ["dataset", "step"]
    )["records"]

    valid = int(
        summary.loc[("accidents", "valid_time_and_coordinates")]
    )
    rural = int(
        summary.loc[("accidents", "rural_accidents")]
    )
    injury = int(
        summary.loc[("accidents", "rural_injury_accidents")]
    )
    matched = int(
        summary.loc[("accidents", "primary_wind_oe_sample")]
    )

    boxes = [
        ("Valid accident\nrecords", valid),
        ("Rural\naccidents", rural),
        ("Rural injury\naccidents", injury),
        ("Primary weather\nO/E sample", matched),
    ]

    exclusions = [
        f"−{count(valid - rural)}\nurban or otherwise excluded",
        f"−{count(rural - injury)}\ndamage-only accidents",
        f"−{count(injury - matched)}\nwithout qualifying weather match",
    ]

    figure, axis = plt.subplots(
        figsize=(10.5, 2.15),
    )

    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")

    draw_horizontal_flow(
        axis,
        boxes,
        exclusions,
    )

    figure.subplots_adjust(
        left=0.01,
        right=0.99,
        top=0.98,
        bottom=0.05,
    )

    png_path = OUT / "accident_flow.png"
    pdf_path = OUT / "accident_flow.pdf"

    figure.savefig(
        png_path,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.02,
        facecolor="white",
    )

    figure.savefig(
        pdf_path,
        bbox_inches="tight",
        pad_inches=0.02,
        facecolor="white",
    )

    plt.close(figure)


def weather_figure() -> None:
    """Retain weather-flow generation for supporting use."""
    audit = pd.read_csv(WEATHER_AUDIT)

    total = audit[
        audit["year"].astype(str).eq("total")
    ]

    if len(total) != 1:
        raise ValueError(
            "Weather cleaning table must contain one total row"
        )

    total = total.iloc[0]

    raw = int(total["input_rows"])
    retained = int(total["clean_wind_rows"])

    figure, axis = plt.subplots(
        figsize=(6.6, 2.1),
    )

    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")

    axis.set_xlim(0, 7)
    axis.set_ylim(0, 2.0)
    axis.axis("off")

    boxes = [
        ("Raw weather\nobservations", raw),
        ("Clean wind\nobservations", retained),
    ]

    x_positions = [0.45, 4.20]
    box_width = 2.30
    box_height = 0.85
    y = 0.90

    for i, ((label, value), x) in enumerate(
        zip(boxes, x_positions)
    ):
        add_box(
            axis=axis,
            x=x,
            y=y,
            width=box_width,
            height=box_height,
            label=label,
            value=value,
        )

        if i == 0:
            axis.annotate(
                "",
                xy=(x_positions[1] - 0.10, y + box_height / 2),
                xytext=(x + box_width + 0.10, y + box_height / 2),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=ARROW,
                    lw=1.15,
                    mutation_scale=10,
                    shrinkA=0,
                    shrinkB=0,
                ),
            )

            axis.text(
                3.50,
                y - 0.16,
                f"−{count(raw - retained)} excluded by quality rules",
                ha="center",
                va="top",
                fontsize=7.8,
                color=MUTED,
            )

    figure.subplots_adjust(
        left=0.02,
        right=0.98,
        top=0.98,
        bottom=0.05,
    )

    figure.savefig(
        OUT / "weather_flow.png",
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.02,
        facecolor="white",
    )

    figure.savefig(
        OUT / "weather_flow.pdf",
        bbox_inches="tight",
        pad_inches=0.02,
        facecolor="white",
    )

    plt.close(figure)


def traffic_figure() -> None:
    """Retain simple traffic-flow generation for supporting use."""
    summary = pd.read_csv(SELECTION).set_index(
        ["dataset", "step"]
    )["records"]

    annual_total = int(
        summary.loc[
            ("annual_traffic", "road_section_year_periods")
        ]
    )
    annual_wind = int(
        summary.loc[
            ("annual_traffic", "road_periods_with_wind")
        ]
    )

    daily_total = int(
        summary.loc[
            ("daily_traffic", "counter_days")
        ]
    )
    daily_wind = int(
        summary.loc[
            ("daily_traffic", "counter_days_with_daytime_wind")
        ]
    )

    figure, axes = plt.subplots(
        2,
        1,
        figsize=(7.2, 3.8),
    )

    figure.patch.set_facecolor("white")

    datasets = [
        (
            axes[0],
            "Annual traffic",
            annual_total,
            annual_wind,
        ),
        (
            axes[1],
            "Daily counter traffic",
            daily_total,
            daily_wind,
        ),
    ]

    for axis, title, total, retained in datasets:
        axis.set_facecolor("white")
        axis.set_xlim(0, 7)
        axis.set_ylim(0, 1.8)
        axis.axis("off")

        axis.text(
            0.12,
            1.58,
            title,
            fontsize=9.8,
            fontweight="semibold",
            color=TEXT,
        )

        for x, label, value in [
            (0.50, "Available records", total),
            (4.15, "With weather data", retained),
        ]:
            add_box(
                axis=axis,
                x=x,
                y=0.48,
                width=2.25,
                height=0.78,
                label=label,
                value=value,
            )

        axis.annotate(
            "",
            xy=(4.03, 0.87),
            xytext=(2.87, 0.87),
            arrowprops=dict(
                arrowstyle="-|>",
                color=ARROW,
                lw=1.15,
                mutation_scale=10,
                shrinkA=0,
                shrinkB=0,
            ),
        )

    figure.subplots_adjust(
        left=0.03,
        right=0.98,
        top=0.98,
        bottom=0.03,
        hspace=0.45,
    )

    figure.savefig(
        OUT / "traffic_flow.png",
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.02,
        facecolor="white",
    )

    figure.savefig(
        OUT / "traffic_flow.pdf",
        bbox_inches="tight",
        pad_inches=0.02,
        facecolor="white",
    )

    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=OUT,
    )
    return parser.parse_args()


def main() -> None:
    global OUT
    OUT = parse_args().output_dir
    OUT.mkdir(parents=True, exist_ok=True)

    accident_figure()
    weather_figure()
    traffic_figure()


if __name__ == "__main__":
    main()