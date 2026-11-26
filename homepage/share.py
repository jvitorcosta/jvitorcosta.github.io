"""The share image of a post: blog/share/<slug>.png, 1200 x 630, the title and date on a card.

Link previews need a PNG and the generator has no image library, so tools/share_images.py draws the
card below with a local Chrome and the PNG is committed. It carries the fingerprint of the card it
shows, so a post whose title or date changed is not shared with an old picture.
"""

from __future__ import annotations

import hashlib
import struct
import zlib
from datetime import date
from html import escape

SHARE_DIR = "blog/share"
SIZE = (1200, 630)
SIGNATURE = b"\x89PNG\r\n\x1a\n"
KEY = b"card\x00"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def date_label(iso: str) -> str:
    """"Nov 26, 2026": the card is in English, like the posts."""
    d = date.fromisoformat(iso)
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def card_html(post, base: str) -> str:
    """The 1200x630 page that becomes the image, in the Purpura palette like the home share image.
    `base` is the URL of the site folder, for the fonts and the avatar. A longer title gets a
    smaller size, so it stays inside the card."""
    size = 52 if len(post.title) <= 40 else 40 if len(post.title) <= 80 else 28
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:P;src:url({base}/assets/fonts/press-start-2p-latin.woff2)}}
@font-face{{font-family:I;src:url({base}/assets/fonts/inter-latin.woff2);font-weight:100 900}}
html,body{{margin:0;width:1200px;height:630px;background:#820ad1;overflow:hidden}}
.card{{position:absolute;left:70px;top:70px;width:1060px;height:490px;box-sizing:border-box;background:#f7f0e1;
border:8px solid #2a0845;box-shadow:16px 16px 0 #4a0478;padding:48px 60px;display:flex;flex-direction:column;color:#2a0845}}
.lv{{font:400 24px P;margin:0;color:#820ad1}}
h1{{font:400 {size}px/1.5 P;margin:auto 0;overflow-wrap:break-word}}
.by{{display:flex;gap:24px;align-items:center;font:500 30px/1.4 I}}
.ava{{width:96px;height:96px;flex:none;image-rendering:pixelated;background:#e9dcc2;border:5px solid #2a0845;padding:4px;box-sizing:border-box}}
.url{{font:400 18px P;color:#820ad1;margin-left:auto}}
</style></head><body><div class="card"><div class="lv">&#9654; BLOG</div><h1>{escape(post.title)}</h1>
<div class="by"><img class="ava" src="{base}/assets/avatar.png" alt=""><div>Vitor Pinheiro<br>{date_label(post.date)}</div>
<div class="url">jvitorcosta.github.io</div></div></div></body></html>"""


def fingerprint(post) -> str:
    """Changes when what the card shows changes (title, date or design), on any checkout."""
    return hashlib.sha256(card_html(post, "").replace("\r\n", "\n").encode("utf-8")).hexdigest()[:16]


def stamp(png: bytes, value: str) -> bytes:
    """The PNG with the fingerprint in a tEXt chunk right after the header."""
    data = KEY + value.encode("ascii")
    chunk = struct.pack(">I", len(data)) + b"tEXt" + data + struct.pack(">I", zlib.crc32(b"tEXt" + data))
    after_header = len(SIGNATURE) + 25  # IHDR is always 4 + 4 + 13 + 4 bytes
    return png[:after_header] + chunk + png[after_header:]


def stamped(png: bytes) -> str:
    """The fingerprint stored by stamp(), or ""."""
    at = len(SIGNATURE)
    while at + 8 <= len(png):
        length, kind = struct.unpack(">I4s", png[at:at + 8])
        data = png[at + 8:at + 8 + length]
        if kind == b"tEXt" and data.startswith(KEY):
            return data[len(KEY):].decode("ascii", "replace")
        at += 12 + length
    return ""
