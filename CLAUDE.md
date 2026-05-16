# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Run the app:** `./todo` (bash launcher that execs `.venv/bin/python todo.py`)
- **Run directly:** `.venv/bin/python todo.py`
- **Use isolated data:** set `TODO_TUI_DATA=/tmp/test-todos.json` to point at a throwaway store instead of `~/.config/todo-tui/todos.json` — useful when testing without touching real data.

There is no build step, no test suite, and no linter configured. Dependencies (`textual`, `rich`) live only in `.venv`; there is no `requirements.txt`. If adding dependencies, install into `.venv` and consider adding a requirements file. This is not a git repository.

## Architecture

[Textual](https://textual.textualize.io/) TUI. One class per module; `todo.py` is a thin entry point that imports and runs `TodoApp`. Modules import siblings by bare name (`from store import Store`) — this works because `todo.py` is run as a script, putting its directory on `sys.path`; there is no package/`__init__.py`. Import order, low to high: `subtask` → `todo_item` → `parsing` / `store` / `row` → `todo_row` → `app`.

| File | Contents |
|------|----------|
| `subtask.py` | `Subtask` dataclass |
| `todo_item.py` | `Todo` dataclass |
| `parsing.py` | `parse_input`, `next_occurrence`, `REPEAT_RE`, `SCORE_RE` |
| `store.py` | `Store`, `DATA_PATH` |
| `row.py` | `Row` (flattened parent+subtask view model) |
| `todo_row.py` | `TodoRow` (the `ListItem` widget) |
| `app.py` | `TodoApp` |

Three layers:

**Persistence** — `Store` holds all `Todo`s and serializes the entire collection to one JSON file on every mutation. There is no partial/incremental write: every action calls `store.save()` then `refresh_list()`. `Todo.from_dict` handles backward-compatible loading (missing fields default), so adding new optional `Todo` fields is safe for existing data files.

**Domain model** — `Todo` (parent) owns a list of `Subtask`s. Todos are bucketed by an ISO date string (`Todo.date`), and the UI only ever shows one day at a time. Key cross-cutting rules live in two methods, not in the UI handlers:
- `Store.rollover()` runs once at startup: any incomplete todo dated in the past is moved to today, so nothing is ever stranded on an old day.
- `_complete_parent()` / `_uncomplete_parent()` are the *only* correct ways to flip a parent's done state. Completing a repeating todo spawns a dated clone (with fresh subtask copies) for its next occurrence; completing a scored todo records its score. Do not set `todo.done` directly — route through these.

**UI** — `TodoApp` renders the current day's todos via a `ListView`. The parent/subtask tree is flattened into a `list[Row]` (`Row` = parent + optional subtask) by `_flatten`; `ListView.index` maps back into `self._rows`. The bottom `Input` is a single reused widget driven by `self._input_mode`, a string tag that is one of `"new"`, `"sub:<parent_id>"`, or `"score:<parent_id>"`. `add_submitted` branches on that tag — when adding a new input flow, follow this mode-string pattern rather than adding more widgets.

## Behaviors worth knowing before editing

- **Input syntax** — `parse_input` strips inline tokens from a new todo's text: `/N` sets `max_score`, and `*daily` / `*weekly` / `*weekdays` / `*Nd` set `repeat`. Regexes are `SCORE_RE` and `REPEAT_RE`.
- **Scored todos** don't toggle done directly — toggling opens the input in `score:` mode to collect a 0..max integer.
- **Subtask/parent sync** (`action_toggle`): checking the last subtask auto-completes a non-scored parent; unchecking one re-opens a completed parent.
- **Reviving** — toggling a *done* todo while viewing a past day un-completes it, moves it to today, and jumps the view to today.
- **Adding is today-only** — `action_add` / `action_add_sub` refuse unless `_viewing_today()`.
