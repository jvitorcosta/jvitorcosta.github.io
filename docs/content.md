# Editing the content

All hand-written text lives in `data/`, so a content change never touches code. Open a PR, and
the merge publishes it.

| File | What it holds |
|---|---|
| `data/strings.toml` | every piece of page text, in an `[en]` and a `[pt]` table |
| `data/party.toml` | the Favorites tiles |
| `data/pc_box.toml` | names, lines, tags and pins for rows in Projects |
| `data/links.toml` | profile links (trainer buttons, the tiles at the end of each Lately row) |
| `data/activity.toml` | the activity row used when Strava is off |
| `data/jobs.json` | Experience roles, **copied from curriculum-vitae, don't edit here** |

Before opening the PR:

```bash
uv run --python 3.12 --group dev pytest
uv run --python 3.12 python -m homepage && python -m http.server 8000
```

and look at http://localhost:8000 in both languages, on a phone width too.

## Page text: `data/strings.toml`

- Both tables must have the same keys. `{braces}` are filled in by the code (`{n}`, `{page}`).
- The Chinese name, the motto and the `*_zh` subtitles are the same in both tables; the page
  shows them once.
- `page_title` and `page_description` (English) become the browser tab, the search result and
  the link preview.
- PC box tag labels are `tag_<name>` (`tag_ai`, `tag_uni`…).

## A Favorites tile: `data/party.toml`

At most 6 tiles; 4 make the 2×2 grid the page is designed around. Tiles show in file order.

```toml
[[member]]
repo = "garmin-watchfaces"        # GitHub repo under jvitorcosta
tag = "WRIST"                     # small label on the picture: one word, caps
picture = "https://…/photo.jpg"   # optional: site path or https URL
emoji = "⌚"                       # shown when there's no picture
name_en = "Watch faces"
name_pt = "Mostradores"
blurb_en = "Faces I code for my Garmin"
blurb_pt = "Mostradores que eu programo pro Garmin"
url = "projects/…html"            # optional, see below
```

- **Where it links:** `url` if set, else `projects/<repo>.html` when that case page exists,
  else the GitHub repo.
- **Picture:** a remote picture is downloaded at build time like every cover, so it must be
  `.jpg`, `.png` or `.webp`. A local file goes in `assets/party/` (the Open Radars map there is
  drawn by hand as SVG; local SVGs are fine).
- A repo shown as a tile is left out of Projects, so it never appears twice.
- How to word the blurb is in [design.md](design.md#card-and-row-wording).

## A Projects row: `data/pc_box.toml`

Every public repo gets a row automatically (forks, archived and private repos aside). Without
an entry here, a row shows the repo name and its GitHub description. An entry gives it plain
words. Write both languages: a line is used only when `en` and `pt` are both set, and a title
only when `title_en` and `title_pt` both are; otherwise that part falls back.

```toml
[ask-vitor]                       # the repo name
title_en = "Ask Vitor"
title_pt = "Pergunte ao Vitor"
tag = "ai"                        # ai, data, tool, gadget, uni or course
pin = true                        # optional: pinned rows lead, in file order
en = "a bot about me on my own PC that says when it doesn't know"
pt = "um robô sobre mim no meu PC que admite quando não sabe"
case = "ask-vitor"                # optional: projects/<case>.html when that page exists
```

- Lines are cut at 60 characters, on a word, with "…", so keep them shorter.
- Only 5 rows show. Pinned rows come first, then the newest pushed, with `uni` and `course`
  last; the rest are behind "+ n more".
- A repo's homepage on GitHub (the "Website" field) gives the row a "try it ›" link.
- The GitHub repo description is still worth keeping current: it shows when there's no entry
  here, and on GitHub itself.

## Links: `data/links.toml`

`instagram`, `github`, `linkedin`, `email` are the trainer buttons. `resume` is the filled button in
Experience; it points at `Vitor_Pinheiro_Resume.pdf` at the site root, a copy of `resume/` in the
curriculum-vitae repo: copy it again whenever the resume changes. `spotify`, `letterboxd`,
`myanimelist`, `goodreads`, `strava` are the tiles at the end of each Lately row. An empty value
hides that button or makes the tile a plain picture. Only `http(s)`, `mailto` and site paths are
allowed.

## The fallback activity: `data/activity.toml`

Used only when the Strava secrets aren't set or Strava has never answered. Same fields as a
Strava row. Leave out `distance_km` for activities without distance. Never add maps, routes,
places or health data.

## Experience and the case pages

`data/jobs.json`, `projects/`, `privacy.html`, `og-image.png`, `sitemap.xml` and `robots.txt` are
generated in [curriculum-vitae](https://github.com/jvitorcosta/curriculum-vitae) from its job
files and `case-studies/*.md`. To change a role or a case page, change it there, then copy:

```bash
cd ../curriculum-vitae
uv run --python 3.12 python tools/build_site.py --copy-to ../jvitorcosta.github.io
cd ../jvitorcosta.github.io
git checkout -- favicon.svg      # this site keeps its own pixel favicon
git status                       # review, then open a PR here
```

Re-copy also after any change to `assets/site.css` or `assets/site.js`: the case pages point at
those files with a hash of their content, and `tests/test_assets.py` fails until they match.

## Icons: `tools/pixel_icons.py`

The 20×20 app tiles in `assets/icons/` are drawn as text grids in `tools/pixel_icons.py`
(it also writes a 32×20 `assets/party/open-radars-manaus.svg`, which the page no longer uses; the
tile uses the hand-made `open-radars-manaus-map.svg`): one character per pixel, `.` for the background, a colour per letter.
Edit the grid, then:

```bash
uv run --python 3.12 python tools/pixel_icons.py assets/icons assets/party
git status
```

The script rewrites every icon. Keep only the ones you meant to change (`git checkout --` the
rest); on Windows the others may differ only in line endings. A new tile's first colour must be
the brand colour in `markup.PLATFORMS`, and its glyph must reach 3:1 contrast on it (a test
checks).

## Palettes and styles

`assets/site.css` defines each palette as a `.pal-<name>` block of colour tokens. Pages start with
`class="pal-nu"`, so visitors without JavaScript get Nu Purple. The
list of palettes is in three places that must agree: `render.PALETTES`, `PALETTES` in
`assets/site.js`, and `cv/site.py` in curriculum-vitae. Every palette must pass the contrast
tests in `tests/test_assets.py`.
