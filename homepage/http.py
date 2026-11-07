from __future__ import annotations

import urllib.parse
import urllib.request

USER_AGENT = "Mozilla/5.0 (homepage; +https://jvitorcosta.github.io)"
TIMEOUT = 30


def get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def post(url: str, data: dict) -> bytes:
    """Form-encoded POST, for OAuth token refreshes."""
    body = urllib.parse.urlencode(data).encode("ascii")
    req = urllib.request.Request(url, data=body, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()
