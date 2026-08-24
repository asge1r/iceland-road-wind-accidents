"""Create simple English descriptive figures for the accident data."""

import argparse
from pathlib import Path
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


STUDY_ACCIDENTS = Path("data/analysis/accidents.csv")
OUT_DATA = Path("reports/main/tables/accident_characteristics.csv")
OUT_TYPE_AUDIT = Path("archive/generated_diagnostics/accident_types.csv")

BLUE = "#547A99"
GREEN = "#4F8068"
GOLD = "#D5A444"
TEXT = "#243238"


def broad_accident_family(code: int) -> str:
    """Map the detailed accident code to a small interpretable family."""
    if 11 <= code <= 95:
        return "Single vehicle: run-off-road, rollover, fall, or other"
    if 111 <= code <= 160:
        return "Same direction: overtaking, lane change, or rear-end"
    if 211 <= code <= 280:
        return "Opposing, overtaking, or reversing vehicles"
    if 310 <= code <= 440:
        return "Turning and changes in direction"
    if 510 <= code <= 696:
        return "Junctions, roundabouts, and priority"
    if 710 <= code <= 743:
        return "Stopped or parked vehicles"
    if 810 <= code <= 880:
        return "Pedestrians and horse riders"
    if 910 <= code <= 999:
        return "Animals, fixed objects, and other events"
    if 1090 <= code <= 1095:
        return "Bicycles"
    return "Unclassified"


def prepare_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    study = pd.read_csv(STUDY_ACCIDENTS)
    if study["vehicle_count"].isna().any():
        raise ValueError("Some study accidents have no prepared vehicle count.")
    study["vehicle_group"] = study["vehicle_count"].map(
        lambda n: "1 vehicle" if n == 1 else ("2 vehicles" if n == 2 else "3 or more")
    )
    study["accident_family"] = study["tegohapps"].map(broad_accident_family)
    study["severity_group"] = np.where(
        study["meidsli"].le(2), "Fatal or serious", "Minor injury"
    )

    family = (
        study.groupby("accident_family", as_index=False)
        .agg(count=("id", "size"))
        .sort_values("count", ascending=False)
    )
    family["percent"] = 100 * family["count"] / len(study)

    vehicles = (
        study["vehicle_group"]
        .value_counts()
        .reindex(["1 vehicle", "2 vehicles", "3 or more"], fill_value=0)
        .rename_axis("category")
        .reset_index(name="count")
    )
    vehicles["percent"] = 100 * vehicles["count"] / len(study)

    severity = (
        study.groupby(["accident_family", "severity_group"], as_index=False)
        .agg(count=("id", "size"))
    )
    severity["group_total"] = severity.groupby("severity_group")["count"].transform("sum")
    severity["percent"] = 100 * severity["count"] / severity["group_total"]

    tidy = pd.concat(
        [
            family.assign(dimension="accident_family", category=family["accident_family"])[
                ["dimension", "category", "count", "percent"]
            ],
            vehicles.assign(dimension="vehicle_count")[
                ["dimension", "category", "count", "percent"]
            ],
            severity.assign(
                dimension="accident_family_by_severity",
                category=severity["accident_family"] + " | " + severity["severity_group"],
            )[["dimension", "category", "count", "percent"]],
        ],
        ignore_index=True,
    )
    return family, vehicles, severity, tidy


def wrap(values: pd.Series, width: int = 42) -> list[str]:
    return ["\n".join(textwrap.wrap(value, width=width)) for value in values]


def plot_accident_families(family: pd.DataFrame) -> None:
    data = family.sort_values("count")
    fig, axis = plt.subplots(figsize=(10.5, 7), constrained_layout=True)
    bars = axis.barh(wrap(data["accident_family"]), data["count"], color=BLUE)
    for bar, count, percent in zip(
        bars, data["count"], data["percent"], strict=True
    ):
        axis.text(
            bar.get_width() + 25,
            bar.get_y() + bar.get_height() / 2,
            f"{count:,} ({percent:.1f}%)",
            va="center",
            fontsize=9,
            color=TEXT,
        )
    axis.set_title("Rural injury accidents by accident type", weight="bold")
    axis.set_xlabel("Accidents")
    axis.set_xlim(0, data["count"].max() * 1.24)
    axis.grid(axis="x", alpha=0.2)
    axis.spines[["top", "right", "left"]].set_visible(False)
    fig.savefig("reports/main/figures/accident_types.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def plot_vehicles(vehicles: pd.DataFrame) -> None:
    fig, axis = plt.subplots(figsize=(8, 5.5), constrained_layout=True)
    bars = axis.bar(
        vehicles["category"], vehicles["count"], color=[GREEN, BLUE, GOLD]
    )
    for bar, count, percent in zip(
        bars, vehicles["count"], vehicles["percent"], strict=True
    ):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{count:,}\n({percent:.1f}%)",
            ha="center",
            va="bottom",
            color=TEXT,
        )
    axis.set_title("Vehicles involved in rural injury accidents", weight="bold")
    axis.set_ylabel("Accidents")
    axis.set_ylim(0, vehicles["count"].max() * 1.18)
    axis.grid(axis="y", alpha=0.2)
    axis.spines[["top", "right"]].set_visible(False)
    fig.savefig("reports/main/figures/vehicles_per_accident.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def plot_severity(severity: pd.DataFrame, family: pd.DataFrame) -> None:
    order = family.sort_values("count", ascending=False)["accident_family"].tolist()
    pivot = (
        severity.pivot(index="accident_family", columns="severity_group", values="percent")
        .reindex(order)
        .fillna(0)
    )
    pivot = pivot.iloc[::-1]
    y = np.arange(len(pivot))
    width = 0.38
    fig, axis = plt.subplots(figsize=(10.5, 7.5), constrained_layout=True)
    axis.barh(
        y - width / 2,
        pivot["Minor injury"],
        width,
        label="Minor injury (code 3)",
        color=BLUE,
    )
    axis.barh(
        y + width / 2,
        pivot["Fatal or serious"],
        width,
        label="Fatal or serious (codes 1–2)",
        color=GOLD,
    )
    axis.set_yticks(y, wrap(pd.Series(pivot.index), width=38))
    axis.set_xlabel("Share within severity group (%)")
    axis.set_title("Accident types by injury severity", weight="bold")
    axis.legend(frameon=False)
    axis.grid(axis="x", alpha=0.2)
    axis.spines[["top", "right"]].set_visible(False)
    fig.savefig("reports/main/figures/accident_types_by_severity.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-a", "--accidents", type=Path, default=STUDY_ACCIDENTS)
    parser.add_argument("-o", "--output", type=Path, default=OUT_DATA)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global STUDY_ACCIDENTS, OUT_DATA
    STUDY_ACCIDENTS = args.accidents
    OUT_DATA = args.output
    family, vehicles, severity, tidy = prepare_data()
    OUT_DATA.parent.mkdir(parents=True, exist_ok=True)
    tidy.to_csv(OUT_DATA, index=False)
    severity.to_csv(OUT_TYPE_AUDIT, index=False)
    plot_accident_families(family)
    plot_vehicles(vehicles)
    plot_severity(severity, family)
    print("Wrote reports/main/figures/accident_types.png")
    print("Wrote reports/main/figures/vehicles_per_accident.png")
    print("Wrote reports/main/figures/accident_types_by_severity.png")


if __name__ == "__main__":
    main()
