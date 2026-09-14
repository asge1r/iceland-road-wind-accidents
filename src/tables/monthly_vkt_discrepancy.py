"""Diagnose composition and concentration in monthly-frequency VKT rates."""

from pathlib import Path

import pandas as pd


INPUT = Path("data/analysis/monthly_vkt_section.csv")
OUTPUT = Path("reports/main/tables/monthly_vkt_discrepancy.csv")


def build(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    strata = ["counter_section_id", "year", "season"]
    for variable in ["f", "fg"]:
        data = panel[panel["variable"].eq(variable)].copy()
        data["stratum_accidents"] = data.groupby(strata, observed=True)["observed_accidents"].transform("sum")
        data["stratum_vkt"] = data.groupby(strata, observed=True)["estimated_vehicle_km"].transform("sum")
        data["within_stratum_expected"] = (
            data["stratum_accidents"] * data["estimated_vehicle_km"] / data["stratum_vkt"]
        )
        section_baseline = data.groupby("counter_section_id", observed=True).agg(
            section_accidents=("observed_accidents", "sum"),
            section_vkt=("estimated_vehicle_km", "sum"),
        )
        section_baseline["section_baseline_rate_per_million"] = (
            section_baseline["section_accidents"] / section_baseline["section_vkt"] * 1_000_000
        )
        for bin_label, part in data.groupby("bin_label", observed=True):
            by_section = part.groupby("counter_section_id", observed=True).agg(
                exposure=("estimated_vehicle_km", "sum"),
                observed=("observed_accidents", "sum"),
            )
            exposure_share = by_section["exposure"] / by_section["exposure"].sum()
            observed_share = by_section["observed"] / by_section["observed"].sum() if by_section["observed"].sum() else by_section["observed"]
            observed = int(part["observed_accidents"].sum())
            expected = float(part["within_stratum_expected"].sum())
            exposure = float(part["estimated_vehicle_km"].sum())
            weighted = by_section.join(section_baseline[["section_baseline_rate_per_million"]])
            rows.append({
                "variable": variable,
                "bin_label": bin_label,
                "bin_order": int(part["bin_order"].iloc[0]),
                "observed_accidents": observed,
                "estimated_vehicle_km": exposure,
                "raw_rate_per_million_vkt": observed / exposure * 1_000_000,
                "within_section_year_season_expected": expected,
                "within_section_year_season_oe": observed / expected,
                "exposure_weighted_section_baseline_rate": (
                    weighted["exposure"] * weighted["section_baseline_rate_per_million"]
                ).sum() / weighted["exposure"].sum(),
                "exposure_top_section_share": exposure_share.max(),
                "exposure_top_five_share": exposure_share.nlargest(5).sum(),
                "exposure_hhi": (exposure_share ** 2).sum(),
                "accident_top_section_share": observed_share.max(),
                "accident_top_five_share": observed_share.nlargest(5).sum(),
            })
    return pd.DataFrame(rows).sort_values(["variable", "bin_order"])


def main() -> None:
    result = build(pd.read_csv(INPUT))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)
    print(f"wrote={OUTPUT} rows={len(result):,}")


if __name__ == "__main__":
    main()
