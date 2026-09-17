"""Generate compact thesis tables for the supervisor-aligned traffic analysis."""

from pathlib import Path
import re

import pandas as pd


SELECTION = Path("reports/main/tables/monthly_vkt_selection.csv")
RATES = Path("reports/main/tables/monthly_vkt_rate.csv")
OUTPUT_DIR = Path("reports/thesis/generated")


def selection_tex(data: pd.DataFrame) -> str:
    rows = []
    for index, row in enumerate(data.itertuples(index=False)):
        removed = "--" if row.removed == 0 else f"{row.removed:,}"
        step = str(row.step)
        step = step.replace(">=", "$\\geq$").replace("<=", "$\\leq$")
        # Reader-facing ranges use en dashes in LaTeX.
        step = re.sub(r"(?<=\d)-(?=\d)", "--", step)
        step = step.replace("counter-section road/year", "counter-section for road/year")
        if "Require usable wind and gust" in step:
            step += r" ($\leq$20 km, $\pm$5 min)"
        if index > 0:
            step = chr(96 + index) + ") " + re.sub(r"^[0a-z]\)\s*", "", step)
        rows.append(
            f"{step} & {removed} & {row.remaining:,} \\\\ \\grayhline"
        )

    # Do not draw a grey rule after the final row.
    if rows:
        rows[-1] = rows[-1].replace(r" \\ \grayhline", r" \\")

    return r"""\begin{table}[H]
\centering
\caption[Selection for the monthly-frequency VKT analysis.]{Selection for the monthly-frequency VKT analysis. The first row includes urban and rural injury accidents; the rural restriction is applied in step (b). The final set contains minor, serious and fatal injury accidents and is distinct from the supporting allocated daily-counter sample.}
\label{tab:monthly-vkt-selection}
\small
\begin{tabular}{p{0.64\textwidth}rr}
\toprule
Step & Removed & Remaining \\ \midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}

\vspace{0.4em}
\begin{minipage}{0.94\textwidth}
\footnotesize
\textit{Notes:} The 21 road-location failures in step (d) comprise five records
without usable road geometry, 15 located more than 100 m from their registered
road, and one projected outside the counter sections. For step (f), the 20 km
weather distance is measured from the counter-section location rather than the
accident coordinate; valid mean wind and gust are required within five minutes
of the recorded accident time.
\end{minipage}
\end{table}
"""


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
\\caption{Monthly-frequency VKT rates, 2019--2024. Exposure is the full observed daily traffic count times rural section length, allocated by the assigned station's pooled 2007--2025 calendar-month weather frequency for 07:00--24:00.}
\\label{tab:monthly-vkt-rate}
\\small
\\begin{tabular}{llrrr}
\\toprule
Measure & Interval (m/s) & Observed & \\shortstack{Million\\\\vehicle-km} & \\shortstack{Accidents per\\\\million vehicle-km} \\\\ \\midrule
""" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "monthly_vkt_selection.tex").write_text(selection_tex(pd.read_csv(SELECTION)))
    (OUTPUT_DIR / "monthly_vkt_rate.tex").write_text(rates_tex(pd.read_csv(RATES)))
    print("wrote monthly VKT thesis tables")


if __name__ == "__main__":
    main()
