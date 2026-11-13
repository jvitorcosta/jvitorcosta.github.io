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
PALETTES = ("night", "nu")
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


def test_nu_purple_is_the_default_whatever_the_system_scheme():
    """Nu Purple is the main theme: no light/dark switch in the CSS or the script."""
    assert "prefers-color-scheme" not in css() and "prefers-color-scheme" not in js()
    assert 'return "nu";' in js()
    assert "pocket" not in css() and "pocket" not in js()


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
    assert text.index("@font-face") < text.index(".pal-night")
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


COPIED_PAGES = sorted([*ROOT.glob("projects/*.html"), ROOT / "privacy.html", ROOT / "site-privacy.html"])


@pytest.mark.parametrize("page", COPIED_PAGES, ids=lambda p: p.name)
def test_copied_pages_point_at_the_current_assets(page):
    # These pages come from curriculum-vitae with the site.css hash of the day they were copied.
    # After a style change, re-copy them (tools/build_site.py --copy-to) or phones keep the old CSS.
    html = page.read_text(encoding="utf-8")
    if "http-equiv=\"refresh\"" in html:
        return  # a redirect stub, no styles
    from homepage.markup import versioned
    for asset in ("site.css", "site.js"):
        current = versioned(f"assets/{asset}").split("?v=")[1]
        assert f"{asset}?v={current}" in html, f"{page.name}: re-copy the case pages ({asset})"


def test_asset_version_ignores_line_endings():
    # Windows checks files out with CRLF, the GitHub runner with LF: both must get the same ?v=,
    # or pages copied from a Windows build disagree with the homepage built on GitHub.
    from homepage.markup import content_version
    assert content_version(b"a {}\r\nb {}\r\n") == content_version(b"a {}\nb {}\n")
    assert content_version(b"a {}\n") != content_version(b"b {}\n")


def test_two_columns_only_on_wide_screens():
    text = css()
    wide = re.search(r"@media \(min-width: 900px\) \{(.*?)\n\}", text, re.S).group(1)
    assert re.search(r"\.cols \{[^}]*display: flex", wide)
    assert "max-width: 1000px" in wide
    # Work sits in the left column, so it is too tall to pin; phones put Lately first and Work last.
    assert "position: sticky" not in text
    phone = re.search(r"@media \(max-width: 899px\) \{(.*?)\n\}", text, re.S).group(1)
    assert "#right-now { order: 1; }" in phone and "#work { order: 4; }" in phone


@pytest.mark.parametrize("name", PALETTES)
def test_resume_button_and_status_pill_are_readable(name):
    p = palette(name)
    assert contrast(p["accent"], p["ink-on-bg"]) >= 4.5  # Resume (PDF): light text on the accent
    assert contrast(p["soft"], p["ink"]) >= 4.5           # status pill text
    assert contrast(p["box"], p["line"]) >= 3.0           # pill border on the card


def test_primary_button_is_filled_with_the_accent():
    rule = re.search(r"(?m)^\.links \.primary\s*\{([^}]*)\}", css())
    assert rule, ".links .primary rule missing"
    assert "background: var(--accent)" in rule.group(1) and "color: var(--ink-on-bg)" in rule.group(1)
    assert "#trainer .links .primary" not in css()


ASK_JS_PATH = ROOT / "assets" / "ask.js"


def ask_js() -> str:
    return ASK_JS_PATH.read_text(encoding="utf-8")


def test_ask_script_exists_and_never_inserts_html():
    # API text, source labels and dates go in with textContent / createElement only.
    source = ask_js()
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert sink not in source


def test_ask_script_holds_no_url():
    # The endpoint comes from #ask[data-endpoint]; links in the fixed replies come from the markup.
    source = ask_js()
    assert not re.search(r"https?:|mailto:|www\.", source)
    assert "data-endpoint" in source


def test_ask_close_button_closes_like_escape():
    source = ask_js()
    assert re.search(r'querySelector\("\[data-ask-close\]"\)', source)
    assert re.search(r'addEventListener\("click", close\)', source)
    assert re.search(r'e\.key === "Escape"\) close\(\)', source)


def _ask_frames(stream: str) -> list:
    # Runs the real SSE parser from ask.js (splitFrames + parseFrame) on a fixed stream.
    source = ask_js()
    funcs = "".join(re.search(rf"(?ms)^  function {name}\(.*?^  \}}\n", source).group(0)
                    for name in ("parseFrame", "splitFrames"))
    script = (funcs + f"var out = splitFrames({json.dumps(stream)});"
              "process.stdout.write(JSON.stringify([out.frames.map(parseFrame), out.rest]));")
    return json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_ask_stream_frames_follow_the_api_contract():
    stream = ('data: {"token": "Vitor "}\n\ndata: {"token": "works"}\n\n'
              'event: done\ndata: {"kind": "answer", "sources": []}\n\nevent: err')
    frames, rest = _ask_frames(stream)
    assert frames == [
        {"event": "message", "data": {"token": "Vitor "}},
        {"event": "message", "data": {"token": "works"}},
        {"event": "done", "data": {"kind": "answer", "sources": []}},
    ]
    assert rest == "event: err"  # an unfinished frame waits for the next chunk


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_ask_stream_frames_accept_crlf_and_no_space():
    stream = ('data:{"token": "a"}\r\n\r\nevent:done\r\ndata: {"kind": "fallback", "sources": []}\r\n\r\n'
              'data: {"t')
    frames, rest = _ask_frames(stream)
    assert frames == [
        {"event": "message", "data": {"token": "a"}},
        {"event": "done", "data": {"kind": "fallback", "sources": []}},
    ]
    assert rest == 'data: {"t'
    # A chunk ending between CR and LF keeps the CR, so the next chunk's LF doesn't end a frame early.
    frames, rest = _ask_frames('data: {"token": "a"}\r\n\r')
    assert frames == [] and rest == 'data: {"token": "a"}\n\r'


def test_ask_keeps_focus_and_marks_the_answer_busy():
    source = ask_js()
    # Clearing the chips or hiding STOP must not drop keyboard focus to <body>.
    assert "keepFocus(chips)" in source and "keepFocus(stop)" in source
    assert re.search(r"function keepFocus\(node\)[^}]*document\.activeElement", source)
    assert 'answer.setAttribute("aria-busy", "true")' in source
    assert 'answer.removeAttribute("aria-busy")' in source
    # Only an error releases the reader early; after `done` the API still writes its log, so the
    # script keeps reading to the end instead of cancelling.
    assert source.count("reader.cancel()") == 1
    error = re.search(r'if \(frame\.event === "error"\) \{(.*?)\}', source, re.S).group(1)
    assert "reader.cancel()" in error
    done = re.search(r'if \(frame\.event === "done"\) \{(.*?)\n {16}\}', source, re.S).group(1)
    assert "cancel" not in done and "drain()" in done
    assert re.search(r"function drain\(\) \{[^}]*reader\.read\(\)", source)


def _ask_sources(sources: list) -> list:
    # Runs the real renderSources from ask.js on a tiny fake DOM; returns each tag's English text.
    source = ask_js()
    funcs = "".join(re.search(rf"(?ms)^ {{2,4}}function {name}\(.*?^ {{2,4}}\}}\n", source).group(0)
                    for name in ("el", "both", "shortDate", "renderSources"))
    dom = """
    function Node(tag) { this.tag = tag; this.children = []; this.attrs = {}; this.textContent = ""; }
    Node.prototype.appendChild = function (c) { this.children.push(c); return c; };
    Node.prototype.setAttribute = function (k, v) { this.attrs[k] = v; };
    var document = { createElement: function (t) { return new Node(t); },
                     createTextNode: function (t) { var n = new Node("#text"); n.textContent = t; return n; } };
    function english(n) {
      if (n.attrs.lang === "pt") return "";
      return n.textContent + n.children.map(english).join("");
    }
    var sources = new Node("div");
    """
    script = (dom + funcs + f"renderSources({json.dumps(sources)});"
              "process.stdout.write(JSON.stringify(sources.children.map(english)));")
    run = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(run.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_ask_sources_date_only_live_and_repo_facts():
    tags = _ask_sources([
        {"id": "cv.nubank", "label": "CV · Experience", "updated": "2026-11-12"},
        {"id": "about.morning", "label": "About Vitor", "updated": "2026-11-12"},
        {"id": "live.song", "label": "Spotify", "updated": "2026-11-11"},
        {"id": "repo.car-cyberdeck", "label": "GitHub", "updated": "2026-11-06"},
    ])
    assert tags[0] == "[CV · Experience]" and tags[1] == "[About Vitor]"
    assert tags[2].startswith("[Spotify · ") and "11" in tags[2] and "2026" in tags[2]
    assert tags[3].startswith("[GitHub · ") and "2026" in tags[3]


def test_ask_openers_report_expanded_state():
    source = ask_js()
    assert 'setAttribute("aria-expanded", String(expanded))' in source
    assert re.search(r"function open\(button\) \{[^}]*expand\(true\)", source)
    assert re.search(r"function close\(\) \{[^}]*expand\(false\)", source)


def test_ask_layout_details():
    text = css()
    phone = re.search(r"@media \(max-width: 420px\) \{(.*?)\n\}", text, re.S).group(1)
    # TALK makes five trainer links; the odd one spans the row instead of sitting alone.
    assert "#trainer .links [data-ask-open] { grid-column: 1 / -1; }" in phone
    # Newlines in a streamed answer show as line breaks.
    assert re.search(r"(?m)^\.ask-answer \{[^}]*white-space: pre-line", text)


def test_ask_dialogue_styles():
    text = css()
    assert re.search(r"(?m)^\.ask \{[^}]*border: 4px solid var\(--line\)", text)
    assert re.search(r'#ask-title \{[^}]*"Press Start 2P"', text)
    assert re.search(r"(?m)^\.ask-cursor \{[^}]*animation:", text)
    motion = re.search(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}", text, re.S).group(1)
    assert ".ask-cursor" in motion
    # The ASK ME button looks like the language button.
    assert re.search(r"\[data-lang-toggle\], \.ask-open \{", text)
    close = _rule(r"\.ask \.ask-close")
    assert "min-width: 44px" in close and "min-height: 44px" in close
    assert "position: absolute" not in close  # it sits in the header row, never over the text
    assert "Segoe UI Symbol" in close  # a font with the glyph; Press Start 2P has none
    assert re.search(r"(?m)^\.ask-head \{[^}]*display: flex", text)


def test_ask_openers_are_revealed_by_the_script():
    # Rendered hidden, so a visitor without JavaScript never sees a button that does nothing.
    source = ask_js()
    assert re.search(r"function reveal\(\) \{[^}]*\.hidden = false", source, re.S)
    assert re.search(r"^\s*reveal\(\);", source, re.M)


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_ask_keep_focus_moves_focus_to_the_input_only_from_inside_the_node():
    # Runs the real keepFocus from ask.js with a fake document and fake nodes.
    func = re.search(r"(?ms)^ {2,6}function keepFocus\(.*?^ {2,6}\}\n", ask_js()).group(0)
    script = """
    var focused = null;
    var input = { focus: function () { focused = "input"; } };
    var inside = {}, outside = {};
    var document = { activeElement: inside };
    function box(owns) { return { contains: function (n) { return n === owns; } }; }
    """ + func + """
    keepFocus(box(inside));
    var moved = focused;
    focused = null;
    keepFocus(box(outside));
    process.stdout.write(JSON.stringify([moved, focused]));
    """
    run = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True)
    assert json.loads(run.stdout) == ["input", None]
