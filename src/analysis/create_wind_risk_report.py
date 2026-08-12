"""Create the primary gust O/E result from the compact-analysis workflow."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.wind_bins import FG_UPPER_BOUNDS, labels


DETAILS = Path("data/cache/oe_station_period_bins.parquet")
TABLE = Path("reports/main/tables/gust_risk.csv")
FIGURE = Path("reports/main/figures/gust_risk.png")
BINS = labels(FG_UPPER_BOUNDS)
SEED = 20260729  # fixed seed from the former complete scenario sequence
REPLICATES = 5000


def primary_station_bins(details: pd.DataFrame) -> pd.DataFrame:
    """Return station-by-gust-bin observed and expected accident counts."""
    data = details[
        details["variable"].eq("fg")
        & details["radius_km"].eq(20)
        & details["severity_group"].eq("Injury accidents")
        & details["analysis_season"].eq("All seasons")
        & details["max_time_difference_minutes"].eq(5)
    ].copy()
    return data.groupby(["weather_station_id", "weather_bin"], as_index=False).agg(
        observed_accidents=("observed_accidents", "sum"),
        expected_accidents=("expected_accidents", "sum"),
    )


def bootstrap(station_bins: pd.DataFrame) -> pd.DataFrame:
    """Calculate weather-station-clustered 95% intervals for each gust bin."""
    observed = station_bins.pivot(index="weather_station_id", columns="weather_bin", values="observed_accidents").reindex(columns=BINS, fill_value=0).fillna(0)
    expected = station_bins.pivot(index="weather_station_id", columns="weather_bin", values="expected_accidents").reindex(index=observed.index, columns=BINS, fill_value=0).fillna(0)
    rng = np.random.default_rng(SEED)
    weights = rng.multinomial(len(observed), np.full(len(observed), 1 / len(observed)), size=REPLICATES)
    ratios = np.divide(weights @ observed.to_numpy(float), weights @ expected.to_numpy(float), out=np.full((REPLICATES, len(BINS)), np.nan), where=(weights @ expected.to_numpy(float)) > 0)
    return pd.DataFrame({
        "weather_bin": BINS,
        "station_bootstrap_ci_95_low": np.nanpercentile(ratios, 2.5, axis=0),
        "station_bootstrap_ci_95_high": np.nanpercentile(ratios, 97.5, axis=0),
        "bootstrap_probability_above_1": np.nanmean(ratios > 1, axis=0),
    })


def summarize(details: pd.DataFrame) -> pd.DataFrame:
    station_bins = primary_station_bins(details)
    result = station_bins.groupby("weather_bin", as_index=False).agg(
        observed_accidents=("observed_accidents", "sum"), expected_accidents=("expected_accidents", "sum")
    ).set_index("weather_bin").reindex(BINS, fill_value=0).reset_index()
    result["observed_expected_ratio"] = result["observed_accidents"] / result["expected_accidents"]
    result = result.merge(bootstrap(station_bins), on="weather_bin", how="left")
    result["sparse_bin_fewer_than_20_accidents"] = result["observed_accidents"].lt(20)
    return result.rename(columns={"weather_bin": "wind_gust_interval_ms"})


def plot(data: pd.DataFrame) -> None:
    x = np.arange(len(data)); values = data["observed_expected_ratio"].to_numpy(float)
    low = values - data["station_bootstrap_ci_95_low"].to_numpy(float)
    high = data["station_bootstrap_ci_95_high"].to_numpy(float) - values
    colors = np.where(data["sparse_bin_fewer_than_20_accidents"], "#A8A8A8", "#C7522A")
    fig, axis = plt.subplots(figsize=(14.5, 7.2), constrained_layout=True)
    axis.bar(x, values, color=colors, width=.72)
    axis.errorbar(x, values, yerr=[low, high], fmt="none", ecolor="#222222", capsize=4)
    axis.axhline(1, color="#222222", linestyle="--", linewidth=1)
    axis.set_xticks(x, data["wind_gust_interval_ms"].str.replace(">=", "≥", regex=False))
    axis.set_xlabel("Maximum wind-gust interval, fg (m/s)")
    axis.set_ylabel("Observed / expected accidents")
    axis.set_title("Rural injury accidents by maximum wind gust")
    axis.grid(axis="y", alpha=.2); axis.set_ylim(0, max(1.5, float(data["station_bootstrap_ci_95_high"].max()) * 1.18))
    FIGURE.parent.mkdir(parents=True, exist_ok=True); fig.savefig(FIGURE, dpi=240); plt.close(fig)


def main() -> None:
    data = summarize(pd.read_parquet(DETAILS))
    TABLE.parent.mkdir(parents=True, exist_ok=True); data.to_csv(TABLE, index=False)
    plot(data)
    print(f"Wrote {TABLE} and {FIGURE}")


if __name__ == "__main__":
    main()
