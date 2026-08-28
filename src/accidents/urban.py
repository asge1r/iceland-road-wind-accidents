"""Classify accidents with the supplied Statistics Iceland urban boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath
from pyproj import Transformer


URBAN_GEOJSON_FILE = Path("data/raw/accidents/urban_boundaries_2020_2024.geojson")

SEVERITY_LABELS = {
    1: "Fatal accident",
    2: "Serious accident",
    3: "Minor injuries",
    4: "No injuries",
}

# Supervisor-defined special case: treat the whole Vestmannaeyjar island
# municipality area as urban, not only the built-up Hagstofa locality polygon.
VESTMANNAEYJAR_BBOX_WGS84 = {
    "lat_min": 63.34,
    "lat_max": 63.50,
    "lon_min": -20.55,
    "lon_max": -20.05,
}


def valid_iceland_coordinates(df: pd.DataFrame) -> pd.Series:
    lat = pd.to_numeric(df["lat"], errors="coerce")
    lon = pd.to_numeric(df["lon"], errors="coerce")
    return lat.between(63, 67) & lon.between(-25, -12)


def ring_bbox(ring: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def bbox_contains(bbox: tuple[float, float, float, float], x: float, y: float) -> bool:
    minx, miny, maxx, maxy = bbox
    return minx <= x <= maxx and miny <= y <= maxy


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    x1, y1 = ring[0]
    for i in range(1, n + 1):
        x2, y2 = ring[i % n]
        if min(y1, y2) <= y <= max(y1, y2) and min(x1, x2) <= x <= max(x1, x2):
            dx = x2 - x1
            dy = y2 - y1
            if abs(dy) < 1e-12 and abs(y - y1) < 1e-9:
                return True
            if abs(dx) < 1e-12 and abs(x - x1) < 1e-9:
                return True
        crosses = (y1 > y) != (y2 > y)
        if crosses:
            x_intersect = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if abs(x_intersect - x) < 1e-9:
                return True
            if x_intersect > x:
                inside = not inside
        x1, y1 = x2, y2
    return inside


def point_in_polygon(x: float, y: float, polygon: list[list[list[float]]]) -> bool:
    if not polygon or not point_in_ring(x, y, polygon[0]):
        return False
    return not any(point_in_ring(x, y, hole) for hole in polygon[1:])


def normalise_feature(feature: dict[str, Any]) -> dict[str, Any]:
    geometry = feature.get("geometry") or {}
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if geom_type == "Polygon":
        polygons = [coordinates]
    elif geom_type == "MultiPolygon":
        polygons = coordinates
    else:
        polygons = []

    polygon_bboxes = [ring_bbox(poly[0]) for poly in polygons if poly]
    minx = min(b[0] for b in polygon_bboxes)
    miny = min(b[1] for b in polygon_bboxes)
    maxx = max(b[2] for b in polygon_bboxes)
    maxy = max(b[3] for b in polygon_bboxes)
    props = feature.get("properties") or {}
    return {
        "properties": props,
        "polygons": polygons,
        "polygon_bboxes": polygon_bboxes,
        "bbox": (minx, miny, maxx, maxy),
    }


def load_urban_features(
    path: Path = URBAN_GEOJSON_FILE,
) -> list[dict[str, Any]]:
    """Load the unchanged boundary delivery required by accident preparation."""
    if not path.exists():
        raise FileNotFoundError(
            f"Missing supplied urban-boundary file: {path}. "
            "Place the source file under data/raw/ before running preparation."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    features = [normalise_feature(feature) for feature in data.get("features", [])]
    if not features:
        raise ValueError(f"No urban polygons found in {path}")
    return features


def find_urban_area(
    x: float,
    y: float,
    features: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for feature in features:
        if not bbox_contains(feature["bbox"], x, y):
            continue
        for polygon, bbox in zip(feature["polygons"], feature["polygon_bboxes"], strict=False):
            if bbox_contains(bbox, x, y) and point_in_polygon(x, y, polygon):
                return feature["properties"]
    return None


def is_vestmannaeyjar_municipality(lat: float, lon: float) -> bool:
    bbox = VESTMANNAEYJAR_BBOX_WGS84
    return (
        bbox["lat_min"] <= lat <= bbox["lat_max"]
        and bbox["lon_min"] <= lon <= bbox["lon_max"]
    )


def classify_accidents(accidents: pd.DataFrame, features: list[dict[str, Any]]) -> pd.DataFrame:
    out = accidents.copy()
    out["lat"] = pd.to_numeric(out["lat"], errors="coerce")
    out["lon"] = pd.to_numeric(out["lon"], errors="coerce")

    valid = valid_iceland_coordinates(out).to_numpy()
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3057", always_xy=True)
    xs, ys = transformer.transform(out["lon"].to_numpy(), out["lat"].to_numpy())
    points = np.column_stack([xs, ys])
    n = len(out)

    urban_rural = np.full(n, None, dtype=object)
    urban_area_name = np.full(n, None, dtype=object)
    urban_area_code = np.full(n, None, dtype=object)
    urban_area_population_2020 = np.full(n, None, dtype=object)
    urban_source = np.full(n, None, dtype=object)

    urban_rural[~valid] = "Unknown"
    urban_source[~valid] = "invalid_or_missing_coordinate"

    for feature in features:
        props = feature["properties"]
        minx, miny, maxx, maxy = feature["bbox"]
        candidate = (
            valid
            & pd.isna(urban_rural)
            & (xs >= minx)
            & (xs <= maxx)
            & (ys >= miny)
            & (ys <= maxy)
        )
        if not candidate.any():
            continue
        candidate_idx = np.flatnonzero(candidate)
        matched_idx: list[np.ndarray] = []
        for polygon, bbox in zip(feature["polygons"], feature["polygon_bboxes"], strict=False):
            pminx, pminy, pmaxx, pmaxy = bbox
            submask = (
                (xs[candidate_idx] >= pminx)
                & (xs[candidate_idx] <= pmaxx)
                & (ys[candidate_idx] >= pminy)
                & (ys[candidate_idx] <= pmaxy)
            )
            if not submask.any():
                continue
            sub_idx = candidate_idx[submask]
            inside = MplPath(np.asarray(polygon[0], dtype=float)).contains_points(points[sub_idx], radius=1e-9)
            for hole in polygon[1:]:
                if inside.any():
                    inside &= ~MplPath(np.asarray(hole, dtype=float)).contains_points(points[sub_idx], radius=1e-9)
            if inside.any():
                matched_idx.append(sub_idx[inside])
        if not matched_idx:
            continue
        idx = np.concatenate(matched_idx)
        urban_rural[idx] = "Urban"
        urban_area_name[idx] = props.get("heiti")
        urban_area_code[idx] = props.get("stadur")
        urban_area_population_2020[idx] = props.get("fjoldi_2020")
        urban_source[idx] = "hagstofa_thettbylisstadir_2020_2024"

    lat = out["lat"].to_numpy()
    lon = out["lon"].to_numpy()
    bbox = VESTMANNAEYJAR_BBOX_WGS84
    vestmannaeyjar = (
        valid
        & pd.isna(urban_rural)
        & (lat >= bbox["lat_min"])
        & (lat <= bbox["lat_max"])
        & (lon >= bbox["lon_min"])
        & (lon <= bbox["lon_max"])
    )
    urban_rural[vestmannaeyjar] = "Urban"
    urban_area_name[vestmannaeyjar] = "Vestmannaeyjar municipality"
    urban_area_code[vestmannaeyjar] = "manual_vestmannaeyjar"
    urban_source[vestmannaeyjar] = "manual_supervisor_rule"

    rural = valid & pd.isna(urban_rural)
    urban_rural[rural] = "Rural"
    urban_source[rural] = "outside_hagstofa_urban_polygon"

    out["x_3057"] = xs
    out["y_3057"] = ys
    out["urban_rural"] = urban_rural
    out["urban_area_name"] = urban_area_name
    out["urban_area_code"] = urban_area_code
    out["urban_area_population_2020"] = urban_area_population_2020
    out["urban_rural_source"] = urban_source
    out["severity_label"] = pd.to_numeric(out["meidsli"], errors="coerce").map(SEVERITY_LABELS)
    return out
