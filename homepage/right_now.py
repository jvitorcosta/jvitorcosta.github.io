"""The four live rows of the Right now box: Spotify, Letterboxd, Goodreads, Strava."""

from __future__ import annotations

from dataclasses import replace

from homepage.markup import ARROW, Page, clip, esc, safe_url
from homepage.model import Activity, Book, Film, LiveData, Song

SPOTIFY_ENDPOINT = "https://spotify-now-playing-ashen-two.vercel.app/api/now-playing.json"


def _row(url: str, inner: str) -> str:
    url = safe_url(url)
    if url:
        return f'<a class="row" href="{esc(url)}">{inner}</a>'
    return f'<div class="row">{inner}</div>'


def _thumb(src: str, tall: bool = False, field: str = "") -> str:
    attrs = f' data-field="{field}"' if field else ""
    src = safe_url(src)
    if not src and not field:
        return ""
    src_attr = f' src="{esc(src)}"' if src else ""
    cls = "th tall" if tall else "th"
    h = 66 if tall else 46
    return f'<img class="{cls}"{attrs}{src_attr} alt="" width="46" height="{h}" loading="lazy">'


def _song(p: Page, song: Song | None) -> str:
    """Spotify row. Without a saved song it is a hidden, empty shell that site.js fills.

    The saved song is hours old by the time anyone reads the page, so it always renders as
    "last played"; only site.js's live fetch may switch the row to playing (ON, bars).
    """
    shell = song is None
    song = Song("", "", "", "", False) if shell else replace(song, playing=False)
    label_key = "listening" if song.playing else "last_played"
    s = p.c.strings
    labels = " ".join(
        f'data-{key.replace("_", "-")}-{lang}="{esc(s[lang][key])}"'
        for key in ("listening", "last_played") for lang in ("en", "pt")
    )
    hidden = "" if song.playing else " hidden"
    body = (
        f'<span class="k px" data-field="label">{"" if shell else p.t(label_key)}</span>'
        f'<span class="t"><span data-field="title">{esc(song.title)}</span>'
        f' <span class="badge" data-field="badge"{hidden}>ON</span></span>'
        f'<span data-field="artist">{esc(song.artist)}</span>'
    )
    inner = _thumb(song.cover, field="cover") + f'<div class="body">{body}</div>'
    playing = "true" if song.playing else "false"
    row = f'<a class="row">{inner}</a>' if shell else _row(song.url, inner)
    return (f'<li id="spotify-row"{" hidden" if shell else ""} data-endpoint="{SPOTIFY_ENDPOINT}" '
            f'data-playing="{playing}" {labels}>{row}{p.go("spotify")}</li>')


def _stars(rating: float | None) -> str:
    if rating is None:
        return ""
    whole = int(rating)
    return "★" * whole + ("½" if rating - whole >= 0.5 else "")


def _marks_text(rating: float | None, liked: bool) -> dict[str, str]:
    """What the star and heart glyphs say, for screen readers ("3.5 stars, liked")."""
    words = {"en": [], "pt": []}
    if rating is not None:
        n = f"{rating:g}"
        one = rating == 1
        words["en"].append(f"{n} star" + ("" if one else "s"))
        words["pt"].append(f"{n.replace('.', ',')} estrela" + ("" if one else "s"))
    if liked:
        words["en"].append("liked")
        words["pt"].append("curtiu")
    return {lang: ", ".join(w) for lang, w in words.items()}


def _film(p: Page, film: Film) -> str:
    year = f" ({esc(film.year)})" if film.year else ""
    glyphs = " ".join(m for m in (_stars(film.rating), "♥" if film.liked else "") if m)
    marks = (f'<span aria-hidden="true">{glyphs}</span>'
             f'<span class="sr">{p.both(_marks_text(film.rating, film.liked))}</span>'
             if glyphs else "")
    detail = " · ".join(m for m in (marks, p.date(film.watched)) if m)
    review = (f'<br><i class="review">“{esc(clip(film.review, 70))}”</i>'
              if film.review else "")
    body = (f'<span class="k px">{p.t("watched")}</span>'
            f'<span class="t">{esc(clip(film.title, 48))}{year}</span>{detail}{review}')
    inner = _thumb(film.poster, tall=True) + f'<div class="body">{body}</div>'
    return f"<li>{_row(film.url, inner)}{p.go('letterboxd')}</li>"


def _book(p: Page, book: Book) -> str:
    detail = esc(book.author)
    bar = ""
    if book.page is not None and book.pages:
        detail += " · " + p.t("page_of", page=book.page, pages=book.pages)
        bar = f'<div class="hp"><i style="width:{round(100 * book.page / book.pages)}%"></i></div>'
    body = (f'<span class="k px">{p.t("finished" if book.finished else "reading")}</span>'
            f'<span class="t">{esc(clip(book.title, 48))}</span>{detail}{bar}')
    inner = _thumb(book.cover, tall=True) + f'<div class="body">{body}</div>'
    return f"<li>{_row(book.url, inner)}{p.go('goodreads')}</li>"


def _duration(minutes: int) -> str:
    return f"{minutes} min" if minutes < 60 else f"{minutes // 60}h{minutes % 60:02d}"


def _activity(p: Page, act: Activity) -> str:
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
    # Strava brand rule: a link to Strava data must read "View on Strava", in every language.
    link = safe_url(act.url) or safe_url(p.c.links.get("strava", ""))
    view = (f'<a class="strava-link" href="{esc(link)}">'
            f'{p.both({"en": "View on Strava", "pt": "View on Strava"})}</a>' if link else "")
    body = (f'<span class="k px">{p.t("moving")}</span>'
            f'<span class="t">{esc(headline)}</span>{" · ".join(parts)}{view}')
    inner = (f'<div class="stv" aria-hidden="true">{esc(act.emoji)}</div>'
             f'<div class="body">{body}</div>')
    return f'<li><div class="row">{inner}</div>{p.go("strava")}</li>'


def right_now(p: Page, live: LiveData) -> str:
    others = [
        render(p, value)
        for render, value in ((_film, live.film), (_book, live.book), (_activity, live.activity))
        if value is not None
    ]
    # Hidden while only the empty Spotify shell is in it; site.js reveals it after a fetch.
    hidden = " hidden" if live.song is None and not others else ""
    rows = [_song(p, live.song)] + others
    return (f'<section class="box" id="right-now"{hidden}>'
            f'<h2 class="h px"><span>{ARROW}{p.t("right_now")}'
            f'<span class="cursor" aria-hidden="true">_</span></span></h2>'
            f'<ul class="menu">{"".join(rows)}</ul></section>')
