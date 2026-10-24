# Mark a commit on another branch during a LazyGit bisect

In LazyGit 0.66.2, the built-in `b` menu belongs to the main Commits view. The commit list opened from another branch is a different context, `subCommits`.

The [configuration](config.yml) adds a good/bad menu on `b` in that view. It passes the **selected commit's hash** to Git. The main Commits view keeps its built-in bisect menu.

## Add the command

Copy the entry under `customCommands` in [config.yml](config.yml) into your LazyGit configuration. If you already have a `customCommands` list, append the entry to that list. Keep your other configuration. Pick another key if you already use `b` in `subCommits`.

1. Start with a clean working tree. In the main Commits view, select the known-bad commit, press `b`, then choose **Mark … as bad (start bisect)**.
2. Open the Branches view, highlight the known-good branch, and press **Enter**, which opens its commits without checking out the branch.
3. Select the actual known-good commit, press `b`, and choose **good**. Check the hash in the menu title. Git's result appears in a popup.
4. Dismiss the popup and return to the main Commits view. Test the checked-out revision and use the built-in `b` menu to mark it good or bad. Continue until LazyGit reports the first bad commit, then confirm its reset prompt to return to the branch where the bisect started.

This uses the documented [custom-command contexts and placeholders](https://github.com/jesseduffield/lazygit/blob/v0.66.2/docs/Custom_Command_Keybindings.md#contexts). No plugin or custom LazyGit build is needed.

## Try a complete example

Requires Python 3.9+, Git 2.28+, and LazyGit. The setup creates a new local repository with synthetic text files and no remote. It refuses an existing target and changes no global Git or LazyGit settings.

```sh
python3 demo.py /tmp/branch-bisect-demo
lazygit --path /tmp/branch-bisect-demo \
  --use-config-dir /tmp/branch-bisect-settings \
  --use-config-file "$PWD/config.yml" log
```

The graph deliberately has a separate staging commit:

```text
A -- 1 -- 2 -- 3 -- 4 -- 5 -- 6 -- 7 -- 8  dev, bad
 \
  S  staging, known good
```

Revision **5** is the first bad commit.

Follow the four steps above. Start at **Development revision 08**, then select **Known-good staging side commit** in staging's commit list.

Because staging has diverged, Git first says **a merge base must be tested** and checks out **Common baseline**. Test it too; do not assume a good branch tip proves its ancestor is good. In this demo it is good. Return to the main Commits view with `4`, open `b`, and mark it good.

For each checked-out candidate, run this in a second shell:

```sh
python3 demo.py --check /tmp/branch-bisect-demo
```

Levels below 5 are good; levels 5 and above are bad. The complete sequence is baseline 0 **good**, revision 4 **good**, revision 6 **bad**, revision 5 **bad**. LazyGit should identify **Development revision 05**. Confirm reset; `dev` should be checked out again at revision 08, with `git status --short` empty.

## Boundaries and verification

- Use ordinary `good`/`bad` terms. If you started Git bisect with custom terms, change the fixed menu values to match them.
- Choose commits whose behavior you have actually tested. If the branches have no common history, or the common ancestor is bad, the assumed good-to-bad range may not exist. Read Git's diagnostic and reassess the range.
- Bisect switches tracked working-tree contents. Keep local edits committed or safely set aside before starting. The example does not stash, clean, force checkout, or delete files.
- The custom menu always marks its selected hash. During the actual search, use the main view's native menu to mark the checked-out candidate.

Verified with the official LazyGit 0.66.2 macOS arm64 binary and Git 2.39.3 in a software-operated terminal. Without the configuration, `b` in staging's commit view did not change the bisect log. With it, the exact selected staging hash was recorded, the merge base was tested, the expected first bad commit was found, and the native reset restored `dev` with a clean working tree and unchanged existing content. This is synthetic-repository validation; the original requester's repository has not been tested.

## Optional coffee

This example is free. If it saved you some time and you would like to buy me a coffee, thank you. It is entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
