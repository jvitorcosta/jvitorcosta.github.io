import json

import pytest

from tools import study_progress as sp

ROADMAP = """---
type: track
---
# Roadmap

Prose with a link [[Ignored Note]] outside any topic.

## Agents <!-- topic id=agents role=ai now=yes current=yes pt="Agentes" -->
- [[E5 Agents]]
- [[34 ReAct]]
- [[Harness#Lectures]]
- [x] Build an MCP server
- [ ] Bank 7 aloud

## Security <!-- topic id=security role=ai now=no pt="Segurança" -->
- [ ] Red-team the agent

## Site sync

- [ ] not a topic item
"""


def vault(tmp_path, roadmap=ROADMAP):
    v = tmp_path / "Vault"
    study = v / "Areas" / "Study"
    (study / "LLM Course").mkdir(parents=True, exist_ok=True)
    (study / "Papers").mkdir(exist_ok=True)
    (v / ".obsidian").mkdir(exist_ok=True)
    (v / ".obsidian" / "E5 Agents.md").write_text("---\nstatus: done\n---\n", encoding="utf-8")
    (study / "LLM Course" / "E5 Agents.md").write_text("---\ntype: lesson\nstatus: in-progress\n---\n", encoding="utf-8")
    (study / "Papers" / "34 ReAct.md").write_text("---\nstatus: todo\n---\n", encoding="utf-8")
    (study / "Harness.md").write_text(
        "---\nstatus: later\n---\n# H\n## Lectures\n- [x] 1\n- [ ] 2\n- [ ] 3\n- [x] 4\n## Projects\n- [ ] p\n",
        encoding="utf-8")
    (study / "Roadmap.md").write_text(roadmap, encoding="utf-8")
    return v


def test_percent_comes_from_checkboxes_and_note_statuses(tmp_path):
    data = sp.build(vault(tmp_path), "Roadmap", today="2026-11-23")
    # in-progress 0.5, todo 0, Lectures 2 of 4 = 0.5, checked 1, unchecked 0: 2.0 / 5 = 40%
    assert data == {
        "updated": "2026-11-23",
        "topics": [{
            "id": "agents", "title": {"en": "Agents", "pt": "Agentes"}, "percent": 40, "current": True,
            "items": [
                {"text": "E5 Agents", "percent": 50},
                {"text": "34 ReAct", "percent": 0},
                {"text": "Harness: Lectures", "percent": 50},
                {"text": "Build an MCP server", "percent": 100},
                {"text": "Bank 7 aloud", "percent": 0},
            ],
        }],
    }


def test_only_now_topics_reach_the_site_and_each_has_a_percent(tmp_path):
    ids = [t["id"] for t in sp.build(vault(tmp_path), "Roadmap")["topics"]]
    assert ids == ["agents"]
    everything = sp.build(vault(tmp_path), "Roadmap", only_now=False)["topics"]
    assert [(t["id"], t["percent"], t["current"]) for t in everything] == [
        ("agents", 40, True), ("security", 0, False)]


def test_output_never_leaks_paths_or_note_names(tmp_path):
    v = vault(tmp_path)
    text = json.dumps(sp.build(v, "Roadmap"))
    for secret in ("Vault", "Areas", "Study", "obsidian", ".md", "[[", "\\", "/"):
        assert secret not in text


def test_unresolved_link_is_an_error_not_a_silent_zero(tmp_path):
    bad = ROADMAP.replace("[[34 ReAct]]", "[[No Such Note]]")
    with pytest.raises(sp.RoadmapError, match="No Such Note"):
        sp.build(vault(tmp_path, bad), "Roadmap")


def test_heading_without_checkboxes_is_an_error(tmp_path):
    bad = ROADMAP.replace("[[Harness#Lectures]]", "[[Harness#Nothing]]")
    with pytest.raises(sp.RoadmapError, match="Nothing"):
        sp.build(vault(tmp_path, bad), "Roadmap")


def test_duplicate_topic_ids_and_empty_topics_are_errors(tmp_path):
    dup = ROADMAP.replace("id=security", "id=agents")
    with pytest.raises(sp.RoadmapError, match="duplicate"):
        sp.build(vault(tmp_path, dup), "Roadmap")
    empty = ROADMAP.replace("- [ ] Red-team the agent\n", "")
    with pytest.raises(sp.RoadmapError, match="no items"):
        sp.build(vault(tmp_path, empty), "Roadmap")


def test_missing_portuguese_title_is_an_error(tmp_path):
    bad = ROADMAP.replace(' pt="Agentes"', "")
    with pytest.raises(sp.RoadmapError, match="pt"):
        sp.build(vault(tmp_path, bad), "Roadmap")


def test_cli_writes_file_with_lf_and_check_detects_drift(tmp_path):
    v = vault(tmp_path)
    out = tmp_path / "study-progress.json"
    args = ["--vault", str(v), "--note", "Roadmap", "--out", str(out), "--today", "2026-11-23"]
    assert sp.main(args) == 0
    raw = out.read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n")
    assert sp.main([*args, "--check"]) == 0
    # a later date alone is not drift
    assert sp.main(["--vault", str(v), "--note", "Roadmap", "--out", str(out), "--today", "2026-12-01", "--check"]) == 0
    (v / "Areas" / "Study" / "Roadmap.md").write_text(ROADMAP.replace("- [ ] Bank 7", "- [x] Bank 7"), encoding="utf-8")
    assert sp.main([*args, "--check"]) == 1
    assert out.read_bytes() == raw  # --check never writes


def test_cli_needs_a_vault(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("STUDY_VAULT", raising=False)
    assert sp.main(["--out", str(tmp_path / "x.json")]) == 2
    assert "vault" in capsys.readouterr().err.lower()


def test_cli_reports_roadmap_errors_without_writing(tmp_path, capsys):
    v = vault(tmp_path, ROADMAP.replace("[[34 ReAct]]", "[[Gone]]"))
    out = tmp_path / "x.json"
    assert sp.main(["--vault", str(v), "--note", "Roadmap", "--out", str(out)]) == 2
    assert "Gone" in capsys.readouterr().err
    assert not out.exists()


def test_exactly_one_current_topic_among_the_ones_on_the_site(tmp_path):
    none = ROADMAP.replace(" current=yes", "")
    with pytest.raises(sp.RoadmapError, match="current"):
        sp.build(vault(tmp_path, none), "Roadmap")
    two = ROADMAP.replace('id=security role=ai now=no', 'id=security role=ai now=yes current=yes')
    with pytest.raises(sp.RoadmapError, match="current"):
        sp.build(vault(tmp_path, two), "Roadmap")
    # a topic that is not on the site may not be the current one
    hidden = ROADMAP.replace('now=no', 'now=no current=yes')
    with pytest.raises(sp.RoadmapError, match="current"):
        sp.build(vault(tmp_path, hidden), "Roadmap")
