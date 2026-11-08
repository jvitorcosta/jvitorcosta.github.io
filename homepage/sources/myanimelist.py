"""The anime I'm watching on MyAnimeList, or the last one I finished.

Reads the public list through the JSON the list page itself loads (no key needed). Only what the
row shows is kept: title, cover, link, episode progress, my score and the update date; never notes.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from homepage import http
from homepage.model import Anime

MAL = "https://myanimelist.net"
# status 7 is the whole list; order 5 is last updated first.
LIST_URL = f"{MAL}/animelist/yulong17/load.json?status=7&order=5"
WATCHING, COMPLETED = 1, 2
MANAUS = timezone(timedelta(hours=-4))


def fetch_anime(get: Callable[..., bytes] = http.get) -> Anime | None:
    try:
        entries = json.loads(get(LIST_URL))
    except ValueError as exc:
        raise ValueError(f"list is not JSON: {exc}") from None
    if not isinstance(entries, list):
        raise ValueError("list is not a JSON array")
    entries = sorted(entries, key=lambda e: e.get("updated_at") or 0, reverse=True)
    for status in (WATCHING, COMPLETED):
        for e in entries:
            if e.get("status") == status:
                return _anime(e)
    return None


def _anime(e: dict) -> Anime:
    updated = datetime.fromtimestamp(int(e.get("updated_at") or 0), MANAUS)
    return Anime(
        title=str(e.get("anime_title_eng") or e.get("anime_title") or ""),
        cover=str(e.get("anime_image_path") or ""),
        url=MAL + str(e.get("anime_url") or ""),
        watching=e.get("status") == WATCHING,
        episode=int(e.get("num_watched_episodes") or 0),
        episodes=int(e.get("anime_num_episodes") or 0),
        score=int(e["score"]) if e.get("score") else None,
        date=updated.date().isoformat(),
    )
