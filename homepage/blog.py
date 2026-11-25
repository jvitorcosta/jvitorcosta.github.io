"""Blog posts: small markdown files in blog/posts/ turned into pages at blog/<slug>.html.

The converter handles only what a post needs and refuses everything else with the file and line,
so a mistake shows up in the build, not on the page. Nothing in a post is ever passed through as
HTML: all text is escaped, links and images must be http(s), mailto or site-relative.
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from homepage.content import Content
from homepage.markup import ARROW, Page, esc, safe_url, versioned

POSTS_DIR = "blog/posts"
SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
LANES = ("post", "fragment")
WORDS_PER_MINUTE = 200
REQUIRED = ("title", "date", "summary")
OPTIONAL = ("updated", "lane", "tags", "cover", "cover_alt")


class BlogError(ValueError):
    """A post that cannot be built; the message starts with the file and line."""


@dataclass(frozen=True)
class Post:
    slug: str
    title: str
    date: str  # ISO, YYYY-MM-DD
    updated: str  # ISO or ""
    lane: str  # "post" or "fragment"
    tags: tuple[str, ...]
    summary: str
    cover: str  # site-relative to blog/, or ""
    cover_alt: str
    body: str  # HTML
    words: int

    @property
    def minutes(self) -> int:
        return max(1, math.ceil(self.words / WORDS_PER_MINUTE))


# ---------- the header ----------

def _front_matter(text: str, where: str) -> tuple[dict[str, str], str, int]:
    """The `key: value` header between two --- lines, the body, and the body's first line number."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise BlogError(f"{where}:1: a post starts with a --- header")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise BlogError(f"{where}:1: the --- header is never closed") from None
    fields: dict[str, str] = {}
    for n, line in enumerate(lines[1:end], start=2):
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        key = key.strip()
        if not sep or key not in REQUIRED + OPTIONAL:
            raise BlogError(f"{where}:{n}: unknown or malformed header line {line!r}")
        if key in fields:
            raise BlogError(f"{where}:{n}: {key} is set twice")
        fields[key] = value.strip()
    return fields, "\n".join(lines[end + 1:]), end + 2


def _iso(value: str, key: str, where: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError:
        raise BlogError(f"{where}: {key} must be YYYY-MM-DD, not {value!r}") from None
    return value


def _tags(value: str, where: str) -> tuple[str, ...]:
    inner = value.strip()
    if not (inner.startswith("[") and inner.endswith("]")):
        raise BlogError(f"{where}: tags look like [garmin, monkey-c]")
    tags = tuple(t.strip() for t in inner[1:-1].split(",") if t.strip())
    for tag in tags:
        if not SLUG.fullmatch(tag):
            raise BlogError(f"{where}: tag {tag!r} may only use a-z, 0-9 and -")
    return tags


# ---------- the body ----------

INLINE = re.compile(
    r"`(?P<code>[^`]+)`"
    r"|\*\*(?P<bold>[^*]+)\*\*"
    r"|\*(?P<em>[^*\s][^*]*)\*"
    r"|\[(?P<text>[^\]]+)\]\((?P<url>[^)\s]+)\)"
)
IMAGE = re.compile(r'!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)(?: "(?P<caption>[^"]*)")?\)')
HEADING = re.compile(r"(#{1,6}) +(.*\S)")
BULLET = re.compile(r"- +(.*)")
NUMBER = re.compile(r"\d+\. +(.*)")
LANGUAGE = re.compile(r"[a-z0-9+#-]*")


def _inline(text: str, where: str) -> str:
    """Escaped text with `code`, **bold**, *italic* and [links](url); anything else stays plain."""
    out, pos = [], 0
    for m in INLINE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        if m.group("code") is not None:
            out.append(f"<code>{esc(m.group('code'))}</code>")
        elif m.group("bold") is not None:
            out.append(f"<strong>{esc(m.group('bold'))}</strong>")
        elif m.group("em") is not None:
            out.append(f"<em>{esc(m.group('em'))}</em>")
        else:
            url = safe_url(m.group("url"))
            if not url:
                raise BlogError(f"{where}: link {m.group('url')!r} must be http(s), mailto or relative")
            out.append(f'<a href="{esc(url)}">{esc(m.group("text"))}</a>')
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def _image(m: re.Match, where: str) -> str:
    src, alt = m.group("src"), m.group("alt").strip()
    if not safe_url(src) or src.startswith(("/", "\\")) or ".." in src.split("/"):
        raise BlogError(f"{where}: image {src!r} must be a relative path inside blog/")
    if not alt:
        raise BlogError(f"{where}: an image needs alt text")
    caption = m.group("caption")
    cap = f"<figcaption>{_inline(caption, where)}</figcaption>" if caption else ""
    return f'<figure><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy">{cap}</figure>'


def _slug_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def _blocks(body: str, first_line: int, where: str) -> list[tuple[int, list[str]]]:
    """Blocks of consecutive non-blank lines, each with its first line number. A fenced code block
    is one block even when it holds blank lines."""
    blocks: list[tuple[int, list[str]]] = []
    current: list[str] = []
    start, fence = first_line, False
    for n, line in enumerate(body.split("\n"), start=first_line):
        if line.startswith("```"):
            if not fence and current:
                blocks.append((start, current))
                current = []
            if not current:
                start = n
            current.append(line)
            fence = not fence
            if not fence:
                blocks.append((start, current))
                current = []
            continue
        if fence:
            current.append(line)
        elif line.strip():
            if not current:
                start = n
            current.append(line)
        elif current:
            blocks.append((start, current))
            current = []
    if fence:
        raise BlogError(f"{where}:{start}: a code block is never closed")
    if current:
        blocks.append((start, current))
    return blocks


def _block(lines: list[str], n: int, where: str, ids: set[str]) -> str:
    here = f"{where}:{n}"
    first = lines[0]
    if first.startswith("```"):
        language = first[3:].strip()
        if not LANGUAGE.fullmatch(language):
            raise BlogError(f"{here}: unsupported code language {language!r}")
        code = esc("\n".join(lines[1:-1]))
        cls = f' class="language-{language}"' if language else ""
        return f"<pre><code{cls}>{code}</code></pre>"
    if first.startswith("<"):
        raise BlogError(f"{here}: raw HTML is not allowed in a post")
    heading = HEADING.fullmatch(first)
    if heading:
        level, text = len(heading.group(1)), heading.group(2)
        if level not in (2, 3) or len(lines) > 1:
            raise BlogError(f"{here}: use ## or ### on a line of its own (the title is the page's h1)")
        ident = base = _slug_id(text)
        k = 2
        while ident in ids:
            ident, k = f"{base}-{k}", k + 1
        ids.add(ident)
        return f'<h{level} id="{ident}">{_inline(text, here)}</h{level}>'
    if BULLET.fullmatch(first) or NUMBER.fullmatch(first):
        ordered = bool(NUMBER.fullmatch(first))
        items = []
        for i, line in enumerate(lines):
            m = (NUMBER if ordered else BULLET).fullmatch(line)
            if not m:
                raise BlogError(f"{where}:{n + i}: lists are flat, one item per line, all bullets or all numbers")
            items.append(f"<li>{_inline(m.group(1), here)}</li>")
        tag = "ol" if ordered else "ul"
        return f"<{tag}>{''.join(items)}</{tag}>"
    if first.startswith(">"):
        text = " ".join(line[1:].strip() for line in lines)
        return f"<blockquote><p>{_inline(text, here)}</p></blockquote>"
    if first.startswith(("|", "* ", "+ ", "---", "===")):
        raise BlogError(f"{here}: tables, * or + lists and rules are not supported")
    image = IMAGE.fullmatch(first.strip())
    if image and len(lines) == 1:
        return _image(image, here)
    return f"<p>{_inline(' '.join(line.strip() for line in lines), here)}</p>"


def _words(body: str) -> int:
    text = re.sub(r"```.*?```", " ", body, flags=re.S)
    return len(re.findall(r"[\w'-]+", text))


def parse_post(text: str, slug: str, where: str = "") -> Post:
    """One post from its file text; raises BlogError with the file and line when it is not valid."""
    where = where or f"{POSTS_DIR}/{slug}.md"
    if not SLUG.fullmatch(slug):
        raise BlogError(f"{where}: the file name may only use a-z, 0-9 and -")
    fields, body, first_line = _front_matter(text, where)
    for key in REQUIRED:
        if not fields.get(key):
            raise BlogError(f"{where}: the header needs {key}")
    published = _iso(fields["date"], "date", where)
    updated = _iso(fields["updated"], "updated", where) if fields.get("updated") else ""
    lane = fields.get("lane", "post")
    if lane not in LANES:
        raise BlogError(f"{where}: lane is post or fragment, not {lane!r}")
    cover, cover_alt = fields.get("cover", ""), fields.get("cover_alt", "")
    if cover:
        if not cover_alt:
            raise BlogError(f"{where}: a cover needs cover_alt")
        if not safe_url(cover) or cover.startswith(("/", "\\")) or ".." in cover.split("/"):
            raise BlogError(f"{where}: cover must be a relative path inside blog/")
    ids: set[str] = set()
    html = "\n".join(_block(lines, n, where, ids) for n, lines in _blocks(body, first_line, where))
    if not html:
        raise BlogError(f"{where}: the post has no text")
    return Post(slug, fields["title"], published, updated, lane,
                _tags(fields["tags"], where) if "tags" in fields else (),
                fields["summary"], cover, cover_alt, html, _words(body))


def load_posts(root: Path) -> list[Post]:
    """Every post under blog/posts/, newest first. A post that fails to build is reported and left out,
    like a source that fails: one bad file must not stop the whole site."""
    posts = []
    folder = Path(root) / POSTS_DIR
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        try:
            posts.append(parse_post(path.read_text(encoding="utf-8"), path.stem, f"{POSTS_DIR}/{path.name}"))
        except BlogError as exc:
            print(f"::warning::{exc}", file=sys.stderr)
    return sorted(posts, key=lambda post: (post.date, post.slug), reverse=True)


# ---------- the page ----------

def _long_date(p: Page, iso: str) -> str:
    """"Nov 26, 2026" / "26 nov 2026" for an ISO date, in both languages."""
    d = date.fromisoformat(iso)
    text = {}
    for lang, s in p.c.strings.items():
        day = s["date"].format(month=s["months"].split()[d.month - 1], day=d.day)
        text[lang] = f"{day}, {d.year}" if lang == "en" else f"{day} {d.year}"
    return p.both(text)


def render_post(content: Content, post: Post, site: str, top: str, footer: str, theme_color: str,
                early_script: str) -> str:
    """The standalone page for one post. `top`, `footer`, `theme_color` and `early_script` come from
    render.py so the blog shares the chrome of the rest of the site; pages sit in blog/, so every
    asset path starts with ../"""
    p = Page(content)
    url = f"{site}blog/{post.slug}.html"
    title = f"{esc(post.title)} | Vitor Pinheiro"
    summary = esc(post.summary)
    image = f"{site}blog/{post.cover}" if post.cover else f"{site}{versioned('og-image.png')}"
    published = f'<time datetime="{post.date}">{_long_date(p, post.date)}</time>'
    updated = (f' · <time datetime="{post.updated}">{p.t("blog_updated")} {_long_date(p, post.updated)}</time>'
               if post.updated and post.updated != post.date else "")
    tags = "".join(f'<li>{esc(t)}</li>' for t in post.tags)
    tag_list = f'<ul class="tags" aria-label="Tags">{tags}</ul>' if tags else ""
    cover = (f'<figure class="cover"><img src="{esc(post.cover)}" alt="{esc(post.cover_alt)}"></figure>'
             if post.cover else "")
    meta = (f'<p class="meta">{published}{updated} · {p.t("blog_min", n=post.minutes)}</p>')
    modified = f'\n<meta property="article:modified_time" content="{post.updated}">' if post.updated else ""
    return f"""<!doctype html>
<html lang="en" class="pal-nu">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="{theme_color}">
<title>{title}</title>
<meta name="description" content="{summary}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{esc(post.title)}">
<meta property="og:description" content="{summary}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="article">
<meta property="og:image" content="{image}">
<meta property="article:published_time" content="{post.date}">{modified}
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="../favicon.ico" sizes="32x32">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="../apple-touch-icon.png">
<script>{early_script}</script>
<link rel="stylesheet" href="../{versioned("assets/site.css")}">
<script src="../{versioned("assets/site.js")}" defer></script>
</head>
<body>
<a class="skip" href="#post">{p.t("skip")}</a>
<main class="in">
{top}
<article class="box post" id="post">
<p class="crumb"><a href="../">{ARROW}{p.t("back_home")}</a></p>
<h1 class="post-title">{esc(post.title)}</h1>
{meta}
{tag_list}
{cover}
<div class="prose" lang="en-US">
{post.body}
</div>
</article>
</main>
{footer}
</body>
</html>
"""
