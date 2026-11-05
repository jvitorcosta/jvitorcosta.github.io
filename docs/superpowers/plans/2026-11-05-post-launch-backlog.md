# Post-launch Backlog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear the backlog left after the homepage launch: get the daily refresh publishing again, bring the copy and link preview in line with the new intro, stop stale caches on case pages, fill the last emoji tile, and tidy branches and dependencies.

**Architecture:** Two repos. `jvitorcosta.github.io` (this repo) builds `index.html` with the stdlib-only `homepage/` package and is served by GitHub Pages. `curriculum-vitae` generates `projects/*.html`, `og-image.png`, `favicon.svg`, sitemap and robots, and copies them in with `tools/build_site.py --copy-to`. A third repo, `jvitorcosta/jvitorcosta` (GitHub profile), only gets a cron change.

**Tech Stack:** Python 3.12 via uv, pytest, GitHub Actions, GitHub Pages, headless Chrome for image rendering.

**Spec:** `docs/superpowers/specs/2026-11-05-personal-homepage-design.md` (the original design). The backlog itself was agreed in chat on 2026-11-05; each task below names the item it closes.

## Global Constraints

- Merging to `main` publishes. Open PRs; never merge. João merges.
- `curriculum-vitae`: ask João before pushing anything that publishes. Never read `curriculum-vitae/private/`. Stage files by name, never `git add -A`.
- Commits are João's own work: no co-author trailer.
- `homepage/` stays stdlib-only. Pillow is allowed only in one-off tools run with `uv run --no-project --with pillow`.
- No maps, locations or health data on the site. Strava data links read "View on Strava".
- Photos go through an EXIF check (no GPS) before they are committed; cars must not show a licence plate.
- Tests: `uv run --python 3.12 --group dev pytest` (site), `uv run --python 3.12 pytest` (cv). Both stay green after every task.
- Browser checks at 360px width, EN and PT, in the Nu Purple theme at least.

## Review Focus

- A daily run where every source fails must still publish the last good page, not an empty one (Task 1).
- A daily run where nothing changed must not create a commit or a deploy error (Task 1).
- A source failing quietly for a week must be visible somewhere João looks (Task 7).
- Case pages built without `--copy-to` (no site checkout next to them) must still build, just without a version tag (Task 4).
- A visitor whose browser blocks `data:` images must still see the Spotify row, without a cover (Task 9).

---

## Decisions João makes before execution

| # | Question | Default if not answered |
|---|----------|-------------------------|
| D1 | Daily refresh: deploy Pages from Actions (Task 1A) or let GitHub Actions bypass `protect-main` (Task 1B)? | 1A |
| D2 | Intro: keep "Here, I try to keep my passion for tech alive." or switch to "This is my corner of the internet, where I keep my passion for tech alive."? | Keep the current intro |
| D3 | Privacy page for the Google OAuth app: still needed? | Yes: port it (Task 8) |
| D4 | Open Radars tile: a photo João sends, or a pixel-art speed-camera tile? | Pixel tile |

---

### Task 1A: Publish the daily refresh through GitHub Actions (D1 = 1A)

Closes: "daily refresh is broken". The job can't push to `main` because the `protect-main` ruleset (id 26615241) only accepts PRs. Instead of pushing generated files, the job keeps its memory on an unprotected `state` branch and deploys the built site as a Pages artifact.

**Files:**
- Modify: `.github/workflows/update-home.yml`
- Modify: `.gitignore` (add `index.html`, `data/state.json`, `assets/live/`)
- Create: `docs/deploy.md` (how the site is published, how to run a build locally)
- Repo setting (João approves): Pages source → "GitHub Actions"

**Interfaces:**
- Produces: branch `state` holding only `data/state.json` and `assets/live/*`. Later tasks that change the build don't need to know about it.

- [ ] **Step 1: Create the `state` branch from the current generated files**

```bash
git switch --orphan state
git checkout main -- data/state.json assets/live
git commit -m "chore: seed state branch"
git push -u origin state
git switch main
```

- [ ] **Step 2: Rewrite `update-home.yml`**

Two jobs. `build` (permissions `contents: write` for the `state` push only) does:
1. Check out `main`.
2. Check out `state` into `.state/` (`actions/checkout`, `ref: state`, `path: .state`), then copy `.state/data/state.json` and `.state/assets/live/` into place. A missing `state` branch must not fail the job: the build already treats a missing state file as empty.
3. Run `uv run --locked --no-dev python -m homepage`.
4. Copy `data/state.json` and `assets/live/` back into `.state/`. Commit and push there only when `git -C .state status --porcelain` is non-empty.
5. Remove `.state/`, then run `actions/upload-pages-artifact` with `path: .`.

`deploy` (needs `build`; permissions `pages: write`, `id-token: write`; environment `github-pages`) runs `actions/deploy-pages`.

Keep the triggers (cron, `workflow_dispatch`, push to `main`). Pin every action to a full SHA with a `# vX.Y.Z` comment, as the existing file does.

- [ ] **Step 3: Stop tracking generated files on `main`**

Remove them from git tracking, then add them to `.gitignore`:

```bash
git rm --cached index.html data/state.json -r assets/live
```

Local builds still write these files; they just aren't committed any more.

- [ ] **Step 4: Write `docs/deploy.md`**

Cover four things:
- the two jobs and what each does;
- why the `state` branch exists;
- that `index.html` is no longer in git;
- how to preview locally: `uv run --python 3.12 python -m homepage`, then `python -m http.server`.

- [ ] **Step 5: Open the PR.** Its description lists the setting João must flip **before** merging (Pages → Source → GitHub Actions). Merging before that leaves the old legacy deploy serving a `main` without `index.html`.

- [ ] **Step 6: After João merges, verify**

Run: `gh workflow run update-home.yml` and wait for it, then `curl -s https://jvitorcosta.github.io/ | grep -c 'id="trainer"'`
Expected: the run is green with both jobs, the curl prints `1`, and the `state` branch has a new commit only if something changed.

### Task 1B: Let GitHub Actions bypass `protect-main` (D1 = 1B, instead of 1A)

- [ ] **Step 1:** João adds the GitHub Actions integration to the bypass list of ruleset `protect-main` (Settings → Rules → protect-main → Bypass list → Add bypass → GitHub Actions). This is a security setting, so João changes it.
- [ ] **Step 2: Verify.** Run: `gh workflow run update-home.yml`. Expected: green, and `git log origin/main -1` shows "chore: refresh homepage" when something changed.

### Task 2: Page title, description and intro copy

Closes: "page title and description out of date". Also applies D2.

**Files:**
- Modify: `data/strings.toml` (`page_title`, `page_description`, and `intro` if D2 says switch, in both `[en]` and `[pt]`)
- Test: `tests/test_content.py:75` (the exact title assertion)

- [ ] **Step 1: Update the expected title in `tests/test_content.py`** to `"Vitor Pinheiro · engineer from Manaus"`. Run the test and expect FAIL.
- [ ] **Step 2: Set the new copy**

| Key | `[en]` | `[pt]` |
|---|---|---|
| `page_title` | `Vitor Pinheiro · engineer from Manaus` | `Vitor Pinheiro · engenheiro de Manaus` |
| `page_description` | `Engineer from Manaus. What I've been listening to, watching, reading and training lately, and the gadgets I build for my car, my watch and my city.` | `Engenheiro de Manaus. O que eu ando ouvindo, assistindo, lendo e treinando, e os gadgets que eu crio pro meu carro, meu relógio e minha cidade.` |

- [ ] **Step 3: Run the full suite and expect PASS.** Rebuild, then commit `data/strings.toml` and `tests/test_content.py`. Open a PR.

### Task 3: Regenerate the link-preview image from a committed tool (cv repo)

Closes: "og-image still shows the old intro".

**Files:**
- Create: `curriculum-vitae/tools/og_image.py`
- Modify: `curriculum-vitae/cv/site_assets/og-image.png` (the generated output)

**Interfaces:**
- Produces: `python tools/og_image.py --site <site checkout> --intro "<text>"` writes `cv/site_assets/og-image.png` (1200×630).

- [ ] **Step 1: Write `tools/og_image.py`**

It writes a temporary HTML page and renders it with headless Chrome:

```
chrome --headless=new --hide-scrollbars --allow-file-access-from-files --window-size=1200,630 --screenshot=<out> <html>
```

Find Chrome via `--chrome`, else `CHROME` in the environment, else the default Windows path.

Use the layout and colours from the image published on 2026-11-05:
- Nu Purple background `#820ad1`.
- Card `#f7f0e1` with an 8px `#2a0845` border and a 16px `#4a0478` offset shadow.
- Avatar `<site>/assets/avatar.png` at 288px with `image-rendering: pixelated`, on `#e9dcc2`.
- "▶ TRAINER CARD", "VITOR" and the URL in Press Start 2P. The intro in Inter 500 at 36px.
- Fonts come from `<site>/assets/fonts`.

- [ ] **Step 2: Run it with the current intro.** Look at the PNG. Expected: the text fits on at most three lines and nothing is clipped.
- [ ] **Step 3: Commit, then copy into the site.** Commit the tool and the PNG in cv. Copy into the site with `build_site.py --copy-to` (only `og-image.png` should change), and open PRs in both repos.

### Task 4: Version the stylesheet link on case pages (cv repo)

Closes: "case pages can show stale styles". Mirrors `homepage.markup.versioned()` in the site repo.

**Files:**
- Modify: `curriculum-vitae/cv/site.py` (`_page()` stylesheet link; `build_site()`)
- Test: `curriculum-vitae/tests/test_site.py`

**Interfaces:**
- Produces: `_css_href(out: Path) -> str`. It returns `"../assets/site.css?v=<first 8 hex of sha256 of out/assets/site.css>"` when that file exists, else `"../assets/site.css"`.

- [ ] **Step 1: Write the failing tests**

```python
def test_case_page_stylesheet_is_versioned_when_the_site_css_is_there(tmp_path):
    out = tmp_path / "out"; (out / "assets").mkdir(parents=True)
    (out / "assets" / "site.css").write_text("body{}", encoding="utf-8")
    build_site(ROOT, PROFILE, out)
    page = (out / "projects" / "solvedor.html").read_text(encoding="utf-8")
    digest = hashlib.sha256(b"body{}").hexdigest()[:8]
    assert f'<link rel="stylesheet" href="../assets/site.css?v={digest}">' in page

def test_case_page_stylesheet_is_plain_without_the_site_css(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    page = (tmp_path / "projects" / "solvedor.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="../assets/site.css">' in page
```

- [ ] **Step 2: Run them and expect the first to FAIL.**
- [ ] **Step 3: Implement `_css_href` and use it.** Pass the result into `_page()`, which renders the link. Run the cv suite and expect PASS.
- [ ] **Step 4: Commit, push, copy into the site, and open PRs.** After the copy, every `projects/*.html` should carry the same `?v=` as `index.html`'s stylesheet.

### Task 5: Open Radars tile (D4)

Closes: "Open Radars still shows 📍".

**Files:**
- With a photo: create `assets/party/open-radars-manaus.jpg`. EXIF check, no plates; resize with Pillow to fit within 640×640, quality 82.
- Without a photo: add a `speed_camera` grid to `tools/pixel_icons.py` and write `assets/party/open-radars-manaus.svg`. The tile is 20×20, mirroring the icon tool.
- Modify: `data/party.toml` (`picture = "assets/party/open-radars-manaus.<ext>"` on the `open-radars-manaus` member; keep `emoji` as the fallback)
- Modify: `tests/test_build.py:93`. `test_failed_download_never_hotlinks` injects a remote picture next to `emoji = "📍"`. Point it at a member that has no `picture` left. If none is left, give the test its own `member()` from the test helpers instead of editing `data/party.toml` text.

Pixel tile spec:
- 20×20, `shape-rendering="crispEdges"`.
- Background `#ead9fb`.
- A grey pole (`#5f5e5a`) with a dark camera box (`#2a0845`) and a red lens (`#d63333`).
- A yellow speed sign (`#ffb703`) with "60" left out. Two pixels can't carry digits.

- [ ] **Step 1: Add the picture.** With a photo, resize and check EXIF. Without one, add the grid and run `python tools/pixel_icons.py assets/icons`. That writes the icons; write the party tile with a second output path argument, or a `--party` flag.
- [ ] **Step 2: Fix the test (as above), then run the suite and expect PASS.** Check the tile in the browser at 360px, then commit and open a PR.

### Task 6: Cyberdeck photos on the case page (cv repo)

Closes: "more Cyberdeck photos".

**Files:**
- Create: `curriculum-vitae/case-studies/images/car-cyberdeck/companion.jpg`, `dashboard-night.jpg`, `yellow-deck-night.jpg`. Sources: `inbox/cyberdeck-photos/clean/cyberdeck-companion.jpg`, `inbox/cyberdeck-photos-2/clean/dashboard-night.jpg` and `inbox/cyberdeck-photos-2/clean/yellow-deck-night.jpg`. Each must pass the EXIF check and fit within 1200×1200 at quality 82.
- Modify: `curriculum-vitae/case-studies/car-cyberdeck.md` and `car-cyberdeck.pt.md`:
  - front matter `cover: images/car-cyberdeck/companion.jpg` with `cover_alt`;
  - one `![alt](images/car-cyberdeck/<file>)` image after the "How it grew" heading;
  - one image after the paragraph about the lights screen.

Alt text (EN / PT):
- **companion:** "The Game Boy Advance shell on the dashboard, showing a song as a Pokémon battle" / "A carcaça de Game Boy Advance no painel, mostrando uma música como batalha Pokémon".
- **dashboard-night:** "Both screens and the phone at night on the dashboard" / "As duas telas e o celular à noite no painel".
- **yellow-deck-night:** "The yellow lights screen at night" / "A tela amarela das luzes à noite".

- [ ] **Step 1: Look at each photo at full size before copying.** No plates, no faces, and no readable personal notifications. The phone screen in `dashboard-night` is already blurred; keep it that way.
- [ ] **Step 2: Copy, resize, edit both markdown files, then run the cv suite and expect PASS.**
- [ ] **Step 3: Build into the site and check the page.** Check `projects/car-cyberdeck.html` in the browser in EN and PT. Commit, then open PRs in both repos.

### Task 7: Make silently failing sources visible

Closes: "Goodreads scraping is fragile". The scraper stays; failures become visible within days instead of never.

**Files:**
- Modify: `homepage/state.py` (`refresh()`)
- Modify: `homepage/build.py` (write the summary)
- Test: `tests/test_state.py`, `tests/test_build.py`

**Interfaces:**
- Produces: `state["updated"]: dict[str, str]`, the source name mapped to the ISO date of its last successful fetch. `refresh(..., today: str)` sets it on success.
- Produces: `stale_sources(state: dict, today: str, days: int = 7) -> list[tuple[str, int]]` in `homepage/state.py`.

- [ ] **Step 1: Write the failing tests**

```python
def test_refresh_records_the_day_of_the_last_success():
    state = {}
    refresh("book", lambda: BOOK, state, Book, today="2026-11-05")
    assert state["updated"]["book"] == "2026-11-05"

def test_failed_refresh_keeps_the_old_success_day():
    state = {"updated": {"book": "2026-11-01"}, "book": to_dict(BOOK)}
    refresh("book", boom, state, Book, today="2026-11-05")
    assert state["updated"]["book"] == "2026-11-01"

def test_stale_sources_lists_only_those_older_than_a_week():
    state = {"updated": {"book": "2026-10-28", "film": "2026-11-04"}}
    assert stale_sources(state, "2026-11-05") == [("book", 8)]
```

In `tests/test_build.py`, add a test that builds with `GITHUB_STEP_SUMMARY` set to a temp file and a state whose `updated["book"]` is 10 days old. Assert the file contains `book` and `10 days`, and stderr contains `::warning::book has not updated for 10 days`.

- [ ] **Step 2: Run them and expect FAIL.**
- [ ] **Step 3: Implement**
  - `refresh` gains `today`; callers in `build.py` pass `date.today().isoformat()`.
  - `build.py` calls `stale_sources` after refreshing and prints one `::warning::` per stale source.
  - When `GITHUB_STEP_SUMMARY` is set, `build.py` appends a Markdown table (Source, Last update, Days).
  - A missing or non-dict `updated` is treated as empty.
- [ ] **Step 4: Run the suite and expect PASS. Commit and open a PR.**

### Task 8: Privacy pages for the Google OAuth app (D3)

Closes: "unmerged privacy branches". `origin/add-privacy-page` (site) adds a hand-written `privacy.html` plus a sitemap line. `origin/site/privacy` (cv) adds it to the generator, which is the right home now that the cv generator owns the case pages, the sitemap and robots.

- [ ] **Step 1: If D3 = keep, port the cv branch onto current `main`**
  - Branch `feat/privacy-page` from cv `main`.
  - Cherry-pick `1b3ca6d`, then resolve against the new `cv/site.py`: the page uses `_page()` and the shared header, is English-only, and is listed in the sitemap.
  - Run the cv suite and expect PASS.
  - Build into the site and confirm `privacy.html` renders.
  - Open PRs in both repos.
  - Delete the stale branches only after João merges: `origin/site/privacy` and the site's `origin/add-privacy-page`.
- [ ] **Step 1 (alternative): If D3 = drop**, ask João to confirm, then delete both remote branches.

### Task 9: Serve the Spotify cover without contacting Spotify (spotify-now-playing + site)

Closes: "the Spotify cover loads from Spotify's servers".

**Files:**
- Modify: `spotify-now-playing/api/orchestrator.py` (`now_playing_json()`): add `"cover_data"`, a `data:image/jpeg;base64,…` string of the **smallest** album image (64px). Use the existing image loader with a 2s timeout. Leave it out on any error.
- Test: `spotify-now-playing` tests for `now_playing_json`, with the fetch mocked.
- Modify: `assets/site.js` (the cover block at lines 99-107): prefer `data.cover_data` when it starts with `data:image/jpeg;base64,` or `data:image/png;base64,`; else fall back to `safeHttps(data.cover)`.
- Modify: `tests/test_assets.py`: assert `site.js` accepts only those two `data:` prefixes.

- [ ] **Step 1: Endpoint test and change.** Write the test and run it (FAIL), implement, run again (PASS). Open a PR in the fork. João deploys it via Vercel.
- [ ] **Step 2: Site JS test and change.** Same cycle, then a PR in the site repo. Merge it only after the endpoint is live; until then the old field keeps working.

### Task 10: Refresh the GitHub profile's Letterboxd card more often (profile repo)

Closes: "the profile card updates once a day".

- [ ] **Step 1: Change the cron.** In the `jvitorcosta/jvitorcosta` repo's `.github/workflows/update-profile.yml`, change `cron: "0 9 * * *"` to `cron: "0 9,21 * * *"`, with the comment `# 05:00 and 17:00 in Manaus`.
- [ ] **Step 2: Open a PR.** After merge, `gh run list --workflow update-profile.yml` should show two scheduled runs a day.

### Task 11: Patch `pypdf` in curriculum-vitae (Dependabot)

Closes: "10 high Dependabot alerts". All ten are `pypdf` in `uv.lock`.

- [ ] **Step 1: Upgrade.** Branch, then run `uv lock --upgrade-package pypdf`. Then `uv run --python 3.12 pytest` and expect PASS.
- [ ] **Step 2: Check the resume still builds.** Rebuild the PDF the way the README says. The output must still open, and its page count must not change.
- [ ] **Step 3: Commit `uv.lock` and open a PR.** After merge, `gh api repos/jvitorcosta/curriculum-vitae/dependabot/alerts -q '[.[]|select(.state=="open")]|length'` should print `0`.

### Task 12: Delete merged local branches

- [ ] **Step 1: Delete.** Run `git branch -d` on each (not `-D`, so git refuses anything unmerged):
  - site: `polish/after-launch`, `fix/asset-versions`;
  - cv: `feat/site-homepage-split`.
  
  Delete the matching remote branches only if João says so.

### Task 13: João's own steps (no code)

- Instagram app: Edit profile → Links → Add external link → `https://jvitorcosta.github.io`, titled as João likes ("My corner of the internet" was the suggestion).
- Answer D1–D4.
- Merge each PR after reading it. Flip the Pages source before merging Task 1A.

---

## Order

1. Run 1A (or 1B), 2, 3 and 4 first: they fix what visitors see today.
2. Tasks 5 and 6 are independent of each other and of 1–4.
3. Task 7 depends on 1A only if 1A changes `build.py` callers; it doesn't, so it can run any time.
4. Tasks 8–12 are independent.
5. Each task ends in its own PR, so João can merge them one by one.
