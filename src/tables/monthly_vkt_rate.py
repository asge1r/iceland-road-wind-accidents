"""Publish the monthly-frequency daily-counter rate table."""

from pathlib import Path

import pandas as pd


INPUT = Path("data/analysis/monthly_vkt.csv")
OUTPUT = Path("reports/main/tables/monthly_vkt_rate.csv")


def main() -> None:
    data = pd.read_csv(INPUT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUTPUT, index=False)
    print(f"wrote={OUTPUT} rows={len(data):,}")


if __name__ == "__main__":
    main()
