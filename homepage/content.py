"""Hand-written content of the homepage, read from the files in data/."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from homepage.model import Activity, from_dict

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


def _toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


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
    activity = _toml(data / "activity.toml").get("activity")
    return Content(
        strings={lang: dict(strings.get(lang, {})) for lang in LANGS},
        links={k: str(v) for k, v in _toml(data / "links.toml").items()},
        party=party,
        jobs=jobs,
        activity=from_dict(Activity, {"distance_km": None, "url": "", **activity})
        if activity else None,
    )
