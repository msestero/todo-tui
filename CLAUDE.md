# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Run the app:** `./todo` (bash launcher that execs `.venv/bin/python src/todo.py`)
- **Run directly:** `.venv/bin/python src/todo.py`
- **Run tests:** `.venv/bin/python -m pytest tests/`
- **Lint:** `.venv/bin/ruff check src/ tests/`
- **Format:** `.venv/bin/ruff format src/ tests/`
- **Install (dev):** `./install.sh` — sets up `.venv`, installs runtime + dev deps (ruff, pytest), and wires up the git pre-commit hook.
- **Use isolated data:** set `TODO_TUI_DATA=/tmp/test-todos.json` to point at a throwaway store instead of `~/.config/todo-tui/todos.json`.

Runtime deps (`textual`, `rich`) are in `requirements.txt`; dev deps (`ruff`, `pytest`) are installed by `install.sh`. Lint/format config is in `pyproject.toml`. Tests in `tests/` cover the non-UI logic (serialization, Store, flatten/collapse, completion helpers) and use the `data_path` fixture (in `tests/conftest.py`) to redirect `TODO_TUI_DATA` to a temp file per test.

## Workflow (for Claude)

When making changes, follow this loop:

1. **Add or update tests alongside any feature or logic change.** New behavior in `src/` should land with new assertions in `tests/`. Bug fixes get a regression test.
2. **Before claiming a task is done, run:** `.venv/bin/ruff check src/ tests/ && .venv/bin/ruff format --check src/ tests/ && .venv/bin/python -m pytest tests/`. All three must pass.
3. **If green, commit and push immediately.** The user prefers small commits pushed to `master` rather than batched. Use terse commit messages (one short line is fine).
4. **If anything is red, fix it before committing** — do not skip hooks (`--no-verify`) without being asked.

The git pre-commit hook (`scripts/pre-commit`, symlinked into `.git/hooks/`) runs the same lint + format-check + tests gate, so a `git commit` will fail on red.

UI-only changes that genuinely have no testable logic (pure CSS, label tweaks) don't need new tests — but flatten/completion/store logic, key bindings, and form behavior do.

## Architecture

[Textual](https://textual.textualize.io/) TUI. All source lives in `src/`; one class per module; `src/todo.py` is a thin entry point that imports and runs `TodoApp`. Modules import siblings by bare name (`from store import Store`) — this works because `src/todo.py` is run as a script, putting `src/` on `sys.path`; there is no package/`__init__.py`. Tests add `src/` to `sys.path` via `tests/conftest.py`. Import order, low to high: `subtask` → `todo_item` → `store` / `row` → `todo_row` / `forms` → `app`.

| File | Contents |
|------|----------|
| `src/subtask.py` | `Subtask` dataclass |
| `src/todo_item.py` | `Todo` dataclass |
| `src/store.py` | `Store`, `DATA_PATH` |
| `src/row.py` | `Row` (flattened parent+subtask view model) |
| `src/view_model.py` | `ViewState`, `build_rows` — pure flatten of todos→rows |
| `src/todo_row.py` | `TodoRow` (the `ListItem` widget) |
| `src/week_view.py` | `Week`, `WeekViewState`, `build_week_rows` — sidebar view-model |
| `src/week_row_widget.py` | `WeekRowWidget` (sidebar `ListItem`) |
| `src/claude_context.py` | `build_context` — renders todo+subtasks to markdown for claude |
| `src/forms.py` | `TodoForm`, `SubtaskForm`, `NewFolderForm` — modal `ModalScreen`s |
| `src/launcher.py` | `launch(folders, session_id, session_name)` — tmux pane layout |
| `src/app.py` | `TodoApp` |
| `src/todo.py` | Entry point |

Three layers:

**Persistence** — `Store` holds all `Todo`s and serializes the entire collection to one JSON file on every mutation. There is no partial/incremental write: every action calls `_save_and_refresh()`. `Store.save()` is atomic (write to `*.tmp` sibling, then `os.replace`) so a kill mid-write cannot corrupt the file. `Todo.from_dict` / `Subtask.from_dict` handle backward-compatible loading (missing fields default, unknown keys ignored), so adding new optional fields is safe for existing data files.

**Domain model** — `Todo` (parent) owns a list of `Subtask`s. Todos are bucketed by an ISO date string (`Todo.date`), and the UI only ever shows one day at a time. Two cross-cutting rules live outside the UI handlers:
- `Store.rollover()` runs once at startup: any incomplete todo dated in the past is moved to today, so nothing is ever stranded on an old day.
- `_complete_parent()` / `_uncomplete_parent()` are the *only* correct ways to flip a parent's done state. Do not set `todo.done` directly — route through these.

**UI** — `TodoApp` lays out a horizontal split: a `#sidebar` `ListView` (weeks, oldest at top, one open at a time) on the left and a `#list` `ListView` for the selected day's todos on the right. The parent/subtask tree is flattened into a `list[Row]` (`Row` = parent + optional subtask) by `view_model.build_rows`; `ListView.index` maps back into `self._rows`. The sidebar uses `week_view.build_week_rows` over `store.dates()`. `ListView.Selected` is dispatched by `event.list_view.id` — `#sidebar` enter toggles a week's expansion or jumps `current_date` to the picked day, `#list` enter toggles subtask collapse. `←` focuses the sidebar, `→` focuses the list; `t` jumps to today and reopens today's week; `h` toggles hide-done-subtasks for the selected parent (independent from full collapse — pending subtasks stay visible, done ones drop out and the parent row shows an `(N done hidden)` indicator). Adding/editing parents and subtasks is done through modal `ModalScreen`s in `forms.py`: `TodoForm` and `SubtaskForm` are both thin subclasses of `_ItemForm` (same shape, different placeholder). The form dismisses with `dict | None` — `{"text": str, "folders": list[str], "claude_session_id": str | None}` on save, `None` on cancel.

The footer is bare — only `? Help` is shown. Pressing `?` opens `HelpScreen` (in `app.py`), which lists every binding sourced from the `HELP_ENTRIES` table at the top of the file.

## Claude integration

Pressing `c` on a row opens a tmux layout — left pane runs `claude`, right column has one shell per folder stacked vertically.

- **Folder resolution.** A subtask inherits the parent's folders if its own `folders` list is empty; the session id is always the row's own. If neither parent nor subtask has any folders, a `NewFolderForm` modal asks for a name, creates `~/TodoList/<name>`, attaches it to the **parent** (since subtasks inherit), saves, and continues to launch.
- **Session ids are pre-bound.** First `c` on a row generates a fresh uuid, saves it to the row, and passes it to claude via `--session-id <uuid>`. Subsequent `c` resumes via `--resume <uuid>`. No filesystem polling, no manual paste-back.
- **tmux behavior.** Inside tmux, opens a new window. Window title is the todo/subtask text; session name (when spawned outside tmux) is `todo-<id>`. Outside tmux, creates a detached session and spawns a terminal (`$TERMINAL` if set, otherwise tries alacritty/kitty/wezterm/foot/ghostty/gnome-terminal/konsole/xterm) attached to it.
- **Folder paths** are `expanduser()`-resolved before launch; if a folder no longer exists, the launch aborts with a notification (it does *not* auto-recreate).
- **Subtask context on every launch.** On every `c` (both first launch and resume), the parent todo + its subtasks are rendered to markdown by `claude_context.build_context` and passed to claude via `--append-system-prompt`. Re-injecting on each launch reflects the live state of the todo (e.g. newly-checked subtasks) rather than freezing it at first launch.
- **Answering "what are the subtasks?" — read the system prompt, not the JSON.** When the user (in a session launched via `c`) asks about the current todo's subtasks or their done state, the answer is already in your system prompt as a `# Task: …` / `## Subtasks` block. Read it from there. Do **not** shell out to `cat ~/.config/todo-tui/todos.json` — that defeats the whole point of the injection. The JSON is only the right source if the user asks about *other* todos in the day or explicitly says to re-check the file.

## Behaviors worth knowing before editing

- **Add/edit forms** — `a` opens `TodoForm` for a new parent; `s` opens `SubtaskForm` under the selected parent; `e` opens the appropriate edit form for the selected row. Both forms collect `text`, `folders` (comma-separated, parsed into a list by `_parse_folders`), and an optional `claude_session_id`. Inline labels, no title, up/down navigation, `enter` saves, `esc` cancels.
- **Subtask/parent sync** (`action_toggle`): checking the last subtask auto-completes the parent; unchecking one re-opens a completed parent.
- **Reviving** — toggling a *done* todo while viewing a past day un-completes it, moves it to today, and jumps the view to today.
- **Adding is today-only** — `action_add` / `action_add_sub` refuse unless `_viewing_today()`.
- **Collapse state is per-parent and in-memory only** — `TodoApp._collapsed: set[str]` of parent ids; reset on app restart. `enter` toggles collapse for the parent owning the selected row (works on parent or subtask). Triggered via `ListView.Selected` (not a key binding), so it never fires while a modal form is open — that lets `enter` still submit the form.
