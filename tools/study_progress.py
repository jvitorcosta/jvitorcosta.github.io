"""Computes data/study-progress.json from the study roadmap note in the vault.

    uv run --python 3.12 python tools/study_progress.py --vault <vault folder>

The roadmap note holds one `## ` topic per bar candidate; its comment
(`<!-- topic id=... role=... now=yes|no pt="..." -->`) marks the topic. Each `- ` line under it is one item:
  - `- [ ]` / `- [x]`    0 or 100%
  - `- [[Note]]`         the note's `status` (todo 0, in-progress or reading 50, done 100)
  - `- [[Note#Heading]]` the share of ticked checkboxes under that heading of the note
A topic's percent is the average of its items. Only `now=yes` topics are written, and exactly one of
them is `current=yes`: the site's card shows that one, and its tree lists every written topic with
its items. Written: ids, titles, percents and item labels (a checkbox's text, or a note's name):
no paths. The site renders the file and computes nothing.
Nothing here commits or pushes: review the diff, then open a PR.

Exit codes: 0 ok, 1 `--check` found the file out of date, 2 a bad roadmap or a missing vault.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from datetime import date
from pathlib import Path

DEFAULT_NOTE = "AI Engineer and FDE Roadmap"  # a note name, found anywhere in the vault
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "study-progress.json"
STATUS_SHARE = {"todo": 0.0, "later": 0.0, "next": 0.0, "in-progress": 0.5, "reading": 0.5,
                "active": 0.5, "done": 1.0}
TOPIC = re.compile(r"^##\s+(?P<title>.*?)\s*<!--\s*topic\s+(?P<attrs>.*?)-->\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
BOX = re.compile(r"^\s*[-*]\s+\[(?P<mark>[ xX])\]\s*(?P<text>.*?)\s*$")
LINK = re.compile(r"^\s*[-*]\s+\[\[(?P<target>[^\]|]+)(?:\|[^\]]*)?\]\]\s*$")
NUMBER = re.compile(r"^\d+\.\s*")


class RoadmapError(Exception):
    pass


def _body(text: str) -> tuple[dict[str, str], list[str]]:
    """Frontmatter keys (flat) and the body lines of a note."""
    text = text.replace("\r\n", "\n")
    meta: dict[str, str] = {}
    if text.startswith("---\n"):
        head, sep, rest = text[4:].partition("\n---")
        if sep:
            for line in head.splitlines():
                key, colon, value = line.partition(":")
                if colon and not key.startswith((" ", "\t")):
                    meta[key.strip()] = value.strip().strip("\"'")
            text = rest.split("\n", 1)[1] if "\n" in rest else ""
    return meta, text.splitlines()


def _index(vault: Path) -> dict[str, Path]:
    notes: dict[str, Path] = {}
    for path in sorted(vault.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(vault).parts):
            continue
        notes.setdefault(path.stem, path)
    return notes


def _heading_share(lines: list[str], heading: str, note: str) -> float:
    level = None
    ticked = total = 0
    for line in lines:
        h = HEADING.match(line)
        if h:
            if level is not None and len(h.group(1)) <= level:
                break
            if level is None and h.group(2) == heading:
                level = len(h.group(1))
            continue
        box = BOX.match(line) if level is not None else None
        if box:
            total += 1
            ticked += box.group("mark") != " "
    if level is None or not total:
        raise RoadmapError(f"{note}#{heading}: no checkboxes under that heading")
    return ticked / total


def _item_label(target: str) -> str:
    name, _, heading = target.partition("#")
    name = name.strip()
    return f"{name}: {heading.strip()}" if heading.strip() else name


def _item_share(target: str, notes: dict[str, Path]) -> float:
    name, _, heading = target.partition("#")
    name = name.strip()
    if name not in notes:
        raise RoadmapError(f"link [[{target}]] matches no note in the vault")
    meta, lines = _body(notes[name].read_text(encoding="utf-8"))
    if heading:
        return _heading_share(lines, heading.strip(), name)
    status = meta.get("status", "")
    if status not in STATUS_SHARE:
        raise RoadmapError(f"[[{name}]] has status {status!r}, which has no percent")
    return STATUS_SHARE[status]


def _attrs(raw: str, title: str) -> dict[str, str]:
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        raise RoadmapError(f"topic {title!r}: unreadable comment ({exc})") from exc
    return dict(p.partition("=")[::2] for p in parts)


def build(vault: Path, note: str = DEFAULT_NOTE, today: str | None = None, only_now: bool = True) -> dict:
    vault = Path(vault)
    notes = _index(vault)
    if note not in notes:
        raise RoadmapError(f"roadmap note not found: {note}")
    _, lines = _body(notes[note].read_text(encoding="utf-8"))
    topics: list[dict] = []
    seen: set[str] = set()
    current: dict | None = None

    def close() -> None:
        if current is not None:
            if not current["items"]:
                raise RoadmapError(f"topic {current['id']} has no items")
            shares = [s for _, s in current["items"]]
            current["percent"] = int(sum(shares) / len(shares) * 100 + 0.5)
            topics.append(current)

    for line in lines:
        head = TOPIC.match(line)
        if head:
            close()
            title = NUMBER.sub("", head.group("title"))
            attrs = _attrs(head.group("attrs"), title)
            tid = attrs.get("id", "")
            if not tid or not attrs.get("pt"):
                raise RoadmapError(f"topic {title!r} needs id= and pt= in its comment")
            if tid in seen:
                raise RoadmapError(f"duplicate topic id {tid}")
            seen.add(tid)
            current = {"id": tid, "title": {"en": title, "pt": attrs["pt"]}, "now": attrs.get("now") == "yes",
                       "current": attrs.get("current") == "yes", "items": []}
            continue
        h2 = HEADING.match(line)
        if h2 and h2.group(1) == "##":
            close()
            current = None  # a plain ## heading ends the topic
            continue
        if current is None:
            continue
        box, link = BOX.match(line), LINK.match(line)
        if box:
            current["items"].append((box.group("text"), 0.0 if box.group("mark") == " " else 1.0))
        elif link:
            target = link.group("target")
            current["items"].append((_item_label(target), _item_share(target, notes)))
    close()
    shown = [t for t in topics if t["now"] or not only_now]
    if only_now and sum(t["current"] for t in shown) != 1:
        raise RoadmapError("exactly one now=yes topic must also be current=yes")
    if any(t["current"] and not t["now"] for t in topics):
        raise RoadmapError("the current topic must be now=yes")
    out = [{"id": t["id"], "title": t["title"], "percent": t["percent"], "current": t["current"],
            "items": [{"text": text, "percent": int(share * 100 + 0.5)} for text, share in t["items"]]}
           for t in shown]
    return {"updated": today or date.today().isoformat(), "topics": out}


def render(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write data/study-progress.json from the roadmap note.")
    ap.add_argument("--vault", default=os.environ.get("STUDY_VAULT"), help="vault folder (or set STUDY_VAULT)")
    ap.add_argument("--note", default=DEFAULT_NOTE, help="roadmap note name")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--today", help="YYYY-MM-DD, for tests")
    ap.add_argument("--check", action="store_true", help="exit 1 if the file is out of date; write nothing")
    args = ap.parse_args(argv)
    if not args.vault:
        print("error: give --vault <folder> or set STUDY_VAULT", file=sys.stderr)
        return 2
    try:
        data = build(Path(args.vault), args.note, args.today)
    except RoadmapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.check:
        try:
            old = json.loads(args.out.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            old = None
        same = old is not None and {**old, "updated": ""} == {**data, "updated": ""}
        print("study-progress.json is up to date" if same else "study-progress.json is out of date")
        return 0 if same else 1
    args.out.write_bytes(render(data).encode("utf-8"))
    print(f"wrote {args.out}: " + ", ".join(f"{t['id']} {t['percent']}%" for t in data["topics"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
