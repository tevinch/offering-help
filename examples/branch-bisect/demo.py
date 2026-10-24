"""Create a disposable, diverged Git history for trying branch bisecting."""

import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--check", action="store_true", help="test the current demo revision")
    args = parser.parse_args()
    directory = args.directory.resolve()
    marker = directory / ".git" / "branch-bisect-example.json"

    if args.check:
        if not marker.is_file():
            parser.error("not a repository created by this example")
        level = int((directory / "level.txt").read_text())
        good = level < 5
        print(f"level={level}: {'good' if good else 'bad'}")
        return 0 if good else 1

    if directory.exists():
        parser.error("choose a new directory; the target already exists")
    directory.mkdir(parents=True)
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

    def git(*arguments):
        return subprocess.check_output(
            ["git", "-C", str(directory), *arguments],
            env=environment, text=True, stderr=subprocess.STDOUT,
        ).strip()

    git("init", "-b", "dev")
    git("config", "user.name", "Tevinch")
    git("config", "user.email", "tevin.chang@live.com")
    git("config", "core.hooksPath", os.devnull)
    (directory / "level.txt").write_text("0\n")
    (directory / "kept.txt").write_text("Existing project content stays intact.\n")
    git("add", ".")
    git("commit", "-m", "Common baseline")
    baseline = git("rev-parse", "HEAD")
    git("checkout", "-b", "staging")
    (directory / "staging-note.txt").write_text("Independent staging documentation.\n")
    git("add", ".")
    git("commit", "-m", "Known-good staging side commit")
    staging = git("rev-parse", "HEAD")
    git("checkout", "dev")
    revisions = []
    for level in range(1, 9):
        (directory / "level.txt").write_text(f"{level}\n")
        git("add", "level.txt")
        git("commit", "-m", f"Development revision {level:02}")
        revisions.append(git("rev-parse", "HEAD"))
    result = {
        "baseline": baseline, "staging": staging,
        "devTip": revisions[-1], "firstBad": revisions[4],
    }
    marker.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Created {directory}\nFirst bad: {result['firstBad']} (revision 05)")
    print("The staging tip is on a separate branch, not an ancestor of dev.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
