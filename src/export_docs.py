"""Write documentation for the canonical analysis CSV layer."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_readme(output: Path, daily_present: bool) -> None:
    daily_text = (
        "`daily_traffic.csv` is included when the local daily PDF data are available."
        if daily_present
        else "Daily traffic data are added when the local daily PDF data are available."
    )
    accidents = pd.read_csv(output / "accidents.csv", usecols=["timestamp"])
    years = pd.to_datetime(accidents["timestamp"], errors="coerce").dt.year.dropna()
    period = f"{int(years.min())}–{int(years.max())}"
    text = f"""# Analysis data

This directory is the only input layer used by the ordinary analysis scripts.
The files are generated during preparation and are deliberately CSV so that
they can be opened and checked directly. Do not edit them by hand.

- `accidents.csv`: the {period} rural injury-accident events, outcomes, locations, and calendar classifications.
- `accident_conditions.csv`: independently matched wind and temperature plus estimated astronomical daylight at each accident time.
- `temperature_matches.csv`: one row per accident with temperature, station, distance, time difference, and source.
- `weather_frequency.csv`: pooled 2007–2025 station-season wind and temperature counts. `f` and `fg` are in m/s and temperature is in degrees Celsius.
- `weather_yearly.csv`: station-year-season mean-wind and temperature counts used only for the year-adjusted O/E comparison.
- `temperature_frequency.csv`: inspectable station-year-season temperature counts from the clean official weather file.
- `weather_source_audit.csv`: source-file hashes, row checks, and date coverage for the official delivery.
- `weather_cleaning.csv`: annual and total counts from the fixed weather-quality rules.
- `case_control.csv`: accident times and same-hour, same-weekday control times for mean wind, gust, and temperature models.
- `annual_traffic.csv`: annual road-section traffic values (ADU, SDU and VDU).
- `road_rate.csv`: compact road-section/year/traffic-period/wind-bin input for the conditional Poisson model.
- `road_temperature.csv`: matching road-section/year/traffic-period temperature-bin input for the secondary conditional Poisson model.
- `road_seasons.csv`: compact road-section/year/season/wind-bin input for season-specific mean-wind models.
- `road_exposure.csv`: 18 aggregated rows used for the descriptive accident-per-vehicle-km table.
- `selection_summary.csv`: counts for the accident and traffic selection figures.
- `daily_traffic.csv`: optional large CSV with one daily counter total and observation counts in six mean-wind intervals, 2019–2024.
- `counter_locations.csv`: one geometry-interpolated location per counter-site year for the selected-counter analyses.
- `counter_wind.csv`: accident-time mean wind from the same station used for the assigned counter-day.
- `counter_check.csv`: independent comparison of estimated counter locations with official 20 m road-station points.
- `daily_season_panel.csv`: canonical counter-year-season input derived during analysis when optional daily-counter data are available.
- {daily_text}
- `manifest.csv`: row counts, columns, and a short description of each analysis file.
"""
    (output / "README.md").write_text(text, encoding="utf-8")


def write_manifest(
    output: Path, entries: list[tuple[str, int, list[str], str]]
) -> None:
    manifest = pd.DataFrame(
        entries, columns=["file", "records", "columns", "description"]
    )
    manifest["columns"] = manifest["columns"].str.join(", ")
    manifest.to_csv(output / "manifest.csv", index=False)


def register_manifest_file(output: Path, filename: str, description: str) -> None:
    """Add or refresh one analysis-stage intermediate in the manifest."""
    path = output / filename
    manifest_path = output / "manifest.csv"
    if not path.exists() or not manifest_path.exists():
        return
    data = pd.read_csv(path)
    manifest = pd.read_csv(manifest_path)
    row = pd.DataFrame(
        [{
            "file": filename,
            "records": len(data),
            "columns": ", ".join(data.columns),
            "description": description,
        }]
    )
    manifest = pd.concat(
        [manifest[~manifest["file"].eq(filename)], row], ignore_index=True
    )
    manifest.loc[manifest["file"].eq("manifest.csv"), "records"] = len(manifest)
    manifest.to_csv(manifest_path, index=False)
