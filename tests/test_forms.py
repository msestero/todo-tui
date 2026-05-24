from forms import _parse_folders


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
