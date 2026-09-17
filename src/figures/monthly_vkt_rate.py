"""Port Kristján's rate presentation to the unchanged monthly exposure results."""
from pathlib import Path
import pandas as pd
from src.figures.weather_rate import make_figures
from src.tables.monthly_vkt_rate import severity_rates, SECTIONS, INPUT

OUTPUT = Path("reports/main/figures")
ACCIDENTS = Path("data/analysis/vkt_accidents.csv")


def main() -> None:
    data = severity_rates(pd.read_csv(SECTIONS), pd.read_csv(INPUT), pd.read_csv(ACCIDENTS))
    data = data.rename(columns={"observed_accidents": "accidents"})
    data["outcome"] = data["outcome"].replace({"Serious or fatal injury accidents": "Severe/fatal accidents"})
    # The same display aggregation sums existing counts and exposure; no CSV changes.
    paths = make_figures(data, OUTPUT, variables=("f", "fg", "temperature"), prefix="monthly_", annual_variables=("f", "fg"))
    print("wrote=" + ",".join(map(str, paths)))


if __name__ == "__main__":
    main()
