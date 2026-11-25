import json
import re
import shutil
import xml.dom.minidom
from pathlib import Path

from homepage.blog import parse_post
from homepage.build import build
from homepage.render import render_blog_post, render_blog_sitemap
from tests.test_blog import FRAGMENT, SAMPLE
from tests.test_build import fake_get, sources
from tests.test_render import content

ROOT = Path(__file__).resolve().parents[1]
from tests.test_build import site  # noqa: E402,F401  (a fixture)


def structured_data(html: str) -> dict:
    raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    return json.loads(raw)


def test_a_post_page_carries_blogposting_data_matching_the_visible_dates():
    html = render_blog_post(content(), parse_post(SAMPLE, "sample-post"))
    data = structured_data(html)
    assert data["@type"] == "BlogPosting" and data["headline"] == "A sample post for the tests"
    assert data["datePublished"] == "2026-11-26" and data["dateModified"] == "2026-11-27"
    assert data["mainEntityOfPage"] == "https://jvitorcosta.github.io/blog/sample-post.html"
    assert data["author"] == {"@type": "Person", "name": "Vitor Pinheiro", "url": "https://jvitorcosta.github.io/"}
    assert data["keywords"] == "garmin, monkey-c" and data["inLanguage"] == "en"
    assert '<time datetime="2026-11-26">' in html and '<time datetime="2026-11-27">' in html  # the same dates are shown


def test_without_an_update_the_modified_date_is_the_published_date():
    data = structured_data(render_blog_post(content(), parse_post(FRAGMENT, "short-note")))
    assert data["dateModified"] == data["datePublished"] == "2026-12-02"
    assert "keywords" in data  # the fragment has a tag


def test_a_title_cannot_close_the_script_tag():
    text = SAMPLE.replace("title: A sample post for the tests", "title: Tags </script><b>x</b> & more")
    html = render_blog_post(content(), parse_post(text, "sample-post"))
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    assert "</script" not in block and "\\u003c" in block
    assert json.loads(block)["headline"] == "Tags </script><b>x</b> & more"


def test_the_blog_sitemap_lists_the_index_and_each_post_with_its_last_change():
    posts = [parse_post(FRAGMENT, "short-note"), parse_post(SAMPLE, "sample-post")]
    xml_text = render_blog_sitemap(posts)
    xml.dom.minidom.parseString(xml_text)  # well formed
    assert "<loc>https://jvitorcosta.github.io/blog/</loc><lastmod>2026-12-02</lastmod>" in xml_text
    assert "<loc>https://jvitorcosta.github.io/blog/sample-post.html</loc><lastmod>2026-11-27</lastmod>" in xml_text
    assert "<loc>https://jvitorcosta.github.io/blog/short-note.html</loc><lastmod>2026-12-02</lastmod>" in xml_text


def test_the_blog_sitemap_is_valid_and_empty_without_posts():
    xml_text = render_blog_sitemap([])
    xml.dom.minidom.parseString(xml_text)
    assert "<url>" not in xml_text and "sitemaps.org/schemas/sitemap" in xml_text


def test_robots_lists_both_sitemaps():
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://jvitorcosta.github.io/sitemap.xml" in robots
    assert "Sitemap: https://jvitorcosta.github.io/sitemap-blog.xml" in robots


def test_the_build_always_writes_the_blog_sitemap(site):
    build(site, sources(), get=fake_get)
    assert "<url>" not in (site / "sitemap-blog.xml").read_text(encoding="utf-8")  # no posts yet
    posts = site / "blog" / "posts"
    posts.mkdir(parents=True)
    shutil.copy(ROOT / "tests" / "fixtures" / "blog" / "sample-post.md", posts / "sample-post.md")
    build(site, sources(), get=fake_get)
    assert "blog/sample-post.html</loc>" in (site / "sitemap-blog.xml").read_text(encoding="utf-8")
