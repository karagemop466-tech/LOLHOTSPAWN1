"""Reverse-engineered collector for the Hotspawn Play League of Legends lobby.

How the page is delivered (verified 2026-10-21):
  * https://play.hotspawn.com/lol-pickems is an Angular SSR app.
  * The server embeds the fully hydrated component state in a
    <script id="ng-state" type="application/json"> tag.
  * The match list lives at state["1214417440"]["b"] (264 entries when probed).
    Each entry carries the Hotspawn match id, competition, tier, start time,
    offered points and both participants (id, name, crowd pick percentage).
  * Crowd pick percentages are recorded for transparency but are NEVER used as
    a probability input (per project requirement).

Only the match *list* is taken from Hotspawn. Probabilities come from external
bookmakers / prediction markets (see markets.py).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from common import http_get, iso, now_utc

LOBBY_URL = "https://play.hotspawn.com/lol-pickems"
MATCH_URL = "https://www.hotspawn.com/matches/{slug}"

TEAM_LOGO = "https://phpstack-1372681-6459848.cloudwaysapps.com/teams/{tid}.svg"


def _state_key_with_matches(state: dict) -> str:
    """Find the ng-state key that holds the list of pick'em matches."""
    best, best_len = None, -1
    for key, node in state.items():
        if not isinstance(node, dict):
            continue
        for sub_key, value in node.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                keys = set(value[0])
                if {"competition_name", "participants0_name", "participants1_name"} <= keys:
                    if len(value) > best_len:
                        best, best_len = (key, sub_key), len(value)
    if not best:
        raise RuntimeError("ng-state: could not locate the pick'em match list")
    return best


def fetch_matches() -> dict:
    html = http_get(LOBBY_URL, {"Accept": "text/html"}, gz=True).decode("utf-8", "replace")
    m = re.search(r'id="ng-state"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("ng-state not found in lol-pickems HTML (page format changed?)")
    state = json.loads(m.group(1))
    key, sub = _state_key_with_matches(state)
    raw = state[key][sub]

    matches = []
    for r in raw:
        start_ms = r.get("scheduled_start_time") or r.get("lock_time")
        start = (datetime.fromtimestamp(int(start_ms) / 1000, tz=timezone.utc)
                 if start_ms else None)
        lock = (datetime.fromtimestamp(int(r["lock_time"]) / 1000, tz=timezone.utc)
                if r.get("lock_time") else None)
        hs_url = None
        # The SSR payload keeps a match-id -> slug map; fall back to a search URL.
        matches.append({
            "hotspawn_id": str(r.get("id")),
            "tournament": r.get("competition_name"),
            "competition_id": str(r.get("competition_id") or ""),
            "tier": (r.get("tier") or "").strip(),
            "stage": (r.get("stage") or "").strip(),
            "sport": r.get("sport_name"),
            "status": r.get("status"),
            "start_utc": iso(start) if start else None,
            "lock_utc": iso(lock) if lock else None,
            "best_of": r.get("best_of") or r.get("series_format"),
            "offered_points": r.get("offered_points"),
            "team1": {
                "name": r.get("participants0_name"),
                "id": str(r.get("participants0_id") or ""),
                "crowd_pct": r.get("participants0_picked_percent"),
                "logo": TEAM_LOGO.format(tid=r.get("participants0_id")) if r.get("participants0_id") else None,
            },
            "team2": {
                "name": r.get("participants1_name"),
                "id": str(r.get("participants1_id") or ""),
                "crowd_pct": r.get("participants1_picked_percent"),
                "logo": TEAM_LOGO.format(tid=r.get("participants1_id")) if r.get("participants1_id") else None,
            },
            "hotspawn_url": hs_url,
        })

    # The slug map sits next to the match list in the same ng-state bucket.
    slug_map = {}
    for node in state.values():
        if isinstance(node, dict):
            for value in node.values():
                if isinstance(value, dict) and value and all(
                        isinstance(v, str) and v.startswith("https://www.hotspawn.com/matches/")
                        for v in value.values()):
                    slug_map.update(value)
    for mt in matches:
        url = slug_map.get(mt["hotspawn_id"])
        mt["hotspawn_url"] = url

    return {
        "source": LOBBY_URL,
        "retrieved_at": iso(now_utc()),
        "matches": matches,
    }


if __name__ == "__main__":
    d = fetch_matches()
    print(json.dumps(d["matches"][:2], indent=2)[:1500])
    print("count:", len(d["matches"]))
