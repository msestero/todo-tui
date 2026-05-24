"""Tests for the pieces of launcher.py that don't need a live tmux.

The orchestration paths (`launch`, `find_window`, etc.) shell out to tmux and
are smoke-tested manually via the `c` keybinding. Here we cover only the pure
helpers and constants — the bits that change shape when we evolve the API.
"""

from __future__ import annotations

import launcher
from launcher import _build_claude_cmd


def test_build_claude_cmd_uses_session_id_when_not_resuming():
    cmd = _build_claude_cmd("abc-uuid", resume=False)
    assert "claude --session-id" in cmd
    assert "abc-uuid" in cmd


def test_build_claude_cmd_uses_resume_when_resuming():
    cmd = _build_claude_cmd("abc-uuid", resume=True)
    assert "claude --resume" in cmd
    assert "abc-uuid" in cmd


def test_build_claude_cmd_quotes_session_id():
    """Shell-quote the session id so a malicious or weird value can't break out."""
    cmd = _build_claude_cmd("a; rm -rf /", resume=False)
    # The dangerous substring should appear only inside single quotes.
    assert "'a; rm -rf /'" in cmd or "'a;\\ rm\\ -rf\\ /'" in cmd


def test_build_claude_cmd_keeps_pane_open_after_claude_exits():
    cmd = _build_claude_cmd("x", resume=False)
    # The trailing `exec $SHELL` is what keeps the pane alive.
    assert "exec ${SHELL:-bash}" in cmd


def test_public_api_is_exposed():
    """Lock in the public surface so the reuse-existing-window feature has
    stable hooks to call into."""
    for name in (
        "launch",
        "find_window",
        "has_session",
        "select_window",
        "attach_session",
        "in_tmux",
    ):
        assert hasattr(launcher, name), f"launcher.{name} is missing"
