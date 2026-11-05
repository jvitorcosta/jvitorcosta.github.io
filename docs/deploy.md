# How the site is published

`.github/workflows/update-home.yml` runs every day at 05:00 Manaus time, on every push to `main`, and on demand (`gh workflow run update-home.yml`).

1. **build** checks out `main`, restores what earlier runs remembered from the `state` branch, runs `python -m homepage`, saves the new state back to `state`, and uploads the whole folder as a Pages artifact.
2. **deploy** publishes that artifact to GitHub Pages.

## Why a `state` branch

`main` is protected by the `protect-main` ruleset: changes only arrive through pull requests. The daily job can't push there, so it keeps its memory somewhere it can push:

- `data/state.json`, the last good value of every source, used when a source is down.
- `assets/live/`, the covers and posters downloaded for the current page.

The `state` branch holds only those files. Deleting it is safe: the next run starts from empty state and rebuilds it.

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
