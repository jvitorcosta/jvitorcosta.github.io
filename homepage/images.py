from __future__ import annotations

import hashlib
import posixpath
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from homepage import http

SITE_DIR = "assets/live"


def cache_image(url: str, dest: Path, get: Callable[..., bytes] = http.get) -> str:
    suffix = posixpath.splitext(urlparse(url).path)[1] or ".jpg"
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + suffix
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    if not target.exists():
        target.write_bytes(get(url))
    return f"{SITE_DIR}/{name}"


def prune(dest: Path, keep: set[str]) -> None:
    """Delete cached files not in keep (site-relative paths or bare file names)."""
    wanted = {posixpath.basename(k) for k in keep}
    for f in Path(dest).iterdir():
        if f.is_file() and f.name not in wanted:
            f.unlink()
