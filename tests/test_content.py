from pathlib import Path

import pytest

from homepage.content import load_content
from homepage.model import Activity

ROOT = Path(__file__).resolve().parents[1]


def test_loads_starting_party_in_order():
    content = load_content(ROOT)
    assert [(m.repo, m.tag) for m in content.party] == [
        ("car-cyberdeck", "DAILY"),
        ("garmin-watchfaces", "WRIST"),
        ("open-radars-manaus", "CITY"),
        ("haylou-faces", "WRIST"),
    ]
    first = content.party[0]
    assert first.name["en"] == "Car Cyberdeck"
    assert first.blurb["en"] == "Spotify as a Pokémon battle on my dashboard"
    assert set(first.name) == set(first.blurb) == {"en", "pt"}


def test_loads_links_jobs_and_activity():
    content = load_content(ROOT)
    assert content.links["letterboxd"] == "https://letterboxd.com/zubu/"
    assert content.links["instagram"] == "https://www.instagram.com/joaovpi/"
    assert [j.company for j in content.jobs] == ["Qubika", "Nubank", "EloGroup"]
    assert content.activity == Activity(
        "Ride", "🚴", "Night Ride", 5.0, 25, "12.1 km/h · 3 PRs", "2026-11-04", ""
    )


def _copy_data(tmp_path: Path) -> Path:
    (tmp_path / "data").mkdir()
    for f in (ROOT / "data").iterdir():
        if f.suffix in {".toml", ".json"} and f.name != "state.json":
            (tmp_path / "data" / f.name).write_bytes(f.read_bytes())
    return tmp_path


def test_more_than_six_members_is_an_error(tmp_path):
    root = _copy_data(tmp_path)
    member = (
        '[[member]]\nrepo = "r{i}"\ntag = "X"\nname_en = "n"\nname_pt = "n"\n'
        'blurb_en = "b"\nblurb_pt = "b"\n'
    )
    (root / "data" / "party.toml").write_text(
        "\n".join(member.format(i=i) for i in range(7)), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="party has 7 members, max is 6"):
        load_content(root)


def test_missing_activity_is_none(tmp_path):
    root = _copy_data(tmp_path)
    (root / "data" / "activity.toml").write_text("", encoding="utf-8")
    assert load_content(root).activity is None


def test_both_languages_have_the_same_keys():
    strings = load_content(ROOT).strings
    assert set(strings) == {"en", "pt"}
    assert set(strings["en"]) == set(strings["pt"])
    required = {
        "greeting", "intro", "right_now", "listening", "last_played", "watched",
        "reading", "moving", "party", "pc_box", "all_on_github", "more", "work",
        "work_line", "footer", "page_title", "page_description",
    }
    assert required <= set(strings["en"])
    assert all(v.strip() for lang in strings.values() for v in lang.values())
    assert strings["en"]["page_title"] == (
        "Vitor Pinheiro · AI engineer in Manaus who builds gadgets for his car, watch and city"
    )


def test_pc_box_texts_start_empty():
    assert load_content(ROOT).pc_box == {}


def test_pc_box_texts_are_loaded(tmp_path):
    root = _copy_data(tmp_path)
    (root / "data" / "pc_box.toml").write_text(
        '[solvedor]\nen = "my thesis"\npt = "meu TCC"\n', encoding="utf-8"
    )
    assert load_content(root).pc_box == {"solvedor": {"en": "my thesis", "pt": "meu TCC"}}


def test_missing_pc_box_file_is_empty(tmp_path):
    root = _copy_data(tmp_path)
    (root / "data" / "pc_box.toml").unlink(missing_ok=True)
    assert load_content(root).pc_box == {}
