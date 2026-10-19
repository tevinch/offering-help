"""Run with: python3 -m unittest -v"""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from reverse_notes import reverse_changes


class ReverseChangesTests(unittest.TestCase):
    def test_recent_supplied_entry_moves_first_without_changing_credits(self):
        original = (
            "Canary warning.\n\n## What's Changed\n"
            "* Older change by @dev-one in https://github.com/example/project/pull/1\n"
            "* Recent change by @dev-two in https://github.com/example/project/pull/2\n"
            "\n## New Contributors\n"
            "* @dev-two made their first contribution in https://github.com/example/project/pull/2\n"
            "\n**Full Changelog**: https://github.com/example/project/compare/v1...v2"
        )
        expected = (
            "Canary warning.\n\n## What's Changed\n"
            "* Recent change by @dev-two in https://github.com/example/project/pull/2\n"
            "* Older change by @dev-one in https://github.com/example/project/pull/1\n"
            "\n## New Contributors\n"
            "* @dev-two made their first contribution in https://github.com/example/project/pull/2\n"
            "\n**Full Changelog**: https://github.com/example/project/compare/v1...v2"
        )
        self.assertEqual(reverse_changes(original), expected)

    def test_preserves_crlf_and_no_final_newline(self):
        original = (
            "## What's Changed\r\n\r\n"
            "* A by @a in https://github.com/example/project/pull/8\r\n"
            "* B by @b in https://github.com/example/project/pull/3"
        )
        expected = (
            "## What's Changed\r\n\r\n"
            "* B by @b in https://github.com/example/project/pull/3\r\n"
            "* A by @a in https://github.com/example/project/pull/8"
        )
        self.assertEqual(reverse_changes(original), expected)

    def test_keeps_markdown_unicode_and_duplicate_titles(self):
        original = (
            "## What's Changed\n"
            "* Fix `x[y]` — café by @build-user in https://github.com/example/project/pull/9\n"
            "* Fix `x[y]` — café by @dev in https://github.com/example/project/pull/4\n"
            "\n**Full Changelog**: https://github.com/example/project/compare/a...b\n"
        )
        expected = (
            "## What's Changed\n"
            "* Fix `x[y]` — café by @dev in https://github.com/example/project/pull/4\n"
            "* Fix `x[y]` — café by @build-user in https://github.com/example/project/pull/9\n"
            "\n**Full Changelog**: https://github.com/example/project/compare/a...b\n"
        )
        self.assertEqual(reverse_changes(original), expected)

    def test_empty_and_single_entry_sections_stay_identical(self):
        for original in (
            "## What's Changed",
            "## What's Changed\n\n**Full Changelog**: https://github.com/example/project/compare/a...b\n",
            "## What's Changed\n* One by @dev in https://github.com/example/project/pull/1\n\n",
        ):
            with self.subTest(original=original):
                self.assertEqual(reverse_changes(original), original)

    def test_rejects_ambiguous_or_unrecognized_change_blocks(self):
        bullet = "* One by @dev in https://github.com/example/project/pull/1\n"
        invalid = (
            "## Changes\n" + bullet,
            "## What's Changed\n" + bullet + "## What's Changed\n",
            "## What's Changed\n### Features\n" + bullet,
            "## What's Changed\n- One by @dev in https://github.com/example/project/pull/1\n",
            "## What's Changed\n* A free-form entry\n",
            "## What's Changed\n" + bullet + "  continuation\n",
            "## What's Changed\n" + bullet + "\n" + bullet,
            "## What's Changed\n" + bullet + "\nUnrecognized trailing prose\n",
            "## What's Changed\r" + bullet,
        )
        for original in invalid:
            with self.subTest(original=original):
                with self.assertRaises(ValueError):
                    reverse_changes(original)


class CliTests(unittest.TestCase):
    script = Path(__file__).with_name("reverse_notes.py")
    source = (
        b"Warning\r\n\r\n## What's Changed\r\n"
        b"* A by @a in https://github.com/example/project/pull/1\r\n"
        b"* B by @b in https://github.com/example/project/pull/2\r\n"
        b"\r\n**Full Changelog**: https://github.com/example/project/compare/a...b"
    )
    expected = (
        b"Warning\r\n\r\n## What's Changed\r\n"
        b"* B by @b in https://github.com/example/project/pull/2\r\n"
        b"* A by @a in https://github.com/example/project/pull/1\r\n"
        b"\r\n**Full Changelog**: https://github.com/example/project/compare/a...b"
    )

    def run_cli(self, source, target):
        return subprocess.run(
            [sys.executable, str(self.script), str(source), str(target)],
            capture_output=True, text=True, check=False,
        )

    def test_writes_a_new_file_with_exact_bytes_and_preserves_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "notes ' $() ü.md"
            target = Path(directory) / 'ordered " notes.md'
            source.write_bytes(self.source)
            result = self.run_cli(source, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_bytes(), self.expected)
            self.assertEqual(source.read_bytes(), self.source)

    def test_existing_output_and_same_path_are_refused_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.md"
            target = Path(directory) / "ordered.md"
            source.write_bytes(self.source)
            target.write_bytes(b"Keep existing output")
            for output in (target, source):
                with self.subTest(output=output):
                    result = self.run_cli(source, output)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(result.stderr)
                    self.assertEqual(source.read_bytes(), self.source)
                    self.assertEqual(target.read_bytes(), b"Keep existing output")

    def test_invalid_or_non_utf8_input_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.md"
            target = Path(directory) / "ordered.md"
            for content in (b"unknown format", b"\xff\xfe"):
                with self.subTest(content=content):
                    source.write_bytes(content)
                    result = self.run_cli(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(result.stderr)
                    self.assertFalse(target.exists())
                    self.assertEqual(source.read_bytes(), content)

    def test_symlink_output_is_refused_without_touching_its_target(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.md"
            existing = Path(directory) / "existing.md"
            output = Path(directory) / "output.md"
            source.write_bytes(self.source)
            existing.write_bytes(b"Keep target")
            output.symlink_to(existing)
            result = self.run_cli(source, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(output.is_symlink())
            self.assertEqual(existing.read_bytes(), b"Keep target")


if __name__ == "__main__":
    unittest.main()
