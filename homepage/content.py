"""Hand-written content of the homepage, read from the files in data/."""

from __future__ import annotations

import json
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from homepage.model import AboutFact, Activity, from_dict

MAX_PARTY = 6
LANGS = ("en", "pt")


@dataclass(frozen=True)
class PartyMember:
    repo: str
    tag: str
    picture: str
    name: dict[str, str]
    blurb: dict[str, str]
    url: str
    emoji: str = ""


@dataclass(frozen=True)
class Job:
    title: str
    company: str
    start: str
    end: str


@dataclass(frozen=True)
class Content:
    strings: dict[str, dict[str, str]]
    links: dict[str, str]
    party: list[PartyMember] = field(default_factory=list)
    jobs: list[Job] = field(default_factory=list)
    activity: Activity | None = None
    pc_box: dict[str, dict[str, str]] = field(default_factory=dict)
    about: list[AboutFact] = field(default_factory=list)


def _toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _warn(message: str) -> None:
    print(f"::warning::{message}", file=sys.stderr)


def _activity(path: Path) -> Activity | None:
    """The hand-written last activity; a broken file skips the row instead of failing the job."""
    try:
        d = _toml(path).get("activity")
        if d is None:
            return None
        if not isinstance(d, dict):
            raise ValueError("[activity] must be a table")
        act = from_dict(Activity, {"distance_km": None, "url": "", **d})
        text = ("sport", "emoji", "title", "detail", "date", "url")
        if not all(isinstance(getattr(act, f), str) for f in text):
            raise ValueError(f"{', '.join(text)} must be text")
        if not isinstance(act.moving_min, int) or isinstance(act.moving_min, bool):
            raise ValueError("moving_min must be a whole number")
        if act.distance_km is not None and (
                not isinstance(act.distance_km, (int, float)) or isinstance(act.distance_km, bool)):
            raise ValueError("distance_km must be a number")
        return act
    except Exception as exc:
        reason = str(exc) or type(exc).__name__
        _warn(f"activity row skipped, data/activity.toml unreadable: {reason}")
        return None


def _about(path: Path) -> list[AboutFact]:
    """The hand-written facts for the Ask Vitor assistant; a bad row is skipped with a warning."""
    facts = []
    for i, row in enumerate(_toml(path).get("fact", [])):
        try:
            fact = AboutFact(row["id"], row["source"], row["text"])
            if not all(isinstance(v, str) and v.strip() for v in (fact.id, fact.source, fact.text)):
                raise ValueError("id, source and text must be non-empty text")
            facts.append(fact)
        except Exception as exc:
            _warn(f"about fact #{i + 1} skipped: {str(exc) or type(exc).__name__}")
    return facts


def _pc_box(path: Path) -> dict[str, dict[str, str]]:
    texts = {}
    for name, text in _toml(path).items():
        if not isinstance(text, dict):
            _warn(f"pc_box {name} skipped: expected a table with en and pt")
            continue
        texts[name] = {lang: str(text[lang]) for lang in LANGS if text.get(lang)}
        for key in ("case", "title_en", "title_pt", "tag"):
            if text.get(key):
                texts[name][key] = str(text[key])
        if text.get("pin") is True:
            texts[name]["pin"] = "true"
    return texts


def _member(d: dict) -> PartyMember:
    return PartyMember(
        repo=d["repo"],
        tag=d["tag"],
        picture=d.get("picture", ""),
        name={lang: d[f"name_{lang}"] for lang in LANGS},
        blurb={lang: d[f"blurb_{lang}"] for lang in LANGS},
        url=d.get("url", ""),
        emoji=d.get("emoji", ""),
    )


def load_content(root: Path) -> Content:
    data = Path(root) / "data"
    strings = _toml(data / "strings.toml")
    party = [_member(m) for m in _toml(data / "party.toml").get("member", [])]
    if len(party) > MAX_PARTY:
        raise ValueError(f"party has {len(party)} members, max is {MAX_PARTY}")
    jobs_file = data / "jobs.json"
    jobs = [
        Job(j["title"], j["company"], j["start"], j["end"])
        for j in (json.loads(jobs_file.read_text(encoding="utf-8")) if jobs_file.exists() else [])
    ]
    return Content(
        strings={lang: dict(strings.get(lang, {})) for lang in LANGS},
        links={k: str(v) for k, v in _toml(data / "links.toml").items()},
        party=party,
        jobs=jobs,
        activity=_activity(data / "activity.toml"),
        pc_box=_pc_box(data / "pc_box.toml"),
        about=_about(data / "about.toml"),
    )
