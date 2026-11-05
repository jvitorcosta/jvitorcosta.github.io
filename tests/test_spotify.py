import json

import pytest

from homepage.sources.spotify import fetch_song


def test_song_maps_fields():
    body = {"playing": True, "title": "T", "artist": "A", "cover": "c", "url": "u"}
    seen = []

    def get(url, headers=None):
        seen.append(url)
        return json.dumps(body).encode()

    s = fetch_song(get=get)
    assert (s.title, s.artist, s.cover, s.url, s.playing) == ("T", "A", "c", "u", True)
    assert seen == ["https://spotify-now-playing-ashen-two.vercel.app/api/now-playing.json"]


def test_song_error_payload_raises():
    with pytest.raises(ValueError):
        fetch_song(get=lambda url, headers=None: b'{"error": "nope"}')


def test_song_non_json_raises():
    with pytest.raises(ValueError):
        fetch_song(get=lambda url, headers=None: b"<html>")
