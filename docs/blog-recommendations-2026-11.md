# A blog on the site: references and recommendations (November 2026)

A list only, to decide the plan from. Nothing is built. The idea: one post for each feature or project that ships in the repositories, starting with the Volley Score app for the Garmin Forerunner 255.

## 1. What other dev blogs do (pages opened this session)

| Blog | Format | Worth copying |
|---|---|---|
| [Julia Evans, blogging principles](https://jvns.ca/blog/2017/03/20/blogging-principles/) and [blog about what you've struggled with](https://jvns.ca/blog/2021/05/24/blog-about-what-you-ve-struggled-with/) | Short, personal posts, many under 500 words | Write for your past self, from your own experience, soon after, about what the struggle taught you. A good checklist for the voice. |
| [Simon Willison, TIL](https://til.simonwillison.net) and [link blog guide](https://simonwillison.net/2024/Dec/22/link-blog/) | Tiny notes: one problem, a snippet, a few lines | A topic tag on each note; credit the source and add one takeaway. |
| [Brandur, Fragments](https://brandur.org/fragments) | A separate lane for "notes that don't merit a write-up", with its own feed | A low-pressure short lane next to the long posts, listed as title, date, link. |
| [Dan Abramov, overreacted](https://overreacted.io/) | Essays and project announcements | Plain title, one-line tagline, date on its own line. |
| [Josh Comeau](https://www.joshwcomeau.com/blog/) | Long interactive tutorials, "how I built X" | The "how I built X" framing with a year label suits project posts. |
| [Amos, fasterthanli.me](https://fasterthanli.me/articles) | Long deep dives, a yearly recap | Reading time on every listing; a year-end recap post. |
| [Sam Hartley, Garmin watch face build log (dev.to)](https://dev.to/samhartley_dev/i-built-a-custom-garmin-watch-face-with-live-stock-sparklines-heres-what-i-learned-129n) | Build log with lessons, 900 to 1,000 words | The closest model for the Garmin post: a short story to open, one heading per technical problem ("The font problem that cost me a week"), a list of gotchas, the end result, a link to the source. |

Also seen but not opened: Garmin Connect IQ forum showcase posts (a place to cross-post), and a Hacker's Diet watch app write-up (the page failed to load).

## 2. Guidance from primary sources

- **Dates** ([Google](https://developers.google.com/search/docs/appearance/publication-dates)): show a visible, labelled date, with "Updated" when it changes, and match it in `BlogPosting` structured data (`datePublished`, `dateModified`).
- **Titles** ([Google](https://developers.google.com/search/docs/appearance/title-link)): a unique, concise `<title>` per post, the first `<h1>` is the post title, the page's own language.
- **Canonical** ([Google](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)): an absolute self-referencing canonical on each post.
- **Two languages** ([Google](https://developers.google.com/search/docs/specialty/international/localized-versions)): one URL per language with reciprocal `hreflang` links, `x-default`, and a language switch that is a plain link to the other URL. This differs from the site today, where one URL switches language with a script.
- **Share previews** ([Open Graph](https://ogp.me/)): `og:type` article, `og:image` with alt text, `article:published_time`, `og:locale` and `og:locale:alternate`. One generated pixel-style image per post would fit.
- **Images** ([W3C](https://www.w3.org/WAI/tutorials/images/decision-tree/)): a short description for an informative image, empty `alt` for a decorative one; for a demo GIF, describe what changes.
- **Feeds:** no primary source found this session; Brandur and Simon Willison both publish Atom feeds. Practical: an Atom feed, autodiscovery `<link rel="alternate" type="application/atom+xml">`, the permalink as the entry id.

## 3. Post templates for "a new feature in my repo"

1. **Ship note**, 150 to 300 words: what changed, a screenshot or GIF, why, a link to the PR, a "try it" link.
2. **What and why**, 400 to 700 words: the problem, the constraint, the choice, the result with a demo, "what I would do differently".
3. **Build log**, 600 to 1,000 words (the Hartley model): a short opening story, one heading per problem, a gotchas list, the end result, a source link.
4. **How it works**, 800 to 1,500 words: a diagram or demo first, then a walkthrough with code and commentary.
5. **TIL or fragment**, 50 to 200 words: one problem, one snippet, one takeaway, a tag.
6. **Postmortem or "bug I hit"**, 300 to 600 words: symptom, wrong guesses, root cause, fix.

## 4. Recommendations

**Format.** Two lanes, like Brandur: **posts** (templates 2, 3 and 4, about one a month at most) and **fragments** (templates 1, 5 and 6, as short as you like, one per shipped feature). That keeps "one post per feature" cheap: most features get a fragment, the interesting ones get a full post.

**First post: Volley Score** (repo `garmin-watchfaces`, PRs 6 to 10). Use template 3, a build log, about 800 words, with the screenshots already in `docs/images` (simulator, menu, wheel, tie-break, winner screen). Material the repo already holds:
- Why: a scoreboard you can run with the watch's own buttons in a beach volleyball game, saved when the watch sleeps.
- Problems worth a heading each: the match as a list of events that is replayed (so undo is just dropping the last event); the tie-break rules (win by 2, sudden death, max +1, max +2) and the once-per-match question; a roulette selector on three buttons; drawing a split screen that fills as points come; the pixel icon; unit tests in the simulator.
- Gotchas list from the simulator versus the real watch (buttons and haptics were only tested on the simulator at first; check this before writing).
- End: the repo link and how to sideload. The app is **not** on the Connect IQ Store (sideload only), so there is no store link.

**Where posts live.** Three options:
- **A. In this repo, written as small markdown files**, built by the existing generator. The generator has no libraries today, so it needs a tiny markdown converter limited to headings, paragraphs, lists, links, images, code and quotes. Fewest moving parts; the post lives next to the site.
- **B. In curriculum-vitae, like the case studies**, which already renders markdown with a library and handles pt files. The cost: every post needs a commit in two repos and a copy step that publishes.
- **C. Hand-written HTML per post.** No converter, but easy to drift from the site style.
My pick is **A**.

**Languages.** The cheapest path is to write posts in English first, with a Portuguese translation file when João wants one, and to give each language its own URL (`/blog/volley-score.html` and `/pt/blog/volley-score.html`) with `hreflang`. That is the guidance above and the only way Portuguese posts can be found in search. A post without a translation is shown in English on both.

**Pieces to build, in order:**
1. The post page: title, date (and "Updated"), reading time, tags, the same pixel boxes, both palettes, code blocks, images with alt text, a link back.
2. The blog index (`/blog/`): posts and fragments in two lists, newest first.
3. An Atom feed with autodiscovery.
4. A "Latest post" row on the home page and a BLOG button in the top bar.
5. Open Graph tags and a generated pixel-style image per post.
6. `BlogPosting` structured data and the sitemap entries.
7. Optional: tags pages, a year-end recap.

**Voice.** Plain and first person, as in the resume rules ("I built", with "we" only for team work). Julia Evans's principles are a good checklist: write for past you, say what you know honestly, stay positive.

**Decisions needed from João:** (1) one lane or two; (2) where posts live (A, B or C); (3) one URL per language or the current toggle; (4) whether the first post is English only or both; (5) whether to check the real-watch behaviour before the Volley Score post is written.
