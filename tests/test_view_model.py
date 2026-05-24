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


def test_done_parents_sort_to_bottom():
    a = Todo.new("a")
    b = Todo.new("b")
    c = Todo.new("c")
    a.done = True
    rows = build_rows([a, b, c], ViewState())
    assert [r.parent.text for r in rows] == ["b", "c", "a"]


def test_done_subtasks_sort_to_bottom_within_parent():
    t = _todo_with_subs("p", ["a", "b", "c"])
    t.subtasks[0].done = True
    t.subtasks[2].done = True
    rows = build_rows([t], ViewState())
    sub_texts = [r.sub.text for r in rows if r.sub]
    assert sub_texts == ["b", "a", "c"]


def test_parent_sort_is_stable_among_pending():
    a = Todo.new("a")
    b = Todo.new("b")
    c = Todo.new("c")
    rows = build_rows([a, b, c], ViewState())
    assert [r.parent.text for r in rows] == ["a", "b", "c"]


def test_done_parent_keeps_its_subtasks_grouped_below_it():
    """When a parent moves to the bottom, its subtasks come with it."""
    a = _todo_with_subs("a", ["a1"])
    b = _todo_with_subs("b", ["b1"])
    a.done = True
    rows = build_rows([a, b], ViewState())
    texts = [r.parent.text + ("/" + r.sub.text if r.sub else "") for r in rows]
    assert texts == ["b", "b/b1", "a", "a/a1"]
