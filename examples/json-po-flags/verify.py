"""End-to-end JSON→PO→native Weblate checks→msgmerge→JSON validation."""
from __future__ import annotations

from copy import deepcopy
import json
from importlib.metadata import version
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from translate.storage.pypo import pofile

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
MSGMERGE = os.environ.get("MSGMERGE", "msgmerge")
assert version("weblate") == "2026.10.1"
assert version("translate-toolkit") == "3.20.0"


def command(*args, expected=0):
    result = subprocess.run([str(arg) for arg in args], capture_output=True, text=True)
    assert result.returncode == expected, result.stdout + result.stderr
    return result


def read_po(path):
    with path.open("rb") as source:
        return pofile(source)


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_native(report, bad=False):
    rows = {item["id"]: item for item in report["records"]}
    assert set(rows) == {"docs.guide", "legacy.items", "plain.example"}
    expected = {"docs.guide": "md-syntax", "legacy.items": "java_format", "plain.example": None}
    for key, active in expected.items():
        assert {check["id"] for check in rows[key]["checks"]} == {"md-syntax", "java_format"}
        assert len(rows[key]["checks"]) == 2
        for check in rows[key]["checks"]:
            assert check["executions"] == int(check["id"] == active), (key, check)
            assert check["failed"] == bool(bad and check["id"] == active), (key, check)
    return rows


with tempfile.TemporaryDirectory(prefix="catalog-roundtrip-") as directory:
    work = Path(directory)
    source = json.loads((ROOT / "messages.json").read_text())
    # Exercise removal of a source-owned flag as well as adding one later.
    source["docs.guide"]["weblateFlags"].append("ignore-md-reflink")
    source_path = work / "source.json"
    write_json(source_path, source)
    original_bytes = source_path.read_bytes()
    pot = work / "messages.pot"
    command(PYTHON, ROOT / "catalog.py", "extract", source_path, pot)
    translations = {
        "docs.guide": "Lesen Sie **dies**, bevor Sie fortfahren.",
        "legacy.items": "Artikel: {0}", "plain.example": "Ein Beispiel.",
    }
    target_map = work / "translations.json"
    write_json(target_map, translations)
    po = work / "de.po"
    result = command(PYTHON, ROOT / "native_checks.py", pot, "--translations", target_map, "--output", po)
    good = json.loads(result.stdout)
    assert good["resavedByWeblate"]
    original_po_bytes = po.read_bytes()
    rows = check_native(good)
    for key in source:
        assert rows[key]["source"] == source[key]["defaultMessage"]
        assert rows[key]["description"] == source[key]["description"]
        assert rows[key]["target"] == translations[key]
        for flag in source[key]["weblateFlags"]:
            assert flag in rows[key]["flags"], rows[key]
    compiled = work / "de.json"
    command(PYTHON, ROOT / "catalog.py", "compile", source_path, po, compiled)
    expected = deepcopy(source)
    for key, value in translations.items():
        expected[key]["defaultMessage"] = value
    assert json.loads(compiled.read_text()) == expected
    assert source_path.read_bytes() == original_bytes
    print("PASS JSON→POT→Weblate PoUnit.set_target/save→JSON preserves IDs, source, descriptions, flags, extra metadata and translations")

    bad_map = work / "bad.json"
    write_json(bad_map, {"docs.guide": "Lesen Sie dies, bevor Sie fortfahren.", "legacy.items": "Artikel: {1}"})
    bad_po = work / "bad.po"
    bad = json.loads(command(PYTHON, ROOT / "native_checks.py", po, "--translations", bad_map, "--output", bad_po).stdout)
    check_native(bad, bad=True)
    print("PASS real Markdown and Java MessageFormat checks execute and reject broken translations; unflagged plain text remains unchecked")

    no_flags = read_po(bad_po)
    for unit in no_flags.units:
        for flag in ["md-text", "java-format"]:
            unit.settypecomment(flag, False)
    no_flags_path = work / "no-flags.po"
    no_flags_path.write_bytes(bytes(no_flags))
    report = json.loads(command(PYTHON, ROOT / "native_checks.py", no_flags_path).stdout)
    try:
        check_native(report, bad=True)
    except AssertionError:
        pass
    else:
        raise AssertionError("Missing flags must fail the observed-check acceptance")
    print("PASS dropping PO flags is rejected by independent execution/result checks")

    omitted = work / "omitted-check.py"
    code = (ROOT / "native_checks.py").read_text()
    needle = "checker.check_target_with_flags([wrapped.source], [wrapped.target], context, flags)"
    assert needle in code
    omitted.write_text(code.replace(needle, "False"))
    report = json.loads(command(PYTHON, omitted, bad_po).stdout)
    try:
        check_native(report, bad=True)
    except AssertionError:
        pass
    else:
        raise AssertionError("Omitting native checks must fail acceptance")
    print("PASS omitting native check calls is rejected")

    updated = deepcopy(source)
    updated["legacy.items"]["defaultMessage"] = "Items total: {0}"
    updated["legacy.items"]["description"] = "Updated legacy count description."
    updated["docs.guide"]["weblateFlags"] = ["md-text", "ignore-md-link"]
    updated_source = work / "source-v2.json"
    write_json(updated_source, updated)
    updated_pot = work / "messages-v2.pot"
    command(PYTHON, ROOT / "catalog.py", "extract", updated_source, updated_pot)
    merged = work / "merged.po"
    command(MSGMERGE, "--previous", "--no-wrap", "--output-file", merged, po, updated_pot)
    refreshed = work / "refreshed.po"
    command(PYTHON, ROOT / "catalog.py", "refresh-flags", updated_source, merged, refreshed)
    merged = refreshed
    merged_units = {unit.getcontext(): unit for unit in read_po(merged).units if not unit.isheader() and not unit.isobsolete()}
    assert merged_units["docs.guide"].target == translations["docs.guide"]
    assert merged_units["docs.guide"].hastypecomment("md-text")
    assert merged_units["docs.guide"].hastypecomment("ignore-md-link")
    assert not merged_units["docs.guide"].hastypecomment("ignore-md-reflink")
    assert merged_units["plain.example"].target == translations["plain.example"]
    legacy = merged_units["legacy.items"]
    assert legacy.target == translations["legacy.items"] and legacy.isfuzzy()
    assert legacy.prev_source == source["legacy.items"]["defaultMessage"]
    assert legacy.getnotes("developer") == updated["legacy.items"]["description"]
    assert legacy.hastypecomment("java-format")
    blocked = work / "must-not-exist.json"
    command(PYTHON, ROOT / "catalog.py", "compile", updated_source, merged, blocked, expected=2)
    assert not blocked.exists()
    accepted_map = work / "accepted.json"
    write_json(accepted_map, {"legacy.items": "Artikel insgesamt: {0}"})
    accepted_po = work / "accepted.po"
    accepted = json.loads(command(PYTHON, ROOT / "native_checks.py", merged, "--translations", accepted_map, "--output", accepted_po).stdout)
    updated_rows = check_native(accepted)
    assert updated_rows["legacy.items"]["description"] == updated["legacy.items"]["description"]
    assert "ignore-md-link" in updated_rows["docs.guide"]["flags"]
    assert "ignore-md-reflink" not in updated_rows["docs.guide"]["flags"]
    final = work / "de-v2.json"
    command(PYTHON, ROOT / "catalog.py", "compile", updated_source, accepted_po, final)
    expected = deepcopy(updated)
    for key, value in translations.items():
        expected[key]["defaultMessage"] = value
    expected["legacy.items"]["defaultMessage"] = "Artikel insgesamt: {0}"
    assert json.loads(final.read_text()) == expected
    assert po.read_bytes() == original_po_bytes and source_path.read_bytes() == original_bytes
    print("PASS source update→GNU msgmerge preserves other translations and flags, retains changed translation as fuzzy/previous, blocks compile until updated, then produces exact JSON")

    for invalid in [{"a":{"defaultMessage":"x","weblateFlags":"md-text"}}, {"a":{"defaultMessage":"x","description":7}}, {"a":{"defaultMessage":"x","weblateFlags":["md-text\nother"]}}]:
        invalid_source = work / "invalid.json"
        write_json(invalid_source, invalid)
        invalid_output = work / "invalid.pot"
        command(PYTHON, ROOT / "catalog.py", "extract", invalid_source, invalid_output, expected=2)
        assert not invalid_output.exists()
    duplicate = work / "duplicate.json"
    duplicate.write_text('{"a":{"defaultMessage":"first"},"a":{"defaultMessage":"second"}}')
    command(PYTHON, ROOT / "catalog.py", "extract", duplicate, work / "duplicate.pot", expected=2)
    before = compiled.read_bytes()
    command(PYTHON, ROOT / "catalog.py", "compile", source_path, po, compiled, expected=2)
    assert compiled.read_bytes() == before
    print("PASS invalid metadata, duplicate JSON keys and overwriting an existing output are rejected")
