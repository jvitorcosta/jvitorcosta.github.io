import html as htmllib
import re
import tomllib
from pathlib import Path

from homepage.content import Content, Job, PartyMember
from homepage.model import Activity, Book, Film, LiveData, Repo, Song
from homepage.render import clip, render_home, safe_url

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
    for key in ("greeting", "intro", "right_now", "last_played", "watched", "reading", "moving",
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
    assert re.search(r'<link rel="stylesheet" href="assets/site\.css\?v=[0-9a-f]{8}">', html)
    assert re.search(r'<script src="assets/site\.js\?v=[0-9a-f]{8}" defer></script>', html)
    assert "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html
    ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html).group(1)
    assert '"addressLocality": "Manaus"' in ld and '"addressCountry": "BR"' in ld
    assert "https://github.com/jvitorcosta" in ld and "instagram" not in ld


def test_palette_and_language_buttons(tmp_path):
    html = render(tmp_path)
    for p, label in (("pocket", "Pocket"), ("night", "Night Menu"), ("nu", "Nu Purple")):
        assert f'<button type="button" data-palette="{p}" aria-label="{label}"' in html
    assert ('<button type="button" data-lang-toggle aria-label="EN > PT, switch language">'
            "EN > PT</button>") in html


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


def test_all_rows_missing_hides_the_box(tmp_path):
    html = render(tmp_path, lv=LiveData(None, None, None, None))
    # only the hidden Spotify shell is left, so the box stays hidden until JS fills it
    assert '<section class="box" id="right-now" hidden>' in html
    assert len(re.findall(r"<li[ >]", html)) == 1


def test_spotify_shell_when_no_song(tmp_path):
    html = render(tmp_path, lv=live(song=None))
    row = re.search(r'<li id="spotify-row"[^>]*>.*?</li>', html, re.S).group(0)
    head = row.split(">", 1)[0]
    assert " hidden" in head
    assert ('data-endpoint="https://spotify-now-playing-ashen-two.vercel.app/api/'
            'now-playing.json"') in head
    for field in ("cover", "title", "artist", "label", "badge"):
        assert f'data-field="{field}"' in row
    assert "src=" not in row.split('class="go"')[0]
    assert 'data-field="title"></span>' in row
    assert 'data-field="artist"></span>' in row
    assert '<section class="box" id="right-now">' in html


def test_spotify_row(tmp_path):
    html = render(tmp_path)
    row = re.search(r'<li id="spotify-row".*?</li>', html, re.S).group(0)
    assert ('data-endpoint="https://spotify-now-playing-ashen-two.vercel.app/api/'
            'now-playing.json"') in row
    for field in ("cover", "title", "artist", "label"):
        assert f'data-field="{field}"' in row
    assert f'<a class="row" href="{SONG.url}"' in row


def test_saved_song_never_renders_as_playing(tmp_path):
    # SONG.playing is True, but the build ran hours ago: only site.js's live fetch may say ON.
    html = render(tmp_path)
    row = re.search(r'<li id="spotify-row".*?</li>', html, re.S).group(0)
    assert 'data-playing="false"' in row and 'data-playing="true"' not in row
    assert '<span class="badge" data-field="badge" hidden>ON</span>' in row
    label = re.search(r'data-field="label">(.*?)</span></span>', row, re.S).group(0)
    assert esc(STRINGS["en"]["last_played"]) in label
    assert esc(STRINGS["en"]["listening"]) not in label


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
    captured = capsys.readouterr()
    assert "::warning::party repo ghost not found" in captured.err
    assert captured.out == ""
    assert "explicit" not in captured.err
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
    assert '<a class="row"' not in html.split('id="party"')[0].split("Leg day")[0][-300:]
    assert "Leg day · 50 min" in html
    link = re.search(r'<a class="strava-link" href="([^"]+)">(.*?)</a>', html).groups()
    assert link[0] == "https://www.strava.com/activities/1"
    assert link[1] == '<span lang="en">View on Strava</span><span lang="pt">View on Strava</span>'
    assert "Leg day" not in link[1]


def test_activity_row_is_never_a_link_and_falls_back_to_profile(tmp_path):
    act = Activity("Run", "🏃", "Morning Run", 5.0, 30, "", "2026-11-03",
                   "https://www.strava.com/activities/2")
    html = render(tmp_path, lv=live(activity=act))
    row = html[html.index("Morning Run") - 400:html.index("Morning Run")]
    assert '<div class="row">' in row and '<a class="row"' not in row
    profile = "https://www.strava.com/athletes/1"
    html = render(tmp_path, c=content(links={**LINKS, "strava": profile}))
    assert f'<a class="strava-link" href="{profile}">' in html
    assert 'class="strava-link"' not in render(tmp_path)  # no url, no profile


def test_unsafe_urls_are_not_links(tmp_path):
    bad = "javascript:alert(1)"
    song = Song("S", "A", "c.jpg", bad, True)
    film = Film("F", "2026", None, False, "2026-11-05", "", "p.jpg", " JavaScript:alert(1)")
    party = PARTY + [member("evil", url=bad)]
    repos = REPOS + [Repo("x", "d", bad, bad, "")]
    links = {**LINKS, "letterboxd": "data:text/html,hi", "github": bad}
    html = render(tmp_path, c=content(party=party, links=links),
                  lv=live(song=song, film=film), repos=repos)
    assert "javascript:" not in html.lower()
    assert "data:text" not in html
    assert 'href=""' not in html


def test_safe_url():
    assert safe_url("https://x.y/z") == "https://x.y/z"
    assert safe_url("http://x.y") == "http://x.y"
    assert safe_url("mailto:a@b.c") == "mailto:a@b.c"
    assert safe_url("projects/a.html") == "projects/a.html"
    assert safe_url("assets/live/c.jpg") == "assets/live/c.jpg"
    for bad in ("javascript:alert(1)", "java	script:x", "data:x", "vbscript:x", "//evil.com", ""):
        assert safe_url(bad) == "", bad


def test_pc_box_hand_written_text(tmp_path):
    texts = {"ask-vitor": {"en": "a chatbot that only knows my CV", "pt": "um chatbot que só conhece meu CV"}}
    box = section(render(tmp_path, c=content(pc_box=texts)), "pc-box", "work")
    assert ('<span><span lang="en">a chatbot that only knows my CV</span>'
            '<span lang="pt">um chatbot que só conhece meu CV</span></span>') in box
    assert "<span>my thesis</span>" in box  # falls back to the GitHub description


def test_no_powered_by_strava(tmp_path):
    # The activity row is typed by hand, not fetched from Strava's API, so no API credit.
    assert "Powered by" not in render(tmp_path)


def test_work_section(tmp_path):
    work = section(render(tmp_path), "work")
    assert "Qubika · Nubank" in work
    assert 'href="https://www.linkedin.com/in/jvpro/"' in work


def test_no_external_image_sources(tmp_path):
    html = render(tmp_path, content(party=[member("car-cyberdeck", emoji="🚗")]))
    srcs = re.findall(r'src="([^"]*)"', html)
    assert srcs and not [s for s in srcs if re.match(r"(https?:)?//", s)]
    for icon in ("spotify", "letterboxd", "goodreads", "strava"):
        assert re.search(rf'src="assets/icons/{icon}\.svg\?v=[0-9a-f]{{8}}"', html)


def test_language_toggle_label_contains_visible_text(tmp_path):
    html = render(tmp_path)
    assert 'data-lang-toggle aria-label="EN > PT, switch language">EN > PT</button>' in html


def test_vendored_icons_are_plain_svgs():
    for icon in ("spotify", "letterboxd", "goodreads", "strava"):
        svg = (ROOT / "assets" / "icons" / f"{icon}.svg").read_text(encoding="utf-8")
        assert svg.startswith("<svg") and "<script" not in svg and "href" not in svg


def _case_page(tmp_path, slug):
    (tmp_path / "projects").mkdir(exist_ok=True)
    (tmp_path / "projects" / f"{slug}.html").write_text("x")


def test_pc_box_case_field_links_the_case_page_and_keeps_github_and_try(tmp_path):
    _case_page(tmp_path, "solvedor")
    texts = {"or-solver": {"en": "solves school maths", "pt": "resolve contas", "case": "solvedor"}}
    repos = [repo("or-solver", "desc", "https://solvedor.app")]
    box = section(render(tmp_path, c=content(pc_box=texts), repos=repos), "pc-box", "work")
    row = re.search(r'<div class="repo">(.*?)</div>', box, re.S).group(1)
    assert row.startswith('<a href="projects/solvedor.html">or-solver<span>')
    assert 'href="https://github.com/jvitorcosta/or-solver"' in row
    assert 'href="https://solvedor.app"' in row


def test_pc_box_case_field_without_the_page_links_github(tmp_path):
    texts = {"or-solver": {"en": "a", "pt": "b", "case": "solvedor"}}
    box = section(render(tmp_path, c=content(pc_box=texts), repos=[repo("or-solver")]),
                  "pc-box", "work")
    assert "projects/solvedor.html" not in box
    assert box.count('href="https://github.com/jvitorcosta/or-solver"') == 1


def test_pc_box_case_field_must_be_a_plain_slug(tmp_path):
    _case_page(tmp_path, "solvedor")
    texts = {"or-solver": {"en": "a", "pt": "b", "case": "../solvedor"}}
    box = section(render(tmp_path, c=content(pc_box=texts), repos=[repo("or-solver")]),
                  "pc-box", "work")
    assert "projects/" not in box


def test_work_links_the_resume_case_page_when_it_exists(tmp_path):
    assert "resume-as-code" not in section(render(tmp_path), "work")
    _case_page(tmp_path, "resume-as-code")
    work = section(render(tmp_path), "work")
    assert ('<a href="projects/resume-as-code.html"><span lang="en">How my resume is built</span>'
            '<span lang="pt">Como meu currículo é feito</span> ›</a>') in work


def test_section_arrows_are_hidden_from_screen_readers(tmp_path):
    html = render(tmp_path)
    h2s = re.findall(r"<h2.*?</h2>", html, re.S)
    assert len(h2s) == 4
    for h2 in h2s:
        assert '<span aria-hidden="true">▶</span>' in h2
        assert "▶" not in h2.replace('<span aria-hidden="true">▶</span>', "")


def test_star_rating_has_a_text_alternative(tmp_path):
    row = section(render(tmp_path), "right-now", "party")
    assert '<span aria-hidden="true">★★★½ ♥</span>' in row
    assert ('<span class="sr"><span lang="en">3.5 stars, liked</span>'
            '<span lang="pt">3,5 estrelas, curtiu</span></span>') in row


def test_star_text_variants(tmp_path):
    def sr(rating, liked):
        film = Film("F", "2026", rating, liked, "2026-11-05", "", "", "https://x/f")
        m = re.search(r'<span class="sr">(<span lang="en">[^<]*</span>'
                      r'<span lang="pt">[^<]*</span>)</span>', section(
                          render(tmp_path, lv=live(film=film)), "right-now", "party")
                      .split("Letterboxd")[0].split("F</span>")[-1])
        return m.group(1) if m else ""

    assert sr(1.0, False) == '<span lang="en">1 star</span><span lang="pt">1 estrela</span>'
    assert sr(4.0, False) == '<span lang="en">4 stars</span><span lang="pt">4 estrelas</span>'
    assert sr(None, True) == '<span lang="en">liked</span><span lang="pt">curtiu</span>'
    assert sr(None, False) == ""


def test_palette_labels_follow_the_language(tmp_path):
    top = render(tmp_path).split("</header>")[0]
    assert 'role="group" aria-label="Colours" data-aria-en="Colours" data-aria-pt="Cores"' in top
    for en, pt in (("Pocket", "Pocket"), ("Night Menu", "Menu Noturno"), ("Nu Purple", "Roxo Nu")):
        assert f'aria-label="{en}" data-aria-en="{en}" data-aria-pt="{pt}"' in top


def test_footer_is_a_landmark_outside_main(tmp_path):
    html = render(tmp_path)
    assert html.index("</main>") < html.index('<footer class="foot">')
    assert html.index('<footer class="foot">') < html.index("</body>")


def test_early_palette_script_runs_before_the_stylesheet(tmp_path):
    head = render(tmp_path).split("</head>")[0]
    m = re.search(r"<script>(.*?)</script>", head, re.S)
    assert m and m.start() < head.index('<link rel="stylesheet" href="assets/site.css?v=')
    script = m.group(1)
    assert script.lstrip().startswith("try{") and "catch(e){}" in script
    assert 'localStorage.getItem("palette")' in script
    assert "pocket|night|nu" in script
    assert '"pal-"+p' in script and 'setAttribute("data-pal",p)' in script
    assert script.count("{") == script.count("}") and script.count("(") == script.count(")")


def test_early_script_also_applies_the_language(tmp_path):
    # A Portuguese visitor must not see English for a moment while site.js loads.
    script = re.search(r"<script>(.*?)</script>", render(tmp_path).split("</head>")[0], re.S).group(1)
    assert 'localStorage.getItem("lang")' in script
    assert "navigator.language" in script and "h.lang=" in script
    assert script.count("try{") == script.count("catch(e){}") == 2  # storage can throw on its own


def test_page_requests_no_third_party_fonts(tmp_path):
    html = render(tmp_path)
    assert "googleapis" not in html and "gstatic" not in html
    assert 'rel="preconnect"' not in html
    hosts = re.findall(r'(?:src|href)="(https?://[^"/]+)', html.split("</head>")[0])
    assert hosts == ["https://jvitorcosta.github.io"]  # canonical link only


def test_trainer_card_shows_the_pixel_avatar(tmp_path):
    html = render(tmp_path)
    assert '<img class="ava" src="assets/avatar.png" alt="" width="72" height="72">' in html
    assert '>V</div>' not in html


def test_trainer_card_shows_the_motto_once_in_spanish(tmp_path):
    # The motto is Spanish in both languages, so it is written once and read out as Spanish.
    html = render(tmp_path)
    assert html.count('<p class="motto" lang="es">') == 1
    assert "“Dios me prepara a fuego lento.”" in html


def test_tab_and_home_screen_icons(tmp_path):
    head = render(tmp_path).split("</head>")[0]
    assert '<link rel="icon" href="favicon.svg" type="image/svg+xml">' in head
    assert '<link rel="apple-touch-icon" href="apple-touch-icon.png">' in head


def test_asset_version_follows_the_file_content():
    # Phones kept old icons next to a new stylesheet; a content hash in the URL makes them refetch.
    import hashlib
    from homepage.markup import SITE_ROOT, versioned
    data = (SITE_ROOT / "assets" / "site.css").read_bytes()
    assert versioned("assets/site.css") == "assets/site.css?v=" + hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()[:8]


def test_trainer_card_shows_the_full_name_and_the_chinese_name(tmp_path):
    html = render(tmp_path)
    name = re.search(r'<h1 class="px name">(.*?)</h1>', html).group(1)
    assert name.count("VITOR PINHEIRO") == 2  # English and Portuguese spans
    # Written once, marked as Chinese so it is read out and drawn with a font that has the glyphs.
    assert name.count('<span class="zh" lang="zh-Hans">白玉龙</span>') == 1
