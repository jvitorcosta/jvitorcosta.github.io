# Personal Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the resume-style homepage of jvitorcosta.github.io with a phone-first, bilingual, three-palette "Game Boy menu" page that shows what Vitor listens to, watches, reads and does, the projects he picks, every other repo, and a short work line, refreshed daily.

**Architecture:** A small stdlib-only Python package (`homepage/`) in the site repo fetches Letterboxd, Goodreads, GitHub and the Spotify fork's new JSON endpoint, keeps the last good value of each in `data/state.json`, and renders a static `index.html` from hand-edited TOML content. A daily GitHub Action runs it and commits. Plain CSS/JS in `assets/` does the palette and language switches and a live Spotify refresh. The private resume repo stops writing `index.html`, exports the public job list, and restyles the case-study pages with the shared stylesheet.

**Tech Stack:** Python 3.12 stdlib (`urllib`, `xml.etree`, `html`, `tomllib`, `json`), pytest, uv; plain HTML/CSS/JS; GitHub Actions; Flask (Spotify fork only, already there).

**Spec:** `docs/superpowers/specs/2026-11-05-personal-homepage-design.md` (and the mockup `docs/superpowers/specs/2026-11-05-homepage-mockup.html`, the visual reference for every rendering task).

## Global Constraints

- Three palettes, class names `pal-pocket`, `pal-night`, `pal-nu`. Nu Purple background `#820AD1`. Starting values are the CSS variables in the mockup (`--bg --box --ink --line --shadow --soft --accent --hp --ink-on-bg`).
- First visit: Pocket if `prefers-color-scheme: light`, Night Menu if dark. Choice remembered in `localStorage` key `palette`; language in key `lang`.
- Languages `en` and `pt` (Brazil). First visit follows `navigator.language` (`pt*` → `pt`, else `en`).
- WCAG AA contrast (4.5:1 body text, 3:1 large text and UI borders) in all three palettes; tap targets ≥ 44px; works at 360px wide; pixel font (`Press Start 2P`) only for headings and labels; `prefers-reduced-motion` stops the cursor blink and music bars.
- No maps, routes, start/end points, heart rate or health data anywhere.
- No Strava API calls from the site or its workflow (Strava API Agreement, Nov 2024: data only to the athlete). Strava row comes from `data/activity.toml`, edited by Vitor.
- Nothing from `curriculum-vitae/private/` beyond name, email, links, headline, job titles and dates, case studies. Never the phone number.
- A failing source keeps its last value in `data/state.json` and prints `::warning::<source> not updated: <reason>`; the job never fails because of a source.
- Letterboxd user `zubu`; Goodreads profile `https://www.goodreads.com/user/show/185113793-vitor-pinheiro`; GitHub user `jvitorcosta`; Spotify fork `jvitorcosta/spotify-now-playing` at `https://spotify-now-playing-ashen-two.vercel.app`.
- PC box excludes repos `jvitorcosta`, `jvitorcosta.github.io`, `spotify-now-playing`, forks, archived and private repos, and anything in the party.
- Party: at most 6. Starting list: car-cyberdeck (DAILY), garmin-watchfaces (WRIST), open-radars-manaus (CITY), haylou-faces (WRIST).
- Work section: one sentence, companies, and a LinkedIn link (no resume PDF).
- Actions pinned to commit SHAs with `permissions: contents: write` only, as in `jvitorcosta/jvitorcosta/.github/workflows/update-profile.yml`.
- Commits are authored as Vitor's own work: no `Co-Authored-By: Claude` trailer.
- Publishing (pushing to `main` of the site repo, deploying the fork) needs Vitor's OK; work on branches and open PRs.

## Calls this plan makes where the spec left room

- Goodreads: the public profile shows only "currently reading", not finished books with ratings, so when nothing is being read the row keeps the last saved book (instead of "last finished with rating").
- Case-study pages get the shared stylesheet and palette dots but no language switch: their content is English only.
- Link-preview tags (`og:*`) are in English: a static page has one set; the Portuguese text is on the page itself.

## Review Focus

- **Goodreads with nothing on "currently reading", or a redesigned page** → the row keeps the last saved book and the job logs a warning; the page never shows an empty row. (Test in Task 4.)
- **Titles with quotes, `&`, `<`, emoji or 80+ characters** (film reviews in Portuguese, book subtitles) → escaped everywhere and clipped with "…" so rows never overflow at 360px. (Tests in Tasks 3 and 7.)
- **Instagram's in-app browser: `localStorage` throws or JS is off** → the page renders fully readable in English with the palette from `prefers-color-scheme`; switches just don't remember. (Test in Task 8.)
- **Spotify endpoint down, slow or blocked by CORS** → the row keeps the server-rendered last value with "Last played", no layout jump, no console error loop. (Test in Task 1 for the endpoint, Task 8 for the page.)
- **A brand-new public repo with no description, or a party repo that was renamed or made private** → PC box shows it with just its name; a missing party repo is skipped with a warning instead of breaking the build. (Tests in Tasks 5 and 7.)

---

## File Structure

**`jvitorcosta/spotify-now-playing` (fork, clone to `D:\dev\projects\spotify-now-playing`)**
- Modify `api/orchestrator.py`: new route `/api/now-playing.json`.
- Create `tests/test_now_playing_json.py`; add `pytest` dev group to `pyproject.toml`.

**`jvitorcosta/jvitorcosta.github.io` (`D:\dev\projects\jvitorcosta.github.io`)**
- `pyproject.toml`: uv project `homepage`, no runtime deps, dev group `pytest`.
- `homepage/model.py`: dataclasses shared by everything.
- `homepage/http.py`: `get(url) -> bytes` with the site's User-Agent.
- `homepage/state.py`: last-good-value store and `refresh()`.
- `homepage/sources/letterboxd.py`, `goodreads.py`, `github.py`, `spotify.py`: one fetcher each.
- `homepage/images.py`: download posters/covers into `assets/live/`.
- `homepage/content.py`: load `data/*.toml` and `data/jobs.json`.
- `homepage/render.py`: `render_home()`, all HTML.
- `homepage/build.py`: CLI, wires it all and writes `index.html`.
- `data/strings.toml`, `data/party.toml`, `data/links.toml`, `data/activity.toml`, `data/jobs.json`, `data/state.json`.
- `assets/site.css`, `assets/site.js`, `assets/live/` (cached images).
- `tests/` with `fixtures/`.
- `.github/workflows/update-home.yml`.

**`curriculum-vitae` (private, `D:\dev\projects\curriculum-vitae`)**
- Modify `cv/site.py`: drop `index.html`, export `jobs.json`, case pages use `/assets/site.css` + `/assets/site.js`.
- Modify `tests/test_site.py`.

---

### Task 1: Spotify fork JSON endpoint

**Files:**
- Modify: `api/orchestrator.py` (add the route next to `/redirect`, before the catch-all is fine since Flask prefers the more specific rule)
- Modify: `pyproject.toml` (add `[dependency-groups] dev = ["pytest>=8.0"]`)
- Test: `tests/test_now_playing_json.py`

**Interfaces:**
- Consumes: `get_active_service() -> (name, service)`; `service.get_now_playing() -> dict` with keys `is_playing, track_name, artist_name, album_art_url, track_url`.
- Produces: `GET /api/now-playing.json` → `200 application/json` body `{"playing": bool, "title": str, "artist": str, "cover": str, "url": str}`; headers `Access-Control-Allow-Origin: https://jvitorcosta.github.io`, `Cache-Control: s-maxage=10`. On any error: `503` with `{"error": "<message>"}` and the same CORS header.

- [ ] **Step 1: Clone the fork and branch**

```bash
gh repo clone jvitorcosta/spotify-now-playing D:/dev/projects/spotify-now-playing
cd D:/dev/projects/spotify-now-playing && git switch -c feat/now-playing-json
```

- [ ] **Step 2: Write the failing tests**

```python
from api import orchestrator

TRACK = {"is_playing": True, "track_name": "Taxi Lunar", "artist_name": "Geraldo Azevedo",
         "album_name": "x", "album_art_url": "https://i.scdn.co/image/abc", "track_url": "https://open.spotify.com/track/1"}

class Fake:
    def __init__(self, result=None, exc=None): self.result, self.exc = result, exc
    def get_now_playing(self):
        if self.exc: raise self.exc
        return self.result

def client(monkeypatch, service):
    monkeypatch.setattr(orchestrator, "get_active_service", lambda: ("spotify", service))
    return orchestrator.app.test_client()

def test_returns_track_as_json(monkeypatch):
    r = client(monkeypatch, Fake(TRACK)).get("/api/now-playing.json")
    assert r.status_code == 200 and r.is_json
    assert r.get_json() == {"playing": True, "title": "Taxi Lunar", "artist": "Geraldo Azevedo",
                            "cover": "https://i.scdn.co/image/abc", "url": "https://open.spotify.com/track/1"}
    assert r.headers["Access-Control-Allow-Origin"] == "https://jvitorcosta.github.io"

def test_service_error_is_503_json_with_cors(monkeypatch):
    r = client(monkeypatch, Fake(exc=RuntimeError("boom"))).get("/api/now-playing.json")
    assert r.status_code == 503 and "error" in r.get_json()
    assert r.headers["Access-Control-Allow-Origin"] == "https://jvitorcosta.github.io"

def test_svg_route_unchanged(monkeypatch):
    r = client(monkeypatch, Fake(TRACK)).get("/api/orchestrator")
    assert r.mimetype == "image/svg+xml"
```

- [ ] **Step 3: Run to verify they fail**

Run: `uv run --group dev pytest tests/test_now_playing_json.py -v`
Expected: the first two FAIL (404 / not JSON). In `test_svg_route_unchanged`, monkeypatch `orchestrator.make_svg` to return `"<svg/>"` so it never touches the network; it passes before and after.

- [ ] **Step 4: Implement `now_playing_json() -> Response` in `api/orchestrator.py`**

Use `flask.jsonify`; set the two headers on both the success and error responses.

- [ ] **Step 5: Run to verify they pass**

Run: `uv run --group dev pytest -v` → all PASS.

- [ ] **Step 6: Commit, push, open PR, and stop for Vitor's OK before merging** (merging deploys to Vercel)

```bash
git add api/orchestrator.py pyproject.toml tests/
git commit -m "feat: add /api/now-playing.json for the website"
git push -u origin feat/now-playing-json && gh pr create --fill
```

After merge, verify: `curl -s https://spotify-now-playing-ashen-two.vercel.app/api/now-playing.json` prints the JSON with `playing`.

---

### Task 2: Site repo scaffold, model and state

**Files:**
- Create: `pyproject.toml`, `homepage/__init__.py`, `homepage/model.py`, `homepage/http.py`, `homepage/state.py`, `tests/test_state.py`, `.gitignore` (add `.venv/`, `__pycache__/`, `.superpowers/`)

Work on branch `feat/homepage` from `origin/main` in the site repo (the design doc commit is on `docs/homepage-redesign`; merge or cherry-pick it first).

**Interfaces:**
- Produces (`homepage/model.py`, all `@dataclass(frozen=True)`; every field JSON-serialisable):
  - `Song(title: str, artist: str, cover: str, url: str, playing: bool)`
  - `Film(title: str, year: str, rating: float | None, liked: bool, watched: str, review: str, poster: str, url: str)` (`watched` ISO date)
  - `Book(title: str, author: str, cover: str, url: str, page: int | None, pages: int | None)`
  - `Activity(sport: str, emoji: str, title: str, distance_km: float | None, moving_min: int, detail: str, date: str, url: str)`
  - `Repo(name: str, description: str, url: str, homepage: str, pushed: str)`
  - `LiveData(song: Song | None, film: Film | None, book: Book | None, activity: Activity | None)`
  - `to_dict(obj) -> dict` / `from_dict(cls, d) -> obj` helpers.
- Produces (`homepage/http.py`): `get(url: str, headers: dict | None = None) -> bytes`, UA `"Mozilla/5.0 (homepage; +https://jvitorcosta.github.io)"`, timeout 30.
- Produces (`homepage/state.py`):
  - `load_state(path: Path) -> dict[str, dict]` (missing file → `{}`)
  - `save_state(path: Path, state: dict) -> None` (sorted keys, indent 2, UTF-8, trailing newline)
  - `refresh(name: str, fetch: Callable[[], T | list[T] | None], state: dict, cls: type[T]) -> T | list[T] | None`: on success stores `to_dict(result)` (or a list of them when `fetch` returns a list, as for repos) in `state[name]` and returns it; on exception or `None` prints `::warning::{name} not updated: {reason}` and returns the stored value decoded with `from_dict(cls, …)` (element-wise for a stored list), else `None`.

- [ ] **Step 1: Write the failing tests** in `tests/test_state.py`:
  - `test_refresh_stores_new_value` — fetch returns a `Book`; `state["book"]` equals its dict.
  - `test_refresh_keeps_last_value_on_error` — state has a book; fetch raises `ValueError("layout")`; returns the old `Book`; captured stdout contains `::warning::book not updated: layout`.
  - `test_refresh_keeps_last_value_on_none` — same with fetch returning `None`.
  - `test_refresh_without_history_returns_none`.
  - `test_refresh_list_roundtrip` — fetch returns two `Repo`s, then a failing fetch returns those two `Repo`s from state.
  - `test_state_roundtrip(tmp_path)` — save then load gives the same dict; file ends with `\n`.
- [ ] **Step 2: Run** `uv run --group dev pytest tests/test_state.py -v` → FAIL (module missing).
- [ ] **Step 3: Implement** `model.py`, `http.py`, `state.py` per the interfaces.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: homepage package scaffold, model and state store`.

---

### Task 3: Letterboxd source

**Files:**
- Create: `homepage/sources/__init__.py`, `homepage/sources/letterboxd.py`, `tests/fixtures/letterboxd.xml`, `tests/test_letterboxd.py`

**Interfaces:**
- Consumes: `Film`, `http.get`.
- Produces: `fetch_film(user: str = "zubu", get: Callable[[str], bytes] = http.get) -> Film | None` — first `<item>` with `letterboxd:filmTitle`; poster URL rewritten `-0-600-0-900-` → `-0-230-0-345-`; review is the description text without the `<img>`, `""` when it starts with `"Watched on "`; `url` is the item `<link>`.

Port the parsing from `jvitorcosta/jvitorcosta/scripts/letterboxd_card.py` (`latest_film`); don't import it.

- [ ] **Step 1: Save the fixture**: download `https://letterboxd.com/zubu/rss/` and trim to the `<channel>` header plus three items: a list item without `filmTitle` first, then a film with a review containing `&amp;` and an emoji, then a film whose description is only `Watched on …`.
- [ ] **Step 2: Write the failing tests:**
  - `test_skips_non_film_items_and_reads_the_first_film` — title, year, `rating == 3.5` style float, `liked`, `watched` ISO.
  - `test_review_text_is_unescaped_plain_text` — contains `&` and the emoji, no `<`.
  - `test_watched_on_only_means_no_review`.
  - `test_poster_uses_230_size`.
  - `test_feed_without_films_returns_none`.
- [ ] **Step 3: Run** → FAIL. **Step 4: Implement.** **Step 5: Run** → PASS.
- [ ] **Step 6: Commit** `feat: Letterboxd source`.

---

### Task 4: Goodreads source

**Files:**
- Create: `homepage/sources/goodreads.py`, `tests/fixtures/goodreads-profile.html`, `tests/fixtures/goodreads-empty.html`, `tests/test_goodreads.py`

**Interfaces:**
- Produces: `fetch_book(profile_url: str = GOODREADS_PROFILE, get = http.get) -> Book | None`.
  - Find the element with `id="currentlyReadingReviews"`; take the **first** `div.Updates` inside it.
  - Title from `a.bookTitle` text; URL from its `href` made absolute (`https://www.goodreads.com` + href); author from `a.authorName`.
  - Cover from the `div.firstcol img src`, size token `._SX98_.` → `._SX318_.`.
  - Progress from the first `(page N of M)` text after that entry (regex `\(page (\d+) of (\d+)\)`), else `page = pages = None`.
  - No `currentlyReadingReviews` block, or no `a.bookTitle` → raise `ValueError("no currently-reading book on the profile page")` (so `refresh` keeps the last book and warns).
  - Use `html.parser.HTMLParser` or regex; no third-party parser.

- [ ] **Step 1: Save fixtures**: from the live profile page keep only the `currentlyReadingReviews` block (both books) and the progress markup; strip every `<form>` (they carry tokens). For the empty fixture, the same page shell without that block.
- [ ] **Step 2: Write the failing tests:**
  - `test_reads_first_currently_reading_book` — `title == "Can't Hurt Me: Master Your Mind and Defy the Odds"`, `author == "David Goggins"`, `page == 210`, `pages == 366`, cover ends `._SX318_.jpg`, url starts `https://www.goodreads.com/book/show/41721428`.
  - `test_missing_block_raises_value_error` (empty fixture).
  - `test_title_entities_are_unescaped` — `&#39;` becomes `'`.
- [ ] **Step 3: Run** → FAIL. **Step 4: Implement.** **Step 5: Run** → PASS.
- [ ] **Step 6: Commit** `feat: Goodreads source`.

---

### Task 5: GitHub repos and Spotify last value

**Files:**
- Create: `homepage/sources/github.py`, `homepage/sources/spotify.py`, `tests/test_github.py`, `tests/test_spotify.py`

**Interfaces:**
- Produces: `fetch_repos(user: str = "jvitorcosta", token: str | None = None, get = http.get) -> list[Repo]` — `GET https://api.github.com/users/{user}/repos?type=owner&sort=pushed&per_page=100`, drops `fork`, `archived`, `private`, and names in `EXCLUDED = {"jvitorcosta", "jvitorcosta.github.io", "spotify-now-playing"}`; keeps API order (newest push first); `description` `""` when null; `homepage` `""` when null.
- Produces: `fetch_song(get = http.get) -> Song | None` — `GET {SPOTIFY_BASE}/api/now-playing.json`, maps `playing,title,artist,cover,url`; non-JSON or `"error"` key → `ValueError`.

- [ ] **Step 1: Write the failing tests** with a fake `get` returning canned JSON:
  - `test_filters_forks_archived_private_and_excluded`.
  - `test_null_description_becomes_empty_string`.
  - `test_keeps_newest_first_order`.
  - `test_sends_token_when_given` (fake `get` records headers; `Authorization: Bearer x`).
  - `test_song_maps_fields` / `test_song_error_payload_raises`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (let `http.get` accept `headers`). **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: GitHub repos and Spotify sources`.

---

### Task 6: Image cache

**Files:**
- Create: `homepage/images.py`, `tests/test_images.py`

**Interfaces:**
- Produces: `cache_image(url: str, dest: Path, get = http.get) -> str` — file name `sha1(url)[:16] + suffix` (suffix from the URL path, default `.jpg`), written once (skip download if the file exists), returns the site-relative path `assets/live/<name>`. `prune(dest: Path, keep: set[str]) -> None` deletes cached files not in `keep`.

- [ ] **Step 1: Write the failing tests:** `test_downloads_once` (fake get called once over two calls), `test_returns_site_relative_path`, `test_prune_removes_unused`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: cache posters and covers in the repo`.

---

### Task 7: Content files and the renderer

**Files:**
- Create: `data/strings.toml`, `data/party.toml`, `data/links.toml`, `data/activity.toml`, `data/jobs.json` (temporary copy until Task 10 exports it), `homepage/content.py`, `homepage/render.py`, `tests/test_content.py`, `tests/test_render.py`

**Interfaces:**
- `data/links.toml`: keys `instagram, github, linkedin, email, spotify, letterboxd, goodreads, strava` (`instagram` and `spotify` empty until Vitor sends them).
- `data/party.toml`: `[[member]]` tables with `repo, tag, picture` (optional, site-relative or https), `name_en, name_pt, blurb_en, blurb_pt`, optional `url` (defaults to `projects/<repo>.html` if that file exists, else the GitHub URL).
- `data/strings.toml`: `[en]` and `[pt]` tables with keys `greeting, intro, right_now, listening, last_played, watched, reading, moving, party, pc_box, all_on_github, more, work, work_line, footer, page_title, page_description`. English copy from the mockup; Portuguese written by the implementer and flagged for Vitor's review in the PR.
- `data/activity.toml`: one `[activity]` table matching `Activity` fields (seed with the 2026-11-04 Night Ride: Ride, 🚴, "Night Ride", 5.0 km, 25 min, "12.1 km/h · 3 PRs", 2026-11-04, Strava activity URL left to Vitor).
- Produces (`content.py`): `PartyMember(repo, tag, picture, name: dict[str, str], blurb: dict[str, str], url)`; `Job(title, company, start, end)`; `Content(strings: dict[str, dict[str, str]], links: dict[str, str], party: list[PartyMember], jobs: list[Job], activity: Activity | None)`; `load_content(root: Path) -> Content`. More than 6 party members → `ValueError("party has 7 members, max is 6")`.
- Produces (`render.py`): `render_home(content: Content, live: LiveData, repos: list[Repo], site_root: Path) -> str`.
  - Every user-facing text appears as `<span lang="en">…</span><span lang="pt">…</span>`; `<html lang="en" class="pal-night">` by default (JS adjusts). CSS hides the other language.
  - Sections in order with ids `trainer, right-now, party, pc-box, work`, matching the mockup's markup.
  - Right now rows: link to the item (`song.url`, `film.url`, `book.url`, `activity.url`), round profile icon linking to `links[<platform>]`; a row whose live value is `None` is omitted; Spotify row carries `id="spotify-row"` and `data-endpoint="https://spotify-now-playing-ashen-two.vercel.app/api/now-playing.json"` and says `last_played` unless `song.playing`.
  - Book row: progress bar width `round(100*page/pages)%` when both known.
  - Text clipping: `clip(text, n)` with `…`: film/book titles 48, review 70, repo description 60.
  - Party: members whose `repo` isn't in `repos` and has no explicit `url` are skipped with `::warning::party repo <name> not found`.
  - PC box: `repos` minus party repos, first 8 shown, then `+ {n} more` linking to `https://github.com/jvitorcosta?tab=repositories`; repos with `projects/<name>.html` under `site_root` link there, else to `url`; `homepage` (live demo) shown as "try it".
  - Links with an empty value are not rendered.
  - Head: `<title>` and `og:title`/`og:description` from `strings.en` (page_title "Vitor Pinheiro · AI engineer in Manaus who builds gadgets for his car, watch and city"), `og:image` kept, canonical `https://jvitorcosta.github.io/`, Person JSON-LD (name, url, address Manaus BR, sameAs github/linkedin/instagram when set), `<link rel="stylesheet" href="assets/site.css">`, `<script src="assets/site.js" defer>`, Google Fonts `Inter` and `Press Start 2P`.
  - Footer: "Powered by Strava" only while an activity row is shown.

- [ ] **Step 1: Write the failing tests** in `tests/test_content.py`: `test_loads_starting_party_in_order` (the four repos and tags from Global Constraints), `test_more_than_six_members_is_an_error`, `test_both_languages_have_the_same_keys`.
- [ ] **Step 2: Write the failing tests** in `tests/test_render.py` using a `Content` and `LiveData` built in the test:
  - `test_sections_in_order` — index of `id="trainer"` < `right-now` < `party` < `pc-box` < `work`.
  - `test_every_text_in_both_languages` — for each strings key used, both `lang="en"` and `lang="pt"` spans present.
  - `test_profile_icons_link_to_profiles` — `https://letterboxd.com/zubu/` and the Goodreads profile URL appear as hrefs.
  - `test_empty_links_are_not_rendered` — `instagram = ""` → no `Instagram` link.
  - `test_missing_live_value_omits_row` — `book=None` → no "Reading" row, no empty box.
  - `test_spotify_row_says_last_played_when_not_playing`.
  - `test_progress_bar_width` — 210/366 → `width:57%`.
  - `test_escapes_and_clips` — film title `Tom & Jerry <3 "Live"` plus 80 chars renders escaped (`&amp;`, `&lt;`, `&quot;`) and ends with `…`.
  - `test_pc_box_excludes_party_and_shows_more` — 12 non-party repos → 8 rows and `+ 4 more`.
  - `test_missing_party_repo_is_skipped_with_warning` (capsys).
  - `test_repo_without_description_shows_name_only`.
  - `test_no_map_or_coordinates` — output contains none of `polyline`, `latlng`, `map`.
  - `test_powered_by_strava_only_with_activity`.
- [ ] **Step 3: Run** `uv run --group dev pytest -v` → FAIL.
- [ ] **Step 4: Write the data files**, then **implement** `content.py` and `render.py`.
- [ ] **Step 5: Run** → PASS.
- [ ] **Step 6: Commit** `feat: homepage content files and renderer`.

---

### Task 8: Stylesheet and switches

**Files:**
- Create: `assets/site.css`, `assets/site.js`, `tests/test_assets.py`

**Interfaces:**
- `site.css`: the mockup's styles generalised: `.pal-pocket`, `.pal-night`, `.pal-nu` set the CSS variables on `<html>`; `@media (prefers-color-scheme: light)` makes Pocket the no-JS default; `html[lang=pt] [lang=en], html[lang=en] [lang=pt] { display:none }` (spans only, never the `<html>` element); `@media (prefers-reduced-motion: reduce)` disables animations; layout fluid from 360px, centered column max 480px on desktop.
- `site.js` (no dependencies, every `localStorage` access in `try/catch`):
  - `applyPalette(name)`, `applyLang(code)`; initial values from storage, else `prefers-color-scheme` / `navigator.language`.
  - Palette dots (`button[data-palette]`) and language button (`button[data-lang-toggle]`) wired; buttons carry `aria-pressed` and `aria-label`.
  - Spotify: one `fetch(row.dataset.endpoint)` on load with an 4 s `AbortController` timeout; on success update cover, title, artist, href and the ON / Last played label; on any failure do nothing (no retry loop).

- [ ] **Step 1: Write the failing tests** in `tests/test_assets.py`:
  - `test_palettes_pass_wcag_aa` — parse `--box/--ink`, `--bg/--ink-on-bg`, `--box/--accent` (3:1) for each of the three palette blocks in `site.css` and assert ratios with the WCAG relative-luminance formula (`(L1+0.05)/(L2+0.05)`): body pairs ≥ 4.5, accent ≥ 3.0.
  - `test_nu_purple_is_820AD1` — `.pal-nu` block has `--bg:#820ad1` (case-insensitive).
  - `test_storage_access_is_guarded` — every `localStorage` occurrence in `site.js` sits inside a `try {` block (simple scan: count of `localStorage` equals count inside try bodies).
  - `test_spotify_fetch_has_timeout` — `site.js` contains `AbortController`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement**, tuning palette values only as far as needed to pass. **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: palettes, language switch and live Spotify row`.

---

### Task 9: Build CLI and the daily workflow

**Files:**
- Create: `homepage/build.py`, `homepage/__main__.py` (calls `build.main()`), `tests/test_build.py`, `.github/workflows/update-home.yml`
- Modify: `index.html` (generated), `data/state.json` (generated), `assets/live/` (generated)

**Interfaces:**
- Consumes everything above.
- Produces: `build(root: Path, sources: dict[str, Callable[[], object]] | None = None) -> Path` — loads content and state, runs `refresh` for `song, film, book` (+ `repos` as a list, kept the same way), caches `film.poster`, `book.cover`, `song.cover` through `cache_image` and swaps in the local path, prunes unused images, renders, writes `index.html` and `data/state.json`, returns the index path. `sources` lets tests inject fakes. `main()` reads `GITHUB_TOKEN` from the environment.
- Workflow `update-home.yml`: `schedule: "0 9 * * *"` (05:00 Manaus), `workflow_dispatch`, `push` to `main`; steps checkout → setup-uv → `uv run python -m homepage` → git-auto-commit with `file_pattern: index.html data/state.json assets/live/*`, message `chore: refresh homepage`, bot author; same pinned SHAs as `jvitorcosta/jvitorcosta/.github/workflows/update-profile.yml`.

- [ ] **Step 1: Write the failing tests** in `tests/test_build.py` (copy `data/` and `assets/` into `tmp_path`):
  - `test_build_writes_index_and_state` with all-fake sources.
  - `test_failing_source_keeps_previous_value` — state has a book, book source raises → index still contains the old title; stdout has the warning.
  - `test_images_are_local` — index references `assets/live/` for poster and cover, no `ltrbxd.com` or `gr-assets.com` `src`.
  - `test_second_build_is_byte_identical` — same inputs, same output (no timestamps).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Run the real build** `uv run python -m homepage` → prints the warnings (if any) and writes `index.html`.
- [ ] **Step 6: Commit** `feat: daily homepage build`.

---

### Task 10: Resume repo stops owning the homepage

**Files (in `curriculum-vitae`, branch `feat/site-homepage-split`):**
- Modify: `cv/site.py` — remove the `index.html` block and the homepage-only constants (`INTRO`, `OUTSIDE_WORK`, `SKILLS` if unused elsewhere); add `jobs.json` export; `_page()` links `../assets/site.css` and `../assets/site.js` instead of inline `CSS`, adds `<html class="pal-night">` and the three palette dots in a small header (no language switch: case studies are English only, so the back link reads "← Vitor"); sitemap still lists `/` and the case pages.
- Modify: `tests/test_site.py`, `CLAUDE.md` (the site line).

**Interfaces:**
- Produces: `out / "data" / "jobs.json"`: list of `{"title", "company", "start", "end"}` from `_jobs()`, `_date()`-formatted, nothing else.
- The site repo's `data/jobs.json` from Task 7 is replaced by this file on the next `tools/build_site.py --copy-to` run.

- [ ] **Step 1: Update tests first:**
  - replace `test_builds_home_and_one_page_per_case_study` with `test_builds_one_page_per_case_study_and_no_index` (no `index.html` in output).
  - `test_exports_public_jobs_json` — keys exactly `{"title","company","start","end"}`; no `phone`, no `email`.
  - `test_case_pages_use_shared_stylesheet` — `href="../assets/site.css"` present, no inline `<style>`.
  - keep `test_never_publishes_the_phone_number` and sitemap/redirect tests.
- [ ] **Step 2: Run** `uv run pytest tests/test_site.py -v` → FAIL. **Step 3: Implement.** **Step 4: Run** `uv run pytest -v` → all PASS.
- [ ] **Step 5: Commit** `feat(site): homepage moves to the site repo; export jobs, shared stylesheet`.
- [ ] **Step 6: Ask Vitor before copying into the site repo** (that repo's rule), then `uv run python tools/build_site.py --copy-to D:/dev/projects/jvitorcosta.github.io` on the `feat/homepage` branch and check `git status` there: only `projects/`, `data/jobs.json`, sitemap, robots change; `index.html` untouched.

---

### Task 11: Strava terms check

**Files:**
- Modify: `docs/superpowers/specs/2026-11-05-personal-homepage-design.md` (Strava section: record the finding and the source URL)

No code unless the check finds an allowed automatic source.

- [ ] **Step 1:** Read the current Strava API Agreement and Brand Guidelines (developers.strava.com) and confirm or refute "API data may only be shown to the athlete it belongs to".
- [ ] **Step 2:** Check whether strava.com still offers official profile/activity embeds, and whether an embed of a public activity shows a map. Note both in the spec with links.
- [ ] **Step 3:** Report to Vitor in one message: what's allowed, and that the row stays manual (`data/activity.toml`) unless he picks an allowed embed. Do not build an API-fed version.
- [ ] **Step 4: Commit** `docs: Strava terms finding`.

---

### Task 12: Check it like a visitor, then open the PR

- [ ] **Step 1:** Serve the site repo locally (`uv run python -m http.server 8790 --bind 127.0.0.1`) and open it in the browser pane at 360×780 and 1280×900.
- [ ] **Step 2:** For each palette (Pocket, Night Menu, Nu Purple) and each language, screenshot the top and the party; check nothing overflows, the pixel font is only on headings, every row and icon is a working link.
- [ ] **Step 3:** Block `localStorage` (DevTools override or a private window) and disable JS once each: the page must still render fully in English with a readable palette.
- [ ] **Step 4:** Point the Spotify endpoint at a dead URL in the page (temporarily edit `data-endpoint` in the served copy): the row stays on the saved song, no console error loop.
- [ ] **Step 5:** Run `design:accessibility-review` on the screenshots and fix anything it flags at AA.
- [ ] **Step 6:** Open the site repo PR (`feat/homepage` → `main`) with screenshots, the Portuguese copy flagged for Vitor's review, and the list of things still needed from him (Instagram handle, Spotify profile URL, photos, Strava decision). Do not merge: merging publishes.
