"""The latest Strava activity, through the Strava API with my own app's refresh token.

Only what the row shows is kept: sport, title, distance, moving time, speed or pace, PR count,
date and the activity link. Never the map, start/end points, heart rate or other health data.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Callable

from homepage import http
from homepage.model import Activity

TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities?per_page=10"
ACTIVITY_URL = "https://www.strava.com/api/v3/activities"
EMOJI = {
    "Ride": "🚴", "MountainBikeRide": "🚵", "GravelRide": "🚴", "EBikeRide": "🚴", "VirtualRide": "🚴",
    "Run": "🏃", "TrailRun": "🏃", "VirtualRun": "🏃", "Walk": "🚶", "Hike": "🥾", "Swim": "🏊",
    "WeightTraining": "🏋️", "Workout": "💪", "Crossfit": "💪", "Yoga": "🧘", "Rowing": "🚣",
}
# Sports Strava shows as a pace rather than a speed.
PACE = {"Run", "TrailRun", "VirtualRun", "Walk", "Hike"}


def fetch_activity(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    get: Callable[..., bytes] = http.get,
    post: Callable[[str, dict], bytes] = http.post,
) -> Activity | None:
    token = json.loads(post(TOKEN_URL, {
        "client_id": client_id, "client_secret": client_secret,
        "grant_type": "refresh_token", "refresh_token": refresh_token,
    }))["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    activities = json.loads(get(ACTIVITIES_URL, headers=headers))
    for a in activities:
        if a.get("visibility") == "only_me":
            continue
        # The list sends pr_count 0; the activity's own page has the real count. Without it the
        # row still shows, just without PRs.
        try:
            detail = json.loads(get(f"{ACTIVITY_URL}/{a['id']}", headers=headers))
            a = dict(a, pr_count=detail.get("pr_count", a.get("pr_count")))
        except Exception as exc:
            print(f"::warning::Strava PR count not read: {exc}", file=sys.stderr)
        return _row(a)
    return None


def _row(a: dict) -> Activity:
    sport = a.get("sport_type") or a.get("type") or "Workout"
    meters, seconds = float(a.get("distance") or 0), int(a.get("moving_time") or 0)
    detail = []
    if meters > 0 and seconds > 0:
        if sport in PACE:
            per_km = round(seconds / (meters / 1000))
            detail.append(f"{per_km // 60}:{per_km % 60:02d} /km")
        else:
            detail.append(f"{meters / seconds * 3.6:.1f} km/h")
    prs = int(a.get("pr_count") or 0)
    if prs:
        detail.append(f"{prs} PR" + ("s" if prs > 1 else ""))
    return Activity(
        sport=sport,
        emoji=EMOJI.get(sport, "🏅"),
        title=str(a.get("name") or sport),
        distance_km=round(meters / 1000, 1) if meters > 0 else None,
        moving_min=round(seconds / 60),
        detail=" · ".join(detail),
        date=str(a.get("start_date_local") or "")[:10],
        url=f"https://www.strava.com/activities/{a['id']}",
    )
