import asyncio
from dataclasses import asdict

from textual.app import App
from textual.widgets import Input

from app import TodoApp
from forms import ItemFormResult, SubtaskForm, TodoForm, _parse_folders, _wrap_index
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


# ---------------- _wrap_index ----------------


def test_wrap_index_steps_forward_and_back():
    assert _wrap_index(0, 1, 3) == 1
    assert _wrap_index(1, -1, 3) == 0


def test_wrap_index_wraps_at_both_ends():
    assert _wrap_index(2, 1, 3) == 0
    assert _wrap_index(0, -1, 3) == 2


def test_wrap_index_handles_empty_field_list():
    assert _wrap_index(0, 1, 0) == 0


# ---------------- form focus navigation ----------------


class _FormHarness(App):
    """Minimal app that just pushes `form` so a Pilot can drive it."""

    def __init__(self, form):
        super().__init__()
        self._form = form

    def on_mount(self) -> None:
        self.push_screen(self._form)


def _focus_after(form, keys: list[str]) -> list[str]:
    """Press `keys` in `form` and return the focused input id after each press."""

    async def run() -> list[str]:
        app = _FormHarness(form)
        seen: list[str] = []
        async with app.run_test() as pilot:
            await pilot.pause()
            for key in keys:
                await pilot.press(key)
                await pilot.pause()
                focused = app.focused
                seen.append(focused.id if isinstance(focused, Input) else None)
        return seen

    return asyncio.run(run())


def test_form_opens_focused_on_text():
    assert _focus_after(TodoForm(), []) == []
    # first field is focused before any key is pressed
    assert _focus_after(TodoForm(), ["down", "up"]) == ["folders", "text"]


def test_down_walks_fields_and_wraps_to_top():
    assert _focus_after(TodoForm(), ["down", "down", "down"]) == ["folders", "session", "text"]


def test_up_from_first_field_wraps_to_last():
    assert _focus_after(TodoForm(), ["up"]) == ["session"]


def test_tab_navigates_the_same_fields():
    assert _focus_after(TodoForm(), ["tab", "tab"]) == ["folders", "session"]
    assert _focus_after(TodoForm(), ["shift+tab"]) == ["session"]


def test_subtask_form_navigates_too():
    assert _focus_after(SubtaskForm(), ["down", "up", "up"]) == ["folders", "text", "session"]


def test_arrows_do_not_disturb_typed_text():
    """Up/down move focus; they must not eat or alter the input's contents."""

    async def run() -> tuple[str, str]:
        app = _FormHarness(TodoForm(ItemFormResult(text="hello", folders=["a"])))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("down", "up")
            await pilot.pause()
            screen = app.screen
            return (
                screen.query_one("#text", Input).value,
                screen.query_one("#folders", Input).value,
            )

    assert asyncio.run(run()) == ("hello", "a")


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
