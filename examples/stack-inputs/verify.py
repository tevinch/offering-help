#!/usr/bin/env python3
"""Verify local stack generation with an installed Terramate CLI. MIT, Tevinch."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid


EXPECTED = {
    "dev-eu": {"stack": "dev-eu", "region": "eu-west-1", "account": "demo-development", "environment": "development"},
    "staging-us": {"stack": "staging-us", "region": "us-east-1", "account": "demo-staging", "environment": "staging"},
    "prod-apac": {"stack": "prod-apac", "region": "ap-southeast-2", "account": "demo-production", "environment": "production"},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terramate", required=True, help="Path to an installed Terramate binary")
    parser.add_argument("--report", type=Path, help="Write the command transcript and observations as JSON")
    args = parser.parse_args()
    executable = str(Path(args.terramate).resolve())
    template = Path(__file__).resolve().parent / "template"
    report = {"commands": [], "checks": [], "outputs": {}}

    def check(name, actual, expected):
        assert actual == expected, (
            f"{name}: expected {expected!r}, got {actual!r}\n"
            f"Latest command: {report['commands'][-1] if report['commands'] else None}"
        )
        report["checks"].append({"name": name, "value": actual})

    with tempfile.TemporaryDirectory(prefix="stack-inputs-") as temporary:
        base = Path(temporary)
        cli_config = base / "cli-config.hcl"
        cli_config.write_text(
            "disable_checkpoint = true\ndisable_checkpoint_signature = true\ndisable_telemetry = true\n"
            + "user_terramate_dir = " + json.dumps(str(base / "cli-data")) + "\n",
            encoding="utf-8",
        )
        env = {
            "PATH": os.environ.get("PATH", os.defpath), "LANG": "C", "NO_COLOR": "1",
            "TM_CLI_CONFIG_FILE": str(cli_config), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
        }

        def run(repo, *command, success=True):
            actual_command = [executable, *command] if command[0] != "git" else list(command)
            completed = subprocess.run(actual_command, cwd=repo, env=env, text=True, capture_output=True, timeout=30)
            report["commands"].append({
                "scenario": repo.name, "command": ["terramate", *command] if command[0] != "git" else list(command),
                "exit": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr,
            })
            if success:
                assert completed.returncode == 0, f"{command} failed:\n{completed.stdout}\n{completed.stderr}"
            else:
                assert completed.returncode != 0, f"{command} unexpectedly succeeded"
            return completed

        def setup(name, omit_generator=False):
            repo = base / name
            repo.mkdir()
            run(repo, "git", "-c", "init.templateDir=", "init", "--quiet")
            run(repo, "git", "config", "user.name", "Tevinch")
            run(repo, "git", "config", "user.email", "tevin.chang@live.com")
            for source in template.glob("*.tm.hcl"):
                if not (omit_generator and source.name == "generate.tm.hcl"):
                    shutil.copyfile(source, repo / source.name)
            return repo

        def inputs(repo, stack, values):
            text = "globals {\n" + "".join(
                f"  {key} = {json.dumps(value)}\n" for key, value in values.items() if key != "stack"
            ) + "}\n"
            (repo / "stacks" / stack / "globals.tm.hcl").write_text(text, encoding="utf-8")

        def outputs(repo, expected):
            found = {}
            for name, wanted in expected.items():
                path = repo / "stacks" / name / "settings.json"
                assert path.is_file(), f"missing generated settings.json for {name}"
                found[name] = json.loads(path.read_text(encoding="utf-8"))
                check(f"{repo.name}/{name} exact generated values", found[name], wanted)
            report["outputs"][repo.name] = found
            return found

        repo = setup("two-phase")
        version = run(repo, "--version").stdout.strip()
        report["version"] = version
        metadata = {}
        for name in EXPECTED:
            run(repo, "create", "--no-generate", f"stacks/{name}")
            folder = repo / "stacks" / name
            check(f"{name} created before local globals", (folder / "globals.tm.hcl").exists(), False)
            check(f"{name} has no premature output", (folder / "settings.json").exists(), False)
            metadata[name] = (folder / "stack.tm.hcl").read_bytes()
            identifier = re.search(rb'\bid\s*=\s*"([^"]+)"', metadata[name]).group(1).decode()
            check(f"{name} native stack UUID version", uuid.UUID(identifier).version, 4)
        listing = run(repo, "list").stdout.splitlines()
        check("native list contains all three stacks", sorted(listing), sorted(f"stacks/{name}" for name in EXPECTED))
        for name, values in EXPECTED.items():
            inputs(repo, name, values)
            (repo / "stacks" / name / "notes.txt").write_bytes(b"Existing notes.\n  Keep spacing.\n")
        run(repo, "generate")
        outputs(repo, EXPECTED)
        before = {name: (repo / "stacks" / name / "settings.json").read_bytes() for name in EXPECTED}
        run(repo, "generate")
        for name in EXPECTED:
            check(f"{name} repeated generation byte-idempotent", (repo / "stacks" / name / "settings.json").read_bytes(), before[name])
        changed = {**EXPECTED, "staging-us": {
            "stack": "staging-us", "region": "us-west-2", "account": "demo-staging", "environment": "staging",
        }}
        inputs(repo, "staging-us", changed["staging-us"])
        run(repo, "generate")
        outputs(repo, changed)
        for name in EXPECTED:
            check(f"{name} native metadata preserved", (repo / "stacks" / name / "stack.tm.hcl").read_bytes(), metadata[name])
            check(f"{name} existing user content preserved", (repo / "stacks" / name / "notes.txt").read_bytes(), b"Existing notes.\n  Keep spacing.\n")
            check(f"{name} only intended output changed", (repo / "stacks" / name / "settings.json").read_bytes() != before[name], name == "staging-us")

        missing = {key: value for key, value in changed["prod-apac"].items() if key != "account"}
        inputs(repo, "prod-apac", missing)
        failure = run(repo, "-C", "stacks/prod-apac", "generate", success=False)
        diagnostic = failure.stdout + failure.stderr
        check("missing account is diagnosed", 'attribute named "account"' in diagnostic, True)
        inputs(repo, "prod-apac", changed["prod-apac"])
        run(repo, "generate")
        outputs(repo, changed)

        inherited = setup("inherited")
        (inherited / "globals.tm.hcl").write_text(
            'globals {\n  region = "eu-central-1"\n  account = "demo-shared"\n  environment = "preview"\n}\n', encoding="utf-8")
        run(inherited, "create", "stacks/defaults")
        (inherited / "stacks/override").mkdir(parents=True)
        inputs(inherited, "override", {"region": "us-west-2"})
        run(inherited, "create", "stacks/override")
        outputs(inherited, {
            "defaults": {"stack": "defaults", "region": "eu-central-1", "account": "demo-shared", "environment": "preview"},
            "override": {"stack": "override", "region": "us-west-2", "account": "demo-shared", "environment": "preview"},
        })

        early = setup("without-no-generate")
        failure = run(early, "create", "stacks/too-early", success=False)
        diagnostic = failure.stdout + failure.stderr
        check("ordinary create before required globals fails generation", 'attribute named "region"' in diagnostic, True)
        check("failed generation can leave created stack metadata", (early / "stacks/too-early/stack.tm.hcl").is_file(), True)

        absent = setup("without-generator", omit_generator=True)
        for name, values in EXPECTED.items():
            run(absent, "create", "--no-generate", f"stacks/{name}")
            inputs(absent, name, values)
        run(absent, "generate")
        try:
            outputs(absent, EXPECTED)
        except AssertionError as error:
            check("missing generator is caught by final output acceptance", "missing generated settings.json" in str(error), True)
        else:
            raise AssertionError("missing-generator control did not fail final output acceptance")

        # JSON reporting represents byte observations as their literal UTF-8 text.
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2, default=lambda value: value.decode("utf-8")) + "\n", encoding="utf-8")
        native_commands = sum(command["command"][0] == "terramate" for command in report["commands"])
        print(json.dumps({"version": version, "checks": len(report["checks"]), "native_commands": native_commands, "outputs": report["outputs"]}, indent=2))


if __name__ == "__main__":
    main()
