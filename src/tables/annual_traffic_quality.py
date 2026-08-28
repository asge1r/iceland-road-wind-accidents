"""Write a compact quality audit of annual road-section traffic inputs."""

from __future__ import annotations

import argparse
import calendar
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = Path("data/analysis/annual_traffic.csv")
DEFAULT_OUTPUT = Path("reports/main/tables/annual_traffic_quality.csv")
PERIOD_MONTHS = {"VDU": [12, 1, 2, 3], "SDU": [6, 7, 8, 9]}


def period_days(year: int, period: str) -> int:
    return sum(calendar.monthrange(int(year), month)[1] for month in PERIOD_MONTHS[period])


def build_audit(source: pd.DataFrame) -> pd.DataFrame:
    required = {"year", "road_section", "section_length_km", "adu", "sdu", "vdu"}
    missing = required - set(source)
    if missing:
        raise ValueError(f"Annual-traffic CSV is missing columns: {sorted(missing)}")
    data = source[source["year"].between(2007, 2025)].copy()
    if data.duplicated(["year", "road_section"]).any():
        raise ValueError("Annual traffic has duplicate road-section/year keys")
    year_days = data["year"].map(lambda year: 366 if calendar.isleap(int(year)) else 365)
    sdu_days = data["year"].map(lambda year: period_days(int(year), "SDU"))
    vdu_days = data["year"].map(lambda year: period_days(int(year), "VDU"))
    vhdu_days = year_days - sdu_days - vdu_days
    derived_vhdu = (
        data["adu"] * year_days - data["sdu"] * sdu_days - data["vdu"] * vdu_days
    ) / vhdu_days
    rows = [
        ("section_years", len(data), "Rows in the 2007–2025 annual-traffic study period."),
        ("road_sections", data["road_section"].nunique(), "Distinct registered road sections."),
        ("nonpositive_section_length", data["section_length_km"].le(0).sum(), "Excluded from vehicle-kilometre exposure."),
        ("nonpositive_adu", data["adu"].le(0).sum(), "Source values requiring exclusion from annual exposure."),
        ("nonpositive_sdu", data["sdu"].le(0).sum(), "Source values requiring exclusion from SDU exposure."),
        ("nonpositive_vdu", data["vdu"].le(0).sum(), "Source values requiring exclusion from VDU exposure."),
        ("nonpositive_derived_vhdu", derived_vhdu.le(0).sum(), "Residual VHDU values excluded from exposure."),
        ("sdu_below_vdu", data["sdu"].lt(data["vdu"]).sum(), "Descriptive source check; not automatically invalid."),
        (
            "adu_outside_sdu_vdu_range",
            (
                data["adu"].lt(data[["sdu", "vdu"]].min(axis=1))
                | data["adu"].gt(data[["sdu", "vdu"]].max(axis=1))
            ).sum(),
            "Descriptive source check; seasonal averages need not bracket ADU.",
        ),
    ]
    return pd.DataFrame(rows, columns=["metric", "section_years", "interpretation"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    audit = build_audit(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(args.output, index=False)
    print(audit.to_string(index=False))


if __name__ == "__main__":
    main()
