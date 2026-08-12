"""Export the small Git-tracked bundle used to reproduce reported results.

This deliberately exports final tables and figures, not raw data, daily
counter-day records, or the 10-minute weather archive. It is suitable for a
supervisor to clone and inspect immediately.
"""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path("data/replication")
WORKING = [
    Path("data/processed/accidents.csv"),
    Path("data/processed/stations.csv"),
    Path("data/processed/annual_traffic.csv"),
]
TABLES = Path("reports/main/tables")
FIGURES = Path("reports/main/figures")


def copy_file(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Missing {source}; create the local results first.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> None:
    for source in WORKING:
        copy_file(source, ROOT / "working" / source.name)
    for source in sorted(TABLES.glob("*.csv")):
        copy_file(source, ROOT / "tables" / source.name)
    for source in sorted(FIGURES.glob("*.png")):
        copy_file(source, ROOT / "figures" / source.name)
    (ROOT / "README.md").write_text(
        "# Replication bundle\n\n"
        "This small bundle lets a clone display and redraw the reported results "
        "without raw accident deliveries, daily counter records, or the 10-minute "
        "weather archive. `working/` contains the three small inspection tables; "
        "`tables/` contains exact numerical result tables; and `figures/` is the "
        "reference output snapshot. Run `python -m src.reproduce_results` to draw "
        "the core result figures again from the result tables.\n",
        encoding="utf-8",
    )
    print(f"Wrote replication bundle to {ROOT}")


if __name__ == "__main__":
    main()
