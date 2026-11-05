from __future__ import annotations

from pathlib import Path

import pytest

from homepage.sources import goodreads

FIXTURES = Path(__file__).parent / "fixtures"


def _get(name: str):
    return lambda url, headers=None: (FIXTURES / name).read_bytes()


def test_reads_first_currently_reading_book():
    book = goodreads.fetch_book(get=_get("goodreads-profile.html"))
    assert book.title == "Can't Hurt Me: Master Your Mind and Defy the Odds"
    assert book.author == "David Goggins"
    assert (book.page, book.pages) == (210, 366)
    assert book.cover.endswith("._SX318_.jpg")
    assert book.url.startswith("https://www.goodreads.com/book/show/41721428")


def test_missing_block_raises_value_error():
    with pytest.raises(ValueError, match="no currently-reading book"):
        goodreads.fetch_book(get=_get("goodreads-empty.html"))


def test_title_entities_are_unescaped():
    book = goodreads.fetch_book(get=_get("goodreads-profile.html"))
    assert "&#39;" not in book.title
    assert "'" in book.title


def test_profile_without_a_current_book_says_nothing_is_being_read():
    # The page loaded fine (his name is on it) but the currently-reading list is gone.
    with pytest.raises(goodreads.NothingReading):
        goodreads.fetch_book(get=_get("goodreads-not-reading.html"))


def test_unrecognised_page_is_a_plain_failure_not_a_finished_book():
    with pytest.raises(ValueError) as exc:
        goodreads.fetch_book(get=_get("goodreads-empty.html"))
    assert not isinstance(exc.value, goodreads.NothingReading)
