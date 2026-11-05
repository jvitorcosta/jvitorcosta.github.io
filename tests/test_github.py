import json

from homepage.sources.github import fetch_repos


def repo(name, **kw):
    d = {"name": name, "description": "d", "html_url": f"https://github.com/jvitorcosta/{name}",
         "homepage": "", "pushed_at": "2026-01-01T00:00:00Z",
         "fork": False, "archived": False, "private": False}
    d.update(kw)
    return d


def fake(repos, seen=None):
    def get(url, headers=None):
        if seen is not None:
            seen.append((url, headers))
        return json.dumps(repos).encode()
    return get


def test_filters_forks_archived_private_and_excluded():
    repos = [repo("keep"), repo("f", fork=True), repo("a", archived=True), repo("p", private=True),
             repo("jvitorcosta"), repo("jvitorcosta.github.io"), repo("spotify-now-playing")]
    assert [r.name for r in fetch_repos(get=fake(repos))] == ["keep"]


def test_null_description_becomes_empty_string():
    r = fetch_repos(get=fake([repo("x", description=None, homepage=None)]))[0]
    assert r.description == "" and r.homepage == ""


def test_keeps_newest_first_order():
    assert [r.name for r in fetch_repos(get=fake([repo("b"), repo("a")]))] == ["b", "a"]


def test_maps_fields():
    r = fetch_repos(get=fake([repo("x", homepage="https://h")]))[0]
    assert (r.url, r.homepage, r.pushed) == ("https://github.com/jvitorcosta/x", "https://h", "2026-01-01T00:00:00Z")


def test_sends_token_when_given():
    seen = []
    fetch_repos(token="x", get=fake([], seen))
    url, headers = seen[0]
    assert url == "https://api.github.com/users/jvitorcosta/repos?type=owner&sort=pushed&per_page=100"
    assert headers["Authorization"] == "Bearer x"
    assert headers["Accept"] == "application/vnd.github+json"


def test_no_auth_header_without_token():
    seen = []
    fetch_repos(get=fake([], seen))
    assert "Authorization" not in seen[0][1]
