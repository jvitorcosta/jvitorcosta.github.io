"""Renders index.html from the hand-written content, the live data and the repo list.

Every user-facing text is written in both languages as
<span lang="en">…</span><span lang="pt">…</span>; assets/site.css hides the other one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from homepage.content import Content, PartyMember
from homepage.markup import ARROW, Page, clip, esc, safe_url, versioned, warn
from homepage.model import LiveData, Repo
from homepage.right_now import right_now

__all__ = ["clip", "render_home", "safe_url"]

SITE = "https://jvitorcosta.github.io/"
GITHUB_REPOS = "https://github.com/jvitorcosta?tab=repositories"
PC_BOX_ROWS = 5  # with 5 the right column ends about level with the left on a laptop
COURSEWORK = {"uni", "course"}
# key, English name, Portuguese name, swatch colour
PALETTES = (("night", "Red Lantern", "Lanterna Vermelha", "#d4a72c"),
            ("nu", "Nu Purple", "Roxo Nu", "#820ad1"))
CASE_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
RESUME_CASE = "resume-as-code"
# Applies a remembered palette and language before the page paints, so neither flashes; site.js
# does the rest (buttons) once it loads.
EARLY_PALETTE = ('try{var p=localStorage.getItem("palette");'
                 f'if(/^({"|".join(k for k, *_ in PALETTES)})$/.test(p)){{'
                 'var h=document.documentElement;h.className="pal-"+p;'
                 'h.setAttribute("data-pal",p)}}catch(e){}'
                 # Same rule as site.js initialLang: stored choice, else the browser language.
                 'var h=document.documentElement,l=(navigator.language||"").toLowerCase().indexOf("pt")?"en":"pt";'
                 'try{var s=localStorage.getItem("lang");if(s=="en"||s=="pt")l=s}catch(e){}h.lang=l;')
TRAINER_LINKS = (("instagram", "Instagram"), ("github", "GitHub"),
                 ("linkedin", "LinkedIn"), ("email", "Email"))


def _member_url(m: PartyMember, repos: dict[str, Repo], site_root: Path) -> str:
    if m.url:
        return safe_url(m.url)
    if (site_root / "projects" / f"{m.repo}.html").exists():
        return f"projects/{m.repo}.html"
    return safe_url(repos[m.repo].url)


def _party(p: Page, repos: list[Repo], site_root: Path) -> str:
    by_name = {r.name: r for r in repos}
    tiles = []
    for m in p.c.party:
        if m.repo not in by_name and not m.url:
            warn(f"party repo {m.repo} not found")
            continue
        picture = safe_url(m.picture)
        pic = (f'<img src="{esc(picture)}" alt="" loading="lazy">' if picture
               else f'<span class="emoji" aria-hidden="true">{esc(m.emoji)}</span>')
        inner = (f'<div class="pic">{pic}<span class="lv">{esc(m.tag)}</span></div>'
                 f'<div class="n"><b>{p.both(m.name)}</b>{p.both(m.blurb)}</div>')
        url = _member_url(m, by_name, site_root)
        tiles.append(f'<a class="mon" href="{esc(url)}">{inner}</a>' if url
                     else f'<div class="mon">{inner}</div>')
    if not tiles:
        return ""
    return (f'<section class="box" id="party"><h2 class="h px"><span>{ARROW}{p.t("party")}{p.zh("party")}</span></h2>'
            f'<div class="party">{"".join(tiles)}</div></section>')


def _case_page(slug: str, site_root: Path) -> str:
    """projects/<slug>.html when that page is in the site, else ""."""
    if CASE_SLUG.fullmatch(slug) and (site_root / "projects" / f"{slug}.html").exists():
        return f"projects/{slug}.html"
    return ""


def _repo(p: Page, r: Repo, site_root: Path) -> str:
    text = p.c.pc_box.get(r.name, {})
    case = _case_page(text.get("case", ""), site_root) or _case_page(r.name, site_root)
    github = safe_url(r.url)
    href = case or github
    if text.get("en") and text.get("pt"):
        desc = f"<span>{p.both({lang: clip(text[lang], 60) for lang in ('en', 'pt')})}</span>"
    elif r.description:
        desc = f"<span>{esc(clip(r.description, 60))}</span>"
    else:
        desc = ""
    demo_url = safe_url(r.homepage)
    demo = (f' <a class="try" href="{esc(demo_url)}">{p.t("try_it")} ›</a>'
            if demo_url else "")
    if case and github:  # the name opens the story; the code stays one tap away
        demo += f' <a class="try" href="{esc(github)}">GitHub ›</a>'

    if text.get("title_en") and text.get("title_pt"):
        title = p.both({lang: text[f"title_{lang}"] for lang in ("en", "pt")})
    else:
        title = esc(r.name)
    tag_key = f'tag_{text.get("tag", "")}'
    if tag_key in p.c.strings["en"]:
        title += f' <span class="tag">{p.t(tag_key)}</span>'
    name = (f'<a href="{esc(href)}"><b>{title}</b>{desc}</a>' if href
            else f'<span class="name"><b>{title}</b>{desc}</span>')
    return f'<div class="repo">{name}{demo}</div>'


def _pc_box(p: Page, repos: list[Repo], site_root: Path) -> str:
    party = {m.repo for m in p.c.party}
    rest = [r for r in repos if r.name not in party]
    # Pinned rows lead, in the order data/pc_box.toml lists them; then the rest newest first,
    # with coursework last so it never pushes my own projects under "+ n more".
    pinned = [name for name, text in p.c.pc_box.items() if text.get("pin")]

    def order(r: Repo) -> tuple[int, bool]:
        if r.name in pinned:
            return pinned.index(r.name), False
        return len(pinned), p.c.pc_box.get(r.name, {}).get("tag") in COURSEWORK

    rest.sort(key=order)
    if not rest:
        return ""
    rows = [_repo(p, r, site_root) for r in rest[:PC_BOX_ROWS]]
    extra = len(rest) - PC_BOX_ROWS
    if extra > 0:
        rows.append(f'<a class="more" href="{GITHUB_REPOS}">{p.t("more", n=extra)}'
                    f' <span aria-hidden="true">›</span></a>')
    return (f'<section class="box pc" id="pc-box"><h2 class="h px"><span>{ARROW}{p.t("pc_box")}{p.zh("pc_box")}</span>'
            f'<a href="{GITHUB_REPOS}">{p.t("all_on_github")}</a></h2>{"".join(rows)}</section>')


def _trainer(p: Page) -> str:
    links = "".join(f'<a href="{esc(safe_url(p.c.links[key]))}">{label}</a>'
                    for key, label in TRAINER_LINKS if safe_url(p.c.links.get(key, "")))
    nav = f'<nav class="links">{links}</nav>' if links else ""
    status = (f'<p class="status"><i aria-hidden="true"></i>{p.t("status")}</p>'
              if p.c.strings["en"].get("status") else "")
    return (f'<section class="box" id="trainer"><div class="trainer">'
            '<img class="ava" src="assets/avatar.png" alt="" width="72" height="72"><div>'
            f'<h1 class="px name">{p.t("greeting")} '
            f'<span class="zh" lang="zh-Hans">{esc(p.c.strings["en"]["chinese_name"])}</span></h1>'
            f'<p class="small">{p.t("intro")}</p>'
            f'<p class="motto" lang="es">“{esc(p.c.strings["en"]["motto"])}”</p>{status}</div></div>{nav}</section>')


def _month(p: Page, text: str) -> dict[str, str]:
    """"Feb 2026" in both languages ("fev 2026"); anything else stays as written."""
    en = p.c.strings["en"]["months"].split()
    month, _, year = text.partition(" ")
    if month not in en:
        return {lang: text for lang in p.c.strings}
    return {lang: f'{s["months"].split()[en.index(month)]} {year}' for lang, s in p.c.strings.items()}


def _work(p: Page, site_root: Path) -> str:
    roles = []
    for j in p.c.jobs:
        start, end = _month(p, j.start), _month(p, j.end)
        dates = p.both({lang: f"{start[lang]} – {end[lang]}" for lang in ("en", "pt")})
        roles.append(f"<li><b>{esc(j.title)}</b>{esc(j.company)} · {dates}</li>")
    jobs = f'<ol class="jobs">{"".join(roles)}</ol>' if roles else ""
    # The resume PDF sits with the jobs it describes, as the one filled button.
    pdf = safe_url(p.c.links.get("resume", ""))
    linkedin = safe_url(p.c.links.get("linkedin", ""))
    buttons = ((f'<a class="primary" href="{esc(pdf)}">{p.t("resume")}</a>' if pdf else "")
               + (f'<a href="{esc(linkedin)}">LinkedIn ›</a>' if linkedin else ""))
    link = f'<div class="links">{buttons}</div>' if buttons else ""
    resume = _case_page(RESUME_CASE, site_root)
    if resume:
        link += f'<p class="small aside"><a href="{resume}">{p.t("resume_case")} ›</a></p>'
    return (f'<section class="box" id="work"><h2 class="h px"><span>{ARROW}{p.t("work")}{p.zh("work")}</span></h2>'
            f'<p class="small">{p.t("work_line")}</p>{jobs}{link}</section>')


def _aria(en: str, pt: str) -> str:
    return f'aria-label="{en}" data-aria-en="{en}" data-aria-pt="{pt}"'


def _title(en: str, pt: str) -> str:
    """A hover name; site.js swaps it to data-title-<lang> when the language changes."""
    return f'title="{en}" data-title-en="{en}" data-title-pt="{pt}"'


def _top() -> str:
    dots = "".join(
        f'<button type="button" data-palette="{key}" {_aria(en, pt)} {_title(en, pt)} '
        f'style="background:{colour}"></button>'
        for key, en, pt, colour in PALETTES
    )
    # site.js swaps aria-label to data-aria-<lang> when the language changes.
    return (f'<header class="top"><div class="sw" role="group" {_aria("Colours", "Cores")}>'
            f'{dots}</div>'
            '<button type="button" data-lang-toggle aria-label="EN > PT, switch language">EN > PT</button>'
            "</header>")


def _footer(p: Page, live: LiveData) -> str:
    return (f'<footer class="foot">{p.t("footer")}<br>{p.t("made_by")}<br>'
            # "#top" scrolls to the top of the page by the HTML spec; no element needs that id.
            f'<a href="#top">{p.t("back_to_top")}</a></footer>')


def _json_ld(links: dict[str, str]) -> str:
    person = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Vitor Pinheiro",
        "jobTitle": "AI Engineer",
        "url": SITE,
        "address": {"@type": "PostalAddress", "addressLocality": "Manaus",
                    "addressCountry": "BR"},
        "sameAs": [safe_url(links[k]) for k in ("github", "linkedin", "instagram")
                   if safe_url(links.get(k, ""))],
    }
    return json.dumps(person, ensure_ascii=False).replace("<", "\\u003c")


def _head(p: Page) -> str:
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
<meta property="og:image" content="{SITE}{versioned("og-image.png")}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<script>{EARLY_PALETTE}</script>
<link rel="stylesheet" href="{versioned("assets/site.css")}">
<script src="{versioned("assets/site.js")}" defer></script>
<script type="application/ld+json">{_json_ld(p.c.links)}</script>
</head>"""


def render_404(content: Content) -> str:
    """GitHub Pages serves 404.html for any missing path, so every URL in it is root-relative."""
    p = Page(content)
    return f"""<!doctype html>
<html lang="en" class="pal-nu">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{esc(content.strings["en"]["not_found_title"])}</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<script>{EARLY_PALETTE}</script>
<link rel="stylesheet" href="/{versioned("assets/site.css")}">
<script src="/{versioned("assets/site.js")}" defer></script>
</head>
<body>
<main class="in">
{_top()}
<section class="box" id="not-found"><h1 class="h px"><span>{ARROW}404</span></h1>
<p class="small">{p.t("not_found")}</p>
<div class="links"><a href="/">{p.t("back_home")}</a></div></section>
</main>
</body>
</html>
"""


def render_home(content: Content, live: LiveData, repos: list[Repo], site_root: Path) -> str:
    p = Page(content)
    site_root = Path(site_root)
    # Two columns on a wide screen (assets/site.css), one on a phone. The code order is the phone
    # order, which screen readers and the keyboard follow too: who I am and my projects, then
    # the rest.
    # Wide screens: who I am, what I build and where I work on the left. Phones show Work last (CSS).
    side = [_trainer(p), _party(p, repos, site_root), _work(p, site_root)]
    rest = [right_now(p, live), _pc_box(p, repos, site_root)]
    body = (f'{_top()}\n<div class="cols">\n'
            f'<div class="col side">\n{chr(10).join(s for s in side if s)}\n</div><!-- /side -->\n'
            f'<div class="col">\n{chr(10).join(s for s in rest if s)}\n</div>\n</div>')
    # The footer sits outside <main> so it is the page's contentinfo landmark.
    return (f'<!doctype html>\n<html lang="en" class="pal-nu">\n{_head(p)}\n'
            f'<body>\n<main class="in">\n{body}\n</main>\n{_footer(p, live)}\n'
            f'</body>\n</html>\n')
