import re
import shutil
from pathlib import Path

import pytest

from homepage.build import build
from homepage.model import Book, Film, Repo, Song
from homepage.state import load_state, save_state

ROOT = Path(__file__).resolve().parents[1]
POSTER = "https://a.ltrbxd.com/resized/poster.jpg"
COVER = "https://i.gr-assets.com/images/cover.jpg"
SONG_COVER = "https://i.scdn.co/image/abc"
PIC = "https://raw.githubusercontent.com/jvitorcosta/x/HEAD/p.png"
EXTERNAL = ("ltrbxd.com", "gr-assets.com", "scdn.co", "raw.githubusercontent.com")

FILM = Film("Hope", "2026", 3.5, True, "2026-11-05", "bom", POSTER, "https://letterboxd.com/zubu/film/hope/")
BOOK = Book("Can't Hurt Me", "David Goggins", COVER, "https://www.goodreads.com/book/1", 210, 366)
SONG = Song("Taxi Lunar", "Geraldo Azevedo", SONG_COVER, "https://open.spotify.com/track/1", False)
REPOS = [Repo("car-cyberdeck", "dash", "https://github.com/jvitorcosta/car-cyberdeck", "", "2026-11-01T00:00:00Z")]


def fake_get(url, headers=None):
    return b"img:" + url.encode()


def failing_get(url, headers=None):
    raise OSError("offline")


def boom():
    raise RuntimeError("layout changed")


def sources(**over):
    s = {"song": lambda: SONG, "film": lambda: FILM, "book": lambda: BOOK, "repos": lambda: REPOS}
    s.update(over)
    return s


@pytest.fixture
def site(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    shutil.copytree(ROOT / "assets", tmp_path / "assets")
    return tmp_path


def srcs(html):
    return re.findall(r'src="([^"]*)"', html)


def test_build_writes_index_and_state(site):
    index = build(site, sources(), get=fake_get)
    assert index == site / "index.html"
    html = index.read_text(encoding="utf-8")
    assert "Hope" in html and "Can&#x27;t Hurt Me" in html or "Hurt Me" in html
    state = load_state(site / "data" / "state.json")
    assert set(state) == {"song", "film", "book", "repos"}
    assert (site / "assets" / "live").is_dir()


def test_failing_source_keeps_previous_value(site, capsys):
    from homepage.model import to_dict
    save_state(site / "data" / "state.json", {"book": to_dict(BOOK)})
    build(site, sources(book=boom), get=fake_get)
    captured = capsys.readouterr()
    assert "Hurt Me" in (site / "index.html").read_text(encoding="utf-8")
    assert "::warning::book not updated: layout changed" in captured.err
    assert "::warning::" not in captured.out


def test_empty_repo_list_keeps_previous_repos(site, capsys):
    build(site, sources(), get=fake_get)
    before = load_state(site / "data" / "state.json")["repos"]
    build(site, sources(repos=lambda: []), get=fake_get)
    assert load_state(site / "data" / "state.json")["repos"] == before
    assert "::warning::repos not updated" in capsys.readouterr().err


def test_images_are_local(site):
    build(site, sources(), get=fake_get)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert html.count("assets/live/") >= 3
    for s in srcs(html):
        assert not any(h in s for h in EXTERNAL), s
    assert len(list((site / "assets" / "live").iterdir())) >= 3


def test_failed_download_never_hotlinks(site):
    party = site / "data" / "party.toml"
    party.write_text(party.read_text(encoding="utf-8").replace(
        'picture = "assets/party/open-radars-manaus.svg"', 'picture = "%s"' % PIC, 1), encoding="utf-8")
    assert PIC in party.read_text(encoding="utf-8")
    build(site, sources(), get=failing_get)
    html = (site / "index.html").read_text(encoding="utf-8")
    for s in srcs(html):
        assert not any(h in s for h in EXTERNAL), s
    assert PIC not in html


def test_failed_download_keeps_cached_path_for_unchanged_item(site):
    build(site, sources(), get=fake_get)
    first = (site / "index.html").read_text(encoding="utf-8")
    build(site, sources(), get=failing_get)
    assert (site / "index.html").read_text(encoding="utf-8") == first


def test_unused_images_are_pruned(site):
    build(site, sources(), get=fake_get)
    before = set((site / "assets" / "live").iterdir())
    other = Film("Other", "2025", 4.0, False, "2026-11-06", "", "https://a.ltrbxd.com/other.jpg", "")
    build(site, sources(film=lambda: other), get=fake_get)
    after = set((site / "assets" / "live").iterdir())
    assert len(after) == len(before) and after != before


def test_second_build_is_byte_identical(site):
    build(site, sources(), get=fake_get)
    files = ("index.html", "data/state.json")
    first = {f: (site / f).read_bytes() for f in files}
    build(site, sources(), get=fake_get)
    assert {f: (site / f).read_bytes() for f in files} == first
    assert b"\r" not in first["index.html"] and first["data/state.json"].endswith(b"\n")


def test_missing_song_renders_shell(site):
    build(site, sources(song=lambda: None), get=fake_get)
    assert "data-field" in (site / "index.html").read_text(encoding="utf-8")


def test_image_warning_names_the_item(site, capsys):
    build(site, sources(), get=failing_get)
    err = capsys.readouterr().err
    assert "::warning::film poster image not cached: offline" in err
    assert "::warning::book cover image not cached: offline" in err


def test_book_that_left_currently_reading_shows_as_finished(site, capsys):
    from homepage.model import to_dict
    from homepage.sources.goodreads import NothingReading

    def not_reading():
        raise NothingReading("nothing on the currently-reading shelf")

    save_state(site / "data" / "state.json", {"book": to_dict(BOOK)})
    build(site, sources(book=not_reading), get=fake_get)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "Hurt Me" in html and "FINISHED" in html and "TERMINEI" in html
    assert 'class="hp"' not in html  # no progress bar for a finished book
    stored = load_state(site / "data" / "state.json")["book"]
    assert stored["finished"] is True and stored["page"] is None
    assert "::warning::book" not in capsys.readouterr().err  # finishing a book is not a failure
