"""Build a transparent daily-traffic response analysis by mean wind speed.

The analytical unit is one physical traffic counter on one calendar day.  The
input already contains a nearest usable weather-station match and daytime mean
wind (10:00--21:59).  We assume that 95% of the reported 24-hour traffic count
occurred in that daytime window.  This factor changes vehicle totals but cancels
out of observed/expected ratios.

Expected traffic is calculated within counter, year, month, and weekday.  Thus,
the comparison controls directly for the local seasonal and weekly traffic
pattern.  VDU, SDU, and the ADU-derived spring/autumn value (VHDU) are
retained as transparent annual traffic references, not used to replace observed
daily counts.
"""

from __future__ import annotations

import argparse
import calendar
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT = Path("data/processed/traffic/daily_traffic_weather.parquet")
ANNUAL = Path("data/processed/traffic/annual_road_section_exposure.csv")
DAY_PANEL = Path("data/processed/traffic/daily_traffic_wind_response.parquet")
RESULTS = Path("reports/main/tables/daily_traffic_wind.csv")
PERIOD_SUMMARY = Path("reports/main/tables/daily_traffic_period_summary.csv")
FIGURE_ALL = Path("reports/main/figures/daily_traffic_wind.png")
DETAILED_RESULTS = Path("reports/working/tables/daily_traffic_wind_detailed.csv")
FIGURE_DETAILED = Path("reports/working/figures/daily_traffic_wind_detailed.png")
FIGURE_PERIOD = Path("reports/working/figures/daily_traffic_wind_by_period.png")
NOTES = Path("archive/generated_diagnostics/daily_traffic_wind_analysis_notes.md")

DAYTIME_TRAFFIC_SHARE = 0.95
F_UPPER_BOUNDS = np.arange(3, 34, 3, dtype=float)
PERIOD_ORDER = ["VDU", "SDU", "VHDU"]
PERIOD_MONTHS = {
    "VDU": [12, 1, 2, 3],
    "SDU": [6, 7, 8, 9],
    "VHDU": [4, 5, 10, 11],
}


def normalize_section(values: pd.Series) -> pd.Series:
    """Return lower-case road-section identifiers suitable for joins."""
    return values.astype("string").str.strip().str.lower()


def traffic_period(month: pd.Series) -> pd.Series:
    """Classify each month using the official VDU/SDU definitions."""
    result = pd.Series("VHDU", index=month.index, dtype="string")
    result.loc[month.isin(PERIOD_MONTHS["VDU"])] = "VDU"
    result.loc[month.isin(PERIOD_MONTHS["SDU"])] = "SDU"
    return pd.Categorical(result, categories=PERIOD_ORDER, ordered=True)


def period_days(year: int, period: str) -> int:
    """Count calendar days in a traffic period for one calendar year."""
    return sum(calendar.monthrange(int(year), month)[1] for month in PERIOD_MONTHS[period])


def wind_labels() -> list[str]:
    lower = np.concatenate(([0.0], F_UPPER_BOUNDS[:-1]))
    return [f"{int(lo)}-{int(hi)}" for lo, hi in zip(lower, F_UPPER_BOUNDS, strict=True)]


def combine_high_wind_tail(panel: pd.DataFrame) -> pd.DataFrame:
    """Create the stable thesis display with a single >=24 m/s category.

    The detailed 3 m/s bins remain available for diagnostic work.  The pooled
    tail has enough counter-days for a readable main result, whereas the
    individual 27--30 and 30--33 m/s bins are too sparse to interpret alone.
    """
    output = panel.copy()
    display_labels = ["0-3", "3-6", "6-9", "9-12", "12-15", "15-18", "18-21", "21-24", ">=24"]
    output["f_bin"] = output["f_bin"].astype("string").replace(
        {"24-27": ">=24", "27-30": ">=24", "30-33": ">=24"}
    )
    output["f_bin"] = pd.Categorical(output["f_bin"], categories=display_labels, ordered=True)
    return output


def add_annual_traffic_references(panel: pd.DataFrame, annual_path: Path) -> pd.DataFrame:
    """Attach official SDU/VDU and a day-weighted derived VHDU reference."""
    annual = pd.read_csv(
        annual_path,
        usecols=["year", "road_section", "adu", "sdu", "vdu"],
    )
    annual["road_section"] = normalize_section(annual["road_section"])
    annual = annual.drop_duplicates(["year", "road_section"])
    year_days = annual["year"].map(lambda value: 366 if calendar.isleap(int(value)) else 365)
    sdu_days = annual["year"].map(lambda value: period_days(int(value), "SDU"))
    vdu_days = annual["year"].map(lambda value: period_days(int(value), "VDU"))
    other_days = year_days - sdu_days - vdu_days
    annual["other_daily_traffic_derived"] = (
        annual["adu"] * year_days - annual["sdu"] * sdu_days - annual["vdu"] * vdu_days
    ) / other_days
    annual.loc[annual["other_daily_traffic_derived"].le(0), "other_daily_traffic_derived"] = np.nan

    output = panel.merge(
        annual,
        on=["year", "road_section"],
        how="left",
        validate="many_to_one",
    )
    output["annual_period_daily_traffic"] = np.select(
        [output["traffic_period"].eq("VDU"), output["traffic_period"].eq("SDU")],
        [output["vdu"], output["sdu"]],
        default=output["other_daily_traffic_derived"],
    )
    output["annual_period_traffic_method"] = np.where(
        output["traffic_period"].eq("VHDU"),
        "ADU-derived VHDU (Apr-May, Oct-Nov)",
        "Official seasonal daily traffic",
    )
    return output


def prepare_panel(input_path: Path, annual_path: Path) -> pd.DataFrame:
    """Create the compact counter-day panel used in the wind-response analysis."""
    source = pd.read_parquet(input_path)
    needed = [
        "date", "year", "counter_site_id", "road_section", "station_id", "site_name",
        "traffic_volume", "location_method", "location_is_estimated",
        "weather_station_id", "weather_station_name", "weather_station_dist_km",
        "f_daytime_mean", "fg_daytime_max", "observation_count",
    ]
    missing = set(needed) - set(source.columns)
    if missing:
        raise ValueError(f"Daily traffic input is missing columns: {sorted(missing)}")
    panel = source[needed].copy()
    panel["date"] = pd.to_datetime(panel["date"])
    panel["road_section"] = normalize_section(panel["road_section"])
    panel["month"] = panel["date"].dt.month.astype("int8")
    panel["weekday"] = panel["date"].dt.weekday.astype("int8")
    panel["traffic_period"] = traffic_period(panel["month"])
    panel["estimated_daytime_traffic"] = DAYTIME_TRAFFIC_SHARE * panel["traffic_volume"]

    # The wind bins deliberately stop at 33 m/s. The separate daily diagnostic
    # has already excluded the identified anomalous Reykjavík station series;
    # only five counter-days remain at >=33 m/s and they are outside the display.
    panel["wind_analysis_eligible"] = panel["f_daytime_mean"].between(0, 33, inclusive="left")
    panel["f_bin"] = pd.cut(
        panel["f_daytime_mean"],
        bins=np.concatenate(([0.0], F_UPPER_BOUNDS)),
        labels=wind_labels(),
        right=False,
        include_lowest=True,
        ordered=True,
    )
    baseline_keys = ["counter_site_id", "year", "month", "weekday"]
    baseline = panel.groupby(baseline_keys, as_index=False).agg(
        baseline_days=("traffic_volume", "size"),
        baseline_mean_daily_traffic=("traffic_volume", "mean"),
        baseline_median_daily_traffic=("traffic_volume", "median"),
    )
    panel = panel.merge(baseline, on=baseline_keys, how="left", validate="many_to_one")
    panel["expected_daytime_traffic"] = (
        DAYTIME_TRAFFIC_SHARE * panel["baseline_mean_daily_traffic"]
    )
    panel["daily_traffic_oe"] = (
        panel["estimated_daytime_traffic"] / panel["expected_daytime_traffic"]
    )
    panel = add_annual_traffic_references(panel, annual_path)
    return panel


def bootstrap_ratios(data: pd.DataFrame, bins: list[str], replicates: int, seed: int) -> pd.DataFrame:
    """Counter-cluster bootstrap intervals for volume-weighted O/E traffic."""
    by_counter = data.groupby(["counter_site_id", "f_bin"], observed=True, as_index=False).agg(
        observed=("estimated_daytime_traffic", "sum"),
        expected=("expected_daytime_traffic", "sum"),
    )
    counters = by_counter["counter_site_id"].drop_duplicates().to_numpy()
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | str]] = []
    for bin_label in bins:
        values = by_counter[by_counter["f_bin"].astype("string").eq(bin_label)]
        indexed = values.set_index("counter_site_id")
        observed = indexed["observed"].reindex(counters, fill_value=0.0).to_numpy(float)
        expected = indexed["expected"].reindex(counters, fill_value=0.0).to_numpy(float)
        sampled = rng.integers(0, len(counters), size=(replicates, len(counters)))
        boot_observed = observed[sampled].sum(axis=1)
        boot_expected = expected[sampled].sum(axis=1)
        ratio = np.divide(
            boot_observed,
            boot_expected,
            out=np.full(replicates, np.nan),
            where=boot_expected > 0,
        )
        rows.append(
            {
                "f_bin": bin_label,
                "oe_ci_95_low": float(np.nanpercentile(ratio, 2.5)),
                "oe_ci_95_high": float(np.nanpercentile(ratio, 97.5)),
            }
        )
    return pd.DataFrame(rows)


def summarize(data: pd.DataFrame, *, scope: str, replicates: int, seed: int) -> pd.DataFrame:
    """Summarize observed and expected daytime traffic in each wind bin."""
    data = data[data["wind_analysis_eligible"] & data["f_bin"].notna()].copy()
    categories = [str(value) for value in data["f_bin"].cat.categories]
    summary = data.groupby("f_bin", observed=True, as_index=False).agg(
        counter_days=("date", "size"),
        counters=("counter_site_id", "nunique"),
        weather_stations=("weather_station_id", "nunique"),
        observed_daytime_vehicles=("estimated_daytime_traffic", "sum"),
        expected_daytime_vehicles=("expected_daytime_traffic", "sum"),
        median_daily_traffic_oe=("daily_traffic_oe", "median"),
        median_annual_period_daily_traffic=("annual_period_daily_traffic", "median"),
    )
    summary["observed_to_expected_traffic"] = (
        summary["observed_daytime_vehicles"] / summary["expected_daytime_vehicles"]
    )
    summary["relative_traffic_pct"] = 100 * summary["observed_to_expected_traffic"]
    intervals = bootstrap_ratios(data, categories, replicates, seed)
    summary = summary.merge(intervals, on="f_bin", how="left", validate="one_to_one")
    summary["relative_traffic_ci_95_low_pct"] = 100 * summary["oe_ci_95_low"]
    summary["relative_traffic_ci_95_high_pct"] = 100 * summary["oe_ci_95_high"]
    summary["scope"] = scope
    summary["daytime_traffic_share_assumption"] = DAYTIME_TRAFFIC_SHARE
    return summary


def build_results(panel: pd.DataFrame, replicates: int) -> pd.DataFrame:
    """Return pooled and VDU/SDU/VHDU wind-response summaries."""
    frames = [summarize(panel, scope="All periods", replicates=replicates, seed=20260729)]
    for index, period in enumerate(PERIOD_ORDER):
        frames.append(
            summarize(
                panel[panel["traffic_period"].eq(period)],
                scope=period,
                replicates=replicates,
                seed=20260730 + index,
            )
        )
    return pd.concat(frames, ignore_index=True)


def build_period_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Describe the daily-count sample and its annual traffic reference by period."""
    data = panel[panel["wind_analysis_eligible"]].copy()
    return (
        data.groupby("traffic_period", observed=True, as_index=False)
        .agg(
            counter_days=("date", "size"),
            counters=("counter_site_id", "nunique"),
            road_sections=("road_section", "nunique"),
            weather_stations=("weather_station_id", "nunique"),
            mean_daily_traffic=("traffic_volume", "mean"),
            median_daily_traffic=("traffic_volume", "median"),
            median_annual_period_daily_traffic=("annual_period_daily_traffic", "median"),
            annual_reference_coverage_pct=("annual_period_daily_traffic", lambda x: 100 * x.notna().mean()),
        )
        .sort_values("traffic_period")
    )


def plot_results(results: pd.DataFrame, path: Path, scope: str, title: str) -> None:
    """Plot volume-weighted observed/expected traffic, with counter bootstrap CIs."""
    data = results[results["scope"].eq(scope)].copy()
    x = np.arange(len(data))
    sparse = data["counters"].lt(20)
    colors = np.where(sparse, "#A8A8A8", "#287271")
    values = data["relative_traffic_pct"].to_numpy(float)
    low = values - data["relative_traffic_ci_95_low_pct"].to_numpy(float)
    high = data["relative_traffic_ci_95_high_pct"].to_numpy(float) - values

    fig, axis = plt.subplots(figsize=(11.4, 6.6))
    bars = axis.bar(x, values, width=0.72, color=colors)
    axis.errorbar(x, values, yerr=[low, high], fmt="none", ecolor="#202020", capsize=3)
    axis.axhline(100, color="#202020", linestyle="--", linewidth=1.2)
    display_bins = data["f_bin"].astype("string").str.replace(">=", "≥", regex=False)
    axis.set_xticks(x, display_bins, rotation=0)
    axis.set_xlabel("Daytime mean wind speed, 10:00–21:59 (m/s)")
    axis.set_ylabel("Daily traffic relative to expected (%)")
    axis.set_title(title)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    ymax = max(112, float(data["relative_traffic_ci_95_high_pct"].max()) * 1.12)
    axis.set_ylim(0, ymax)
    for bar, row in zip(bars, data.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            min(ymax - 2, row.relative_traffic_pct + 1.5),
            f"n={row.counter_days:,}",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
    fig.subplots_adjust(left=0.11, right=0.98, top=0.91, bottom=0.24)
    fig.text(
        0.5,
        0.035,
        "Expected traffic: mean for the same counter, year, month, and weekday. "
        "Daytime traffic is estimated as 95% of the 24-hour count; error bars are 95% counter-cluster bootstrap intervals.",
        ha="center",
        fontsize=8.3,
        color="#444444",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def plot_period_results(results: pd.DataFrame, path: Path) -> None:
    """Show the result separately for official summer, winter, and VHDU periods."""
    fig, axes = plt.subplots(3, 1, figsize=(11.4, 12.6), sharex=True)
    ymax = max(112, float(results["relative_traffic_ci_95_high_pct"].max()) * 1.12)
    titles = {
        "VDU": "Winter daily traffic (VDU: December–March)",
        "SDU": "Summer daily traffic (SDU: June–September)",
        "VHDU": "Spring/autumn traffic (VHDU: April–May, October–November)",
    }
    for axis, period in zip(axes, PERIOD_ORDER, strict=True):
        data = results[results["scope"].eq(period)]
        x = np.arange(len(data))
        sparse = data["counters"].lt(20)
        values = data["relative_traffic_pct"].to_numpy(float)
        low = values - data["relative_traffic_ci_95_low_pct"].to_numpy(float)
        high = data["relative_traffic_ci_95_high_pct"].to_numpy(float) - values
        bars = axis.bar(x, values, width=0.72, color=np.where(sparse, "#A8A8A8", "#287271"))
        axis.errorbar(x, values, yerr=[low, high], fmt="none", ecolor="#202020", capsize=3)
        axis.axhline(100, color="#202020", linestyle="--", linewidth=1.1)
        axis.set_title(titles[period], fontsize=11)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
        axis.set_ylim(0, ymax)
        for bar, row in zip(bars, data.itertuples(index=False), strict=True):
            axis.text(bar.get_x() + bar.get_width() / 2, min(ymax - 2, row.relative_traffic_pct + 1.2), f"n={row.counter_days:,}", ha="center", va="bottom", fontsize=7.5)
    axes[-1].set_xticks(np.arange(len(data)), data["f_bin"], rotation=0)
    axes[-1].set_xlabel("Daytime mean wind speed, 10:00–21:59 (m/s)")
    fig.supylabel("Estimated daytime traffic relative to expected (%)")
    fig.supxlabel("")
    fig.text(
        0.5,
        0.012,
        "Expected traffic is standardized within counter, year, month, and weekday. Grey bars have fewer than 20 counters.",
        ha="center", fontsize=8.3, color="#444444",
    )
    fig.tight_layout(rect=(0.03, 0.04, 1, 0.99))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)


def write_notes(path: Path, panel: pd.DataFrame, results: pd.DataFrame) -> None:
    """Write a compact methodological record next to the generated files."""
    eligible = panel[panel["wind_analysis_eligible"]]
    text = f"""# Daily traffic and wind analysis

## Unit and exposure

- Unit: one physical counter on one date.
- Daily traffic rows: {len(panel):,}.
- Rows with mean wind from 0 to <33 m/s: {len(eligible):,} ({100 * len(eligible) / len(panel):.2f}%).
- Traffic is reported as a 24-hour count. For the daytime wind comparison,
  estimated daytime traffic equals {DAYTIME_TRAFFIC_SHARE:.0%} of the daily count.

## Standardisation

For each counter-day, expected traffic is the arithmetic mean daily count for
the same counter, calendar year, month, and weekday. The reported ratio is the
sum of observed estimated daytime vehicles divided by the sum of expected
daytime vehicles in a wind bin. This is equivalent to comparing the observed
share of traffic in the bin with its expected share after local calendar
standardisation.

## Seasonal references

- VDU: December--March; official VDU daily traffic.
- SDU: June--September; official SDU daily traffic.
- VHDU: April--May and October--November; day-weighted residual derived from
  ADU, SDU, and VDU. It is retained as a reference column, not substituted for
  observed daily traffic.

## Outputs

- `{DAY_PANEL}`: counter-day analysis data.
- `{RESULTS}`: thesis display with the stable >=24 m/s tail.
- `{DETAILED_RESULTS}`: retained 3 m/s-bin sensitivity output.
- `{PERIOD_SUMMARY}`: daily-count sample by traffic period.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build daily traffic O/E by mean wind.")
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--annual", type=Path, default=ANNUAL)
    parser.add_argument("--day-panel", type=Path, default=DAY_PANEL)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--period-summary", type=Path, default=PERIOD_SUMMARY)
    parser.add_argument("--figure", type=Path, default=FIGURE_ALL)
    parser.add_argument("--detailed-results", type=Path, default=DETAILED_RESULTS)
    parser.add_argument("--detailed-figure", type=Path, default=FIGURE_DETAILED)
    parser.add_argument(
        "--write-detailed",
        action="store_true",
        help="Also regenerate the detailed 3 m/s-bin sensitivity outputs.",
    )
    parser.add_argument("--period-figure", type=Path, default=FIGURE_PERIOD)
    parser.add_argument("--notes", type=Path, default=NOTES)
    parser.add_argument("--bootstrap-replicates", type=int, default=1000)
    args = parser.parse_args()

    panel = prepare_panel(args.input, args.annual)
    results = build_results(combine_high_wind_tail(panel), args.bootstrap_replicates)
    period_summary = build_period_summary(panel)
    paths = [args.day_panel, args.results, args.period_summary, args.figure, args.notes]
    if args.write_detailed:
        paths.extend([args.detailed_results, args.detailed_figure, args.period_figure])
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.day_panel, index=False, compression="zstd")
    results.to_csv(args.results, index=False)
    period_summary.to_csv(args.period_summary, index=False)
    plot_results(results, args.figure, "All periods", "Daily traffic relative to expected traffic by mean wind speed")
    if args.write_detailed:
        detailed_results = build_results(panel, args.bootstrap_replicates)
        detailed_results.to_csv(args.detailed_results, index=False)
        plot_results(detailed_results, args.detailed_figure, "All periods", "Daily traffic: detailed 3 m/s wind bins")
        plot_period_results(detailed_results, args.period_figure)
    write_notes(args.notes, panel, results)
    print(period_summary.to_string(index=False))
    print(results[results["scope"].eq("All periods")].to_string(index=False))


if __name__ == "__main__":
    main()
