"""Exercise the complete CLI against temporary SQLite and CSV files."""
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
DOTNET = os.environ.get("DOTNET", "dotnet")
DLL = ROOT / "bin/Release/net10.0/CsvRuntimeMap.dll"
HEADER = ["EventID", "Period", "MeanLoss", "DayInPeriod", "RegionalPeril", "CatalogueTypeCode"]
ROW = ["EV-001", "2026", "12.50", "4", "North, coast", "TYPE-A"]
EXPECTED = [
    {"EventId": "EV-001", "Period": "2026", "MeanLossAmount": 12.5,
     "DayInPeriod": "4", "PerilZone": "North, coast", "CatalogueTypeCode": "TYPE-A"},
    {"EventId": "EV-002", "Period": "2027", "MeanLossAmount": 0,
     "DayInPeriod": "", "PerilZone": "南", "CatalogueTypeCode": "TYPE-B"},
]


def build():
    subprocess.run([DOTNET, "restore", "--locked-mode"], cwd=ROOT, check=True)
    subprocess.run([DOTNET, "build", "-c", "Release", "--no-restore"], cwd=ROOT, check=True)


def main():
    build()
    results = []
    binary_before = hashlib.sha256(DLL.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="csv-alias-check-") as work:
        folder = Path(work)
        db = folder / "aliases.db"

        def reset_db(sql=None, parameters=()):
            if db.exists():
                db.unlink()
            with sqlite3.connect(db) as con:
                con.executescript((ROOT / "fixtures/aliases.sql").read_text())
                assert con.execute("SELECT count(*) FROM CsvColumnMappings").fetchone()[0] == 18
                if sql:
                    con.execute(sql, parameters)

        def csv_file(header=HEADER, rows=None, raw=None):
            path = folder / "input.csv"
            if raw is not None:
                path.write_text(raw, encoding="utf-8")
            else:
                with path.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(header)
                    writer.writerows([ROW] if rows is None else rows)
            return path

        def run(name, source, expected=None, error=None, database=None):
            proc = subprocess.run([DOTNET, str(DLL), str(database or db), str(source)],
                                  text=True, capture_output=True, timeout=30)
            if error:
                assert proc.returncode != 0, f"{name}: accepted invalid input"
                assert proc.stdout == "", f"{name}: emitted a partial result"
                assert error in proc.stderr, f"{name}: wrong error: {proc.stderr}"
                results.append({"name": name, "status": "passed", "error": error})
            else:
                assert proc.returncode == 0, f"{name}: {proc.stderr}"
                assert proc.stderr == "", f"{name}: unexpected stderr: {proc.stderr}"
                actual = json.loads(proc.stdout)
                assert actual == expected, f"{name}: {actual!r} != {expected!r}"
                results.append({"name": name, "status": "passed", "records": actual})

        # Break caught: stale hard-coded aliases or a partial six-field map.
        reset_db()
        run("original18 metadata rows import all6 members", ROOT / "fixtures/original.csv", EXPECTED)
        run("new alias fails before metadata update", ROOT / "fixtures/new-alias.csv", error="HeaderValidationException")
        with sqlite3.connect(db) as con:
            con.execute("INSERT INTO CsvColumnMappings VALUES (?, ?, ?)",
                        ("EventNumber", "EventId", "String"))
            assert con.execute("SELECT count(*) FROM CsvColumnMappings").fetchone()[0] == 19
        run("same binary imports after DB-only change", ROOT / "fixtures/new-alias.csv", EXPECTED)

        # Break caught: ordinal mapping, altered string contents, ignored metadata aliases.
        for alias_header in [
            ["Event", "PeriodId", "Perspvalue", "DayInPeriod", "PerilZone", "CatalogueType"],
            ["Eve", "Year", "Loss", "DayInPeriod", "Region", "Catalogue"],
            ["EveId", "Period", "MeanLoss", "DayInPeriod", "RegionalPeril", "TypeCode"],
        ]:
            run("alternate names: " + alias_header[0], csv_file(alias_header), EXPECTED[:1])
        run("reordered headers", csv_file(HEADER[::-1], [ROW[::-1]]), EXPECTED[:1])
        content_row = ["ÉV-\"3\"", "", "-1234.75", "", "west, \"bay\"\nshore", "南"]
        run("quoted content Unicode and empty strings", csv_file(rows=[content_row]),
            [{"EventId": 'ÉV-"3"', "Period": "", "MeanLossAmount": -1234.75,
              "DayInPeriod": "", "PerilZone": 'west, "bay"\nshore', "CatalogueTypeCode": "南"}])
        run("header-only input", csv_file(rows=[]), [])
        run("unmapped extra column", csv_file(HEADER + ["Note"], [ROW + ["keep local"]]), EXPECTED[:1])

        # Break caught: disabling CsvHelper validation, swallowing conversion errors,
        # or writing earlier records before a later record fails.
        run("missing required header", csv_file(HEADER[:-1], [ROW[:-1]]), error="HeaderValidationException")
        run("missing required field", csv_file(rows=[ROW[:-1]]), error="MissingFieldException")
        for value in ["", "not-a-decimal", "79228162514264337593543950336"]:
            invalid = ROW.copy()
            invalid[2] = value
            run("invalid decimal: " + repr(value), csv_file(rows=[ROW, invalid]), error="TypeConverterException")
        run("malformed quotes", csv_file(raw=','.join(HEADER) + '\nEV-1,2026,12,4,North,bad"value\n'),
            error="BadDataException")
        run("empty file", csv_file(raw=""), error="InvalidDataException")
        run("same header twice", csv_file(HEADER + ["EventID"], [ROW + ["EV-OTHER"]]), error="InvalidDataException")
        run("two aliases for same property", csv_file(HEADER + ["Event"], [ROW + ["EV-OTHER"]]), error="InvalidDataException")

        # Break caught: treating DB metadata as unchecked instructions or silently
        # using a default property/type after a bad configuration edit.
        invalid_metadata = [
            ("SQL NULL alias", "UPDATE CsvColumnMappings SET CsvColumnName = NULL WHERE CsvColumnName = 'EventID'", ()),
            ("SQL NULL property", "UPDATE CsvColumnMappings SET PropertyName = NULL WHERE CsvColumnName = 'EventID'", ()),
            ("SQL NULL type", "UPDATE CsvColumnMappings SET DataType = NULL WHERE CsvColumnName = 'EventID'", ()),
            ("empty alias", "UPDATE CsvColumnMappings SET CsvColumnName = '' WHERE CsvColumnName = 'EventID'", ()),
            ("blank alias", "UPDATE CsvColumnMappings SET CsvColumnName = '   ' WHERE CsvColumnName = 'EventID'", ()),
            ("unknown property", "INSERT INTO CsvColumnMappings VALUES ('Other', 'Unexpected', 'String')", ()),
            ("unknown datatype", "UPDATE CsvColumnMappings SET DataType = 'Number' WHERE PropertyName = 'MeanLossAmount'", ()),
            ("wrong known datatype", "UPDATE CsvColumnMappings SET DataType = 'String' WHERE PropertyName = 'MeanLossAmount'", ()),
            ("alias belongs to two properties", "INSERT INTO CsvColumnMappings VALUES ('EventID', 'Period', 'String')", ()),
            ("required property absent", "DELETE FROM CsvColumnMappings WHERE PropertyName = 'DayInPeriod'", ()),
        ]
        for name, sql, parameters in invalid_metadata:
            reset_db(sql, parameters)
            run(name, ROOT / "fixtures/original.csv", error="InvalidDataException")
        reset_db()
        missing = folder / "does-not-exist.db"
        run("missing DB is not created", ROOT / "fixtures/original.csv", error="SqliteException", database=missing)
        assert not missing.exists()
        run("DB remains usable after failures", ROOT / "fixtures/original.csv", EXPECTED)
        with sqlite3.connect(db) as con:
            assert con.execute("SELECT count(*) FROM CsvColumnMappings").fetchone()[0] == 18
    binary_after = hashlib.sha256(DLL.read_bytes()).hexdigest()
    assert binary_before == binary_after, "validation rebuilt or changed the executable"
    print(json.dumps({"status": "passed", "checks": len(results), "binarySha256": binary_after,
                      "unchangedBinary": True, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
