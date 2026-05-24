from subtask import Subtask
from todo_item import Todo
from view_model import ViewState, build_rows


def _todo_with_subs(text: str, sub_texts: list[str]) -> Todo:
    t = Todo.new(text)
    t.subtasks = [Subtask.new(s) for s in sub_texts]
    return t


def test_no_subtasks_yields_only_parent():
    t = Todo.new("solo")
    rows = build_rows([t], ViewState())
    assert len(rows) == 1
    assert rows[0].parent is t
    assert rows[0].sub is None
    assert rows[0].collapsed is False


def test_subtasks_appear_in_order_below_parent():
    t = _todo_with_subs("p", ["a", "b"])
    rows = build_rows([t], ViewState())
    assert len(rows) == 3
    assert rows[0].sub is None
    assert rows[1].sub is t.subtasks[0]
    assert rows[2].sub is t.subtasks[1]


def test_collapsed_parent_hides_subtasks_and_flags_row():
    t = _todo_with_subs("p", ["a", "b"])
    state = ViewState(collapsed={t.id})
    rows = build_rows([t], state)
    assert len(rows) == 1
    assert rows[0].collapsed is True


def test_collapsed_parent_with_no_subtasks_does_not_flag():
    """A parent with no subtasks shouldn't render '(0 hidden)' even if its
    id is in the collapsed set."""
    t = Todo.new("empty")
    rows = build_rows([t], ViewState(collapsed={t.id}))
    assert rows[0].collapsed is False


def test_mixed_collapse_across_multiple_parents():
    a = _todo_with_subs("a", ["a1"])
    b = _todo_with_subs("b", ["b1", "b2"])
    rows = build_rows([a, b], ViewState(collapsed={b.id}))
    texts = [r.parent.text + ("/" + r.sub.text if r.sub else "") for r in rows]
    assert texts == ["a", "a/a1", "b"]


def test_empty_input_returns_empty_list():
    assert build_rows([], ViewState()) == []


def test_default_view_state_is_empty():
    state = ViewState()
    assert state.collapsed == set()
