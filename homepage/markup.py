"""Shared HTML helpers: escaping, clipping, safe links and the bilingual text helper."""

from __future__ import annotations

import hashlib
import sys
from datetime import date
from functools import cache
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from homepage.content import Content

ARROW = '<span aria-hidden="true">▶</span> '  # decoration before every section title
SITE_ROOT = Path(__file__).resolve().parents[1]
ICONS = "assets/icons"  # pixel app tiles, drawn by tools/pixel_icons.py
# platform: (display name, brand colour of the round profile icon)
PLATFORMS = {
    "spotify": ("Spotify", "#121212"),
    "letterboxd": ("Letterboxd", "#202830"),
    "goodreads": ("Goodreads", "#382110"),
    "strava": ("Strava", "#fc4c02"),
}


def clip(text: str, n: int) -> str:
    """Shorten text to at most n characters, ending with … when cut."""
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def esc(text: str) -> str:
    return escape(text, quote=True)


def safe_url(url: str) -> str:
    """The URL when it is http(s), mailto or site-relative; "" for anything else."""
    url = (url or "").strip()
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme in {"http", "https"} and parsed.netloc:
        return url
    if scheme == "mailto":
        return url
    if url and not scheme and not parsed.netloc and not url.startswith(("/", "\\")):
        return url
    return ""


def content_version(data: bytes) -> str:
    """Short content hash, the same for CRLF and LF checkouts of a text file.
    curriculum-vitae's cv/site.py computes the same value for the pages it copies here."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()[:8]


@cache
def versioned(path: str) -> str:
    """Site-relative asset URL with a content hash, so browsers refetch it when the file changes."""
    return f"{path}?v={content_version((SITE_ROOT / path).read_bytes())}"


def warn(message: str) -> None:
    print(f"::warning::{message}", file=sys.stderr)


class Page:
    """Small helpers bound to one Content."""

    def __init__(self, content: Content):
        self.c = content

    def t(self, key: str, **fmt: object) -> str:
        """Both languages of strings[key], formatted and escaped."""
        return self.both({lang: s[key].format(**fmt) for lang, s in self.c.strings.items()})

    @staticmethod
    def both(text: dict[str, str]) -> str:
        return "".join(f'<span lang="{lang}">{esc(text[lang])}</span>' for lang in ("en", "pt"))

    def date(self, iso: str) -> str:
        try:
            d = date.fromisoformat(iso[:10])
        except ValueError:
            return ""
        return self.both({
            lang: s["date"].format(month=s["months"].split()[d.month - 1], day=d.day)
            for lang, s in self.c.strings.items()
        })

    def go(self, platform: str) -> str:
        """Pixel brand tile at the end of a row, linking to Vitor's profile there."""
        name, colour = PLATFORMS[platform]
        img = f'<img src="{versioned(f"{ICONS}/{platform}.svg")}" alt="" width="40" height="40">'
        link = safe_url(self.c.links.get(platform, ""))
        if not link:
            return f'<span class="go" style="background:{colour}" aria-hidden="true">{img}</span>'
        return (f'<a class="go" href="{esc(link)}" style="background:{colour}">{img}'
                f'<span class="sr">{self.t("profile", app=name)}</span></a>')
