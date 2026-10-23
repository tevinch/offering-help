"""Exercise the checked-in rules with the actual ast-grep CLI; without running C/C++ source."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
CLI = str(Path(sys.argv.pop(1)).resolve()) if len(sys.argv) > 1 else "ast-grep"
CASE_RULE = (ROOT / "capture-case.yml").read_text()
SINGLE_RULE = (ROOT / "extract-single-switch.yml").read_text()
ORIGINAL = (ROOT / "example.cpp").read_text()


def scan(source, rule=CASE_RULE, language="Cpp"):
    with tempfile.TemporaryDirectory(prefix="switch capture ") as directory:
        root = Path(directory)
        rule_file = root / "rule.yml"
        rule_file.write_text(rule.replace("language: Cpp", "language: " + language))
        source_file = root / ("example.cpp" if language == "Cpp" else "example.c")
        source_file.write_text(source)
        result = subprocess.run(
            [CLI, "scan", "--rule", str(rule_file), "--json=compact", str(source_file)],
            text=True, capture_output=True, check=True,
        )
        assert source_file.read_text() == source, "read-only scan changed its input"
        return json.loads(result.stdout)


def captures(matches):
    return [
        [node["text"] for node in match["metaVariables"]["multi"]["BODY"]]
        for match in matches
    ]


class CaptureTests(unittest.TestCase):
    def test_original_exact_nodes_and_extracted_text(self):
        for language in ("Cpp", "C"):
            with self.subTest(language=language):
                matches = scan(ORIGINAL, language=language)
                self.assertEqual(captures(matches), [["x();", "y();", "break;"]])
                match = matches[0]
                self.assertEqual(match["metaVariables"]["single"]["X"]["text"], "123")
                self.assertEqual(match["metaVariables"]["transformed"]["STATEMENTS"].strip(), "x();\ny();")

    def test_adjacent_branches_are_not_captured(self):
        source = "switch(123) { case 7: z(); break; case 123: x(); y(); break; default: q(); }"
        for language in ("Cpp", "C"):
            self.assertEqual(captures(scan(source, language=language)), [["x();", "y();", "break;"]])

    def test_empty_single_and_comment_body(self):
        for body, expected in (
            ("", ["break;"]),
            ("x();", ["x();", "break;"]),
            ("x(); /* keep */ y();", ["x();", "/* keep */", "y();", "break;"]),
        ):
            with self.subTest(body=body):
                result = scan("switch(123) { case 123: " + body + " break; }")
                self.assertEqual(captures(result), [expected])
                text = result[0]["metaVariables"]["transformed"]["STATEMENTS"].strip()
                self.assertEqual(text, body)

    def test_wrong_switch_missing_or_nonterminal_break(self):
        for source in (
            "switch(999) { case 123: x(); y(); break; }",
            "switch(123) { case 999: x(); y(); break; }",
            "switch(123) { case 123: x(); y(); }",
            "switch(123) { case 123: x(); break; y(); }",
            "switch(123) { case 123: x(); break /* comment */; }",
            "switch(123) { case 123: { x(); y(); break; } }",
        ):
            with self.subTest(source=source):
                self.assertEqual(scan(source), [])

    def test_nearest_switch_only(self):
        wrong = "switch(123) { case 7: switch(999) { case 123: x(); y(); break; } break; }"
        right = "switch(999) { case 7: switch(123) { case 123: x(); y(); break; } break; }"
        for language in ("Cpp", "C"):
            self.assertEqual(scan(wrong, language=language), [])
            self.assertEqual(captures(scan(right, language=language)), [["x();", "y();", "break;"]])

    def test_terminal_removal_preserves_strings_comments_and_nested_breaks(self):
        body = 'print("break;"); /* break; */ switch(7) { case 7: z(); break; }'
        source = "switch(123) { case 123: " + body + " break; /* outside branch */ }"
        for language in ("Cpp", "C"):
            matches = scan(source, language=language)
            outer = next(match for match in matches if match["metaVariables"]["single"]["X"]["text"] == "123")
            self.assertEqual(outer["metaVariables"]["transformed"]["STATEMENTS"].strip(), body)
            self.assertEqual(len(matches), 2)

    def test_separate_case_variable_allows_different_case(self):
        independent_case = CASE_RULE.replace("case $X:", "case $CASE:")
        source = "switch(123) { case 7: x(); y(); break; }"
        matches = scan(source, independent_case)
        self.assertEqual(captures(matches), [["x();", "y();", "break;"]])
        self.assertEqual(matches[0]["metaVariables"]["single"]["CASE"]["text"], "7")
        self.assertEqual(matches[0]["metaVariables"]["single"]["X"]["text"], "123")

    def test_whole_switch_replacement_preview(self):
        for language in ("Cpp", "C"):
            matches = scan(ORIGINAL, SINGLE_RULE, language)
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["replacement"].strip(), "x();\ny();")
            self.assertEqual(matches[0]["text"].strip(), ORIGINAL.strip())
        self.assertEqual(scan("switch(123) { case 123: x(); break; case 7: y(); break; }", SINGLE_RULE), [])


if __name__ == "__main__":
    version = subprocess.run([CLI, "--version"], text=True, capture_output=True, check=True)
    print(version.stdout.strip(), flush=True)
    unittest.main(verbosity=2)
