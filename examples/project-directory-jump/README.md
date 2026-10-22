# Jump within a tmux session's project

Keep project searches inside a fixed directory even when another project has more frequently visited directories with the same names. The Bash/Zsh functions `pz` and `pzi` use a `PROJECT_ROOT` environment variable and zoxide's existing `query --base-dir` option.

For example, `pz sub target` jumps to a matching directory inside the session's project. `pzi target` shows an interactive fzf selection from that project. The usual `z` and `zi` commands remain available.

## Setup

Requires zoxide 0.10.0, Bash or Zsh, and tmux. Interactive selection also requires fzf. First set up zoxide's normal shell integration according to its [official instructions](https://github.com/ajeetdsouza/zoxide#installation), so visited directories enter its database.

Download `project-jump.sh` from this directory, review it, and source it in each shell where you want the commands. For example, after zoxide initialization in your Bash or Zsh startup file:

```sh
source /absolute/path/to/project-jump.sh
```

Use absolute project paths and distinct session names:

```sh
tmux new-session -d -s alpha -c "/work/alpha project" \
    -e "PROJECT_ROOT=/work/alpha project"
tmux new-session -d -s beta -c "/work/beta project" \
    -e "PROJECT_ROOT=/work/beta project"
tmux attach-session -t alpha
```

Inside alpha, after visiting some directories:

```sh
pz target
pwd
pzi target
```

Both searches are restricted to alpha's root. A new pane in beta inherits beta's root. Each root is fixed for the session, so moving deeper inside a project does not narrow the search to the current subdirectory.

`PROJECT_ROOT` is this example's setting; zoxide does not read it itself. The actual option in 0.10.0 is `--base-dir`, with a hyphen. These helpers pass it on every search. Direct `zoxide query` calls and other integrations keep their own behavior.

## Existing sessions and child shells

For a session that already exists, set its environment for future panes:

```sh
tmux set-environment -t alpha PROJECT_ROOT "/work/alpha project"
```

That does not change a shell which is already running. In such a shell, set and export its root too:

```sh
export PROJECT_ROOT="/work/alpha project"
source /absolute/path/to/project-jump.sh
```

Children inherit the exported root. An interactive child needs the same startup-file setup; a noninteractive shell must source the helper explicitly. There is no need to use tmux's global environment. Avoid adding `PROJECT_ROOT` to `update-environment`, which can replace a session value when you attach from another shell. See tmux's [global and session environment documentation](https://github.com/tmux/tmux/blob/3.8/tmux.1#L7861) for the inheritance model.

## Behavior

The helper uses the existing zoxide database and respects `_ZO_EXCLUDE_DIRS` and the usual interactive fzf options. It does not import directories or create a second database. If the database has no matching in-project directory, visit that directory normally first. No match, an unset/invalid root, a cancelled selection, or a selected symlink resolving outside the root leaves the current directory unchanged.

These are keyword-search commands: `pz` with no keywords picks the highest-ranked in-project entry. They do not reproduce `z`'s special handling of home, `-`, or direct paths, and they have no custom completion setup. The helper resolves selected paths to their physical directories. It does not change existing shell settings or install itself.

## Run the checks

With zoxide, tmux, fzf, Bash and Python 3 on `PATH`:

```sh
python3 test_project_jump.py
```

The tests create a private tmux socket, temporary home/configuration, synthetic project directories and a temporary zoxide database. They terminate only that test server. No existing tmux session, shell startup file or zoxide database is used.

The checks give beta the higher global score, then verify actual directory changes inside both sessions, a new pane and a child shell. They verify that the normal zoxide prompt hook records a newly visited directory. A real fzf instance waits for input, receives a selection and changes the pane's directory. Missing matches, exclusions, similarly named sibling projects, spaces and outside-project symlinks are covered too.

Verified through scripted shell and terminal checks with zoxide 0.10.0, tmux 3.8, fzf 0.74.5, Bash 3.2 and Zsh 5.9 on macOS. The tmux/fzf interaction is tested in Bash; the helper's noninteractive behavior is tested in both shells.

## Optional coffee

This example is free. If it saved you time and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
