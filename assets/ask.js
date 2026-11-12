/* jvitorcosta.github.io: the TALK dialogue. Opens #ask, sends a question to the Ask Vitor API
   (#ask[data-endpoint]) and streams the answer in. Loaded only when the build sets ask_api.
   API text, source labels and dates go in with textContent, never as HTML. */
(function () {
  "use strict";

  var root = document.documentElement;
  var FOLLOWUPS = 2;

  function lang() {
    return root.lang === "pt" ? "pt" : "en";
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  /* ---------- SSE (same algorithm as ask-vitor web/lib/askStream.ts) ---------- */
  // One frame: an optional "event: <name>" line and a "data: <json>" line.
  function parseFrame(frame) {
    var event = "message";
    var data = {};
    frame.split("\n").forEach(function (line) {
      if (line.indexOf("event: ") === 0) event = line.slice("event: ".length);
      else if (line.indexOf("data: ") === 0) data = JSON.parse(line.slice("data: ".length));
    });
    return { event: event, data: data };
  }

  // Frames end with a blank line; a network chunk can stop mid-frame, so the tail waits.
  function splitFrames(buffer) {
    var frames = buffer.split("\n\n");
    var rest = frames.pop();
    return { frames: frames, rest: rest };
  }

  /* ---------- the dialogue ---------- */
  function init() {
    var box = document.getElementById("ask");
    var endpoint = box && box.getAttribute("data-endpoint");
    var form = box && box.querySelector("form.ask-form");
    if (!endpoint || !form || !window.fetch) return;

    var input = form.querySelector('input[name="q"]');
    var stop = form.querySelector("[data-ask-stop]");
    var answer = box.querySelector(".ask-answer");
    var sources = box.querySelector(".ask-sources");
    var chips = box.querySelector(".ask-chips");
    var error = box.querySelector(".ask-error");
    var opener = null;
    var controller = null;
    var asked = {};

    var followups = { en: [], pt: [] };
    ["en", "pt"].forEach(function (code) {
      var list = box.getAttribute("data-followups-" + code);
      followups[code] = list ? list.split("|") : [];
    });

    function placeholder() {
      var text = input.getAttribute("data-placeholder-" + lang());
      if (text) input.setAttribute("placeholder", text);
    }

    // site.js switches the language by setting <html lang>; text in both languages follows by CSS,
    // the placeholder attribute needs setting again.
    placeholder();
    if (window.MutationObserver) {
      new MutationObserver(placeholder).observe(root, { attributes: true, attributeFilter: ["lang"] });
    }

    /* open / close */
    function open(button) {
      opener = button;
      box.hidden = false;
      box.scrollIntoView({ block: "nearest" });
      input.focus({ preventScroll: true });
    }

    function close() {
      if (controller) controller.abort();
      box.hidden = true;
      if (opener) opener.focus();
    }

    Array.prototype.forEach.call(document.querySelectorAll("[data-ask-open]"), function (b) {
      b.addEventListener("click", function () { open(b); });
    });
    var closer = box.querySelector("[data-ask-close]");
    if (closer) closer.addEventListener("click", close);
    box.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });

    /* pieces of an answer */
    // A text in both languages, shown by the same lang rule as the rest of the page.
    function both(parent, texts) {
      ["en", "pt"].forEach(function (code) {
        var span = el("span", "", texts[code]);
        span.setAttribute("lang", code);
        parent.appendChild(span);
      });
    }

    function shortDate(iso, code) {
      var d = new Date(String(iso).slice(0, 10) + "T00:00:00Z");
      if (isNaN(d.getTime())) return String(iso);
      return d.toLocaleDateString(code === "pt" ? "pt-BR" : "en", {
        day: "numeric", month: "short", year: "numeric", timeZone: "UTC"
      });
    }

    function renderSources(list) {
      (Array.isArray(list) ? list : []).forEach(function (s) {
        if (!s || typeof s.label !== "string") return;
        var tag = el("span", "ask-tag", "[" + s.label);
        if (typeof s.updated === "string" && s.updated) {
          tag.appendChild(document.createTextNode(" · "));
          both(tag, { en: shortDate(s.updated, "en"), pt: shortDate(s.updated, "pt") });
        }
        tag.appendChild(document.createTextNode("]"));
        sources.appendChild(tag);
      });
    }

    function chip(texts) {
      var b = el("button");
      b.type = "button";
      b.setAttribute("data-ask-q", "");
      both(b, texts);
      chips.appendChild(b);
    }

    function wasAsked(i) {
      return asked[(followups.en[i] || "").toLowerCase()] || asked[(followups.pt[i] || "").toLowerCase()];
    }

    function suggest(n) {
      for (var i = 0; i < followups.en.length && n > 0; i++) {
        if (wasAsked(i)) continue;
        chip({ en: followups.en[i], pt: followups.pt[i] || followups.en[i] });
        n--;
      }
    }

    // A fixed reply from the markup (.ask-msgs), copied in whole so its links come along.
    function message(kind) {
      var node = box.querySelector('.ask-msgs [data-ask-msg="' + kind + '"]');
      return node ? node.cloneNode(true) : el("p");
    }

    function showError(kind) {
      error.textContent = "";
      error.appendChild(message(kind));
      error.hidden = false;
    }

    /* asking */
    function snapshot() {
      return [answer, sources, chips].map(function (node) {
        return { node: node, children: Array.prototype.slice.call(node.childNodes) };
      });
    }

    function restore(saved) {
      saved.forEach(function (s) {
        s.node.textContent = "";
        s.children.forEach(function (c) { s.node.appendChild(c); });
      });
    }

    function ask(question) {
      question = question.trim();
      if (!question || controller) return; // one request at a time
      var saved = snapshot();
      answer.textContent = "";
      sources.textContent = "";
      chips.textContent = "";
      error.textContent = "";
      error.hidden = true;

      var line = el("p");
      var text = document.createTextNode("");
      var cursor = el("span", "ask-cursor", "▼");
      cursor.setAttribute("aria-hidden", "true");
      line.appendChild(text);
      line.appendChild(cursor);
      answer.appendChild(line);

      controller = new AbortController();
      var signal = controller.signal;
      stop.hidden = false;

      function finish() {
        line.removeChild(cursor);
        if (!text.data) answer.removeChild(line);
        controller = null;
        stop.hidden = true;
      }

      function done(data) {
        asked[question.toLowerCase()] = true;
        if (data.kind === "answer") {
          renderSources(data.sources);
          suggest(FOLLOWUPS);
        } else if (data.kind === "fallback") {
          answer.appendChild(message("fallback"));
        } else if (data.kind === "off_topic") {
          suggest(1);
        }
      }

      fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question }),
        credentials: "omit",
        signal: signal
      })
        .then(function (response) {
          if (response.status === 422) return "invalid";
          if (response.status === 429) return "rate_limited";
          if (!response.ok || !response.body) return "down";
          input.value = "";
          var reader = response.body.getReader();
          var decoder = new TextDecoder();
          var buffer = "";

          function read() {
            return reader.read().then(function (chunk) {
              if (chunk.done) return "down"; // closed before the answer finished
              buffer += decoder.decode(chunk.value, { stream: true });
              var split = splitFrames(buffer);
              buffer = split.rest;
              for (var i = 0; i < split.frames.length; i++) {
                var frame = parseFrame(split.frames[i]);
                if (frame.event === "done") {
                  reader.cancel().catch(function () { /* already closed */ });
                  done(frame.data);
                  return "ok";
                }
                if (frame.event === "error") return "down";
                if (typeof frame.data.token === "string") text.appendData(frame.data.token);
              }
              return read();
            });
          }
          return read();
        })
        .catch(function () {
          return signal.aborted ? "stopped" : "down"; // STOP keeps the partial answer
        })
        .then(function (outcome) {
          finish();
          if (outcome === "invalid") restore(saved);
          else if (outcome === "rate_limited" || outcome === "down") showError(outcome);
        });
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      ask(input.value);
    });
    stop.addEventListener("click", function () {
      if (controller) controller.abort();
      input.focus();
    });
    chips.addEventListener("click", function (e) {
      var b = e.target.closest ? e.target.closest("button[data-ask-q]") : null;
      if (!b) return;
      var span = b.querySelector('[lang="' + lang() + '"]');
      ask((span || b).textContent);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
