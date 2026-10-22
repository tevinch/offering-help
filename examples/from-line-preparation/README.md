# Keep the first From match in each file

`prepare.sh` prefixes `>` to every line starting with `From` except the first such line **in each input file**. It writes new copies, then combines them in the order supplied. The original files are unchanged.

This addresses the text-processing workflow in [sd issue 358](https://github.com/chmln/sd/issues/358). sd 1.1.0 has a maximum replacement count, but no negative count or skip-first option. A separate Perl invocation per file gives each file its own counter:

```sh
perl -pe 'BEGIN { binmode STDIN; binmode STDOUT; $seen = 0 }
    s/^From/>From/ if /^From/ && ++$seen > 1' < one.txt > one-prepared.txt
```

Use a new output filename for that command. The included script adds destination checks and handles several files:

```sh
bash prepare.sh prepared ./one.txt ./two.txt
```

Requires Bash and Perl. `prepared` must not already exist; input basenames must be distinct. Quote paths containing spaces. The result is:

```text
prepared/
  parts/one.txt
  parts/two.txt
  combined.txt
```

Each `parts` file preserves all original bytes except the inserted `>` characters, including CRLF and a missing final newline. `combined.txt` adds an LF after any nonempty part that lacks one; otherwise the following file's first `From` could end up halfway through a line. Empty files contribute no bytes. An error leaves any already-created copies for inspection; the script does not delete them or overwrite an existing destination.

For example, given two files:

```text
# one.txt
From first@example.test Thu Oct 22 10:00:00 2026
Subject: One

From the body

# two.txt
From second@example.test Thu Oct 22 11:00:00 2026
Subject: Two

From another body
```

Their envelope lines stay unchanged and their body matches become `>From the body` and `>From another body`. A subsequent splitter using `^From` sees two records.

The rule is exactly `^From`: it also matches `From:` and `Fromage`. It leaves the first matching line wherever that line occurs, and leaves already quoted `>From` lines alone. Running it again **on the separate parts** is idempotent. Do not run it on an already combined mailbox: that would retain only the combined file's first unquoted match.

This is the requested text preparation, not a general `.eml`-to-mbox converter. For mail, use it only when each file already contains the intended first separator and its format matches your downstream splitter. Conventional separators start with `From `, including the space; `From:` is an email header. mbox variants also differ in quoting and message termination, and mboxrd escapes existing quoted `From ` lines too. No envelope lines, headers or canonical blank-line terminators are created here. See [RFC 4155](https://www.rfc-editor.org/rfc/rfc4155.html) before choosing a mailbox-specific transformation.

Run the synthetic checks with Python 3:

```sh
python3 test_prepare.py
```

The checks run the real Bash/Perl commands, compare exact output and unchanged inputs, split the combined output into the expected records, repeat the transformation, and cover empty/no-match files, raw bytes, CRLF, missing final newlines, spaces in paths and output collisions. Verified with Bash 3.2 and Perl 5.34.1 on macOS. No real mail is used.

## Optional coffee

This example is free. If it saved you time and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
