import re
import struct
import zlib
from pathlib import Path

from homepage import share
from homepage.blog import load_posts, parse_post
from homepage.render import render_blog_post
from tests.test_blog import SAMPLE
from tests.test_render import content

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://jvitorcosta.github.io/"


def png(width: int = 1200, height: int = 630) -> bytes:
    """The smallest thing shaped like a PNG: the signature, IHDR, an empty IDAT and IEND."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return share.SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", b"") + chunk(b"IEND", b"")


def site_with_post(tmp_path: Path, image: bytes | None) -> Path:
    posts = tmp_path / "blog" / "posts"
    posts.mkdir(parents=True)
    (posts / "sample-post.md").write_text(SAMPLE, encoding="utf-8")
    if image is not None:
        folder = tmp_path / "blog" / "share"
        folder.mkdir()
        (folder / "sample-post.png").write_bytes(image)
    return tmp_path


def meta(html: str, prop: str) -> str:
    return re.search(f'<meta property="{prop}" content="([^"]*)">', html).group(1)


def test_a_stamped_png_remembers_which_card_it_shows():
    stamped = share.stamp(png(), "abc123")
    assert share.stamped(stamped) == "abc123" and share.stamped(png()) == ""
    assert stamped.startswith(share.SIGNATURE) and stamped.endswith(png()[-12:])


def test_the_card_shows_the_escaped_title_and_the_date():
    post = parse_post(SAMPLE.replace("title: A sample post for the tests", "title: Tags <b> & more"), "sample-post")
    card = share.card_html(post, "file:///site")
    assert "Tags &lt;b&gt; &amp; more" in card and "Nov 26, 2026" in card and "<b>" not in card
    assert "width:1200px;height:630px" in card and "file:///site/assets/fonts/" in card


def test_the_fingerprint_follows_the_title_and_date_not_the_checkout_path():
    post = parse_post(SAMPLE, "sample-post")
    renamed = parse_post(SAMPLE.replace("title: A sample post", "title: Another post"), "sample-post")
    reworded = parse_post(SAMPLE.replace("summary: One sentence", "summary: Some other sentence"), "sample-post")
    assert share.fingerprint(post) != share.fingerprint(renamed)
    assert share.fingerprint(post) == share.fingerprint(reworded)
    assert re.fullmatch(r"[0-9a-f]{16}", share.fingerprint(post))


def test_a_post_with_a_current_image_shares_it(tmp_path):
    image = share.stamp(png(), share.fingerprint(parse_post(SAMPLE, "sample-post")))
    [post] = load_posts(site_with_post(tmp_path, image))
    assert re.fullmatch(r"share/sample-post\.png\?v=[0-9a-f]{8}", post.share)
    html = render_blog_post(content(), post)
    assert meta(html, "og:image") == f"{SITE}blog/{post.share}"
    assert meta(html, "og:image:width") == "1200" and meta(html, "og:image:height") == "630"
    assert meta(html, "og:image:alt") == "A sample post for the tests, Nov 26, 2026. Vitor Pinheiro&#x27;s blog."
    assert f'"image": "{SITE}blog/{post.share}"' in html


def test_without_an_image_the_home_one_is_shared(tmp_path, capsys):
    [post] = load_posts(site_with_post(tmp_path, None))
    assert post.share == "" and capsys.readouterr().err == ""
    html = render_blog_post(content(), post)
    assert re.fullmatch(re.escape(SITE) + r"og-image\.png\?v=[0-9a-f]{8}", meta(html, "og:image"))
    assert meta(html, "og:image:width") == "1200" and meta(html, "og:image:height") == "630"
    assert "Vitor Pinheiro" in meta(html, "og:image:alt")


def test_a_stale_image_is_reported_and_not_shared(tmp_path, capsys):
    [post] = load_posts(site_with_post(tmp_path, share.stamp(png(), "0" * 16)))
    assert post.share == ""
    assert "::warning::blog/share/sample-post.png" in capsys.readouterr().err


def test_every_published_post_has_a_current_share_image():
    """Run `python -m tools.share_images` after adding a post or changing its title or date."""
    posts = load_posts(ROOT)
    assert posts
    for post in posts:
        data = (ROOT / "blog" / "share" / f"{post.slug}.png").read_bytes()
        assert struct.unpack(">II", data[16:24]) == (1200, 630), post.slug
        assert share.stamped(data) == share.fingerprint(post), post.slug
        assert post.share, post.slug
