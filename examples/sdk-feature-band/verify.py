#!/usr/bin/env python3
"""Exercise SDK resolution and a real build in fresh copies of this sample."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent
FILES = ["global.json", "SdkSelection.csproj", "Program.cs"]


def run(dotnet, arguments, cwd):
    result = subprocess.run([dotnet, *arguments], cwd=cwd, text=True, capture_output=True)
    print(f"$ dotnet {' '.join(arguments)}", flush=True)
    print(result.stdout, end="", flush=True)
    print(result.stderr, end="", file=sys.stderr, flush=True)
    return result


def main():
    dotnet = sys.argv[1] if len(sys.argv) > 1 else shutil.which("dotnet")
    assert dotnet, "Pass a dotnet host with a .NET 10.0.4xx SDK installed"
    dotnet = str(Path(dotnet).resolve())
    before = {f: hashlib.sha256((SOURCE / f).read_bytes()).hexdigest() for f in FILES}
    with tempfile.TemporaryDirectory(prefix="sdk selection ") as directory:
        root = Path(directory)
        (root / "global.json").write_text('{"sdk":{"version":"8.0.100","rollForward":"disable"}}\n')
        sample = root / "sample"
        sample.mkdir()
        for filename in FILES:
            shutil.copyfile(SOURCE / filename, sample / filename)
        selected = run(dotnet, ["--version"], sample)
        assert selected.returncode == 0, "sample global.json did not select an available compatible SDK"
        version = selected.stdout.strip()
        assert re.fullmatch(r"10\.0\.4\d\d", version), f"expected stable 10.0.4xx, got {version!r}"
        prop = run(dotnet, ["msbuild", "SdkSelection.csproj", "-getProperty:NETCoreSdkVersion"], sample)
        assert prop.returncode == 0 and prop.stdout.strip() == version, "project resolved a different SDK"
        built = run(dotnet, ["build", "SdkSelection.csproj", "--nologo"], sample)
        assert built.returncode == 0, "native project build failed"
        started = run(dotnet, ["run", "--project", "SdkSelection.csproj", "--no-build"], sample)
        assert started.returncode == 0 and started.stdout.strip() == "SDK selection sample ran."
        inherited_dir = root / "ancestor-only"
        inherited_dir.mkdir()
        print("Negative control: a directory without the sample's global.json inherits the ancestor pin", flush=True)
        inherited = run(dotnet, ["--version"], inherited_dir)
        assert inherited.returncode != 0 or inherited.stdout.strip() == "8.0.100", "ancestor SDK pin was ignored"
        installed = run(dotnet, ["--list-sdks"], sample)
        assert installed.returncode == 0
        installed_versions = {line.split()[0] for line in installed.stdout.splitlines() if line.strip()}
        missing = next((f"10.0.{patch}" for patch in range(400, 500) if f"10.0.{patch}" not in installed_versions), None)
        assert missing, "negative fixture needs a missing patch in the 4xx band"
        strict = root / "strict"
        strict.mkdir()
        (strict / "global.json").write_text(json.dumps({"sdk": {"version": missing, "rollForward": "disable", "allowPrerelease": False}}))
        print("Negative control: a missing SDK with rollForward=disable must fail", flush=True)
        refused = run(dotnet, ["--version"], strict)
        assert refused.returncode != 0, "strict missing SDK pin unexpectedly resolved"
        assert (root / "global.json").read_text() == '{"sdk":{"version":"8.0.100","rollForward":"disable"}}\n'
        if len(sys.argv) > 2:
            older = str(Path(sys.argv[2]).resolve())
            print("Negative control: the older host must not resolve this sample's SDK", flush=True)
            refused_old = run(older, ["--version"], sample)
            assert refused_old.returncode != 0, "the older host unexpectedly supplies the required SDK"
        print(f"PASS: SDK {version} selected, project property matched, actual build/run completed; missing strict pin rejected")
    assert {f: hashlib.sha256((SOURCE / f).read_bytes()).hexdigest() for f in FILES} == before
    print("PASS: original sample files unchanged; fixture ancestor global.json unchanged")


if __name__ == "__main__":
    main()
