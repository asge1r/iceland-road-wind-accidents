"""Build the canonical accident table directly from immutable source files."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from pyproj import Transformer

from src.accidents.urban import SEVERITY_LABELS, classify_accidents, load_urban_features


RAW_2007_2024 = Path("data/raw/accidents/accidents_2007_2024.txt")
RAW_2025 = Path("data/raw/accidents/accidents_2025.txt")
RAW_ROAD_LINKS = Path("data/raw/accidents/road_links_2007_2025.txt")
VEHICLE_SOURCES = [
    (Path("data/raw/accidents/vehicles_2007_2024.txt"), "nid", "taeki"),
    (Path("data/raw/accidents/vehicles_2025.txt"), "NID", "Nr. Ökutækis"),
]
DEFAULT_OUTPUT = Path("data/processed/accidents/all_accidents_enriched.parquet")
DEFAULT_RURAL_INJURY = Path("data/processed/accidents/rural_injury_accidents_base.parquet")


def read_accident_file(path: Path, newer_format: bool) -> pd.DataFrame:
    """Read one source delivery and standardise only column names and types."""
    source = pd.read_csv(path, sep="\t", dtype=str)
    source.columns = [column.strip() for column in source.columns]
    names = (
        {
            "nid": "nid", "Dagsetning": "date_text", "Tími": "time_text",
            "xhnit": "x_3057", "yhnit": "y_3057", "meidsli": "meidsli",
            "tegohapps": "tegohapps", "stadsetn": "stadsetn",
        }
        if not newer_format
        else {
            "NID": "nid", "Dagsetning": "date_text", "Tími": "time_text",
            "Xhnit": "x_3057", "Yhnit": "y_3057", "Meiðsli": "meidsli",
            "Tegund óhapps": "tegohapps", "Staðsetning": "stadsetn",
        }
    )
    missing = set(names) - set(source.columns)
    if missing:
        raise ValueError(f"{path} is missing expected source columns: {sorted(missing)}")
    accidents = source[list(names)].rename(columns=names).copy()
    for column in ["nid", "x_3057", "y_3057", "meidsli", "tegohapps"]:
        accidents[column] = pd.to_numeric(accidents[column], errors="coerce")
    accidents["timestamp"] = pd.to_datetime(
        accidents["date_text"].fillna("") + " " + accidents["time_text"].fillna(""),
        format="%d.%m.%Y %H:%M:%S:%f",
        errors="coerce",
    ).dt.floor("s")
    return accidents.dropna(subset=["nid", "timestamp", "x_3057", "y_3057"]).copy()


def add_coordinates(accidents: pd.DataFrame) -> pd.DataFrame:
    transformer = Transformer.from_crs("EPSG:3057", "EPSG:4326", always_xy=True)
    output = accidents.copy()
    output["lon"], output["lat"] = transformer.transform(
        output["x_3057"].to_numpy(), output["y_3057"].to_numpy()
    )
    return output


def add_road_links(accidents: pd.DataFrame, links_path: Path) -> pd.DataFrame:
    """Attach the supplied NID road-link record without spatially snapping crashes."""
    links = pd.read_csv(links_path, sep="\t", dtype=str)
    links.columns = [column.strip() for column in links.columns]
    links = links.rename(columns={"nid": "nid", "dagstimi": "road_link_datetime", "sveitavegur": "registered_road_section", "borgarnumer": "registered_urban_code"})
    links["nid"] = pd.to_numeric(links["nid"], errors="coerce")
    links = links.dropna(subset=["nid"]).drop_duplicates("nid", keep="last")
    links["registered_road_section"] = links["registered_road_section"].astype("string").str.strip().str.lower()
    road_parts = links["registered_road_section"].str.extract(r"^(?P<registered_road_number>\d+)-(?P<registered_road_part>[a-z0-9]+)$")
    links = pd.concat([links, road_parts], axis=1)
    links["is_registered_urban_code"] = links["registered_urban_code"].notna()
    return accidents.merge(links, on="nid", how="left", validate="one_to_one")


def add_vehicle_count(accidents: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for path, identifier, vehicle in VEHICLE_SOURCES:
        if path.exists():
            source = pd.read_csv(path, sep="\t", usecols=[identifier, vehicle])
            frames.append(source.rename(columns={identifier: "nid", vehicle: "vehicle_id"}))
    if not frames:
        raise FileNotFoundError("No supplied vehicle data file was found")
    vehicles = pd.concat(frames, ignore_index=True)
    vehicles["nid"] = pd.to_numeric(vehicles["nid"], errors="coerce")
    counts = vehicles.dropna(subset=["nid"]).groupby("nid")["vehicle_id"].nunique()
    output = accidents.join(counts.rename("vehicle_count"), on="nid")
    output["vehicle_count"] = output["vehicle_count"].astype("Int64")
    return output


def prepare(include_2025: bool, output: Path, rural_output: Path) -> None:
    frames = [read_accident_file(RAW_2007_2024, newer_format=False)]
    if include_2025:
        frames.append(read_accident_file(RAW_2025, newer_format=True))
    accidents = pd.concat(frames, ignore_index=True).drop_duplicates("nid", keep="last")
    accidents = add_vehicle_count(add_road_links(add_coordinates(accidents), RAW_ROAD_LINKS))
    accidents = classify_accidents(accidents, load_urban_features())
    accidents["date"] = accidents["timestamp"].dt.date.astype(str)
    accidents["hour"] = accidents["timestamp"].dt.hour.astype("Int64")
    accidents["severity"] = accidents["meidsli"].map(SEVERITY_LABELS)
    accidents = accidents.sort_values(["timestamp", "nid"]).reset_index(drop=True)
    if accidents["nid"].duplicated().any():
        raise ValueError("Canonical accident output contains duplicate nid values.")

    output.parent.mkdir(parents=True, exist_ok=True)
    rural_output.parent.mkdir(parents=True, exist_ok=True)
    accidents.to_parquet(output, index=False, compression="zstd")
    rural = accidents[accidents["urban_rural"].eq("Rural") & accidents["meidsli"].lt(4)].copy()
    rural.to_parquet(rural_output, index=False, compression="zstd")
    print(
        f"Wrote {len(accidents):,} accidents ({accidents['timestamp'].min():%Y}–{accidents['timestamp'].max():%Y}) to {output}; "
        f"rural injury accidents: {len(rural):,}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-y", "--include-2025", action="store_true", help="Add the separate 2025 source delivery.")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "-r", "--rural-output", type=Path, default=DEFAULT_RURAL_INJURY,
        help="Pre-weather rural injury subset; the weather-matched canonical file is written by match_weather.",
    )
    args = parser.parse_args()
    prepare(args.include_2025, args.output, args.rural_output)


if __name__ == "__main__":
    main()
