"""Hotspawn collection: LoL pick'em lobby, official fixture records, league pages.

Endpoints (all public, verified 2026-10-21 — see COORDINATION.md log):

* ``https://play.hotspawn.com/lol-pickems``
    Server-rendered League of Legends Pick'em lobby.  The lobby is the authoritative list of
    matches Hotspawn is currently offering pick'ems for (this week), including tier, points,
    stage, lock countdown and a link to the match page.  ``/lobby`` is the *other* title
    (Counter-Strike) lobby and is deliberately not used for LoL.
* ``https://www.hotspawn.com/wp-json/wp/v2/fixtures``
    Hotspawn's own WordPress REST feed for fixture posts.  Used to verify that each pick'em
    really exists on Hotspawn and to capture the canonical match-page URL + title.
* ``https://www.hotspawn.com/league-of-legends/tournament/<slug>``
    League page listing every fixture with an explicit ``HH:MM UTC`` kickoff, opponent and
    result, used to (a) verify lobby-derived kickoffs and (b) harvest completed results for
    the probability model.

No probability is ever derived from Hotspawn's "X% picked" values.  They are stored in
``hotspawn_pick_pct`` purely so the site can show the public pick distribution next to *our*
number, and they are excluded from every model/market input.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .common import (
    MONTHS, Fetcher, canon_team, html_to_lines, iso, log, parse_countdown, utcnow,
    write_debug,
)

LOBBY_URL = "https://play.hotspawn.com/lol-pickems"
FIXTURES_API = "https://www.hotspawn.com/wp-json/wp/v2/fixtures"
LEAGUE_BASE = "https://www.hotspawn.com/league-of-legends/tournament"

MATCH_HREF = re.compile(r'''(?:https?://[A-Za-z0-9.\-]*hotspawn\.com)?/matches/''' r'''(?P<slug>[^"'?#\s]*?)-(?P<id>\d{5,9})''')
LOBBY_DATE = re.compile(r"^(?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
                        r"(?P<day>\d{1,2}), (?P<hh>\d{1,2}):(?P<mm>\d{2})$")
RESET_RE = re.compile(r"Resets in\s+([0-9dhms ]+)")
COUNT_RE = re.compile(r"All tiers \((\d+)\)")
PCT_RE = re.compile(r"^(\d{1,3})\s*%\s*picked$", re.I)
TIME_UTC_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*UTC\b")
DAY_MON_RE = re.compile(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b")
SCORE_RE = re.compile(r"\b(\d{1,2})\s*[:\-]\s*(\d{1,2})\b")
LABELS_SKIP = {
    "who will win?", "sign in for streaks", "locks in", "view match", "points available",
    "stage", "tier", "live", "upcoming", "finished", "completed", "utc", "sign in to track",
}


SLUG_PROVIDER_ID = re.compile(r"-(\d{4,9})$")
SLUG_TOURNAMENT = re.compile(r"-league-of-legends-match-at-(.+?)-\d{4,9}$")


def provider_id_from_slug(slug: str | None):
    """Hotspawn's fixture slug ends with the provider id that also ends the match-page URL.

    The WordPress *post* id is a different number, so this is the only reliable join key between a
    lobby card (which shows the provider id) and the fixture feed.
    """
    m = SLUG_PROVIDER_ID.search(slug or "")
    return int(m.group(1)) if m else None


def tournament_slug_from_fixture_slug(slug: str | None):
    m = SLUG_TOURNAMENT.search(slug or "")
    return m.group(1) if m else None


# --------------------------------------------------------------------------- lobby
def parse_lobby(lines: list[str], fetched_at: datetime) -> list[dict]:
    """Parse the server-rendered lobby text stream into one dict per pick'em card."""
    out: list[dict] = []
    n = len(lines)
    for i, line in enumerate(lines):
        m = LOBBY_DATE.match(line)
        if not m:
            continue
        window = lines[i + 1: i + 26]
        if not window:
            continue
        card = {
            "lobby_index": len(out),
            "lobby_date_label": line,
            "lobby_tournament": None,
            "points": None,
            "tier": None,
            "multiplier": None,
            "stage": None,
            "lock_countdown_s": None,
            "match_url": None,
            "fixture_id": None,
            "fixture_slug": None,
            "teams": [],
            "hotspawn_pick_pct": [],
            "parse_notes": [],
        }
        # tournament name = first following line that is not a label
        for cand in window:
            if cand.lower() in LABELS_SKIP or cand.startswith("This week"):
                continue
            if LOBBY_DATE.match(cand):
                break
            card["lobby_tournament"] = cand
            break

        blob = "\n".join(window)
        pm = re.search(r"(\d{1,3})\s*pts", blob)
        if pm:
            card["points"] = int(pm.group(1))
        tm = re.search(r"Tier\s*[:\-]?\s*(S|A|B|C|D|WAITING FOR INFORMATION)"
                       r"(?:\s*(?:×|x)\s*([\d.]+))?", blob, re.I)
        if tm:
            card["tier"] = tm.group(1).upper() if tm.group(1).upper() != "WAITING FOR INFORMATION" \
                else "WAITING"
            if tm.group(2):
                card["multiplier"] = float(tm.group(2))
        sm = re.search(r"Stage\s*([A-Za-z][A-Za-z \-]{2,40})", blob)
        if sm:
            card["stage"] = re.split(r"(?:Multiplier|Locks in|Sign in)", sm.group(1))[0].strip() or None

        mm = MATCH_HREF.search(blob)
        if mm:
            card["fixture_id"] = int(mm.group("id"))
            card["fixture_slug"] = mm.group("slug")
            card["match_url"] = f"https://www.hotspawn.com/matches/{mm.group('slug')}-{mm.group('id')}"
        else:
            card["parse_notes"].append("no hotspawn match-page link in lobby card")

        # "Locks in" countdown.  Measured against the absolute time printed on the same card, the
        # countdown is systematically long (the lobby HTML is a cached server render), so it is
        # stored as a skew measurement and NOT used as the kickoff.
        idx_in_window = None
        for j, cand in enumerate(window):
            if cand.lower().startswith("locks in"):
                idx_in_window = j
                break
        if idx_in_window is not None:
            for cand in window[idx_in_window + 1: idx_in_window + 4]:
                secs = parse_countdown(cand)
                if secs is not None:
                    card["lock_countdown_s"] = secs
                    break
        if card.get("lock_countdown_s") is None:
            card["parse_notes"].append("no readable lock countdown")

        # kickoff: the card's own date line, printed in UTC (cross-checked below against the
        # tournament page, which labels the same value "HH:MM UTC")
        card["kickoff_utc"] = iso(kickoff_from_date_label(line, fetched_at))
        if not card["kickoff_utc"]:
            card["parse_notes"].append("lobby date line not parseable -> no kickoff")
        if card["kickoff_utc"] and card.get("lock_countdown_s") is not None:
            try:
                shown = datetime.fromisoformat(card["kickoff_utc"].replace("Z", "+00:00"))
                by_countdown = fetched_at + timedelta(seconds=card["lock_countdown_s"])
                card["lock_vs_displayed_min"] = round((by_countdown - shown).total_seconds() / 60.0)
            except ValueError:
                pass

        # team names + public pick share (display only)
        for j, cand in enumerate(window):
            pm2 = PCT_RE.match(cand)
            if not pm2:
                continue
            name = window[j - 1] if j else None
            if not name or PCT_RE.match(name) or name.lower() in LABELS_SKIP:
                card["parse_notes"].append("team label missing before a % picked line")
                continue
            if LOBBY_DATE.match(name) or MATCH_HREF.search(name) or len(name) > 60:
                card["parse_notes"].append(f"skipped non-team line {name[:40]!r}")
                continue
            card["teams"].append(name)
            card["hotspawn_pick_pct"].append(int(pm2.group(1)))
        if len(card["teams"]) != 2:
            card["parse_notes"].append(f"expected 2 teams, parsed {len(card['teams'])}")
        out.append(card)
    return out


def kickoff_from_date_label(label, now: datetime | None = None):
    """``"Oct 22, 12:00"`` -> an aware UTC datetime in the year of ``now``."""
    m = LOBBY_DATE.match(str(label or "").strip())
    if not m:
        return None
    year = now.year if isinstance(now, datetime) else datetime.now(timezone.utc).year
    mon = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,
           "nov":11,"dec":12}[m.group("mon").lower()]
    try:
        k = datetime(year, mon, int(m.group("day")), int(m.group("hh")), int(m.group("mm")),
                     tzinfo=timezone.utc)
    except ValueError:
        return None
    if isinstance(now, datetime) and now.month == 12 and k.month == 1:
        k = k.replace(year=year + 1)
    return k


def lobby_totals(lines: list[str]) -> dict:
    totals = {"matches_this_week": None, "tiers_count": None, "reset_in_s": None,
              "card_markers": sum(1 for l in lines if l.lower().startswith("who will win?"))}
    blob = "\n".join(lines[:60])
    tw = re.search(r"(\d+)\s+matches this week", blob)
    if tw:
        totals["matches_this_week"] = int(tw.group(1))
    ct = COUNT_RE.search(blob)
    if ct:
        totals["tiers_count"] = int(ct.group(1))
    rs = RESET_RE.search(blob)
    if rs:
        totals["reset_in_s"] = parse_countdown(rs.group(1))
    return totals


# --------------------------------------------------------------------------- fixtures API
def fixture_records(fetcher: Fetcher, fixture_ids: list[int]) -> dict[int, dict]:
    """Canonical fixture records for the given provider ids, from Hotspawn's own WP REST feed.

    ``include=<provider id>`` cannot be used: the id in a match URL is a provider id, not the
    WordPress post id (``/wp-json/wp/v2/fixtures/1081205`` -> 404 ``rest_post_invalid_id``).  So the
  LoL fixture pages are pulled once and indexed by the id at the end of the post slug.
    """
    want = {int(i) for i in fixture_ids if i}
    out: dict[int, dict] = {}
    feed = search_lol_fixtures(fetcher)
    for row in feed:
        pid = row.get("provider_id")
        if pid and (not want or pid in want) and pid not in out:
            out[pid] = row
    return out


def search_lol_fixtures(fetcher: Fetcher, max_pages: int = 6) -> list[dict]:
    """Every LoL fixture Hotspawn publishes (search of the fixture feed).

    Used as a completeness cross-check: any lobby match missing here, or any LoL fixture in a
    current event missing from the lobby, is recorded so the site can show real coverage
    numbers instead of claiming full coverage blindly.
    """
    found: dict[int, dict] = {}
    for page in range(1, max_pages + 1):
        url = (f"{FIXTURES_API}?search=league%20of%20legends&per_page=100&page={page}"
               f"&orderby=date&order=desc&_fields=id,date,modified,slug,link,title")
        data = fetcher.get_json(url)
        if not isinstance(data, list) or not data:
            break
        for row in data:
            title = ((row.get("title") or {}).get("rendered") or "")
            clean = re.sub(r"\s+", " ", title).strip()
            if "league of legends" not in clean.lower():
                continue
            slug = row.get("slug") or ""
            found[int(row["id"])] = {
                "fixture_id": int(row.get("provider_id") or provider_id_from_slug(slug) or 0),
                "wp_post_id": int(row["id"]),
                "wp_link": row.get("link"),
                "wp_title": clean,
                "wp_date": row.get("date"),
                "wp_modified": row.get("modified"),
                "provider_id": provider_id_from_slug(slug),
                "tournament_slug": tournament_slug_from_fixture_slug(slug),
                "source_url": row.get("link"),
                "source_label": "Hotspawn fixture record (WP REST feed)",
            }
        if len(data) < 100:
            break
    return list(found.values())


# --------------------------------------------------------------------------- league pages
def league_slug_from_url(url: str | None) -> str | None:
    if not url:
        return None
    m = re.search(r"/league-of-legends/tournament/([^/?#]+)", url)
    return m.group(1) if m else None


_CLOCK = re.compile(r"^\d{1,2}:\d{2}(\s*UTC)?$")
_DAYMON = re.compile(r"^\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$", re.I)
_STATUS_WORDS = ("upcoming", "live", "finished", "completed", "ft", "cancelled", "postponed")


def _match_anchors(markup: str):
    """Yield ``(href, inner_html)`` for every anchor pointing at a Hotspawn match page.

    A tiny scanner instead of one regex: real Hotspawn markup is flat, but nested/unclosed
    anchors must not make us skip a fixture (regex ``<a>.*?</a>`` would consume the inner anchor
    of a nested pair and lose a match).  Only ``href`` and the anchor's inner text are needed.
    """
    stack: list[tuple[int, str]] = []
    for tok in re.finditer(r"(?is)<a\b[^>]*>|</a>", markup or ""):
        raw = tok.group(0)
        if raw.lower().startswith("</a"):
            if stack:
                open_end, attrs = stack.pop()
                yield attrs, markup[open_end:tok.start()]
            continue
        href_m = re.search(r"""href\s*=\s*["']([^"']+)["']""", raw, re.I)
        if not href_m:
            continue
        href = href_m.group(1)
        if "/matches/" in href:
            stack.append((tok.end(), href))
        else:
            stack.append((tok.end(), None))


def _anchor_lines(inner: str) -> list[str]:
    text = re.sub(r"(?is)<[^>]+>", "\n", inner or "")
    out = []
    for raw in text.split("\n"):
        import html as _h
        line = _h.unescape(raw).replace("\u00a0", " ").strip()
        if line:
            out.append(line)
    return out


def _split_teams_and_score(lines: list[str]):
    """From an anchor's visible lines, keep the team labels and any series score."""
    teams, score, status = [], None, "upcoming"
    for line in lines:
        low = line.lower().strip()
        if low in _STATUS_WORDS:
            if low in ("finished", "completed", "ft"):
                status = "finished"
            if low in ("cancelled", "postponed"):
                status = low
            continue
        if _CLOCK.match(line) or _DAYMON.match(line):
            continue
        if re.fullmatch(r"\d{1,2}\s*[:\-]\s*\d{1,2}", line):
            a, b = re.split(r"\s*[:\-]\s*", line)
            score = (int(a), int(b))
            status = "finished"
            continue
        if re.fullmatch(r"[\d\s:\-.]+", line):
            continue
        if line.startswith("http") or len(line) > 60:
            continue
        teams.append(line)
    return teams[:2], score, status


def parse_league_page(text: str, base_url: str) -> dict:
    """Fixtures (kickoff in UTC, opponent, status, score) + tournament name from a league page.

    The league page prints every fixture with an explicit ``HH:MM UTC`` stamp, which is what
    lets us verify the lobby's relative "Locks in" countdown against an absolute time.
    """
    fixtures: dict[int, dict] = {}
    for row in _league_rows_from_lines(text, base_url):
        fixtures[row["fixture_id"]] = row
    name = None
    for pat in (r"(?is)<title>(.*?)</title>", r"(?is)<h1[^>]*>(.*?)</h1>"):
        hm = re.search(pat, text or "")
        if hm:
            name = re.sub(r"<[^>]+>", "", hm.group(1))
            name = re.sub(r"(?i)\s*live scores.*$", "", name)
            name = re.sub(r"(?i)\s*[-|]\s*hotspawn\s*$", "", name).strip(" -|")
            if name:
                break
    for href, inner in _match_anchors(text):
        if not href:
            continue
        mm = MATCH_HREF.search(href)
        if not mm:
            continue
        fid = int(mm.group("id"))
        lines = _anchor_lines(inner)
        joined = " ".join(lines)
        time_m = TIME_UTC_RE.search(joined)
        day_m = DAY_MON_RE.search(joined)
        teams, score, status = _split_teams_and_score(lines)
        kickoff = None
        if time_m and day_m:
            year = utcnow().year
            try:
                kickoff = datetime(year, MONTHS[day_m.group(2).lower()], int(day_m.group(1)),
                                   int(time_m.group(1)), int(time_m.group(2)), tzinfo=timezone.utc)
            except ValueError:
                kickoff = None
        if fid in fixtures and (fixtures[fid].get("league_kickoff_utc") or not kickoff):
            continue
        entry = {
            "fixture_id": fid,
            "league_url": base_url,
            "match_page": f"https://www.hotspawn.com/matches/{mm.group('slug')}-{fid}",
            "league_kickoff_utc": iso(kickoff),
            "league_teams": teams,
            "league_status": status,
            "league_score": list(score) if score else None,
            "league_raw": joined[:240],
        }
        if fid in fixtures and fixtures[fid].get("league_kickoff_utc"):
            continue
        fixtures[fid] = entry
    return {"tournament_name": name, "fixtures": list(fixtures.values())}


def harvest_results_from_league(text: str, base_url: str | None = None) -> list[dict]:
    """Completed fixtures with a readable scoreline -> the model's only form input."""
    rows = []
    seen = set()
    for row in _league_rows_from_lines(text, base_url):
        if not row.get("league_score") or row.get("league_status") != "finished":
            continue
        fid = row["fixture_id"]
        if fid in seen:
            continue
        seen.add(fid)
        rows.append({
            "fixture_id": fid,
            "team_home": row["league_home_display"],
            "team_away": row["league_away_display"],
            "score_home": row["league_score"][0],
            "score_away": row["league_score"][1],
            "source_url": row["match_page"],
            "source_note": "Hotspawn tournament page row: " + (row.get("league_raw") or "")[:160],
            "played_utc": row.get("league_kickoff_utc"),
        })
    for href, inner in _match_anchors(text):
        if not href:
            continue
        mm = MATCH_HREF.search(href)
        if not mm:
            continue
        fid = int(mm.group("id"))
        lines = _anchor_lines(inner)
        if any(l.lower().strip() == "upcoming" or l.lower().strip() == "live" for l in lines):
            continue
        teams, score, status = _split_teams_and_score(lines)
        if not score or status != "finished" or len(teams) < 2 or score == (0, 0):
            continue
        if fid in seen:
            continue
        seen.add(fid)
        rows.append({
            "fixture_id": fid,
            "team_home": teams[0],
            "team_away": teams[1],
            "score_home": score[0],
            "score_away": score[1],
            "source_url": f"https://www.hotspawn.com/matches/{mm.group('slug')}-{fid}",
        })
    return rows


_LEAGUE_CLOCK = re.compile(r"^(\d{1,2}):(\d{2})(?:\s*(?:UTC|GMT))?$", re.I)
_LEAGUE_DAY_A = re.compile(r"^(\d{1,2})\s+([A-Z][a-z]{2})(?:\s+(\d{4}))?$")
_LEAGUE_DAY_B = re.compile(r"^([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?$")
_LEAGUE_VS = re.compile(r"^(?P<a>[^|]{1,60}?)\s+(?:vs\.?|versus|@)\s+(?P<b>[^|]{1,60}?)$", re.I)
_LEAGUE_SCORE = re.compile(r"^(\d{1,2})\s*[:\-]\s*(\d{1,2})$")
_LEAGUE_STATUS = {
    "finished": "finished", "completed": "finished", "full time": "finished", "ft": "finished",
    "live": "live", "in progress": "live",
    "upcoming": "scheduled", "not started": "scheduled", "scheduled": "scheduled",
    "cancelled": "cancelled", "postponed": "postponed",
}


def _league_day(label: str):
    a = _LEAGUE_DAY_A.match(label)
    if a:
        return int(a.group(1)), a.group(2), (int(a.group(3)) if a.group(3) else None)
    b = _LEAGUE_DAY_B.match(label)
    if b:
        return int(b.group(2)), b.group(1), (int(b.group(3)) if b.group(3) else None)
    return None


def _league_rows_from_lines(markup: str, base_url: str | None = None) -> list[dict]:
    """Fixture rows read off the *text* of a league page (no assumption about element names).

    Hotspawn's tournament page prints, per fixture: a day label, a ``HH:MM UTC`` line, the two team
    labels, the match-page URL (kept inline by ``html_to_lines``) and a score or state word.  Rows
    are therefore matched by proximity between two consecutive clock lines, which survives the
    Next.js markup changes that break ``<tr>``/anchor assumptions.
    """
    lines = [l.strip() for l in html_to_lines(markup or "")]
    now = utcnow()
    clocks = [i for i, l in enumerate(lines) if _LEAGUE_CLOCK.match(l)]
    rows: list[dict] = []
    seen: set[int] = set()
    for k, i in enumerate(clocks):
        nxt = clocks[k + 1] if k + 1 < len(clocks) else len(lines)
        window = lines[i + 1:min(nxt, i + 15)]
        cm = _LEAGUE_CLOCK.match(lines[i])
        url_m = None
        score = None
        status = "scheduled"
        text_bits: list[str] = []
        for cand in window:
            if url_m is None and cand.startswith(("http", "/")):
                url_m = MATCH_HREF.search(cand)
                if url_m:
                    continue
            sm = _LEAGUE_SCORE.match(cand)
            if sm and score is None and not cand.startswith("http"):
                score = (int(sm.group(1)), int(sm.group(2)))
                continue
            low = cand.lower()
            if low in _LEAGUE_STATUS:
                status = _LEAGUE_STATUS[low]
                continue
            if _league_day(cand):
                break                       # next fixture block starts at the next day label
            if low.startswith(("who will win", "sign in", "locks in", "view match",
                               "points available", "tier", "stage", "multiplier")):
                continue
            if len(cand) <= 60:
                text_bits.append(cand)
        vs = None
        for cand in text_bits:
            vs = _LEAGUE_VS.match(cand)
            if vs:
                break
        if vs is None and len(text_bits) >= 3:
            joined = " ".join(text_bits)
            vs = _LEAGUE_VS.match(joined)
        if url_m is None or vs is None:
            continue
        fid = int(url_m.group("id"))
        if fid in seen:
            continue
        seen.add(fid)
        day = year = mon = None
        for back in range(i - 1, max(-1, i - 10), -1):
            d = _league_day(lines[back])
            if d:
                day, mon, year = d
                break
        kickoff = None
        if day and mon:
            try:
                kickoff = datetime(year or now.year, MONTHS[mon.lower()], day,
                                   int(cm.group(1)), int(cm.group(2)), tzinfo=timezone.utc)
            except (KeyError, ValueError):
                kickoff = None
        rows.append({
            "fixture_id": fid,
            "league_url": base_url,
            "match_page": f"https://www.hotspawn.com/matches/{url_m.group('slug')}-{fid}",
            "league_kickoff_utc": iso(kickoff),
            "league_teams": [canon_team(vs.group("a")), canon_team(vs.group("b"))],
            "league_home_display": vs.group("a").strip(),
            "league_away_display": vs.group("b").strip(),
            "league_status": "finished" if (score and status == "scheduled") else status,
            "league_score": list(score) if score else None,
            "league_day_label": lines[i - 1] if i else None,
            "league_raw": " | ".join([lines[i]] + window[:7])[:300],
            "time_shown_utc": bool(cm.group(2)),
        })
    return rows


# --------------------------------------------------------------------------- driver
def collect(fetcher: Fetcher, out_dir: str = "data", deep: bool = True) -> dict:
    """Full Hotspawn collection -> ``data/hotspawn.json``."""
    fetched_at = utcnow()
    markup = fetcher.get(LOBBY_URL)
    if not markup:
        return {"error": "lobby unreachable", "matches": [], "fetched_at": iso(fetched_at)}

    lines = html_to_lines(markup)
    write_debug("lobby_text_sample.txt", "\n".join(lines[:220]), out_dir)
    write_debug("lobby_text_tail.txt", "\n".join(lines[-160:]), out_dir)
    try:
        first = next(i for i, l in enumerate(lines) if l.lower().startswith("who will win?"))
    except StopIteration:
        first = 0
    write_debug("lobby_text_cards.txt",
                "\n".join(lines[max(0, first - 14):first + 90]), out_dir)
    pos = (markup or "").find("/matches/")
    write_debug("lobby_html_cards.txt",
                (markup[max(0, pos - 4000):pos + 2500] if pos != -1 else (markup or "")[:6000]),
                out_dir)

    cards = parse_lobby(lines, fetched_at)
    totals = lobby_totals(lines)
    log(f"lobby: parsed {len(cards)} pick'em cards (page reports {totals})")

    ids = [c["fixture_id"] for c in cards if c.get("fixture_id")]
    records = fixture_records(fetcher, ids)
    matched = 0
    for card in cards:
        rec = records.get(card.get("fixture_id")) if card.get("fixture_id") else None
        if rec:
            matched += 1
            card["wp_post_id"] = rec.get("wp_post_id")
            card["wp_title"] = rec.get("wp_title")
            card["wp_link"] = rec.get("wp_link")
            card["league_slug"] = rec.get("tournament_slug")
            card["fixture_verified"] = True
            names = FIXTURE_TITLE_TEAMS.match(rec.get("wp_title") or "")
            if names and len(card.get("teams") or []) == 2:
                a, b = names.group(1).strip(), names.group(2).strip()
                if a.lower() != card["teams"][0].lower() and b.lower() == card["teams"][0].lower():
                    card["teams"] = [b, a]     # fixture feed lists the higher seed second
                    card["teams_swapped_from_feed"] = True
        else:
            card["fixture_verified"] = False
    log(f"fixtures feed: matched {matched}/{len(set(ids))} distinct lobby fixture ids "
        f"({len(records)} records indexed)")

    # completeness cross-check against the whole LoL fixture feed
    all_fixtures = [f for f in records.values()] if deep else []
    seen_ids = set(ids)
    extra = [f for f in all_fixtures if f["fixture_id"] not in seen_ids]

    # league pages: verify kickoff times + harvest completed results
    slugs = sorted({(records.get(c.get("fixture_id")) or {}).get("tournament_slug")
                    or league_slug_from_url(c.get("match_url"))
                    for c in cards if c.get("match_url") or c.get("fixture_id")} - {None})
    log(f"league pages: fetching {len(slugs)} tournaments")
    leagues = {}
    def worker(slug):
        body = fetcher.get(f"{LEAGUE_BASE}/{slug}")
        return slug, body
    if slugs:
        for slug, body in fetcher.map(slugs, worker, max_workers=5):
            if not body:
                continue
            markup = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
            if not leagues:
                write_debug("league_page_sample.txt",
                            "\n".join(html_to_lines(markup)[:160]), out_dir)
            parsed = parse_league_page(markup, f"{LEAGUE_BASE}/{slug}")
            results = harvest_results_from_league(markup, f"{LEAGUE_BASE}/{slug}")
            leagues[slug] = {
                "slug": slug,
                "tournament_name": parsed["tournament_name"],
                "fixtures": parsed["fixtures"],
                "results": results,
            }
            log(f"  league {slug}: {len(parsed['fixtures'])} fixtures, {len(results)} with scores")

    return {
        "fetched_at": iso(fetched_at),
        "lobby_url": LOBBY_URL,
        "totals": totals,
        "matches": cards,
        "fixture_records": {str(k): v for k, v in records.items()},
        "feed_fixture_count": len(records),
        "feed_only_fixtures": extra[:80],
        "leagues": leagues,
    }
