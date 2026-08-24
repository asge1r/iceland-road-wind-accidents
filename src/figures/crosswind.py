"""Create the exploratory frequency-adjusted crosswind figure.

The input is the verified summary produced by the archived direction pilot.
Traffic is deliberately not added: daily traffic can be crosswind-adjusted
only after wind direction has been obtained for all counter-days.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


DEFAULT_INPUT = Path("reports/main/tables/crosswind.csv")
DEFAULT_OUTPUT = Path("reports/main/figures/crosswind.png")


def create_figure(summary: pd.DataFrame, output: Path) -> None:
    """Plot O/E and weather-station bootstrap intervals for two wind groups."""
    required = {
        "crosswind_group",
        "observed_accidents",
        "expected_accidents",
        "observed_expected_ratio",
        "ci_95_low",
        "ci_95_high",
    }
    missing = required - set(summary)
    if missing:
        raise ValueError(f"Crosswind summary is missing columns: {sorted(missing)}")

    values = summary["observed_expected_ratio"].to_numpy(dtype=float)
    low = summary["ci_95_low"].to_numpy(dtype=float)
    high = summary["ci_95_high"].to_numpy(dtype=float)
    errors = np.vstack([values - low, high - values])
    x = np.arange(len(summary))

    fig, axis = plt.subplots(figsize=(7.2, 5.2))
    bars = axis.bar(
        x,
        values,
        yerr=errors,
        capsize=6,
        width=0.62,
        color=["#6B8E9B", "#C7522A"],
    )
    axis.axhline(1, color="#333333", linestyle="--", linewidth=1.2)
    axis.set_xticks(x, ["Crosswind <9 m/s", "Crosswind ≥9 m/s"])
    axis.set_ylabel("Observed / expected injury accidents (O/E)")
    axis.set_title("Injury accidents during crosswind")
    axis.grid(axis="y", color="#dddddd", linewidth=0.7)
    axis.set_axisbelow(True)

    for bar, row in zip(bars, summary.itertuples(index=False), strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            row.ci_95_high + 0.025,
            f"O/E {row.observed_expected_ratio:.2f}\n"
            f"{row.observed_accidents:,.0f} observed",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    axis.set_ylim(0, max(1.45, float(high.max()) + 0.18))
    fig.text(
        0.5,
        0.01,
        "Frequency-adjusted within weather station and week; not traffic-adjusted.",
        ha="center",
        fontsize=8.5,
        color="#444444",
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    create_figure(pd.read_csv(args.input), args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
