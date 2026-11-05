from __future__ import annotations

import json
from collections.abc import Callable

from homepage import http
from homepage.model import Repo

EXCLUDED = {"jvitorcosta", "jvitorcosta.github.io", "spotify-now-playing"}


def fetch_repos(
    user: str = "jvitorcosta",
    token: str | None = None,
    get: Callable[..., bytes] = http.get,
) -> list[Repo]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/users/{user}/repos?type=owner&sort=pushed&per_page=100"
    return [
        Repo(
            name=r["name"],
            description=r.get("description") or "",
            url=r["html_url"],
            homepage=r.get("homepage") or "",
            pushed=r.get("pushed_at") or "",
        )
        for r in json.loads(get(url, headers=headers))
        if not (r.get("fork") or r.get("archived") or r.get("private") or r["name"] in EXCLUDED)
    ]
