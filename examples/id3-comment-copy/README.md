# Keep an imported ID3v1 comment out of a converted copy

`mid3iconv --remove-v1` can remove the on-disk ID3v1 tag while leaving an “ID3v1 Comment” in ID3v2. Mutagen's default load merges v1 fields into its v2-style view. Comments with different descriptions or languages have different keys, so a full Japanese comment and a shorter English-labelled fallback can coexist. The converter loads that merged view, then saves it; removing the v1 tail does not undo the earlier import.

This example shows which comments are actually in v2 and which are imported from v1. If you choose to omit an imported comment, it prepares a **new copy**, retains the other loaded metadata on supported inputs, and leaves encoding conversion to the official `mid3iconv` command. It uses public ID3 APIs and changes no library behavior.

Requires Python 3.10+; tested with Python 3.12 and Mutagen 1.48.1.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest -v
python demo.py demo-output
```

Run these commands from this directory. Use a new demo directory each time. The demo creates its own tags and silent MPEG frames, reproduces the imported-comment behavior with the real converter, then checks a complete preparation and Shift-JIS conversion. The JSON result shows the original unchanged, the media bytes preserved, the selected comment absent, and the work-note field converted to `作業メモ`. It uses no downloaded music.

## Inspect your original first

```sh
python id3_comment_copy.py inspect original.mp3
```

Each comment includes its exact `key`, language, description, text and `in_v2` flag. For example:

```json
{
  "key": "COMM:ID3v1 Comment:eng",
  "language": "eng",
  "description": "ID3v1 Comment",
  "text": ["Short legacy note"],
  "in_v2": false
}
```

`in_v2: false` means this key appears only in the merged read. It does **not** prove the comment is unwanted or duplicate. Read its content and choose deliberately. `has_v1` checks the conventional `TAG` marker 128 bytes from the end; `in_v2` comes from a separate `load_v1=False` read.

## Prepare and convert a separate copy

Use the exact imported key from your inspection. The example below uses the synthetic fixture's key; your file may differ.

```sh
python id3_comment_copy.py prepare original.mp3 converted.mp3 \
  --drop-imported-comment 'COMM:ID3v1 Comment:eng'
```

The output must not exist. Preparation requires an actual v2.3/v2.4 header and removes only the explicitly selected imported `COMM` key. It retains the other loaded fields on supported inputs, including title, artist or track fields found only in v1, then saves v2.4 without a v1 tail. The original stays unchanged. Serialization, padding and the v2 version may change in the copy.

Preparation refuses inputs whose metadata it cannot preserve safely. In particular, automatic v2.4 translation can discard v2.3 fields such as `TSIZ`, `RVAD`, `EQUA` or `TRDA`; it can also rename date/people fields. This recipe conservatively refuses those changes, unrecognized frames, and loaded values that fail a v2.4 serialization check, before creating an output. Keep the original and diagnose its version-specific metadata separately. Ordinary v2.3 fields that pass these checks remain supported.

Then choose the encoding that produced your original incorrectly labelled tag bytes. For the demo it is `shift_jis`; **do not assume that is right for another file**.

```sh
mid3iconv -e shift_jis --dry-run --debug converted.mp3
mid3iconv -e shift_jis --remove-v1 converted.mp3
python id3_comment_copy.py inspect converted.mp3
```

Preparation does not convert text. `mid3iconv` converts the copied legacy fields to Unicode. The final inspection should retain the full main comment and the other wanted fields, with the selected imported comment absent. Check your actual metadata before replacing any original; these scripts never replace it.

An already-converted file may have the same comment physically stored in v2. The command refuses that selection: its origin can no longer be established from a merged-read difference. Compare an unmodified original and diagnose that physical v2 frame separately. V1-only sources are also refused by this omission recipe. It does not decide which of your metadata to retain.

## Verification and scope

The scripted tests run the actual converter, check Shift-JIS text repair, both main and separate v2 comments, v1-only fallback title/artist/track, album precedence, a custom text field, picture/private-frame bytes, a URL, source bytes and the complete MPEG payload. They also cover repeated conversion/inspection and refusal of lossy version-specific/unknown-frame inputs, v1-only sources, absent/non-comment keys, physical-v2 selections, existing outputs, source aliases and symlinks.

Verified with synthetic files on Mutagen 1.48.1. The linked song and original application have not been tested. Actual file contents and source encoding still need inspection. Repeated conversion is checked for this fixture; arbitrary encodings and already-correct Latin-1 text still require inspection.

Official references: [`ID3.load` / `ID3.save`](https://mutagen.readthedocs.io/en/latest/api/id3.html), [`mid3iconv` options](https://mutagen.readthedocs.io/en/latest/man/mid3iconv.html), [1.48.1 converter source](https://github.com/quodlibet/mutagen/blob/release-1.48.1/mutagen/_tools/mid3iconv.py), [stable release](https://pypi.org/project/mutagen/1.48.1/). Mutagen is a separate GPL-2.0-or-later dependency; this example contains no copied converter implementation.

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
