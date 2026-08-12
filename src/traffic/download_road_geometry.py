"""Download official road-section geometry for daily-counter locations.

The Icelandic Road and Coastal Administration MapServer/6 layer supplies road
geometry and the official start/end road stations.  The downloaded GeoJSON is
an unchanged local reference input, not a processed analysis output.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


LAYER_URL = (
    "https://vegasja.vegagerdin.is/arcgis/rest/services/data/vegakerfi/"
    "MapServer/6/query"
)
PAGE_SIZE = 500
DEFAULT_OUTPUT = Path("data/raw/traffic/reference/roads.geojson")


def fetch_json(parameters: dict[str, object]) -> dict[str, object]:
    """Request one JSON/GeoJSON page and fail clearly on a service error."""
    with urlopen(f"{LAYER_URL}?{urlencode(parameters)}", timeout=120) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload


def download() -> dict[str, object]:
    """Download every road-section feature, checking that pagination is complete."""
    count = int(fetch_json({"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"])
    features: list[object] = []
    for offset in range(0, count, PAGE_SIZE):
        page = fetch_json(
            {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "3057",
                "orderByFields": "OBJECTID",
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE,
                "f": "geojson",
            }
        )
        page_features = page.get("features", [])
        features.extend(page_features)
        print(f"Downloaded {len(features):,}/{count:,} road sections", flush=True)
        if not page_features:
            break
    if len(features) != count:
        raise RuntimeError(f"Expected {count:,} road sections but received {len(features):,}.")
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    roads = download()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(roads, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(roads['features']):,} official road sections to {args.output}")


if __name__ == "__main__":
    main()
