"""Classify accidents as urban, rural, or unknown using Statistics Iceland boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from matplotlib.path import Path as MplPath
from pyproj import Transformer


ACCIDENTS_FILE = Path("archive/data_legacy_2026-07-22/processed/accidents_latlon.parquet")
RAW_ACCIDENTS_FILE = Path("data/raw/accidents/accidents_2007_2024.txt")
URBAN_GEOJSON_FILE = Path("data/raw/accidents/urban_boundaries_2020_2024.geojson")
OUT_PARQUET = Path("archive/data_legacy_2026-07-22/processed/accidents_urban_rural.parquet")
OUT_CSV = Path("archive/generated_diagnostics/accidents_urban_rural.csv")
OUT_SUMMARY = Path("archive/generated_diagnostics/urban_rural_summary.csv")
OUT_AREA_COUNTS = Path("archive/generated_diagnostics/urban_area_accident_counts.csv")
OUT_NOTES = Path("archive/generated_diagnostics/urban_rural_notes.txt")

HAGSTOFA_WFS_URL = (
    "https://gis.is/geoserver/Hagstofan/ows?"
    "service=WFS&version=1.0.0&request=GetFeature&"
    "typeName=Hagstofan:thettbylisstadir&outputFormat=application/json"
)

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


def load_accidents() -> pd.DataFrame:
    """Read prepared coordinates or derive them from the raw accident file."""
    if ACCIDENTS_FILE.exists():
        return pd.read_parquet(ACCIDENTS_FILE)
    if not RAW_ACCIDENTS_FILE.exists():
        raise FileNotFoundError(
            f"Missing both {ACCIDENTS_FILE} and {RAW_ACCIDENTS_FILE}"
        )
    accidents = pd.read_csv(RAW_ACCIDENTS_FILE, sep="\t", dtype=str)
    accidents.columns = [column.strip() for column in accidents.columns]
    for column in ["nid", "xhnit", "yhnit", "meidsli", "tegohapps", "flokkur2"]:
        accidents[column] = pd.to_numeric(accidents[column], errors="coerce")
    accidents = accidents.dropna(subset=["nid", "xhnit", "yhnit"]).copy()
    to_wgs84 = Transformer.from_crs("EPSG:3057", "EPSG:4326", always_xy=True)
    accidents["lon"], accidents["lat"] = to_wgs84.transform(
        accidents["xhnit"].to_numpy(), accidents["yhnit"].to_numpy()
    )
    ACCIDENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    accidents.to_parquet(ACCIDENTS_FILE, index=False)
    return accidents


def download_urban_boundaries() -> None:
    if URBAN_GEOJSON_FILE.exists():
        return
    URBAN_GEOJSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(HAGSTOFA_WFS_URL, timeout=60)
    response.raise_for_status()
    data = response.json()
    URBAN_GEOJSON_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


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


def load_urban_features() -> list[dict[str, Any]]:
    download_urban_boundaries()
    data = json.loads(URBAN_GEOJSON_FILE.read_text(encoding="utf-8"))
    return [normalise_feature(feature) for feature in data.get("features", [])]


def load_urban_boundary_metadata() -> dict[str, Any]:
    download_urban_boundaries()
    data = json.loads(URBAN_GEOJSON_FILE.read_text(encoding="utf-8"))
    features = data.get("features", [])
    valid_from = sorted(
        {
            (feature.get("properties") or {}).get("gildirfra")
            for feature in features
            if (feature.get("properties") or {}).get("gildirfra")
        }
    )
    valid_to = sorted(
        {
            (feature.get("properties") or {}).get("gildirtil")
            for feature in features
            if (feature.get("properties") or {}).get("gildirtil")
        }
    )
    crs = ((data.get("crs") or {}).get("properties") or {}).get("name")
    return {
        "total_features": data.get("totalFeatures", len(features)),
        "number_returned": data.get("numberReturned", len(features)),
        "timestamp": data.get("timeStamp"),
        "crs": crs,
        "bbox": data.get("bbox"),
        "valid_from_values": valid_from,
        "valid_to_values": valid_to,
        "property_fields": sorted({key for f in features for key in (f.get("properties") or {}).keys()}),
    }


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


def write_outputs(classified: pd.DataFrame, feature_count: int) -> None:
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    classified.to_parquet(OUT_PARQUET, index=False)
    classified.to_csv(OUT_CSV, index=False)

    severity = classified["severity_label"].fillna("Unknown")
    summary = (
        classified.assign(severity_label=severity)
        .groupby(["urban_rural", "severity_label"], dropna=False, observed=False)
        .size()
        .reset_index(name="accidents")
    )
    totals = summary.groupby("urban_rural")["accidents"].transform("sum")
    summary["share_within_urban_rural_pct"] = 100 * summary["accidents"] / totals
    summary.to_csv(OUT_SUMMARY, index=False)

    area_counts = (
        classified[classified["urban_rural"].eq("Urban")]
        .groupby(["urban_area_name", "urban_area_code", "urban_rural_source"], dropna=False, observed=False)
        .agg(
            accidents=("nid", "count"),
            injury_accidents=("meidsli", lambda s: int((pd.to_numeric(s, errors="coerce") < 4).sum())),
            serious_or_fatal_accidents=("meidsli", lambda s: int((pd.to_numeric(s, errors="coerce") <= 2).sum())),
            population_2020=("urban_area_population_2020", "first"),
        )
        .reset_index()
        .sort_values(["accidents", "urban_area_name"], ascending=[False, True])
    )
    area_counts.to_csv(OUT_AREA_COUNTS, index=False)

    source_counts = classified["urban_rural_source"].value_counts(dropna=False)
    metadata = load_urban_boundary_metadata()
    notes = [
        "Urban/Rural Classification Notes",
        "================================",
        f"Input accidents: {ACCIDENTS_FILE}",
        f"Input urban boundaries: {URBAN_GEOJSON_FILE}",
        f"Hagstofa WFS: {HAGSTOFA_WFS_URL}",
        "Hagstofa WFS layer: Hagstofan:thettbylisstadir",
        "Hagstofa WFS request: service=WFS, version=1.0.0, request=GetFeature, outputFormat=application/json",
        f"Hagstofa features loaded: {feature_count}",
        f"GeoJSON metadata totalFeatures: {metadata['total_features']}",
        f"GeoJSON metadata numberReturned: {metadata['number_returned']}",
        f"GeoJSON metadata timestamp: {metadata['timestamp']}",
        f"GeoJSON CRS: {metadata['crs']}",
        f"GeoJSON bbox: {metadata['bbox']}",
        f"Boundary valid-from values: {metadata['valid_from_values']}",
        f"Boundary valid-to values: {metadata['valid_to_values']}",
        f"Boundary property fields: {metadata['property_fields']}",
        f"Classified accidents: {len(classified):,}",
        "",
        "Method:",
        "Accident longitude/latitude coordinates are transformed from EPSG:4326 to EPSG:3057.",
        "An accident is classified as Urban if the projected point falls inside a Statistics Iceland",
        "urban-locality polygon from the 2020-2024 'Þéttbýlisstaðir' dataset.",
        "Valid Icelandic coordinates outside those polygons are classified as Rural.",
        "Invalid or missing coordinates are classified as Unknown.",
        "",
        "Special rule:",
        "Vestmannaeyjar is treated as Urban for the whole island/municipality area, following",
        "the supervisor's instruction. This is implemented with a documented WGS84 bounding box:",
        f"{VESTMANNAEYJAR_BBOX_WGS84}.",
        "",
        "Important limitation:",
        "The Hagstofa layer covers 2020-2024 boundaries. Earlier accidents are classified using",
        "these boundaries for consistency, so historical expansion of towns is not modelled here.",
        "",
        "Output files:",
        f"- {OUT_PARQUET}",
        f"- {OUT_CSV}",
        f"- {OUT_SUMMARY}",
        f"- {OUT_AREA_COUNTS}",
        "",
        "Classification source counts:",
        source_counts.to_string(),
        "",
        "Urban/rural severity summary:",
        summary.to_string(index=False),
    ]
    OUT_NOTES.write_text("\n".join(notes) + "\n", encoding="utf-8")
    print("\n".join(notes))


def main() -> None:
    accidents = load_accidents()
    features = load_urban_features()
    classified = classify_accidents(accidents, features)
    write_outputs(classified, len(features))


if __name__ == "__main__":
    main()
