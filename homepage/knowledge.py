"""knowledge.json: the public facts the Ask Vitor API answers from."""

from __future__ import annotations

import json
import re
from pathlib import Path

from homepage.markup import warn
from homepage.model import AboutFact, LiveData, Repo

FACT_ID = re.compile(r"[a-z0-9._-]+")

# Never-share categories: nothing matching these may reach knowledge.json. The build test scans
# every fact against them; a hit means a source or about.toml row leaks something private.
NEVER_SHARE_PATTERNS = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b",  # CPF
    r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dx]\b",  # RG
    r"\b(?:cpf|rg|passport|passaporte)\b",
    r"\d{8,}",  # long id-like numbers
    r"(?:\+?\d{2}\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]\d{4}\b",  # phone number
    r"\b(?:rua|avenida|av\.|travessa|street|st\.|road|rd\.)\s+\w[\w ]*\d",  # street address
    r"\b(?:endereço|address|bairro)\b",
    r"\b(?:salary|salário|salario)\b",  # salary
    r"(?:R\$|USD|US\$)\s?\d[\d.,]*\s?(?:k|mil)?\s*(?:/|per |por |a )\s*(?:month|mês|mes|year|ano|hour|hora)\b",
    r"\bheart rate\b|\bfrequência cardíaca\b|\d\s?bpm\b",
    r"\b\d+(?:[.,]\d+)?\s?kg\b|\bbody weight\b|\bpeso corporal\b",  # body weight
))


def _fact(id: str, source: str, updated: str, text: str) -> dict:
    return {"id": id, "source": source, "updated": updated, "text": text}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-")


def _sport(name: str) -> str:
    """Strava's sport type in words with its article: "WeightTraining" -> "a weight training"."""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).lower()
    return f"{'an' if words[:1] in set('aeiou') else 'a'} {words}"


def _valid(facts: list[dict]) -> list[dict]:
    """Drops facts with a malformed or repeated id, so one bad row can't make the API reject the file."""
    seen: set[str] = set()
    kept = []
    for f in facts:
        if not FACT_ID.fullmatch(f["id"]) or f["id"] in seen:
            warn(f"knowledge fact dropped, bad or repeated id: {f['id']!r}")
            continue
        seen.add(f["id"])
        kept.append(f)
    return kept


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
        text = f"Vitor's latest Strava activity was {_sport(t.sport)}"
        text += f" of {t.distance_km:g} km." if t.distance_km else "."
        facts.append(_fact("live.activity", "Strava", when("activity"), text))
    return {"version": 1, "generated": today, "facts": _valid(facts)}


def write_knowledge(path: Path, data: dict) -> None:
    text = json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    Path(path).write_bytes(text.encode("utf-8"))
