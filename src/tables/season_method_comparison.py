"""Compare the four season-specific strong-wind analyses."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


WEATHER = Path("reports/working/tables/oe_scenarios.csv")
MATCHED = Path("reports/main/tables/wind_season.csv")
ANNUAL = Path("reports/main/tables/season_rate.csv")
DAILY = Path("reports/working/tables/daily_season_rate.csv")
DAILY_OE = Path("reports/main/tables/daily_season_oe.csv")
DAILY_FULL_INTERACTION = Path("reports/working/tables/daily_season_interaction.csv")
DAILY_FOCUSED_INTERACTION = Path(
    "reports/working/tables/daily_highwind_season_interaction.csv"
)
OUTPUT = Path("reports/working/tables/season_method_comparison.csv")
SEASON_MAP = {"Fall": "Autumn"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    weather = pd.read_csv(WEATHER)
    weather = weather[
        weather["variable"].eq("f")
        & weather["radius_km"].eq(20)
        & weather["severity_group"].eq("Injury accidents")
        & weather["max_time_difference_minutes"].eq(5)
        & ~weather["analysis_season"].eq("All seasons")
        & weather["weather_bin"].isin(["15-20", "20-25", ">=25"])
    ].groupby("analysis_season", as_index=False).agg(
        weather_observed_highwind=("observed_accidents", "sum"),
        weather_expected_highwind=("expected_accidents", "sum"),
    )
    weather["weather_only_oe"] = (
        weather["weather_observed_highwind"] / weather["weather_expected_highwind"]
    )
    weather = weather.rename(columns={"analysis_season": "season"})

    matched = pd.read_csv(MATCHED)
    matched_p = float(
        matched.loc[matched["result"].eq("Season interaction test"), "p_value"].iloc[0]
    )
    matched = matched[matched["result"].eq("Season-specific estimate")][
        ["season", "odds_ratio", "ci_95_low", "ci_95_high"]
    ].rename(columns={
        "odds_ratio": "matched_time_or", "ci_95_low": "matched_time_ci_low",
        "ci_95_high": "matched_time_ci_high",
    })

    annual = pd.read_csv(ANNUAL)
    annual = annual[annual["bin_label"].eq(">=15")][
        [
            "season", "observed_accidents", "time_proportional_rate_ratio",
            "time_proportional_ci_95_low", "time_proportional_ci_95_high",
        ]
    ].rename(columns={
        "observed_accidents": "annual_highwind_accidents",
        "time_proportional_rate_ratio": "annual_traffic_rr",
        "time_proportional_ci_95_low": "annual_traffic_ci_low",
        "time_proportional_ci_95_high": "annual_traffic_ci_high",
    })

    daily = pd.read_csv(DAILY)
    daily = daily[daily["wind_bin"].eq(">=15")][
        ["season", "observed_accidents", "rate_ratio", "ci_95_low", "ci_95_high"]
    ].rename(columns={
        "observed_accidents": "daily_highwind_accidents",
        "rate_ratio": "daily_traffic_rr", "ci_95_low": "daily_traffic_ci_low",
        "ci_95_high": "daily_traffic_ci_high",
    })

    daily_oe = pd.read_csv(DAILY_OE)
    daily_oe = daily_oe[daily_oe["wind_bin"].eq(">=15")][
        ["season", "traffic_standardised_oe", "ci_95_low", "ci_95_high"]
    ].rename(columns={
        "ci_95_low": "traffic_oe_ci_low", "ci_95_high": "traffic_oe_ci_high"
    })
    full = pd.read_csv(DAILY_FULL_INTERACTION)
    full_p = float(
        full.loc[full["season"].eq("All seasons"), "p_value"].iloc[0]
    )
    focused = pd.read_csv(DAILY_FOCUSED_INTERACTION)
    focused_p = float(
        focused.loc[focused["season"].eq("All seasons"), "p_value"].iloc[0]
    )

    for frame in (weather, matched, annual, daily, daily_oe):
        frame["season"] = frame["season"].replace(SEASON_MAP)
    result = weather.merge(matched, on="season", validate="one_to_one").merge(
        annual, on="season", validate="one_to_one"
    ).merge(
        daily, on="season", validate="one_to_one"
    ).merge(daily_oe, on="season", validate="one_to_one")
    result["matched_time_interaction_p"] = matched_p
    result["daily_full_interaction_p"] = full_p
    result["daily_highwind_interaction_p"] = focused_p
    order = pd.Categorical(
        result["season"], ["Winter", "Spring", "Summer", "Autumn"], ordered=True
    )
    result = result.assign(_order=order).sort_values("_order").drop(columns="_order")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
