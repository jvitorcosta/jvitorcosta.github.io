# Design rules and decisions

Why the page looks and reads the way it does. When a change would break one of these, change the
rule here first, on purpose.

## Who it's for

Friends who arrive from Instagram, and recruiters who arrive from LinkedIn or my resume. Both
should get, in a few seconds: who I am, what I build, and that I'm a real person with a life.
So the page leads with me and my projects, and the live rows make it feel current.

## Look

- **A handheld game menu.** Boxes with thick borders, a pixel font for headings and labels
  (Press Start 2P), a readable font for everything else (Inter), pixel-art icons. The sections
  borrow game names in spirit (trainer card, favorites, a progress bar like an HP bar).
- **Fonts are self-hosted** in `assets/fonts/` (both under the SIL Open Font License), so a
  visit makes no request to Google. The pixel font has no Chinese glyphs, so Chinese text uses
  the system CJK font.
- **Two palettes:** Red Lantern (`night` in the code, dark, the default: lacquer-red boxes with
  gold borders and yellow links on an imperial-red page, to go with the Chinese name and
  subtitles; it replaced the purple-grey Night Menu and kept its code name so saved choices and
  the case pages still work) and Nu Purple (`nu`, the default
  for systems in light mode). A white palette existed and was removed: the purple one already
  covers light mode, and fewer palettes means fewer colours to keep accessible.
- **Section headings** are 16px pixel caps with a ▶ before them and a Chinese subtitle after,
  matching the Chinese name on the trainer card: FAVORITES 最爱, LATELY 最近, PROJECTS 项目,
  EXPERIENCE 经历. Chinese only, no Japanese.

## Layout

- **Phones (under 900px):** one column, in this order: trainer card, Favorites, Lately, Projects,
  Experience. Who I am and what I build come before what I did lately.
- **Wide screens (900px and up):** two columns, at most 1000px wide. Left: trainer card,
  Favorites, Experience. Right: Lately, Projects. Nothing is pinned while scrolling.
- The code writes sections in the wide-screen order, and CSS `order` moves Experience last on
  phones. So on phones, screen readers and the keyboard reach Experience before Lately. That is
  accepted because the sections don't depend on each other.
- Projects shows 5 rows so the right column ends about level with the left on a laptop.
- Favorites is a 2×2 grid of 4 tiles. A fifth project goes to Projects, not to a lonely tile.

## Languages

English and Portuguese (Brazil), both in the page, switched without a reload (see
[architecture.md](architecture.md#both-languages-in-one-page)). Portuguese reads as written by a
Brazilian, not translated word for word. The motto stays in Spanish in both. The Chinese name and
subtitles are decoration with real meaning, not a third language.

## What the page shows, and what it never shows

- **Side projects only.** Work for employers appears in Experience as title, company and dates,
  nothing more: no work projects, no impact lines, no resume PDF button.
- **Never claim what the repo doesn't back up.** A tile or row says what the project really does
  today, not what it's meant to do one day.
- **Coursework sorts last** in Projects, so it never pushes my own projects under "+ n more".
- **No tracking, no cookies, no analytics.** `localStorage` keeps only the palette and language.
- **No picture from a third-party server.** Covers are downloaded at build time; the Spotify
  cover arrives inline from my own server. A visit loads files from this site, plus one call to
  my Spotify server.
- **No maps, no places, no health data.** The Strava row has no route, start or end point, heart
  rate or calories. Private activities are skipped. Car trips logged as rides are skipped.
- **Anime:** never Plan to Watch or On Hold, never my list notes.
- **Strava's wording:** the link always reads "View on Strava", in both languages. That's
  Strava's brand rule for apps using its data. It's bold, in Strava orange where the contrast
  allows, else in a darker orange with an underline.

## Card and row wording

For a Favorites blurb or a Projects line:

1. **Say what it is**, with a real term (an optimization solver, a cyberdeck, an open map), then
   **what it lets you do**, in short verbs.
2. **Plain words** a friend gets without being an engineer; no stack names.
3. **Cosmetic details stay out of front** (the Pokémon theme of the watch faces is not the
   point).
4. **Only true things:** the cyberdeck shows the music but doesn't control playback; Open
   Radars has the cameras I checked in person; a prototype is called one.
5. **Short:** a Projects line is cut at 60 characters, a blurb should fit two lines on a phone.
6. Write both languages; the Portuguese should sound natural, not translated.

## Accessibility

- Every palette passes WCAG AA: 4.5:1 for text (accent links included), 3:1 for button borders.
  `tests/test_assets.py` checks the actual CSS values.
- Pixel-font labels are at least 10px.
- Tap targets: palette dots are 26px circles in 44px targets; small text links are at least
  24px tall.
- Decorative glyphs (▶, stars, ♥, emoji) are `aria-hidden`, and the stars and heart have a
  screen-reader text ("3.5 stars, liked").
- Section headings are real `<h2>`s; the footer is outside `<main>`, as the page's
  `contentinfo` landmark.
- Movement (the music bars, the blinking cursor) stops under `prefers-reduced-motion`.

## Robustness

- **The page never goes blank.** Each source keeps its last good value; a broken data file skips
  its row instead of failing the build.
- **Loud only when it matters.** One bad run is a warning; a source quiet for a week fails the
  run and sends an email.
- **No dependencies at run time.** The standard library only, so nothing upstream can break the
  build.
- **Same input, same bytes.** Two builds from the same data give an identical page, which keeps
  the `state` branch quiet.
