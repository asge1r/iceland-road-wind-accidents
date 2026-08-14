"""Draw three source-to-analysis selection flow figures."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd


OUT = Path("reports/main/figures")
ACCIDENTS = Path("data/processed/accidents/all_accidents_enriched.parquet")
STUDY = Path("data/processed/accidents/rural_injury_accidents.parquet")
WEATHER_AUDIT = Path("reports/main/tables/weather_cleaning_audit.csv")
ROAD_COVERAGE = Path("reports/main/tables/road_coverage.csv")
DAILY_TRAFFIC = Path("data/processed/traffic/daily_traffic_weather.parquet")

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
    all_accidents = pd.read_parquet(ACCIDENTS)
    study = pd.read_parquet(STUDY)
    valid_coordinates = int(all_accidents["urban_rural"].ne("Unknown").sum())
    rural = int(all_accidents["urban_rural"].eq("Rural").sum())
    matched = int((study["weather_station_dist_km"].le(20) & study["f"].notna() & study["fg"].notna()).sum())
    flow(
        OUT / "accident_flow.png",
        "Accident selection, 2007–2024",
        [
            ("Valid accident time and coordinates", valid_coordinates, ""),
            ("Rural accidents", rural, f"{count(valid_coordinates - rural)} urban"),
            ("Rural injury accidents", len(study), f"{count(rural - len(study))} damage-only"),
            ("Primary wind O/E sample", matched, f"{count(len(study) - matched)} without wind match within 20 km"),
        ],
    )


def weather_figure() -> None:
    audit = pd.read_csv(WEATHER_AUDIT)
    raw = int(audit.loc[audit.metric.eq("raw_10_minute_rows"), "value"].iloc[0])
    nonwind = int(audit.loc[audit.metric.eq("station_year_without_wind_data"), "value"].iloc[0])
    retained = int(audit.loc[audit.metric.eq("clean_wind_rows"), "value"].iloc[0])
    excluded = raw - nonwind - retained
    flow(
        OUT / "weather_flow.png",
        "Weather-data selection, 2007–2025",
        [
            ("Raw station-time records", raw, ""),
            ("Wind-capable station-years", raw - nonwind, f"{count(nonwind)} from station-years without wind data"),
            ("Clean wind observations", retained, f"{count(excluded)} excluded by wind-quality rules"),
        ],
    )


def traffic_figure() -> None:
    road = pd.read_csv(ROAD_COVERAGE).set_index("metric")["value"]
    daily = pd.read_parquet(DAILY_TRAFFIC)
    daily_wind = int(daily["f_daytime_mean"].notna().sum())
    figure, axes = plt.subplots(2, 1, figsize=(10.5, 6.2), constrained_layout=True)
    draw_flow(
        axes[0],
        [
            ("Annual road-period records", int(road["road_section_year_traffic_periods"]), ""),
            ("Road-periods with nearby wind", int(road["periods_with_wind_frequency"]), f"{count(int(road["road_section_year_traffic_periods"] - road["periods_with_wind_frequency"]))} without nearby clean wind"),
        ],
    )
    axes[0].set_title("Annual traffic exposure: road-section sensitivity analysis", loc="left", fontsize=11, weight="bold", color=TEXT)
    draw_flow(
        axes[1],
        [
            ("Daily counter-days, 2019–2024", len(daily), ""),
            ("Daily counter-days with daytime wind", daily_wind, f"{count(len(daily) - daily_wind)} without daytime wind"),
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
