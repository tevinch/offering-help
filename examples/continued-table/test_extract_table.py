"""Own, transient PDF fixtures; no third-party document is distributed."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from extract_table import extract_continued_table


def fixture(path, *, shifted=False, extra=False, missing=False):
    """Write a tiny ASCII PDF with real vertical merges and real blank cells."""
    streams = []
    for page in range(2 if not missing else 1):
        xs = [80, 150, 240, 320, 400, 450, 520]
        if shifted and page == 1:
            xs[2] += 10
        top = 300 if page == 0 else 72
        ys = [top + i * 24 for i in range(6 if page == 0 else 5)]
        ops = []
        def line(x0, y0, x1, y1):
            ops.append(f'{x0} {842-y0} m {x1} {842-y1} l S')
        def text(x, y, value):
            ops.append(f'BT /F1 9 Tf {x} {842-y} Td ({value}) Tj ET')
        for x in xs:
            line(x, top, x, ys[-1])
        for i, y in enumerate(ys):
            if page == 1 and i == 0:
                continue  # The continuation really has no top horizontal edge.
            full = i in (0, len(ys)-1) or (page == 0 and i == 1)
            line(xs[0] if full else xs[4], y, xs[-1], y)
        if page == 0:
            for col, value in enumerate(['Model', 'Name', 'In', 'Out', 'Combined', 'Note']):
                text(xs[col]+3, top+15, value)
        start = top + (24 if page == 0 else 0)
        for col, value in enumerate(['M1' if page == 0 else 'M2', 'A~B', '-2', '0']):
            text(xs[col]+3, start+45, value)
        for row in range(4):
            text(xs[4]+3, start+row*24+15, str(row+1+page*4))
            # Physical blank after a populated cell must remain blank.
            if row != 1:
                text(xs[5]+3, start+row*24+15, f'N{row+1}')
        if extra and page == 1:
            for x in (50, 65, 80):
                line(x, 600, x, 640)
            for y in (600, 620, 640):
                line(50, y, 80, y)
        streams.append('\n'.join(ops).encode('ascii'))
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    page_ids = []
    for content in streams:
        page_id = len(objects)+1
        page_ids.append(page_id)
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_id+1} 0 R >>'.encode())
        objects.append(f'<< /Length {len(content)} >>\nstream\n'.encode()+content+b'\nendstream')
    objects[1] = f'<< /Type /Pages /Count {len(page_ids)} /Kids [{" ".join(f"{i} 0 R" for i in page_ids)}] >>'.encode()
    result = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    xref = len(result)
    result.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        result.extend(f'{offset:010d} 00000 n \n'.encode())
    result.extend(f'trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    path.write_bytes(result)


class ContinuedTableTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'source.pdf'
        fixture(self.path)

    def test_complete_native_extraction_preserves_merges_and_physical_blanks(self):
        # Fails if page 2 is omitted, old model carried over, or blanks filled.
        result = extract_continued_table(self.path, expected_data_rows=(4, 4))
        self.assertEqual(result['header'], ['Model', 'Name', 'In', 'Out', 'Combined', 'Note'])
        self.assertEqual(result['rows'], [
            ['M1','A~B','-2','0','1','N1'], ['M1','A~B','-2','0','2',''],
            ['M1','A~B','-2','0','3','N3'], ['M1','A~B','-2','0','4','N4'],
            ['M2','A~B','-2','0','5','N1'], ['M2','A~B','-2','0','6',''],
            ['M2','A~B','-2','0','7','N3'], ['M2','A~B','-2','0','8','N4']])
        self.assertEqual(result['source_pages'], [1,1,1,1,2,2,2,2])

    def test_refuses_incompatible_grid_extra_table_missing_page_and_wrong_row_count(self):
        for options in ({'shifted': True}, {'extra': True}, {'missing': True}):
            with self.subTest(options=options):
                fixture(self.path, **options)
                with self.assertRaises(ValueError):
                    extract_continued_table(self.path, expected_data_rows=(4,4))
        fixture(self.path)
        with self.assertRaises(ValueError):
            extract_continued_table(self.path)  # Original-document row counts.

    def test_cli_decoded_csv_json_and_no_overwrite(self):
        # Fails on malformed output, duplicate header, source change or clobber.
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        command = [sys.executable, str(Path(__file__).with_name('extract_table.py')),
                   str(self.path), '--rows-per-page', '4,4']
        csv_run = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(csv_run.returncode, 0, csv_run.stderr)
        rows = list(csv.reader(csv_run.stdout.splitlines()))
        self.assertEqual(len(rows), 9)
        self.assertEqual(rows[-1], ['M2','A~B','-2','0','8','N4'])
        output = Path(self.tmp.name)/'table.json'
        run = subprocess.run(command+['--format','json','--output',str(output)], text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(output.read_text())
        self.assertEqual(data['rows'], rows[1:])
        self.assertEqual(data['source_pages'], [1]*4+[2]*4)
        unchanged = output.read_bytes()
        refused = subprocess.run(command+['--output',str(output)], text=True, capture_output=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(output.read_bytes(), unchanged)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)


if __name__ == '__main__':
    unittest.main()
