# How this site works

Everything about the homepage at https://jvitorcosta.github.io: how it is built, where its data
comes from, how it is published, how to change it, and why it is the way it is.

| Read this | When you want to know |
|---|---|
| [architecture.md](architecture.md) | how one build turns data files and live sources into `index.html`, module by module |
| [sources.md](sources.md) | every outside service the page reads (Spotify, Letterboxd, MyAnimeList, Goodreads, Strava, GitHub): the endpoint, the login, what is kept and how a row is chosen |
| [deploy.md](deploy.md) | the GitHub Actions workflow, the schedule, the `state` branch, Pages, secrets and the stale-source alert |
| [content.md](content.md) | how to edit text, add a favorite tile or a project row, change links, draw an icon, refresh the case pages |
| [design.md](design.md) | the rules behind the look and the copy: layout, palettes, languages, privacy, accessibility, card wording |

Short version:

1. All hand-written text lives in `data/` (TOML and one JSON file).
2. A small Python package, `homepage/`, standard library only, reads that text, asks six outside
   services for what I did lately, downloads their pictures and writes one static `index.html`.
3. A GitHub Actions workflow runs that build every 4 hours and on every push to `main`, and
   publishes the result straight to GitHub Pages.
4. In the visitor's browser, `assets/site.js` handles the palette and language buttons and swaps
   in the song playing right now.

`docs/superpowers/` holds the plans the site was first built from. They are history: where they
disagree with these pages or the code, the code wins.
