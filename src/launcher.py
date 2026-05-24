"""Spawn a tmux window/session with Claude on the left and one shell per folder
stacked vertically on the right.

Public surface:
- `launch(...)` — create a fresh window/session for a todo.
- `find_window(name)` — look up a window in the current tmux session.
- `has_session(name)` — check if a detached session exists.
- `select_window(target)` / `attach_session(name)` — switch focus to an existing one.
- `in_tmux()` — are we already inside a tmux session?

The reuse-existing-window flow (pending feature) is `find_window` / `has_session`
+ `select_window` / `attach_session`; the fresh-launch flow is `launch`.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess

_TERMINAL_CANDIDATES = [
    "alacritty",
    "kitty",
    "wezterm",
    "foot",
    "ghostty",
    "gnome-terminal",
    "konsole",
    "xterm",
]


# ---------------------------------------------------------------- low-level tmux


def _tmux(*args: str, capture: bool = False, check: bool = True) -> str:
    """Run `tmux <args>`. Returns captured stdout when `capture=True`, else ''."""
    result = subprocess.run(
        ["tmux", *args],
        capture_output=capture,
        text=True,
        check=check,
    )
    return result.stdout.strip() if capture else ""


def in_tmux() -> bool:
    return bool(os.environ.get("TMUX"))


def find_window(window_name: str) -> str | None:
    """Window id (`@N`) for a window named `window_name` in the current tmux
    session, or None. Returns None if not inside tmux."""
    if not in_tmux():
        return None
    try:
        listing = _tmux("list-windows", "-F", "#{window_name}\t#{window_id}", capture=True)
    except subprocess.CalledProcessError:
        return None
    for line in listing.splitlines():
        name, _, wid = line.partition("\t")
        if name == window_name:
            return wid
    return None


def has_session(session_name: str) -> bool:
    """True iff a detached tmux session with this exact name exists."""
    return (
        subprocess.run(
            ["tmux", "has-session", "-t", f"={session_name}"],
            capture_output=True,
        ).returncode
        == 0
    )


def select_window(target: str) -> None:
    """Switch focus to an existing window (id or `session:window`)."""
    _tmux("select-window", "-t", target)


def attach_session(session_name: str) -> None:
    """Spawn a terminal emulator attached to `session_name`. Use outside tmux."""
    _spawn_attach_terminal(session_name)


# ---------------------------------------------------------------- public: launch


def launch(
    folders: list[str],
    claude_session_id: str,
    resume: bool,
    window_name: str,
    session_name: str,
    initial_context: str | None = None,
) -> None:
    """Open a fresh tmux window/session for this task.

    Layout: left pane runs `claude` (`--resume <id>` if `resume`, else
    `--session-id <id>`); the right column has one shell per folder.

    `initial_context`, when set, is appended to claude's system prompt so the
    task/subtask info is available throughout the session without consuming a
    user turn. Passed on every launch (fresh and resume) since
    `--append-system-prompt` is per-invocation — re-injecting reflects the
    live state of the todo rather than freezing it at first launch.

    Inside tmux: creates a new window in the current session.
    Outside tmux: creates a detached session named `session_name` and spawns a
    terminal attached to it.
    """
    if not folders:
        raise ValueError("launch requires at least one folder")

    primary = folders[0]
    claude_cmd = _build_claude_cmd(claude_session_id, resume, initial_context)

    if in_tmux():
        target = _create_window_here(window_name, primary, claude_cmd)
    else:
        target = _create_detached_session(session_name, window_name, primary, claude_cmd)

    _stack_folder_panes(target, primary, folders[1:])
    _apply_main_vertical_layout(target)

    if not in_tmux():
        _spawn_attach_terminal(session_name)


# ---------------------------------------------------------------- launch helpers


def _build_claude_cmd(session_id: str, resume: bool, initial_context: str | None = None) -> str:
    flag = "--resume" if resume else "--session-id"
    parts = ["claude", flag, shlex.quote(session_id)]
    if initial_context:
        parts += ["--append-system-prompt", shlex.quote(initial_context)]
    cmd = " ".join(parts)
    # Keep the pane open after claude exits so the user can read its output.
    return f"{{ {cmd}; }}; exec ${{SHELL:-bash}}"


def _create_window_here(name: str, cwd: str, cmd: str) -> str:
    """Create a window in the current tmux session. Returns its id (`@N`)."""
    return _tmux(
        "new-window", "-n", name, "-c", cwd,
        "-P", "-F", "#{window_id}",
        "bash", "-c", cmd,
        capture=True,
    )  # fmt: skip


def _create_detached_session(session: str, window_name: str, cwd: str, cmd: str) -> str:
    """Create a detached session with one window. Returns `session:0`."""
    _tmux(
        "new-session", "-d", "-s", session, "-n", window_name, "-c", cwd,
        "bash", "-c", cmd,
    )  # fmt: skip
    return f"{session}:0"


def _stack_folder_panes(window_target: str, primary: str, extras: list[str]) -> None:
    """Split off a right pane in `primary`, then stack `extras` vertically below."""
    anchor = _split_pane(window_target, "-h", primary)
    for folder in extras:
        anchor = _split_pane(anchor, "-v", folder)


def _split_pane(target: str, orientation: str, cwd: str) -> str:
    """Split `target` (window or pane id) and return the new pane's id."""
    return _tmux(
        "split-window", orientation, "-t", target, "-c", cwd,
        "-P", "-F", "#{pane_id}",
        capture=True,
    )  # fmt: skip


def _apply_main_vertical_layout(window_target: str) -> None:
    """Claude takes the main (left) pane at 50%; right column shares evenly."""
    _tmux("set-window-option", "-t", window_target, "main-pane-width", "50%", check=False)
    _tmux("select-layout", "-t", window_target, "main-vertical", check=False)
    _tmux("select-pane", "-t", f"{window_target}.0", check=False)


# ---------------------------------------------------------------- terminal spawn


def _find_terminal() -> str | None:
    env = os.environ.get("TERMINAL")
    if env and shutil.which(env):
        return env
    for candidate in _TERMINAL_CANDIDATES:
        if shutil.which(candidate):
            return candidate
    return None


def _spawn_attach_terminal(session_name: str) -> None:
    term = _find_terminal()
    if term is None:
        raise RuntimeError("No terminal emulator found. Set $TERMINAL.")
    if os.path.basename(term) == "gnome-terminal":
        argv = [term, "--", "tmux", "attach", "-t", session_name]
    else:
        argv = [term, "-e", "tmux", "attach", "-t", session_name]
    subprocess.Popen(argv, start_new_session=True)
