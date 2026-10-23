"""Check the complete file-to-JSON operation and the original filter baseline."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
DOTNET = os.environ.get("DOTNET", "dotnet")


def run(*args):
    return subprocess.run([DOTNET, *args], cwd=ROOT, text=True, capture_output=True)


restore = run("restore", "validation/Validation.csproj", "--locked-mode", "--verbosity", "quiet")
assert restore.returncode == 0, restore.stdout + restore.stderr
build = run("build", "validation/Validation.csproj", "--no-restore", "--nologo", "--verbosity", "quiet")
assert build.returncode == 0, build.stdout + build.stderr
check = run("validation/bin/Debug/net10.0/Validation.dll", "inventory.csv")
assert check.returncode == 0, check.stdout + check.stderr
print(check.stdout, end="")

application = "bin/Debug/net10.0/Inventory.dll"
actual = run(application, "inventory.csv")
assert actual.returncode == 0, actual.stderr
item = {
    "ProductCode": "1231234123123-123123123",
    "Brand": "Item Wheel Components",
    "Description": "28 CHROME MOD *NO RIVETS 1x4 5x114.3 CHROME  ",
    "Stock": "0",
    "StockOther": "0",
}
assert json.loads(actual.stdout) == [item, item], actual.stdout

header = "ProductCode,Brand,Description,Stock,StockOther\n"
with tempfile.TemporaryDirectory() as directory:
    bad_file = Path(directory) / "short-row.csv"
    bad_file.write_text(header + "P,B,D,0,0\nP,B,D,0\n", encoding="utf-8")
    rejected = run(application, str(bad_file))
    assert rejected.returncode == 1, rejected.stdout + rejected.stderr
    assert not rejected.stdout.strip(), "Do not emit partial inventory JSON on a later row error"
    assert "MissingFieldException" in rejected.stderr, rejected.stderr

    absent = run(application, str(Path(directory) / "absent.csv"))
    assert absent.returncode == 1 and not absent.stdout.strip(), absent.stdout + absent.stderr

assert run(application).returncode == 2
print("PASS: file-to-JSON output, no partial result on row errors, missing file, usage status")
