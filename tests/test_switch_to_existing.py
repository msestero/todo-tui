"""Tests for the reuse-existing-window dispatch in TodoApp._switch_to_existing.

We can't instantiate TodoApp without a Textual event loop, so we call the
method on a SimpleNamespace with a notify stub. The launcher primitives are
monkeypatched so no real tmux is needed.
"""

from __future__ import annotations

from types import SimpleNamespace

import launcher
from app import TodoApp
from todo_item import Todo


def _fake_self() -> SimpleNamespace:
    notes: list[tuple[str, str]] = []

    def notify(msg, severity="information"):
        notes.append((msg, severity))

    ns = SimpleNamespace(notify=notify)
    ns._notes = notes
    return ns


def test_returns_false_when_inside_tmux_and_window_missing(monkeypatch):
    monkeypatch.setattr(launcher, "in_tmux", lambda: True)
    monkeypatch.setattr(launcher, "find_window", lambda name: None)
    owner = Todo.new("t")
    assert TodoApp._switch_to_existing(_fake_self(), "t", "todo-x", owner) is False


def test_switches_to_existing_window_inside_tmux(monkeypatch):
    selected: list[str] = []
    monkeypatch.setattr(launcher, "in_tmux", lambda: True)
    monkeypatch.setattr(launcher, "find_window", lambda name: "@7")
    monkeypatch.setattr(launcher, "select_window", lambda target: selected.append(target))
    owner = Todo.new("Ship it")
    ns = _fake_self()
    assert TodoApp._switch_to_existing(ns, "Ship it", "todo-abc", owner) is True
    assert selected == ["@7"]
    assert any("Switched to: Ship it" in m for m, _ in ns._notes)


def test_returns_false_when_outside_tmux_and_session_missing(monkeypatch):
    monkeypatch.setattr(launcher, "in_tmux", lambda: False)
    monkeypatch.setattr(launcher, "has_session", lambda name: False)
    owner = Todo.new("t")
    assert TodoApp._switch_to_existing(_fake_self(), "t", "todo-x", owner) is False


def test_attaches_to_existing_session_outside_tmux(monkeypatch):
    attached: list[str] = []
    monkeypatch.setattr(launcher, "in_tmux", lambda: False)
    monkeypatch.setattr(launcher, "has_session", lambda name: True)
    monkeypatch.setattr(launcher, "attach_session", lambda name: attached.append(name))
    owner = Todo.new("Ship it")
    ns = _fake_self()
    assert TodoApp._switch_to_existing(ns, "Ship it", "todo-abc", owner) is True
    assert attached == ["todo-abc"]
    assert any("Attached: Ship it" in m for m, _ in ns._notes)


def test_attach_failure_is_reported_and_consumes_action(monkeypatch):
    """If a session exists but spawning a terminal fails, we must not fall
    through and start a fresh duplicate session — we already 'used' the action."""
    monkeypatch.setattr(launcher, "in_tmux", lambda: False)
    monkeypatch.setattr(launcher, "has_session", lambda name: True)

    def boom(_):
        raise RuntimeError("no terminal")

    monkeypatch.setattr(launcher, "attach_session", boom)
    owner = Todo.new("t")
    ns = _fake_self()
    assert TodoApp._switch_to_existing(ns, "t", "todo-x", owner) is True
    assert any("Could not attach" in m and sev == "error" for m, sev in ns._notes)
