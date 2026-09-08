"""Count linked accidents for road-period wind intervals."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.traffic.road_common import TRAFFIC_PERIOD_BY_MONTH, YEARS, normalize_section
from src.weather.frequency import F_FIVE_MS_UPPER_BOUNDS, labels

def build_accident_counts(
    accidents_path: Path, annual: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    accidents = pd.read_csv(
        accidents_path,
        usecols=[
            "id",
            "timestamp",
            "meidsli",
            "registered_road_section",
            "within_20km",
            "wind_available",
            "f",
            "fg",
        ],
    )
    timestamp = pd.to_datetime(accidents["timestamp"], errors="coerce")
    accidents["year"] = timestamp.dt.year
    accidents["traffic_period"] = timestamp.dt.month.map(TRAFFIC_PERIOD_BY_MONTH)
    accidents["road_section"] = normalize_section(
        accidents["registered_road_section"]
    )
    accidents["severity_code"] = pd.to_numeric(accidents["meidsli"], errors="coerce")
    accidents = accidents[accidents["year"].isin(YEARS)].merge(
        annual[["year", "road_section"]],
        on=["year", "road_section"],
        how="inner",
        validate="many_to_one",
    )
    diagnostics = {
        "rural_injury_accidents_2007_2025": int(
            pd.read_csv(accidents_path, usecols=["timestamp"])["timestamp"]
            .pipe(pd.to_datetime, errors="coerce")
            .dt.year.isin(YEARS)
            .sum()
        ),
        "exact_annual_road_section_matches": len(accidents),
        "exact_matches_serious_or_fatal": int(accidents["severity_code"].le(2).sum()),
    }
    counts = (
        accidents.groupby(
            ["year", "road_section", "traffic_period"], as_index=False
        )
        .agg(
            injury_accidents=("id", "size"),
            serious_or_fatal_accidents=(
                "severity_code",
                lambda values: int(values.le(2).sum()),
            ),
            fatal_accidents=("severity_code", lambda values: int(values.eq(1).sum())),
        )
    )

    clean_wind = accidents[
        accidents["within_20km"].fillna(False)
        & accidents["wind_available"].fillna(False)
        & accidents["f"].between(0, 45, inclusive="left")
        & accidents["fg"].between(0, 65, inclusive="left")
        & accidents["fg"].add(0.5).ge(accidents["f"])
    ].copy()
    diagnostics["exact_matches_with_clean_wind_within_20km"] = len(clean_wind)
    diagnostics["exact_matches_excluded_from_wind_bins"] = len(accidents) - len(clean_wind)
    diagnostics["clean_wind_bin_coverage_pct_x100"] = int(
        round(10_000 * len(clean_wind) / len(accidents))
    )
    diagnostics["clean_wind_serious_or_fatal"] = int(
        clean_wind["severity_code"].le(2).sum()
    )

    clean_wind["variable"] = "f_5m"
    clean_wind["bin_label"] = pd.cut(
        clean_wind["f"],
        bins=np.concatenate(([0.0], F_FIVE_MS_UPPER_BOUNDS, [np.inf])),
        labels=labels(F_FIVE_MS_UPPER_BOUNDS),
        right=False,
        include_lowest=True,
    ).astype("string")
    bin_counts = (
        clean_wind.groupby(
            ["year", "road_section", "traffic_period", "variable", "bin_label"],
            as_index=False,
            observed=True,
        )
        .agg(
            bin_injury_accidents=("id", "size"),
            bin_serious_or_fatal_accidents=(
                "severity_code", lambda series: int(series.le(2).sum())
            ),
            bin_fatal_accidents=(
                "severity_code", lambda series: int(series.eq(1).sum())
            ),
        )
    )
    return counts, bin_counts, diagnostics
