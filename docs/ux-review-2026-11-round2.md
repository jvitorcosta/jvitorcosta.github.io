# UX and front-end review, round 2 (November 2026)

A list only. Nothing here is built. Each item has a size (S under an hour, M a few hours, L a day or more) and a call for João: do it, skip it, or later. The first review is `ux-review-2026-11.md`; its icons, expandable roles, study map, skip link and tap targets have shipped (PRs 54 to 58).

## 1. What the site is trying to be

The intent in `docs/design.md`: a Game Boy menu / Pokémon trainer card. The page says who João is, shows what he is into right now (music, films, anime, books, runs), links to a few projects and a resume, and keeps a pixel-nerd personality without hiding the facts. Two light palettes (Nu Purple, Red Lantern), English and Portuguese, no framework, one small CSS file and one small script.

It mostly does that. The weight is low (page 57 KB, CSS 23 KB, JS 8 KB, fonts 180 KB), every pair of colours is tested for contrast, motion respects the reduced-motion setting, and the content is reachable without learning any interface. The theme is the container, not the way in.

## 2. What other personal sites do (sources opened this session)

- Game and desktop portfolios: [matteosantoro.dev](https://matteosantoro.dev/) (Game Boy frame as navigation), [mitchivin.com](https://mitchivin.com/) (Windows XP, hidden easter eggs), [joeyderuiter.me](https://joeyderuiter.me/) (desktop with a DOS window), [terminal.satnaing.dev](https://terminal.satnaing.dev/) (type `help`), [win95-portfolio](https://win95-portfolio-green.vercel.app/) (each section is a window). The pattern: the metaphor works best when plain content stays one click away. João's site already follows that; the heavy ones make a recruiter dig.
- Curated lists: [Brutalist Websites](https://brutalistwebsites.com), [IndieWeb 88x31 buttons](https://indieweb.org/88x31).
- Guidance: [web.dev on motion](https://web.dev/learn/accessibility/motion), [US design system language toggle](https://designsystem.digital.gov/patterns/select-a-language/two-languages/), [language switcher spec](https://specification.website/spec/i18n/language-switcher/), [favicon set](https://evilmartians.com/chronicles/how-to-favicon-in-six-files-that-fit-most-needs), [performance budgets](https://web.dev/articles/performance-budgets-101), and a vendor blog on [what recruiters scan first](https://www.fueler.io/blog/your-portfolio-has-7-seconds-what-recruiters-look-at-first) (soft evidence).
- Claims about pixel-font sizes, share-image size and WCAG tap-target numbers are from general practice, not from a page opened here.

Shared patterns: say who you are and what you do in plain words on the first screen; show a contact above the fold; keep easter eggs on top of ordinary content; make motion optional; label the language switch in its own words and mark the current one; keep the pixel font for display text and give body text a readable font; small self-hosted pages with a real share image.

## 3. Section by section

**Top bar (palette dots, EN/PT).** Works. The dots have no visible name; the names (Red Lantern, Nu Purple) live only in the tooltip and the screen-reader label. The language button reads "EN > PT", which shows the target, not the current language.

**Trainer card.** Name, role, city, Chinese name, Spanish motto, tagline, four contact buttons. Strong and personal. Notes: the first screen says "Software engineer" but not the specialty (AI/ML), which is what the experience section sells. The tagline now sits under a motto about slow fire ("Dios me prepara a fuego lento") while the new line says "There is no tomorrow", so patience and urgency sit together. It may be intended as a contrast; that is João's call. The pt line I wrote is "Não existe amanhã."

**Favorites.** Four cards with photo, tag and one line each. Good: concrete and visual. The card art is cropped small; the wrist and city cards depend on a 278 KB radar-map SVG.

**Experience.** Roles now open to the resume bullets. Good. Risks: Nubank holds 17 bullets in four groups, which is a wall of text once open; the bullets are English-only on the Portuguese page; the hint "Tap a role…" is shown on desktop, where it should say "Click". No role is open by default, so a visitor sees only titles on first load.

**Studying now.** Tree map plus the list. Good idea and it fits the theme. Risks: the nine squares are about 35×42 px (passes WCAG AA, below 44); the map is an SVG with text in it, so it scales down with the screen and the labels get small on a phone; the "NOW" marker and the percentages need a legend the first time.

**Lately (Spotify, Letterboxd, MyAnimeList, Goodreads, Strava).** Live rows with cached cover art. Fun and shows the person. Risks: five outside services mean five ways to look stale or broken; there is no visible "updated" time, so a visitor cannot tell a week-old row from a live one; the rows read as content, not as a link, so it is not obvious which are clickable.

**Projects and case pages.** Clear. The case pages reuse the same CSS and palette. Risk: they have the same hand-kept CSS and JS hashes as the home page, so every style change needs a manual update (a test catches it).

**Footer and privacy page.** Fine. No print layout for the resume case, and no "last updated" date.

## 4. Front-end and best practice

What is good: semantic landmarks (header, main, nav, footer), one `h1`, skip link, native `details` for open/close, `aria-pressed` on the palette dots, `lang` on switched text, reduced-motion rule, canonical and Open Graph tags, a share image, SVG favicon plus Apple touch icon, cache-busting hashes, no third-party scripts, tests for contrast.

Gaps worth knowing:

1. Smallest text is 10 px in the pixel font (four places). Pixel fonts read best at their native size multiple and at 12 px or more.
2. No `theme-color` meta, so the phone browser bar does not follow the palette.
3. Only an SVG favicon. Older browsers and some link scanners want a 32 px `.ico` as well.
4. The Portuguese page is the same URL, switched by script. Search engines and shared links see English only; the `description` and the Open Graph text are English-only. `hreflang` pages would fix it but cost a second build.
5. No print stylesheet.
6. The infinite "bars" animation and the blinking cursor are covered by the reduced-motion rule, but the page offers no on-page pause control (web.dev suggests one when motion loops).
7. Fonts: two Inter files plus Press Start 2P (180 KB). Not preloaded, so the first paint can show a fallback font briefly.
8. `site.js` resets the palette on load; with a stored choice there is a short flash prevented only by an inline script. Worth a check on a slow phone.

## 5. Things João may want (all optional)

| # | Idea | Size | Why |
|---|---|---|---|
| 1 | Add a plain line under the tagline or the role: "AI/ML engineer" (no new claims, the resume says it) | S | The first screen says what you do, the way recruiter guidance asks |
| 2 | Open the Qubika role by default, or show the first two bullets of each role before the click | S | Visitors see proof without a click |
| 3 | Group the Nubank bullets as four small collapsible groups, or show the top two of each group | M | A 17-bullet wall is hard to scan |
| 4 | Say "Click" on desktop and "Tap" on touch for the hint (CSS `hover` media query) | S | Small polish |
| 5 | Show the palette name next to the dots, or on hover and focus | S | The two themes have names João uses himself |
| 6 | Language button shows both options with the current one marked ("EN / PT" with `aria-current`) | S | Standard pattern in the guidance above |
| 7 | Raise the 10 px pixel text to 12 px | S | Readability |
| 8 | Study-map squares to 44 px, or a bigger gap | M | Meets the tap-target target |
| 9 | Show "updated 2 h ago" on each Lately row | M | Honest about staleness |
| 10 | Portuguese bullets for the experience (needs João's own wording; no machine rewrite of claims) | L | Pt page is half English today |
| 11 | `theme-color` meta that follows the palette | S | Phone bar matches |
| 12 | Add `favicon.ico` 32 px | S | Older browsers and scanners |
| 13 | Preload the pixel font and the main Inter file | S | Less font flash |
| 14 | Shrink the 278 KB radar-map SVG | M | Smaller first load on mobile data |
| 15 | Print stylesheet so the page prints as a one-page resume | M | Some recruiters print |
| 16 | A tiny easter egg on top of the content (for example the Konami code swaps the avatar) | M | Matches the retro-site pattern, no effect on content |
| 17 | An 88x31 badge of your own, hosted on the site | S | IndieWeb tradition, fits pixel taste |
| 18 | Separate `/pt/` page with `hreflang` | L | Search and shared links in Portuguese |
| 19 | `curriculum-vitae` generator writes `data/experience.json` so the site follows the resume by itself | M | Removes the hand-kept copy |
| 20 | Stale line in `ux-review-2026-11.md` about the study section | S | Docs only |

My own order if it were mine: 1, 5, 6, 7, 11, 2, 4, then 19. Skip 18 and 16 unless the idea appeals.

## 6. Changes already made in this round (separate from the list)

- Tagline now "There is no tomorrow." (pt: "Não existe amanhã.").
- The portrait is transparent, so its background follows the palette: red in Red Lantern, purple in Nu Purple. The tab icon, home-screen icon and share image keep the purple version.
