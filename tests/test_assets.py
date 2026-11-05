"""Checks on assets/site.css and assets/site.js: palette contrast, storage guards, Spotify timeout."""

import re
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
