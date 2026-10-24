# JSON authoring with per-string Weblate flags

Keep the JSON authoring records in your repository, and use standard **PO files as the Weblate interchange format**. This is an extract/compile alternative; it does not add a native Weblate JSON format.

For each stable JSON key, the extractor writes:

| JSON record | PO representation |
| --- | --- |
| Key | `msgctxt` |
| `defaultMessage` | `msgid` |
| `description` | Extracted comment |
| `weblateFlags` | Per-message flags |
| Translation | `msgstr` |

For example:

```json
{
  "docs.guide": {
    "defaultMessage": "Read **this** before continuing.",
    "description": "Introductory documentation; keep the emphasis.",
    "weblateFlags": ["md-text"]
  },
  "legacy.items": {
    "defaultMessage": "Items: {0}",
    "description": "Legacy item count.",
    "weblateFlags": ["java-format"]
  }
}
```

In Weblate 2026.10.1, **`java-format` is the flag for the Java MessageFormat check**. `java-messageformat` is not its enabling flag. The example uses one PO component with different flags on individual messages; it does not require splitting components or encoding the message type in its key.

## Extract and compile

Requires Python 3.12+ and GNU gettext's `msgmerge` for source updates.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python catalog.py extract messages.json messages.pot
python catalog.py compile messages.json locales/de.po de.json
```

The included German PO is a synthetic example. The compiled JSON retains each key, description, flags and any other JSON metadata, replacing `defaultMessage` with the translation. The English authoring file remains unchanged. Your application can consume those messages or adapt the result in its existing compile step; this example does not configure a particular legacy framework.

All output paths passed to the Python commands must be new: they refuse to overwrite an existing source or destination. GNU `msgmerge` has its own output behavior; use a new path for its merged file too. This recipe supports one singular PO entry per JSON key and simple, unparameterized flag names. It does not convert gettext plural entries or implement every possible Weblate metadata field.

A corresponding Weblate component uses:

| Setting | Value |
| --- | --- |
| File format | GNU gettext PO file |
| File mask | `locales/*.po` |
| Template for new translations | `locales/messages.pot` |
| Source language | English |

Keep the generated template at that path, translate the PO files using Weblate's existing workflow, then compile the returned PO. This retains PO as an additional repository format, which is the tradeoff for using the existing reader and checks.

## Update source messages

Extract a new template, let GNU `msgmerge` handle source matching and translation state, then reapply the JSON-owned flags:

```sh
python catalog.py extract messages-v2.json messages-v2.pot
msgmerge --previous --no-wrap -o merged.po locales/de.po messages-v2.pot
python catalog.py refresh-flags messages-v2.json merged.po refreshed.po
```

The refresh step matters: the tested GNU gettext 0.22.5 drops custom `md-text` flags during merging. The step also makes additions/removals of simple JSON flags explicit, while preserving `fuzzy` and the translations chosen by `msgmerge`. It does not implement its own fuzzy matching.

Review changed or empty translations in Weblate before compiling. `compile` refuses fuzzy, empty, missing or duplicate entries, source mismatches and missing required flags. It writes no output when these checks fail. Unchanged translations remain in the merged file; a changed source can retain its old translation with a previous-source record and `fuzzy` state.

Run the full extract → merge → refresh sequence for every authoring change, including changes only to descriptions or flags. `compile` checks required flags but does not synchronize PO metadata, reject extra stale flags or run Weblate's format checks itself; retain the normal Weblate review/check step.

## Verified behavior and limits

The optional native validation uses Weblate **2026.10.1** and Translate Toolkit **3.20.0**. In a separate virtual environment:

```sh
python3 -m venv .venv-native
. .venv-native/bin/activate
pip install --no-deps -r requirements-native.txt
python verify.py
```

This is a pinned environment for the selected parser/check imports, not a complete Weblate server installation. Do not use it to deploy Weblate. The converter itself only needs `requirements.txt`.

The checks load the real `PoFormat`/`PoUnit`, set translations through its methods, save and reload through Weblate, and execute the real Markdown syntax and Java MessageFormat checks. An external call trace confirms the checking methods ran. Broken emphasis and a changed `{0}` placeholder fail; unflagged plain text is skipped. Removing flags or omitting check calls makes acceptance fail.

The source-update test runs actual `msgmerge`, preserves existing translations and descriptions, refreshes flags, rejects fuzzy output, then produces exact JSON after the changed translation is supplied. Duplicate JSON keys, invalid metadata and overwriting an existing output are rejected.

These are scripted file-format and check tests with a small check context, not a Weblate database/UI session, a Hosted Weblate deployment or validation in the original project. Only the two named check types are exercised. GNU gettext 0.22.5 and CPython 3.12.4 on macOS arm64 were used.

References: [Weblate PO support](https://docs.weblate.org/en/latest/formats/gettext.html), [Weblate flags](https://docs.weblate.org/en/latest/admin/checks.html#customizing-behavior-using-flags), [motivating discussion](https://github.com/orgs/WeblateOrg/discussions/22266).

## Optional coffee

If this example saves you some time, you're welcome to buy me a coffee. It is entirely optional; the example stays free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
