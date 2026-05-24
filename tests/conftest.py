"""Point TODO_TUI_DATA at a per-test tmp file before importing project modules.

`store.DATA_PATH` is captured at import time, so the env var must be set before
any test imports `store`. The autouse `data_path` fixture then reloads the
module per test so each test gets its own isolated JSON file.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def data_path(tmp_path, monkeypatch):
    """Isolated todos.json per test. Returns the Path and reloads `store`."""
    path = tmp_path / "todos.json"
    monkeypatch.setenv("TODO_TUI_DATA", str(path))
    import store

    importlib.reload(store)
    # Re-import Todo so store.Todo is the same class used elsewhere
    return path
