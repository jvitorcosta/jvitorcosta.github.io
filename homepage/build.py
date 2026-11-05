"""Daily build: refresh the live sources, cache their images, render index.html."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from homepage import http
from homepage.content import load_content
from homepage.images import cache_image, prune
from homepage.model import Book, Film, LiveData, Repo, Song
from homepage.render import render_home
from homepage.sources.github import fetch_repos
from homepage.sources.goodreads import fetch_book
from homepage.sources.letterboxd import fetch_film
from homepage.sources.spotify import fetch_song
from homepage.state import load_state, refresh, save_state

LIVE_DIR = Path("assets") / "live"


def default_sources(token: str | None = None) -> dict[str, Callable[[], object]]:
    return {
        "song": fetch_song,
        "film": fetch_film,
        "book": fetch_book,
        "repos": lambda: fetch_repos(token=token),
    }


def build(
    root: Path,
    sources: dict[str, Callable[[], object]] | None = None,
    get: Callable[..., bytes] = http.get,
) -> Path:
    root = Path(root)
    sources = sources if sources is not None else default_sources()
    content = load_content(root)
    state_path = root / "data" / "state.json"
    state = load_state(state_path)
    live_dir = root / LIVE_DIR
    used: set[str] = set()

    def local(url: str) -> str:
        """Cache a remote image and return its site path; never keep the remote URL."""
        if not url:
            return ""
        if not url.startswith(("http://", "https://")):
            return url
        try:
            path = cache_image(url, live_dir, get)
        except Exception as exc:
            print(f"::warning::image not cached: {exc}", file=sys.stderr)
            return ""
        used.add(path)
        return path

    song = refresh("song", sources["song"], state, Song)
    film = refresh("film", sources["film"], state, Film)
    book = refresh("book", sources["book"], state, Book)
    repo_fetch = sources["repos"]
    repos = refresh("repos", lambda: repo_fetch() or None, state, Repo) or []

    if song:
        song = replace(song, cover=local(song.cover))
    if film:
        film = replace(film, poster=local(film.poster))
    if book:
        book = replace(book, cover=local(book.cover))
    content = replace(
        content,
        party=[replace(m, picture=local(m.picture)) for m in content.party],
    )

    live_dir.mkdir(parents=True, exist_ok=True)
    prune(live_dir, used)
    live = LiveData(song=song, film=film, book=book, activity=content.activity)
    html = render_home(content, live, repos, root)
    index = root / "index.html"
    index.write_bytes(html.replace("\r\n", "\n").encode("utf-8"))
    save_state(state_path, state)
    return index


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN") or None
    index = build(Path(__file__).resolve().parents[1], default_sources(token))
    print(f"wrote {index}")


if __name__ == "__main__":
    main()
