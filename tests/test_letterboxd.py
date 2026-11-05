from pathlib import Path

from homepage.sources.letterboxd import fetch_film

FIXTURE = (Path(__file__).parent / "fixtures" / "letterboxd.xml").read_bytes()


def fetch(xml: bytes = FIXTURE, user: str = "zubu"):
    return fetch_film(user, get=lambda url: xml)


def test_skips_non_film_items_and_reads_the_first_film():
    film = fetch()
    assert film.title == "Hope"
    assert film.year == "2026"
    assert film.rating == 3.5
    assert film.liked is True
    assert film.watched == "2026-11-05"
    assert film.url == "https://letterboxd.com/zubu/film/hope-2026/"


def test_review_text_is_unescaped_plain_text():
    review = fetch().review
    assert "bem & rápido" in review
    assert "🤤" in review
    assert "<" not in review


def test_watched_on_only_means_no_review():
    head, lst, hope, watched = FIXTURE.decode("utf-8").split("<item>")
    film = fetch(f"{head}<item>{watched}".encode("utf-8"))
    assert film.title == "Killers of the Flower Moon"
    assert film.review == ""


def test_poster_uses_230_size():
    assert "-0-230-0-345-" in fetch().poster
    assert "-0-600-0-900-" not in fetch().poster


def test_feed_without_films_returns_none():
    xml = b'<rss xmlns:letterboxd="https://letterboxd.com"><channel><item><title>x</title></item></channel></rss>'
    assert fetch(xml) is None
