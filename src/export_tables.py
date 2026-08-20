"""Export small, readable canonical analysis files from local caches."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path("data/processed")


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required cache: {path}")
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


def write_csv(frame: pd.DataFrame, path: Path) -> int:
    frame.to_csv(path, index=False)
    return len(frame)


def export_accidents(output: Path) -> tuple[int, list[str]]:
    source = read_table(ROOT / "accidents/rural_injury_accidents.parquet").copy()
    source["year"] = pd.to_datetime(source["timestamp"], errors="coerce").dt.year
    source["primary_wind_match"] = source["wind_available"].fillna(False) & source["within_20km"].fillna(False) & source["weather_time_difference_minutes"].le(5)
    vehicle_sources = [
        (Path("data/raw/accidents/vehicles_2007_2024.txt"), "nid", "taeki"),
        (Path("data/raw/accidents/vehicles_2025.txt"), "NID", "Nr. Ökutækis"),
    ]
    vehicle_frames = []
    for path, identifier, vehicle in vehicle_sources:
        if path.exists():
            frame = pd.read_csv(path, sep="\t", usecols=[identifier, vehicle])
            vehicle_frames.append(frame.rename(columns={identifier: "nid", vehicle: "vehicle_id"}))
    if vehicle_frames:
        vehicles = pd.concat(vehicle_frames, ignore_index=True)
        vehicles["nid"] = pd.to_numeric(vehicles["nid"], errors="coerce")
        vehicle_count = vehicles.dropna(subset=["nid"]).groupby("nid")["vehicle_id"].nunique()
        source = source.join(vehicle_count.rename("vehicle_count"), on="nid")
        source["vehicle_group"] = source["vehicle_count"].map(
            lambda value: "1 vehicle" if value == 1 else "2 or more vehicles"
        )
    columns = [
        "nid",
        "timestamp",
        "meidsli",
        "tegohapps",
        "vehicle_count",
        "weather_station_id",
        "weather_station_dist_km",
        "weather_time_difference_minutes",
        "f",
        "fg",
    ]
    available = [column for column in columns if column in source]
    return write_csv(source[available], output / "accidents.csv"), available


def export_frequency(output: Path) -> tuple[int, list[str]]:
    source = read_table(ROOT / "weather/wind_frequency_station_year_season.parquet").copy()
    source = source.rename(
        columns={"bin_lower_ms": "bin_lower", "bin_upper_ms": "bin_upper"}
    )
    source["unit"] = source["variable"].map(
        {
            "f": "m/s",
            "f_5m": "m/s",
            "fg": "m/s",
            "fg_minus_f": "m/s",
            "gust_factor": "ratio",
        }
    )
    columns = [
        "station", "year", "season", "variable", "bin_label", "unit",
        "measurement_count", "total_measurements_in_period",
    ]
    available = [column for column in columns if column in source]
    tidy = source.sort_values(
        ["station", "year", "season", "variable", "bin_lower"]
    )[available]
    return write_csv(tidy, output / "weather_frequency.csv"), available


def export_stations(output: Path) -> tuple[int, list[str]]:
    source = pd.read_csv(ROOT / "weather/stations.csv")
    columns = [column for column in ["station", "name", "lat", "lon"] if column in source]
    return write_csv(source[columns], output / "stations.csv"), columns


def export_annual_traffic(output: Path) -> tuple[int, list[str]]:
    source = pd.read_csv(ROOT / "traffic/annual_road_section_exposure.csv", low_memory=False)
    columns = [column for column in ["year", "road_section", "section_length_km", "adu", "sdu", "vdu"] if column in source]
    return write_csv(source[columns], output / "annual_traffic.csv"), columns


def display_number(value: object, decimals: int = 1) -> str:
    if pd.isna(value):
        return "not available"
    return f"{float(value):.{decimals}f}"


def write_daily_text(source: pd.DataFrame, output: Path) -> None:
    lines: list[str] = []
    for counter, group in source.groupby("counter_site_id", sort=True):
        first = group.iloc[0]
        station = display_number(first.get("weather_station_id"), 0)
        lines.extend([f"counter: {counter}", f"road-section: {first.get('road_section', 'not available')}", f"road-station-m: {first.get('road_station_m', 'not available')}", "coordinates-epsg3057: " + f"{display_number(first.get('location_x_3057'), 0)} {display_number(first.get('location_y_3057'), 0)}", f"location-method: {first.get('location_method', 'not available')}", f"weather-station: {station} {first.get('weather_station_name', 'not available')}", f"weather-station-distance-km: {display_number(first.get('weather_station_dist_km'))}", "date traffic f-daytime-mean-m-s fg-daytime-max-m-s"])
        for row in group.itertuples(index=False):
            date = pd.Timestamp(row.date).date().isoformat()
            lines.append(f"{date} {display_number(row.traffic_volume, 0)} {display_number(row.f_daytime_mean)} {display_number(row.fg_daytime_max)}")
        lines.append("")
    (output / "daily.txt").write_text("\n".join(lines), encoding="utf-8")


def export_daily_traffic(output: Path) -> tuple[int, list[str]] | None:
    path = ROOT / "traffic/daily_traffic_weather.parquet"
    if not path.exists():
        return None
    source = read_table(path).rename(columns={"station_id": "road_station_m"})
    text_columns = ["date", "year", "counter_site_id", "road_section", "road_station_m", "traffic_volume", "location_x_3057", "location_y_3057", "location_method", "weather_station_id", "weather_station_name", "weather_station_dist_km", "f_daytime_mean", "fg_daytime_max", "typical_traffic", "traffic_index"]
    text_columns = [column for column in text_columns if column in source]
    readable = source[text_columns].sort_values(["counter_site_id", "date"])
    csv_columns = [
        "date", "counter_site_id", "road_section", "traffic_volume",
        "location_method", "weather_station_id", "weather_station_dist_km",
        "f_daytime_mean", "fg_daytime_max",
    ]
    csv_columns = [column for column in csv_columns if column in readable]
    daily = readable[csv_columns].copy()
    if "traffic_volume" in daily:
        daily["traffic_volume"] = daily["traffic_volume"].round().astype("Int64")
    count = write_csv(daily, output / "daily_traffic.csv")
    write_daily_text(readable, output)
    return count, csv_columns


def write_readme(output: Path, daily_present: bool) -> None:
    daily_text = "`daily.txt` is a human-readable counter-by-counter companion generated from the same source table as `daily_traffic.csv`." if daily_present else "Daily traffic files are added when the local daily-PDF cache is available."
    accidents = pd.read_csv(output / "accidents.csv", usecols=["timestamp"])
    years = pd.to_datetime(accidents["timestamp"], errors="coerce").dt.year.dropna()
    period = f"{int(years.min())}–{int(years.max())}"
    text = "# Canonical analysis data\n\nThis directory is the compact, inspectable data layer for the thesis. Files are generated from local `data/raw/` sources and `data/processed/` caches by `python -m src.export_tables`. Do not edit them by hand.\n\n- `accidents.csv`: the " + period + " rural injury-accident study sample and its weather match.\n- `weather_frequency.csv`: station, year and season wind-bin counts used as O/E exposure. `f` and `fg` are in m/s; `gust_factor` is the unitless ratio `fg / f` and is defined only when `f >= 3 m/s`.\n- `stations.csv`: weather-station identifiers and coordinates.\n- `annual_traffic.csv`: annual road-section traffic exposure (ADU, SDU and VDU).\n- `daily_traffic.csv`: daily count, road location and matched daytime wind used in the 2019–2024 traffic analysis.\n- " + daily_text + "\n- `manifest.csv`: row counts, origin and column lists.\n"
    (output / "README.md").write_text(text, encoding="utf-8")


def write_manifest(output: Path, entries: list[tuple[str, int, str, list[str]]]) -> None:
    manifest = pd.DataFrame(entries, columns=["file", "records", "source_cache", "columns"])
    manifest["columns"] = manifest["columns"].str.join(", ")
    manifest.to_csv(output / "manifest.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=Path("data/analysis"), help="Output directory.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, int, str, list[str]]] = []
    for filename, source, exporter in [("accidents.csv", "accidents/rural_injury_accidents.parquet", export_accidents), ("weather_frequency.csv", "weather/wind_frequency_station_year_season.parquet", export_frequency), ("stations.csv", "weather/stations.csv", export_stations), ("annual_traffic.csv", "traffic/annual_road_section_exposure.csv", export_annual_traffic)]:
        records, columns = exporter(args.output)
        entries.append((filename, records, source, columns))
    daily = export_daily_traffic(args.output)
    if daily:
        records, columns = daily
        entries.extend([("daily_traffic.csv", records, "traffic/daily_traffic_weather.parquet", columns), ("daily.txt", records, "traffic/daily_traffic_weather.parquet", ["counter metadata", "date", "traffic", "daytime wind"])])
    write_readme(args.output, daily is not None)
    entries.append(("README.md", 0, "export_tables.py", ["file descriptions", "rebuild instruction"]))
    entries.append(("manifest.csv", len(entries) + 1, "export_tables.py", ["file", "records", "source_cache", "columns"]))
    write_manifest(args.output, entries)
    print(f"Wrote {len(entries)} canonical files to {args.output}")


if __name__ == "__main__":
    main()
