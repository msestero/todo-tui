# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Run the app:** `./todo` (bash launcher that execs `.venv/bin/python todo.py`)
- **Run directly:** `.venv/bin/python todo.py`
- **Run tests:** `.venv/bin/python -m pytest tests/` (requires `pip install pytest`)
- **Use isolated data:** set `TODO_TUI_DATA=/tmp/test-todos.json` to point at a throwaway store instead of `~/.config/todo-tui/todos.json` — useful when testing without touching real data.

There is no build step or linter configured. Runtime dependencies (`textual`, `rich`) are in `requirements.txt`; `pytest` is a dev-only dep installed manually. Tests in `tests/` cover the non-UI logic (serialization, Store, flatten/collapse, completion helpers) and use the `data_path` fixture (in `tests/conftest.py`) to redirect `TODO_TUI_DATA` to a temp file per test.

## Architecture

[Textual](https://textual.textualize.io/) TUI. One class per module; `todo.py` is a thin entry point that imports and runs `TodoApp`. Modules import siblings by bare name (`from store import Store`) — this works because `todo.py` is run as a script, putting its directory on `sys.path`; there is no package/`__init__.py`. Import order, low to high: `subtask` → `todo_item` → `store` / `row` → `todo_row` / `forms` → `app`.

| File | Contents |
|------|----------|
| `subtask.py` | `Subtask` dataclass |
| `todo_item.py` | `Todo` dataclass |
| `store.py` | `Store`, `DATA_PATH` |
| `row.py` | `Row` (flattened parent+subtask view model) |
| `todo_row.py` | `TodoRow` (the `ListItem` widget) |
| `forms.py` | `TodoForm`, `SubtaskForm`, `NewFolderForm` — modal `ModalScreen`s |
| `launcher.py` | `launch(folders, session_id, session_name)` — tmux pane layout |
| `app.py` | `TodoApp` |

Three layers:

**Persistence** — `Store` holds all `Todo`s and serializes the entire collection to one JSON file on every mutation. There is no partial/incremental write: every action calls `_save_and_refresh()`. `Store.save()` is atomic (write to `*.tmp` sibling, then `os.replace`) so a kill mid-write cannot corrupt the file. `Todo.from_dict` / `Subtask.from_dict` handle backward-compatible loading (missing fields default, unknown keys ignored), so adding new optional fields is safe for existing data files.

**Domain model** — `Todo` (parent) owns a list of `Subtask`s. Todos are bucketed by an ISO date string (`Todo.date`), and the UI only ever shows one day at a time. Two cross-cutting rules live outside the UI handlers:
- `Store.rollover()` runs once at startup: any incomplete todo dated in the past is moved to today, so nothing is ever stranded on an old day.
- `_complete_parent()` / `_uncomplete_parent()` are the *only* correct ways to flip a parent's done state. Do not set `todo.done` directly — route through these.

**UI** — `TodoApp` renders the current day's todos via a `ListView`. The parent/subtask tree is flattened into a `list[Row]` (`Row` = parent + optional subtask) by `_flatten`; `ListView.index` maps back into `self._rows`. Adding/editing parents and subtasks is done through modal `ModalScreen`s in `forms.py`: `TodoForm` and `SubtaskForm` are both thin subclasses of `_ItemForm` (same shape, different placeholder). The form dismisses with `dict | None` — `{"text": str, "folders": list[str], "claude_session_id": str | None}` on save, `None` on cancel.

The footer is bare — only `? Help` is shown. Pressing `?` opens `HelpScreen` (in `app.py`), which lists every binding sourced from the `HELP_ENTRIES` table at the top of the file.

## Claude integration

Pressing `c` on a row opens a tmux layout — left pane runs `claude` (resumes via `--resume <id>` if `claude_session_id` is set, else fresh), right column has one shell per folder stacked vertically.

- **Folder resolution.** A subtask inherits the parent's folders if its own `folders` list is empty; the session id is always the row's own. If neither parent nor subtask has any folders, a `NewFolderForm` modal asks for a name, creates `~/TodoList/<name>`, attaches it to the **parent** (since subtasks inherit), saves, and continues to launch.
- **tmux behavior.** Inside tmux, opens a new window named `todo-<id>`. Outside tmux, creates a detached session and spawns a terminal (`$TERMINAL` if set, otherwise tries alacritty/kitty/wezterm/foot/ghostty/gnome-terminal/konsole/xterm) attached to it.
- **Capturing new session ids.** Fresh `claude` invocations don't automatically populate `claude_session_id` — paste the id back in via the edit form (`e`) once you know it. Subsequent `c` will resume.
- **Folder paths** are `expanduser()`-resolved before launch; if a folder no longer exists, the launch aborts with a notification (it does *not* auto-recreate).

## Behaviors worth knowing before editing

- **Add/edit forms** — `a` opens `TodoForm` for a new parent; `s` opens `SubtaskForm` under the selected parent; `e` opens the appropriate edit form for the selected row. Both forms collect `text`, `folders` (comma-separated, parsed into a list by `_parse_folders`), and an optional `claude_session_id`. Inline labels, no title, up/down navigation, `enter` saves, `esc` cancels.
- **Subtask/parent sync** (`action_toggle`): checking the last subtask auto-completes the parent; unchecking one re-opens a completed parent.
- **Reviving** — toggling a *done* todo while viewing a past day un-completes it, moves it to today, and jumps the view to today.
- **Adding is today-only** — `action_add` / `action_add_sub` refuse unless `_viewing_today()`.
