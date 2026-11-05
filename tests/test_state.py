import json

from homepage.model import Book, Repo
from homepage.state import load_state, refresh, save_state

BOOK = Book("Dune", "Frank Herbert", "c.jpg", "https://x/dune", 10, 400)


def test_refresh_stores_new_value():
    state = {}
    result = refresh("book", lambda: BOOK, state, Book)
    assert result == BOOK
    assert state["book"] == {
        "title": "Dune", "author": "Frank Herbert", "cover": "c.jpg",
        "url": "https://x/dune", "page": 10, "pages": 400, "finished": False,
    }


def _old_state():
    state = {}
    refresh("book", lambda: BOOK, state, Book)
    return state


def test_refresh_keeps_last_value_on_error(capsys):
    state = _old_state()

    def boom():
        raise ValueError("layout")

    assert refresh("book", boom, state, Book) == BOOK
    assert "::warning::book not updated: layout" in capsys.readouterr().err


def test_refresh_keeps_last_value_on_none(capsys):
    state = _old_state()
    assert refresh("book", lambda: None, state, Book) == BOOK
    assert "::warning::book not updated: no data" in capsys.readouterr().err


def test_refresh_without_history_returns_none(capsys):
    assert refresh("book", lambda: None, {}, Book) is None
    assert "::warning::book not updated: no data" in capsys.readouterr().err


def test_refresh_list_roundtrip():
    repos = [Repo("a", "d", "u", "", "2026-01-01"), Repo("b", "d", "u", "h", "2026-01-02")]
    state = {}
    assert refresh("repos", lambda: repos, state, Repo) == repos
    assert isinstance(state["repos"], list)

    def boom():
        raise RuntimeError("down")

    assert refresh("repos", boom, state, Repo) == repos


def test_state_roundtrip(tmp_path):
    path = tmp_path / "data" / "state.json"
    state = {"b": {"x": 1}, "a": {"y": "é"}}
    save_state(path, state)
    assert load_state(path) == state
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert list(json.loads(text)) == ["a", "b"]


def test_load_state_missing(tmp_path):
    assert load_state(tmp_path / "nope.json") == {}


def _boom():
    raise RuntimeError("down")


def test_unreadable_stored_value_is_dropped_with_warning(capsys):
    state = {"book": {"title": "Dune"}}  # schema drift: fields missing
    assert refresh("book", _boom, state, Book) is None
    err = capsys.readouterr().err
    assert "::warning::book not updated: down" in err
    assert "::warning::book stored value unreadable:" in err


def test_unreadable_stored_list_is_dropped_with_warning(capsys):
    state = {"repos": [{"name": "a"}, "not a dict"]}
    assert refresh("repos", _boom, state, Repo) is None
    assert "::warning::repos stored value unreadable:" in capsys.readouterr().err


def test_invalid_state_json_is_empty_with_warning(tmp_path, capsys):
    path = tmp_path / "state.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_state(path) == {}
    assert "::warning::state" in capsys.readouterr().err


def test_state_json_that_is_not_an_object_is_empty(tmp_path, capsys):
    path = tmp_path / "state.json"
    path.write_text("[1, 2]", encoding="utf-8")
    assert load_state(path) == {}
    assert "::warning::state" in capsys.readouterr().err
