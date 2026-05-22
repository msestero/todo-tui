"""Spawn a tmux window/session with Claude on the left and one shell per folder
stacked vertically on the right. Inside tmux, opens a new window. Outside tmux,
spawns a terminal emulator running a fresh attached tmux session."""
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


def _find_terminal() -> str | None:
    env = os.environ.get("TERMINAL")
    if env and shutil.which(env):
        return env
    for candidate in _TERMINAL_CANDIDATES:
        if shutil.which(candidate):
            return candidate
    return None


def _split(target: str, orientation: str, cwd: str) -> str:
    """Split `target` (window or pane id) and return the new pane's id."""
    result = subprocess.run(
        ["tmux", "split-window", orientation, "-t", target, "-c", cwd,
         "-P", "-F", "#{pane_id}"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def launch(
    folders: list[str],
    claude_session_id: str | None,
    window_name: str,
    session_name: str,
) -> None:
    """Open a tmux window/session for this task.

    Layout: left pane runs `claude` (resumes if `claude_session_id` is given);
    the right column has one shell per folder, stacked top-to-bottom.

    Inside tmux: creates a new window named `window_name` in the current session.
    Outside tmux: creates a detached tmux session named `session_name`
    (must be a valid tmux session id — no `.` or `:`) with its first window
    named `window_name`, and attaches via a freshly-spawned terminal emulator.
    """
    if not folders:
        raise ValueError("launch requires at least one folder")

    primary_folder = folders[0]
    claude_cmd = (
        f"claude --resume {shlex.quote(claude_session_id)}"
        if claude_session_id else "claude"
    )
    # Keep the pane open after claude exits so the user can read its output.
    keep_open = f"{{ {claude_cmd}; }}; exec ${{SHELL:-bash}}"

    inside_tmux = in_tmux()
    if inside_tmux:
        result = subprocess.run(
            ["tmux", "new-window", "-n", window_name, "-c", primary_folder,
             "-P", "-F", "#{window_id}",
             "bash", "-c", keep_open],
            capture_output=True, text=True, check=True,
        )
        window_target = result.stdout.strip()  # e.g. "@5"
    else:
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name, "-n", window_name,
             "-c", primary_folder,
             "bash", "-c", keep_open],
            check=True,
        )
        window_target = f"{session_name}:0"

    # First folder: right pane (shell in folders[0])
    last_pane = _split(window_target, "-h", primary_folder)
    # Stack additional folders below
    for folder in folders[1:]:
        last_pane = _split(last_pane, "-v", folder)

    # Claude takes half the window; right column shares the other half evenly.
    subprocess.run(
        ["tmux", "set-window-option", "-t", window_target, "main-pane-width", "50%"],
        check=False,
    )
    subprocess.run(["tmux", "select-layout", "-t", window_target, "main-vertical"], check=False)
    subprocess.run(["tmux", "select-pane", "-t", f"{window_target}.0"], check=False)

    if not inside_tmux:
        term = _find_terminal()
        if term is None:
            raise RuntimeError("No terminal emulator found. Set $TERMINAL.")
        if os.path.basename(term) == "gnome-terminal":
            argv = [term, "--", "tmux", "attach", "-t", session_name]
        else:
            argv = [term, "-e", "tmux", "attach", "-t", session_name]
        subprocess.Popen(argv, start_new_session=True)
