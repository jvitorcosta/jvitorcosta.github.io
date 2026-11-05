# Personal homepage redesign

Date: 2026-11-05. Status: draft, waiting for Vitor's approval.
Mockup of the chosen direction: [2026-11-05-homepage-mockup.html](2026-11-05-homepage-mockup.html)
(open it in a browser; the palette dots at the top switch colours).

## Intent

Today jvitorcosta.github.io reads like a resume: headline, skills, three case studies, job list, and
"Outside work" at the bottom. Vitor wants it the other way round. The site should show who he is
first (what he listens to, watches, reads and does for exercise, and the things he builds for his
own life) and his job second.

It will be the link in his Instagram bio, so most visitors are friends on a phone who are not
technical. If someone who has never heard of an ESP32 scrolls for 30 seconds, they should come away
knowing what Vitor does for a living (one line), what he's into, and that he builds real things he
uses every day. Curious or technical visitors can click into any project for the detail.

## Goals

- A phone-first homepage that feels personal and fun, not corporate.
- **Right now**: four live items at the top, the first thing anyone sees:
  1. 🎵 Spotify: what he's listening to now, or last.
  2. 🎬 Letterboxd: the last film he logged.
  3. 📚 Goodreads: what he's reading, with progress.
  4. 🏃 Strava: his last activity (see the Strava constraint below).
- **My party**: the hobby projects he picks, told as stories with pictures in plain words.
- **PC box**: every other public repo, automatically.
- **Work** kept, short and at the end.
- **English and Portuguese**, with a switch.
- **Three colour palettes** the visitor can switch between.
- Refreshes itself with no manual work, like his GitHub profile does now.

## Non-goals

- No blog, comments, contact form, analytics or tracking.
- No rewrite of the content of the existing case studies (Car Cyberdeck, SolvedOR,
  resume-as-code). They get the new look (see "How it's built") but keep their words.
- No change to how the GitHub profile README looks. It keeps its own Spotify and Letterboxd cards.

## Anti-goals (a failure even if it works)

- **Revealing where he lives.** No maps, routes, start or end points, or anything that pinpoints an
  activity. No heart rate or other health data.
- **Breaking a platform's terms**, Strava's in particular (below).
- Jargon above the fold. A friend should not hit "firmware", "CAN bus" or "BLE" before the project
  pages.
- Looking like a generic developer-portfolio template.
- A broken page when one source is down. Each item shows its last known value; never an error or an
  empty box.
- Anything from the private resume repo beyond what's already public (name, email, links, headline,
  job titles and dates, case studies). Never the phone number.

## Look: Game Boy menu, three palettes

Vitor chose the game-menu direction from the mockups (handheld-console menu boxes, chunky borders
with a hard shadow, pixel font for headings only, normal font for everything people read).

- **Palettes** (visitor switches with three colour dots at the top; the choice is remembered):
  - **Pocket**: off-white boxes, navy ink, red and green accents, on a warm grey background.
  - **Night Menu**: dark boxes on near-black, Letterboxd orange and green as accents.
  - **Nu Purple**: background `#820AD1`, light lilac-white boxes, deep purple ink, amber accent.
  - Exact values are in the mockup; the builder may tune them for contrast. *Builder's call:* the
    first visit follows the phone's light/dark setting (Pocket for light, Night Menu for dark).
- Sections, top to bottom, named like a game menu:
  1. **Trainer card**: avatar, "VITOR", one friendly line ("AI engineer from Manaus. I build
     gadgets for my car, my watch and my city."), buttons for Instagram, GitHub, LinkedIn, Email.
  2. **▶ RIGHT NOW**: the four live items as rows (thumbnail, small label, title, one detail line).
  3. **▶ MY PARTY**: chosen projects as tiles in a two-column grid (picture, a small tag like DAILY /
     WRIST / CITY, name, one plain sentence).
  4. **▶ PC BOX**: every other repo as a list (name, a few plain words, "try it" when there's a live
     demo), with "all on GitHub ›".
  5. **▶ WORK**: one sentence ("5 years building AI for banks and fintech"), the companies, and a
     LinkedIn link.
  6. Footer: "Powered by Strava", data credits, "refreshed every day".
- Must pass WCAG AA contrast in all three palettes, tap targets at least 44px, and work at 360px
  wide. Pixel font never for body text. Respect `prefers-reduced-motion` (the blinking cursor and
  the music bars stop).

## Right now: the four items

Every row is a link to the item itself (the song, the film, the book, the activity), and a round
brand-coloured icon at the end of the row links to **his profile** on that platform.

| Item | Source | Shows | Profile link |
|---|---|---|---|
| Spotify | His fork `jvitorcosta/spotify-now-playing` (Vercel, `spotify-now-playing-ashen-two.vercel.app`). Add a small JSON endpoint next to the SVG one. | Cover, song, artist, an "ON" badge while playing, "Last played" otherwise. | His Spotify profile (Vitor to provide the URL). |
| Letterboxd | RSS `https://letterboxd.com/zubu/rss/`, same parsing as `jvitorcosta/jvitorcosta` `scripts/letterboxd_card.py`. | Poster, title (year), stars, ♥, watched date, start of the review. | letterboxd.com/zubu |
| Goodreads | Public profile page `https://www.goodreads.com/user/show/185113793-vitor-pinheiro` (shelf pages and shelf RSS need sign-in or a private key). | "Currently reading": cover, title, author, page X of Y as an HP-style bar. If nothing is being read, the last book finished with his rating. | that profile |
| Strava | See the constraint below. | Sport emoji, activity title, distance, moving time, speed or pace, PRs, date. Activities without distance (weights, boxing) show duration instead. No map. | his Strava athlete page |

### Spotify: new endpoint in the fork (decided)

- Add `GET /api/now-playing.json` (name is the builder's call) to the fork, returning song, artist,
  album cover URL, song URL, and whether it's playing now. CORS open to `https://jvitorcosta.github.io`.
- The site fetches it on page load and draws its own row in the page's style. If the call fails,
  show the last value saved by the daily job.
- The existing SVG endpoint and the GitHub profile card stay exactly as they are.
- The fork's Spotify credentials already live in Vercel. Nothing new for Vitor to set up beyond
  approving the fork change.

### Strava: terms constraint (needs a check before building)

Vitor wants the Strava item. Strava's API Agreement (updated November 2024) says apps may only show
a user's Strava data **to that user**, so a public page fed from the Strava API, even of his own
activities, appears to break the terms. The builder must, in this order:

1. Read the current Strava API Agreement and brand guidelines and confirm the rule.
2. If it holds, use a source that's allowed: Strava's own official embeds or widgets (shared from
   strava.com), styled or framed to fit the row as far as they allow. Check that they don't show a
   map, or that his privacy zones hide home.
3. If no allowed source fits, fall back to a row Vitor updates by hand (a small data file) with a link
   to his Strava profile, and tell Vitor.
4. Never ship an API-fed public Strava item without Vitor's explicit OK after he's seen the terms.

Only activities visible to "Everyone" count. **Car drives must never show**: his radar-laps routine
logs drives on Strava, so exclude driving and other motor activity types.

**Finding (2026-11-05).** Confirmed. The API Agreement (https://www.strava.com/legal/api, read
2026-11-05, page shows effective date June 1, 2026) limits Strava Data shown in an app to the user it
belongs to, and sharing it with others needs that user's explicit consent. So an API-fed public row is out.
The rule covers data obtained through the API; a row Vitor types by hand is his own content and not
"Strava Data", so `data/activity.toml` is fine (the pages don't say this outright; it's our reading).
Brand Guidelines (https://developers.strava.com/guidelines/): a link back to original Strava data must read
"View on Strava" (readable, bold/underlined or #FC5200); don't imply Strava sponsors the page; plain-text
mentions of Strava are fine. The guidelines don't mention profile links specifically.
Official embeds exist (https://support.strava.com/hc/articles/216918527): activity embeds (profile and
activity both "Everyone"), and profile cards (recent activities list or last-week summary, by default
sport type). The help pages don't say whether activity embeds show a map, and third-party plugin pages
say they show the full map, so assume yes; they also don't address personal-site use.
**Recommendation:** keep the manual row plus a "View on Strava" link to his profile. Use the profile
card embed only if Vitor wants it live and accepts its look; skip activity embeds (map risk near home).

## My party and PC box

- **My party** is chosen by Vitor in one short list file in the site repo (repo name, tag, picture,
  one sentence in EN and PT). Up to 6. Starting list: Car Cyberdeck (DAILY), Garmin watch faces
  (WRIST), Open Radars Manaus (CITY), Haylou faces (WRIST).
- **PC box**: every public, non-fork, non-archived repo under `jvitorcosta` not in the party, except
  `jvitorcosta` (profile), `jvitorcosta.github.io` (this site) and `spotify-now-playing` (a fork
  anyway). Pulled from the GitHub API daily, newest push first. Repos with a case study link to
  `projects/<slug>.html`; others to GitHub, plus the live demo when there is one.
- Pictures: car-cyberdeck has no real photo yet, Open Radars and car-can-lab have none. The builder
  asks Vitor for photos (the Cyberdeck in the car, a screenshot of the radar map) and uses a clean
  emoji or illustrated tile until then, as in the mockup.

## Languages

- English and Portuguese (Brazil). The first visit picks the browser language; the EN ▸PT button
  switches and is remembered.
- Hand-written text (trainer card, party sentences, section labels, work line) exists in both
  languages. Vitor reviews the Portuguese. GitHub repo descriptions stay as written there; the PC
  box's few plain words are hand-written in both languages for the repos shown, falling back to the
  GitHub description.

## How it's built

- Static GitHub Pages site, plain HTML/CSS and a little JavaScript (palette and language switches,
  the live Spotify fetch). No framework unless the builder has a strong reason.
- **The site repo owns the homepage.** A build script in `jvitorcosta.github.io` (Python, uv inline
  script, like the profile repo's scripts) renders the homepage from templates plus fetched data
  (Letterboxd, Goodreads, GitHub repos, last Spotify value, Strava as allowed), saves posters and
  covers into the repo, and a daily GitHub Actions workflow runs it and commits the result. Actions
  pinned to SHAs, least-privilege token, a failing source keeps its last value and never fails the
  job.
- **The private resume repo keeps owning the case studies and job list.** Today
  `curriculum-vitae/cv/site.py` writes the whole site, `index.html` included. After this change it
  stops writing `index.html`, exports the public job list as a data file the homepage reads, and
  renders the case-study pages with the new look (shared stylesheet, palette and language switch).
  Publishing to the site stays Vitor's call, as that repo's rules say.
- Existing URLs keep working: `/`, `/projects/*.html`, `/privacy.html` (on the unmerged
  `add-privacy-page` branch), the `cardeck` redirect, sitemap and robots.

## Decided on Vitor's behalf (he accepted these suggestions)

- **Resume link**: points to LinkedIn. No PDF on the site (he took the public PDF down on
  2026-10-23).
- **Project pages**: get the new look, content unchanged.
- **Link preview** (title, og tags, WhatsApp/Instagram card): personal, but says what he does, e.g.
  "Vitor Pinheiro · AI engineer in Manaus who builds gadgets for his car, watch and city", in the
  page's language. Keep the Person JSON-LD.

## Still needed from Vitor

- Instagram handle and Spotify profile URL, for the links.
- Photos for the party tiles that have none (whenever he has them; tiles work without them).
- The Strava decision once the terms are checked (above).

## Left to the builder

- Exact spacing, type sizes and colour tuning within the chosen look.
- Template approach and file layout of the build script.
- How the palette and language switches work technically.
- JSON endpoint name and shape in the Spotify fork.
- How repo pictures are picked for the PC box (if any).
