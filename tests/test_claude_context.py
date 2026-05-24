from claude_context import build_context
from subtask import Subtask
from todo_item import Todo


def test_parent_with_no_subtasks_emits_only_task_line():
    t = Todo.new("Buy milk")
    assert build_context(t) == "# Task: Buy milk"


def test_parent_with_subtasks_renders_markdown_checkboxes():
    t = Todo.new("Ship the thing")
    t.subtasks = [Subtask.new("write docs"), Subtask.new("merge PR")]
    t.subtasks[0].done = True

    expected = "# Task: Ship the thing\n\n## Subtasks\n- [x] write docs\n- [ ] merge PR"
    assert build_context(t) == expected


def test_subtask_order_is_preserved():
    t = Todo.new("p")
    t.subtasks = [Subtask.new("a"), Subtask.new("b"), Subtask.new("c")]
    out = build_context(t)
    assert out.index("- [ ] a") < out.index("- [ ] b") < out.index("- [ ] c")


def test_special_characters_in_text_are_passed_through_as_is():
    """We don't HTML-escape; claude reads markdown directly."""
    t = Todo.new("Use `git` & rebase <main>")
    assert "Use `git` & rebase <main>" in build_context(t)


def test_all_done_subtasks():
    t = Todo.new("Done parent")
    t.subtasks = [Subtask.new("a"), Subtask.new("b")]
    for s in t.subtasks:
        s.done = True
    out = build_context(t)
    assert "- [x] a" in out
    assert "- [x] b" in out
    assert "- [ ]" not in out
