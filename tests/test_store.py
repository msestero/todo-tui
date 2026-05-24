import contextlib
import importlib
import json
from datetime import date, timedelta


def _reload_store():
    import store

    importlib.reload(store)
    return store


def test_load_returns_empty_when_file_missing(data_path):
    s = _reload_store()
    assert not data_path.exists()
    store_obj = s.Store.load()
    assert store_obj.todos == []


def test_save_then_load_round_trip(data_path):
    s = _reload_store()
    from subtask import Subtask

    todo = s.Todo.new("hello", folders=["~/x"], claude_session_id="sid")
    todo.subtasks = [Subtask.new("sub", folders=["~/y"])]

    store_obj = s.Store(todos=[todo])
    store_obj.save()

    reloaded = s.Store.load()
    assert len(reloaded.todos) == 1
    rt = reloaded.todos[0]
    assert rt.text == "hello"
    assert rt.folders == ["~/x"]
    assert rt.claude_session_id == "sid"
    assert len(rt.subtasks) == 1
    assert rt.subtasks[0].text == "sub"
    assert rt.subtasks[0].folders == ["~/y"]


def test_save_is_atomic_no_partial_file(data_path, monkeypatch):
    """If the write process is interrupted between tmp-write and replace,
    the original file must remain intact."""
    s = _reload_store()
    from subtask import Subtask  # noqa

    s.Store(todos=[s.Todo.new("v1")]).save()
    original_bytes = data_path.read_bytes()

    # Force os.replace to blow up — simulates a crash mid-rename.
    import os as real_os

    real_replace = real_os.replace

    def boom(src, dst):
        raise OSError("simulated crash")

    monkeypatch.setattr(s.os, "replace", boom)

    with contextlib.suppress(OSError):
        s.Store(todos=[s.Todo.new("v2-corrupt")]).save()

    # Original file is untouched.
    assert data_path.read_bytes() == original_bytes
    # Restore so tmp cleanup below works
    monkeypatch.setattr(s.os, "replace", real_replace)


def test_save_writes_json_payload_shape(data_path):
    s = _reload_store()
    t = s.Todo.new("hi")
    s.Store(todos=[t]).save()
    raw = json.loads(data_path.read_text())
    assert list(raw.keys()) == ["todos"]
    assert raw["todos"][0]["text"] == "hi"
    assert "subtasks" in raw["todos"][0]


def test_rollover_moves_past_undone_to_today(data_path):
    s = _reload_store()
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    older = (date.today() - timedelta(days=10)).isoformat()

    stale = s.Todo.new("stale")
    stale.date = yesterday
    done_old = s.Todo.new("done old")
    done_old.date = older
    done_old.done = True
    fresh = s.Todo.new("today")
    fresh.date = today

    store_obj = s.Store(todos=[stale, done_old, fresh])
    moved = store_obj.rollover()

    assert moved == 1
    assert stale.date == today
    assert done_old.date == older  # done todos do NOT roll over
    assert fresh.date == today


def test_dates_includes_today_and_visible_only(data_path):
    s = _reload_store()
    today = date.today().isoformat()
    past = (date.today() - timedelta(days=2)).isoformat()
    future = (date.today() + timedelta(days=2)).isoformat()

    a = s.Todo.new("a")
    a.date = past
    b = s.Todo.new("b")
    b.date = future
    store_obj = s.Store(todos=[a, b])

    result = store_obj.dates()
    assert past in result
    assert today in result  # always present even if no todo on today
    assert future not in result  # future hidden
    assert result == sorted(result)


def test_by_date_filters_to_target(data_path):
    s = _reload_store()
    a = s.Todo.new("a")
    a.date = "2026-01-01"
    b = s.Todo.new("b")
    b.date = "2026-01-02"
    c = s.Todo.new("c")
    c.date = "2026-01-01"
    store_obj = s.Store(todos=[a, b, c])

    on_first = store_obj.by_date("2026-01-01")
    assert [t.text for t in on_first] == ["a", "c"]
    assert store_obj.by_date("2026-01-02") == [b]
    assert store_obj.by_date("2099-01-01") == []
