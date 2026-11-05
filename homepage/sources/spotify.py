from __future__ import annotations

import json
from collections.abc import Callable

from homepage import http
from homepage.model import Song

SPOTIFY_BASE = "https://spotify-now-playing-ashen-two.vercel.app"


def fetch_song(get: Callable[..., bytes] = http.get) -> Song | None:
    try:
        data = json.loads(get(f"{SPOTIFY_BASE}/api/now-playing.json"))
    except json.JSONDecodeError as e:
        raise ValueError(f"spotify returned non-JSON: {e}") from e
    if not isinstance(data, dict) or "error" in data:
        raise ValueError(f"spotify error: {data.get('error') if isinstance(data, dict) else data}")
    return Song(
        title=data.get("title") or "",
        artist=data.get("artist") or "",
        cover=data.get("cover") or "",
        url=data.get("url") or "",
        playing=bool(data.get("playing")),
    )
