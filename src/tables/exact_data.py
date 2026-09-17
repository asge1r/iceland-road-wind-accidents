"""Typeset the first two cleaned records with all fields in stored order.

CSV strings are unchanged. Parquet floats use shortest decimal representations
that round-trip to the original NumPy/Arrow dtype, verified bit for bit.
"""
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ACCIDENTS = Path('data/processed/accidents/all.csv')
WEATHER = Path('data/processed/weather/weather.parquet')
OUTPUT = Path('reports/thesis/generated/exact_data.tex')
AUDIT = Path('reports/working/tables/exact_data_excerpts.json')


def csv_excerpt(path):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        reader = csv.reader(stream)
        headers = next(reader)
        rows = [next(reader), next(reader)]
    if any(len(row) != len(headers) for row in rows):
        raise ValueError('Inconsistent CSV column counts')
    return headers, rows


def shortest_float(value):
    """Format a NumPy scalar at its stored precision, never via Python float."""
    if not isinstance(value, np.floating):
        raise TypeError('Float rendering requires an original-dtype NumPy scalar')
    if not np.isfinite(value):
        return str(value)
    candidates = [np.format_float_positional(value, unique=True, trim='-'),
                  np.format_float_scientific(value, unique=True, trim='-', exp_digits=1)]
    rendered = min(candidates, key=len)
    if value.dtype.type(rendered).tobytes() != value.tobytes():
        raise ValueError('Rendered float does not round-trip to its stored bits')
    return rendered


def parquet_value(value):
    if isinstance(value, np.floating):
        return shortest_float(value)
    if isinstance(value, np.datetime64):
        # Seconds suffice when the stored value is exactly on a second;
        # otherwise retain the necessary fractional timestamp digits.
        if value == value.astype('datetime64[s]'):
            return np.datetime_as_string(value, unit='s')
        return np.datetime_as_string(value, unit='auto')
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return 'null'
    return str(value)


def parquet_excerpt(path):
    source = pq.ParquetFile(path)
    batch = next(source.iter_batches(batch_size=2))
    columns = []
    for column, field in zip(batch.columns, batch.schema, strict=True):
        if pa.types.is_floating(field.type) or pa.types.is_timestamp(field.type):
            # Arrow -> NumPy preserves float32 instead of to_pylist's float64.
            values = column.to_numpy(zero_copy_only=False)
            columns.append([parquet_value(v) if column[i].is_valid else 'null'
                            for i,v in enumerate(values)])
        else:
            columns.append([parquet_value(v) for v in column.to_pylist()])
    return batch.schema.names, [list(row) for row in zip(*columns, strict=True)]


def escape(value):
    special = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
               '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
               '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(special.get(c, c) for c in value)


def header_cell(value):
    """Preserve complete headers; portrait blocks leave room for long names."""
    return r'\texttt{'+escape(value)+'}'


def render_table(headers, rows, caption, short_caption, label, note='', blocks=None):
    blocks = blocks or [(0, len(headers))]
    result = [r'\begin{table}[H]', r'\centering',
              r'\captionsetup{width=\linewidth}',
              r'\caption['+short_caption+']{'+caption+'}', r'\label{'+label+'}',
              r'\fontsize{11}{14}\selectfont\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.2}']
    for number, (start, end) in enumerate(blocks):
        if number:
            result.append(r'\par\medskip{\small\itshape Same records, remaining columns.}\par\smallskip')
        result.extend([r'\begin{tabular}{' + 'l'*(end-start) + '}', r'\toprule',
                       ' & '.join(header_cell(v) for v in headers[start:end])+r' \\', r'\midrule'])
        result.extend(' & '.join(r'\texttt{'+escape(v)+'}' for v in row[start:end])+r' \\' for row in rows)
        result.extend([r'\bottomrule', r'\end{tabular}'])
    if note:
        result.extend([r'\par\smallskip\begin{minipage}{\linewidth}\small',
                       r'\textit{Note:} '+note, r'\end{minipage}'])
    result.append(r'\end{table}')
    return '\n'.join(result)


def generate(accidents=ACCIDENTS, weather=WEATHER, output=OUTPUT, audit=AUDIT):
    a = csv_excerpt(accidents)
    w = parquet_excerpt(weather)
    schema = pq.ParquetFile(weather).schema_arrow
    content = '% Generated directly from cleaned files by src.tables.exact_data.\n'
    content += render_table(*a,
        'First two stored records from the cleaned accident dataset.',
        'First two stored records from the cleaned accident dataset.', 'tab:exact-accidents',
        'All columns are shown in source order across the two blocks; CSV values are reproduced without relabelling or rounding.',
        blocks=[(0,5),(5,len(a[0]))])
    content += '\n' + render_table(*w,
        'First two stored records from the cleaned weather dataset.',
        'First two stored records from the cleaned weather dataset.', 'tab:exact-weather',
        'Floating-point values use the shortest decimal representation that round-trips to the stored Parquet dtype.')
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(content)
    Path(audit).parent.mkdir(parents=True, exist_ok=True)
    Path(audit).write_text(json.dumps({
        'accidents': {'source':str(accidents), 'headers':a[0], 'rows':a[1], 'blocks':[[0,5],[5,len(a[0])]]},
        'weather': {'source':str(weather), 'headers':w[0], 'rows':w[1], 'blocks':[[0,len(w[0])]],
                    'schema':{field.name:str(field.type) for field in schema},
                    'float_format':'NumPy unique shortest decimal at original dtype; bitwise round-trip checked'},
    }, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    generate()
