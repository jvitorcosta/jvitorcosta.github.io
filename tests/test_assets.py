"""Checks on assets/site.css and assets/site.js: palette contrast, storage guards, Spotify timeout."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "assets" / "site.css"
JS_PATH = ROOT / "assets" / "site.js"
PALETTES = ("pocket", "night", "nu")
STRAVA_ORANGE = "#fc5200"


def css() -> str:
    return CSS_PATH.read_text(encoding="utf-8")


def js() -> str:
    return JS_PATH.read_text(encoding="utf-8")


def variables(block: str) -> dict[str, str]:
    return {k: v.strip().lower() for k, v in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", block)}


def palette(name: str) -> dict[str, str]:
    """The custom properties of the `.pal-<name> { … }` block."""
    blocks = re.findall(rf"(?m)^\s*\.pal-{name}\s*\{{([^}}]*)\}}", css())
    assert len(blocks) == 1, f".pal-{name} must be defined exactly once"
    return variables(blocks[0])


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name", PALETTES)
def test_palettes_pass_wcag_aa(name):
    p = palette(name)
    assert contrast(p["box"], p["ink"]) >= 4.5
    assert contrast(p["bg"], p["ink-on-bg"]) >= 4.5
    assert contrast(p["box"], p["accent"]) >= 3.0
    # site.css also uses the accent for small text links and the line colour for button borders.
    assert contrast(p["box"], p["accent"]) >= 4.5
    assert contrast(p["box"], p["line"]) >= 3.0


@pytest.mark.parametrize("name", PALETTES)
def test_strava_link_passes_aa_and_is_underlined_when_not_strava_orange(name):
    p = palette(name)
    assert contrast(p["box"], p["strava"]) >= 4.5
    if p["strava"] != STRAVA_ORANGE:
        assert p["strava-decoration"] == "underline"
    assert ".strava-link" in css()


def test_nu_purple_is_820AD1():
    assert palette("nu")["bg"] == "#820ad1"


def test_light_scheme_default_is_pocket():
    """Without JS, a light-mode phone gets Pocket: the media block repeats Pocket's values."""
    m = re.search(r"@media \(prefers-color-scheme: light\)\s*\{\s*[^{]+\{([^}]*)\}", css())
    assert m, "missing prefers-color-scheme: light block"
    assert variables(m.group(1)) == palette("pocket")


def test_lang_rule_never_hides_html_element():
    text = css()
    assert re.search(r"html\[lang=pt\] \[lang=en\]", text)
    assert re.search(r"html\[lang=en\] \[lang=pt\]", text)
    assert "[hidden]" in text
    assert "prefers-reduced-motion: reduce" in text


def _try_bodies(source: str) -> list[str]:
    bodies = []
    for m in re.finditer(r"\btry\s*\{", source):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(source[i], 0)
            i += 1
        bodies.append(source[m.end():i - 1])
    return bodies


def test_storage_access_is_guarded():
    source = js()
    total = source.count("localStorage")
    assert total > 0
    assert sum(body.count("localStorage") for body in _try_bodies(source)) == total


def test_spotify_fetch_has_timeout():
    source = js()
    assert "AbortController" in source
    assert "4000" in source


def test_fetched_data_never_goes_through_innerhtml():
    assert "innerHTML" not in js()


def _rule(selector_pattern: str) -> str:
    m = re.search(rf"(?m)^{selector_pattern}\s*\{{([^}}]*)\}}", css())
    assert m, f"no rule for {selector_pattern}"
    return m.group(1)


def test_brand_icons_contrast_with_their_circle():
    """Each badge's main glyph colour reads on its own circle, which matches the fallback colour."""
    from homepage.markup import ICONS, PLATFORMS

    for platform, (_, circle) in PLATFORMS.items():
        svg = (ROOT / ICONS / f"{platform}.svg").read_text(encoding="utf-8")
        fills = re.findall(r'fill="(#[0-9a-f]{6})"', svg)
        assert fills[0] == circle, f"{platform} circle"
        assert contrast(fills[1], circle) >= 3.0, f"{platform} glyph on {circle}"
    assert "invert" not in css()


def test_language_toggle_name_contains_visible_text():
    source = js()
    assert re.search(r'setAttribute\("aria-label",\s*label', source)


@pytest.mark.parametrize("selector", [r"\.k", r"\.badge", r"\.mon \.lv"])
def test_pixel_labels_are_at_least_10px(selector):
    size = re.search(r"font-size:\s*(\d+)px", _rule(selector))
    assert size and int(size.group(1)) >= 10


def test_language_switch_updates_translated_aria_labels():
    source = js()
    assert "data-aria-" in source
    assert re.search(r'each\("\[data-aria-en\]"', source)


def test_footer_outside_main_keeps_the_column():
    assert re.search(r"body > footer\.foot", css())


def test_fonts_are_self_hosted():
    text = css()
    assert "googleapis" not in text and "gstatic" not in text
    faces = re.findall(r"@font-face\s*\{([^}]*)\}", text)
    families = {re.search(r"font-family:\s*'([^']+)'", f).group(1) for f in faces}
    assert families == {"Inter", "Press Start 2P"}
    for face in faces:
        assert "font-display: swap" in face and "unicode-range:" in face
        for src in re.findall(r"url\(([^)]+)\)", face):
            assert not re.match(r"(https?:)?//", src)
            assert (CSS_PATH.parent / src.strip("'\"")).is_file(), src
    # @font-face rules come first, before any other rule
    assert text.index("@font-face") < text.index(".pal-pocket")
    for licence in ("OFL-Inter.txt", "OFL-PressStart2P.txt"):
        assert (ROOT / "assets" / "fonts" / licence).is_file()


def _cover_src(data: dict) -> str:
    # Runs the real coverSrc() from site.js, together with safeHttps() which it calls.
    source = js()
    funcs = "".join(re.search(rf"(?ms)^  function {name}\(.*?^  \}}\n", source).group(0)
                    for name in ("safeHttps", "coverSrc"))
    script = funcs + f"process.stdout.write(coverSrc({json.dumps(data)}));"
    return subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_spotify_cover_prefers_the_inline_image():
    # The inline cover keeps visitors' browsers off Spotify's CDN; only JPEG/PNG data URIs pass.
    jpeg = "data:image/jpeg;base64,/9j/AAA="
    assert _cover_src({"cover_data": jpeg, "cover": "https://i.scdn.co/image/a"}) == jpeg
    assert _cover_src({"cover_data": "data:image/png;base64,iVBO", "cover": ""}) == "data:image/png;base64,iVBO"
    assert _cover_src({"cover_data": "data:image/svg+xml;base64,PHN2Zz4=",
                       "cover": "https://i.scdn.co/image/a"}) == "https://i.scdn.co/image/a"
    assert _cover_src({"cover_data": "javascript:alert(1)", "cover": "http://x"}) == ""
    assert _cover_src({"cover": "https://i.scdn.co/image/a"}) == "https://i.scdn.co/image/a"


FAKE_IMG = """
function fakeImg(src) {
  var a = src ? {src: src} : {};
  return {hidden: false, onerror: null,
    getAttribute: function (k) { return k in a ? a[k] : null; },
    setAttribute: function (k, v) { a[k] = String(v); },
    removeAttribute: function (k) { delete a[k]; }};
}
"""


def _cover_after(initial: str, src: str, fail: bool) -> str:
    # Runs the real setCover() from site.js on a fake <img>, optionally firing its error event.
    source = js()
    func = re.search(r"(?ms)^  function setCover\(.*?^  \}\n", source).group(0)
    script = (FAKE_IMG + func + f"var img = fakeImg({json.dumps(initial)}); setCover(img, {json.dumps(src)});"
              + ("if (img.onerror) img.onerror();" if fail else "")
              + "process.stdout.write(JSON.stringify([img.getAttribute('src'), img.hidden]));")
    return subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_blocked_inline_cover_falls_back_to_the_saved_one():
    saved, inline = "assets/live/abc.jpg", "data:image/jpeg;base64,/9j/AAA="
    assert json.loads(_cover_after(saved, inline, fail=False)) == [inline, False]
    assert json.loads(_cover_after(saved, inline, fail=True)) == [saved, False]
    assert json.loads(_cover_after("", inline, fail=True))[1] is True  # nothing to fall back to: hide


COPIED_PAGES = sorted([*ROOT.glob("projects/*.html"), ROOT / "privacy.html"])


@pytest.mark.parametrize("page", COPIED_PAGES, ids=lambda p: p.name)
def test_copied_pages_point_at_the_current_stylesheet(page):
    # These pages come from curriculum-vitae with the site.css hash of the day they were copied.
    # After a style change, re-copy them (tools/build_site.py --copy-to) or phones keep the old CSS.
    html = page.read_text(encoding="utf-8")
    if "http-equiv=\"refresh\"" in html:
        return  # a redirect stub, no styles
    from homepage.markup import versioned
    current = versioned("assets/site.css").split("?v=")[1]
    assert f"site.css?v={current}" in html, f"{page.name}: re-copy the case pages"
