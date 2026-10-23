#!/usr/bin/env python3
"""Exercise npm tarball packaging with a temporary official dprint JSON fixture."""

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request


CLI_VERSION = "0.64.3"
JSON_VERSION = "0.25.2"
JSON_INTEGRITY = "sha512-QpOGNXL3cOunsB7IBPJxlIisMhFcIeMXSAWoavJKwjJjtOZW5sDojlgn2MPYNdHVgknZeQsUqDYyhGqqN1bYuQ=="
NATIVE_INTEGRITIES = {
    "darwin-arm64": "sha512-doIkcq1e6kbut7iGC3U+mEDrI8ncLPpZrfP0/jU4x12dX15tH7HUfoeW63AJbKL940rEBKPGemihDWA7DhGUKQ==",
    "darwin-x64": "sha512-2tLgFrMGWa03WTcoXLjU1JAUmHgIUaq4I91Ik1xPx+jxt7NEkeo0qPny1bqFFtOkCkI13R5CkLAgTrNA5KK8PQ==",
    "linux-x64-glibc": "sha512-wKVnD6eO8S4U8LbVcZy0l0ioJKfLbsL1OYUr0f4M99lrBv30RA385sii5Fq/NSM8O/sh9gII8zRvdtTMUWbImg==",
    "linux-arm64-glibc": "sha512-dJQ5PS0+7COmKG0NHy11pEoCfzeL1slrGuHWS0uQmyIbBskbItFnubR9KsD1J/UfYIq62rySvAm2D+MNw7cYOA==",
}
JSON_SOURCE = "https://raw.githubusercontent.com/dprint/dprint-plugin-json/f643fb7f6a119e7e8e87abbe8da7d9ca69aaebd9"
CLI_SOURCE = "https://raw.githubusercontent.com/dprint/dprint/3c029b24fed3c5e002dac00704894011b5c2adee"
INPUT = b'{\n"message":"keep me",\n"values":[1,2,3],\n"nested":{\n"enabled":true\n}\n}\n'
EXPECTED = b'''{
    "message": "keep me",
    "values": [1, 2, 3],
    "nested": {
        "enabled": true
    }
}
'''


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "wasm-package-example"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(80 * 1024 * 1024 + 1)
    require(len(data) <= 80 * 1024 * 1024, "Download exceeds size limit")
    return data


def package_member(package, version, integrity, member):
    leaf = package.rsplit("/", 1)[-1]
    url = f"https://registry.npmjs.org/{package}/-/{leaf}-{version}.tgz"
    archive = fetch(url)
    actual = "sha512-" + base64.b64encode(hashlib.sha512(archive).digest()).decode()
    require(actual == integrity, f"Registry integrity mismatch: {package}@{version}")
    print(f"Verified registry SHA512: {package}@{version}", flush=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as packed:
        entry = packed.getmember(member)
        require(entry.isfile(), f"Not a regular archive file: {member}")
        return packed.extractfile(entry).read()


def license_text(source, checksum):
    content = fetch(source + "/LICENSE")
    require(hashlib.sha256(content).hexdigest() == checksum, "Upstream license checksum changed")
    return content


def native_platform():
    system = platform.system().lower()
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64"}.get(platform.machine())
    suffix = "-glibc" if system == "linux" and platform.libc_ver()[0] == "glibc" else ""
    name = f"{system}-{arch}{suffix}"
    require(name in NATIVE_INTEGRITIES, "Supported: macOS arm64/x64 and Linux glibc arm64/x64")
    return name


def run(args, cwd, env, success=True, failure_text=None):
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, timeout=120)
    output = result.stdout + result.stderr
    if success:
        require(result.returncode == 0, f"Command failed: {args}\n{output}")
    else:
        require(result.returncode != 0, f"Expected failure: {args}\n{output}")
        if failure_text:
            require(failure_text in output, f"Unexpected failure (wanted {failure_text!r}):\n{output}")
        if failure_text == "Could not find plugin.wasm":
            print(f"Expected missing-file failure (exit {result.returncode}):\n{output.strip()}", flush=True)
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def pack(stage, wasm_path, wasm, env, expect_wasm=True):
    result = run(["npm", "pack", "--ignore-scripts", "--json"], stage, env)
    tarball = stage / json.loads(result.stdout)[0]["filename"]
    with tarfile.open(tarball, "r:gz") as archive:
        names = archive.getnames()
        print(f"Packed {stage.name}: {', '.join(names)}", flush=True)
        target = "package/" + wasm_path
        require((target in names) == expect_wasm, f"Archive missing or unexpectedly includes {target}")
        if expect_wasm:
            require(archive.extractfile(target).read() == wasm, "Packed Wasm bytes differ")
        require("package/LICENSE" in names, "Fixture license absent from archive")
        require("package/README.md" in names, "Fixture attribution absent from archive")
    return tarball


def consumer(root, label, tarball, package_name, wasm_path, wasm, env):
    directory = root / ("consumer-" + label)
    directory.mkdir()
    write_json(directory / "package.json", {"name": "format-consumer", "version": "0.0.0", "private": True})
    run(["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund", str(tarball)], directory, env)
    installed = directory / "node_modules" / package_name
    require(not installed.is_symlink(), "Consumer must install a tarball, not link the source")
    if wasm_path:
        require((installed / wasm_path).read_bytes() == wasm, "Installed Wasm bytes differ")
    (directory / "sample.json").write_bytes(INPUT)
    (directory / "notes.txt").write_bytes(b"Original unrelated content.\n")
    return directory


def config(directory, specifier):
    write_json(directory / "dprint.json", {
        "indentWidth": 4,
        "lineWidth": 80,
        "includes": ["sample.json"],
        "plugins": [specifier],
    })


def assert_content(directory, expected):
    actual = (directory / "sample.json").read_bytes()
    require(actual == expected, f"Unexpected formatted bytes:\n{actual!r}\nExpected:\n{expected!r}")
    require(json.loads(actual) == json.loads(INPUT), "Original JSON values changed")
    require((directory / "notes.txt").read_bytes() == b"Original unrelated content.\n", "Unrelated file changed")


def formatted(dprint, directory, env):
    args = [str(dprint), "check", "--config", "dprint.json", "sample.json"]
    run(args, directory, env, success=False, failure_text="Found 1 not formatted file")
    assert_content(directory, INPUT)
    run([str(dprint), "fmt", "--config", "dprint.json", "sample.json"], directory, env)
    assert_content(directory, EXPECTED)
    run(args, directory, env)
    run([str(dprint), "fmt", "--config", "dprint.json", "sample.json"], directory, env)
    assert_content(directory, EXPECTED)


def verify():
    require(shutil.which("npm"), "npm must be on PATH")
    template = Path(__file__).resolve().parent / "template" / "package.json"
    metadata = json.loads(template.read_text())
    require(metadata.get("private") is True, "Keep the fixture package private")
    require(not any(key in metadata for key in ["main", "exports", "type", "keywords", "scripts", "dependencies"]),
            "Minimum template must not depend on JS metadata, scripts, or dependencies")
    name = metadata["name"]
    with tempfile.TemporaryDirectory(prefix="wasm-package-") as temporary:
        root = Path(temporary).resolve()
        # npm's user/global config and cache, plus dprint's cache/config, stay local to this run.
        empty_config = root / "empty.npmrc"
        empty_config.write_text("")
        env = os.environ.copy()
        for key in list(env):
            if key.lower().startswith("npm_config_") or key.startswith("DPRINT_"):
                del env[key]
        env.update({
            "npm_config_userconfig": str(empty_config),
            "npm_config_globalconfig": str(root / "global.npmrc"),
            "npm_config_cache": str(root / "npm-cache"),
            "npm_config_update_notifier": "false",
            "DPRINT_CACHE_DIR": str(root / "dprint-cache"),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "GIT_CONFIG_GLOBAL": str(root / "empty.gitconfig"),
            "GIT_CONFIG_NOSYSTEM": "1",
        })
        wasm = package_member("@dprint/json", JSON_VERSION, JSON_INTEGRITY, "package/plugin.wasm")
        print(f"Fixture Wasm SHA256: {hashlib.sha256(wasm).hexdigest()}", flush=True)
        notice = license_text(JSON_SOURCE, "b1f397e882e63feef0d0331a7d55e2b36deddf8d098a6216f4754397710b60df")
        target = native_platform()
        binary = package_member("@dprint/" + target, CLI_VERSION, NATIVE_INTEGRITIES[target], "package/dprint")
        dprint = root / "dprint"
        dprint.write_bytes(binary)
        dprint.chmod(0o700)
        (root / "dprint-LICENSE").write_bytes(license_text(
            CLI_SOURCE, "f49eac7bc59816a4b7fffd64914169ef46deb636f94b77eaa274e7352983c3fa"))
        version = run([str(dprint), "--version"], root, env).stdout.strip()
        require(version == "dprint " + CLI_VERSION, "Unexpected native dprint version")
        print(f"Native {version} ({target}); npm " + run(["npm", "--version"], root, env).stdout.strip(), flush=True)

        def stage(label, path, data):
            directory = root / ("package-" + label)
            directory.mkdir()
            write_json(directory / "package.json", data)
            destination = directory / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(wasm)
            (directory / "LICENSE").write_bytes(notice)
            (directory / "README.md").write_text(
                f"Temporary packaging fixture: @dprint/json@{JSON_VERSION}.\n"
                f"Source: {JSON_SOURCE}\nMIT, copyright 2020 David Sherret.\n"
                "Not an original formatter and not for registry publication.\n")
            return directory

        default = stage("root", "plugin.wasm", metadata)
        tarball = pack(default, "plugin.wasm", wasm, env)
        local = consumer(root, "root", tarball, name, "plugin.wasm", wasm, env)
        config(local, "npm:" + name)
        formatted(dprint, local, env)
        print("PASS root: pack → clean tarball install → native fmt → exact bytes → check/idempotence", flush=True)

        custom_metadata = dict(metadata, files=["wasm/format.wasm"], main="wasm/format.wasm",
                               exports={".": "./wasm/format.wasm"})
        custom = stage("custom", "wasm/format.wasm", custom_metadata)
        tarball = pack(custom, "wasm/format.wasm", wasm, env)
        local = consumer(root, "custom", tarball, name, "wasm/format.wasm", wasm, env)
        config(local, "npm:" + name)
        run([str(dprint), "fmt", "--config", "dprint.json", "sample.json"], local, env,
            success=False, failure_text="Could not find plugin.wasm")
        assert_content(local, INPUT)
        print("PASS missing default: main/exports do not redirect native lookup", flush=True)
        config(local, "npm:" + name + "/wasm/format.wasm")
        formatted(dprint, local, env)
        print("PASS custom: explicit npm subpath formats exact output", flush=True)

        excluded = stage("excluded", "plugin.wasm", dict(metadata, files=["dist/"]))
        tarball = pack(excluded, "plugin.wasm", wasm, env, expect_wasm=False)
        local = consumer(root, "excluded", tarball, name, None, wasm, env)
        require(not (local / "node_modules" / name / "plugin.wasm").exists(), "Excluded Wasm was installed")
        config(local, "npm:" + name)
        run([str(dprint), "fmt", "--config", "dprint.json", "sample.json"], local, env,
            success=False, failure_text="Could not find plugin.wasm")
        assert_content(local, INPUT)
        print("PASS excluded Wasm: pack succeeds, consumer formatting fails", flush=True)
    print("All checks passed. Temporary fixture packages, binaries and caches are removed.", flush=True)


if __name__ == "__main__":
    verify()
