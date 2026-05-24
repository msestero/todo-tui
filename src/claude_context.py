"""Build a markdown context blob from a Todo for the Claude session.

Pure — no I/O, no model coupling beyond reading fields. The launcher will
eventually accept the returned string and pipe it to claude (via stdin, a
system-prompt flag, or a temp file), but that's a feature concern. This
module's job is just: "given a parent todo with subtasks, produce the prompt
material."
"""

from __future__ import annotations

from todo_item import Todo


def build_context(todo: Todo) -> str:
    """Markdown rendering of a parent todo + its subtasks for claude.

    Format:

        # Task: <parent text>

        ## Subtasks
        - [x] completed sub one
        - [ ] pending sub two

    When the parent has no subtasks, only the task line is emitted.
    """
    lines = [f"# Task: {todo.text}"]
    if todo.subtasks:
        lines.append("")
        lines.append("## Subtasks")
        lines.extend(_subtask_line(sub) for sub in todo.subtasks)
    return "\n".join(lines)


def _subtask_line(sub) -> str:
    mark = "x" if sub.done else " "
    return f"- [{mark}] {sub.text}"
