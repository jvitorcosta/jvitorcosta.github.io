# Blog plan (November 2026)

From the recommendations in `blog-recommendations-2026-11.md` and João's answers. Nothing is built yet; each step below is its own PR, one at a time, and João merges each.

## Decided

- **Where posts live:** in this repo, as small markdown files, built by the existing generator (`homepage/`). The generator has no libraries, so it gets a tiny markdown converter.
- **Language:** English only. No Portuguese translations and no second URL per language. (This settles the `hreflang` question: not needed.)

## Assumed (cheap to change, say so if wrong)

- **Two lanes:** *posts* (build logs, how-it-works, what-and-why) and *fragments* (short notes, one per shipped feature). Both use the same file format; the front matter says which lane.
- **The watch check comes before the first post is published**, not before it is drafted: João tries the buttons and haptics of Volley Score on the real watch and the post says what he saw.

## What a post is

A file `blog/posts/<slug>.md` with a small header, then the body in markdown:

```
---
title: Building a volleyball scoreboard for my watch
date: 2026-11-26
updated: 2026-11-27        # optional, shown as "Updated"
lane: post                 # or fragment
tags: [garmin, monkey-c]
summary: One sentence for the list, the feed and the share preview.
cover: images/volleyscore-sim.png      # optional
cover_alt: The scoreboard on the watch simulator, split blue and red.
---
```

The converter handles only what the posts need: headings (`##`, `###`), paragraphs, bullet and numbered lists, links, images (with alt text and an optional caption), fenced code with a language label, block quotes, inline code, bold and italic. Raw HTML is not allowed; everything is escaped. A post that uses something outside that list fails the build with the file and line, so mistakes show up before publishing.

Output: `blog/<slug>.html`, in the same pixel boxes and both palettes as the rest of the site. The body is marked `lang="en-US"` so it shows on the Portuguese page too (as the resume bullets do); the navigation, labels and footer stay bilingual.

## Steps (each one a PR)

1. **The post page.** The converter, the post template (title, date and "Updated", reading time, tags, cover, code blocks with a copy-free plain style, a link back to the blog), a sample post used only by tests, and tests for the converter (every construct, escaping, a bad file). Self-referencing canonical, a unique title, `og:type` article with `article:published_time`.
2. **The index and the feed.** `blog/index.html` with the two lanes, newest first, with date, reading time and summary; `blog/feed.xml` (Atom, permalink as the entry id, autodiscovery link in the head of every page that has the blog); a BLOG button in the top bar and a "Latest post" row on the home page.
3. **Sitemap and structured data.** `BlogPosting` JSON-LD with `datePublished` and `dateModified` matching the visible dates. The sitemap and `robots.txt` come from the curriculum-vitae generator today; the least invasive fix is a `sitemap-blog.xml` written here plus one extra `Sitemap:` line in `robots.txt` (a one-line change in curriculum-vitae, its own small PR).
4. **Share image per post.** A 1200 x 630 pixel-style image (title and date on the palette) with `og:image:alt`, width and height. Most link previews need a PNG or JPEG, not an SVG, and this site has no image library. Two ways out: reuse the script in curriculum-vitae that already draws the home image, or give every post the cover image from its header and fall back to the home image. To be decided when we get there.
5. **The first post: Volley Score.** A build log of about 800 words, from the app's README and PRs 6 to 10 in `garmin-watchfaces`, with the screenshots that already exist in that repo (copied into `blog/images/`). I draft it in João's voice ("I built", per the resume rules); João edits it and runs the watch check. The app is sideload-only, so it ends with the repo link and the install steps, not a store link.
6. **Optional later:** tag pages, a year-end recap, a fragment for each new feature.

## Risks and notes

- **Writing is the real work.** The code is small; a post needs João's review and, for the first one, his experience on the watch. I can draft every post from the repo and the PRs, but he decides what goes public.
- **No claims without a source.** A post may only state what the repo, a PR or João says. Numbers and tool names come from there.
- **Sitemap ownership** is split between two repos today (see step 3). It is the only place the blog touches curriculum-vitae.
- **Static, no JavaScript** for the blog: the toggle, palettes and skip link already work on any page that loads the shared script and stylesheet.
- **Images** are copied into this repo, so a post never depends on another site staying up.

## Order and size

Steps 1 and 2 are the core (a medium PR each). Steps 3 and 4 are small and can wait. Step 5 can start as soon as step 1 is merged, because the first post is also the test of the template.
