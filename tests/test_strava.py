import json
from pathlib import Path
from urllib.parse import parse_qs

import pytest

from homepage.sources.strava import fetch_activity

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "strava-activities.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "id", "client_secret": "secret", "refresh_token": "refresh"}


def fake(activities, details=None):
    """`details` maps an activity id to what the single-activity request returns; by default it
    echoes the list entry, as a raising callable it fails."""
    calls = []
    by_id = {str(a["id"]): a for a in activities}

    def post(url, data):
        calls.append(("post", url, data))
        return json.dumps({"access_token": "access", "refresh_token": "refresh"}).encode()

    def get(url, headers=None):
        calls.append(("get", url, headers))
        if "/athlete/activities" in url:
            return json.dumps(activities).encode()
        activity_id = url.rsplit("/", 1)[1]
        detail = (details or {}).get(activity_id, by_id[activity_id])
        if callable(detail):
            detail()
        return json.dumps(detail).encode()

    return calls, get, post


def fetch(activities=FIXTURE, details=None):
    calls, get, post = fake(activities, details)
    return fetch_activity(**CREDS, get=get, post=post), calls


def test_refreshes_the_token_then_reads_the_latest_activities():
    _, calls = fetch()
    (kind, url, data), (kind2, url2, headers) = calls[:2]
    assert (kind, url) == ("post", "https://www.strava.com/oauth/token")
    assert data == {"client_id": "id", "client_secret": "secret",
                    "grant_type": "refresh_token", "refresh_token": "refresh"}
    assert kind2 == "get" and url2.startswith("https://www.strava.com/api/v3/athlete/activities?")
    assert headers == {"Authorization": "Bearer access"}


def test_ride_becomes_the_row_with_speed_and_prs():
    act, _ = fetch()
    assert act.sport == "Ride" and act.emoji == "🚴" and act.title == "Lunch Ride"
    assert act.distance_km == 11.9 and act.moving_min == 47
    assert act.detail == "15.3 km/h · 12 PRs"
    assert act.date == "2026-11-06"
    assert act.url == "https://www.strava.com/activities/20885035443"


def test_pr_count_comes_from_the_activity_itself():
    # The list endpoint sends pr_count 0; only the single-activity request has the real number.
    listed = dict(FIXTURE[0], pr_count=0)
    act, calls = fetch([listed], details={"20885035443": dict(FIXTURE[0], pr_count=12)})
    assert act.detail == "15.3 km/h · 12 PRs"
    assert calls[-1] == ("get", "https://www.strava.com/api/v3/activities/20885035443",
                         {"Authorization": "Bearer access"})


def test_failed_activity_request_keeps_the_listed_values():
    def down():
        raise OSError("503")

    act, _ = fetch([dict(FIXTURE[0], pr_count=0)], details={"20885035443": down})
    assert act.title == "Lunch Ride" and act.detail == "15.3 km/h"


def test_run_shows_pace_and_no_prs():
    act, _ = fetch(FIXTURE[1:])
    assert act.emoji == "🏃" and act.detail == "5:30 /km"


def test_activity_without_distance_shows_only_time():
    act, _ = fetch([{"id": 3, "name": "Weights", "sport_type": "WeightTraining",
                     "start_date_local": "2026-11-04T19:00:00Z", "distance": 0, "moving_time": 3600}])
    assert act.distance_km is None and act.moving_min == 60 and act.detail == ""
    assert act.emoji == "🏋️"


def test_private_activities_are_skipped():
    hidden = dict(FIXTURE[0], visibility="only_me")
    act, _ = fetch([hidden, FIXTURE[1]])
    assert act.title == "Morning Run"


@pytest.mark.parametrize("drive", [
    {"distance": 9658.4, "moving_time": 1019, "max_speed": 24.54},  # 34.1 km/h average
    {"distance": 9000.0, "moving_time": 1800, "max_speed": 19.0},  # 18 km/h, but 68 km/h top
])
def test_drives_logged_as_rides_are_skipped(drive):
    # Laps pressed in the car for open-radars-manaus get saved as rides.
    act, _ = fetch([dict(FIXTURE[0], **drive), FIXTURE[1]])
    assert act.title == "Morning Run"


def test_fast_bike_ride_still_shows():
    act, _ = fetch([dict(FIXTURE[0], max_speed=14.0)])
    assert act.title == "Lunch Ride"


def test_no_activities_means_no_row():
    act, _ = fetch([])
    assert act is None


def test_never_keeps_location_or_health_fields():
    # The row is public: no route, start/end point or heart rate may ever reach it.
    act, _ = fetch()
    text = json.dumps(act.__dict__)
    for leak in ("abc123", "-3.1", "-60.0", "151"):
        assert leak not in text


def test_failed_token_refresh_raises_so_the_last_value_is_kept():
    def post(url, data):
        raise OSError("401")

    with pytest.raises(OSError):
        fetch_activity(**CREDS, get=lambda url, headers=None: b"[]", post=post)
