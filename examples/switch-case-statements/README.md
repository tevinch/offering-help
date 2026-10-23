# Capture C/C++ switch branch statements

Extract the statements before the final `break;` in one `case`, while checking
the surrounding `switch` expression. This answers the C/C++ pattern question in
[ast-grep discussion #2991](https://github.com/ast-grep/ast-grep/discussions/2991).

The example uses ast-grep **0.51.0**. On this version, the discussion's original
short pattern already captures the body, including `break;`. The more specific
pattern with `$$$BODY` immediately followed by `break;` still does not match:
C/C++ parses that sequence as a declaration. Adding a semicolon creates an
`expression_statement`, so the placeholder then matches inside one expression
instead of spanning several statements.

`capture-case.yml` captures the complete case body, checks that its final direct
statement is a bare `break;`, and exposes the preceding text as `$STATEMENTS`.
It uses the existing pattern, relational-rule, and transformation settings.

## Run

Install the pinned CLI using the [official installation guidance](https://ast-grep.github.io/guide/quick-start.html),
for example with npm:

```sh
npm install --global @ast-grep/cli@0.51.0
ast-grep --version
ast-grep scan --rule capture-case.yml --json=pretty example.cpp
```

The relevant part of the result is:

```json
{
  "metaVariables": {
    "single": { "X": { "text": "123" } },
    "multi": {
      "BODY": [
        { "text": "x();" },
        { "text": "y();" },
        { "text": "break;" }
      ]
    },
    "transformed": { "STATEMENTS": "x();\ny();\n" }
  }
}
```

`BODY` contains AST nodes, including the terminal break. `STATEMENTS` is text,
with that break removed; it is not another multi-node capture. To print it:

```sh
ast-grep scan --rule capture-case.yml --json=compact example.cpp > matches.json
python3 -c 'import json; [print(m["metaVariables"]["transformed"]["STATEMENTS"], end="") for m in json.load(open("matches.json"))]'
```

The result is `x();` followed by `y();`. A scan leaves the input file unchanged.
For C, change `language: Cpp` to `language: C` and scan a `.c` file.

## Match the surrounding switch

The rule selects `case_statement`. Its `switch (0)` is parsing context, so it
does **not** constrain the enclosing switch. The two `inside` clauses check the
direct containing compound statement and its direct switch parent instead.
They do not walk past a nested switch to match a different outer switch.

The repeated `$X` intentionally requires the switch expression and case value
to have the same syntax, as in the question's first playground link. To capture
any case and retain both values, change only `case $X:` to `case $CASE:` in
`capture-case.yml`. The result then has separate `X` and `CASE` captures.
This is a syntactic comparison, not evaluation of constant expressions.

The rule includes neighboring cases and default branches in the surrounding
switch, but `BODY` belongs only to the selected case. An inner matching switch
can produce its own separate result.

## Preview the original single-switch extraction

For the discussion's single-case example, `extract-single-switch.yml` selects
the **whole switch** and provides `$STATEMENTS` as its replacement:

```sh
ast-grep scan --rule extract-single-switch.yml --json=pretty example.cpp
```

The JSON `replacement` is `x();\ny();\n`. This is a read-only preview; the rule
does not match a switch with additional cases. It demonstrates the requested
extraction, not a general semantics-preserving C/C++ refactor. Applying such a
replacement could remove switch-expression side effects or change control flow.
The branch rule intentionally has no `fix`: replacing just a case with its body
would remove its label while leaving the switch around it.

## Scope and checks

These rules cover a case directly inside the switch body, ending with a bare
`break;` (whitespace between `break` and `;` is allowed). Statements and comments
before that break are preserved, including strings containing `break;` and
breaks inside nested switches. Comments after the final break are outside the
captured case body in these grammars and are not included in the extracted text.

A braced case body, fallthrough case without a terminal break, or a break written
as `break /* comment */;` is not matched. This example does not analyze which
statements execute or infer fallthrough/control-flow behavior. The transformation
only removes the anchored terminal token sequence after the AST rule establishes
that a final break statement is present. Formatting follows ast-grep's captured
text handling and is not a byte-for-byte source export.

Run the scripted checks with Python 3.9 or later:

```sh
python3 verify.py
# Or give the installed executable explicitly:
python3 verify.py /path/to/ast-grep
```

The checks run the real CLI against temporary C and C++ files: exact original
captures and extracted text, empty/single/multiple statements, comments and
strings, neighboring cases, missing/nonterminal breaks, mismatched expressions,
nested switches, separate case variables, and whole-switch replacement preview.
They also verify that scans leave their input files unchanged.

References: [pattern syntax](https://ast-grep.github.io/guide/pattern-syntax.html),
[pattern parsing](https://ast-grep.github.io/advanced/pattern-parse.html),
[relational rules](https://ast-grep.github.io/guide/rule-config/relational-rule.html),
[transformations](https://ast-grep.github.io/reference/yaml/transformation.html).

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
