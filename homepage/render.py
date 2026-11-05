"""Renders index.html from the hand-written content, the live data and the repo list.

Every user-facing text is written in both languages as
<span lang="en">…</span><span lang="pt">…</span>; assets/site.css hides the other one.
"""

from __future__ import annotations

import json
from datetime import date
from html import escape
from pathlib import Path

from homepage.content import Content, PartyMember
from homepage.model import Activity, Book, Film, LiveData, Repo, Song

SITE = "https://jvitorcosta.github.io/"
OG_IMAGE = SITE + "og-image.png"
GITHUB_REPOS = "https://github.com/jvitorcosta?tab=repositories"
SPOTIFY_ENDPOINT = "https://spotify-now-playing-ashen-two.vercel.app/api/now-playing.json"
ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@11.14.0/icons"
FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700"
         "&family=Press+Start+2P&display=swap")
PC_BOX_ROWS = 8
PALETTES = (("pocket", "Pocket", "#fbfaf4"), ("night", "Night Menu", "#221d33"),
            ("nu", "Nu Purple", "#820ad1"))
# platform: (display name, brand colour of the round profile icon)
PLATFORMS = {
    "spotify": ("Spotify", "#1db954"),
    "letterboxd": ("Letterboxd", "#202830"),
    "goodreads": ("Goodreads", "#553b08"),
    "strava": ("Strava", "#fc4c02"),
}
TRAINER_LINKS = (("instagram", "Instagram"), ("github", "GitHub"),
                 ("linkedin", "LinkedIn"), ("email", "Email"))


def clip(text: str, n: int) -> str:
    """Shorten text to at most n characters, ending with … when cut."""
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def esc(text: str) -> str:
    return escape(text, quote=True)


class _Page:
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
        """Round brand icon at the end of a row, linking to Vitor's profile there."""
        name, colour = PLATFORMS[platform]
        img = f'<img src="{ICONS}/{platform}.svg" alt="" width="17" height="17">'
        link = self.c.links.get(platform, "")
        if not link:
            return f'<span class="go" style="background:{colour}" aria-hidden="true">{img}</span>'
        return (f'<a class="go" href="{esc(link)}" style="background:{colour}">{img}'
                f'<span class="sr">{self.t("profile", app=name)}</span></a>')


def _row(url: str, inner: str) -> str:
    if url:
        return f'<a class="row" href="{esc(url)}">{inner}</a>'
    return f'<div class="row">{inner}</div>'


def _thumb(src: str, tall: bool = False, field: str = "") -> str:
    attrs = f' data-field="{field}"' if field else ""
    if not src and not field:
        return ""
    src_attr = f' src="{esc(src)}"' if src else ""
    cls = "th tall" if tall else "th"
    h = 66 if tall else 46
    return f'<img class="{cls}"{attrs}{src_attr} alt="" width="46" height="{h}" loading="lazy">'


def _song(p: _Page, song: Song) -> str:
    label_key = "listening" if song.playing else "last_played"
    s = p.c.strings
    labels = " ".join(
        f'data-{key.replace("_", "-")}-{lang}="{esc(s[lang][key])}"'
        for key in ("listening", "last_played") for lang in ("en", "pt")
    )
    hidden = "" if song.playing else " hidden"
    body = (
        f'<span class="k px" data-field="label">{p.t(label_key)}</span>'
        f'<span class="t"><span data-field="title">{esc(song.title)}</span>'
        f' <span class="badge" data-field="badge"{hidden}>ON</span></span>'
        f'<span data-field="artist">{esc(song.artist)}</span>'
    )
    inner = _thumb(song.cover, field="cover") + f'<div class="body">{body}</div>'
    playing = "true" if song.playing else "false"
    return (f'<li id="spotify-row" data-endpoint="{SPOTIFY_ENDPOINT}" data-playing="{playing}" '
            f'{labels}>{_row(song.url, inner)}{p.go("spotify")}</li>')


def _stars(rating: float | None) -> str:
    if rating is None:
        return ""
    whole = int(rating)
    return "★" * whole + ("½" if rating - whole >= 0.5 else "")


def _film(p: _Page, film: Film) -> str:
    year = f" ({esc(film.year)})" if film.year else ""
    marks = " ".join(m for m in (_stars(film.rating), "♥" if film.liked else "") if m)
    detail = " · ".join(m for m in (marks, p.date(film.watched)) if m)
    review = (f'<br><i class="review">“{esc(clip(film.review, 70))}”</i>'
              if film.review else "")
    body = (f'<span class="k px">{p.t("watched")}</span>'
            f'<span class="t">{esc(clip(film.title, 48))}{year}</span>{detail}{review}')
    inner = _thumb(film.poster, tall=True) + f'<div class="body">{body}</div>'
    return f"<li>{_row(film.url, inner)}{p.go('letterboxd')}</li>"


def _book(p: _Page, book: Book) -> str:
    detail = esc(book.author)
    bar = ""
    if book.page is not None and book.pages:
        detail += " · " + p.t("page_of", page=book.page, pages=book.pages)
        bar = f'<div class="hp"><i style="width:{round(100 * book.page / book.pages)}%"></i></div>'
    body = (f'<span class="k px">{p.t("reading")}</span>'
            f'<span class="t">{esc(clip(book.title, 48))}</span>{detail}{bar}')
    inner = _thumb(book.cover, tall=True) + f'<div class="body">{body}</div>'
    return f"<li>{_row(book.url, inner)}{p.go('goodreads')}</li>"


def _duration(minutes: int) -> str:
    return f"{minutes} min" if minutes < 60 else f"{minutes // 60}h{minutes % 60:02d}"


def _activity(p: _Page, act: Activity) -> str:
    if act.distance_km is not None:
        headline = f"{act.title} · {act.distance_km:.1f} km"
        parts = [esc(_duration(act.moving_min))]
    else:
        headline = f"{act.title} · {_duration(act.moving_min)}"
        parts = []
    if act.detail:
        parts.append(esc(act.detail))
    when = p.date(act.date)
    if when:
        parts.append(when)
    body = (f'<span class="k px">{p.t("moving")}</span>'
            f'<span class="t">{esc(headline)}</span>{" · ".join(parts)}')
    inner = (f'<div class="stv" aria-hidden="true">{esc(act.emoji)}</div>'
             f'<div class="body">{body}</div>')
    return f"<li>{_row(act.url, inner)}{p.go('strava')}</li>"


def _right_now(p: _Page, live: LiveData) -> str:
    rows = [
        render(p, value)
        for render, value in ((_song, live.song), (_film, live.film),
                              (_book, live.book), (_activity, live.activity))
        if value is not None
    ]
    if not rows:
        return ""
    return (f'<section class="box" id="right-now"><h2 class="h px"><span>▶ {p.t("right_now")}'
            f'<span class="cursor" aria-hidden="true">_</span></span></h2>'
            f'<ul class="menu">{"".join(rows)}</ul></section>')


def _member_url(m: PartyMember, repos: dict[str, Repo], site_root: Path) -> str:
    if m.url:
        return m.url
    if (site_root / "projects" / f"{m.repo}.html").exists():
        return f"projects/{m.repo}.html"
    return repos[m.repo].url


def _party(p: _Page, repos: list[Repo], site_root: Path) -> str:
    by_name = {r.name: r for r in repos}
    tiles = []
    for m in p.c.party:
        if m.repo not in by_name and not m.url:
            print(f"::warning::party repo {m.repo} not found")
            continue
        pic = (f'<img src="{esc(m.picture)}" alt="" loading="lazy">' if m.picture
               else f'<span class="emoji" aria-hidden="true">{esc(m.emoji)}</span>')
        tiles.append(
            f'<a class="mon" href="{esc(_member_url(m, by_name, site_root))}">'
            f'<div class="pic">{pic}<span class="lv">{esc(m.tag)}</span></div>'
            f'<div class="n"><b>{p.both(m.name)}</b>{p.both(m.blurb)}</div></a>'
        )
    if not tiles:
        return ""
    return (f'<section class="box" id="party"><h2 class="h px"><span>▶ {p.t("party")}</span></h2>'
            f'<div class="party">{"".join(tiles)}</div></section>')


def _repo(p: _Page, r: Repo, site_root: Path) -> str:
    case_study = site_root / "projects" / f"{r.name}.html"
    href = f"projects/{r.name}.html" if case_study.exists() else r.url
    desc = f"<span>{esc(clip(r.description, 60))}</span>" if r.description else ""
    demo = (f' <a class="try" href="{esc(r.homepage)}">{p.t("try_it")} ›</a>'
            if r.homepage else "")
    return f'<div class="repo"><a href="{esc(href)}">{esc(r.name)}{desc}</a>{demo}</div>'


def _pc_box(p: _Page, repos: list[Repo], site_root: Path) -> str:
    party = {m.repo for m in p.c.party}
    rest = [r for r in repos if r.name not in party]
    if not rest:
        return ""
    rows = [_repo(p, r, site_root) for r in rest[:PC_BOX_ROWS]]
    extra = len(rest) - PC_BOX_ROWS
    if extra > 0:
        rows.append(f'<a class="more" href="{GITHUB_REPOS}">{p.t("more", n=extra)}'
                    f' <span aria-hidden="true">›</span></a>')
    return (f'<section class="box pc" id="pc-box"><h2 class="h px"><span>▶ {p.t("pc_box")}</span>'
            f'<a href="{GITHUB_REPOS}">{p.t("all_on_github")}</a></h2>{"".join(rows)}</section>')


def _trainer(p: _Page) -> str:
    links = "".join(f'<a href="{esc(p.c.links[key])}">{label}</a>'
                    for key, label in TRAINER_LINKS if p.c.links.get(key))
    nav = f'<nav class="links">{links}</nav>' if links else ""
    return (f'<section class="box" id="trainer"><div class="trainer">'
            f'<div class="ava px" aria-hidden="true">V</div><div>'
            f'<h1 class="px name">{p.t("greeting")}</h1>'
            f'<p class="small">{p.t("intro")}</p></div></div>{nav}</section>')


def _work(p: _Page) -> str:
    companies = list(dict.fromkeys(j.company for j in p.c.jobs))
    names = f'<p class="small companies">{esc(" · ".join(companies))}</p>' if companies else ""
    linkedin = p.c.links.get("linkedin", "")
    link = (f'<div class="links"><a href="{esc(linkedin)}">LinkedIn ›</a></div>'
            if linkedin else "")
    return (f'<section class="box" id="work"><h2 class="h px"><span>▶ {p.t("work")}</span></h2>'
            f'<p class="small">{p.t("work_line")}</p>{names}{link}</section>')


def _top() -> str:
    dots = "".join(
        f'<button type="button" data-palette="{key}" aria-label="{label}" '
        f'style="background:{colour}"></button>'
        for key, label, colour in PALETTES
    )
    return (f'<header class="top"><div class="sw" role="group" aria-label="Colours">{dots}</div>'
            '<button type="button" data-lang-toggle aria-label="Switch language">EN ▸PT</button>'
            "</header>")


def _footer(p: _Page, live: LiveData) -> str:
    strava = f'{p.t("strava_credit")} · ' if live.activity is not None else ""
    return f'<footer class="foot">{strava}{p.t("footer")}<br>{p.t("made_by")}</footer>'


def _json_ld(links: dict[str, str]) -> str:
    person = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Vitor Pinheiro",
        "jobTitle": "AI Engineer",
        "url": SITE,
        "address": {"@type": "PostalAddress", "addressLocality": "Manaus",
                    "addressCountry": "BR"},
        "sameAs": [links[k] for k in ("github", "linkedin", "instagram") if links.get(k)],
    }
    return json.dumps(person, ensure_ascii=False).replace("<", "\\u003c")


def _head(p: _Page) -> str:
    en = p.c.strings["en"]
    title, description = esc(en["page_title"]), esc(en["page_description"])
    return f"""<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{SITE}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{SITE}">
<meta property="og:type" content="website">
<meta property="og:image" content="{OG_IMAGE}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS.replace("&", "&amp;")}">
<link rel="stylesheet" href="assets/site.css">
<script src="assets/site.js" defer></script>
<script type="application/ld+json">{_json_ld(p.c.links)}</script>
</head>"""


def render_home(content: Content, live: LiveData, repos: list[Repo], site_root: Path) -> str:
    p = _Page(content)
    site_root = Path(site_root)
    sections = [
        _top(),
        _trainer(p),
        _right_now(p, live),
        _party(p, repos, site_root),
        _pc_box(p, repos, site_root),
        _work(p),
        _footer(p, live),
    ]
    body = "\n".join(s for s in sections if s)
    return (f'<!doctype html>\n<html lang="en" class="pal-night">\n{_head(p)}\n'
            f'<body>\n<main class="in">\n{body}\n</main>\n</body>\n</html>\n')
