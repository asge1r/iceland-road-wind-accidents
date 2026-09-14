"""Plot accident rates from daily traffic and pooled monthly weather."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


INPUT = Path("data/analysis/monthly_vkt.csv")
OUTPUT = Path("reports/main/figures/monthly_vkt_rate.png")


def main() -> None:
    data = pd.read_csv(INPUT)
    data = data[data["outcome"].eq("All injury accidents")]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.7), constrained_layout=True)
    for ax, variable, title in zip(
        axes, ["f", "fg"], ["Mean wind speed", "Maximum gust"], strict=True,
    ):
        part = data[data["variable"].eq(variable)].sort_values("bin_order")
        tick_labels = part["bin_label"].str.replace(">=", "≥", regex=False)
        bars = ax.bar(
            tick_labels, part["rate_per_million_vehicle_km"],
            color="#4477AA", edgecolor="white",
        )
        ax.bar_label(bars, labels=[str(value) for value in part["observed_accidents"]], padding=3, fontsize=8)
        ax.set_title(title)
        ax.set_xlabel("Weather bin (m/s)")
        ax.set_ylabel("Injury accidents per million estimated VKT")
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)
    fig.suptitle("Daily-counter rate with vehicle-km allocated by monthly weather frequency")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=220)
    plt.close(fig)
    print(f"wrote={OUTPUT}")


if __name__ == "__main__":
    main()
