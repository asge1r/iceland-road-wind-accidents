"""Assemble the final road-period traffic and accident panel."""

from __future__ import annotations

import calendar

import numpy as np
import pandas as pd

from src.traffic.road_common import (
    TRAFFIC_PERIOD_MONTHS,
    YEARS,
    traffic_period_days,
)

def build_base_table(
    assigned_panel: pd.DataFrame,
    counts: pd.DataFrame,
) -> pd.DataFrame:
    base = assigned_panel.merge(
        counts,
        on=["year", "road_section", "traffic_period"],
        how="left",
        validate="one_to_one",
    )
    for column in [
        "injury_accidents",
        "serious_or_fatal_accidents",
        "fatal_accidents",
    ]:
        base[column] = base[column].fillna(0).astype(int)
    base["traffic_period_months"] = base["traffic_period"].map(
        TRAFFIC_PERIOD_MONTHS
    )
    base["period"] = base["traffic_period"] + " " + base["year"].astype(str)
    year_days = base["year"].map(lambda year: 366 if calendar.isleap(year) else 365)
    sdu_days = base["year"].map(lambda year: traffic_period_days(year, "SDU"))
    vdu_days = base["year"].map(lambda year: traffic_period_days(year, "VDU"))
    other_days = year_days - sdu_days - vdu_days
    base["other_daily_traffic_derived"] = (
        base["adu"] * year_days - base["sdu"] * sdu_days - base["vdu"] * vdu_days
    ) / other_days
    invalid_other = base["other_daily_traffic_derived"].le(0)
    base.loc[invalid_other, "other_daily_traffic_derived"] = np.nan
    base["traffic_reference_name"] = base["traffic_period"].map(
        {"VDU": "VDU", "SDU": "SDU", "VHDU": "Derived VHDU"}
    )
    base["traffic_reference_daily_volume"] = np.select(
        [
            base["traffic_period"].eq("VDU"),
            base["traffic_period"].eq("SDU"),
        ],
        [base["vdu"], base["sdu"]],
        default=base["other_daily_traffic_derived"],
    )
    base["traffic_reference_method"] = np.where(
        base["traffic_period"].eq("VHDU"),
        "derived residual from ADU, SDU, VDU and calendar-day weights",
        "official seasonal average for the defined traffic period",
    )
    return base.sort_values(
        ["road_section", "year", "traffic_period_order"]
    )

def build_long_table(
    base: pd.DataFrame, wind: pd.DataFrame, bin_counts: pd.DataFrame
) -> pd.DataFrame:
    wind = wind[
        wind["year"].isin(YEARS) & wind["variable"].eq("f_5m")
    ].copy()
    wind_columns = [
        "weather_station_id",
        "year",
        "traffic_period",
        "variable",
        "bin_label",
        "bin_lower_ms",
        "bin_upper_ms",
        "measurement_count",
        "total_measurements_in_period",
        "frequency_pct",
    ]
    wind_key = [
        "weather_station_id",
        "year",
        "traffic_period",
        "variable",
        "bin_label",
    ]
    if wind.duplicated(wind_key).any():
        raise ValueError("Wind frequency contains duplicate station-period-bin keys")

    bin_template = (
        wind[["variable", "bin_label", "bin_lower_ms", "bin_upper_ms"]]
        .drop_duplicates()
        .sort_values(["variable", "bin_lower_ms"])
    )
    expanded = base.assign(_cross=1).merge(
        bin_template.assign(_cross=1), on="_cross", how="inner"
    ).drop(columns="_cross")
    long = expanded.merge(
        wind[wind_columns].drop(
            columns=["bin_lower_ms", "bin_upper_ms"]
        ),
        on=wind_key,
        how="left",
        validate="many_to_one",
    )
    period_totals = (
        wind.groupby(
            ["weather_station_id", "year", "traffic_period", "variable"],
            as_index=False,
        )["total_measurements_in_period"]
        .max()
        .rename(
            columns={"total_measurements_in_period": "available_period_measurements"}
        )
    )
    long = long.merge(
        period_totals,
        on=["weather_station_id", "year", "traffic_period", "variable"],
        how="left",
        validate="many_to_one",
    )
    long["wind_frequency_available"] = long["available_period_measurements"].notna()
    missing_zero = long["wind_frequency_available"] & long["frequency_pct"].isna()
    long.loc[missing_zero, "measurement_count"] = 0
    long.loc[missing_zero, "frequency_pct"] = 0.0
    long.loc[long["wind_frequency_available"], "total_measurements_in_period"] = (
        long.loc[long["wind_frequency_available"], "available_period_measurements"]
    )
    long = long.drop(columns="available_period_measurements")
    long = long.merge(
        bin_counts,
        on=[
            "year",
            "road_section",
            "traffic_period",
            "variable",
            "bin_label",
        ],
        how="left",
        validate="one_to_one",
    )
    for column in [
        "bin_injury_accidents",
        "bin_serious_or_fatal_accidents",
        "bin_fatal_accidents",
    ]:
        long[column] = long[column].fillna(0).astype(int)
    return long.sort_values(
        [
            "road_section",
            "year",
            "traffic_period_order",
            "variable",
            "bin_lower_ms",
        ],
        na_position="last",
    )
