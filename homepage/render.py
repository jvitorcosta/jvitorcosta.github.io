"""Renders index.html from the hand-written content, the live data and the repo list.

Every user-facing text is written in both languages as
<span lang="en">…</span><span lang="pt">…</span>; assets/site.css hides the other one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from homepage.content import Content, PartyMember, StudyTopic
from homepage.markup import ARROW, ICONS, Page, clip, esc, safe_url, versioned, warn
from homepage.model import LiveData, Repo
from homepage.right_now import right_now

__all__ = ["clip", "render_home", "safe_url"]

SITE = "https://jvitorcosta.github.io/"
GITHUB_REPOS = "https://github.com/jvitorcosta?tab=repositories"
PC_BOX_ROWS = 5  # with 5 the right column ends about level with the left on a laptop
COURSEWORK = {"uni", "course"}
# key, English name, Portuguese name, swatch colour
PALETTES = (("night", "Mandarin", "Mandarim", "#d4a72c"),
            ("nu", "Purpura", "Púrpura", "#820ad1"))
# Browser-bar colour per palette: the same as --bg in assets/site.css.
THEME_COLOR = {"night": "#8f1d1d", "nu": "#820ad1"}
# Both languages stay visible and CSS marks the current one (html[lang]); site.js keeps the label.
LANG_TOGGLE = '<span class="l-en">EN</span> / <span class="l-pt">PT</span>'
LANG_TOGGLE_LABEL = "EN / PT, switch language"
CASE_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
RESUME_CASE = "resume-as-code"
# Applies a remembered palette and language before the page paints, so neither flashes; site.js
# does the rest (buttons) once it loads.
EARLY_PALETTE = ('try{var p=localStorage.getItem("palette");'
                 f'if(/^({"|".join(k for k, *_ in PALETTES)})$/.test(p)){{'
                 'var h=document.documentElement;h.className="pal-"+p;'
                 'h.setAttribute("data-pal",p);'
                 f'var c={json.dumps(THEME_COLOR)}[p],m=document.querySelector("meta[name=theme-color]");'
                 'if(m)m.content=c}}catch(e){}'
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


LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def _ask_api(p: Page) -> str:
    """Base URL of the Ask Vitor API; "" (the feature is off) unless links.toml sets an https:// one
    (or http:// on localhost / 127.0.0.1, for local development)."""
    api = p.c.links.get("ask_api", "").strip()
    parsed = urlparse(api)
    secure = parsed.scheme == "https" and bool(parsed.hostname)
    local = parsed.scheme == "http" and parsed.hostname in LOCAL_HOSTS
    return api.rstrip("/") if secure or local else ""


def _ask_opener(p: Page, key: str, extra: str = "") -> str:
    """An ASK ME / TALK button; ask.js reveals it (hidden without JavaScript) and flips aria-expanded when the dialogue opens and closes."""
    return (f'<button type="button"{extra} data-ask-open hidden aria-controls="ask" aria-expanded="false">'
            f'{ARROW}{p.t(key)}</button>')


def _ask(p: Page) -> str:
    """The hidden dialogue box; assets/ask.js shows it and talks to the API.

    The follow-up questions are not markup: both languages go in data-followups-en/-pt
    ("|"-separated) for the script to render as chips after each answer."""
    api = _ask_api(p)
    if not api:
        return ""
    suggest = {lang: s["ask_suggest"].split("|") for lang, s in p.c.strings.items()}
    chips = "".join(f'<button type="button" data-ask-q>{p.both({lang: qs[i] for lang, qs in suggest.items()})}</button>'
                    for i in range(len(suggest["en"])))
    attrs = "".join(f' data-followups-{lang}="{esc(s["ask_followups"])}"' for lang, s in p.c.strings.items())
    placeholders = "".join(f' data-placeholder-{lang}="{esc(s["ask_placeholder"])}"'
                           for lang, s in p.c.strings.items())
    # Fixed replies; the script picks one by the API's `kind` or status, never by matching text.
    resume = safe_url(p.c.links.get("resume", ""))
    email = safe_url(p.c.links.get("email", ""))
    # site.js swaps aria-label to data-aria-<lang> when the language changes.
    close, send = (_aria(*(esc(p.c.strings[lang][key]) for lang in ("en", "pt"))) for key in ("ask_close", "ask_send"))
    msgs = (f'<p data-ask-msg="fallback">{p.t("ask_fallback_hint")}'
            + (f' <a href="{esc(email)}">{p.t("ask_email")} ›</a>' if email else "") + "</p>"
            f'<p data-ask-msg="rate_limited">{p.t("ask_rate_limited")}</p>'
            f'<p data-ask-msg="down">{p.t("ask_down")}'
            + (f' <a href="{esc(resume)}">{p.t("resume")} ›</a>' if resume else "") + "</p>")
    return (f'<section class="box ask" id="ask" hidden data-endpoint="{esc(api)}/ask/stream"{attrs} '
            'aria-labelledby="ask-title">'
            '<div class="ask-head"><h2 class="h px" id="ask-title"><span>VITOR:</span></h2>'
            f'<button type="button" class="ask-close" data-ask-close {close}>✕</button></div>'
            f'<div class="ask-answer" aria-live="polite"><p>{p.t("ask_greeting")}</p></div>'
            '<div class="ask-sources"></div>'
            f'<div class="ask-chips">{chips}</div>'
            f'<form class="ask-form"><input type="text" name="q" maxlength="500" autocomplete="off"{placeholders} '
            f'{_aria("Your question", "Sua pergunta")}>'
            f'<button type="submit" {send}>A</button>'
            f'<button type="button" data-ask-stop hidden>{p.t("ask_stop")}</button></form>'
            f'<div class="ask-error" role="alert" hidden></div><div class="ask-msgs" hidden>{msgs}</div>'
            f'<p class="small ask-notice">{p.t("ask_notice")} '
            f'<a href="site-privacy.html">{p.t("privacy_link")} ›</a></p></section>')


def _bar(percent: int, label: str) -> str:
    return (f'<div class="bar" role="progressbar" aria-labelledby="{label}" aria-valuemin="0" '
            f'aria-valuemax="100" aria-valuenow="{percent}"><i style="width:{percent}%"></i></div>')


def _study_slug(t: StudyTopic, n: int) -> str:
    return t.id if CASE_SLUG.fullmatch(t.id) else f"t{n}"


def _glyph(percent: int) -> tuple[str, str]:
    return ("done", "✓") if percent >= 100 else ("part", "◐") if percent else ("todo", "○")


def _study_topic(p: Page, t: StudyTopic, slug: str, open_it: bool) -> str:
    label = f"study-{slug}"
    subs = []
    for sub in t.subtopics:
        items = "".join(
            f'<li class="item {_glyph(i.percent)[0]}"><span class="mark" aria-hidden="true">'
            f'{_glyph(i.percent)[1]}</span><span>{esc(i.text)}</span><span class="pct">{i.percent}%</span></li>'
            for i in sub.items)
        subs.append(f'<li><details class="sub"><summary><span class="row"><span>{esc(sub.title)}</span>'
                    f'<span class="pct">{sub.percent}%</span></span></summary><ul class="items">{items}</ul>'
                    "</details></li>")
    return (f'<li><details class="topic"{" open" if open_it else ""}><summary>'
            f'<span class="row"><b id="{label}">{p.both(t.title)}</b><span class="pct">{t.percent}%</span></span>'
            f'{_bar(t.percent, label)}</summary><ul class="subs">{"".join(subs)}</ul></details></li>')


STEP = 48  # width given to each leaf of the study map, in viewBox units
HIT = 48  # height of a leaf's tap area; with the page's usual phone width one unit is about one CSS pixel
GROUP_H = 120  # vertical room for one group: its box, its row of leaves and the NOW label
MAP_PAD = 12  # room at each side, for the trunk that leads to the lower group
MAP_BRANCH = {"study_topics": {"en": "TOPICS", "pt": "TÓPICOS"}, "study_labs": {"en": "LABS", "pt": "LABS"}}


def _tspans(text: dict[str, str]) -> str:
    """Both languages inside an SVG <text>. Never a <span>: in inline SVG the HTML parser treats
    it as foreign and drops everything after it out of the SVG."""
    return "".join(f'<tspan lang="{lang}">{esc(text[lang])}</tspan>' for lang in ("en", "pt"))


def _study_map(p: Page, topics: list[tuple[str, list[StudyTopic]]], slugs: dict[int, str], now: StudyTopic) -> str:
    """A small tree drawn as inline SVG: the path at the root, Topics and Labs stacked under it, one
    pixel square per topic that fills with its percent. Each square links to its place in the
    list below (site.js opens it). Every square sits in a 48 x 48 tap area, so on a phone it is
    about 44 px or more, which is why the groups stack instead of sitting side by side. Colours come
    from the palette's CSS variables, so both palettes work; the current topic has a ring and the
    word NOW, not colour alone."""
    width = max(240, max(len(ts) for _, ts in topics) * STEP + 2 * MAP_PAD)
    mid = width / 2
    root = esc(p.c.strings["en"]["study_path"])
    edges, nodes, labels = [], [], []
    for k, (kind_key, ts) in enumerate(topics):
        gy = 52 + k * GROUP_H  # top of this group's box
        # The first group hangs straight under the root; later ones branch off a trunk at the left edge.
        edges.append(f'<path d="M{mid:g} 28V52"/>' if k == 0 else
                     f'<path d="M{mid:g} 28V40H{MAP_PAD / 2:g}V{gy + 11}H{mid - 36:g}"/>')
        labels.append(f'<rect class="gbox" x="{mid - 36:g}" y="{gy}" width="72" height="22"/>'
                      f'<text x="{mid:g}" y="{gy + 15}">{_tspans(MAP_BRANCH[kind_key])}</text>')
        x0 = mid - len(ts) * STEP / 2
        for i, t in enumerate(ts):
            cx = x0 + STEP / 2 + i * STEP
            edges.append(f'<path d="M{mid:g} {gy + 22}V{gy + 37}H{cx:g}V{gy + 52}"/>')
            fill = 0 if not t.percent else max(2, round(t.percent / 100 * 22))
            is_now = t is now
            name_en, name_pt = esc(t.title["en"]), esc(t.title["pt"])
            nodes.append(
                f'<a class="sn{" now" if is_now else ""}" href="#study-{slugs[id(t)]}" '
                f'{_aria(f"{name_en}, {t.percent}%", f"{name_pt}, {t.percent}%")}>'
                f'<rect class="hit" x="{cx - STEP / 2:g}" y="{gy + 46}" width="{STEP}" height="{HIT}"/>'
                f'<rect class="sq" x="{cx - 11:g}" y="{gy + 53}" width="22" height="22"/>'
                f'<rect class="fl" x="{cx - 11:g}" y="{gy + 75 - fill}" width="22" height="{fill}"/>'
                + (f'<rect class="ring" x="{cx - 15:g}" y="{gy + 49}" width="30" height="30"/>'
                   f'<text x="{cx:g}" y="{gy + 104}">{_tspans({lang: s["study_now"] for lang, s in p.c.strings.items()})}</text>'
                   if is_now else "")
                + "</a>")
    # The last group needs room for the NOW label only when the current topic is in it.
    height = 52 + (len(topics) - 1) * GROUP_H + (116 if now in topics[-1][1] else 98)
    return (f'<svg class="smap" viewBox="0 0 {width:g} {height}" role="group" '
            f'{_aria("Study map: topics and labs, with progress", "Mapa de estudo: tópicos e laboratórios, com progresso")}>'
            f'<g class="edges">{"".join(edges)}</g>'
            f'<rect class="gbox" x="{mid - 86:g}" y="4" width="172" height="24"/>'
            f'<text x="{mid:g}" y="20">{root}</text>{"".join(labels)}{"".join(nodes)}</svg>')


def _study(p: Page) -> str:
    """The topic I am studying now as a card; opening it shows a small tree map and then every
    topic and lab with its subtopics and concepts as a list. The only links are the map's
    squares, which point inside the section. Nothing is computed here."""
    if not p.c.study:
        return ""
    now = next((t for t in p.c.study if t.current), p.c.study[0])
    slugs = {id(t): _study_slug(t, n) for n, t in enumerate(p.c.study)}
    card = (f'<div class="row"><b id="study-now-{slugs[id(now)]}">{p.both(now.title)}</b>'
            f'<span class="pct">{now.percent}%</span></div>{_bar(now.percent, f"study-now-{slugs[id(now)]}")}')
    groups, branches = [], []
    for kind, key in (("study", "study_topics"), ("lab", "study_labs")):
        ts = [t for t in p.c.study if t.kind == kind]
        rows = "".join(_study_topic(p, t, slugs[id(t)], t is now) for t in ts)
        if rows:
            groups.append(f'<h3 class="gh">{p.t(key)}</h3><ul class="study">{rows}</ul>')
            branches.append((key, ts))
    tree_map = _study_map(p, branches, slugs, now) if branches else ""
    when = p.date(p.c.study_updated)
    asof = f'<p class="small">{p.t("study_asof")} {when}</p>' if when else ""
    return (f'<section class="box" id="study"><h2 class="h px"><span>{ARROW}{p.t("study")}{p.zh("study")}</span></h2>'
            f'{asof}'
            f'<details class="tree"><summary><span class="now">{p.t("study_now")}</span>'
            f'<span class="path">{p.t("study_path")}</span>{card}'
            f'<span class="all">{p.t("study_all")}</span></summary>'
            f'<div class="groups">{tree_map}{"".join(groups)}</div></details></section>')


def _trainer(p: Page) -> str:
    # Each button leads with its 20x20 pixel tile (tools/pixel_icons.py); the label already names it.
    links = "".join(f'<a href="{esc(safe_url(p.c.links[key]))}">'
                    f'<img src="{versioned(f"{ICONS}/{key}.svg")}" alt="" width="20" height="20">{label}</a>'
                    for key, label in TRAINER_LINKS if safe_url(p.c.links.get(key, "")))
    if _ask_api(p):
        links = _ask_opener(p, "ask_talk") + links
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


def _group(heading: str, items: tuple[str, ...], first: bool) -> str:
    bullets = "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"
    if not heading:
        return bullets
    return (f'<details class="grp"{" open" if first else ""}><summary><span>{esc(heading)}</span>'
            f'<span class="n">{len(items)}</span></summary>{bullets}</details>')


def _work(p: Page, site_root: Path) -> str:
    roles = []
    for j in p.c.jobs:
        start, end = _month(p, j.start), _month(p, j.end)
        dates = p.both({lang: f"{start[lang]} – {end[lang]}" for lang in ("en", "pt")})
        head = f"<b>{esc(j.title)}</b>{esc(j.company)} · {dates}"
        if not j.details:
            roles.append(f"<li>{head}</li>")
            continue
        # A native disclosure: opens with Enter or Space, works without JavaScript, and any number
        # of roles can stay open. The bullets are the public resume's own English text, so they
        # carry lang="en-US" (not "en", which would hide them on the Portuguese page).
        # A group with a heading is its own small disclosure (the first one open), so a long role
        # such as four groups of bullets reads as four short rows; a group without one is a plain list.
        groups = "".join(_group(h, items, first=n == 0) for n, (h, items) in enumerate(j.details))
        # The first role opens on load, so a visitor sees proof without a click.
        opened = " open" if not any("<details" in r for r in roles) else ""
        roles.append(f'<li><details class="job"{opened}><summary>{head}</summary>'
                     f'<div class="did" lang="en-US">{groups}</div></details></li>')
    jobs = f'<ol class="jobs">{"".join(roles)}</ol>' if roles else ""
    # "Tap" on touch screens, "Click" where a mouse hovers (assets/site.css picks one).
    hint = (f'<p class="small hint"><span class="tap">{p.t("work_hint")}</span>'
            f'<span class="click">{p.t("work_hint_click")}</span></p>'
            if any(j.details for j in p.c.jobs) else "")
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
            f'<p class="small">{p.t("work_line")}</p>{hint}{jobs}{link}</section>')


def _aria(en: str, pt: str) -> str:
    return f'aria-label="{en}" data-aria-en="{en}" data-aria-pt="{pt}"'


def _title(en: str, pt: str) -> str:
    """A hover name; site.js swaps it to data-title-<lang> when the language changes."""
    return f'title="{en}" data-title-en="{en}" data-title-pt="{pt}"'


def _top(p: Page | None = None) -> str:
    """The header; with a Page whose links set ask_api it also gets the ASK ME button."""
    dots = "".join(
        f'<button type="button" data-palette="{key}" {_aria(en, pt)} {_title(en, pt)} '
        f'style="background:{colour}"></button>'
        for key, en, pt, colour in PALETTES
    )
    ask = _ask_opener(p, "ask_open", ' class="ask-open"') if p and _ask_api(p) else ""
    # site.js swaps aria-label to data-aria-<lang> when the language changes.
    # The name of the active palette sits next to the dots (CSS shows the one that matches
    # html.pal-*); it is aria-hidden because each dot already carries its name.
    names = "".join(f'<span class="pn pn-{key}"><span lang="en">{en}</span><span lang="pt">{pt}</span></span>'
                    for key, en, pt, _ in PALETTES)
    return (f'<header class="top"><div class="sw" role="group" {_aria("Colours", "Cores")}>'
            f'{dots}<span class="pname" aria-hidden="true">{names}</span></div>{ask}'
            f'<button type="button" data-lang-toggle aria-label="{LANG_TOGGLE_LABEL}">{LANG_TOGGLE}</button>'
            "</header>")


def _footer(p: Page, live: LiveData) -> str:
    return (f'<footer class="foot">{p.t("footer")}<br>{p.t("made_by")}<br>'
            # "#top" scrolls to the top of the page by the HTML spec; no element needs that id.
            f'<a href="#top">{p.t("back_to_top")}</a> · '
            f'<a href="site-privacy.html">{p.t("footer_privacy")}</a></footer>')


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
<meta name="theme-color" content="{THEME_COLOR["nu"]}">
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
<meta name="theme-color" content="{THEME_COLOR["nu"]}">
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
    side = [_trainer(p), _ask(p), _party(p, repos, site_root), _work(p, site_root)]
    rest = [right_now(p, live), _pc_box(p, repos, site_root), _study(p)]
    body = (f'{_top(p)}\n<div class="cols">\n'
            f'<div class="col side">\n{chr(10).join(s for s in side if s)}\n</div><!-- /side -->\n'
            f'<div class="col">\n{chr(10).join(s for s in rest if s)}\n</div>\n</div>')
    # The footer sits outside <main> so it is the page's contentinfo landmark.
    script = f'<script src="{versioned("assets/ask.js")}" defer></script>\n' if _ask_api(p) else ""
    return (f'<!doctype html>\n<html lang="en" class="pal-nu">\n{_head(p)}\n'
            f'<body>\n<a class="skip" href="#trainer">{p.t("skip")}</a>\n'
            f'<main class="in">\n{body}\n</main>\n{_footer(p, live)}\n{script}'
            f'</body>\n</html>\n')
