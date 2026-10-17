"""Behavioral checks for the file export example; uses only the standard library."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from export_delta import convert_delta


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "export_delta.py"


class DocumentTests(unittest.TestCase):
    def test_many_runs_keep_their_own_inline_styles(self):
        # Catches applying the next operation's style or pairing adjacent ops.
        document = {"ops": [
            {"insert": "One "},
            {"insert": "bold", "attributes": {"bold": True}},
            {"insert": " / "},
            {"insert": "two", "attributes": {"italic": True, "underline": True}},
            {"insert": " / "},
            {"insert": "link", "attributes": {"link": "https://example.com/?a=1&b=2"}},
            {"insert": "\n", "attributes": {"header": 2}},
        ]}
        self.assertEqual(convert_delta(document),
                         '## One <strong>bold</strong> / <u><em>two</em></u> / '
                         '<a href="https://example.com/?a=1&amp;b=2">link</a>\n')

    def test_a_multiline_operation_is_split_at_every_newline(self):
        # Catches one-paragraph-per-op behavior and lost consecutive blank lines.
        self.assertEqual(convert_delta({"ops": [{"insert": "One\nTwo\n\nThree\n"}]}),
                         "One\n\nTwo\n\n<p><br></p>\n\nThree\n")

    def test_inline_style_survives_across_a_multiline_operation(self):
        self.assertEqual(convert_delta({"ops": [
            {"insert": "One\nTwo", "attributes": {"bold": True}},
            {"insert": "\n", "attributes": {"header": 3}},
        ]}), "<strong>One</strong>\n\n### <strong>Two</strong>\n")

    def test_newline_style_applies_to_each_line_not_the_previous_operation(self):
        self.assertEqual(convert_delta({"ops": [
            {"insert": "First\nSecond\n", "attributes": {"header": 1}},
            {"insert": "Third\n"},
        ]}), "# First\n\n# Second\n\nThird\n")

    def test_literal_markup_and_unicode_remain_text(self):
        self.assertEqual(convert_delta({"ops": [{"insert": '*x* [y](z) <b>& 中文 \\ `code`\n'}]}),
                         '\\*x\\* \\[y\\]\\(z\\) &lt;b&gt;&amp; 中文 \\\\ \\`code\\`\n')

    def test_edge_and_repeated_spaces_remain_visible_even_across_runs(self):
        self.assertEqual(convert_delta({"ops": [
            {"insert": " A "},
            {"insert": " B ", "attributes": {"bold": True}},
            {"insert": "\n"},
        ]}), "&#160;A&#160;<strong>&#160;B&#160;</strong>\n")

    def test_empty_document_and_multiple_blank_paragraphs_are_visible(self):
        self.assertEqual(convert_delta({"ops": [{"insert": "\n\n"}]}),
                         "<p><br></p>\n\n<p><br></p>\n")

    def test_link_attribute_is_escaped_without_changing_link_text(self):
        # Catches a quote in a URL terminating the generated href attribute.
        self.assertEqual(convert_delta({"ops": [
            {"insert": "Read <this>", "attributes": {"link": 'https://example.com/?q="x"&a=1'}},
            {"insert": "\n"},
        ]}), '<a href="https://example.com/?q=&quot;x&quot;&amp;a=1">Read &lt;this&gt;</a>\n')

    def test_invalid_unicode_in_a_link_is_rejected_before_returning_markdown(self):
        with self.assertRaises(ValueError):
            convert_delta({"ops": [
                {"insert": "Read", "attributes": {"link": "https://example.com/\ud800"}},
                {"insert": "\n"},
            ]})

    def test_contact_links_supported_by_snow_retain_their_schemes(self):
        # Catches rejecting Quill's documented safe contact link schemes.
        document = {"ops": [
            {"insert": "Phone", "attributes": {"link": "tel:+15555550100"}},
            {"insert": " or "},
            {"insert": "message", "attributes": {"link": "sms:+15555550100?body=Hello"}},
            {"insert": " or "},
            {"insert": "email", "attributes": {"link": "mailto:hello@example.com"}},
            {"insert": "\n"},
        ]}
        try:
            actual = convert_delta(document)
        except ValueError as error:
            self.fail(f"supported contact links were rejected: {error}")
        self.assertEqual(actual, '<a href="tel:+15555550100">Phone</a> or '
             '<a href="sms:+15555550100?body=Hello">message</a> or '
             '<a href="mailto:hello@example.com">email</a>\n')

    def test_relative_and_fragment_links_keep_the_original_href(self):
        # Catches rewriting or refusing links that need the destination document's base URL.
        cases = [
            ("/chapter", '<a href="/chapter">Link</a>\n'),
            ("chapter-2.html", '<a href="chapter-2.html">Link</a>\n'),
            ("#part", '<a href="#part">Link</a>\n'),
            ("//example.com/path", '<a href="//example.com/path">Link</a>\n'),
            ("chapter two.html", '<a href="chapter two.html">Link</a>\n'),
            ("https://example.com/a b", '<a href="https://example.com/a b">Link</a>\n'),
        ]
        for link, expected in cases:
            with self.subTest(link=link):
                try:
                    actual = convert_delta({"ops": [
                        {"insert": "Link", "attributes": {"link": link}}, {"insert": "\n"},
                    ]})
                except ValueError as error:
                    self.fail(f"supported link was rejected: {error}")
                self.assertEqual(actual, expected)

    def test_flat_ordered_items_continue_and_type_changes_restart(self):
        document = {"ops": [
            {"insert": "One\nTwo\n", "attributes": {"list": "ordered"}},
            {"insert": "Bullet\n", "attributes": {"list": "bullet"}},
            {"insert": "Three\n", "attributes": {"list": "ordered"}},
            {"insert": "Break\n"},
            {"insert": "Four\n", "attributes": {"list": "ordered"}},
        ]}
        self.assertEqual(convert_delta(document),
                         "1. One\n2. Two\n\n- Bullet\n\n1. Three\n\nBreak\n\n1. Four\n")

    def test_nested_lists_return_to_the_correct_parent_counter(self):
        document = {"ops": [
            {"insert": "Parent\n", "attributes": {"list": "ordered"}},
            {"insert": "Child\n", "attributes": {"list": "bullet", "indent": 1}},
            {"insert": "Grandchild\n", "attributes": {"list": "ordered", "indent": 2}},
            {"insert": "Next child\n", "attributes": {"list": "bullet", "indent": 1}},
            {"insert": "Next parent\n", "attributes": {"list": "ordered"}},
        ]}
        self.assertEqual(convert_delta(document),
                         "1. Parent\n   - Child\n     1. Grandchild\n   - Next child\n2. Next parent\n")

    def test_number_width_controls_nested_indentation(self):
        document = {"ops": [
            {"insert": "Item\n" * 10, "attributes": {"list": "ordered"}},
            {"insert": "Child\n", "attributes": {"list": "bullet", "indent": 1}},
            {"insert": "Next\n", "attributes": {"list": "ordered"}},
        ]}
        self.assertIn("9. Item\n10. Item\n    - Child\n11. Next\n", convert_delta(document))

    def test_complete_fixture_has_the_hand_checked_result(self):
        document = json.loads((HERE / "chapter.json").read_text(encoding="utf-8"))
        self.assertEqual(convert_delta(document), (HERE / "chapter.md").read_text(encoding="utf-8"))

    def test_unsupported_or_malformed_content_is_rejected(self):
        # Catches silent data loss, accepting changes as snapshots, and Python bool-as-int mistakes.
        invalid = [
            None, [], {}, {"ops": []}, {"ops": "text"}, {"ops": [{"insert": "no newline"}]},
            {"ops": [{"insert": ""}]}, {"ops": [{"retain": 3}]}, {"ops": [{"delete": 1}]},
            {"ops": [{"insert": {"image": "https://example.com/a.png"}}]},
            {"ops": [{"insert": "A\n", "attributes": {"color": "red"}}]},
            {"ops": [{"insert": "A\n", "attributes": None}]},
            {"ops": [{"insert": "A\n", "attributes": {"bold": 1}}]},
            {"ops": [{"insert": "A\n", "attributes": {"bold": False}}]},
            {"ops": [{"insert": "A\n", "attributes": {"bold": None}}]},
            {"ops": [{"insert": "A\n", "attributes": {"header": True}}]},
            {"ops": [{"insert": "A\n", "attributes": {"header": 4}}]},
            {"ops": [{"insert": "A\n", "attributes": {"header": 1, "list": "bullet"}}]},
            {"ops": [{"insert": "A\n", "attributes": {"list": "checked"}}]},
            {"ops": [{"insert": "A\n", "attributes": {"indent": 1}}]},
            {"ops": [{"insert": "A\n", "attributes": {"list": "bullet", "indent": True}}]},
            {"ops": [{"insert": "A\n", "attributes": {"list": "bullet", "indent": -1}}]},
            {"ops": [{"insert": "A\n", "attributes": {"list": "bullet", "indent": 9}}]},
            {"ops": [{"insert": "A\n", "attributes": {"list": "bullet", "indent": 1}}]},
            {"ops": [{"insert": "A\n", "attributes": {"link": "javascript:alert(1)"}}]},
            {"ops": [{"insert": "A\n", "attributes": {"link": "https://"}}]},
            {"ops": [{"insert": "A\n", "attributes": {"link": "data:text/html,text"}}]},
            {"ops": [{"insert": "A\n", "attributes": {"link": "file:///chapter"}}]},
            {"ops": [{"insert": "A\n", "attributes": {"link": " javascript:alert(1)"}}]},
            {"ops": [{"insert": "A\n", "attributes": {"link": "chapter\tname"}}]},
            {"ops": [{"insert": "A\n", "attributes": {"link": "chapter\\name"}}]},
            {"ops": [{"insert": "A\r\n"}]}, {"ops": [{"insert": "A\tB\n"}]},
            {"ops": [{"insert": "A\ud800\n"}]},
            {"ops": [{"insert": "A", "attributes": {"header": 1}}, {"insert": "\n"}]},
            {"ops": [{"insert": "A\n", "unexpected": True}]},
        ]
        for document in invalid:
            with self.subTest(document=document), self.assertRaises(ValueError):
                convert_delta(document)

    def test_indent_cannot_skip_a_level(self):
        with self.assertRaises(ValueError):
            convert_delta({"ops": [
                {"insert": "Root\n", "attributes": {"list": "bullet"}},
                {"insert": "Too deep\n", "attributes": {"list": "bullet", "indent": 2}},
            ]})

    def test_a_new_list_after_a_paragraph_needs_a_root_item(self):
        with self.assertRaises(ValueError):
            convert_delta({"ops": [
                {"insert": "Root\n", "attributes": {"list": "bullet"}},
                {"insert": "Paragraph\n"},
                {"insert": "Child\n", "attributes": {"list": "bullet", "indent": 1}},
            ]})


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "chapter.json"
        self.target = self.root / "chapter.md"
        self.source.write_bytes((HERE / "chapter.json").read_bytes())

    def run_export(self, target=None):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.source), str(target or self.target)],
                              capture_output=True, text=True, encoding="utf-8")

    def test_file_export_repeat_and_update_preserve_source(self):
        original = self.source.read_bytes()
        first = self.run_export()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(self.target.exists(), "CLI must create the output file")
        expected = (HERE / "chapter.md").read_bytes()
        self.assertEqual(self.target.read_bytes(), expected)
        self.assertEqual(self.source.read_bytes(), original)
        second_target = self.root / "copy.md"
        repeated = self.run_export(second_target)
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(second_target.read_bytes(), expected)
        self.source.write_text('{"ops":[{"insert":"Revised\\n"}]}', encoding="utf-8")
        updated = self.run_export()
        self.assertEqual(updated.returncode, 0, updated.stderr)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "Revised\n")

    def test_late_validation_failure_leaves_existing_output_unchanged(self):
        self.target.write_bytes(b"previous export\n")
        self.source.write_text('{"ops":[{"insert":"Good\\n"},{"insert":{"image":"image.png"}}]}',
                               encoding="utf-8")
        result = self.run_export()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error", result.stderr.lower())
        self.assertEqual(self.target.read_bytes(), b"previous export\n")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["chapter.json", "chapter.md"])

    def test_rejection_does_not_create_a_new_output(self):
        self.source.write_text('{"ops":[{"retain":1}]}', encoding="utf-8")
        self.assertNotEqual(self.run_export().returncode, 0)
        self.assertFalse(self.target.exists())

    def test_invalid_json_and_duplicate_keys_preserve_existing_output(self):
        self.target.write_bytes(b"keep this")
        for invalid in ['{broken', '{"ops": [], "ops": [{"insert": "A\\n"}]}']:
            with self.subTest(invalid=invalid):
                self.source.write_text(invalid, encoding="utf-8")
                self.assertNotEqual(self.run_export().returncode, 0)
                self.assertEqual(self.target.read_bytes(), b"keep this")

    def test_same_path_and_hardlink_alias_are_rejected(self):
        original = self.source.read_bytes()
        self.assertNotEqual(self.run_export(self.source).returncode, 0)
        self.assertEqual(self.source.read_bytes(), original)
        os.link(self.source, self.target)
        self.assertNotEqual(self.run_export().returncode, 0)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(self.target.read_bytes(), original)

    def test_symlink_alias_is_rejected(self):
        self.target.symlink_to(self.source)
        original = self.source.read_bytes()
        self.assertNotEqual(self.run_export().returncode, 0)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertTrue(self.target.is_symlink())

    def test_output_error_does_not_leave_temporary_files(self):
        self.target.mkdir()
        (self.target / "keep.txt").write_text("keep", encoding="utf-8")
        result = self.run_export()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.target / "keep.txt").read_text(encoding="utf-8"), "keep")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["chapter.json", "chapter.md"])


if __name__ == "__main__":
    unittest.main()
