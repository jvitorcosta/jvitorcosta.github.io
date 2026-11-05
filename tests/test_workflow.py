"""Runs the state-branch step of update-home.yml against throwaway local repos."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "update-home.yml").read_text(encoding="utf-8")
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(not BASH or not shutil.which("git"), reason="needs bash and git")


def step_script(name: str) -> str:
    m = re.search(rf"(?ms)^      - name: {re.escape(name)}\n(.*?)(?=^      - |\Z)", WORKFLOW)
    assert m, name
    run = re.search(r"(?ms)^        run: \|\n(.*)", m.group(1))
    assert run, f"{name} has no run block"
    return "\n".join(line[10:] for line in run.group(1).splitlines())


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def checkout(tmp_path, with_state: bool) -> Path:
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(tmp_path, "init", "-q", "-b", "main", str(work))
    for k, v in (("user.name", "t"), ("user.email", "t@t")):
        git(work, "config", k, v)
    (work / "README").write_text("x")
    git(work, "add", "README")
    git(work, "commit", "-qm", "main")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "-q", "origin", "main")
    if with_state:
        git(work, "checkout", "-q", "--orphan", "state")
        git(work, "rm", "-rqf", ".")
        (work / "data").mkdir()
        (work / "data" / "state.json").write_text('{"book": 1}\n')
        git(work, "add", "data")
        git(work, "commit", "-qm", "state")
        git(work, "push", "-q", "origin", "state")
        git(work, "checkout", "-q", "main")
        git(work, "branch", "-qD", "state")
    return work


def run(work: Path, name: str):
    return subprocess.run([BASH, "-e", "-c", step_script(name)], cwd=work, capture_output=True, text=True)


def test_existing_state_branch_is_checked_out(tmp_path):
    work = checkout(tmp_path, with_state=True)
    assert run(work, "Fetch the state branch").returncode == 0
    assert (work / ".state" / "data" / "state.json").read_text() == '{"book": 1}\n'


def test_missing_state_branch_starts_empty_and_is_created_on_save(tmp_path):
    # Deleting the branch is documented as safe: the next run must recreate it.
    work = checkout(tmp_path, with_state=False)
    assert run(work, "Fetch the state branch").returncode == 0
    (work / "data").mkdir()
    (work / "data" / "state.json").write_text("{}\n")
    (work / "assets" / "live").mkdir(parents=True)
    (work / "assets" / "live" / "a.jpg").write_text("img")
    result = run(work, "Save state")
    assert result.returncode == 0, result.stderr
    listed = subprocess.run(["git", "ls-remote", "--heads", "origin", "state"], cwd=work,
                            capture_output=True, text=True).stdout
    assert "refs/heads/state" in listed


def test_unreachable_state_branch_fails_the_job(tmp_path):
    # A failed fetch must stop the run, never deploy a page built from empty state.
    work = checkout(tmp_path, with_state=True)
    git(work, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    assert run(work, "Fetch the state branch").returncode != 0
