"""Model serious-or-fatal severity among recorded injury accidents."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.weather.frequency import TEMPERATURE_LABELS, TEMPERATURE_THRESHOLDS


ACCIDENTS = Path("data/analysis/accidents.csv")
CONDITIONS = Path("data/analysis/accident_conditions.csv")
OUTPUT = Path("reports/main/tables/severity_conditions.csv")


def categorical_design(
    values: pd.Series, categories: list[str], reference: str, prefix: str
) -> pd.DataFrame:
    factor = pd.Categorical(values, categories=categories, ordered=True)
    return pd.get_dummies(factor, prefix=prefix, dtype=float).drop(
        columns=f"{prefix}_{reference}"
    )


def fit(accidents: pd.DataFrame, conditions: pd.DataFrame) -> pd.DataFrame:
    accident_columns = {"id", "meidsli", "hour", "season"}
    condition_columns = {
        "id", "f", "weather_station_dist_km", "weather_time_difference_minutes",
        "temperature_c", "temp_distance_km", "temp_time_diff_min", "daylight_class",
    }
    for data, required, name in [
        (accidents, accident_columns, "accidents.csv"),
        (conditions, condition_columns, "accident_conditions.csv"),
    ]:
        missing = required - set(data)
        if missing:
            raise ValueError(f"{name} is missing columns: {sorted(missing)}")
    data = accidents[list(accident_columns)].merge(
        conditions[list(condition_columns)], on="id", validate="one_to_one"
    )
    valid = (
        data["f"].notna()
        & data["weather_station_dist_km"].le(20)
        & data["weather_time_difference_minutes"].le(5)
        & data["temperature_c"].notna()
        & data["temp_distance_km"].le(20)
        & data["temp_time_diff_min"].le(5)
        & data["daylight_class"].notna()
    )
    data = data[valid].reset_index(drop=True).copy()
    data["wind"] = pd.cut(
        data["f"], [0, 10, 15, np.inf], labels=["0-10", "10-15", ">=15"], right=False
    ).astype("string")
    data["temperature"] = pd.cut(
        data["temperature_c"],
        [-np.inf, *TEMPERATURE_THRESHOLDS, np.inf],
        labels=TEMPERATURE_LABELS,
        right=False,
    ).astype("string")
    data["time"] = pd.cut(
        data["hour"], [0, 6, 10, 16, 20, 24],
        labels=["00-06", "06-10", "10-16", "16-20", "20-24"], right=False,
    ).astype("string")
    specifications = [
        ("Mean wind", "wind", ["0-10", "10-15", ">=15"], "0-10", "m/s"),
        ("Temperature", "temperature", TEMPERATURE_LABELS, "0-3", "°C"),
        ("Daylight", "daylight_class", ["Darkness", "Civil twilight", "Daylight"], "Daylight", ""),
        ("Time of day", "time", ["00-06", "06-10", "10-16", "16-20", "20-24"], "10-16", ""),
        ("Season", "season", ["Winter", "Spring", "Summer", "Fall"], "Summer", ""),
    ]
    designs = [
        categorical_design(data[column], categories, reference, f"x{index}")
        for index, (_, column, categories, reference, _) in enumerate(specifications)
    ]
    design = sm.add_constant(pd.concat(designs, axis=1), has_constant="add")
    outcome = data["meidsli"].le(2).astype(int)
    model = sm.Logit(outcome, design).fit(disp=False, cov_type="HC1")
    intervals = model.conf_int()
    rows: list[dict[str, object]] = []
    for index, (predictor, _, categories, reference, unit) in enumerate(specifications):
        for category in categories:
            if category == reference:
                continue
            term = f"x{index}_{category}"
            suffix = f" {unit}" if unit else ""
            rows.append(
                {
                    "predictor": predictor,
                    "comparison": f"{category}{suffix}",
                    "reference": f"{reference}{suffix}",
                    "odds_ratio": np.exp(model.params[term]),
                    "ci_95_low": np.exp(intervals.loc[term].iloc[0]),
                    "ci_95_high": np.exp(intervals.loc[term].iloc[1]),
                    "p_value": model.pvalues[term],
                    "accidents": len(data),
                    "serious_or_fatal_accidents": int(outcome.sum()),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=ACCIDENTS)
    parser.add_argument("-c", "--conditions", type=Path, default=CONDITIONS)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = fit(pd.read_csv(args.accidents), pd.read_csv(args.conditions))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
