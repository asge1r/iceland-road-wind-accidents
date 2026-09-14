"""Generate compact thesis tables for the supervisor-aligned traffic analysis."""

from pathlib import Path

import pandas as pd


SELECTION = Path("reports/main/tables/monthly_vkt_selection.csv")
RATES = Path("reports/main/tables/monthly_vkt_rate.csv")
OUTPUT_DIR = Path("reports/thesis/generated")


def selection_tex(data: pd.DataFrame) -> str:
    rows = []
    for row in data.itertuples(index=False):
        removed = "--" if row.removed == 0 else f"{row.removed:,}"
        rows.append(f"{str(row.step).replace('>=', '$\\geq$')} & {removed} & {row.remaining:,} \\\\ \\grayhline")
    return """\\begin{table}[htbp]
\\centering
\\caption{Selection for the monthly-frequency daily-counter rate. The final set contains all injury severities and is distinct from the earlier allocated daily samples.}
\\label{tab:monthly-vkt-selection}
\\small
\\begin{tabular}{p{0.64\\textwidth}rr}
\\toprule
Step & Removed & Remaining \\\\ \\midrule
""" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n"


def rates_tex(data: pd.DataFrame) -> str:
    data = data[data["outcome"].eq("All injury accidents")].copy()
    names = {"f": "Mean wind", "fg": "Gust"}
    rows = []
    for row in data.sort_values(["variable", "bin_order"]).itertuples(index=False):
        label = str(row.bin_label).replace(">=", "$\\geq$")
        rows.append(
            f"{names[row.variable]} & {label} & {row.observed_accidents:,} & "
            f"{row.estimated_vehicle_km / 1e6:.1f} & {row.rate_per_million_vehicle_km:.3f} \\\\ \\grayhline"
        )
    return """\\begin{table}[htbp]
\\centering
\\caption{Monthly-frequency daily-counter rates, 2019--2024. Exposure is the full observed daily traffic count times rural section length, allocated by the assigned station's pooled 2007--2025 calendar-month weather frequency for 07:00--24:00.}
\\label{tab:monthly-vkt-rate}
\\small
\\begin{tabular}{llrrr}
\\toprule
Measure & Interval (m/s) & Observed & Million VKT & Rate per million VKT \\\\ \\midrule
""" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "monthly_vkt_selection.tex").write_text(selection_tex(pd.read_csv(SELECTION)))
    (OUTPUT_DIR / "monthly_vkt_rate.tex").write_text(rates_tex(pd.read_csv(RATES)))
    print("wrote monthly VKT thesis tables")


if __name__ == "__main__":
    main()
