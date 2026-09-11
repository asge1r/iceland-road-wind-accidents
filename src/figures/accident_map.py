"""Map study accidents and accidents occurring in strong mean wind."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon
from pyproj import Transformer

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ACCIDENTS = Path("data/analysis/accidents.csv")
CONDITIONS = Path("data/analysis/accident_conditions.csv")
ROADS = Path("data/raw/traffic/reference/roads.geojson")
COUNTRIES = Path("data/raw/reference/countries.geojson")
OUTPUT = Path("reports/main/figures/accident_map.png")

# Icelandic projected coordinates -> longitude/latitude.
TRANSFORMER = Transformer.from_crs(
    "EPSG:3057",
    "EPSG:4326",
    always_xy=True,
)


def transform_line(coordinates):
    """Convert a GeoJSON line from EPSG:3057 to longitude/latitude."""
    xs = [point[0] for point in coordinates]
    ys = [point[1] for point in coordinates]
    lon, lat = TRANSFORMER.transform(xs, ys)
    return lon, lat


def plot_roads(axis, path: Path) -> None:
    """Plot official road geometry as a faint geographic backdrop."""
    with path.open("r", encoding="utf-8") as file:
        road_data = json.load(file)

    for feature in road_data.get("features", []):
        geometry = feature.get("geometry")
        if not geometry:
            continue

        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")

        if not coordinates:
            continue

        if geometry_type == "LineString":
            lon, lat = transform_line(coordinates)

            axis.plot(
                lon,
                lat,
                color="#AEB6BA",
                linewidth=0.28,
                alpha=0.25,
                zorder=1,
            )

        elif geometry_type == "MultiLineString":
            for line in coordinates:
                lon, lat = transform_line(line)

                axis.plot(
                    lon,
                    lat,
                    color="#AEB6BA",
                    linewidth=0.28,
                    alpha=0.25,
                    zorder=1,
                )


def plot_iceland(axis, path: Path) -> None:
    """Plot Iceland's national outline from the country GeoJSON file."""
    with path.open("r", encoding="utf-8") as file:
        countries = json.load(file)

    iceland = None

    for feature in countries.get("features", []):
        properties = feature.get("properties", {})

        # The downloaded dataset commonly stores the country as ADMIN.
        names = {
            str(properties.get("ADMIN", "")),
            str(properties.get("name", "")),
            str(properties.get("NAME", "")),
        }

        if "Iceland" in names:
            iceland = feature
            break

    if iceland is None:
        raise ValueError("Could not find Iceland in countries.geojson")

    geometry = iceland.get("geometry")
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    def add_polygon(polygon_coordinates):
        # First ring is the exterior boundary.
        exterior = polygon_coordinates[0]

        patch = Polygon(
            exterior,
            closed=True,
            facecolor="#F4F5F5",
            edgecolor="#9EA7AB",
            linewidth=0.8,
            zorder=0,
        )
        axis.add_patch(patch)

    if geometry_type == "Polygon":
        add_polygon(coordinates)

    elif geometry_type == "MultiPolygon":
        for polygon in coordinates:
            add_polygon(polygon)

    else:
        raise ValueError(
            f"Unexpected Iceland geometry type: {geometry_type}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-c", "--conditions", type=Path, default=CONDITIONS)
    parser.add_argument("-r", "--roads", type=Path, default=ROADS)
    parser.add_argument(
        "--countries",
        type=Path,
        default=COUNTRIES,
    )
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    accidents = pd.read_csv(
        args.accidents,
        usecols=["id", "lon", "lat"],
    )

    conditions = pd.read_csv(
        args.conditions,
        usecols=[
            "id",
            "f",
            "weather_station_dist_km",
            "weather_time_difference_minutes",
        ],
    )

    data = accidents.merge(
        conditions,
        on="id",
        validate="one_to_one",
    )

    strong = (
        data["f"].ge(15)
        & data["weather_station_dist_km"].le(20)
        & data["weather_time_difference_minutes"].le(5)
    )

    figure, axis = plt.subplots(
        figsize=(9.2, 7.0),
        constrained_layout=True,
    )

    # National outline underneath everything else.
    plot_iceland(axis, args.countries)

    # Official road network.
    plot_roads(axis, args.roads)

    # Ordinary rural injury accidents.
    axis.scatter(
        data.loc[~strong, "lon"],
        data.loc[~strong, "lat"],
        s=6,
        color="#567A96",
        alpha=0.30,
        linewidths=0,
        rasterized=True,
        zorder=2,
        label=f"Other rural injury accidents (n={(~strong).sum():,})",
    )

    # Accidents occurring during strong mean wind.
    axis.scatter(
        data.loc[strong, "lon"],
        data.loc[strong, "lat"],
        s=25,
        color="#B85C4A",
        alpha=0.92,
        linewidths=0,
        zorder=3,
        label=f"Mean wind ≥15 m/s (n={strong.sum():,})",
    )

    axis.set_xlim(-25, -13)
    axis.set_ylim(63.2, 66.7)

    # Approximate longitude/latitude aspect correction at Iceland's latitude.
    mid_latitude = 65.0
    axis.set_aspect(1 / np.cos(np.deg2rad(mid_latitude)))

    axis.set_xlabel("Longitude", fontsize=11)
    axis.set_ylabel("Latitude", fontsize=11)
    axis.tick_params(axis="both", labelsize=9)

    axis.grid(
        alpha=0.07,
        linewidth=0.6,
    )

    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)

    axis.legend(
        frameon=False,
        loc="lower left",
        bbox_to_anchor=(0.03, 0.03),
        fontsize=9.5,
        markerscale=1.25,
        handletextpad=0.5,
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure.savefig(
        args.output,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.05,
    )

    plt.close(figure)

    print(f"strong_wind_accidents={strong.sum():,}")
    print(f"other_accidents={(~strong).sum():,}")
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()