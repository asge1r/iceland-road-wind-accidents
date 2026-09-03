"""Draw three source-to-analysis selection flow figures."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd


OUT = Path("reports/main/figures")
SELECTION = Path("data/analysis/selection_summary.csv")
WEATHER_AUDIT = Path("reports/main/tables/weather_cleaning_audit.csv")

KEEP = "#5F8F78"
DROP = "#C96A5B"
TEXT = "#263238"


def count(value: int) -> str:
    return f"{value:,}"


def draw_flow(axis, boxes: list[tuple[str, int, str]]) -> None:
    """Render one retained-data flow on a supplied axis."""
    axis.set_xlim(0, len(boxes) * 3.1)
    axis.set_ylim(-1.2, 1.3)
    axis.axis("off")
    for index, (label, value, loss) in enumerate(boxes):
        x = index * 3.1 + 0.1
        patch = FancyBboxPatch(
            (x, 0), 2.6, 0.8, boxstyle="round,pad=0.05,rounding_size=0.08",
            facecolor=KEEP, edgecolor="white", linewidth=1.5,
        )
        axis.add_patch(patch)
        axis.text(x + 1.3, 0.53, label, ha="center", va="center", fontsize=10, weight="bold", color="white")
        axis.text(x + 1.3, 0.22, f"n = {count(value)}", ha="center", va="center", fontsize=11, color="white")
        if index:
            axis.annotate("", xy=(x - 0.1, 0.4), xytext=(x - 0.45, 0.4), arrowprops={"arrowstyle": "->", "color": TEXT, "lw": 1.8})
            if loss:
                axis.text(x - 0.28, -0.3, loss, ha="center", va="top", fontsize=8.5, color=DROP, wrap=True)

def flow(path: Path, title: str, boxes: list[tuple[str, int, str]]) -> None:
    """Render a one-row flow: retained steps above, main loss below arrows."""
    figure, axis = plt.subplots(figsize=(14, 3.8), constrained_layout=True)
    draw_flow(axis, boxes)
    axis.set_title(title, loc="left", fontsize=15, weight="bold", color=TEXT)
    figure.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(figure)


def accident_figure() -> None:
    summary = pd.read_csv(SELECTION).set_index(["dataset", "step"])["records"]
    valid_coordinates = int(summary.loc[("accidents", "valid_time_and_coordinates")])
    rural = int(summary.loc[("accidents", "rural_accidents")])
    study = int(summary.loc[("accidents", "rural_injury_accidents")])
    matched = int(summary.loc[("accidents", "primary_wind_oe_sample")])
    flow(
        OUT / "accident_flow.png",
        "Accident selection, 2007–2025",
        [
            ("Valid accident time and coordinates", valid_coordinates, ""),
            ("Rural accidents", rural, f"{count(valid_coordinates - rural)} urban"),
            ("Rural injury accidents", study, f"{count(rural - study)} damage-only"),
            ("Primary wind O/E sample", matched, f"{count(study - matched)} without wind match within 20 km"),
        ],
    )


def weather_figure() -> None:
    audit = pd.read_csv(WEATHER_AUDIT)
    raw = int(audit.loc[audit.metric.eq("raw_10_minute_rows"), "value"].iloc[0])
    wind_capable = raw - int(
        audit.loc[audit.metric.eq("station_year_without_wind_data"), "value"].iloc[0]
    )
    retained = int(audit.loc[audit.metric.eq("clean_wind_rows"), "value"].iloc[0])
    no_wind_year = raw - wind_capable
    missing = int(audit.loc[audit.metric.eq("missing_wind_in_wind_capable_station_year"), "value"].iloc[0])
    inconsistent = int(audit.loc[audit.metric.eq("fg_zero_with_positive_f"), "value"].iloc[0]) + int(
        audit.loc[audit.metric.eq("fg_below_f_beyond_tolerance"), "value"].iloc[0]
    )
    frozen = int(audit.loc[audit.metric.eq("frozen_zero_runs"), "value"].iloc[0])
    quality_excluded = wind_capable - retained
    invalid = quality_excluded - missing - inconsistent - frozen
    flow(
        OUT / "weather_flow.png",
        "Weather-data selection, 2007–2025",
        [
            ("Raw station-time records", raw, ""),
            ("Station-years with wind data", wind_capable, f"{count(no_wind_year)} from station-years without wind data"),
            (
                "Clean wind observations", retained,
                f"{count(quality_excluded)} excluded by quality rules\n"
                f"{count(missing)} missing; {count(invalid)} negative or above threshold; "
                f"{count(inconsistent)} inconsistent; {count(frozen)} frozen zero runs",
            ),
        ],
    )


def traffic_figure() -> None:
    summary = pd.read_csv(SELECTION).set_index(["dataset", "step"])["records"]
    annual_total = int(summary.loc[("annual_traffic", "road_section_year_periods")])
    annual_wind = int(summary.loc[("annual_traffic", "road_periods_with_wind")])
    daily_total = int(summary.loc[("daily_traffic", "counter_days")])
    daily_wind = int(summary.loc[("daily_traffic", "counter_days_with_daytime_wind")])
    figure, axes = plt.subplots(2, 1, figsize=(10.5, 6.2), constrained_layout=True)
    draw_flow(
        axes[0],
        [
            ("Annual road-period records", annual_total, ""),
            ("Road-periods with nearby wind", annual_wind, f"{count(annual_total - annual_wind)} without nearby clean wind"),
        ],
    )
    axes[0].set_title("Annual traffic: road-section comparison", loc="left", fontsize=11, weight="bold", color=TEXT)
    draw_flow(
        axes[1],
        [
            ("Daily counter-days, 2019–2024", daily_total, ""),
            ("Daily counter-days with daytime wind", daily_wind, f"{count(daily_total - daily_wind)} without daytime wind"),
        ],
    )
    axes[1].set_title("Daily counter traffic: travel-demand diagnostic", loc="left", fontsize=11, weight="bold", color=TEXT)
    figure.suptitle("Traffic data selection", x=0.01, ha="left", fontsize=15, weight="bold", color=TEXT)
    figure.savefig(OUT / "traffic_flow.png", dpi=240, bbox_inches="tight")
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=OUT,
        help="Directory for the three PNG figures (default: %(default)s).",
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
