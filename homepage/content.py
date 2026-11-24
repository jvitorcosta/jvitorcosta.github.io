"""Hand-written content of the homepage, read from the files in data/."""

from __future__ import annotations

import json
import re
import sys
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
    # What I did there, as (heading, bullets) groups copied from the public resume; may be empty.
    details: tuple[tuple[str, tuple[str, ...]], ...] = ()


@dataclass(frozen=True)
class StudyItem:
    """One concept: a lesson, paper, question or exercise, and how far along it is (0-100)."""
    text: str
    percent: int


@dataclass(frozen=True)
class StudySubtopic:
    title: str
    percent: int
    items: list[StudyItem] = field(default_factory=list)


@dataclass(frozen=True)
class StudyTopic:
    """A topic I am studying now with its subtopics. kind is "study" (concepts) or "lab" (hands-on
    work); exactly one study topic is current, the one on the card."""
    id: str
    title: dict[str, str]
    percent: int
    current: bool = False
    kind: str = "study"
    subtopics: list[StudySubtopic] = field(default_factory=list)


@dataclass(frozen=True)
class Content:
    strings: dict[str, dict[str, str]]
    links: dict[str, str]
    party: list[PartyMember] = field(default_factory=list)
    jobs: list[Job] = field(default_factory=list)
    activity: Activity | None = None
    pc_box: dict[str, dict[str, str]] = field(default_factory=dict)
    study: list[StudyTopic] = field(default_factory=list)
    study_updated: str = ""


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


MAX_STUDY = 16
STUDY_KINDS = {"study", "lab"}
STUDY_TOPIC_KEYS = {"id", "title", "percent", "current", "kind", "subtopics"}
STUDY_SUB_KEYS = {"title", "percent", "items"}
STUDY_ITEM_KEYS = {"text", "percent"}


def _percent(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _study_item(i: dict) -> StudyItem:
    if set(i) != STUDY_ITEM_KEYS or not _text(i["text"]) or not _percent(i["percent"]):
        raise ValueError("an item needs text and a whole percent from 0 to 100, nothing else")
    return StudyItem(i["text"], i["percent"])


def _study_sub(sub: dict) -> StudySubtopic:
    if (set(sub) != STUDY_SUB_KEYS or not _text(sub["title"]) or not _percent(sub["percent"])
            or not isinstance(sub["items"], list) or not sub["items"]):
        raise ValueError("a subtopic needs a title, a percent and items, nothing else")
    return StudySubtopic(sub["title"], sub["percent"], [_study_item(i) for i in sub["items"]])


def _study_topic(t: dict) -> StudyTopic:
    if set(t) != STUDY_TOPIC_KEYS:
        raise ValueError(f"a topic has keys {sorted(t)}, expected {sorted(STUDY_TOPIC_KEYS)}")
    title = {lang: t["title"][lang] for lang in LANGS}
    if not _text(t["id"]) or not all(_text(v) for v in title.values()):
        raise ValueError("id and both titles must be text")
    if not _percent(t["percent"]) or not isinstance(t["current"], bool) or t["kind"] not in STUDY_KINDS:
        raise ValueError("percent, current and kind are invalid")
    if t["current"] and t["kind"] != "study":
        raise ValueError("only a study topic can be current")
    if not isinstance(t["subtopics"], list) or not t["subtopics"]:
        raise ValueError(f"topic {t['id']} needs subtopics")
    return StudyTopic(t["id"], title, t["percent"], t["current"], t["kind"],
                      [_study_sub(sub) for sub in t["subtopics"]])


def _study(path: Path) -> tuple[list[StudyTopic], str]:
    """The generated study progress (tools/study_progress.py); a broken file hides the block."""
    if not path.exists():
        return [], ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        updated = data["updated"]
        if not isinstance(updated, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated):
            raise ValueError("updated must be YYYY-MM-DD")
        topics = [_study_topic(t) for t in data["topics"]]
        if len(topics) > MAX_STUDY or len({t.id for t in topics}) != len(topics):
            raise ValueError(f"at most {MAX_STUDY} topics, each id once")
        if sum(t.current for t in topics) != 1:
            raise ValueError("exactly one topic must be current")
        return topics, updated
    except Exception as exc:
        _warn(f"study block skipped, data/study-progress.json unreadable: {str(exc) or type(exc).__name__}")
        return [], ""


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


def _job_details(path: Path) -> dict[str, tuple[tuple[str, tuple[str, ...]], ...]]:
    """experience.json: {company: [{"heading": "", "items": ["…"]}]}. A broken file means no
    details (the roles still show), with a warning."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {company: tuple((str(g.get("heading", "")), tuple(str(i) for i in g["items"])) for g in groups)
                for company, groups in raw.items()}
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        _warn(f"experience.json skipped: {e}")
        return {}


def load_content(root: Path) -> Content:
    data = Path(root) / "data"
    strings = _toml(data / "strings.toml")
    party = [_member(m) for m in _toml(data / "party.toml").get("member", [])]
    if len(party) > MAX_PARTY:
        raise ValueError(f"party has {len(party)} members, max is {MAX_PARTY}")
    jobs_file = data / "jobs.json"
    details = _job_details(data / "experience.json")
    jobs = [
        Job(j["title"], j["company"], j["start"], j["end"], details.get(j["company"], ()))
        for j in (json.loads(jobs_file.read_text(encoding="utf-8")) if jobs_file.exists() else [])
    ]
    study, study_updated = _study(data / "study-progress.json")
    return Content(
        strings={lang: dict(strings.get(lang, {})) for lang in LANGS},
        links={k: str(v) for k, v in _toml(data / "links.toml").items()},
        party=party,
        jobs=jobs,
        activity=_activity(data / "activity.toml"),
        pc_box=_pc_box(data / "pc_box.toml"),
        study=study,
        study_updated=study_updated,
    )
