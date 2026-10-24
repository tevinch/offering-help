"""Build and check the real CLI against independent expected records."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
DOTNET = os.environ.get("DOTNET", "dotnet")
subprocess.run([DOTNET, "restore", "--locked-mode"], cwd=ROOT, check=True)
subprocess.run([DOTNET, "build", "-c", "Release", "--no-restore"], cwd=ROOT, check=True)
DLL = ROOT / "bin/Release/net10.0/TempProjection.dll"

def run(*args):
    return subprocess.run([DOTNET, str(DLL), *args], cwd=ROOT, capture_output=True, text=True)

def expected_rows(count):
    from datetime import datetime, timedelta
    rows = []
    for i in range(count):
        alternate = i % 2 == 1
        rows.append({
            "CreateTime": (datetime(2026, 10, 1) + timedelta(days=i)).isoformat(),
            "ScheduleId": f"s-{i:02}", "ProcId": "proc-alt" if alternate else "proc-1",
            "CaseId": "case-1", "ProgressMonth": "2026年10月",
            "ProgressValue": 0 if alternate else i,
            "ScheduleDetail": f"detail {i}", "ContributionRatio": None if alternate else 0.75,
            "Volume": "V-1", "CaseName": "文档", "UndertakeDepartment": "D-1",
            "ProcName": "CTRL-alt" if alternate else "CTRL",
            "ProcStatus": "" if alternate else "ready", "Undertaker": "user-1",
            "ProgressCostDays": i + 0.5, "EstimatedRiskFee": 12.5,
        })
    return rows

checks = 0
for count, sizes in [(0, []), (1, [1]), (23, [10, 10, 3])]:
    result = run("--count", str(count))
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    data = json.loads(result.stdout)
    expected = expected_rows(count)
    assert data["ListRows"] == expected, data["ListRows"]
    assert data["Chunks"] == [expected[i:i+10] for i in range(0, count, 10)], data["Chunks"]
    assert [len(b) for b in data["Chunks"]] == sizes
    assert data["SourceBefore"] == data["SourceAfter"]
    assert len(data["SourceAfter"]) == count + 3
    assert len(data["ExecutedSql"]) == 2, data["ExecutedSql"]
    for sql in data["ExecutedSql"]:
        assert 'FROM (' in sql and 'case_proc_schedule' in sql
        outer = sql.rsplit(') a', 1)[-1]
        assert 'JOIN' not in outer, outer
    assert data["SqlServerGeneratedOnly"]
    assert 'WITH(NoLock)' in data["SqlServerSql"] or 'With(NoLock)' in data["SqlServerSql"]
    assert 'JOIN' not in data["SqlServerSql"].rsplit(') a', 1)[-1]
    assert 'a.[Id]' in data["SqlServerSql"]
    checks += 1
    print(f"PASS count={count}, chunks={sizes}, all 16 output fields, filters, SQL and unchanged source")

baseline = run("--count", "23", "--baseline")
assert baseline.returncode == 2 and not baseline.stdout.strip(), baseline
assert baseline.stderr.strip(), baseline.stderr
checks += 1
print("PASS unprojected-member baseline fails without partial JSON")

for args in [("--count", "-1"), ("--count", "no"), ("--unknown",)]:
    result = run(*args)
    assert result.returncode == 2 and not result.stdout.strip() and result.stderr.strip(), args
    checks += 1
print(f"PASS {checks} end-to-end checks")
