from __future__ import annotations

import html
import re
from collections.abc import Callable

from homepage import http
from homepage.model import Book

GOODREADS = "https://www.goodreads.com"
GOODREADS_PROFILE = f"{GOODREADS}/user/show/185113793-vitor-pinheiro"
NO_BOOK = "no currently-reading book on the profile page"
# Only on a real profile page: tells "he finished the book" apart from "the page changed".
PROFILE_MARKER = 'id="profileNameTopHeading"'


class NothingReading(ValueError):
    """The profile loaded but lists no currently-reading book."""


def _text(raw: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


def fetch_book(profile_url: str = GOODREADS_PROFILE, get: Callable[..., bytes] = http.get) -> Book | None:
    page = get(profile_url).decode("utf-8", errors="replace")
    start = page.find('id="currentlyReadingReviews"')
    if start < 0:
        raise (NothingReading if PROFILE_MARKER in page else ValueError)(NO_BOOK)
    block = page[start:]
    # Only the first entry: stop at the next one so its progress is never read.
    first = block.find('class="Updates')
    if first < 0:
        raise ValueError(NO_BOOK)
    entry = block[first + 1 :]
    second = entry.find('class="Updates')
    entry = block[first:] if second < 0 else entry[:second]

    title = re.search(r'<a[^>]*class="bookTitle"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', entry, re.S)
    if not title:
        title = re.search(r'<a[^>]*href="([^"]+)"[^>]*class="bookTitle"[^>]*>(.*?)</a>', entry, re.S)
    if not title:
        raise ValueError(NO_BOOK)
    author = re.search(r'<a[^>]*class="authorName"[^>]*>(.*?)</a>', entry, re.S)
    cover = re.search(r'class="firstcol".*?<img[^>]*\ssrc="([^"]+)"', entry, re.S)
    progress = re.search(r"\(page (\d+) of (\d+)\)", entry)
    return Book(
        title=_text(title.group(2)),
        author=_text(author.group(1)) if author else "",
        cover=html.unescape(cover.group(1)).replace("._SX98_.", "._SX318_.") if cover else "",
        url=GOODREADS + html.unescape(title.group(1)),
        page=int(progress.group(1)) if progress else None,
        pages=int(progress.group(2)) if progress else None,
    )
