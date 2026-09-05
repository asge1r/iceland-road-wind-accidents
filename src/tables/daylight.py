"""Compare accident-time daylight with matched non-accident dates."""

from __future__ import annotations

import argparse
import calendar
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.discrete.conditional_models import ConditionalLogit

from src.analysis.solar import DAYLIGHT_LABELS, daylight_class, solar_elevation


INPUT = Path("data/analysis/accidents.csv")
OUTPUT = Path("reports/main/tables/daylight.csv")


def matched_times(accidents: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for accident in accidents.itertuples(index=False):
        timestamp = accident.timestamp
        days = calendar.monthrange(timestamp.year, timestamp.month)[1]
        times = [timestamp]
        times.extend(
            pd.Timestamp(
                timestamp.year, timestamp.month, day,
                timestamp.hour, timestamp.minute, timestamp.second,
            )
            for day in range(1, days + 1)
            if pd.Timestamp(timestamp.year, timestamp.month, day).weekday()
            == timestamp.weekday()
            and day != timestamp.day
        )
        for index, sample_time in enumerate(times):
            rows.append(
                {
                    "stratum_id": accident.id,
                    "case": int(index == 0),
                    "timestamp": sample_time,
                    "lat": accident.lat,
                    "lon": accident.lon,
                }
            )
    return pd.DataFrame(rows)


def fit(accidents: pd.DataFrame) -> pd.DataFrame:
    required = ["id", "timestamp", "lat", "lon"]
    missing = set(required) - set(accidents)
    if missing:
        raise ValueError(f"accidents.csv is missing columns: {sorted(missing)}")
    accidents = accidents[required].copy()
    accidents["timestamp"] = pd.to_datetime(accidents["timestamp"], errors="raise")
    samples = matched_times(accidents)
    samples["solar_elevation_deg"] = solar_elevation(
        samples["timestamp"], samples["lat"], samples["lon"]
    )
    samples["daylight_class"] = daylight_class(samples["solar_elevation_deg"])
    informative = samples.groupby("stratum_id")["daylight_class"].nunique().gt(1)
    design = pd.get_dummies(
        pd.Categorical(samples["daylight_class"], categories=DAYLIGHT_LABELS),
        dtype=float,
    ).drop(columns="Daylight")
    model = ConditionalLogit(
        samples["case"], design, groups=samples["stratum_id"]
    ).fit(disp=False, maxiter=500)
    intervals = model.conf_int()
    case_counts = samples[samples["case"].eq(1)]["daylight_class"].value_counts()
    rows = []
    for comparison in ["Darkness", "Civil twilight"]:
        rows.append(
            {
                "predictor": "Daylight",
                "comparison": comparison,
                "reference": "Daylight",
                "odds_ratio": np.exp(model.params[comparison]),
                "ci_95_low": np.exp(intervals.loc[comparison].iloc[0]),
                "ci_95_high": np.exp(intervals.loc[comparison].iloc[1]),
                "p_value": model.pvalues[comparison],
                "observed_accidents": int(case_counts.get(comparison, 0)),
                "total_strata": samples["stratum_id"].nunique(),
                "informative_strata": int(informative.sum()),
                "control_times": int(samples["case"].eq(0).sum()),
                "matching": "same location, month, weekday, and clock time",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = fit(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
