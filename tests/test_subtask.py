from subtask import Subtask


def test_new_assigns_id_and_defaults():
    s = Subtask.new("a thing")
    assert len(s.id) == 8
    assert s.text == "a thing"
    assert s.done is False
    assert s.folders == []
    assert s.claude_session_id is None


def test_new_with_optional_fields():
    s = Subtask.new("x", folders=["~/proj"], claude_session_id="sess-1")
    assert s.folders == ["~/proj"]
    assert s.claude_session_id == "sess-1"


def test_new_copies_folders_list():
    src = ["a"]
    s = Subtask.new("x", folders=src)
    src.append("b")
    assert s.folders == ["a"]


def test_from_dict_full():
    raw = {"id": "abc", "text": "t", "done": True, "folders": ["f1"], "claude_session_id": "sid"}
    s = Subtask.from_dict(raw)
    assert s == Subtask(id="abc", text="t", done=True, folders=["f1"], claude_session_id="sid")


def test_from_dict_defaults_for_missing_fields():
    s = Subtask.from_dict({"id": "x", "text": "t"})
    assert s.done is False
    assert s.folders == []
    assert s.claude_session_id is None


def test_from_dict_null_folders_becomes_empty_list():
    s = Subtask.from_dict({"id": "x", "text": "t", "folders": None})
    assert s.folders == []
