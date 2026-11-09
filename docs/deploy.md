# How the site is published

`.github/workflows/update-home.yml` runs every 4 hours (01:00, 05:00, 09:00, 13:00, 17:00 and 21:00 Manaus time), on every push to `main`, and on demand (`gh workflow run update-home.yml`).

1. **build** checks out `main`, restores what earlier runs remembered from the `state` branch, runs `python -m homepage`, saves the new state back to `state`, and uploads the whole folder as a Pages artifact.
2. **deploy** publishes that artifact to GitHub Pages.

## Why a `state` branch

`main` is protected by the `protect-main` ruleset: changes only arrive through pull requests. The daily job can't push there, so it keeps its memory somewhere it can push:

- `data/state.json`, the last good value of every source, used when a source is down.
- `assets/live/`, the covers and posters downloaded for the current page.

The `state` branch holds only those files. Deleting it is safe: the next run starts from empty state and creates it again. If the branch exists but cannot be fetched, the run fails instead of deploying a page built from empty state.

## What is not in git any more

`index.html`, `data/state.json` and `assets/live/` are built, not committed. They are listed in `.gitignore`.

## Preview locally

```bash
uv run --python 3.12 python -m homepage
python -m http.server 8000
```

Then open http://localhost:8000. The local build starts from your local `data/state.json`, if you have one.

## Pages setting

Settings → Pages → Build and deployment → Source must be **GitHub Actions**. With "Deploy from a branch" the site would serve `main` as-is, which has no `index.html`.

## Strava

The activity row reads my latest Strava activity through my own Strava API app. It keeps only the
sport, title, distance, moving time, speed or pace, PR count, date and link: never the map,
start/end points, heart rate or other health data. Private ("only me") activities are skipped.

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
