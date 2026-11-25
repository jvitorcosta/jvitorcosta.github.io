/* jvitorcosta.github.io: palette dots, language switch and the live Spotify row.
   Shared by the homepage and the case-study pages; every part no-ops when its markup is absent. */
(function () {
  "use strict";

  var root = document.documentElement;
  var PALETTES = ["night", "nu"];
  var THEME_COLOR = { night: "#8f1d1d", nu: "#820ad1" }; // the palettes' --bg, for the browser bar
  var LANGS = ["en", "pt"];
  var SPOTIFY_TIMEOUT_MS = 4000;

  // A square on the study map jumps to its topic in the list; open the details around it first.
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("#study a[href^='#study-']");
    var t = a && document.getElementById(a.getAttribute("href").slice(1));
    for (var d = t && t.closest("details"); d; d = d.parentElement && d.parentElement.closest("details")) {
      d.open = true;
    }
  });

  function load(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function save(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      /* private mode or storage blocked: the choice just isn't remembered */
    }
  }

  function initialPalette() {
    var stored = load("palette");
    if (PALETTES.indexOf(stored) >= 0) return stored;
    return "nu"; // Nu Purple is the main theme, whatever the system colour scheme
  }

  function initialLang() {
    var stored = load("lang");
    if (LANGS.indexOf(stored) >= 0) return stored;
    var nav = (navigator.language || "").toLowerCase();
    return nav.indexOf("pt") === 0 ? "pt" : "en";
  }

  function each(selector, fn) {
    Array.prototype.forEach.call(document.querySelectorAll(selector), fn);
  }

  /* ---------- palette ---------- */
  function applyPalette(name) {
    if (PALETTES.indexOf(name) < 0) return;
    PALETTES.forEach(function (p) { root.classList.remove("pal-" + p); });
    root.classList.add("pal-" + name);
    root.setAttribute("data-pal", name);
    var meta = document.querySelector("meta[name=theme-color]");
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "theme-color";
      document.head.appendChild(meta);
    }
    meta.content = THEME_COLOR[name];
    each("button[data-palette]", function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-palette") === name ? "true" : "false");
    });
  }

  // Run straight away (before wiring anything) so the stored palette replaces the hardcoded one
  // as early as a deferred script can.
  applyPalette(initialPalette());

  /* ---------- Spotify ---------- */
  function safeHttps(url) {
    if (typeof url !== "string" || !url) return "";
    try {
      var u = new URL(url);
      return u.protocol === "https:" ? u.href : "";
    } catch (e) {
      return "";
    }
  }

  // The endpoint inlines the cover so the browser never calls Spotify's CDN; only JPEG/PNG pass.
  function coverSrc(data) {
    var inline = data.cover_data;
    if (typeof inline === "string" &&
        (inline.indexOf("data:image/jpeg;base64,") === 0 || inline.indexOf("data:image/png;base64,") === 0)) {
      return inline;
    }
    return safeHttps(data.cover);
  }

  // If the new cover fails (a browser that blocks data: images, say), go back to the cover the
  // page was built with; with none, hide the image rather than show a broken one.
  function setCover(cover, src) {
    var saved = cover.getAttribute("data-saved-src");
    if (saved === null) {
      saved = cover.getAttribute("src") || "";
      cover.setAttribute("data-saved-src", saved);
    }
    cover.onerror = function () {
      cover.onerror = null;
      if (saved && cover.getAttribute("src") !== saved) cover.setAttribute("src", saved);
      else cover.hidden = true;
    };
    if (src) {
      cover.setAttribute("src", src);
      cover.hidden = false;
    } else {
      cover.removeAttribute("src");
      cover.hidden = true;
    }
  }

  function spotifyLabel(row) {
    var label = row.querySelector('[data-field="label"]');
    if (!label) return;
    var key = row.getAttribute("data-playing") === "true" ? "listening" : "last-played";
    var text = row.getAttribute("data-" + key + "-" + (root.lang === "pt" ? "pt" : "en"));
    if (text) label.textContent = text;
  }

  function setText(row, field, value) {
    var el = row.querySelector('[data-field="' + field + '"]');
    if (el) el.textContent = value;
  }

  function fillSpotify(row, data) {
    if (!data || typeof data !== "object" || typeof data.title !== "string" || !data.title) return;
    var playing = data.playing === true;
    setText(row, "title", data.title);
    setText(row, "artist", typeof data.artist === "string" ? data.artist : "");

    var link = row.querySelector("a.row");
    var href = safeHttps(data.url);
    if (link) {
      if (href) link.setAttribute("href", href);
      else link.removeAttribute("href");
    }
    var cover = row.querySelector('[data-field="cover"]');
    if (cover) setCover(cover, coverSrc(data));
    var badge = row.querySelector('[data-field="badge"]');
    if (badge) badge.hidden = !playing;

    row.setAttribute("data-playing", playing ? "true" : "false");
    row.setAttribute("data-filled", "");
    spotifyLabel(row);

    row.hidden = false;
    var box = document.getElementById("right-now");
    if (box) box.hidden = false;
  }

  function loadSpotify() {
    var row = document.getElementById("spotify-row");
    var endpoint = row && safeHttps(row.getAttribute("data-endpoint"));
    if (!endpoint || !window.fetch) return;
    var controller = window.AbortController ? new AbortController() : null;
    var timer = controller ? setTimeout(function () { controller.abort(); }, SPOTIFY_TIMEOUT_MS) : 0;
    fetch(endpoint, { signal: controller ? controller.signal : undefined, credentials: "omit" })
      .then(function (response) {
        if (!response.ok) throw new Error("spotify " + response.status);
        return response.json();
      })
      .then(function (data) { fillSpotify(row, data); })
      .catch(function () { /* keep the row the daily job rendered; no retries */ })
      .then(function () { clearTimeout(timer); });
  }

  /* ---------- language ---------- */
  function applyLang(code) {
    if (LANGS.indexOf(code) < 0) return;
    root.lang = code;
    each("button[data-lang-toggle]", function (b) {
      // Both languages stay visible; CSS fills the current one (html[lang]). WCAG 2.5.3: the
      // accessible name starts with the visible text. Pages built before this change get the markup here.
      if (!b.querySelector(".l-en")) {
        b.textContent = "";
        [["l-en", "EN"], [null, " / "], ["l-pt", "PT"]].forEach(function (part) {
          if (!part[0]) { b.appendChild(document.createTextNode(part[1])); return; }
          var s = document.createElement("span");
          s.className = part[0];
          s.textContent = part[1];
          b.appendChild(s);
        });
      }
      b.setAttribute("aria-label", "EN / PT" + (code === "pt" ? ", mudar idioma" : ", switch language"));
    });
    // Labels without visible text (palette dots and their group) follow the page language.
    each("[data-aria-en]", function (el) {
      var label = el.getAttribute("data-aria-" + code);
      if (label) el.setAttribute("aria-label", label);
    });
    each("[data-title-en]", function (el) {
      var title = el.getAttribute("data-title-" + code);
      if (title) el.setAttribute("title", title);
    });
    var row = document.getElementById("spotify-row");
    if (row && row.hasAttribute("data-filled")) spotifyLabel(row);
  }

  /* ---------- wiring ---------- */
  function init() {
    applyPalette(root.getAttribute("data-pal") || initialPalette());
    each("button[data-palette]", function (b) {
      b.addEventListener("click", function () {
        var name = b.getAttribute("data-palette");
        applyPalette(name);
        save("palette", name);
      });
    });

    // Pages with the language button (the homepage and translated case pages) follow the stored choice.
    var toggles = document.querySelectorAll("button[data-lang-toggle]");
    if (toggles.length) {
      applyLang(initialLang());
      Array.prototype.forEach.call(toggles, function (b) {
        b.addEventListener("click", function () {
          var next = root.lang === "pt" ? "en" : "pt";
          applyLang(next);
          save("lang", next);
        });
      });
    }

    loadSpotify();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
