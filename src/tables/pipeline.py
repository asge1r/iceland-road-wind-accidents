"""Generate the thesis pipeline tables from ``docs/pipeline.md``."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


INPUT = Path("docs/pipeline.md")
PREPARATION_OUTPUT = Path("reports/thesis/generated_pipeline_preparation.tex")
ANALYSIS_OUTPUT = Path("reports/thesis/generated_pipeline_analysis.tex")


def markdown_table(text: str, heading: str) -> list[list[str]]:
    section = text.split(f"## {heading}", maxsplit=1)
    if len(section) != 2:
        raise ValueError(f"Missing Markdown section: {heading}")
    lines = section[1].splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.startswith("| Script |")),
        None,
    )
    if start is None:
        raise ValueError(f"Missing four-column table under: {heading}")
    rows: list[list[str]] = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            raise ValueError(f"Pipeline row does not have four cells: {line}")
        rows.append(cells)
    if not rows:
        raise ValueError(f"No pipeline rows found under: {heading}")
    return rows


def escape_text(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
    }
    return "".join(replacements.get(character, character) for character in value)


def latex_cell(value: str, paths: bool) -> str:
    value = value.replace("<br>", "\n")
    tokens: list[str] = []

    def save(latex: str) -> str:
        tokens.append(latex)
        return f"@@TOKEN{len(tokens) - 1}@@"

    value = re.sub(
        r"\*`([^`]+)`\*",
        lambda match: save(r"\emph{\path{" + match.group(1).strip() + "}}"),
        value,
    )
    value = re.sub(
        r"\*([^*]+/)\*",
        lambda match: save(r"\emph{\path{" + match.group(1).strip() + "}}"),
        value,
    )
    value = re.sub(
        r"`([^`]+)`",
        lambda match: save(
            (r"\path{" if paths else r"\texttt{")
            + (match.group(1).strip() if paths else escape_text(match.group(1).strip()))
            + "}"
        ),
        value,
    )
    value = escape_text(value).replace("\n", r"\newline ")
    for index, token in enumerate(tokens):
        value = value.replace(f"@@TOKEN{index}@@", token)
    return value.strip()


def render_part(
    rows: list[list[str]], caption: str, label: str | None, continued: bool = False
) -> str:
    body = []
    for index, row in enumerate(rows):
        cells = [latex_cell(cell, paths=column < 3) for column, cell in enumerate(row)]
        rule = r" \\ \grayhline" if index < len(rows) - 1 else r" \\"
        body.append(" &\n".join(cells) + rule)
    label_line = rf"\label{{{label}}}" if label else ""
    continuation = r"\ContinuedFloat" if continued else ""
    return "\n".join([
        r"\begin{table}[p]",
        continuation,
        r"\centering",
        r"\tiny",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        rf"\caption{{{caption}}}",
        label_line,
        r"\begin{tabularx}{\textwidth}{L{0.18\textwidth}!{\color{gray!45}\vrule width 0.3pt}L{0.27\textwidth}!{\color{gray!45}\vrule width 0.3pt}L{0.29\textwidth}!{\color{gray!45}\vrule width 0.3pt}X}",
        r"\toprule",
        "Script & Input file(s) & Output file(s) & Description \\\\",
        r"\midrule",
        *body,
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
        "",
    ])


def render(
    rows: list[list[str]], caption: str, label: str, split_at: int | None = None
) -> str:
    if split_at is None or len(rows) <= split_at:
        return render_part(rows, caption, label)
    return "\n".join([
        render_part(rows[:split_at], caption, label),
        render_part(rows[split_at:], f"{caption} (continued)", None, continued=True),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=INPUT)
    parser.add_argument("-p", "--preparation-output", type=Path, default=PREPARATION_OUTPUT)
    parser.add_argument("-a", "--analysis-output", type=Path, default=ANALYSIS_OUTPUT)
    args = parser.parse_args()
    text = args.input.read_text(encoding="utf-8")
    outputs = [
        (
            args.preparation_output,
            render(
                markdown_table(text, "Preparation scripts"),
                "Exact inputs and outputs of the data-preparation pipeline",
                "tab:pipeline",
            ),
        ),
        (
            args.analysis_output,
            render(
                markdown_table(text, "Analysis scripts"),
                "Exact inputs and outputs of the ordinary analysis pipeline",
                "tab:analysis-pipeline",
                split_at=12,
            ),
        ),
    ]
    for path, content in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote={path}")


if __name__ == "__main__":
    main()
