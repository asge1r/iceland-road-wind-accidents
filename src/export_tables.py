"""Export small, readable canonical analysis files from prepared local data."""

from __future__ import annotations

import argparse
import calendar
from pathlib import Path

import pandas as pd


ROOT = Path("data/processed")

PERIOD_MONTHS = {
    "VDU": [12, 1, 2, 3],
    "SDU": [6, 7, 8, 9],
    "VHDU": [4, 5, 10, 11],
}


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required prepared file: {path}")
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


def write_csv(frame: pd.DataFrame, path: Path) -> int:
    frame.to_csv(path, index=False)
    return len(frame)


def days_in_traffic_period(year: int, traffic_period: str) -> int:
    return sum(calendar.monthrange(int(year), month)[1] for month in PERIOD_MONTHS[traffic_period])


def export_accidents(output: Path) -> tuple[int, list[str]]:
    source = read_table(ROOT / "accidents/rural_injury.parquet").copy()
    source = source.rename(columns={"nid": "id"})
    source["weather_station_id"] = pd.to_numeric(
        source["weather_station_id"], errors="coerce"
    ).astype("Int64")
    columns = [
        "id",
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
    source = read_table(ROOT / "weather/frequency.parquet").copy()
    source = source[source["variable"].isin(["f", "fg", "gust_factor"])].copy()
    source["unit"] = source["variable"].map({"f": "m/s", "fg": "m/s", "gust_factor": "ratio"})
    group = ["station", "season", "variable", "bin_label", "unit"]
    counts = source.groupby(group, as_index=False, observed=True).agg(
        measurement_count=("measurement_count", "sum"),
        bin_lower=("bin_lower_ms", "first"),
    )
    totals = source.groupby(
        ["station", "year", "season", "variable", "unit"],
        as_index=False,
        observed=True,
    ).agg(total_measurements_in_period=("total_measurements_in_period", "first"))
    totals = totals.groupby(
        ["station", "season", "variable", "unit"], as_index=False, observed=True
    ).agg(total_measurements_in_period=("total_measurements_in_period", "sum"))
    tidy = counts.merge(
        totals, on=["station", "season", "variable", "unit"], how="left", validate="many_to_one"
    )
    tidy["frequency_pct"] = 100 * tidy["measurement_count"] / tidy["total_measurements_in_period"]
    columns = [
        "station", "season", "variable", "bin_label", "unit",
        "measurement_count", "total_measurements_in_period", "frequency_pct",
    ]
    available = [column for column in columns if column in source]
    tidy = tidy.sort_values(["station", "season", "variable", "bin_lower"])[available]
    return write_csv(tidy, output / "weather_frequency.csv"), available


def export_stations(output: Path) -> tuple[int, list[str]]:
    source = pd.read_csv("data/raw/weather/stations.csv")
    columns = [column for column in ["station", "name", "lat", "lon"] if column in source]
    return write_csv(source[columns], output / "stations.csv"), columns


def export_annual_traffic(output: Path) -> tuple[int, list[str]]:
    source = pd.read_csv(ROOT / "traffic/annual.csv", low_memory=False)
    columns = [column for column in ["year", "road_section", "section_length_km", "adu", "sdu", "vdu"] if column in source]
    return write_csv(source[columns], output / "annual_traffic.csv"), columns


def export_rate_tables(output: Path) -> list[tuple[str, int, list[str], str]]:
    """Write the two compact CSV inputs used by the vehicle-kilometre results.

    ``traffic_rate_summary.csv`` retains all valid road exposure, aggregated to
    traffic period and wind interval. ``rate_model.csv`` retains the complete
    within-road/year/period strata only where at least one matched accident
    occurred; all-zero strata do not contribute information to a conditional
    Poisson model.
    """
    panel_path = ROOT / "traffic/road_period.parquet"
    accident_path = ROOT / "accidents/rate.parquet"
    panel_columns = [
        "year", "road_section", "traffic_period", "weather_station_id", "variable",
        "bin_label", "bin_lower_ms", "frequency_pct", "wind_frequency_available",
        "section_length_km", "traffic_reference_daily_volume",
    ]
    panel = read_table(panel_path)[panel_columns].copy()
    panel = panel[
        panel["variable"].eq("f_5m")
        & panel["wind_frequency_available"].fillna(False)
        & panel["weather_station_id"].notna()
        & panel["section_length_km"].gt(0)
        & panel["traffic_reference_daily_volume"].gt(0)
        & panel["frequency_pct"].notna()
    ].copy()
    panel["road_section"] = panel["road_section"].astype("string").str.strip().str.lower()
    panel["weather_station_id"] = pd.to_numeric(
        panel["weather_station_id"], errors="raise"
    ).astype("Int64")
    panel["period_days"] = [
        days_in_traffic_period(year, period)
        for year, period in zip(panel["year"], panel["traffic_period"], strict=True)
    ]
    panel["estimated_vehicle_km"] = (
        panel["traffic_reference_daily_volume"]
        * panel["section_length_km"]
        * panel["period_days"]
        * panel["frequency_pct"]
        / 100
    )
    keys = ["year", "road_section", "traffic_period", "weather_station_id", "bin_label"]
    if panel.duplicated(keys).any():
        raise ValueError("Road exposure has duplicate road-year-period-wind rows")

    accident_columns = [
        "nid", "year", "road_section", "traffic_period", "rate_weather_station_id",
        "weather_time_difference_minutes", "rate_station_accident_distance_km", "f",
        "fg", "vehicle_group",
    ]
    accidents = read_table(accident_path)[accident_columns].rename(columns={"nid": "id"}).copy()
    accidents["road_section"] = accidents["road_section"].astype("string").str.strip().str.lower()
    accidents = accidents[
        accidents["weather_time_difference_minutes"].le(5)
        & accidents["rate_station_accident_distance_km"].le(20)
        & accidents["f"].between(0, 45, inclusive="left")
        & accidents["fg"].between(0, 65, inclusive="left")
        & accidents["fg"].add(0.5).ge(accidents["f"])
    ].copy()
    stations = panel[["year", "road_section", "traffic_period", "weather_station_id"]].drop_duplicates()
    accidents = accidents.merge(
        stations,
        on=["year", "road_section", "traffic_period"],
        how="inner",
        validate="many_to_one",
    )
    if not accidents["rate_weather_station_id"].eq(accidents["weather_station_id"]).all():
        raise ValueError("Accident and exposure rows use different weather stations")
    bins = panel[["bin_label", "bin_lower_ms"]].drop_duplicates().sort_values("bin_lower_ms")
    accidents["wind_bin"] = pd.cut(
        accidents["f"],
        bins=[*bins["bin_lower_ms"].to_numpy(float), float("inf")],
        labels=bins["bin_label"].tolist(),
        right=False,
        include_lowest=True,
    ).astype("string")
    count_keys = ["year", "road_section", "traffic_period", "wind_bin"]
    counts = accidents.groupby(count_keys, as_index=False).agg(
        injury_accidents=("id", "nunique"),
        one_vehicle_accidents=("vehicle_group", lambda values: values.eq("1 vehicle").sum()),
        multiple_vehicle_accidents=("vehicle_group", lambda values: values.eq("2 or more vehicles").sum()),
    )
    model_strata = counts[["year", "road_section", "traffic_period"]].drop_duplicates()
    model = panel.merge(
        model_strata,
        on=["year", "road_section", "traffic_period"],
        how="inner",
        validate="many_to_one",
    ).merge(
        counts,
        left_on=["year", "road_section", "traffic_period", "bin_label"],
        right_on=count_keys,
        how="left",
        validate="one_to_one",
    )
    model = model.drop(columns="wind_bin")
    for column in ["injury_accidents", "one_vehicle_accidents", "multiple_vehicle_accidents"]:
        model[column] = model[column].fillna(0).astype(int)
    model = model.rename(columns={"bin_label": "wind_bin", "bin_lower_ms": "wind_bin_lower_ms"})[
        [
            "year", "road_section", "traffic_period", "weather_station_id", "wind_bin",
            "wind_bin_lower_ms", "estimated_vehicle_km", "injury_accidents",
            "one_vehicle_accidents", "multiple_vehicle_accidents",
        ]
    ].sort_values(["year", "road_section", "traffic_period", "wind_bin_lower_ms"])
    summary = panel.groupby(["traffic_period", "bin_label", "bin_lower_ms"], as_index=False).agg(
        estimated_vehicle_km=("estimated_vehicle_km", "sum"),
    ).rename(columns={"bin_label": "wind_bin", "bin_lower_ms": "wind_bin_lower_ms"})
    total_counts = counts.groupby("wind_bin", as_index=False).agg(
        injury_accidents=("injury_accidents", "sum"),
    )
    period_counts = accidents.groupby(["traffic_period", "wind_bin"], as_index=False).agg(
        injury_accidents=("id", "nunique"),
    )
    summary = summary.merge(period_counts, on=["traffic_period", "wind_bin"], how="left")
    summary["injury_accidents"] = summary["injury_accidents"].fillna(0).astype(int)
    model_count = write_csv(model, output / "rate_model.csv")
    summary_count = write_csv(
        summary.sort_values(["traffic_period", "wind_bin_lower_ms"]),
        output / "traffic_rate_summary.csv",
    )
    return [
        (
            "rate_model.csv", model_count, list(model.columns),
            "Road-period wind exposure and matched accidents for the rate model.",
        ),
        (
            "traffic_rate_summary.csv", summary_count, list(summary.columns),
            "Vehicle-kilometres and injury accidents by traffic period and wind interval.",
        ),
    ]


def export_selection_summary(output: Path) -> tuple[int, list[str]]:
    """Write the small count table used for the three data-selection figures."""
    all_accidents = read_table(ROOT / "accidents/all.parquet")
    study = read_table(ROOT / "accidents/rural_injury.parquet")
    valid_coordinates = int(all_accidents["urban_rural"].ne("Unknown").sum())
    rural = int(all_accidents["urban_rural"].eq("Rural").sum())
    primary = int(
        (
            study["weather_station_dist_km"].le(20)
            & study["weather_time_difference_minutes"].le(5)
            & study["f"].notna()
            & study["fg"].notna()
        ).sum()
    )
    panel = read_table(ROOT / "traffic/road_period.parquet")
    annual_total = int(panel[["year", "road_section", "traffic_period"]].drop_duplicates().shape[0])
    annual_wind = panel[
        panel["variable"].eq("f_5m")
        & panel["wind_frequency_available"].fillna(False)
        & panel["weather_station_id"].notna()
    ]
    annual_wind = int(
        annual_wind[["year", "road_section", "traffic_period"]].drop_duplicates().shape[0]
    )
    daily_path = ROOT / "traffic/daily_weather.parquet"
    if daily_path.exists():
        daily = read_table(daily_path)
        daily_total = len(daily)
        daily_wind = int(daily["f_daytime_mean"].notna().sum())
    else:
        daily_total = 0
        daily_wind = 0
    summary = pd.DataFrame(
        [
            ("accidents", "valid_time_and_coordinates", valid_coordinates),
            ("accidents", "rural_accidents", rural),
            ("accidents", "rural_injury_accidents", len(study)),
            ("accidents", "primary_wind_oe_sample", primary),
            ("annual_traffic", "road_section_year_periods", annual_total),
            ("annual_traffic", "road_periods_with_wind", annual_wind),
            ("daily_traffic", "counter_days", daily_total),
            ("daily_traffic", "counter_days_with_daytime_wind", daily_wind),
        ],
        columns=["dataset", "step", "records"],
    )
    return write_csv(summary, output / "selection_summary.csv"), list(summary.columns)


def display_number(value: object, decimals: int = 1) -> str:
    if pd.isna(value):
        return "not available"
    return f"{float(value):.{decimals}f}"


def write_daily_text(source: pd.DataFrame, output: Path) -> None:
    lines: list[str] = []
    for counter, group in source.groupby("counter_site_id", sort=True):
        lines.extend([f"counter: {counter}", "date traffic f-mean-m-s fg-mean-m-s"])
        for row in group.itertuples(index=False):
            date = pd.Timestamp(row.date).date().isoformat()
            lines.append(f"{date} {display_number(row.traffic_volume, 0)} {display_number(row.f_daytime_mean)} {display_number(row.fg_daytime_mean)}")
        lines.append("")
    (output / "daily.txt").write_text("\n".join(lines), encoding="utf-8")


def export_daily_traffic(output: Path) -> tuple[int, list[str]] | None:
    path = ROOT / "traffic/daily_weather.parquet"
    if not path.exists():
        return None
    source = read_table(path).rename(columns={"station_id": "road_station_m"})
    text_columns = [
        "date", "counter_site_id", "traffic_volume", "f_daytime_mean",
        "fg_daytime_mean",
    ]
    text_columns = [column for column in text_columns if column in source]
    readable = source[text_columns].sort_values(["counter_site_id", "date"])
    csv_columns = [
        "date", "counter_site_id", "traffic_volume", "f_daytime_mean",
        "fg_daytime_mean",
    ]
    csv_columns = [column for column in csv_columns if column in readable]
    daily = readable[csv_columns].rename(
        columns={
            "counter_site_id": "counter_id",
            "traffic_volume": "traffic",
            "f_daytime_mean": "f_mean",
            "fg_daytime_mean": "fg_mean",
        }
    )
    if "traffic" in daily:
        daily["traffic"] = daily["traffic"].round().astype("Int64")
    count = write_csv(daily, output / "daily_traffic.csv")
    write_daily_text(readable, output)
    return count, list(daily.columns)


def write_readme(output: Path, daily_present: bool) -> None:
    daily_text = (
        "`daily.txt` is a human-readable counter-by-counter companion generated "
        "from the same source table as `daily_traffic.csv`."
        if daily_present
        else "Daily traffic files are added when the local daily PDF data are available."
    )
    accidents = pd.read_csv(output / "accidents.csv", usecols=["timestamp"])
    years = pd.to_datetime(accidents["timestamp"], errors="coerce").dt.year.dropna()
    period = f"{int(years.min())}–{int(years.max())}"
    text = f"""# Canonical analysis data

This directory is the only input layer used by the ordinary analysis scripts.
The files are generated during preparation and are deliberately CSV so that
they can be opened and checked directly. Do not edit them by hand.

- `accidents.csv`: the {period} rural injury-accident study sample and its weather match.
- `weather_frequency.csv`: pooled 2007–2025 station-season wind-bin counts used as O/E exposure. `f` and `fg` are in m/s; `gust_factor` is the unitless ratio `fg / f` and is defined only when `f >= 3 m/s`.
- `stations.csv`: weather-station identifiers and coordinates.
- `annual_traffic.csv`: annual road-section traffic exposure (ADU, SDU and VDU).
- `rate_model.csv`: compact road-section/year/traffic-period/wind-bin input for the conditional Poisson rate model.
- `traffic_rate_summary.csv`: 18 aggregated traffic-exposure rows used for the descriptive accident-per-vehicle-km table.
- `selection_summary.csv`: counts for the accident and traffic selection figures.
- `daily_traffic.csv`: one daily counter total with matched daytime mean wind and gust, 2019–2024.
- {daily_text}
- `oe_station_bins.csv`: station-season O/E calculation rows, generated by `src.analysis.build_oe` and used by the figure script.
- `manifest.csv`: row counts, columns, and a short description of each analysis file.
"""
    (output / "README.md").write_text(text, encoding="utf-8")


def write_manifest(output: Path, entries: list[tuple[str, int, list[str], str]]) -> None:
    manifest = pd.DataFrame(entries, columns=["file", "records", "columns", "description"])
    manifest["columns"] = manifest["columns"].str.join(", ")
    manifest.to_csv(output / "manifest.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=Path("data/analysis"), help="Output directory.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, int, list[str], str]] = []
    for filename, description, exporter in [
        ("accidents.csv", "Rural injury accidents with matched mean wind and gust.", export_accidents),
        ("weather_frequency.csv", "Station-season wind frequencies used as the O/E denominator.", export_frequency),
        ("stations.csv", "Weather-station identifiers, names, and coordinates.", export_stations),
        ("annual_traffic.csv", "Annual road-section traffic volumes and lengths.", export_annual_traffic),
    ]:
        records, columns = exporter(args.output)
        entries.append((filename, records, columns, description))
    entries.extend(export_rate_tables(args.output))
    records, columns = export_selection_summary(args.output)
    entries.append(("selection_summary.csv", records, columns, "Counts used in data-selection figures."))
    daily = export_daily_traffic(args.output)
    if daily:
        records, columns = daily
        entries.extend([
            ("daily_traffic.csv", records, columns, "Daily counter totals with daytime mean wind and gust."),
            ("daily.txt", records, ["counter", "date", "traffic", "daytime wind"], "Human-readable daily counter records."),
        ])
    write_readme(args.output, daily is not None)
    entries.append(("README.md", 0, ["file descriptions", "rebuild instruction"], "Description of the analysis data layer."))
    entries.append(("manifest.csv", len(entries) + 1, ["file", "records", "columns", "description"], "Inventory of the analysis data files."))
    write_manifest(args.output, entries)
    print(f"Wrote {len(entries)} canonical files to {args.output}")


if __name__ == "__main__":
    main()
