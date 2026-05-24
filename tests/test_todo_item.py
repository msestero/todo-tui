from datetime import date

from subtask import Subtask
from todo_item import Todo


def test_new_dates_to_today():
    t = Todo.new("buy milk")
    assert t.date == date.today().isoformat()
    assert t.done is False
    assert t.subtasks == []
    assert t.folders == []
    assert t.claude_session_id is None


def test_from_dict_full():
    raw = {
        "id": "abcd1234",
        "text": "task",
        "date": "2026-01-01",
        "done": True,
        "subtasks": [{"id": "s1", "text": "sub", "done": False,
                      "folders": [], "claude_session_id": None}],
        "folders": ["~/p"],
        "claude_session_id": "sess",
    }
    t = Todo.from_dict(raw)
    assert t.id == "abcd1234"
    assert t.date == "2026-01-01"
    assert t.done is True
    assert t.folders == ["~/p"]
    assert t.claude_session_id == "sess"
    assert t.subtasks == [Subtask(id="s1", text="sub")]


def test_from_dict_backward_compat_missing_fields():
    t = Todo.from_dict({"id": "x", "text": "t", "date": "2026-01-01"})
    assert t.subtasks == []
    assert t.folders == []
    assert t.claude_session_id is None
    assert t.done is False


def test_from_dict_ignores_unknown_keys():
    raw = {"id": "x", "text": "t", "date": "2026-01-01",
           "score": 5, "repeat_days": [1, 2]}
    t = Todo.from_dict(raw)
    assert t.text == "t"
