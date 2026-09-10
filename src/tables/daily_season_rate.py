"""Fit the allocated daily-counter rate model separately by season."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.tables.counter_rate import fit_model
from src.tables.daily_season_panel import LABELS, OUTPUT as PANEL, SEASONS, read_panel


OUTPUT = Path("reports/working/tables/daily_season_rate.csv")
AUDIT = Path("reports/working/tables/daily_season_rate_audit.csv")


def calculate(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    results: list[pd.DataFrame] = []
    audit_rows: list[dict[str, object]] = []
    for season_name in SEASONS:
        data = panel[panel["season"].eq(season_name)].copy()
        informative = data.groupby("stratum")["observed_accidents"].transform("sum").gt(0)
        data = data[informative & data["allocated_vehicles"].gt(0)].copy()
        if data.empty:
            raise ValueError(f"No informative strata remain for {season_name}")

        fit_input = data.rename(columns={"allocated_vehicles": "observed_vehicles"})
        result = fit_model(fit_input, LABELS).rename(
            columns={
                "observed_vehicles": "estimated_vehicles_within_wind_bin",
                "accidents_per_100k_counted_vehicles":
                    "accidents_per_100k_estimated_vehicles",
            }
        )
        result["season"] = season_name
        result["analysis_period"] = "2019-2024"
        result["exposure_method"] = (
            "observed daily traffic allocated by full-day wind frequency"
        )
        results.append(result)
        audit_rows.append(
            {
                "season": season_name,
                "model_accidents": int(data["observed_accidents"].sum()),
                "candidate_strata": int(data["stratum"].nunique()),
                "fitted_strata": int(result["model_strata"].iloc[0]),
                "model_rows": int(result["model_rows"].iloc[0]),
            }
        )
    return pd.concat(results, ignore_index=True), pd.DataFrame(audit_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--panel", type=Path, default=PANEL)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    parser.add_argument("-u", "--audit", type=Path, default=AUDIT)
    args = parser.parse_args()
    output, audit = calculate(read_panel(args.panel))
    for path in [args.output, args.audit]:
        path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    audit.to_csv(args.audit, index=False)
    print("\nAUDIT")
    print(audit.to_string(index=False))
    print("\nRESULTS")
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()
