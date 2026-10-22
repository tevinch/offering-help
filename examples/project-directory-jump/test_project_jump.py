"""Real zoxide, tmux and fzf checks; uses only temporary files and a private socket."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest

HELPER = Path(__file__).with_name("project-jump.sh").resolve()


class ProjectJumpTests(unittest.TestCase):
    def setUp(self):
        for command in ("zoxide", "tmux", "fzf", "bash"):
            if shutil.which(command) is None:
                self.fail(f"Install {command} and put it on PATH before running this test")
        self.temp = tempfile.TemporaryDirectory(prefix="pj-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.alpha = self.root / "alpha project"
        self.beta = self.root / "beta project"
        self.sibling = self.root / "alpha project-copy"
        for root in (self.alpha, self.beta, self.sibling):
            (root / "sub" / "target").mkdir(parents=True)
        self.env = dict(os.environ, HOME=str(self.home), _ZO_DATA_DIR=str(self.root / "database"),
                        LC_ALL="C", LANG="C", TERM="xterm-256color")
        for name in ("TMUX", "TMUX_PANE", "_ZO_EXCLUDE_DIRS", "_ZO_FZF_OPTS", "FZF_DEFAULT_OPTS", "FZF_DEFAULT_COMMAND", "PROJECT_ROOT", "BASH_ENV", "ENV", "ZDOTDIR"):
            self.env.pop(name, None)
        self.env["_ZO_RESOLVE_SYMLINKS"] = "1"
        for root, visits in ((self.alpha, 1), (self.beta, 8), (self.sibling, 4)):
            for _ in range(visits):
                self.run_command("zoxide", "add", str(root / "sub" / "target"))

    def run_command(self, *args, check=True, **kwargs):
        return subprocess.run(args, env=self.env, text=True, capture_output=True, check=check, **kwargs)

    def test_shell_scope_failures_and_existing_exclusions(self):
        self.assertEqual(self.run_command("zoxide", "query", "target").stdout.strip(), str(self.beta / "sub" / "target"))
        for shell in ("bash", "zsh"):
            if not shutil.which(shell):
                continue
            # zoxide removes excluded entries when it saves the database.
            self.run_command("zoxide", "add", str(self.alpha / "sub" / "target"))
            script = 'source "$1"; export PROJECT_ROOT="$2"; pz target || exit; pwd -P'
            result = self.run_command(shell, "-f" if shell == "zsh" else "--noprofile", "-c", script, "check", str(HELPER), str(self.alpha))
            self.assertEqual(result.stdout.strip(), str(self.alpha / "sub" / "target"))
            for setup, word in (("unset PROJECT_ROOT", "target"),
                                ("export PROJECT_ROOT=relative/path", "target"),
                                ("export PROJECT_ROOT=/does-not-exist", "target"),
                                ('export PROJECT_ROOT="$2"', "unmatched-word"),
                                ('export PROJECT_ROOT="$2"; export _ZO_EXCLUDE_DIRS="$2/sub/target"', "target")):
                script = 'source "$1"; ' + setup + '; before=$PWD; if pz "$3"; then exit 99; fi; [ "$PWD" = "$before" ]'
                result = self.run_command(shell, "-f" if shell == "zsh" else "--noprofile", "-c", script, "check", str(HELPER), str(self.alpha), word, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_symlink_cannot_change_into_another_project(self):
        link = self.alpha / "outside-link"
        link.symlink_to(self.beta / "sub" / "target", target_is_directory=True)
        self.env["_ZO_RESOLVE_SYMLINKS"] = "0"
        self.run_command("zoxide", "add", str(link))
        script = 'source "$1"; export PROJECT_ROOT="$2"; before=$PWD; if pz outside-link; then exit 99; fi; [ "$PWD" = "$before" ]'
        result = self.run_command("bash", "--noprofile", "-c", script, "check", str(HELPER), str(self.alpha), check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("resolves outside PROJECT_ROOT", result.stderr)

    def test_two_tmux_sessions_new_pane_child_and_interactive_choice(self):
        socket = self.root / "tmux.sock"
        config = self.root / "tmux.conf"
        config.write_text('set -g update-environment ""\nset -g status off\n')
        rc = self.home / "bashrc"
        rc.write_text('PS1="READY> "\neval "$(zoxide init bash --hook pwd)"\n'
                      + "source " + shlex.quote(str(HELPER)) + "\n"
                      + "printf 'loaded\\n' > " + shlex.quote(str(self.root / "rc-")) + '"$TMUX_PANE"\n'
                      + '__record_prompt() { printf "%s\\n" "$PWD" > ' + shlex.quote(str(self.root / "prompt-")) + '"$TMUX_PANE"; }\n'
                      + 'PROMPT_COMMAND="${PROMPT_COMMAND};__record_prompt"\n')

        def tmux(*args, check=True):
            return self.run_command("tmux", "-S", str(socket), "-f", str(config), *args, check=check)

        self.addCleanup(lambda: tmux("kill-server", check=False))

        def wait_file(path, expected=None):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if path.exists() and path.stat().st_size:
                    text = path.read_text()
                    if expected is None or text == expected:
                        return text
                time.sleep(0.03)
            self.fail(f"No result at {path}; panes:\n{tmux('capture-pane', '-p', '-t', 'alpha').stdout}")

        def send(pane, command):
            tmux("send-keys", "-t", pane, "-l", command)
            tmux("send-keys", "-t", pane, "Enter")

        panes = {}
        for name, project in (("alpha", self.alpha), ("beta", self.beta)):
            pane = tmux("new-session", "-d", "-P", "-F", "#{pane_id}", "-x", "100", "-y", "30", "-s", name,
                        "-e", f"PROJECT_ROOT={project}", "-c", str(project),
                        shutil.which("bash"), "--noprofile", "--rcfile", str(rc), "-i").stdout.strip()
            panes[name] = pane
            self.assertEqual(wait_file(self.root / ("rc-" + pane)), "loaded\n")
            output = self.root / (name + "-jump")
            send(pane, "pz target && pwd -P > " + shlex.quote(str(output)))
            self.assertEqual(wait_file(output).strip(), str(project / "sub" / "target"))
            self.assertEqual(tmux("show-environment", "-t", name, "PROJECT_ROOT").stdout.strip(), f"PROJECT_ROOT={project}")

        pane = tmux("split-window", "-d", "-P", "-F", "#{pane_id}", "-t", "alpha", "-c", str(self.alpha),
                    shutil.which("bash"), "--noprofile", "--rcfile", str(rc), "-i").stdout.strip()
        self.assertEqual(wait_file(self.root / ("rc-" + pane)), "loaded\n")
        child = self.root / "child-jump"
        child_script = 'source "$1"; pz target && printf "%s\\n%s\\n" "$PROJECT_ROOT" "$PWD"'
        send(pane, "bash --noprofile -c " + shlex.quote(child_script) + " child " + shlex.quote(str(HELPER)) + " > " + shlex.quote(str(child)))
        self.assertEqual(wait_file(child).splitlines(), [str(self.alpha), str(self.alpha / "sub" / "target")])

        # Prove the real prompt hook ran: this path was not seeded into the DB.
        visited = self.alpha / "only-visited-by-hook"
        visited.mkdir()
        marker = self.root / "visited"
        send(pane, "cd " + shlex.quote(str(visited)) + " && printf yes > " + shlex.quote(str(marker)))
        wait_file(marker)
        # Wait until the prompt has completed its hook before reading the DB.
        wait_file(self.root / ("prompt-" + pane), str(visited) + "\n")
        result = self.run_command("zoxide", "query", "only-visited-by-hook", check=False)
        self.assertEqual(result.stdout.strip(), str(visited))

        # Real fzf in a pane: two alpha choices, while beta has higher global score.
        choice = self.alpha / "other" / "target"
        choice.mkdir(parents=True)
        self.run_command("zoxide", "add", str(choice))
        interactive = self.root / "interactive-jump"
        send(pane, "pzi target && pwd -P > " + shlex.quote(str(interactive)))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            display = tmux("capture-pane", "-p", "-t", pane).stdout
            if "other/target" in display and "sub/target" in display:
                break
            time.sleep(0.03)
        self.assertIn("other/target", display)
        self.assertIn("sub/target", display)
        self.assertFalse(interactive.exists(), "selection must await real input")
        tmux("send-keys", "-t", pane, "-l", "other/target")
        tmux("send-keys", "-t", pane, "Enter")
        self.assertEqual(wait_file(interactive).strip(), str(choice))
        self.assertEqual(tmux("display-message", "-p", "-t", pane, "#{pane_current_path}").stdout.strip(), str(choice))


if __name__ == "__main__":
    unittest.main(verbosity=2)
