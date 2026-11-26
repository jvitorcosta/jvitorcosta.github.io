import re
from pathlib import Path

import pytest

from homepage.blog import BlogError, load_posts, parse_post
from homepage.render import render_blog_feed, render_blog_index, render_blog_post, render_home
from tests.test_render import REPOS, content, live

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "tests" / "fixtures" / "blog" / "sample-post.md").read_text(encoding="utf-8")
HEAD = "---\ntitle: T\ndate: 2026-11-26\nsummary: S\n---\n\n"


def post(body="Text.\n", header=HEAD, slug="t"):
    return parse_post(header + body, slug, f"blog/posts/{slug}.md")


def test_the_sample_post_has_every_construct():
    p = parse_post(SAMPLE, "sample-post")
    assert (p.title, p.date, p.updated, p.lane) == ("A sample post for the tests", "2026-11-26", "2026-11-27", "post")
    assert p.tags == ("garmin", "monkey-c") and p.cover == "images/cover.png"
    html = p.body
    assert "<code>inline code</code>" in html and "<strong>bold</strong>" in html and "<em>italic</em>" in html
    assert '<a href="https://example.com/page">link</a>' in html
    assert "<p>The first paragraph says what this is" in html and "It wraps onto a second line.</p>" in html
    assert '<h2 id="a-heading-with-an-id">A heading with an id</h2>' in html
    assert '<h3 id="a-smaller-heading">A smaller heading</h3>' in html
    assert "<ul><li>first bullet</li><li>second bullet with <code>code</code></li></ul>" in html
    assert "<ol><li>step one</li><li>step two</li></ol>" in html
    assert "<blockquote><p>A quoted line.</p></blockquote>" in html
    assert '<pre><code class="language-monkey-c">function onUpdate(dc) {' in html
    assert "return &quot;&lt;b&gt;&quot;;" in html and "\n\n    return 1;" in html  # escaped, blank line kept
    assert ('<figure><img src="images/scoreboard.png" alt="The scoreboard on the simulator" loading="lazy">'
            "<figcaption>Split blue and red, <strong>five</strong> to three.</figcaption></figure>") in html
    assert '<a href="../">link to the home page</a>' in html


def test_text_is_escaped_never_passed_through():
    html = post("A < B & C > D and \"quotes\" and `<script>` too.\n").body
    assert "&lt;" in html and "&amp;" in html and "&gt;" in html and "&quot;" in html
    assert "<script>" not in html and "<code>&lt;script&gt;</code>" in html


def test_reading_time_counts_words_outside_code():
    words = " ".join(["word"] * 450)
    assert post(f"{words}\n\n```\n{words}\n```\n").minutes == 3  # the code block is not counted
    assert post("Short.\n").minutes == 1


def test_duplicate_headings_get_different_ids():
    html = post("## Same\n\ntext\n\n## Same\n").body
    assert 'id="same"' in html and 'id="same-2"' in html


@pytest.mark.parametrize("text, message", [
    ("no header\n", "blog/posts/t.md:1: a post starts with a --- header"),
    ("---\ntitle: T\n", "the --- header is never closed"),
    ("---\ntitle: T\ncolour: red\ndate: 2026-11-26\nsummary: S\n---\nx\n", "blog/posts/t.md:3: unknown or malformed"),
    ("---\ntitle: T\ntitle: U\ndate: 2026-11-26\nsummary: S\n---\nx\n", "blog/posts/t.md:3: title is set twice"),
    ("---\ndate: 2026-11-26\nsummary: S\n---\nx\n", "the header needs title"),
    ("---\ntitle: T\ndate: 26/11/2026\nsummary: S\n---\nx\n", "date must be YYYY-MM-DD"),
    ("---\ntitle: T\ndate: 2026-11-26\nsummary: S\nlane: story\n---\nx\n", "lane is post or fragment"),
    ("---\ntitle: T\ndate: 2026-11-26\nsummary: S\ntags: garmin\n---\nx\n", "tags look like"),
    ("---\ntitle: T\ndate: 2026-11-26\nsummary: S\ncover: images/a.png\n---\nx\n", "a cover needs cover_alt"),
    ("---\ntitle: T\ndate: 2026-11-26\nsummary: S\ncover: ../a.png\ncover_alt: A\n---\nx\n", "relative path inside blog/"),
    ("---\ntitle: T\ndate: 2026-11-26\nsummary: S\n---\n\n", "the post has no text"),
])
def test_a_bad_header_names_the_file_and_the_problem(text, message):
    with pytest.raises(BlogError, match=re.escape(message)):
        parse_post(text, "t", "blog/posts/t.md")


@pytest.mark.parametrize("body, message", [
    ("<div>raw</div>\n", "raw HTML is not allowed"),
    ("# Title\n", "use ## or ### on a line of its own"),
    ("#### Deep\n", "use ## or ### on a line of its own"),
    ("- a\n  - nested\n", "lists are flat"),
    ("- a\n1. b\n", "lists are flat"),
    ("| a | b |\n|---|---|\n", "tables, * or + lists and rules are not supported"),
    ("* star bullet\n", "tables, * or + lists and rules are not supported"),
    ("[bad](javascript:alert(1))\n", "must be http(s), mailto or relative"),
    ("![](images/a.png)\n", "an image needs alt text"),
    ("![x](../secret.png)\n", "must be a relative path inside blog/"),
    ("![x](https://example.com/a.png)\n", ""),  # an outside image is allowed only if it is an https URL
    ("```python\nnever closed\n", "a code block is never closed"),
    ("```bad lang!\nx\n```\n", "unsupported code language"),
])
def test_unsupported_markdown_fails_with_file_and_line(body, message):
    if not message:
        assert "<img" in post(body).body
        return
    with pytest.raises(BlogError) as err:
        post(body)
    assert message in str(err.value) and re.search(r"blog/posts/t\.md:\d+", str(err.value))


def test_the_line_number_points_at_the_bad_block():
    with pytest.raises(BlogError, match=r"blog/posts/t\.md:11:"):
        post("fine\n\nfine again\n\n<b>bad</b>\n")  # the header is 5 lines and a blank one, so the body starts on line 7


def test_a_bad_file_name_is_refused():
    with pytest.raises(BlogError, match="file name"):
        post(slug="Bad_Name")


def test_load_posts_sorts_newest_first_and_skips_a_bad_file(tmp_path, capsys):
    folder = tmp_path / "blog" / "posts"
    folder.mkdir(parents=True)
    (folder / "old.md").write_text(HEAD.replace("2026-11-26", "2026-01-05") + "Old.\n", encoding="utf-8")
    (folder / "new.md").write_text(HEAD.replace("2026-11-26", "2026-11-26") + "New.\n", encoding="utf-8")
    (folder / "broken.md").write_text("nothing\n", encoding="utf-8")
    posts = load_posts(tmp_path)
    assert [p.slug for p in posts] == ["new", "old"]
    assert "::warning::blog/posts/broken.md:1" in capsys.readouterr().err


def test_no_posts_folder_means_no_posts(tmp_path):
    assert load_posts(tmp_path) == []


def page(**changes):
    text = SAMPLE
    for old, new in changes.items():
        text = text.replace(old, new)
    return render_blog_post(content(), parse_post(text, "sample-post"))


def test_the_post_page_has_title_meta_and_share_tags():
    html = page()
    assert "<title>A sample post for the tests | Vitor Pinheiro</title>" in html
    assert '<link rel="canonical" href="https://jvitorcosta.github.io/blog/sample-post.html">' in html
    assert '<meta property="og:type" content="article">' in html
    assert '<meta property="article:published_time" content="2026-11-26">' in html
    assert '<meta property="article:modified_time" content="2026-11-27">' in html
    assert '<meta name="description" content="One sentence for the list, the feed and the share preview.">' in html
    assert html.count("<h1") == 1 and '<h1 class="post-title">A sample post for the tests</h1>' in html


def test_the_post_page_shows_dates_reading_time_and_tags():
    html = page()
    assert '<time datetime="2026-11-26"><span lang="en">Nov 26, 2026</span><span lang="pt">26 nov 2026</span></time>' in html
    assert '<time datetime="2026-11-27">' in html and "Updated" in html and "Atualizado em" in html
    assert '<span lang="en">1 min read</span><span lang="pt">1 min de leitura</span>' in html
    assert '<ul class="tags" aria-label="Tags"><li>garmin</li><li>monkey-c</li></ul>' in html


def test_no_updated_line_when_the_dates_match_or_are_missing():
    assert "Atualizado em" not in page(**{"updated: 2026-11-27": "updated: 2026-11-26"})
    assert "article:modified_time" not in page(**{"updated: 2026-11-27\n": ""})


def test_the_post_uses_the_shared_chrome_with_paths_one_level_up():
    html = page()
    assert re.search(r'href="\.\./assets/site\.css\?v=[0-9a-f]{8}"', html)
    assert re.search(r'src="\.\./assets/site\.js\?v=[0-9a-f]{8}" defer', html)
    assert 'href="../favicon.ico"' in html and 'href="../site-privacy.html"' in html
    assert 'class="skip" href="#post"' in html and 'data-palette="night"' in html
    assert '<a href="../"><span aria-hidden="true">' in html  # the way back home
    assert "localStorage.getItem" in html  # the saved palette is applied before the first paint


def test_the_body_is_english_on_both_language_pages():
    html = page()
    # lang="en-US" is not hidden by html[lang=pt] [lang=en], so the English post shows on the pt page too
    assert '<div class="prose" lang="en-US">' in html
    assert 'lang="en">' not in html.split('<div class="prose"')[1].split("</div>")[0]


def test_a_post_without_a_cover_has_no_figure_and_shares_the_home_image():
    text = SAMPLE.replace("cover: images/cover.png\ncover_alt: A small test picture.\n", "")
    html = render_blog_post(content(), parse_post(text, "sample-post"))
    assert re.search(r'og:image" content="https://jvitorcosta\.github\.io/og-image\.png\?v=[0-9a-f]{8}"', html)
    assert 'class="cover"' not in html


FRAGMENT = (
    "---\n"
    "title: A short note\n"
    "date: 2026-12-02\n"
    "lane: fragment\n"
    "tags: [til]\n"
    "summary: Note & more\n"
    "---\n\n"
    "A note.\n"
)


def two_posts():
    return [parse_post(FRAGMENT, "short-note"), parse_post(SAMPLE, "sample-post")]


def test_the_index_lists_posts_and_fragments_with_their_dates():
    html = render_blog_index(content(), two_posts())
    assert html.index('<span lang="en">Posts</span>') < html.index("Fragments")
    assert '<a class="row" href="sample-post.html">' in html and '<a class="row" href="short-note.html">' in html
    assert '<span class="t" lang="en-US">A sample post for the tests</span>' in html
    assert '<span lang="en-US">Note &amp; more</span>' in html
    assert '<link rel="canonical" href="https://jvitorcosta.github.io/blog/">' in html
    assert '<a href="feed.xml">' in html and 'rel="alternate" type="application/atom+xml"' in html
    assert html.count("<h1") == 1 and 'href="../site-privacy.html"' in html


def test_the_index_leaves_out_an_empty_lane():
    html = render_blog_index(content(), [two_posts()[1]])
    assert "Fragments" not in html and "Posts" in html


def test_the_feed_is_atom_with_stable_ids_and_escaped_text():
    import xml.dom.minidom
    feed = render_blog_feed(two_posts())
    assert feed.startswith('<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"')
    assert "<id>https://jvitorcosta.github.io/blog/sample-post.html</id>" in feed
    assert "<id>https://jvitorcosta.github.io/blog/short-note.html</id>" in feed
    assert "<published>2026-11-26T00:00:00Z</published><updated>2026-11-27T00:00:00Z</updated>" in feed
    assert "<summary>Note &amp; more</summary>" in feed and '<category term="garmin"/>' in feed
    assert "<updated>2026-12-02T00:00:00Z</updated>" in feed.split("<entry>")[0]  # the newest entry
    assert "<author><name>Vitor Pinheiro</name></author>" in feed
    xml.dom.minidom.parseString(feed)  # well formed


def test_an_empty_feed_is_still_valid_atom():
    import xml.dom.minidom
    xml.dom.minidom.parseString(render_blog_feed([]))


def test_the_home_page_shows_the_blog_only_when_there_is_a_post(tmp_path):
    none = render_home(content(), live(), REPOS, tmp_path)
    assert 'id="writing"' not in none and 'class="top-link"' not in none and "feed.xml" not in none
    html = render_home(content(), live(), REPOS, tmp_path, two_posts())
    assert '<a class="top-link" href="blog/">BLOG</a>' in html
    assert ('<link rel="alternate" type="application/atom+xml" title="Vitor Pinheiro: blog" '
            'href="https://jvitorcosta.github.io/blog/feed.xml">') in html
    start = html.index('id="writing"')
    row = html[start:html.index("</section>", start)]
    assert 'href="blog/short-note.html"' in row and "A short note" in row  # the newest post
    assert "Latest post" in row and "Último post" in row and 'href="blog/"' in row


def test_the_post_page_links_to_the_blog_and_the_feed():
    html = page()
    assert '<a href="./"><span lang="en">All posts</span>' in html
    assert '<a class="top-link" href="./">BLOG</a>' in html
    assert 'rel="alternate" type="application/atom+xml"' in html
