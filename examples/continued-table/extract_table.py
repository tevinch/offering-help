"""A bounded recipe for a two-page, six-column continued ruled table."""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import sys

import pdfplumber


def _boundaries(values):
    # TableFinder already snaps nearby edges. Retain its geometry unchanged.
    return sorted(set(values))


def _expand_cells(table):
    """Repeat text only inside its real rectangle, never into a later cell."""
    xs = _boundaries(v for cell in table.cells for v in (cell[0], cell[2]))
    ys = _boundaries(v for cell in table.cells for v in (cell[1], cell[3]))
    if len(xs) != 7:
        raise ValueError('Expected exactly six physical columns')
    values = {}
    native = table.extract(x_tolerance=3, y_tolerance=3)
    if len(native) != len(table.rows):
        raise ValueError('Inconsistent native extraction')
    for row, texts in zip(table.rows, native):
        if len(texts) != len(row.cells):
            raise ValueError('Inconsistent native row')
        for cell, text in zip(row.cells, texts):
            if cell is not None:
                # This source wraps Chinese words across physical lines. Remove
                # whitespace only; retain every non-whitespace code point.
                values[cell] = ''.join((text or '').split())
    if set(values) != set(table.cells):
        raise ValueError('A physical cell has no native extraction result')
    rows = []
    for top, bottom in zip(ys, ys[1:]):
        row = []
        for left, right in zip(xs, xs[1:]):
            covering = [cell for cell in table.cells
                        if cell[0] == left and cell[2] == right
                        and cell[1] <= top and cell[3] >= bottom]
            if len(covering) != 1:
                raise ValueError('Missing, overlapping, or horizontally merged cell')
            row.append(values[covering[0]])
        rows.append(row)
    return xs, rows


def extract_continued_table(path, *, expected_data_rows=(16, 4), continuation_top=72):
    """Return one header, ordered rows and one-based source page per row.

    Assumes exactly two pages, one ruled table per page, a first-page header,
    six unchanged column boundaries, and a known missing continuation top edge.
    Row counts and the continuation coordinate are explicit source assertions.
    """
    if (len(expected_data_rows) != 2 or any(n <= 0 for n in expected_data_rows)
            or not math.isfinite(continuation_top) or continuation_top < 0):
        raise ValueError('Supply two positive data row counts and a finite top coordinate')
    result = {'header': [], 'rows': [], 'source_pages': []}
    first_grid = None
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != 2:
            raise ValueError('Expected the complete two-page document')
        for index, page in enumerate(pdf.pages):
            settings = {'vertical_strategy': 'lines', 'horizontal_strategy': 'lines'}
            if index == 1:
                if continuation_top >= page.height:
                    raise ValueError('Continuation top is outside the page')
                # Numeric coordinates are measured down from the page top.
                # Keep ordinary horizontal lines and add only the missing edge.
                settings['explicit_horizontal_lines'] = [continuation_top]
            tables = page.find_tables(table_settings=settings)
            if len(tables) != 1:
                raise ValueError(f'Page {index+1}: expected exactly one table')
            table = tables[0]
            xs, rows = _expand_cells(table)
            if index == 0:
                first_grid = xs
                result['header'] = rows.pop(0)
                if not all(result['header']) or len(set(result['header'])) != 6:
                    raise ValueError('First page must contain six distinct nonempty headers')
            elif (any(abs(a-b) > 1 for a, b in zip(first_grid, xs))
                  or abs(table.bbox[1]-continuation_top) > 1):
                raise ValueError('Continuation does not match the first-page grid/top')
            if len(rows) != expected_data_rows[index]:
                raise ValueError(f'Page {index+1}: expected {expected_data_rows[index]} data rows, got {len(rows)}')
            if any(not row[0] or row == result['header'] for row in rows):
                raise ValueError('Missing model or unexpected repeated header')
            result['rows'].extend(rows)
            result['source_pages'].extend([index+1]*len(rows))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--format', choices=('csv', 'json'), default='csv')
    parser.add_argument('--output', type=Path, help='New file only; default is stdout')
    parser.add_argument('--rows-per-page', default='16,4', help='Expected DATA rows, default: 16,4')
    parser.add_argument('--continuation-top', type=float, default=72, help='Points below page top, default: 72')
    args = parser.parse_args(argv)
    try:
        counts = tuple(int(value) for value in args.rows_per_page.split(','))
        data = extract_continued_table(args.input, expected_data_rows=counts,
                                       continuation_top=args.continuation_top)
        if args.format == 'json':
            text = json.dumps(data, ensure_ascii=False, indent=2)+'\n'
        else:
            buffer = io.StringIO(newline='')
            writer = csv.writer(buffer, lineterminator='\n')
            writer.writerows([data['header'], *data['rows']])
            text = buffer.getvalue()
        # Validate everything before opening an output. Exclusive creation also
        # protects the source when its path is accidentally supplied as output.
        if args.output:
            with args.output.open('x', encoding='utf-8', newline='') as stream:
                stream.write(text)
        else:
            sys.stdout.write(text)
    except (ValueError, OSError) as error:
        parser.exit(2, f'error: {error}\n')


if __name__ == '__main__':
    main()
