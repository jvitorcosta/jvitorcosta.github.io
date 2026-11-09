# Data sources

The page reads six outside services. Each one has a module in `homepage/sources/` with one
function that returns one dataclass (or `None` when there is nothing to show). None of them uses
an SDK: every call is a plain HTTP request through `homepage/http.py`.

What all of them share:

- **Failures never break the page.** A source that raises or returns nothing keeps its last good
  value from `data/state.json` (see [architecture.md](architecture.md)). A source quiet for more
  than 7 days turns the workflow run red, but only once it has worked at least once: a source
  that has never answered has no date to be stale from.
- **Only what the row shows is kept.** Each module copies the handful of fields it needs and drops
  the rest of the answer. Nothing else is stored.
- **No picture is loaded from the services' own servers.** Covers are downloaded into
  `assets/live/` at build time. The Spotify cover is the one exception, explained below.
- **Tests never call the network.** Each source takes a `get` function and the tests pass a fake
  one. `tests/fixtures/` holds saved real answers from Letterboxd, MyAnimeList, Goodreads and
  Strava; the Spotify and GitHub tests use small inline answers.

| Row | Service | Endpoint | Login | Module |
|---|---|---|---|---|
| Song | Spotify, via my own small server | `spotify-now-playing-ashen-two.vercel.app/api/now-playing.json` | none (the server holds the Spotify login) | `spotify.py` |
| Film | Letterboxd | `letterboxd.com/zubu/rss/` | none, public RSS | `letterboxd.py` |
| Anime | MyAnimeList | `myanimelist.net/animelist/yulong17/load.json?status=7&order=5` | none, public list | `myanimelist.py` |
| Book | Goodreads | my public profile page | none | `goodreads.py` |
| Activity | Strava | Strava API v3 | OAuth refresh token, repo secrets | `strava.py` |
| Projects | GitHub | REST API `users/jvitorcosta/repos` | the workflow's `GITHUB_TOKEN` | `github.py` |

## Song: Spotify

Spotify's API needs a user login, which a static page can't hold. So the login lives on a small
Flask server I run on Vercel, [jvitorcosta/spotify-now-playing](https://github.com/jvitorcosta/spotify-now-playing).
Its `/api/now-playing.json` returns:

```json
{"playing": true, "title": "…", "artist": "…", "cover": "https://i.scdn.co/…", "url": "https://open.spotify.com/track/…", "cover_data": "data:image/jpeg;base64,…"}
```

It asks Spotify for the current track, else the most recent one. It also downloads the cover
itself and sends it inline as `cover_data`, so a visitor's browser never contacts Spotify's image
servers. Only `https://jvitorcosta.github.io` may call it from a browser (CORS), and the answer is
cached for 10 seconds. On any error it returns `{"error": "now playing unavailable"}` with
status 503.

The song is read twice:

1. **At build time** by `fetch_song`. That song is always shown as LISTENED, because it is
   hours old by the time anyone reads the page.
2. **In the browser** by `assets/site.js`, once per visit, with a 4-second timeout. Its answer
   replaces the built song (title, artist, cover, link): the current track, else the latest one.
   Only when `playing` is true does the row say LISTENING with the ON badge; otherwise it stays
   LISTENED. If the call fails, the built row stays. With no saved song at all, the row (and the
   Lately box, when it has nothing else) starts hidden and appears only if this call succeeds.

## Film: Letterboxd

The public diary RSS feed of `zubu`. `fetch_film` takes the first item that is a film (lists are
skipped) and keeps: title, year, my rating, whether I liked it, watched date, my review
(dropped when it is only the automatic "Watched on …" line), poster and link. The poster URL is
rewritten to a smaller size (`-0-230-0-345-`). The row shows stars, ♥, the date and the first 70
characters of the review.

## Anime: MyAnimeList

MyAnimeList has an official API, but it needs an app key. The public list page loads its rows
from a JSON address that needs no key, so `fetch_anime` reads that. This is not an official API
and may change; if it does, the source fails, the last anime stays, and after a week the run
turns red.

- `status=7` means the whole list, `order=5` means most recently updated first. The entries are
  also sorted by `updated_at` in code, in case the order ever changes.
- **How the row is picked:** the most recently updated entry in **Watching** (status 1). If
  nothing is in Watching, the most recently updated **Completed** one (status 2). Plan to Watch
  and On Hold are never shown.
- **Watching** shows "ep X of Y" with a progress bar, or just "ep X" while the episode count is
  unknown (still airing).
- **Finished** shows my score (when I gave one) and the date I last updated it, in Manaus time
  (UTC-4).
- The English title is used when the list has one. My list notes are never read into the row.

## Book: Goodreads

Goodreads closed its API, so `fetch_book` reads my public profile page. It takes the first book
under "Currently Reading" and keeps title, author, cover (asked at a larger size, `_SX318_`), link
and "page X of Y" progress when the page shows it.

It tells two kinds of empty apart:

- The profile loaded (its name heading is there) but the currently-reading block is gone: I
  finished the book. It raises `NothingReading`, and the build keeps the last book marked
  FINISHED, without progress.
- The page doesn't look like a profile any more (Goodreads changed it, or sent a login or error
  page): it raises a plain error, so the last value is kept and the alert fires after a week.

This is the most fragile source, because any change to Goodreads' HTML can break it. The
fixtures in `tests/fixtures/goodreads-*.html` are real saved pages.

## Activity: Strava

Read with my own Strava API app (setup in [deploy.md](deploy.md)), scope `activity:read`.

1. Trade the refresh token for an access token (`POST /oauth/token`).
2. List my latest 10 activities (`GET /athlete/activities?per_page=10`).
3. Take the first one that is not private ("only me") and not a car trip saved as a ride. An
   outdoor ride (Ride, MountainBikeRide, GravelRide, EBikeRide; not VirtualRide) counts as a car trip when it averages over 30 km/h or tops 60 km/h; my real bike rides
   are far below that.
4. Fetch that activity on its own (`GET /activities/{id}`) for its PR count, because the list
   always says 0. That answer's `pr_count` was also seen lower than the app's (1 against 3), so
   the build also counts the segment efforts marked as my best (`pr_rank` 1) and shows the
   higher number. Each run logs both counts. If this second request fails, the row still shows,
   just without PRs.

The row shows: sport emoji, title, distance, moving time, pace (runs, walks, hikes) or speed
(everything else with a distance), PR count, date and a **View on Strava** link. Never the map, start or end points, heart
rate or any other health data.

Without the three Strava secrets the source is not used at all, and the row comes from
`data/activity.toml`. The same file is used while Strava has never answered, or answers with no
activity to show.

## Projects: GitHub

`fetch_repos` lists my own repos (`type=owner`), most recently pushed first, up to 100. Forks,
archived and private repos are dropped, and so are `jvitorcosta` (my profile README),
`jvitorcosta.github.io` (this site) and `spotify-now-playing` (the song server). It keeps name,
description, link, homepage and last push date. The workflow passes its own `GITHUB_TOKEN`,
which raises the rate limit; without it the call still works unauthenticated.

An empty list counts as a failure, so the last list stays.

The Favorites tiles and the Projects rows both come from this list (see
[architecture.md](architecture.md)); the text on them comes from `data/`.

## Adding a source

1. A module in `homepage/sources/` with `fetch_x(get=http.get) -> X | None`. It raises on an
   answer it doesn't understand, and returns `None` only when there is truly nothing to show.
2. A frozen dataclass `X` in `homepage/model.py`, with only the fields the row shows, and a field
   for it in `LiveData`.
3. A saved real answer in `tests/fixtures/` and a `tests/test_x.py`.
4. An entry in `build.default_sources`, a `refresh("x", …)` line in `build.build`, and a
   `local(...)` call for its picture. A source that returns a list must turn an empty list into
   `None` (as `repos` does with `or None`), or an empty answer would overwrite good state.
5. A row function in `homepage/right_now.py`, added to the list of rows in `right_now()`, its labels in both tables of `data/strings.toml`,
   the profile link in `data/links.toml`, a 20×20 icon in `tools/pixel_icons.py` with its brand
   colour in `markup.PLATFORMS`, and its name in the footer string.
