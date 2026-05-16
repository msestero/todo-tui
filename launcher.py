"""Spawn terminal sessions for Claude, tmux-aware.

Inside tmux: opens a new window (or a split pane if TODO_TUI_TMUX_SPLIT is
set). Outside tmux: opens a standalone terminal emulator window.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess


# Terminal emulators tried, in order, when $TERMINAL is unset or not found.
_TERMINAL_CANDIDATES = [
    "alacritty", "kitty", "wezterm", "foot", "ghostty",
    "gnome-terminal", "konsole", "xterm",
]


def in_tmux() -> bool:
    return bool(os.environ.get("TMUX"))


def _tmux_window_exists(name: str) -> bool:
    result = subprocess.run(
        ["tmux", "list-windows", "-F", "#{window_name}"],
        capture_output=True, text=True,
    )
    return result.returncode == 0 and name in result.stdout.split()


def _find_terminal() -> str | None:
    env = os.environ.get("TERMINAL")
    if env and shutil.which(env):
        return env
    for candidate in _TERMINAL_CANDIDATES:
        if shutil.which(candidate):
            return candidate
    return None


def open_session(
    cwd: str,
    shell_command: str,
    *,
    window_name: str | None = None,
    reuse: bool = False,
) -> str | None:
    """Run `shell_command` in a new terminal context with `cwd` as its directory.

    The command is followed by an interactive shell so the window stays open
    after the command exits. If `reuse` is set and a tmux window named
    `window_name` already exists, switches to it instead of spawning a new one.

    Returns the tmux window name when run inside tmux, else None.
    Raises RuntimeError if no terminal emulator can be found (non-tmux only).
    """
    wrapped = f"cd {shlex.quote(cwd)} && {{ {shell_command}; }}; exec ${{SHELL:-bash}}"

    if in_tmux():
        if reuse and window_name and _tmux_window_exists(window_name):
            subprocess.run(["tmux", "select-window", "-t", window_name])
            return window_name
        verb = "split-window" if os.environ.get("TODO_TUI_TMUX_SPLIT") else "new-window"
        args = ["tmux", verb, "-c", cwd]
        if window_name and verb == "new-window":
            args += ["-n", window_name]
        args += ["bash", "-c", wrapped]
        subprocess.run(args)
        return window_name

    term = _find_terminal()
    if term is None:
        raise RuntimeError("No terminal emulator found. Set $TERMINAL.")
    if os.path.basename(term) == "gnome-terminal":
        argv = [term, f"--working-directory={cwd}", "--", "bash", "-c", wrapped]
    else:
        argv = [term, "-e", "bash", "-c", wrapped]
    subprocess.Popen(argv, start_new_session=True)
    return None
