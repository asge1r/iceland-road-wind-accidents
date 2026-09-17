"""Illustrate one cleaned accident before any weather linkage."""
from pathlib import Path
import pandas as pd
from src.tables.thesis import write_table


def cleaned_example(output: Path) -> None:
    data = pd.read_csv("data/processed/accidents/all.csv", low_memory=False, dtype={"lat": str, "lon": str})
    eligible = data[data.urban_rural.eq("Rural") & data.meidsli.eq(3)
                    & data.vehicle_count.eq(1)
                    & data.registered_road_section.str.startswith("1-", na=False)]
    row = eligible.sort_values(["timestamp", "id"]).iloc[0]
    timestamp = pd.Timestamp(row.timestamp)
    rows = [
        ["Source record identifier", "Withheld"],
        ["Date", timestamp.strftime("%Y-%m-%d")],
        ["Recorded time", timestamp.strftime("%H:%M:%S")],
        ["Registered road section", row.registered_road_section],
        ["Latitude / longitude (degrees)", f"{row.lat}, {row.lon}"],
        ["Area classification", "Rural"],
        ["Injury category", "Minor injury"],
        ["Involved vehicles", int(row.vehicle_count)],
    ]
    write_table(output / "cleaned_accident_example.tex",
        "Example of a cleaned rural injury accident record. The table illustrates "
        "accident-level information retained before weather matching. The source "
        "record identifier is withheld; other displayed fields are reproduced from the cleaned accident record.",
        "tab:cleaned-accident-example", "ll", ["Field", "Example value"], rows,
        short_caption="Example of a cleaned rural injury accident record.")


if __name__ == "__main__":
    cleaned_example(Path("reports/thesis/generated"))
