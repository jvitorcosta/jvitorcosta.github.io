/* jvitorcosta.github.io: palette dots, language switch and the live Spotify row.
   Shared by the homepage and the case-study pages; every part no-ops when its markup is absent. */
(function () {
  "use strict";

  var root = document.documentElement;
  var PALETTES = ["pocket", "night", "nu"];
  var LANGS = ["en", "pt"];
  var SPOTIFY_TIMEOUT_MS = 4000;

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

  function prefersLight() {
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches);
  }

  function initialPalette() {
    var stored = load("palette");
    if (PALETTES.indexOf(stored) >= 0) return stored;
    return prefersLight() ? "pocket" : "night";
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
    var src = safeHttps(data.cover);
    if (cover) {
      if (src) {
        cover.setAttribute("src", src);
        cover.hidden = false;
      } else {
        cover.removeAttribute("src");
        cover.hidden = true;
      }
    }
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
      // WCAG 2.5.3: the accessible name starts with the visible text.
      var label = code === "pt" ? "PT > EN" : "EN > PT";
      b.textContent = label;
      b.setAttribute("aria-label", label + (code === "pt" ? ", mudar idioma" : ", switch language"));
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

    // Only bilingual pages (the homepage) have the toggle; case pages stay in their own language.
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
