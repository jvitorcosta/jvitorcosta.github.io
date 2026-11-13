import re
from pathlib import Path

from homepage.content import load_content
from homepage.model import AboutFact

ROOT = Path(__file__).resolve().parents[1]

NEVER_SHARE = (
    "salary", "salário", "address", "endereço", "bairro", "heart rate", "injury", "injuries",
    "lesão", "cpf", "not working", "unemployed", "girlfriend", "namorada", "father", "pai",
)


def _facts():
    return load_content(ROOT).about


def test_ids_unique_and_well_formed():
    ids = [f.id for f in _facts()]
    assert ids
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z0-9._-]+", i) for i in ids)


def test_every_fact_has_source_and_text():
    for f in _facts():
        assert isinstance(f, AboutFact)
        assert f.source.strip(), f.id
        assert f.text.strip(), f.id


def test_no_never_share_content():
    for f in _facts():
        assert "@" not in f.text, f.id
        assert not re.search(r"\d{8,}", f.text), f.id
        for word in NEVER_SHARE:
            pattern = rf"\b{re.escape(word)}\b"
            assert not re.search(pattern, f.text, re.IGNORECASE), f"{f.id}: {word}"


def test_load_content_reads_about(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "about.toml").write_text(
        '[[fact]]\nid = "a.one"\nsource = "S"\ntext = "One."\n\n'
        '[[fact]]\nid = "a.bad"\nsource = "S"\n\n'
        '[[fact]]\nid = "a.two"\nsource = "S"\ntext = "Two."\n',
        encoding="utf-8",
    )
    assert load_content(tmp_path).about == [AboutFact("a.one", "S", "One."), AboutFact("a.two", "S", "Two.")]


def test_missing_about_file_is_empty(tmp_path):
    (tmp_path / "data").mkdir()
    assert load_content(tmp_path).about == []


def _about_warnings(tmp_path, toml, capsys):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "about.toml").write_text(toml, encoding="utf-8")
    facts = load_content(tmp_path).about
    return facts, capsys.readouterr().err


def test_skipped_row_produces_a_warning(tmp_path, capsys):
    facts, err = _about_warnings(tmp_path, '[[fact]]\nid = "a.bad"\nsource = "S"\n', capsys)
    assert facts == []
    assert "about fact #1 skipped" in err


def test_single_fact_table_warns_how_to_fix_it(tmp_path, capsys):
    facts, err = _about_warnings(tmp_path, '[fact]\nid = "a.one"\nsource = "S"\ntext = "One."\n', capsys)
    assert facts == []
    assert "[[fact]]" in err and "double brackets" in err
