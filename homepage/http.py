from __future__ import annotations

import urllib.request

USER_AGENT = "Mozilla/5.0 (homepage; +https://jvitorcosta.github.io)"
TIMEOUT = 30


def get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()
