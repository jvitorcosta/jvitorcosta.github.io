# How the site is published

`.github/workflows/update-home.yml` builds the page and publishes it straight to GitHub Pages.

## When it runs

- **Every 4 hours:** 00:00, 04:00, 08:00, 12:00, 16:00 and 20:00 Manaus time. The cron line is
  in UTC (`0 0,4,8,12,16,20 * * *`); Manaus is UTC-4 all year, so the same six hours work out to
  those local times. GitHub can start scheduled runs 10 to 30 minutes late.
- **On every push to `main`**, so a merged change is live in a couple of minutes.
- **On demand:** `gh workflow run update-home.yml`, or Actions → Update homepage → Run workflow.

Runs never overlap (`concurrency: update-home`); a new one waits for the current one.

## The three jobs

1. **build** (`contents: write`, used only to push the `state` branch)
   1. Checks out `main`.
   2. Fetches the `state` branch into `.state/`. A missing branch means a first build: it
      starts empty. A branch that exists but can't be fetched fails the job, so a page built from
      empty state is never published.
   3. Copies `data/state.json` and `assets/live/` from `.state/` into the checkout.
   4. Installs uv and runs `uv run --locked --no-dev python -m homepage`, with `GITHUB_TOKEN`
      and the three Strava secrets in the environment.
   5. Copies the new state back into `.state/` and pushes it to `state` as
      `github-actions[bot]`, only when something changed.
   6. Deletes `.state/` and uploads the whole folder as the Pages artifact.
2. **deploy** (`pages: write`, `id-token: write`) publishes that artifact.
3. **alert** runs only when the build reported stale sources. It fails with the list of
   sources that haven't updated for over a week (only sources that have worked at least once
   are tracked), so GitHub emails me. It runs after the deploy,
   so the page still updates with everything else.

Every action is pinned to a full commit SHA with its version in a comment. Dependabot is turned on
in the repo settings (there is no `dependabot.yml`) and has opened PRs to update them.

## Why a `state` branch

`main` is protected by the `protect-main` ruleset: changes only arrive through pull requests. The
scheduled job can't push there, so it keeps its memory somewhere it can push:

- `data/state.json`, the last good value of every source and the day it last updated.
- `assets/live/`, the covers and posters downloaded for the current page.

The `state` branch holds only those files. Deleting it is safe: the next run starts from empty
state and creates it again. Until each source answers once, its row is missing (the activity
row falls back to `data/activity.toml`).

`index.html`, `404.html`, `data/state.json` and `assets/live/` are built, not committed, and
listed in `.gitignore`. To look at the current state:

```bash
git fetch origin state
git show origin/state:data/state.json
```

## Reading a run

- Each source that didn't update prints a yellow `::warning::` with the reason.
- Stale sources also get a table in the run summary.
- The Strava source logs a line like `Strava PRs: 5 segments, 3 segment PRs, pr_count 1`:
  counts only, no names or places.

## Pages setting

Settings → Pages → Build and deployment → Source must be **GitHub Actions**. With "Deploy from a
branch" the site would serve `main` as-is, which has no `index.html`.

`.nojekyll` tells Pages not to run Jekyll over the files.

## Preview locally

```bash
uv run --python 3.12 python -m homepage
python -m http.server 8000
```

Then open http://localhost:8000. The local build reads and writes your local `data/state.json`
and `assets/live/`. Delete both before committing or running the tests, so you start clean.
Locally there are no Strava secrets, so the activity row comes from `data/activity.toml`.

## Strava

The activity row reads my latest Strava activity through my own Strava API app. What it keeps and
how it picks the activity is in [sources.md](sources.md).

One-time setup:

1. Create an app at https://www.strava.com/settings/api. Website: `https://jvitorcosta.github.io`,
   Authorization Callback Domain: `localhost`.
2. Open this URL (with the app's Client ID) and click Authorize:
   `https://www.strava.com/oauth/authorize?client_id=CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read`
3. The browser lands on a `localhost` page that fails to load. Copy the `code=` value from its address bar.
4. Exchange it for a refresh token:
   ```bash
   curl -X POST https://www.strava.com/oauth/token -d client_id=CLIENT_ID -d client_secret=CLIENT_SECRET -d code=CODE -d grant_type=authorization_code
   ```
5. In the repo: Settings → Secrets and variables → Actions → New repository secret. Add
   `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET` and `STRAVA_REFRESH_TOKEN` (the `refresh_token` from step 4).

Without the secrets, or until Strava first answers, the row comes from `data/activity.toml`.
If Strava stops answering for a week (a revoked app, say), the run turns red like any other source.

## The case pages come from another repo

`projects/*.html`, `projects/images/`, `privacy.html`, `data/jobs.json`, `og-image.png`,
`favicon.svg`, `sitemap.xml` and `robots.txt` are generated in
[curriculum-vitae](https://github.com/jvitorcosta/curriculum-vitae) and copied in, then
committed here through a PR. How to refresh them is in [content.md](content.md).
