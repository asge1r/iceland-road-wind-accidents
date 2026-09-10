"""Draw one odds-ratio figure from a completed model-result CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def labels(data: pd.DataFrame, group: str, comparison: str, reference: str) -> list[str]:
    def clean(value: object) -> str:
        text = str(value)
        if text == "Fall":
            text = "Autumn"
        return text.replace(">=", "≥").replace("-", "–")

    return [
        f"{group_value}: {clean(comparison_value)} vs {clean(reference_value)}"
        for group_value, comparison_value, reference_value in zip(
            data[group], data[comparison], data[reference], strict=True
        )
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, required=True)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("-t", "--title", required=True)
    parser.add_argument("-g", "--group-column", default="predictor")
    parser.add_argument("-e", "--estimate-column", default="odds_ratio")
    parser.add_argument(
        "-G", "--groups", nargs="+",
        help="Keep only these values from the group column, in the supplied order.",
    )
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = {
        args.group_column, "comparison", "reference", args.estimate_column,
        "ci_95_low", "ci_95_high",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"Model table is missing columns: {sorted(missing)}")
    if args.groups:
        unknown = set(args.groups) - set(data[args.group_column])
        if unknown:
            raise ValueError(f"Requested groups are absent: {sorted(unknown)}")
        order = {value: index for index, value in enumerate(args.groups)}
        data = data[data[args.group_column].isin(args.groups)].copy()
        data["_group_order"] = data[args.group_column].map(order)
        data = data.sort_values("_group_order", kind="stable").drop(
            columns="_group_order"
        )
    data = data.iloc[::-1].reset_index(drop=True)
    estimates = data[args.estimate_column].to_numpy(float)
    y = np.arange(len(data))
    height = max(4.0, 0.42 * len(data) + 1.8)
    figure, axis = plt.subplots(figsize=(11.5, height), constrained_layout=True)
    axis.scatter(estimates, y, color="#287271", s=42, zorder=3)
    axis.axvline(1, color="#222222", linestyle="--", linewidth=1)
    axis.set_yticks(
        y,
        labels(data, args.group_column, "comparison", "reference"),
    )
    axis.set_xlabel("Odds ratio")
    axis.set_title(args.title)
    axis.grid(axis="x", alpha=0.2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=240)
    plt.close(figure)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
