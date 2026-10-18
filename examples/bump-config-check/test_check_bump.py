"""Run the checker as a user would, against temporary files."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("check_bump.py")


class CheckBumpTests(unittest.TestCase):
    def check(self, config, files=None, expected="1.2.3", links=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bump.yml").write_text(config, encoding="utf-8")
            for name, content in (files or {}).items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            for name, destination in (links or {}).items():
                (root / name).symlink_to(destination)
            before = {
                str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob("*") if p.is_file()
            }
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--config", "bump.yml",
                 "--root", str(root), "--expected-version", expected],
                cwd=root, env={**os.environ, "PATH": ""},
                capture_output=True, text=True,
            )
            after = {
                str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob("*") if p.is_file()
            }
            self.assertEqual(before, after, "checker changed or created a file")
            return result

    def test_checks_every_target_with_mixed_line_endings(self):
        result = self.check(
            "files:\n  - {file-path: package.json, line: 3}\n"
            "  - {file-path: versions.txt, line: 1}\n"
            "  - {file-path: versions.txt, line: 2, start: 13}\n",
            {"package.json": b'{\r\n  "name": "sample",\r\n  "version": "1.2.3"\r\n}\r\n',
             "versions.txt": b"1.2.3\rschema=9.9.9 release=1.2.3\n"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("OK "), 3)
        self.assertIn("Checked 3 targets", result.stdout)

    def test_start_uses_javascript_utf16_units(self):
        result = self.check(
            "files: [{file-path: version.txt, line: 1, start: 9}]\n",
            {"version.txt": "😀 9.9.9 1.2.3\n".encode()},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_yaml12_integer_offsets_do_not_use_legacy_octal(self):
        result = self.check(
            "files: [{file-path: version.txt, line: 010, start: 0o11}]\n",
            {"version.txt": b"wrong\n" * 9 + b"9.9.9    1.2.3\n"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_null_start_has_the_same_meaning_as_omitted_start(self):
        result = self.check(
            "files: [{file-path: version.txt, line: 1, start: null}]\n",
            {"version.txt": b"1.2.3\n"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reports_all_bad_targets_instead_of_stopping_after_first(self):
        result = self.check(
            "files:\n  - {file-path: absent.txt, line: 1}\n"
            "  - {file-path: version.txt, line: 4}\n"
            "  - {file-path: version.txt, line: 1}\n",
            {"version.txt": b"9.9.9\n"},
        )
        self.assertEqual(result.returncode, 1)
        for phrase in ["files[0]", "files[1]", "files[2]", "absent.txt", "9.9.9"]:
            self.assertIn(phrase, result.stderr)

    def test_first_match_must_equal_expected_even_if_later_match_is_correct(self):
        result = self.check(
            "files: [{file-path: version.txt, line: 1}]\n",
            {"version.txt": b"9.9.9 then 1.2.3\n"},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("found 9.9.9", result.stderr)

    def test_start_after_version_fails(self):
        result = self.check(
            "files: [{file-path: version.txt, line: 1, start: 5}]\n",
            {"version.txt": b"1.2.3\n"},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("no numeric version", result.stderr)

    def test_trailing_newline_does_not_add_a_line(self):
        result = self.check(
            "files: [{file-path: version.txt, line: 2}]\n",
            {"version.txt": b"1.2.3\n"},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside", result.stderr)

    def test_absent_or_empty_files_never_succeeds(self):
        for config in ["release: {}\n", "files: []\n", "files: {}\n", "[]\n", ""]:
            with self.subTest(config=config):
                result = self.check(config)
                self.assertEqual(result.returncode, 1)

    def test_invalid_entries_are_not_silently_skipped(self):
        entries = ["{}", "null", "{file-path: version.txt}",
                   "{file-path: version.txt, line: 1, strt: 2}",
                   "{file-path: version.txt, line: true}",
                   "{file-path: version.txt, line: 0}",
                   "{file-path: version.txt, line: -1}",
                   "{file-path: version.txt, line: '1'}",
                   "{file-path: version.txt, line: 1, start: -1}",
                   "{file-path: version.txt, line: 1, start: 1.5}"]
        for entry in entries:
            with self.subTest(entry=entry):
                result = self.check("files: [" + entry + "]\n", {"version.txt": b"1.2.3"})
                self.assertEqual(result.returncode, 1)
                self.assertIn("files[0]", result.stderr)

    def test_duplicate_yaml_keys_fail(self):
        result = self.check("files: []\nfiles: [{file-path: version.txt, line: 1}]\n",
                            {"version.txt": b"1.2.3"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate", result.stderr)

    def test_yaml_aliases_check_each_declaration(self):
        result = self.check("files:\n  - &target {file-path: version.txt, line: 1}\n  - *target\n",
                            {"version.txt": b"1.2.3"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("OK "), 2)

    def test_unquoted_yaml12_filename_on_is_a_string(self):
        result = self.check("files: [{file-path: on, line: 1}]\n", {"on": b"1.2.3"})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_symlink_cannot_read_a_target_outside_root(self):
        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory) / "version.txt"
            external.write_bytes(b"1.2.3")
            result = self.check("files: [{file-path: linked.txt, line: 1}]\n",
                                links={"linked.txt": external})
            self.assertEqual(result.returncode, 1)
            self.assertIn("outside", result.stderr)
            self.assertEqual(external.read_bytes(), b"1.2.3")

    def test_numeric_core_in_prerelease_matches_action_scope(self):
        result = self.check("files: [{file-path: version.txt, line: 1}]\n",
                            {"version.txt": b"v1.2.3-rc.1+build\n"})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_non_ascii_digits_are_not_a_version(self):
        result = self.check("files: [{file-path: version.txt, line: 1}]\n",
                            {"version.txt": "١.٢.٣\n".encode()})
        self.assertEqual(result.returncode, 1)
        self.assertIn("no numeric version", result.stderr)

    def test_absolute_or_parent_paths_are_rejected(self):
        for path in ["/tmp/version.txt", "../version.txt"]:
            with self.subTest(path=path):
                result = self.check(f"files: [{{file-path: '{path}', line: 1}}]\n")
                self.assertEqual(result.returncode, 1)
                self.assertIn("root", result.stderr)

    def test_bad_yaml_and_custom_tags_fail(self):
        for config in ["files: [\n", "files: !!python/object:other.Class {}\n"]:
            with self.subTest(config=config):
                result = self.check(config)
                self.assertEqual(result.returncode, 1)
                self.assertIn("YAML", result.stderr)

    def test_expected_version_is_numeric_core(self):
        result = self.check("files: [{file-path: version.txt, line: 1}]\n",
                            {"version.txt": b"1.2.3"}, expected="1.2.3-rc.1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("X.Y.Z", result.stderr)

    def test_expected_version_rejects_invalid_semver_cores(self):
        for expected in ["01.2.3", "1.02.3", "1.2.03", "9007199254740992.2.3"]:
            with self.subTest(expected=expected):
                result = self.check("files: [{file-path: version.txt, line: 1}]\n",
                                    {"version.txt": expected.encode()}, expected=expected)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("X.Y.Z", result.stderr)


if __name__ == "__main__":
    unittest.main()
