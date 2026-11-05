import html as htmllib
import re
import tomllib
from pathlib import Path

from homepage.content import Content, Job, PartyMember
from homepage.model import Activity, Book, Film, LiveData, Repo, Song
from homepage.render import clip, render_home

ROOT = Path(__file__).resolve().parents[1]
STRINGS = tomllib.loads((ROOT / "data" / "strings.toml").read_text(encoding="utf-8"))
GOODREADS = "https://www.goodreads.com/user/show/185113793-vitor-pinheiro"
LINKS = {
    "instagram": "", "github": "https://github.com/jvitorcosta",
    "linkedin": "https://www.linkedin.com/in/jvpro/", "email": "mailto:joaovpro17@gmail.com",
    "spotify": "", "letterboxd": "https://letterboxd.com/zubu/", "goodreads": GOODREADS,
    "strava": "",
}
SONG = Song("Taxi Lunar", "Geraldo Azevedo", "assets/live/c.jpg",
            "https://open.spotify.com/track/1", True)
FILM = Film("Hope", "2026", 3.5, True, "2026-11-05", "começa bem pra caramba",
            "assets/live/p.jpg", "https://letterboxd.com/zubu/film/hope/")
BOOK = Book("Can't Hurt Me", "David Goggins", "assets/live/b.jpg",
            "https://www.goodreads.com/book/1", 210, 366)
ACTIVITY = Activity("Ride", "🚴", "Night Ride", 5.0, 25, "12.1 km/h · 3 PRs", "2026-11-04", "")


def esc(s: str) -> str:
    return htmllib.escape(s, quote=True)


def member(repo, tag="WRIST", url="", picture="", emoji=""):
    return PartyMember(repo=repo, tag=tag, picture=picture, name={"en": repo, "pt": repo},
                       blurb={"en": f"{repo} en", "pt": f"{repo} pt"}, url=url, emoji=emoji)


PARTY = [member("car-cyberdeck", "DAILY", emoji="🚗"),
         member("garmin-watchfaces", picture="https://x/w.jpg")]


def repo(name, description="plain words", homepage=""):
    return Repo(name, description, f"https://github.com/jvitorcosta/{name}", homepage, "2026-11-01")


REPOS = [repo("car-cyberdeck"), repo("garmin-watchfaces"),
         repo("solvedor", "my thesis", "https://solvedor.app"), repo("ask-vitor")]


def content(**kw):
    base = dict(strings=STRINGS, links=dict(LINKS), party=list(PARTY),
                jobs=[Job("Senior AI/ML Engineer", "Qubika", "Feb 2026", "Jul 2026"),
                      Job("AI/ML Software Engineer", "Nubank", "Sep 2022", "Jul 2026")],
                activity=ACTIVITY)
    base.update(kw)
    return Content(**base)


def live(**kw):
    base = dict(song=SONG, film=FILM, book=BOOK, activity=ACTIVITY)
    base.update(kw)
    return LiveData(**base)


def render(tmp_path, c=None, lv=None, repos=None):
    return render_home(c or content(), lv or live(), REPOS if repos is None else repos, tmp_path)


def section(html, start, end=None):
    i = html.index(f'id="{start}"')
    return html[i:html.index(f'id="{end}"')] if end else html[i:]


def test_sections_in_order(tmp_path):
    html = render(tmp_path)
    idx = [html.index(f'id="{s}"') for s in ("trainer", "right-now", "party", "pc-box", "work")]
    assert idx == sorted(idx)
    assert html.startswith("<!doctype html>")
    assert '<html lang="en" class="pal-night">' in html


def test_every_text_in_both_languages(tmp_path):
    html = render(tmp_path)
    for key in ("greeting", "intro", "right_now", "listening", "watched", "reading", "moving",
                "party", "pc_box", "all_on_github", "work", "work_line", "footer"):
        for lang in ("en", "pt"):
            text = esc(STRINGS[lang][key])
            assert f'<span lang="{lang}">{text}</span>' in html, (lang, key)
    assert html.count('<span lang="en">') == html.count('<span lang="pt">')


def test_head(tmp_path):
    html = render(tmp_path)
    assert f"<title>{esc(STRINGS['en']['page_title'])}</title>" in html
    assert f'property="og:title" content="{esc(STRINGS["en"]["page_title"])}"' in html
    assert f'property="og:description" content="{esc(STRINGS["en"]["page_description"])}"' in html
    assert 'property="og:image" content="https://jvitorcosta.github.io/og-image.png"' in html
    assert '<link rel="canonical" href="https://jvitorcosta.github.io/">' in html
    assert '<link rel="stylesheet" href="assets/site.css">' in html
    assert '<script src="assets/site.js" defer></script>' in html
    assert "family=Inter" in html and "Press+Start+2P" in html
    ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html).group(1)
    assert '"addressLocality": "Manaus"' in ld and '"addressCountry": "BR"' in ld
    assert "https://github.com/jvitorcosta" in ld and "instagram" not in ld


def test_palette_and_language_buttons(tmp_path):
    html = render(tmp_path)
    for p, label in (("pocket", "Pocket"), ("night", "Night Menu"), ("nu", "Nu Purple")):
        assert f'<button type="button" data-palette="{p}" aria-label="{label}"' in html
    assert ('<button type="button" data-lang-toggle aria-label="Switch language">'
            "EN ▸PT</button>") in html


def test_profile_icons_link_to_profiles(tmp_path):
    html = render(tmp_path)
    assert 'href="https://letterboxd.com/zubu/"' in html
    assert f'href="{GOODREADS}"' in html


def test_rows_link_to_items(tmp_path):
    html = render(tmp_path)
    for url in (SONG.url, FILM.url, BOOK.url):
        assert f'<a class="row" href="{url}"' in html


def test_empty_links_are_not_rendered(tmp_path):
    html = render(tmp_path)
    assert ">Instagram<" not in html
    assert 'href=""' not in html
    assert ">GitHub<" in html


def test_missing_live_value_omits_row(tmp_path):
    html = render(tmp_path, lv=live(book=None))
    assert esc(STRINGS["en"]["reading"]) not in html
    assert esc(BOOK.title) not in html
    assert 'class="hp"' not in html
    assert "<li></li>" not in html


def test_all_rows_missing_omits_the_box(tmp_path):
    html = render(tmp_path, lv=LiveData(None, None, None, None))
    assert 'id="right-now"' not in html
    assert 'class="menu"' not in html


def test_spotify_row(tmp_path):
    html = render(tmp_path)
    row = re.search(r'<li id="spotify-row".*?</li>', html, re.S).group(0)
    assert ('data-endpoint="https://spotify-now-playing-ashen-two.vercel.app/api/'
            'now-playing.json"') in row
    for field in ("cover", "title", "artist", "label"):
        assert f'data-field="{field}"' in row
    assert f'<a class="row" href="{SONG.url}"' in row
    assert 'data-playing="true"' in row
    assert ">ON<" in row


def test_spotify_row_says_last_played_when_not_playing(tmp_path):
    song = Song(SONG.title, SONG.artist, SONG.cover, SONG.url, False)
    html = render(tmp_path, lv=live(song=song))
    label = re.search(r'data-field="label">(.*?)</span></span>', html, re.S).group(0)
    assert esc(STRINGS["en"]["last_played"]) in label
    assert esc(STRINGS["pt"]["last_played"]) in label
    assert esc(STRINGS["en"]["listening"]) not in label
    assert 'data-playing="false"' in html


def test_progress_bar_width(tmp_path):
    html = render(tmp_path)
    assert "width:57%" in html


def test_progress_bar_needs_both_numbers(tmp_path):
    book = Book(BOOK.title, BOOK.author, BOOK.cover, BOOK.url, None, 366)
    assert 'class="hp"' not in render(tmp_path, lv=live(book=book))


def test_escapes_and_clips(tmp_path):
    title = 'Tom & Jerry <3 "Live"' + "x" * 80
    film = Film(title, "2026", None, False, "2026-11-05", "r" * 100, "p.jpg", "https://x/f")
    html = render(tmp_path, lv=live(film=film))
    assert "Tom &amp; Jerry &lt;3 &quot;Live&quot;" in html
    assert "<3" not in html
    clipped = clip(title, 48)
    assert len(clipped) == 48 and clipped.endswith("…")
    assert esc(clipped) in html
    assert "r" * 69 + "…" in html and "r" * 70 not in html


def test_clip_leaves_short_text():
    assert clip("short", 10) == "short"
    assert clip("", 10) == ""


def test_pc_box_excludes_party_and_shows_more(tmp_path):
    repos = [repo("car-cyberdeck"), repo("garmin-watchfaces")] + [repo(f"r{i}") for i in range(12)]
    box = section(render(tmp_path, repos=repos), "pc-box", "work")
    assert box.count('class="repo"') == 8
    assert ">r7<" in box and ">r8<" not in box
    assert "car-cyberdeck" not in box
    assert "+ 4 more" in box
    assert 'href="https://github.com/jvitorcosta?tab=repositories"' in box


def test_pc_box_without_extra_repos_has_no_more_row(tmp_path):
    box = section(render(tmp_path), "pc-box", "work")
    assert 'class="more"' not in box
    assert box.count('class="repo"') == 2


def test_pc_box_links_case_study_and_live_demo(tmp_path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / "solvedor.html").write_text("x")
    box = section(render(tmp_path), "pc-box", "work")
    assert 'href="projects/solvedor.html"' in box
    assert 'href="https://solvedor.app"' in box
    assert esc(STRINGS["en"]["try_it"]) in box
    assert 'href="https://github.com/jvitorcosta/ask-vitor"' in box
    assert "+ 0" not in box


def test_party_links(tmp_path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / "car-cyberdeck.html").write_text("x")
    party = section(render(tmp_path), "party", "pc-box")
    assert '<a class="mon" href="projects/car-cyberdeck.html"' in party
    assert '<a class="mon" href="https://github.com/jvitorcosta/garmin-watchfaces"' in party
    assert "🚗" in party and 'src="https://x/w.jpg"' in party
    assert ">DAILY<" in party
    assert '<span lang="pt">car-cyberdeck pt</span>' in party


def test_missing_party_repo_is_skipped_with_warning(tmp_path, capsys):
    party = PARTY + [member("ghost"), member("explicit", url="https://example.com/e")]
    html = render(tmp_path, c=content(party=party))
    out = capsys.readouterr().out
    assert "::warning::party repo ghost not found" in out
    assert "explicit" not in out
    assert "ghost" not in html
    assert 'href="https://example.com/e"' in html


def test_repo_without_description_shows_name_only(tmp_path):
    box = section(render(tmp_path, repos=[repo("bare", "")]), "pc-box", "work")
    row = re.search(r'<div class="repo">(.*?)</div>', box, re.S).group(1)
    assert re.fullmatch(r'\s*<a href="[^"]+">bare</a>\s*', row), row


def test_repo_description_is_clipped(tmp_path):
    html = render(tmp_path, repos=[repo("long", "d" * 100)])
    assert "d" * 59 + "…" in html and "d" * 60 not in html


def test_no_map_or_coordinates(tmp_path):
    html = render(tmp_path).lower()
    for word in ("polyline", "latlng", "map_url", "summary_polyline", "start_latlng"):
        assert word not in html


def test_activity_without_url_is_not_a_link(tmp_path):
    html = render(tmp_path)
    assert '<div class="row">' in html
    assert "Night Ride · 5.0 km" in html
    assert "25 min" in html and "12.1 km/h · 3 PRs" in html


def test_activity_without_distance_shows_duration(tmp_path):
    act = Activity("WeightTraining", "🏋️", "Leg day", None, 50, "", "2026-11-03",
                   "https://www.strava.com/activities/1")
    html = render(tmp_path, lv=live(activity=act))
    assert '<a class="row" href="https://www.strava.com/activities/1"' in html
    assert "Leg day · 50 min" in html


def test_powered_by_strava_only_with_activity(tmp_path):
    assert "Powered by Strava" in render(tmp_path)
    assert "Powered by Strava" not in render(tmp_path, lv=live(activity=None))


def test_work_section(tmp_path):
    work = section(render(tmp_path), "work")
    assert "Qubika · Nubank" in work
    assert 'href="https://www.linkedin.com/in/jvpro/"' in work
