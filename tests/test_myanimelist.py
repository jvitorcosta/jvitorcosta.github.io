import json
from pathlib import Path

import pytest

from homepage.sources.myanimelist import fetch_anime

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "myanimelist.json").read_text(encoding="utf-8"))


def fetch(entries=FIXTURE):
    calls = []

    def get(url, headers=None):
        calls.append(url)
        return json.dumps(entries).encode()

    return fetch_anime(get=get), calls


def test_reads_the_public_list_of_yulong17():
    _, calls = fetch()
    assert calls == ["https://myanimelist.net/animelist/yulong17/load.json?status=7&order=5"]


def test_watching_wins_over_newer_plan_to_watch_and_older_finished():
    anime, _ = fetch()
    assert anime.title == "Cyberpunk: Edgerunners" and anime.watching
    assert (anime.episode, anime.episodes) == (1, 10)
    assert anime.url == "https://myanimelist.net/anime/42310/Cyberpunk__Edgerunners"
    assert anime.cover.startswith("https://cdn.myanimelist.net/r/192x272/images/anime/1818/")
    assert anime.date == "2026-11-08"


def test_without_watching_shows_the_latest_finished_with_english_title_and_score():
    anime, _ = fetch([e for e in FIXTURE if e["status"] != 1])
    assert anime.title == "Evangelion: 3.0+1.0 Thrice Upon a Time"
    assert not anime.watching and anime.score == 10


def test_unscored_anime_has_no_score():
    anime, _ = fetch()
    assert anime.score is None


def test_never_keeps_notes():
    anime, _ = fetch()
    assert "private note" not in json.dumps(anime.__dict__)


def test_nothing_watched_or_finished_means_no_row():
    anime, _ = fetch(FIXTURE[:1])
    assert anime is None


@pytest.mark.parametrize("body", [b"<html>login</html>", b'{"errors": []}'])
def test_unexpected_answer_raises_so_the_last_value_is_kept(body):
    with pytest.raises(ValueError):
        fetch_anime(get=lambda url, headers=None: body)
