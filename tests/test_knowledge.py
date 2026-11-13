import json
import re

from homepage.knowledge import build_knowledge, write_knowledge
from homepage.model import AboutFact, Activity, Anime, Book, Film, LiveData, Repo, Song

TODAY = "2026-11-12"
ABOUT = [AboutFact("about.morning", "About Vitor", "Vitor starts the day with coffee."),
         AboutFact("cv.nubank", "CV · Experience", "Vitor worked at Nubank.")]
REPO = Repo("car-cyberdeck", "A car dashboard", "https://github.com/jvitorcosta/car-cyberdeck", "", "2026-11-01T00:00:00Z")
SONG = Song("Taxi Lunar", "Geraldo Azevedo", "", "https://open.spotify.com/track/1", False)
FILM = Film("Hope", "2026", 3.5, True, "2026-11-05", "Rua X 123, call 99999-0000", "", "https://letterboxd.com/x")
BOOK = Book("Can't Hurt Me", "David Goggins", "", "https://goodreads.com/b/1", 210, 366)
ANIME = Anime("Frieren", "", "https://myanimelist.net/anime/1", True, 5, 28, 9, "2026-11-10")
ACTIVITY = Activity("Run", "x", "Morning run at Ponta Negra", 5.2, 31, "5:58/km · 165 bpm", "2026-11-09", "")
UPDATED = {"song": "2026-11-11", "film": "2026-11-10", "book": "2026-11-09", "anime": "2026-11-08",
           "activity": "2026-11-07", "repos": "2026-11-06"}


def full():
    live = LiveData(SONG, FILM, BOOK, ACTIVITY, ANIME)
    return build_knowledge(ABOUT, [REPO], live, UPDATED, TODAY)


def facts_by_id(data):
    return {f["id"]: f for f in data["facts"]}


def test_contract_shape():
    data = full()
    assert data["version"] == 1 and data["generated"] == TODAY
    ids = [f["id"] for f in data["facts"]]
    assert len(ids) == len(set(ids))
    for f in data["facts"]:
        assert re.fullmatch(r"[a-z0-9._-]+", f["id"])
        assert set(f) == {"id", "source", "updated", "text"}
        assert f["text"]
    by = facts_by_id(data)
    assert by["about.morning"]["updated"] == TODAY
    assert by["live.song"]["updated"] == "2026-11-11"
    assert by["repo.car-cyberdeck"]["updated"] == "2026-11-06"
    assert by["live.song"]["source"] == "Spotify"
    assert "Taxi Lunar" in by["live.song"]["text"] and "Geraldo Azevedo" in by["live.song"]["text"]


def test_film_has_no_review():
    text = facts_by_id(full())["live.film"]["text"]
    assert "Hope" in text and "2026" in text
    assert "Rua X" not in text and "99999" not in text


def test_activity_only_sport_and_distance():
    text = facts_by_id(full())["live.activity"]["text"]
    assert "Run" in text.title() and "5.2" in text
    assert "Ponta Negra" not in text and "2026-11-09" not in text
    assert "bpm" not in text and "31" not in text


def test_missing_sources_are_skipped():
    data = build_knowledge(ABOUT, [], LiveData(None, None, None, None, None), {}, TODAY)
    assert [f["id"] for f in data["facts"]] == ["about.morning", "cv.nubank"]


def test_write_is_deterministic_lf(tmp_path):
    p = tmp_path / "knowledge.json"
    write_knowledge(p, full())
    first = p.read_bytes()
    write_knowledge(p, full())
    assert p.read_bytes() == first and b"\r" not in first
    assert json.loads(first)["version"] == 1


def activity_text(sport):
    t = Activity(sport, "x", "", 5.0, 31, "", "2026-11-09", "")
    live = LiveData(None, None, None, t, None)
    return facts_by_id(build_knowledge([], [], live, UPDATED, TODAY))["live.activity"]["text"]


def test_activity_sport_is_split_into_words_with_the_right_article():
    assert activity_text("WeightTraining") == "Vitor's latest Strava activity was a weight training of 5 km."
    assert activity_text("AlpineSki").startswith("Vitor's latest Strava activity was an alpine ski ")
    assert activity_text("Run").startswith("Vitor's latest Strava activity was a run ")


def test_bad_or_repeated_ids_are_dropped_with_a_warning(capsys):
    about = [AboutFact("about.ok", "About Vitor", "First."),
             AboutFact("Bad Id!", "About Vitor", "Broken id."),
             AboutFact("about.ok", "About Vitor", "Repeated id.")]
    data = build_knowledge(about, [], LiveData(None, None, None, None, None), {}, TODAY)
    assert [(f["id"], f["text"]) for f in data["facts"]] == [("about.ok", "First.")]
    err = capsys.readouterr().err
    assert "Bad Id!" in err and "about.ok" in err


def test_activity_without_a_fetch_date_uses_its_own_date_not_today():
    # The hand-written fallback row was never fetched, so state has no day for it.
    live = LiveData(None, None, None, ACTIVITY, None)
    data = build_knowledge([], [], live, {}, TODAY)
    assert facts_by_id(data)["live.activity"]["updated"] == "2026-11-09"


def test_activity_with_unreadable_date_falls_back_to_today():
    t = Activity("Run", "x", "", 5.0, 31, "", "n/a", "")
    data = build_knowledge([], [], LiveData(None, None, None, t, None), {}, TODAY)
    assert facts_by_id(data)["live.activity"]["updated"] == TODAY


def test_activity_with_zero_or_missing_distance_omits_it():
    for distance in (0, 0.0, None):
        t = Activity("WeightTraining", "x", "", distance, 50, "", "2026-11-09", "")
        live = LiveData(None, None, None, t, None)
        text = facts_by_id(build_knowledge([], [], live, UPDATED, TODAY))["live.activity"]["text"]
        assert text == "Vitor's latest Strava activity was a weight training."
