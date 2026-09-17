"""Audit supplied register extracts without changing any analytical products."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path('data/raw/accidents')
OUTPUT = Path('reports/working/deadline_review_20260917/register_sources.json')


def main():
    summary = {}
    frames = {}
    for period in ('2007_2024', '2025'):
        events = pd.read_csv(ROOT / f'accidents_{period}.txt', sep='\t')
        events.columns = events.columns.str.strip()
        ids = 'nid' if period == '2007_2024' else 'NID'
        years = pd.to_datetime(events['Dagsetning'], format='%d.%m.%Y').dt.year
        event_year = pd.Series(years.to_numpy(), index=events[ids])
        assert event_year.index.is_unique
        for kind in ('injuries', 'vehicles'):
            name = f'{kind}_{period}'
            path = ROOT / f'{name}.txt'
            data = pd.read_csv(path, sep='\t')
            data.columns = data.columns.str.strip()
            frames[name] = data
            matched_year = data[ids].map(event_year)
            if kind == 'injuries':
                assert matched_year.notna().all(), f'{name}: unmatched accident IDs'
            summary[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                rows=len(data), unique_accident_ids=int(data[ids].nunique()),
                year_min=int(matched_year.min()), year_max=int(matched_year.max()),
                columns=data.columns.tolist(), null_counts=data.isna().sum().to_dict(),
                rows_without_accident=int(matched_year.isna().sum()),
                ids_without_accident=int(data.loc[matched_year.isna(),ids].nunique()))
            if kind == 'injuries':
                severity = 'meidsli' if period == '2007_2024' else 'Meiðsli'
                summary[name]['injury_codes'] = {int(k): int(v) for k,v in data[severity].value_counts().items()}
        injury_ids = set(frames[f'injuries_{period}'][ids])
        vehicle_ids = set(frames[f'vehicles_{period}'][ids])
        summary[f'injury_ids_without_vehicle_{period}'] = len(injury_ids-vehicle_ids)
        assert injury_ids <= vehicle_ids
    person = summary['injuries_2007_2024']; vehicle = summary['vehicles_2007_2024']
    assert (person['rows'],person['unique_accident_ids']) == (23131,16143)
    assert person['injury_codes'] == {3:19557,2:3361,1:213}
    assert (vehicle['rows'],vehicle['unique_accident_ids']) == (215982,118249)
    for kind in ('injuries','vehicles'):
        assert (summary[f'{kind}_2007_2024']['year_min'],summary[f'{kind}_2007_2024']['year_max']) == (2007,2024)
        assert summary[f'{kind}_2025']['year_min'] == summary[f'{kind}_2025']['year_max'] == 2025
    book = ROOT/'accident_codebook.xls'
    xls = pd.ExcelFile(book)
    summary['dictionary'] = dict(path=str(book),sha256=hashlib.sha256(book.read_bytes()).hexdigest(),
        sheets=xls.sheet_names, verified_title=xls.sheet_names[0], publication_date=None,
        citation_decision='Describe as accompanying table descriptions; no institutional publication/version date verified.',
        scope='Database schema and code definitions, not a statement of delivered field completeness.')
    summary['coverage_note'] = 'Named extracts end in 2024. Separate 2025 person/vehicle deliveries also exist; harmonisation and coding audits are needed before subgroup use. Three rows (two IDs) in the older vehicle extract lack matching accident records, so their dates cannot be independently confirmed.'
    summary['field_note'] = 'Delivered fields include person age, sex, position, class and injury, and vehicle ID/class. Police weather, road-surface, recorded cause, speed and tourism/nationality fields are not in these delivered extracts. Zero nulls do not establish valid or complete coding.'
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    print('Register source counts, injury codes, ID inclusion and temporal coverage verified; wrote',OUTPUT)


if __name__ == '__main__':
    main()
