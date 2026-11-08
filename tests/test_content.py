import re
from pathlib import Path

import pytest

from homepage.content import load_content
from homepage.model import Activity

ROOT = Path(__file__).resolve().parents[1]


def test_loads_starting_party_in_order():
    content = load_content(ROOT)
    assert [(m.repo, m.tag) for m in content.party] == [
        ("car-cyberdeck", "DAILY"),
        ("or-solver-streamlit", "THESIS"),
        ("garmin-watchfaces", "WRIST"),
        ("open-radars-manaus", "CITY"),
    ]
    first = content.party[0]
    assert first.name["en"] == "Car Cyberdeck"
    assert first.blurb["en"] == "My car's cyberdeck: lights by touch, voice or watch, synced to the music"
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
        "Vitor Pinheiro · software engineer from Manaus"
    )


JARGON = ("can bus", "ble", "esp32", "lightgbm", "shap", "firmware", "fastapi", "streamlit",
          "llm", "api")


def test_pc_box_texts_are_short_plain_and_bilingual():
    pc_box = load_content(ROOT).pc_box
    assert pc_box
    for name, text in pc_box.items():
        for lang in ("en", "pt"):
            assert 0 < len(text[lang]) <= 60, (name, lang)
            words = text[lang].lower()
            found = [j for j in JARGON if re.search(r"\b" + re.escape(j) + r"\b", words)]
            assert not found, (name, lang, found)


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


@pytest.mark.parametrize("text", [
    "[activity\nsport = ",  # not TOML
    '[activity]\nsport = "Ride"\nemoji = "🚴"\n',  # incomplete
    '[activity]\nsport = "Ride"\nemoji = "🚴"\ntitle = "x"\nmoving_min = "25"\n'
    'detail = ""\ndate = "2026-11-04"\n',  # wrong type
    'activity = "Ride"\n',  # not a table
])
def test_bad_activity_file_skips_the_row_with_warning(tmp_path, capsys, text):
    root = _copy_data(tmp_path)
    (root / "data" / "activity.toml").write_text(text, encoding="utf-8")
    assert load_content(root).activity is None
    assert "::warning::activity" in capsys.readouterr().err


def test_non_table_pc_box_entry_is_skipped_with_warning(tmp_path, capsys):
    root = _copy_data(tmp_path)
    (root / "data" / "pc_box.toml").write_text(
        'oops = "text"\n[ask-vitor]\nen = "a"\npt = "b"\n', encoding="utf-8"
    )
    pc_box = load_content(root).pc_box
    assert "oops" not in pc_box and pc_box["ask-vitor"]["en"] == "a"
    assert "::warning::pc_box oops" in capsys.readouterr().err


def test_pc_box_case_field_is_loaded(tmp_path):
    root = _copy_data(tmp_path)
    (root / "data" / "pc_box.toml").write_text(
        '[or-solver-streamlit]\nen = "a"\npt = "b"\ncase = "solvedor"\n', encoding="utf-8"
    )
    assert load_content(root).pc_box["or-solver-streamlit"]["case"] == "solvedor"


def test_real_pc_box_links_solvedor_case():
    assert load_content(ROOT).pc_box["or-solver-streamlit"]["case"] == "solvedor"


def test_pc_box_rows_have_titles_and_known_tags():
    content = load_content(ROOT)
    tags = {k[4:] for k in content.strings["en"] if k.startswith("tag_")}
    for name, text in content.pc_box.items():
        assert text.get("title_en") and text.get("title_pt"), name
        assert text.get("tag") in tags, (name, text.get("tag"))


def test_pc_box_title_tag_and_pin_are_loaded(tmp_path):
    root = _copy_data(tmp_path)
    (root / "data" / "pc_box.toml").write_text(
        '[ask-vitor]\nen = "a"\npt = "b"\ntitle_en = "Ask Vitor"\ntitle_pt = "Pergunte"\n'
        'tag = "ai"\npin = true\n', encoding="utf-8")
    assert load_content(root).pc_box["ask-vitor"] == {
        "en": "a", "pt": "b", "title_en": "Ask Vitor", "title_pt": "Pergunte", "tag": "ai", "pin": "true"}
