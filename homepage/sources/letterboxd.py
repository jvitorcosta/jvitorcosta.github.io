from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable

from homepage import http
from homepage.model import Film

NS = {"letterboxd": "https://letterboxd.com"}


def fetch_film(user: str = "zubu", get: Callable[[str], bytes] = http.get) -> Film | None:
    root = ET.fromstring(get(f"https://letterboxd.com/{user}/rss/"))
    for item in root.iter("item"):
        title = item.findtext("letterboxd:filmTitle", namespaces=NS)
        if not title:  # lists and other non-film entries
            continue
        desc = item.findtext("description") or ""
        poster = re.search(r'<img src="([^"]+)"', desc)
        review = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", desc)).split())
        rating = item.findtext("letterboxd:memberRating", namespaces=NS)
        return Film(
            title=title,
            year=item.findtext("letterboxd:filmYear", namespaces=NS) or "",
            rating=float(rating) if rating else None,
            liked=item.findtext("letterboxd:memberLike", namespaces=NS) == "Yes",
            watched=item.findtext("letterboxd:watchedDate", namespaces=NS) or "",
            # A diary entry without a review has "Watched on ..." as its only text.
            review="" if review.startswith("Watched on ") else review,
            poster=poster.group(1).replace("-0-600-0-900-", "-0-230-0-345-") if poster else "",
            url=item.findtext("link") or "",
        )
    return None
