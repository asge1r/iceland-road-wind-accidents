"""Standardize AADT, SDT, WDT, and road-section length from annual traffic files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pandas as pd


RAW_DIR = Path("data/raw/traffic/annual")
HISTORICAL_RAW_DIR = RAW_DIR
OUT_DIR = Path("data/processed/traffic")
OUT_CSV = OUT_DIR / "annual.csv"
OUT_NOTES = Path("archive/generated_diagnostics/annual_traffic_notes.txt")

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def col_to_idx(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch.upper()) - 64
    return n - 1


def shared_strings(z: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
        for si in root.findall("a:si", NS)
    ]


def workbook_sheets(z: ZipFile) -> list[tuple[str, str]]:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sheets: list[tuple[str, str]] = []
    for sh in wb.find("a:sheets", NS):
        target = relmap[sh.attrib[f"{{{NS['r']}}}id"]]
        sheet_path = "xl/" + target if not target.startswith("/") else target[1:]
        sheets.append((sh.attrib["name"], sheet_path))
    return sheets


def sheet_rows(z: ZipFile, sheet_path: str, strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(z.read(sheet_path))
    rows: list[list[str]] = []
    for row in root.findall(".//a:sheetData/a:row", NS):
        cells: dict[int, str] = {}
        for cell in row.findall("a:c", NS):
            ref = cell.attrib.get("r", "")
            if not ref:
                continue
            idx = col_to_idx(ref)
            typ = cell.attrib.get("t")
            v = cell.find("a:v", NS)
            inline = cell.find("a:is", NS)
            value = ""
            if typ == "s" and v is not None:
                value = strings[int(v.text)]
            elif typ == "inlineStr" and inline is not None:
                value = "".join(
                    t.text or ""
                    for t in inline.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                )
            elif v is not None:
                value = v.text or ""
            cells[idx] = value
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return rows


def numeric(value: object) -> float:
    return float(pd.to_numeric(value, errors="coerce"))


def numeric_or_nan(row: list[object], index: int | None) -> float:
    """Read an optional numeric column, preserving older workbook coverage."""
    return numeric(row[index]) if index is not None and index < len(row) else float("nan")


def normalise_road_section(road_number: object, section_code: object) -> str | None:
    road_number_text = str(road_number).strip()
    section_code_text = str(section_code).strip().lower()
    if not road_number_text or not section_code_text:
        return None
    try:
        road_number_text = str(int(float(road_number_text)))
    except ValueError:
        pass
    try:
        # Excel stores numeric section codes without display formatting. The
        # official key is 01, 02, ..., while alphanumeric codes such as a1 are
        # already preserved as text.
        section_code_text = str(int(float(section_code_text))).zfill(2)
    except ValueError:
        pass
    if road_number_text.lower() == "nan" or section_code_text.lower() == "nan":
        return None
    return f"{road_number_text}-{section_code_text}"


def find_weighted_road_sheet(sheets: list[tuple[str, str]]) -> tuple[str, str]:
    for name, path in sheets:
        if "vegið, vegnúmeraröð" in name.lower():
            return name, path
    for name, path in sheets:
        if "vegnúmeraröð" in name.lower():
            return name, path
    raise ValueError("No road-number-order sheet found.")


def parse_workbook(path: Path) -> pd.DataFrame:
    match = re.search(r"(?:umferd|traffic|umf)_(\d{4})", path.name)
    if not match:
        raise ValueError(f"Could not infer year from {path.name}")
    year = int(match.group(1))

    if path.suffix.lower() == ".xls":
        workbook = pd.ExcelFile(path, engine="xlrd")
        sheet_name = next(
            (name for name in workbook.sheet_names if "vegið, vegnúmeraröð" in name.lower()),
            next(name for name in workbook.sheet_names if "vegnúmeraröð" in name.lower()),
        )
        frame = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="xlrd")
        rows = frame.where(frame.notna(), "").values.tolist()
    else:
        with ZipFile(path) as z:
            strings = shared_strings(z)
            sheet_name, sheet_path = find_weighted_road_sheet(workbook_sheets(z))
            rows = sheet_rows(z, sheet_path, strings)

    header_i = None
    for i, row in enumerate(rows):
        if len(row) > 10 and str(row[0]).strip().lower() == "vegnr" and "kaflanr" in str(row[1]).lower():
            header_i = i
            break
    if header_i is None:
        raise ValueError(f"Could not find header row in {path.name}")

    header = [str(value).strip() for value in rows[header_i]]
    columns = {name: i for i, name in enumerate(header)}

    def col(*names: str) -> int | None:
        stripped = {key.removeprefix("r"): value for key, value in columns.items()}
        for name in names:
            if name in columns:
                return columns[name]
            if name in stripped:
                return stripped[name]
        return None

    required = {
        "road_number": col("Vegnr"),
        "section_code": col("Kaflanr"),
        "road_name": col("Vegheiti"),
        "section_start_name": col("Heiti upphafspunkts"),
        "section_end_name": col("Heiti endapunkts"),
        "section_start_station_km": col("Bst"),
        "section_end_station_km": col("Est"),
        "section_length_km": col("Lengd"),
        "adu": col("ÁDU"),
        "sdu": col("SDU"),
        "vdu": col("VDU"),
        "thousand_vehicle_km": col("Eknir þ. km"),
    }

    records: list[dict[str, object]] = []
    for row in rows[header_i + 1 :]:
        max_required = max(i for i in required.values() if i is not None)
        if len(row) <= max_required:
            continue
        road_section = normalise_road_section(row[required["road_number"]], row[required["section_code"]])
        if road_section is None:
            continue
        adu = pd.to_numeric(row[required["adu"]], errors="coerce")
        length = pd.to_numeric(row[required["section_length_km"]], errors="coerce")
        if pd.isna(adu) or pd.isna(length):
            continue
        records.append(
            {
                "year": year,
                "source_file": path.name,
                "source_sheet": sheet_name,
                "road_section": road_section,
                "road_number": road_section.split("-", maxsplit=1)[0],
                "section_code": road_section.split("-", maxsplit=1)[1],
                "road_name": row[required["road_name"]],
                "section_start_name": row[required["section_start_name"]],
                "section_end_name": row[required["section_end_name"]],
                "section_start_station_km": numeric_or_nan(
                    row, required["section_start_station_km"]
                ),
                "section_end_station_km": numeric_or_nan(
                    row, required["section_end_station_km"]
                ),
                "section_length_km": numeric(row[required["section_length_km"]]),
                "adu": numeric(row[required["adu"]]),
                "sdu": numeric(row[required["sdu"]]),
                "vdu": numeric(row[required["vdu"]]),
                "thousand_vehicle_km": numeric(row[required["thousand_vehicle_km"]]),
            }
        )
    return pd.DataFrame(records).drop_duplicates(["year", "road_section"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input-dir", type=Path, default=RAW_DIR)
    parser.add_argument("-o", "--output", type=Path, default=OUT_CSV)
    parser.add_argument("-n", "--notes", type=Path, default=OUT_NOTES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    historical = [
        path
        for path in args.input_dir.glob("*")
        if path.suffix.lower() in {".xls", ".xlsx"}
        and re.search(r"(?:umferd|umf)_\d{4}", path.name)
    ]
    current = [*args.input_dir.glob("umferd_*.xlsx"), *args.input_dir.glob("traffic_*.xlsx")]
    # Prefer the current standardized copy if the same calendar year exists in
    # both source directories (2018 is historical only in the present project).
    by_year: dict[int, Path] = {}
    for path in sorted([*historical, *current]):
        year = int(re.search(r"(?:umferd|traffic|umf)_(\d{4})", path.name).group(1))
        if year not in by_year or path.parent == RAW_DIR:
            by_year[year] = path
    files = [by_year[year] for year in sorted(by_year)]
    if not files:
        raise SystemExit(f"No annual traffic workbooks found in {args.input_dir}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.notes.parent.mkdir(parents=True, exist_ok=True)

    exposure = pd.concat([parse_workbook(path) for path in files], ignore_index=True)
    exposure = exposure.sort_values(["year", "road_section"])
    exposure.to_csv(args.output, index=False)

    yearly = (
        exposure.groupby("year", as_index=False)
        .agg(
            rows=("road_section", "size"),
            road_sections=("road_section", "nunique"),
            adu_min=("adu", "min"),
            adu_max=("adu", "max"),
        )
    )
    notes = [
        "Annual Road-Section Exposure Notes",
        "==================================",
        f"Input directory: {args.input_dir}",
        f"Workbooks parsed: {len(files)}",
        f"Rows parsed: {len(exposure):,}",
        f"Unique road sections: {exposure['road_section'].nunique():,}",
        f"Output: {args.output}",
        "",
        "Method:",
        "The parser reads the weighted road-number-order sheet from each annual Vegagerdin workbook.",
        "It extracts Vegnr, Kaflanr, road names, section endpoints, section length, ADU, SDU, VDU,",
        "and thousand vehicle-kilometres. The road-section key is normalised as Vegnr-Kaflanr,",
        "matching the registered_road_section field supplied with the accident road-link data.",
        "SDU covers June-September. VDU covers December-March.",
        "",
        "Yearly exposure coverage:",
        yearly.to_string(index=False),
    ]
    args.notes.write_text("\n".join(notes) + "\n", encoding="utf-8")
    print("\n".join(notes))


if __name__ == "__main__":
    main()
