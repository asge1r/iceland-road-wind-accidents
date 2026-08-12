"""Recalculate daily-traffic wind O/E from compact counter-by-bin input."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.plots import plot_daily_wind


INPUT = Path("data/analysis/daily_counter_wind.csv")
TABLE = Path("reports/main/tables/daily_traffic_wind.csv")
FIGURE = Path("reports/main/figures/daily_traffic_wind.png")
BINS = ["0-3", "3-6", "6-9", "9-12", "12-15", "15-18", "18-21", "21-24", ">=24"]


def intervals(data: pd.DataFrame, seed: int = 20260729, reps: int = 5000) -> pd.DataFrame:
    counters = data["counter_site_id"].unique()
    rng = np.random.default_rng(seed)
    rows = []
    for wind_bin in BINS:
        part = data[data["f_bin"].eq(wind_bin)].set_index("counter_site_id")
        observed = part["observed_daytime_vehicles"].reindex(counters, fill_value=0).to_numpy(float)
        expected = part["expected_daytime_vehicles"].reindex(counters, fill_value=0).to_numpy(float)
        draw = rng.integers(0, len(counters), size=(reps, len(counters)))
        ratio = observed[draw].sum(axis=1) / expected[draw].sum(axis=1)
        rows.append({"f_bin": wind_bin, "oe_ci_95_low": np.quantile(ratio, .025), "oe_ci_95_high": np.quantile(ratio, .975)})
    return pd.DataFrame(rows)


def main() -> None:
    data = pd.read_csv(INPUT)
    data = data[data["traffic_period"].eq("All periods")].copy()
    result = data.groupby("f_bin", as_index=False).agg(
        counter_days=("counter_days", "sum"), counters=("counter_site_id", "nunique"),
        observed_daytime_vehicles=("observed_daytime_vehicles", "sum"),
        expected_daytime_vehicles=("expected_daytime_vehicles", "sum"),
    ).set_index("f_bin").reindex(BINS).reset_index()
    result["observed_to_expected_traffic"] = result["observed_daytime_vehicles"] / result["expected_daytime_vehicles"]
    result["relative_traffic_pct"] = 100 * result["observed_to_expected_traffic"]
    result = result.merge(intervals(data), on="f_bin", how="left")
    result["relative_traffic_ci_95_low_pct"] = 100 * result["oe_ci_95_low"]
    result["relative_traffic_ci_95_high_pct"] = 100 * result["oe_ci_95_high"]
    result["scope"] = "All periods"
    result["weather_stations"] = np.nan
    result["daytime_traffic_share_assumption"] = 0.95
    TABLE.parent.mkdir(parents=True, exist_ok=True); result.to_csv(TABLE, index=False)
    plot_daily_wind(result, FIGURE)
    print(f"Wrote {TABLE} and {FIGURE}")


if __name__ == "__main__":
    main()
