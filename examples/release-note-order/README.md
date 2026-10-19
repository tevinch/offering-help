# Reverse generated release-note entries

Put the last supplied change first when a release viewer shows old changes above recent ones. This small Python script reverses the flat PR list under `## What's Changed`, preserving the warning, contributor credits and Full Changelog outside that list.

It reverses the supplied sequence. It does not look up merge dates or sort by PR number; use it when the incoming sequence is the opposite of your desired display order.

## Try it locally

Python 3.9 or newer is sufficient; there are no package dependencies. From this directory:

```sh
python3 -m unittest -v
python3 reverse_notes.py sample.md ordered.md
```

The sample's first change becomes PR 21 and its last becomes PR 12. The input is unchanged. The output must be a new file; an existing file, directory or symlink is refused, including the input path itself. Use a different output name for another run.

The supported input is UTF-8 with exactly one `## What's Changed` heading and a contiguous list of GitHub's single-line entries:

```md
* Change title by @author in https://github.com/owner/repo/pull/123
```

Blank lines around the list are retained. An optional `## New Contributors` or `**Full Changelog**: ` suffix is retained verbatim. LF, CRLF and the presence or absence of the final newline are preserved. Zero or one entries are unchanged. Categories, multiline/nested entries, other list markers, missing/duplicate headings and unrecognized content in the change block fail with a nonzero exit status before creating an output. This is a narrow generated-note format, so review the generated file before adopting a new note layout.

## Use with action-gh-release

The action's [`body_path` input](https://github.com/softprops/action-gh-release/tree/v3.0.3#-external-release-notes) accepts the transformed file. With generation enabled, [v3.0.3 passes through GitHub's generated body](https://github.com/softprops/action-gh-release/blob/v3.0.3/src/github.ts); `append_body` controls concatenation of old and new bodies, not the order of change entries. GitHub's [note configuration](https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes) provides exclusions and categories but no documented order setting.

Copy this directory into your repository as `release-note-order/`. Adapt the two steps in [workflow.yml](workflow.yml) after your existing checkout/build steps:

1. Keep your existing release token, permissions, event guard and asset/name/release settings. The example reuses `secrets.GITHUB_TOKEN` and adds no permission grant or login step. It requires Bash, `gh` and `python3` on the runner; check those commands on your runner, including Windows runners.
2. Match `RELEASE_TAG` and the action's `tag_name`. Match `RELEASE_TARGET` to the target of your existing release. For an existing release without an explicit `target_commitish`, inspect its current target; the example uses `main`. For a new release with no explicit target, leave it empty to retain GitHub's default. Copy any explicit `previous_tag` into `PREVIOUS_TAG`, otherwise leave it empty. This recipe does not change your moving-tag or comparison-baseline policy.
3. Copy your current `body`/warning verbatim into `NOTES_PREAMBLE` (use a YAML `|` block for multiple lines). The file must contain it: `body_path` takes precedence over a separate `body` input. The example joins a nonempty preamble and fresh notes with two LF characters, matching the action's generation path; all content after that assembly is preserved outside the reversed entries.
4. Generate notes afresh for each build with the [generate-notes endpoint](https://docs.github.com/en/rest/releases/releases#generate-release-notes-content-for-a-release). The example extracts the JSON body with Python's standard library, combines the preamble, then runs the CLI. It does not reuse a previously published release body. The endpoint generates text; the later action step publishes the release in your existing workflow.
5. Pass that new file through `body_path` with `generate_release_notes: false` so a second generated list is not added. Keep `append_body: false` to replace the prior body on subsequent updates, and retain your other existing action inputs.

Local checks cover the CLI, a 99-entry public release body with its surrounding text, and adoption from a fresh copy. The workflow shell was exercised locally with two controlled API responses and the real extraction/CLI steps. The API invocation was replaced for that check. The original hosted CI, original updater, a new release publication and requester adoption have **not** been tested. Inspect the produced Markdown and your viewer before using the workflow to publish.

## Optional coffee

This example is free. If it saved you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
