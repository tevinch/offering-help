"""Check bump-release-action file targets without running a release."""

import argparse
from pathlib import Path
import re
import sys

import yaml


VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
CORE = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")


class ConfigLoader(yaml.SafeLoader):
    """Reject duplicate keys rather than silently losing declarations."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    None, None, "duplicate YAML key", key_node.start_mark
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


# Use YAML 1.2 scalar spelling, including decimal 010 and explicit octal 0o10.
ConfigLoader.yaml_implicit_resolvers = {
    key: [(tag, expression) for tag, expression in values
          if tag not in {"tag:yaml.org,2002:bool", "tag:yaml.org,2002:int"}]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
ConfigLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)
ConfigLoader.add_implicit_resolver(
    "tag:yaml.org,2002:int",
    re.compile(r"^[-+]?(?:0b[01_]+|0o[0-7_]+|0x[0-9a-fA-F_]+|[0-9][0-9_]*)$"),
    list("-+0123456789"),
)


def construct_integer(loader, node):
    value = loader.construct_scalar(node).replace("_", "")
    unsigned = value.lstrip("+-")
    base = 0 if unsigned.startswith(("0b", "0o", "0x")) else 10
    return int(value, base)


ConfigLoader.add_constructor("tag:yaml.org,2002:int", construct_integer)


def read_config(path):
    try:
        config = yaml.load(path.read_bytes().decode("utf-8"), Loader=ConfigLoader)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        location = f" at line {mark.line + 1}" if mark else ""
        reason = "duplicate YAML key" if "duplicate YAML key" in str(error) else "invalid YAML"
        raise ValueError(f"{reason}{location}") from error
    except (OSError, UnicodeError) as error:
        raise ValueError("cannot read UTF-8 YAML configuration") from error
    if not isinstance(config, dict):
        raise ValueError("YAML configuration must be a mapping")
    targets = config.get("files")
    if not isinstance(targets, list) or not targets:
        raise ValueError("files must be a nonempty list of targets")
    return targets


def check_target(target, root, expected):
    if not isinstance(target, dict):
        raise ValueError("target must be a mapping")
    if set(target) - {"file-path", "line", "start"}:
        raise ValueError("unknown target field; use file-path, line and optional start")
    name = target.get("file-path")
    line_number = target.get("line")
    start = target.get("start")
    if start is None:
        start = 0
    if not isinstance(name, str) or not name:
        raise ValueError("file-path must be a nonempty string")
    if type(line_number) is not int or line_number < 1:
        raise ValueError("line must be an integer of at least 1")
    if type(start) is not int or start < 0:
        raise ValueError("start must be a nonnegative integer")
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("file-path must stay inside the selected root")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("file-path resolves outside the selected root")
    try:
        text = path.read_bytes().decode("utf-8", errors="replace")
    except (OSError, ValueError) as error:
        raise ValueError(f"cannot read {name}") from error

    # The action recognizes CRLF, CR and LF, without a virtual final empty line.
    lines = re.split(r"\r\n|\r|\n", text)
    if lines[-1] == "":
        lines.pop()
    if line_number > len(lines):
        raise ValueError(f"{name}: line {line_number} is outside the file ({len(lines)} lines)")
    line = lines[line_number - 1]
    # JavaScript String.slice offsets count UTF-16 code units, including surrogates.
    tail = line.encode("utf-16-le", errors="surrogatepass")[start * 2:]
    search = tail.decode("utf-16-le", errors="surrogatepass")
    match = VERSION.search(search)
    if match is None:
        raise ValueError(f"{name}:{line_number}: no numeric version at or after start {start}")
    found = match.group()
    if found != expected:
        raise ValueError(f"{name}:{line_number}: found {found}; expected {expected}")
    return f"{name}:{line_number} (start {start}) = {found}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=".github/bump.yml", help="configuration path, relative to root")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    parser.add_argument("--expected-version", required=True, help="expected numeric X.Y.Z version core")
    args = parser.parse_args()
    if (len(args.expected_version) > 256
            or CORE.fullmatch(args.expected_version) is None
            or any(int(part) > 9007199254740991 for part in args.expected_version.split("."))):
        parser.error("--expected-version must be a numeric X.Y.Z core")
    root = args.root.resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    try:
        targets = read_config(config_path)
    except (ValueError, TypeError) as error:
        print(f"ERROR config: {error}", file=sys.stderr)
        return 1
    failures = 0
    for index, target in enumerate(targets):
        try:
            message = check_target(target, root, args.expected_version)
        except (ValueError, OSError, RuntimeError) as error:
            print(f"ERROR files[{index}]: {error}", file=sys.stderr)
            failures += 1
        else:
            print(f"OK files[{index}]: {message}")
    if failures:
        print(f"Failed {failures} of {len(targets)} targets.", file=sys.stderr)
        return 1
    print(f"Checked {len(targets)} targets; files unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
