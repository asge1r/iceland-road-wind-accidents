"""Clip official road-station lengths to the accident study's rural area."""

from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import substring, transform, unary_union

from src.accidents.urban import load_urban_features, VESTMANNAEYJAR_BBOX_WGS84
from src.traffic.locate_counters import geometry_sequences, interpolate, load_roads


def urban_geometry(path: Path):
    polygons = [Polygon(polygon[0], polygon[1:])
                for feature in load_urban_features(path)
                for polygon in feature["polygons"]]
    bbox = VESTMANNAEYJAR_BBOX_WGS84
    island = box(bbox["lon_min"], bbox["lat_min"], bbox["lon_max"], bbox["lat_max"])
    project = Transformer.from_crs(4326, 3057, always_xy=True).transform
    polygons.append(transform(project, island))
    if not all(polygon.is_valid for polygon in polygons):
        raise ValueError("Invalid urban boundary geometry")
    return unary_union(polygons)


def clipped_lengths(features, start_m: float, end_m: float, urban) -> tuple[float, float]:
    """Return rural and unmapped km; preserve official station-distance units.

    Split at feature boundaries and use the first covering feature, like the
    counter-location interpolator. MultiLineString gaps are never bridged.
    """
    prepared = []
    boundaries = {start_m, end_m}
    for feature in features:
        props = feature["properties"]
        start, end = float(props["KAFLISTODUPPHAF"]), float(props["KAFLISTODENDIR"])
        lines = [LineString(sequence) for sequence in geometry_sequences(feature["geometry"])
                 if len(sequence) >= 2]
        length = sum(line.length for line in lines)
        if end <= start or length <= 0:
            continue
        prepared.append((start, end, lines, length))
        boundaries.update(value for value in (start, end) if start_m < value < end_m)
    rural_m = unknown_m = 0.
    edges = sorted(boundaries)
    for left, right in zip(edges, edges[1:]):
        feature = next((item for item in prepared if item[0] <= left and item[1] >= right), None)
        if feature is None:
            unknown_m += right - left
            continue
        start, end, lines, length = feature
        a, b = (left - start) / (end - start) * length, (right - start) / (end - start) * length
        offset = 0.
        for line in lines:
            lo, hi = max(a - offset, 0.), min(b - offset, line.length)
            if hi > lo:
                piece = substring(line, lo, hi)
                rural_m += piece.difference(urban).length * (end - start) / length
            offset += line.length
    return rural_m / 1000, unknown_m / 1000


def add_rural_lengths(sections: pd.DataFrame, roads_path: Path, urban_path: Path) -> pd.DataFrame:
    roads, urban = load_roads(roads_path), urban_geometry(urban_path)
    cache = {}
    lengths = []
    for row in sections.itertuples(index=False):
        start, end = row.counter_section_start_km, row.counter_section_end_km
        key = (row.road_section, start, end)
        if not np.isfinite(start) or not np.isfinite(end) or end <= start:
            lengths.append((np.nan, np.nan))
            continue
        if key not in cache:
            features = roads.get(tuple(row.road_section.split("-", 1)), [])
            cache[key] = clipped_lengths(features, start * 1000, end * 1000, urban)
        lengths.append(cache[key])
    result = sections.copy()
    result[["rural_section_length_km", "unmapped_section_length_km"]] = lengths
    usable = result.dropna(subset=["counter_section_length_km"])
    if (usable.rural_section_length_km.lt(0).any()
            or (usable.rural_section_length_km + usable.unmapped_section_length_km
                > usable.counter_section_length_km + 1e-8).any()):
        raise ValueError("Clipped lengths exceed their official counter-section length")
    return result


def on_rural_road(accidents: pd.DataFrame, roads_path: Path, urban_path: Path) -> pd.Series:
    """Require the projected accident road position to belong to rural exposure."""
    roads, urban = load_roads(roads_path), urban_geometry(urban_path)
    eligible = []
    for row in accidents.itertuples(index=False):
        point = None
        for feature in roads.get(tuple(row.road_section.split("-", 1)), []):
            try:
                point = Point(interpolate(feature, row.accident_station_m))
                break
            except ValueError:
                continue
        eligible.append(point is not None and not urban.covers(point))
    return pd.Series(eligible, index=accidents.index)
