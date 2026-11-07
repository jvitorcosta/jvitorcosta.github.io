"""Daily build: refresh the live sources, cache their images, render index.html."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import replace
from datetime import date
from pathlib import Path

from homepage import http
from homepage.content import load_content
from homepage.images import cache_image, prune
from homepage.model import Activity, Book, Film, LiveData, Repo, Song, from_dict
from homepage.render import render_404, render_home
from homepage.sources.github import fetch_repos
from homepage.sources.goodreads import NothingReading, fetch_book
from homepage.sources.letterboxd import fetch_film
from homepage.sources.spotify import fetch_song
from homepage.sources.strava import fetch_activity
from homepage.state import load_state, refresh, save_state, stale_sources

LIVE_DIR = Path("assets") / "live"


def default_sources(token: str | None = None) -> dict[str, Callable[[], object]]:
    sources: dict[str, Callable[[], object]] = {
        "song": fetch_song,
        "film": fetch_film,
        "book": fetch_book,
        "repos": lambda: fetch_repos(token=token),
    }
    # Strava only when the workflow has my app's secrets; otherwise data/activity.toml is the row.
    strava = [os.environ.get(k) for k in ("STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN")]
    if all(strava):
        client_id, client_secret, refresh_token = strava
        sources["activity"] = lambda: fetch_activity(client_id, client_secret, refresh_token)
    return sources


def build(
    root: Path,
    sources: dict[str, Callable[[], object]] | None = None,
    get: Callable[..., bytes] = http.get,
    today: str | None = None,
) -> Path:
    root = Path(root)
    today = today or date.today().isoformat()
    sources = sources if sources is not None else default_sources()
    content = load_content(root)
    state_path = root / "data" / "state.json"
    state = load_state(state_path)
    live_dir = root / LIVE_DIR
    used: set[str] = set()

    def local(url: str, label: str) -> str:
        """Cache a remote image and return its site path; never keep the remote URL."""
        if not url:
            return ""
        if not url.startswith(("http://", "https://")):
            return url
        try:
            path = cache_image(url, live_dir, get)
        except Exception as exc:
            print(f"::warning::{label} image not cached: {exc}", file=sys.stderr)
            return ""
        used.add(path)
        return path

    song = refresh("song", sources["song"], state, Song, today)
    film = refresh("film", sources["film"], state, Film, today)
    book_fetch = sources["book"]

    def book_or_finished() -> Book:
        """A book that left the currently-reading shelf was finished: keep it, without progress."""
        try:
            return book_fetch()
        except NothingReading:
            if not isinstance(state.get("book"), dict):
                raise
            last = from_dict(Book, state["book"])
            return replace(last, page=None, pages=None, finished=True)

    book = refresh("book", book_or_finished, state, Book, today)
    repo_fetch = sources["repos"]
    repos = refresh("repos", lambda: repo_fetch() or None, state, Repo, today) or []
    activity = content.activity  # the hand-written row, when Strava is off or has nothing yet
    if "activity" in sources:
        activity = refresh("activity", sources["activity"], state, Activity, today) or activity

    if song:
        song = replace(song, cover=local(song.cover, "song cover"))
    if film:
        film = replace(film, poster=local(film.poster, "film poster"))
    if book:
        book = replace(book, cover=local(book.cover, "book cover"))
    content = replace(
        content,
        party=[replace(m, picture=local(m.picture, f"party {m.repo} picture")) for m in content.party],
    )

    live_dir.mkdir(parents=True, exist_ok=True)
    prune(live_dir, used)
    live = LiveData(song=song, film=film, book=book, activity=activity)
    html = render_home(content, live, repos, root)
    index = root / "index.html"
    index.write_bytes(html.replace("\r\n", "\n").encode("utf-8"))
    (root / "404.html").write_bytes(render_404(content).replace("\r\n", "\n").encode("utf-8"))
    save_state(state_path, state)
    report_stale(state, today)
    return index


def report_stale(state: dict, today: str) -> None:
    """Warn about sources that kept an old value for over a week, list them in the run summary,
    and hand their names to the workflow's alert job (step output `stale`)."""
    stale = stale_sources(state, today)
    for name, age in stale:
        print(f"::warning::{name} has not updated for {age} days", file=sys.stderr)
    if not stale:
        return
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"stale={' '.join(name for name, _ in stale)}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        rows = "".join(f"| {name} | {state['updated'][name]} | {age} |\n" for name, age in stale)
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### Sources not updating\n\n| Source | Last update | Days |\n|---|---|---|\n" + rows)


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN") or None
    index = build(Path(__file__).resolve().parents[1], default_sources(token))
    print(f"wrote {index}")


if __name__ == "__main__":
    main()
