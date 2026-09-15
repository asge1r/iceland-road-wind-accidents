"""Illustrate one cleaned accident before any weather linkage."""
from pathlib import Path
import pandas as pd
from src.tables.thesis import write_table


def cleaned_example(output: Path) -> None:
    data = pd.read_csv("data/processed/accidents/all.csv", low_memory=False)
    eligible = data[data.urban_rural.eq("Rural") & data.meidsli.eq(3)
                    & data.vehicle_count.eq(1)
                    & data.registered_road_section.str.startswith("1-", na=False)]
    row = eligible.sort_values(["timestamp", "id"]).iloc[0]
    timestamp = pd.Timestamp(row.timestamp)
    rows = [
        ["Example identifier", "A (source identifier omitted)"],
        ["Date", timestamp.strftime("%Y-%m-%d")],
        ["Time (rounded to the hour)", timestamp.round("h").strftime("%H:%M")],
        ["Registered road section", row.registered_road_section],
        ["Approximate location", f"{row.lat:.1f} degrees N, {abs(row.lon):.1f} degrees W"],
        ["Area classification", "Rural"],
        ["Injury category", "Minor injury"],
        ["Involved vehicles", int(row.vehicle_count)],
    ]
    write_table(output / "cleaned_accident_example.tex",
        "Example of a cleaned rural injury-accident record. The table illustrates "
        "accident-level information retained before weather matching. The source "
        "identifier is omitted, time is rounded to the hour, and coordinates to "
        "0.1 degree; no weather fields are included.",
        "tab:cleaned-accident-example", "ll", ["Field", "Example value"], rows,
        short_caption="Example of a cleaned rural injury-accident record.")


if __name__ == "__main__":
    cleaned_example(Path("reports/thesis/generated"))
