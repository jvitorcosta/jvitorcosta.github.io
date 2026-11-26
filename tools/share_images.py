"""Draw the share image of every post that lacks a current one (blog/share/<slug>.png).

Run from the site folder after adding a post or changing its title or date, then commit the PNGs:

    python -m tools.share_images            # --all redraws every one, --chrome picks the browser

Uses headless Chrome, so the pixel and body fonts come out exactly as on the site.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from homepage import share
from homepage.blog import load_posts

ROOT = Path(__file__).resolve().parents[1]
WINDOWS_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def find_chrome(given: Path | None) -> Path:
    for candidate in (given, os.environ.get("CHROME"), WINDOWS_CHROME):
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise SystemExit("Chrome not found: pass --chrome or set CHROME")


def draw(post, chrome: Path, out: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        page, shot = Path(tmp) / "card.html", Path(tmp) / "card.png"
        page.write_text(share.card_html(post, ROOT.as_uri()), encoding="utf-8")
        width, height = share.SIZE
        subprocess.run([str(chrome), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--allow-file-access-from-files", "--force-device-scale-factor=1",
                        f"--window-size={width},{height}", f"--screenshot={shot}", page.as_uri()],
                       check=True, capture_output=True, timeout=60)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(share.stamp(shot.read_bytes(), share.fingerprint(post)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true", help="redraw every image, current or not")
    parser.add_argument("--chrome", type=Path, help="path to the Chrome executable")
    args = parser.parse_args()
    for post in load_posts(ROOT):
        if post.share and not args.all:
            continue
        out = ROOT / share.SHARE_DIR / f"{post.slug}.png"
        draw(post, find_chrome(args.chrome), out)
        print(f"wrote {out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
