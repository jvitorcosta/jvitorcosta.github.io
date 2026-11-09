# Architecture

## The pieces

```
data/*.toml, data/jobs.json        hand-written content (text, tiles, links, jobs)
        │
        ▼
homepage/  (Python 3.12, standard library only)
  content.py   reads data/ into a Content object
  sources/     one module per outside service, each returns one small dataclass
  state.py     remembers the last good value of every source (data/state.json)
  images.py    downloads covers and posters into assets/live/
  render.py    the page: head, trainer card, Favorites, Projects, Experience, footer
  right_now.py the Lately box: song, film, anime, book, activity
  markup.py    shared HTML helpers: escaping, safe links, both-language text, dates
  build.py     runs all of the above in order and writes index.html and 404.html
        │
        ▼
index.html, 404.html, assets/live/   built files, never committed
        │
        ▼
assets/site.css, assets/site.js      styles and the small browser script, shared with the case pages
```

There are no third-party Python packages and no SDKs. Each service is reached with
`urllib.request` through `homepage/http.py`, which adds a user agent and a 30-second timeout.
That keeps the build to `python -m homepage` with nothing to install, so a library update can
never break it. The only dev dependency is pytest.

## One build, step by step

`python -m homepage` runs `homepage/build.py:main`:

1. **Load the content.** `content.load_content` reads `data/strings.toml`, `party.toml`,
   `pc_box.toml`, `links.toml`, `activity.toml` and `jobs.json`. A broken `activity.toml` skips that
   row with a warning instead of failing the build. More than 6 Favorites tiles is an error.
2. **Load the state.** `state.load_state` reads `data/state.json`: the last good value of each
   source under its name (`"song"`, `"film"`…), and an `"updated"` map from each name to the day
   it last succeeded. In the workflow that file comes from the `state` branch
   (see [deploy.md](deploy.md)). An unreadable file starts empty with a warning.
3. **Refresh each source.** `state.refresh(name, fetch, state, cls, today)` calls the source:
   - It succeeds with a value: the value is saved in the state with today's date and used.
   - It returns `None` (nothing to show) or raises: a `::warning::` is printed and the last saved
     value is used, so the page never goes blank because one site is down.
   - A saved value that no longer fits its dataclass (an old format, a hand edit) is dropped with a
     warning instead of failing.

   Book has one special case: when the Goodreads profile loads but lists nothing on the
   currently-reading shelf, the last book is kept and marked finished. Activity comes from Strava
   only when the Strava secrets are set; otherwise, or until Strava first answers, it is the
   hand-written row in `data/activity.toml`.
4. **Download the pictures.** Every remote cover, poster and tile picture goes through
   `images.cache_image`: the file is saved as `assets/live/<first 16 hex characters of the URL's
   SHA-1>.<ext>` and the page
   points at that local copy. A picture that fails to download leaves the row without a picture;
   the remote URL is never put in the page. Files no longer used are deleted (`images.prune`).
   The extension is kept only when it is `.jpg`, `.jpeg`, `.png` or `.webp`; anything else (a
   remote `.svg` included) is saved as `.jpg`, so it can never run as a script.
5. **Render.** `render.render_home` writes the page, `render.render_404` the not-found page.
   Line endings are normalised to LF, so two builds from the same data give the same bytes.
6. **Save and report.** The state is written back. `build.report_stale` lists every source whose
   day in `"updated"` is more than 7 days old (a source that has never succeeded has no day, so
   it is never reported): as warnings, as a table in the run summary,
   and as the `stale` step output the workflow's alert job reads.

## The data model

`homepage/model.py` holds one frozen dataclass per row: `Song`, `Film`, `Book`, `Anime`,
`Activity`, `Repo`, plus `LiveData` that carries the five live rows. `to_dict` and `from_dict`
turn them into the JSON kept in `data/state.json`; `from_dict` ignores keys a class no longer has,
so adding or removing a field never breaks an old state file.

`homepage/content.py` holds the hand-written side: `Content`, `PartyMember` (a Favorites tile)
and `Job`.

## The page

`render_home` builds the body from two lists:

| Column (wide screens) | Sections, in code order |
|---|---|
| left, `.col.side` | trainer card, Favorites (`#party`), Experience (`#work`) |
| right | Lately (`#right-now`), Projects (`#pc-box`) |

Section names on the page differ from the names in code because the page was renamed after the
code was written. The code keeps the old names:

| On the page | In code and data |
|---|---|
| FAVORITES 最爱 | `party`, `data/party.toml`, `#party` |
| LATELY 最近 | `right_now`, `#right-now` |
| PROJECTS 项目 | `pc_box`, `data/pc_box.toml`, `#pc-box` |
| EXPERIENCE 经历 | `work`, `data/jobs.json`, `#work` |

How each section decides what to show:

- **Trainer card:** name and Chinese name, intro, motto, and the Instagram, GitHub, LinkedIn and
  Email buttons from `data/links.toml` (an empty link is left out).
- **Favorites:** the tiles in `data/party.toml`, in file order. A tile links to its `url` if set,
  else to `projects/<repo>.html` when that case page exists, else to the GitHub repo. A tile
  whose repo is not in the GitHub list and has no `url` is skipped with a warning.
- **Lately:** song, film, anime, book, activity, in that order; a row with no data is left out.
  See [sources.md](sources.md) for how each row is picked.
- **Projects:** my public repos minus the ones already shown as Favorites. Pinned rows from
  `data/pc_box.toml` come first in file order, then the rest newest-pushed first, with coursework
  (`tag = "uni"` or `"course"`) last. Only the first 5 show (`PC_BOX_ROWS`), then a
  "+ n more" link to GitHub. A row's name links to its case page when there is one, with a
  separate "GitHub ›" link; a repo with a homepage set on GitHub gets "try it ›".
- **Experience:** one line per role from `data/jobs.json` (title, company, dates in the page's
  language), a LinkedIn button and a link to the resume case page.
- **Footer:** where the data comes from and how often the page refreshes.

The `<head>` carries the title and description from `strings.toml`, Open Graph tags with
`og-image.png`, the favicons, a small inline script that applies the saved palette and language
before the page paints (so neither flashes), and JSON-LD describing me as a `Person`.

## Both languages in one page

Every visible text is written twice, as `<span lang="en">…</span><span lang="pt">…</span>`, by
`Page.t(key)` (a key of `strings.toml`) or `Page.both({"en": …, "pt": …})`. `site.css` hides the
spans that don't match `<html lang>`, and the EN > PT button only changes that attribute. So
there is one URL, no reload and nothing fetched when switching. Labels for screen readers
(`aria-label`) and hover names (`title`) carry `data-aria-en`/`data-aria-pt` and
`data-title-en`/`data-title-pt`, and `site.js` swaps them.

The first language is the one saved from the last visit, else Portuguese when the browser asks
for Portuguese, else English.

Chinese subtitles are not a third language: they are shown in both, with `lang="zh-Hans"` so
screen readers pronounce them right, from the `<key>_zh` strings.

## The browser side: `assets/site.js`

The page works without JavaScript. With it:

- **Palette dots** switch between `night` and `nu` and remember the choice in `localStorage`.
  Without a saved choice, a system in light mode gets `nu`.
- **Language button** switches `<html lang>` and remembers it.
- **Spotify row:** the build's song is hours old, so it is always shown as LISTENED. On load,
  `site.js` asks the Spotify endpoint once (4-second timeout, no cookies) and puts its answer in
  the row; only when a song is playing does the row say LISTENING, with ON and moving bars. On any failure the built row
  stays. Fetched text is set with `textContent`, never `innerHTML`, and only `https` links and
  JPEG/PNG data URIs are accepted.

Every `localStorage` access is inside `try`, since private windows can throw.

## Cache busting

`markup.versioned(path)` adds `?v=<8-character hash of the file>` to `site.css`, `site.js`, the
icons and `og-image.png`, so a browser fetches a new copy as soon as the file changes. The hash
ignores CRLF vs LF, so a Windows build and the Linux runner agree. The case pages come from
another repo but compute the same hash, and a test fails when they point at an old one.

## Tests

```bash
uv run --python 3.12 --group dev pytest
```

| File | Covers |
|---|---|
| `test_build.py` | a whole build in a temp folder: fallbacks, local images, pruning, identical rebuilds, stale report, Strava switch, 404 |
| `test_state.py` | loading broken state, refresh, stale detection |
| `test_<source>.py` | each source's parsing and errors, against saved real answers in `tests/fixtures/` (Spotify and GitHub use inline ones) |
| `test_render.py` | section order, rows, links, both languages, headings, escaping |
| `test_content.py` | reading `data/`, bad files |
| `test_assets.py` | palette contrast (WCAG AA), self-hosted fonts, storage guards, Spotify timeout and cover rules (with Node), case-page asset hashes, layout rules |
| `test_images.py` | picture caching and pruning |
| `test_workflow.py` | the workflow's state-branch logic, run as real shell against temp git repos |

No test calls the real services: sources take a `get` function, and tests pass a fake one.
