# todo-tui

A terminal todo list with Claude Code integration. Pick a task, press `c`, and a tmux layout opens with Claude in one pane and shells for each associated folder in the others.

Built on [Textual](https://textual.textualize.io/). Storage is a single JSON file at `~/.config/todo-tui/todos.json` (override with `TODO_TUI_DATA`).

![todo-tui](https://img.shields.io/badge/textual-tui-blue)

## Install

```bash
git clone git@github.com:msestero/todo-tui.git
cd todo-tui
./install.sh             # creates .venv, symlinks `todo` onto PATH
# or
./install.sh --binary    # builds a standalone PyInstaller binary
```

The default install puts `~/.local/bin/todo` on PATH. Override with `PREFIX=/somewhere/else ./install.sh`.

## Run

```bash
todo
```

## Key bindings

| Key | Action |
|---|---|
| `a` | Add a new todo (today only) |
| `s` | Add a subtask under the selected todo |
| `e` | Edit the selected todo or subtask |
| `c` | Open a tmux Claude session for the selected row |
| `space` | Toggle done on the selected row |
| `enter` | Collapse/expand subtasks (task list) — open/select week or day (sidebar) |
| `h` | Hide/show *done* subtasks for the selected parent |
| `d` | Delete the selected todo or subtask |
| `←` / `w` | Focus the week sidebar |
| `→` | Focus the task list |
| `t` | Jump to today (re-opens today's week) |
| `?` | Help |
| `q` | Quit |

The left-side sidebar lists every week that has todos (oldest at the top). `enter` on a week expands it inline into 7 day rows; only one week is open at a time. `enter` on a day jumps the task list to that day and returns focus there.

Inside the add/edit form: `up`/`down` to move between fields, `enter` saves, `esc` cancels.

## Claude integration

`c` opens a tmux window with `claude` on the left and one shell per folder stacked on the right. If neither the selected subtask nor its parent has any folders attached, you're prompted to create one under `~/TodoList/<name>`.

- A fresh row uses `claude --session-id <uuid>` so the session id is captured up front.
- Subsequent presses on the same row use `claude --resume <uuid>`.
- Folders can be edited via `e` (comma-separated). Subtasks inherit folders from their parent if their own list is empty.

## Data

One JSON file, atomically written (tmp + rename) on every mutation:

```json
{
  "todos": [{
    "id": "abcd1234",
    "text": "Buy milk",
    "date": "2026-05-21",
    "done": false,
    "subtasks": [{"id": "ef567890", "text": "Stop", "done": false,
                  "folders": [], "claude_session_id": null}],
    "folders": ["~/projects/milk"],
    "claude_session_id": "01HXYZ..."
  }]
}
```

Past-dated incomplete todos are auto-rolled forward to today on launch.

## Development

```
src/        # all source modules
tests/      # pytest tests (non-UI: serialization, store, flatten, completion)
todo        # bash launcher
install.sh  # symlink or PyInstaller install
```

Run tests:

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests/
```

Use an isolated data file while hacking:

```bash
TODO_TUI_DATA=/tmp/test-todos.json .venv/bin/python src/todo.py
```
