from dataclasses import asdict

from app import TodoApp
from forms import ItemFormResult, _parse_folders
from subtask import Subtask
from todo_item import Todo


def test_parse_empty_returns_empty_list():
    assert _parse_folders("") == []
    assert _parse_folders("   ") == []


def test_parse_single_folder():
    assert _parse_folders("~/proj") == ["~/proj"]


def test_parse_strips_whitespace_around_entries():
    assert _parse_folders("  a  ,  b  ,  c  ") == ["a", "b", "c"]


def test_parse_drops_empty_entries():
    assert _parse_folders("a,,b,") == ["a", "b"]
    assert _parse_folders(",,,") == []


def test_parse_preserves_inner_paths():
    assert _parse_folders("~/a/b, /tmp/c") == ["~/a/b", "/tmp/c"]


# ---------------- ItemFormResult ----------------


def test_item_form_result_defaults():
    r = ItemFormResult()
    assert r.text == ""
    assert r.folders == []
    assert r.claude_session_id is None


def test_item_form_result_round_trips_into_todo_new():
    """`asdict(result)` should be a valid kwargs for `Todo.new`. This is the
    contract that lets `action_add` stay a one-liner."""
    r = ItemFormResult(text="hi", folders=["~/x"], claude_session_id="sid")
    t = Todo.new(**asdict(r))
    assert t.text == "hi"
    assert t.folders == ["~/x"]
    assert t.claude_session_id == "sid"


def test_item_form_result_round_trips_into_subtask_new():
    r = ItemFormResult(text="sub", folders=["~/y"])
    s = Subtask.new(**asdict(r))
    assert s.text == "sub"
    assert s.folders == ["~/y"]
    assert s.claude_session_id is None


# ---------------- _apply_form_result ----------------


def test_apply_form_result_overwrites_todo_fields():
    t = Todo.new("old")
    t.folders = ["a"]
    t.claude_session_id = "old-sid"
    r = ItemFormResult(text="new", folders=["b"], claude_session_id="new-sid")
    TodoApp._apply_form_result(t, r)
    assert t.text == "new"
    assert t.folders == ["b"]
    assert t.claude_session_id == "new-sid"


def test_apply_form_result_clears_session_id_when_blank():
    t = Todo.new("x")
    t.claude_session_id = "had-one"
    TodoApp._apply_form_result(t, ItemFormResult(text="x"))
    assert t.claude_session_id is None


def test_apply_form_result_works_on_subtask():
    s = Subtask.new("old")
    TodoApp._apply_form_result(
        s, ItemFormResult(text="new", folders=["~/z"], claude_session_id="sid")
    )
    assert s.text == "new"
    assert s.folders == ["~/z"]
    assert s.claude_session_id == "sid"
