"""Build daily-traffic response tables by mean wind speed.

The analytical unit is one physical traffic counter on one calendar day.  The
input already contains a nearest usable weather-station match and daytime mean
wind (10:00--21:59). The reported 24-hour count is retained as the traffic
outcome; it is not divided into estimated hourly traffic.

Expected traffic is calculated within counter, year, month, and weekday.  Thus,
the comparison controls directly for the local seasonal and weekly traffic
pattern. Traffic periods are retained only for descriptive seasonal summaries.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT = Path("data/analysis/daily_traffic.csv")
RESULTS = Path("reports/main/tables/daily_traffic_by_wind.csv")
PERIOD_SUMMARY = Path("reports/main/tables/daily_traffic_period_summary.csv")

F_EDGES = np.array([0, 5, 10, 15, 20, 25, np.inf], dtype=float)
F_LABELS = ["0-5", "5-10", "10-15", "15-20", "20-25", ">=25"]
PERIOD_ORDER = ["VDU", "SDU", "VHDU"]
PERIOD_MONTHS = {
    "VDU": [12, 1, 2, 3],
    "SDU": [6, 7, 8, 9],
    "VHDU": [4, 5, 10, 11],
}


def traffic_period(month: pd.Series) -> pd.Series:
    """Classify each month using the official VDU/SDU definitions."""
    result = pd.Series("VHDU", index=month.index, dtype="string")
    result.loc[month.isin(PERIOD_MONTHS["VDU"])] = "VDU"
    result.loc[month.isin(PERIOD_MONTHS["SDU"])] = "SDU"
    return pd.Categorical(result, categories=PERIOD_ORDER, ordered=True)


def prepare_panel(input_path: Path) -> pd.DataFrame:
    """Create the compact counter-day panel used in the wind-response analysis."""
    if input_path.suffix != ".csv":
        raise ValueError(f"Analysis input must be a CSV file: {input_path}")
    source = pd.read_csv(input_path)
    needed = [
        "date", "counter_id", "traffic", "f_mean",
    ]
    missing = set(needed) - set(source.columns)
    if missing:
        raise ValueError(f"Daily traffic input is missing columns: {sorted(missing)}")
    panel = source[needed].copy()
    panel = panel.rename(columns={
        "counter_id": "counter_site_id",
        "traffic": "traffic_volume",
        "f_mean": "f_daytime_mean",
    })
    panel["date"] = pd.to_datetime(panel["date"])
    panel["year"] = panel["date"].dt.year.astype("int16")
    panel["month"] = panel["date"].dt.month.astype("int8")
    panel["weekday"] = panel["date"].dt.weekday.astype("int8")
    panel["traffic_period"] = traffic_period(panel["month"])

    panel["wind_analysis_eligible"] = panel["f_daytime_mean"].between(0, 45, inclusive="left")
    panel["f_bin"] = pd.cut(
        panel["f_daytime_mean"],
        bins=F_EDGES,
        labels=F_LABELS,
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
    panel["expected_daily_traffic"] = panel["baseline_mean_daily_traffic"]
    panel["daily_traffic_oe"] = (
        panel["traffic_volume"] / panel["expected_daily_traffic"]
    )
    return panel


def bootstrap_ratios(data: pd.DataFrame, bins: list[str], replicates: int, seed: int) -> pd.DataFrame:
    """Counter-cluster bootstrap intervals for volume-weighted O/E traffic."""
    by_counter = data.groupby(["counter_site_id", "f_bin"], observed=True, as_index=False).agg(
        observed=("traffic_volume", "sum"),
        expected=("expected_daily_traffic", "sum"),
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
    """Summarize observed and expected daily traffic in each wind bin."""
    data = data[data["wind_analysis_eligible"] & data["f_bin"].notna()].copy()
    categories = [str(value) for value in data["f_bin"].cat.categories]
    summary = data.groupby("f_bin", observed=True, as_index=False).agg(
        counter_days=("date", "size"),
        counters=("counter_site_id", "nunique"),
        observed_daily_vehicles=("traffic_volume", "sum"),
        expected_daily_vehicles=("expected_daily_traffic", "sum"),
        median_daily_traffic_oe=("daily_traffic_oe", "median"),
    )
    summary["observed_to_expected_traffic"] = (
        summary["observed_daily_vehicles"] / summary["expected_daily_vehicles"]
    )
    summary["relative_traffic_pct"] = 100 * summary["observed_to_expected_traffic"]
    intervals = bootstrap_ratios(data, categories, replicates, seed)
    summary = summary.merge(intervals, on="f_bin", how="left", validate="one_to_one")
    summary["relative_traffic_ci_95_low_pct"] = 100 * summary["oe_ci_95_low"]
    summary["relative_traffic_ci_95_high_pct"] = 100 * summary["oe_ci_95_high"]
    summary["scope"] = scope
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
    """Describe the daily-count sample by traffic period."""
    data = panel[panel["wind_analysis_eligible"]].copy()
    return (
        data.groupby("traffic_period", observed=True, as_index=False)
        .agg(
            counter_days=("date", "size"),
            counters=("counter_site_id", "nunique"),
            mean_daily_traffic=("traffic_volume", "mean"),
            median_daily_traffic=("traffic_volume", "median"),
        )
        .sort_values("traffic_period")
    )


def plot_results(results: pd.DataFrame, path: Path, scope: str, title: str) -> None:
    """Plot volume-weighted observed/expected daily traffic."""
    data = results[results["scope"].eq(scope)].copy()
    x = np.arange(len(data))
    sparse = data["counters"].lt(20)
    colors = np.where(sparse, "#A8A8A8", "#287271")
    values = data["relative_traffic_pct"].to_numpy(float)
    fig, axis = plt.subplots(figsize=(11.4, 6.6))
    bars = axis.bar(x, values, width=0.72, color=colors)
    axis.axhline(100, color="#202020", linestyle="--", linewidth=1.2)
    display_bins = data["f_bin"].astype("string").str.replace(">=", "≥", regex=False)
    axis.set_xticks(x, display_bins, rotation=0)
    axis.set_xlabel("Daytime mean wind speed, 10:00–21:59 (m/s)")
    axis.set_ylabel("Daily traffic relative to expected (%)")
    axis.set_title(title)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    ymax = max(110, float(data["relative_traffic_pct"].max()) * 1.08)
    axis.set_ylim(0, ymax)
    for bar, row in zip(bars, data.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            max(4, row.relative_traffic_pct - 3),
            f"n={row.counter_days:,}",
            ha="center",
            va="top",
            fontsize=8.1,
            color="white",
            fontweight="bold",
        )
    fig.subplots_adjust(left=0.11, right=0.98, top=0.91, bottom=0.24)
    fig.text(
        0.5,
        0.035,
        "Expected daily traffic: mean for the same counter, year, month, and weekday. "
        "Wind is the mean from 10:00 to 21:59.",
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
        bars = axis.bar(x, values, width=0.72, color=np.where(sparse, "#A8A8A8", "#287271"))
        axis.axhline(100, color="#202020", linestyle="--", linewidth=1.1)
        axis.set_title(titles[period], fontsize=11)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
        axis.set_ylim(0, ymax)
        for bar, row in zip(bars, data.itertuples(index=False), strict=True):
            axis.text(bar.get_x() + bar.get_width() / 2, min(ymax - 2, row.relative_traffic_pct + 1.2), f"n={row.counter_days:,}", ha="center", va="bottom", fontsize=7.5)
    axes[-1].set_xticks(np.arange(len(data)), data["f_bin"], rotation=0)
    axes[-1].set_xlabel("Daytime mean wind speed, 10:00–21:59 (m/s)")
    fig.supylabel("Daily traffic relative to expected (%)")
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
- Rows with mean wind from 0 to <45 m/s: {len(eligible):,} ({100 * len(eligible) / len(panel):.2f}%).
- Traffic is reported as a 24-hour count. Wind is the mean from 10:00 to 21:59.

## Standardisation

For each counter-day, expected traffic is the arithmetic mean daily count for
the same counter, calendar year, month, and weekday. The reported ratio is the
sum of observed daily vehicles divided by the sum of expected daily vehicles in
a wind bin. This compares the observed share of traffic in the bin with its
expected share after local calendar standardisation.

## Seasons

- VDU: December--March.
- SDU: June--September.
- VHDU: April--May and October--November.

## Outputs

- `{RESULTS}`: thesis display with the stable >=25 m/s tail.
- `{DETAILED_RESULTS}`: the same analysis data retained for inspection.
- `{PERIOD_SUMMARY}`: daily-count sample by traffic period.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build daily traffic O/E by mean wind.")
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-r", "--results", type=Path, default=RESULTS)
    parser.add_argument("-p", "--period-summary", type=Path, default=PERIOD_SUMMARY)
    parser.add_argument("-b", "--bootstrap-replicates", type=int, default=1000)
    args = parser.parse_args()

    panel = prepare_panel(args.input)
    results = build_results(panel, args.bootstrap_replicates)
    period_summary = build_period_summary(panel)
    for path in [args.results, args.period_summary]:
        path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.results, index=False)
    period_summary.to_csv(args.period_summary, index=False)
    print(period_summary.to_string(index=False))
    print(results[results["scope"].eq("All periods")].to_string(index=False))


if __name__ == "__main__":
    main()
