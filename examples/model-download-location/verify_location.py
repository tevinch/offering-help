"""Check a Hub cache or local directory using two small, non-executable JSON files."""
import argparse
import hashlib
import json
import os
from pathlib import Path


REPO = "OpenMOSS-Team/MOSS-Image-Base"
REVISION = "85975793d8b3d432f1b6e27f352abaa4c2a4c0d3"
FILES = ("model_index.json", "scheduler/scheduler_config.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("cache", "local"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--offline", action="store_true", help="Reuse only files already downloaded")
    args = parser.parse_args()
    destination = args.directory.expanduser().resolve()

    # Hub settings are read on import. This is a standalone command, not a notebook cell.
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    if args.mode == "cache":
        os.environ["HF_HUB_CACHE"] = str(destination)
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"

    from huggingface_hub import snapshot_download

    options = {"local_dir": destination} if args.mode == "local" else {}
    downloaded = Path(snapshot_download(
        REPO,
        revision=REVISION,
        allow_patterns=list(FILES),
        local_files_only=args.offline,
        token=False,
        **options,
    ))
    results = {}
    for name in FILES:
        path = (downloaded / name).resolve()
        if not path.is_relative_to(destination):
            raise RuntimeError(f"Downloaded file is outside the requested directory: {path}")
        contents = path.read_bytes()
        parsed = json.loads(contents)
        if not isinstance(parsed, dict) or not parsed:
            raise RuntimeError(f"Expected a nonempty JSON object: {name}")
        results[name] = {"bytes": len(contents), "sha256": hashlib.sha256(contents).hexdigest()}

    print(json.dumps({
        "mode": args.mode,
        "directory": str(destination),
        "download_path": str(downloaded),
        "revision": REVISION,
        "offline": args.offline,
        "files": results,
    }, indent=2))


if __name__ == "__main__":
    main()
