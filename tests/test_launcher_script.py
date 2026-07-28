"""Tests for the `todo` bash launcher (not src/launcher.py)."""

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = REPO_ROOT / "todo"


def _fake_repo(root: Path) -> Path:
    """Copy the real launcher into a fake repo whose python just echoes argv."""
    repo = root / "repo"
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "src" / "todo.py").write_text("")

    stub = repo / ".venv" / "bin" / "python"
    stub.write_text('#!/usr/bin/env bash\necho "$@"\n')
    stub.chmod(0o755)

    launcher = repo / "todo"
    launcher.write_text(LAUNCHER.read_text())
    launcher.chmod(0o755)
    return repo


def _run(path: Path, *args: str) -> str:
    result = subprocess.run([str(path), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def test_launcher_runs_directly(tmp_path):
    repo = _fake_repo(tmp_path)
    assert _run(repo / "todo") == str(repo / "src" / "todo.py")


def test_launcher_runs_through_symlink(tmp_path):
    """Regression: `dirname $0` resolved to the symlink's dir, not the repo."""
    repo = _fake_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    link = bin_dir / "todo"
    link.symlink_to(repo / "todo")

    assert _run(link) == str(repo / "src" / "todo.py")


def test_launcher_runs_from_unrelated_cwd(tmp_path):
    repo = _fake_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    link = bin_dir / "todo"
    link.symlink_to(repo / "todo")

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    result = subprocess.run([str(link)], capture_output=True, text=True, check=True, cwd=elsewhere)
    assert result.stdout.strip() == str(repo / "src" / "todo.py")


def test_launcher_forwards_arguments(tmp_path):
    repo = _fake_repo(tmp_path)
    out = _run(repo / "todo", "--flag", "value")
    assert out == f"{repo / 'src' / 'todo.py'} --flag value"


def test_installed_launcher_resolves_to_repo():
    """The real ~/.local/bin symlink, if present, must reach this repo."""
    installed = Path(os.path.expanduser("~/.local/bin/todo"))
    if not installed.is_symlink():
        return
    assert installed.resolve() == LAUNCHER.resolve()
