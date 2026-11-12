"""knowledge.json: the public facts the Ask Vitor API answers from."""

from __future__ import annotations

import json
import re
from pathlib import Path

from homepage.model import AboutFact, LiveData, Repo


def _fact(id: str, source: str, updated: str, text: str) -> dict:
    return {"id": id, "source": source, "updated": updated, "text": text}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-")


def build_knowledge(
    about: list[AboutFact], repos: list[Repo], live: LiveData, updated: dict[str, str], today: str
) -> dict:
    facts = [_fact(a.id, a.source, today, a.text) for a in about]

    def when(name: str) -> str:
        return updated.get(name) or today

    for r in repos:
        text = f"Vitor's GitHub project {r.name}"
        text += f": {r.description}" if r.description else ""
        facts.append(_fact(f"repo.{_slug(r.name)}", "GitHub", when("repos"), f"{text} ({r.url})"))
    if live.song:
        s = live.song
        facts.append(_fact("live.song", "Spotify", when("song"), f"Vitor last played {s.title} by {s.artist}."))
    if live.film:
        f = live.film
        text = f"Vitor last watched {f.title} ({f.year})"
        text += f", rated {f.rating:g} out of 5" if f.rating is not None else ""
        text += ", and liked it." if f.liked else "."
        facts.append(_fact("live.film", "Letterboxd", when("film"), text))
    if live.book:
        b = live.book
        state = "finished reading" if b.finished else "is reading"
        facts.append(_fact("live.book", "Goodreads", when("book"), f"Vitor {state} {b.title} by {b.author}."))
    if live.anime:
        a = live.anime
        if a.watching:
            total = f" of {a.episodes}" if a.episodes else ""
            text = f"Vitor is watching the anime {a.title}, at episode {a.episode}{total}."
        else:
            text = f"Vitor last finished the anime {a.title}."
        facts.append(_fact("live.anime", "MyAnimeList", when("anime"), text))
    if live.activity:
        t = live.activity
        text = f"Vitor's latest Strava activity was a {t.sport.lower()}"
        text += f" of {t.distance_km:g} km." if t.distance_km else "."
        facts.append(_fact("live.activity", "Strava", when("activity"), text))
    return {"version": 1, "generated": today, "facts": facts}


def write_knowledge(path: Path, data: dict) -> None:
    text = json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    Path(path).write_bytes(text.encode("utf-8"))
