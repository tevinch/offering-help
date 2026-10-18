#!/usr/bin/env python3
"""Check the local Terraform/Helm example without contacting a cluster."""

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent
OVERLAY = "    yamlencode({ rawValuesContent = file(local.values_file) }),\n"


def run(directory, *arguments):
    result = subprocess.run(
        ["terraform", *arguments],
        cwd=directory,
        env={**os.environ, "TF_IN_AUTOMATION": "1", "CHECKPOINT_DISABLE": "1"},
        text=True,
        capture_output=True,
        check=False,
    )
    print(f"terraform {' '.join(arguments)}: exit {result.returncode}")
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    return result


def require_success(result):
    if result.returncode:
        raise AssertionError("The Terraform command failed; see its output above.")
    return result.stdout


def main():
    source_files = [ROOT / "main.tf", ROOT / "values.yaml", *sorted((ROOT / "chart").rglob("*.yaml"))]
    hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files}
    original = (ROOT / "main.tf").read_text()
    source_bytes = (ROOT / "values.yaml").read_bytes()

    with tempfile.TemporaryDirectory(prefix="values-file-check-") as temporary:
        directory = Path(temporary)
        shutil.copytree(ROOT / "chart", directory / "chart")
        shutil.copyfile(ROOT / "values.yaml", directory / "values.yaml")
        lock = ROOT / ".terraform.lock.hcl"
        if lock.exists():
            shutil.copyfile(lock, directory / lock.name)
        config = directory / "main.tf"
        config.write_text(original)
        require_success(run(directory, "init", "-input=false", "-no-color"))

        config.write_text(original.replace(OVERLAY, ""))
        negative = run(directory, "plan", "-input=false", "-no-color")
        assert negative.returncode != 0, "Missing rawValuesContent must fail."
        diagnostic = " ".join((negative.stdout + negative.stderr).split())
        assert "rawValuesContent is required" in diagnostic
        print("PASS: parsed values alone fail the chart's raw-string requirement.")

        config.write_text(original)
        require_success(run(directory, "plan", "-input=false", "-no-color", "-out=example.tfplan"))
        plan = json.loads(require_success(run(directory, "show", "-json", "example.tfplan")))
        values = plan["planned_values"]["outputs"]["rendered_values"]["value"]
        assert base64.b64decode(values["rawValuesBase64"]) == source_bytes
        assert values["replicaCount"] == "3"
        assert values["featureEnabled"] == "true"
        assert values["servicePort"] == "8087"
        assert values["message"] == 'Café, {demo}: "quoted" # literal $value \\\\ path'
        assert json.loads(values["items"]) == ["first", "second"]
        print("PASS: local rendering preserves raw bytes and all parsed sample values.")

        second = run(directory, "plan", "-input=false", "-no-color", "-out=repeat.tfplan")
        require_success(second)
        repeated = json.loads(require_success(run(directory, "show", "-json", "repeat.tfplan")))
        assert repeated["planned_values"]["outputs"] == plan["planned_values"]["outputs"]
        print("PASS: repeated rendering produces the same output.")

        decomposed = source_bytes.replace("Café".encode(), "Cafe\u0301".encode())
        assert decomposed != source_bytes
        (directory / "values.yaml").write_bytes(decomposed)
        normalized = run(directory, "plan", "-input=false", "-no-color")
        assert normalized.returncode != 0, "A string that changes file bytes must be rejected."
        diagnostic = " ".join((normalized.stdout + normalized.stderr).split())
        assert "Resource precondition failed" in diagnostic
        assert "The values file changes under Terraform's Unicode normalization" in diagnostic
        assert "Read complete" not in normalized.stdout
        print("PASS: decomposed Unicode is rejected before its raw bytes can change.")
        (directory / "values.yaml").write_bytes(source_bytes)

    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    print("PASS: source configuration, chart, and values file are unchanged.")


if __name__ == "__main__":
    main()
