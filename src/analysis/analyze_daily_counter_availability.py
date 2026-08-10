"""Test whether daily traffic-counter record availability changes with wind.

The unit is a possible counter-day for which a daytime mean wind is available
from the assigned nearby weather station.  A day is marked available only when
the daily-PDF traffic data contain a record for that counter and date; a zero
traffic count is therefore retained as an available measurement.

Expected availability is standardised within counter, year, month, and weekday.
Consequently, a ratio below one would indicate that counter records are missing
more often than expected on windy days, rather than a seasonal difference in
the ordinary recording schedule.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


WEATHER_CACHE = Path("data/processed/traffic/daily_weather_cache.parquet")
DAILY_TRAFFIC = Path("data/processed/traffic/daily_traffic.parquet")
PANEL = Path("data/processed/traffic/daily_counter_availability.parquet")
RESULTS = Path("reports/working/tables/daily_counter_availability.csv")
FIGURE = Path("reports/working/figures/daily_counter_availability.png")
NOTES = Path("archive/generated_diagnostics/daily_counter_availability_notes.md")

EXCLUDED_STATION_IDS = {7475}
F_BINS = ["0-3", "3-6", "6-9", "9-12", "12-15", "15-18", "18-21", "21-24", ">=24"]


def assign_wind_bin(values: pd.Series) -> pd.Categorical:
    """Return the thesis-display bins, pooling the sparse >=24 m/s tail."""
    numeric = pd.to_numeric(values, errors="coerce")
    result = pd.cut(
        numeric,
        bins=[0, 3, 6, 9, 12, 15, 18, 21, 24, 33],
        labels=F_BINS[:-1] + [">=24"],
        right=False,
        include_lowest=True,
        ordered=True,
    )
    return result.astype(pd.CategoricalDtype(categories=F_BINS, ordered=True))


def prepare_panel(weather_cache: Path, daily_traffic: Path) -> pd.DataFrame:
    """Build one row per wind-observed potential counter-day."""
    weather = pd.read_parquet(
        weather_cache,
        columns=[
            "counter_site_id", "date", "weather_station_id", "f_daytime_mean",
            "counter_location_method", "counter_location_is_estimated",
        ],
    )
    weather["date"] = pd.to_datetime(weather["date"])
    weather["weather_station_id"] = pd.to_numeric(
        weather["weather_station_id"], errors="coerce"
    ).astype("Int64")
    weather["f_daytime_mean"] = pd.to_numeric(weather["f_daytime_mean"], errors="coerce")
    weather = weather[
        weather["weather_station_id"].notna()
        & ~weather["weather_station_id"].isin(EXCLUDED_STATION_IDS)
        & weather["f_daytime_mean"].between(0, 33, inclusive="left")
    ].copy()
    if weather.duplicated(["counter_site_id", "date"]).any():
        raise ValueError("Weather cache must be unique on counter_site_id + date")

    recorded = pd.read_parquet(daily_traffic, columns=["counter_site_id", "date"])
    recorded["date"] = pd.to_datetime(recorded["date"])
    if recorded.duplicated(["counter_site_id", "date"]).any():
        raise ValueError("Daily traffic must be unique on counter_site_id + date")
    recorded["record_available"] = 1

    panel = weather.merge(
        recorded, on=["counter_site_id", "date"], how="left", validate="one_to_one"
    )
    panel["record_available"] = panel["record_available"].fillna(0).astype("int8")
    panel["year"] = panel["date"].dt.year.astype("int16")
    panel["month"] = panel["date"].dt.month.astype("int8")
    panel["weekday"] = panel["date"].dt.weekday.astype("int8")
    panel["f_bin"] = assign_wind_bin(panel["f_daytime_mean"])
    panel["counter_year"] = panel["counter_site_id"].astype("string") + ":" + panel["year"].astype("string")

    keys = ["counter_site_id", "year", "month", "weekday"]
    panel["expected_availability"] = panel.groupby(keys)["record_available"].transform("mean")
    yearly_records = panel.groupby(["counter_site_id", "year"])["record_available"].transform("sum")
    panel["recorded_days_in_counter_year"] = yearly_records.astype("int16")
    panel["stable_counter_year"] = panel["recorded_days_in_counter_year"].ge(300)
    return panel


def summarise(panel: pd.DataFrame, scope: str, stable_only: bool) -> pd.DataFrame:
    """Calculate availability O/E, with the observed possible counter-days retained."""
    data = panel[panel["stable_counter_year"]].copy() if stable_only else panel.copy()
    summary = data.groupby("f_bin", observed=False, as_index=False).agg(
        potential_counter_days=("date", "size"),
        available_counter_days=("record_available", "sum"),
        counters=("counter_site_id", "nunique"),
        counter_years=("counter_year", "nunique"),
        expected_available_days=("expected_availability", "sum"),
    )
    summary["raw_availability_pct"] = 100 * summary["available_counter_days"] / summary["potential_counter_days"]
    summary["availability_oe"] = summary["available_counter_days"] / summary["expected_available_days"]
    summary["availability_relative_to_expected_pct"] = 100 * summary["availability_oe"]
    summary["scope"] = scope
    return summary


def plot_results(results: pd.DataFrame, path: Path) -> None:
    """Draw a compact availability diagnostic for all and stable counter-years."""
    fig, axis = plt.subplots(figsize=(11.2, 6.4))
    x = np.arange(len(F_BINS))
    styles = [("All counter-years", "#287271", -0.13), (">=300 recorded days/year", "#C7522A", 0.13)]
    for scope, color, offset in styles:
        data = results[results["scope"].eq(scope)].set_index("f_bin").reindex(F_BINS)
        axis.plot(
            x + offset, data["availability_relative_to_expected_pct"],
            marker="o", linewidth=2.0, markersize=5.5, color=color, label=scope,
        )
    axis.axhline(100, color="#202020", linestyle="--", linewidth=1.2)
    axis.set_xticks(x, [label.replace(">=", "≥") for label in F_BINS])
    axis.set_xlabel("Daytime mean wind speed, 10:00–21:59 (m/s)")
    axis.set_ylabel("Counter-record availability relative to expected (%)")
    axis.set_title("Daily traffic-counter availability by mean wind speed")
    axis.set_ylim(98.5, 101.5)
    axis.grid(axis="y", alpha=0.22)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="lower left")
    fig.subplots_adjust(left=0.11, right=0.98, top=0.90, bottom=0.23)
    fig.text(
        0.5, 0.04,
        "A possible counter-day has valid daytime wind. Expected availability is the mean for the same counter, year, month, and weekday.\n"
        "The second series restricts to counter-years with at least 300 recorded traffic days.",
        ha="center", fontsize=8.5, color="#444444",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def write_notes(panel: pd.DataFrame, results: pd.DataFrame, path: Path) -> None:
    """Document the denominator and the result in plain language."""
    all_rows = results[results["scope"].eq("All counter-years")]
    overall = panel["record_available"].mean()
    text = f"""# Daily counter availability by wind

## Question

Could the lower observed traffic in high wind be caused by traffic counters
failing to report, rather than by lower traffic volume?

## Denominator

- A potential counter-day is included when the counter has an assigned weather
  station with valid daytime mean wind from 0 to <33 m/s.
- Number of potential counter-days: {len(panel):,}.
- Counter sites: {panel['counter_site_id'].nunique():,}.
- Calendar years: {panel['year'].min()}–{panel['year'].max()}.
- A traffic record is available when a row occurs in `daily_traffic.parquet`.
  A recorded zero is therefore valid and is not treated as missing.
- Overall record availability: {overall:.2%}.

## Standardisation

For each potential counter-day, expected availability is the mean record
availability for the same counter, calendar year, month, and weekday. The
reported O/E is observed available days divided by the sum of these expected
availabilities within the wind bin. It tests record availability conditional on
wind being observable; it does not test weather-station outages.

## Result

Across the displayed bins, all-counter-year availability O/E ranges from
{all_rows['availability_oe'].min():.4f} to {all_rows['availability_oe'].max():.4f}.
Values close to 1.00 mean that daily traffic records are not systematically
less available on windier days after calendar standardisation.

## Outputs

- `{PANEL}`: potential counter-day quality-control panel.
- `{RESULTS}`: numerical results for all counter-years and the stable subset.
- `{FIGURE}`: visual diagnostic.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test daily counter availability by wind bin.")
    parser.add_argument("--weather-cache", type=Path, default=WEATHER_CACHE)
    parser.add_argument("--daily-traffic", type=Path, default=DAILY_TRAFFIC)
    parser.add_argument("--panel", type=Path, default=PANEL)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--figure", type=Path, default=FIGURE)
    parser.add_argument("--notes", type=Path, default=NOTES)
    args = parser.parse_args()

    panel = prepare_panel(args.weather_cache, args.daily_traffic)
    results = pd.concat(
        [
            summarise(panel, "All counter-years", stable_only=False),
            summarise(panel, ">=300 recorded days/year", stable_only=True),
        ],
        ignore_index=True,
    )
    for path in [args.panel, args.results, args.figure, args.notes]:
        path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.panel, index=False, compression="zstd")
    results.to_csv(args.results, index=False)
    plot_results(results, args.figure)
    write_notes(panel, results, args.notes)
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
