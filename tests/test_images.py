from pathlib import Path

from homepage.images import cache_image, prune


def test_downloads_once(tmp_path):
    calls = []

    def get(url, headers=None):
        calls.append(url)
        return b"img"

    a = cache_image("https://x/p.jpg?v=1", tmp_path, get=get)
    b = cache_image("https://x/p.jpg?v=1", tmp_path, get=get)
    assert a == b and len(calls) == 1
    assert (tmp_path / a.split("/")[-1]).read_bytes() == b"img"


def test_returns_site_relative_path(tmp_path):
    p = cache_image("https://x/a.png?z=1", tmp_path / "new", get=lambda u: b"i")
    assert p.startswith("assets/live/") and p.endswith(".png") and "\\" not in p
    assert cache_image("https://x/noext", tmp_path, get=lambda u: b"i").endswith(".jpg")


def test_prune_removes_unused(tmp_path):
    (tmp_path / "keep.jpg").write_bytes(b"1")
    (tmp_path / "drop.jpg").write_bytes(b"2")
    prune(tmp_path, {"assets/live/keep.jpg"})
    assert [p.name for p in Path(tmp_path).iterdir()] == ["keep.jpg"]


def test_stale_tmp_file_is_not_cached(tmp_path):
    url = "https://x/p.jpg"
    p = cache_image(url, tmp_path, get=lambda u: b"first")
    name = p.split("/")[-1]
    (tmp_path / name).unlink()
    (tmp_path / (name + ".tmp")).write_bytes(b"partial")
    cache_image(url, tmp_path, get=lambda u: b"full")
    assert (tmp_path / name).read_bytes() == b"full"
    assert not (tmp_path / (name + ".tmp")).exists()


def test_failed_download_leaves_no_file(tmp_path):
    def boom(u):
        raise OSError("x")

    try:
        cache_image("https://x/p.jpg", tmp_path, get=boom)
    except OSError:
        pass
    assert list(tmp_path.iterdir()) == []
