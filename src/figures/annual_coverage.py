"""Draw annual accident counts and weather-match coverage."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


INPUT = Path("reports/main/tables/weather_coverage.csv")
OUTPUT = Path("reports/main/figures/weather_coverage.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {
        "year", "rural_injury_accidents", "wind_coverage_pct",
        "temperature_coverage_pct",
    }
    if missing := required - set(data):
        raise ValueError(f"Annual coverage table is missing columns: {sorted(missing)}")
    plt.rcParams.update({"font.size": 13, "axes.labelsize": 15, "axes.titlesize": 16})
    count_figure, counts = plt.subplots(figsize=(12, 4.5), constrained_layout=True)
    figure, coverage = plt.subplots(figsize=(12, 4.5), constrained_layout=True)
    counts.bar(data["year"], data["rural_injury_accidents"], color="#547A99")
    counts.set_ylabel("Accidents")
    counts.set_title("Rural injury accidents by year")
    counts.grid(axis="y", alpha=0.2)
    counts.set_xlabel("Year")
    counts.set_xticks(data["year"])
    counts.tick_params(axis="x", labelrotation=45)
    identical = data["wind_coverage_pct"].equals(data["temperature_coverage_pct"])
    if identical:
        coverage.plot(
            data["year"], data["wind_coverage_pct"], marker="o",
            label="Wind and temperature (identical)", color="#287271",
        )
    else:
        coverage.plot(data["year"], data["wind_coverage_pct"], marker="o", color="#287271", label="Wind")
        coverage.plot(
            data["year"], data["temperature_coverage_pct"], marker="o",
            label="Temperature",
        )
    coverage.set_ylabel("Matched accidents (%)")
    coverage.set_xlabel("Year")
    coverage.set_ylim(70, 101)
    coverage.set_title("Weather-match coverage")
    coverage.grid(axis="y", alpha=0.2)
    coverage.legend(frameon=False, ncol=2)
    coverage.set_xticks(data["year"])
    coverage.tick_params(axis="x", labelrotation=45)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count_path = args.output.with_name("annual_accident_counts.png")
    count_figure.savefig(count_path, dpi=240)
    plt.close(count_figure)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
