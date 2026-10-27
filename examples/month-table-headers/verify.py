#!/usr/bin/env python3
"""Check actual workbook contents, not the source code used to generate them."""
from pathlib import Path
from xml.etree import ElementTree as ET
import hashlib
import math
import re
import subprocess
import sys
import tempfile
import zipfile

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
HEADERS = ["All we want is cake!", "Jan 2023", "Feb 2023", "Mar 2023"]


def workbook(path, first_jan, average):
    with zipfile.ZipFile(path) as z:
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        table_names = [n for n in z.namelist() if n.startswith("xl/tables/") and n.endswith(".xml")]
        assert len(table_names) == 1, table_names
        table = ET.fromstring(z.read(table_names[0]))
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            strings = ["".join(si.itertext()) for si in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        cells = {c.attrib["r"]: c for c in sheet.findall(".//s:sheetData/s:row/s:c", NS)}

        def text(address):
            c = cells[address]
            if c.get("t") == "s":
                return strings[int(c.findtext("s:v", namespaces=NS))]
            if c.get("t") == "inlineStr":
                return "".join(c.find("s:is", NS).itertext())
            return c.findtext("s:v", namespaces=NS)

        got = [text(a) for a in ["A1", "B1", "C1", "D1"]]
        assert got == HEADERS, f"month header labels: {got!r} != {HEADERS!r}"
        columns = table.findall("s:tableColumns/s:tableColumn", NS)
        assert [c.get("name") for c in columns] == HEADERS, "field metadata differs from header cells"
        assert table.get("name") == "TableWithData"
        assert table.get("ref") == "A1:D5", table.attrib
        assert table.get("totalsRowCount") == "1", "average totals row missing"
        assert table.find("s:autoFilter", NS).get("ref") == "A1:D4"
        expected = {
            "A2": "Cake", "B2": first_jan, "C2": 0, "D2": 0,
            "A3": "Cheesecake", "B3": 14, "C3": 13, "D3": 0,
            "A4": "Waffles", "B4": 17, "C4": 0, "D4": 0,
            "A5": "Ø",
        }
        for address, value in expected.items():
            actual = text(address)
            assert actual == value if isinstance(value, str) else float(actual) == value, (address, actual, value)
        for column, header, total in zip("BCD", HEADERS[1:], [average, 13 / 3, 0]):
            cell = cells[column + "5"]
            formula = cell.findtext("s:f", namespaces=NS)
            assert formula == f"SUBTOTAL(101,TableWithData[{header}])", (column, formula)
            assert columns["ABCD".index(column)].get("totalsRowFunction") == "average"
            assert math.isclose(float(text(column + "5")), total, rel_tol=1e-12, abs_tol=1e-12)
        assert all(cells[a].get("t") in ("s", "inlineStr") for a in ["A1", "B1", "C1", "D1"])
    print(f"PASS {path.name}: native table, text month labels, original rows, average totals and cached values")


def main():
    dotnet = sys.argv[1] if len(sys.argv) > 1 else "dotnet"
    with tempfile.TemporaryDirectory(prefix="month headers ") as folder:
        out = Path(folder)
        run = subprocess.run([dotnet, "run", "--project", str(Path(__file__).parent / "MonthHeaders.csproj"), "--", str(out)], check=True, text=True, capture_output=True)
        print(run.stdout, end="")
        original = out / "monthly-sales.xlsx"
        first_hash = hashlib.sha256(original.read_bytes()).hexdigest()
        reported = re.search(r"Original SHA256: ([0-9A-F]{64})", run.stdout)
        assert reported and reported[1].lower() == first_hash, "pre-roundtrip hash differs from original output"
        workbook(original, 7, 38 / 3)
        workbook(out / "monthly-sales-updated.xlsx", 10, 41 / 3)
        assert hashlib.sha256(original.read_bytes()).hexdigest() == first_hash
        print("PASS distinct roundtrip output preserves the original file")
        assembly = Path(__file__).parent / "bin/Debug/net10.0/MonthHeaders.dll"
        for existing in ("monthly-sales.xlsx", "monthly-sales-updated.xlsx"):
            target = out / ("existing-" + existing)
            target.mkdir()
            (target / existing).write_bytes(b"existing workbook contents")
            (target / "keep.txt").write_bytes(b"unrelated content")
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            attempt = subprocess.run([dotnet, str(assembly), str(target)], text=True, capture_output=True)
            assert attempt.returncode != 0, f"existing {existing} was not rejected"
            assert {p.name: p.read_bytes() for p in target.iterdir()} == before, "existing output content changed"
        before = {p.name: p.read_bytes() for p in out.glob("*.xlsx") if p.is_file()}
        repeat = subprocess.run([dotnet, str(assembly), str(out)], text=True, capture_output=True)
        assert repeat.returncode != 0, "repeat output was not rejected"
        assert {p.name: p.read_bytes() for p in out.glob("*.xlsx") if p.is_file()} == before
        print("PASS either existing output name and repeat run are rejected without changing content")


if __name__ == "__main__":
    main()
