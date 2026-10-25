# Extract a continued six-column PDF table

The table in [this pdfplumber question](https://github.com/jsvine/pdfplumber/discussions/1365) continues onto a second page without a top horizontal border. Default extraction finds only the two rightmost columns there and loses the first row. Joining the resulting strings cannot restore those missing cells.

This example adds the missing boundary through pdfplumber's documented `explicit_horizontal_lines` setting, keeps the existing ruled lines, and reads both pages separately. It exports one header and all 20 data rows in six columns. Values repeat only within actual vertically merged cell rectangles; physically separate blank cells stay blank. The continuation's model is read from that page.

## Run

Use Python 3.10 or later. Save the question's original `test1.pdf` attachment locally; it is not bundled here. From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest -v
.venv/bin/python extract_table.py /path/to/test1.pdf --output table.csv
.venv/bin/python extract_table.py /path/to/test1.pdf --format json --output table.json
```

Replace `/path/to/test1.pdf` with your actual input path. Output files must not already exist. Omit `--output` to write to stdout. The input is opened for reading only. Validation finishes before any output file is created.

CSV has one six-field header and 20 six-field data records. JSON contains `header`, `rows`, and `source_pages`, with a one-based PDF page number for each data row: 16 records from page 1, followed by four from page 2. Page numbers here mean PDF page positions, rather than printed page labels.

## Why this works

On page 2, the seven vertical borders start 72 points below the page top. Their x coordinates match page 1's six-column grid. The internal horizontal separators cover only the last two columns. Without a top border, the first four merged rectangles and the first right-hand row are not enclosed.

The native configuration is:

```python
settings = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "explicit_horizontal_lines": [72],
}
tables = pdf.pages[1].find_tables(table_settings=settings)
native_rows = tables[0].extract()
```

Apply that added line only to the continuation page. `72` is a coordinate measured down from the top, not a distance carried forward from the previous page. See the official [table methods and settings](https://github.com/jsvine/pdfplumber#extracting-tables).

Native extraction returns text at each physical cell's starting row, with `None` for positions inside a vertical merge. The example maps that text to its cell rectangle and expands each rectangle over the row intervals it actually covers. It does not forward-fill empty strings or copy values across the page break.

## Scope and checks

This is an explicit recipe for the supplied two-page ruled table, not an arbitrary-PDF detector. It expects exactly one table on each page, six matching column boundaries, a six-cell header on page 1, and 16 then four data rows. It rejects missing pages, unexpected row counts, extra detected tables, incompatible grids, horizontal merges, overlapping or uncovered cells, and missing models. An unrelated table with identical geometry and row counts still requires source review; geometry cannot establish its meaning.

For a different document, inspect its layout first and set `--rows-per-page 16,4` and `--continuation-top 72` to its verified values. Both pages must still satisfy the stated assumptions. The code does not infer missing content, perform OCR, or validate the technical meaning of document values.

Normalization removes Unicode whitespace, including line wraps inside Chinese words. All other characters remain unchanged, including `~`, punctuation, parentheses and Chinese text. This suits the supplied table; it is unsuitable when spaces themselves carry meaning.

Verification used pdfplumber 0.11.10 on the unchanged original attachment. All 120 data fields, six headers, ordering and JSON page provenance were compared with a separate transcription from rendered pages. Scripted tests create a separate small PDF transiently and check the missing top boundary, vertical merges, physical blanks, a new continuation model, layout rejection, CSV/JSON and existing-file preservation.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
