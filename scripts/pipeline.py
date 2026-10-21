"""End-to-end pipeline: scrape Hotspawn -> attach external lines -> originate model lines.

    python -m scripts.pipeline --out data [--offline] [--no-lines]

Outputs (all committed so the site can be served by GitHub Pages without a build step):

* ``data/hotspawn.json``     raw collection + debug dumps (lobby parse, league fixtures, results)
* ``data/lines.json``        external market lines + source probe ledger
* ``data/ratings.json``      the team ratings the model produced
* ``data/picks.json``        one row per Hotspawn LoL pick'em, with probability + sources
* ``data/picks.csv``         the same table flattened for spreadsheet review
* ``data/unresolved.json``   every pick that could not be resolved, with the reason
* ``data/flags.json``        irregularities / verification failures that need a human
* ``data/sources.json``      per-host fetch ledger + probe verdicts
* ``data/summary.json``      numbers the executive summary is written from
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import traceback
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import hotspawn as hs                                    # noqa: E402
from scripts import lines as LN                                       # noqa: E402
from scripts import model as MD                                        # noqa: E402
from scripts.common import (                                          # noqa: E402
    Fetcher, canon_team, iso, log, pct, read_json, slugify, team_match, utcnow, write_json,
)

CRON_HOURS = 6  # keep in sync with .github/workflows/refresh.yml


# --------------------------------------------------------------------------- helpers
TITLE_TEAMS = re.compile(r"^\s*(.+?)\s+vs\.?\s+(.+?)\s+(?:League of Legends match|League of Legends)",
                         re.I)


def title_teams(title: str | None) -> list[str] | None:
    """Team labels as published in Hotspawn's own fixture record (authoritative)."""
    if not title:
        return None
    m = TITLE_TEAMS.search(re.sub(r"\s+", " ", title))
    if not m:
        return None
    return [m.group(1).strip(), m.group(2).strip()]


def norm_slug_names(slug: str, tournament: str | None = None) -> list[str]:
    """Team labels implied by a Hotspawn match slug: ``galions-vs-solary-<event-slug>-<id>``.

    Only used when the fixture record has no title.  The trailing tournament slug is stripped so
    the second label is a team, not a team plus half an event name.
    """
    if not slug:
        return []
    head = re.sub(r"-\d{5,9}$", "", slug)
    parts = re.split(r"-vs-|-v-|-versus-", head, maxsplit=1)
    if len(parts) != 2:
        return []
    away = parts[1]
    if tournament:
        ts = slugify(tournament)
        if away.endswith(ts):
            away = away[: -len(ts)].rstrip("-")
        else:
            for cut in ("-league-of-legends-", "-match-at-"):
                if cut in away:
                    away = away.split(cut)[0]
    return [parts[0].replace("-", " "), away.replace("-", " ")] if away else [parts[0].replace("-", " ")]


def lobby_status(kickoff_iso: str | None, now: datetime) -> str:
    kick = None
    try:
        kick = datetime.fromisoformat(kickoff_iso.replace("Z", "+00:00")) if kickoff_iso else None
    except Exception:
        kick = None
    if kick is None:
        return "unknown"
    delta = kick - now
    if delta.total_seconds() <= 0:
        return "locked"
    if delta.total_seconds() <= 3 * 3600:
        return "closing soon"
    if delta.total_seconds() <= 24 * 3600:
        return "today"
    return "upcoming"


def kickoff_from_league(card: dict, league_fixtures: dict) -> tuple[str | None, bool, str]:
    """Return (kickoff_iso, verified, source_label).

    The lobby only exposes a relative countdown, so the absolute ``HH:MM UTC`` stamp on
    Hotspawn's own league page is preferred whenever the fixture appears there.
    """
    fid = card.get("fixture_id")
    derived = card.get("kickoff_utc")
    lf = league_fixtures.get(str(fid)) or league_fixtures.get(fid) if fid else None
    feed = (lf or {}).get("league_kickoff_utc")
    if feed and derived:
        try:
            a = datetime.fromisoformat(derived.replace("Z", "+00:00"))
            b = datetime.fromisoformat(feed.replace("Z", "+00:00"))
            drift = abs((a - b).total_seconds())
            if drift <= 900:
                return feed, True, "hotspawn league page (HH:MM UTC) — matches lobby countdown"
            return feed, False, ("MISMATCH: league page and lobby countdown disagree by "
                                 f"{int(drift // 60)} min — league page used, flagged")
        except Exception:
            return feed, False, "league page only (unparseable lobby countdown)"
    if feed:
        return feed, False, "hotspawn league page only"
    return derived, False, "lobby countdown only (approximate, ±1 min)"


# --------------------------------------------------------------------------- resolve
def resolve(collected: dict, lines_data: dict, model_data: dict) -> dict:
    now = utcnow()
    cards = collected.get("matches") or []
    fixture_records = collected.get("fixture_records") or {}
    leagues = collected.get("leagues") or {}

    league_fixtures: dict[str, dict] = {}
    results: list[dict] = []
    for slug, data in leagues.items():
        for row in data.get("fixtures") or []:
            key = str(row.get("fixture_id"))
            if key not in league_fixtures or not league_fixtures[key].get("league_kickoff_utc"):
                league_fixtures[key] = {**row, "league_slug": slug}
        for res in data.get("results") or []:
            results.append({**res, "league_slug": slug})

    ratings, ratings_meta = MD.build_ratings(results) if results else ({}, {"teams": {}})
    model_probs, model_notes = MD.predict(cards, ratings, ratings_meta) if ratings else ({}, {"unrateable": [], "unrateable_count": 0})

    market = lines_data.get("attach") or {}
    market_flags = lines_data.get("flags") or []

    picks: list[dict] = []
    unresolved: list[dict] = []
    flags: list[dict] = []
    seen_ids: set = set()

    for card in cards:
        fid = card.get("fixture_id")
        teams = card.get("teams") or []
        if fid and fid in seen_ids:
            continue
        if fid:
            seen_ids.add(fid)
        rec = fixture_records.get(str(fid)) or fixture_records.get(fid) or {}
        kickoff, verified_kickoff, kickoff_src = kickoff_from_league(card, league_fixtures)
        status = lobby_status(kickoff, now)

        feed_teams = title_teams(rec.get("wp_title"))
        slug_teams = norm_slug_names(card.get("fixture_slug"), card.get("lobby_tournament"))
        expected = feed_teams or (slug_teams if len(slug_teams) == 2 else None)
        name_checks = []
        if expected:
            for idx, team in enumerate(teams[:2]):
                ok = team_match(team, expected[idx]) if idx < len(expected) else False
                name_checks.append({
                    "field": f"team[{idx}]",
                    "value": team,
                    "expected": expected[idx],
                    "ok": ok,
                    "source_url": rec.get("wp_link") or card.get("match_url"),
                    "note": "lobby label vs Hotspawn fixture record title" if feed_teams
                            else "lobby label vs Hotspawn match-page URL slug",
                })
                if not ok:
                    flags.append({
                        "match": " vs ".join(teams), "fixture_id": fid,
                        "field": f"team[{idx}]",
                        "reason": (f"lobby label {team!r} does not match the fixture record "
                                   f"label {expected[idx]!r}"),
                        "source_url": card.get("match_url"),
                    })

        checks = [{
            "field": "fixture_exists",
            "value": "yes" if rec else "no",
            "ok": bool(rec),
            "source_url": rec.get("wp_link") or card.get("match_url"),
            "note": "Hotspawn WordPress fixture feed (public REST record for this match id)",
        }] + name_checks + [{
            "field": "kickoff_utc",
            "value": kickoff,
            "ok": bool(verified_kickoff),
            "source_url": (league_fixtures.get(str(fid)) or {}).get("league_url"),
            "note": kickoff_src,
        }]
        if not rec:
            flags.append({"match": " vs ".join(teams), "fixture_id": fid,
                          "field": "fixture_exists",
                          "reason": ("no fixture record returned by Hotspawn's public feed for this "
                                     "id — match page listed in lobby only, left unverified"),
                          "source_url": card.get("match_url")})
        if not verified_kickoff:
            flags.append({"match": " vs ".join(teams), "fixture_id": fid, "field": "kickoff_utc",
                          "reason": f"kickoff not cross-checked: {kickoff_src}",
                          "source_url": (league_fixtures.get(str(fid)) or {}).get("league_url")})
        for note in card.get("parse_notes") or []:
            flags.append({"match": " vs ".join(teams), "fixture_id": fid, "field": "lobby_parse",
                          "reason": note, "source_url": card.get("match_url")})

        key = LN.pair_key(teams[0] if teams else None, teams[1] if len(teams) > 1 else None)
        mkt = market.get(key)
        mdl = model_probs.get(key)
        row_model = None
        if mdl:
            row_model = {k: v for k, v in mdl.items()}
        row_market = None
        if mkt:
            prim = mkt["primary"]
            flip = False
            # the source row may list the away team first; orient to the lobby's team order
            src_teams = prim.get("teams") or []
            if len(src_teams) == 2 and len(teams) == 2 and team_match(src_teams[0], teams[1]) \
                    and not team_match(src_teams[0], teams[0]):
                flip = True
            ph, pa = prim.get("devig_home"), prim.get("devig_away")
            if flip:
                ph, pa = pa, ph
            row_market = {
                "prob_home": round(ph, 4) if ph is not None else None,
                "prob_away": round(pa, 4) if pa is not None else None,
                "odds_home": prim.get("odds_home"),
                "odds_away": prim.get("odds_away"),
                "implied_home_raw": prim.get("implied_home_raw"),
                "implied_away_raw": prim.get("implied_away_raw"),
                "market": prim.get("market"),
                "source_label": prim.get("source_label"),
                "source_url": prim.get("url"),
                "fetched_utc": prim.get("fetched_utc"),
                "source_spread": mkt.get("source_spread"),
                "all_sources": [{"source": a.get("source"), "url": a.get("url"),
                                 "prob_home": a.get("devig_home"), "prob_away": a.get("devig_away"),
                                 "odds": [a.get("odds_home"), a.get("odds_away")],
                                 "label": a.get("source_label")} for a in mkt.get("all_sources") or []],
                "orientation": "flipped to lobby order" if flip else "as published",
            }

        prob_home = prob_away = None
        basis = None
        basis_detail = None
        if row_market and row_market.get("prob_home") is not None:
            prob_home, prob_away = row_market["prob_home"], row_market["prob_away"]
            basis = "market"
            basis_detail = f"de-vigged {row_market['source_label'].split(' — ')[0]} price"
        elif row_model and row_model.get("confidence") not in (None, "none"):
            prob_home, prob_away = row_model["prob_home"], row_model["prob_away"]
            basis = "model"
            basis_detail = (f"self-originated series Elo ({row_model['rating_home']:.0f} vs "
                            f"{row_model['rating_away']:.0f}); confidence {row_model['confidence']}")
        else:
            reason_bits = []
            if not row_market:
                reason_bits.append("no price found on Polymarket or the esports books probed")
            if row_market and not row_model:
                reason_bits.append("price found but no model fallback needed")
            if not row_model:
                unr = (model_notes.get("unrateable") or [])
                why = next((u.get("reason") for u in unr if u.get("fixture_id") == fid), None)
                reason_bits.append(why or "no verifiable recent scorelines for either team")
            flags.extend(mkt for mkt in [])
            reason = "; ".join(dict.fromkeys(reason_bits))
            unresolved.append({
                "match": " vs ".join(teams) or "(unparsed card)",
                "fixture_id": fid,
                "hotspawn_url": card.get("match_url"),
                "tournament": card.get("lobby_tournament"),
                "tier": card.get("tier"),
                "kickoff_utc": kickoff,
                "reason": reason,
                "model_available": bool(row_model),
                "market_available": bool(row_market),
                "next_step": ("needs a human line, or a results feed that covers this league — "
                              "see methodology §Limitations"),
            })
            basis = "unresolved"
            basis_detail = reason

        row = {
            "id": f"{'hs' if fid else 'lobby'}-{fid or card.get('lobby_index')}",
            "hotspawn_fixture_id": fid,
            "hotspawn_url": card.get("match_url"),
            "hotspawn_feed_url": rec.get("wp_link"),
            "hotspawn_feed_title": rec.get("wp_title"),
            "lobby_url": collected.get("lobby_url"),
            "league_page_url": (league_fixtures.get(str(fid)) or {}).get("league_url"),
            "tournament": card.get("lobby_tournament"),
            "tier": card.get("tier"),
            "points": card.get("points"),
            "multiplier": card.get("multiplier"),
            "stage": card.get("stage"),
            "kickoff_utc": kickoff,
            "kickoff_verified": verified_kickoff,
            "kickoff_source": kickoff_src,
            "status": status,
            "teams": [{"name": t, "slot": "home" if i == 0 else "away",
                       "hotspawn_pick_pct": (card.get("hotspawn_pick_pct") or [None, None])[i],
                       "canon": canon_team(t)} for i, t in enumerate(teams[:2])],
            "basis": basis,
            "basis_detail": basis_detail,
            "prob_home": prob_home,
            "prob_away": prob_away,
            "pick_home": prob_home,
            "pick_away": prob_away,
            "market": row_market,
            "model": row_model,
            "verification": {"checks": checks, "all_ok": all(c.get("ok") for c in checks)},
        }
        if prob_home is not None:
            row["pick_team"] = teams[0] if prob_home >= prob_away else teams[1]
            row["pick_prob"] = max(prob_home, prob_away)
            row["value_vs_hotspawn"] = None  # deliberately not computed from pick share
        else:
            row["pick_team"] = None
            row["pick_prob"] = None
        picks.append(row)

    for f in market_flags:
        flags.append({**f, "field": f.get("field") or "line"})

    return {
        "generated_at": iso(now),
        "picks": picks,
        "unresolved": unresolved,
        "flags": flags,
        "ratings": {"teams": ratings_meta.get("teams", {}),
                    "params": ratings_meta.get("params", {}),
                    "results_used": ratings_meta.get("results_used", 0),
                    "results_skipped": ratings_meta.get("results_skipped", 0)},
        "model_notes": model_notes,
        "collected_totals": collected.get("totals"),
        "feed_fixture_count": collected.get("feed_fixture_count"),
        "feed_only_count": len(collected.get("feed_only_fixtures") or []),
        "leagues": {slug: {"tournament_name": d.get("tournament_name"),
                          "fixtures": len(d.get("fixtures") or []),
                          "results": len(d.get("results") or [])} for slug, d in leagues.items()},
    }


# --------------------------------------------------------------------------- csv
CSV_COLS = [
    "kickoff_utc", "status", "tournament", "tier", "points", "team_home", "team_away",
    "prob_home", "prob_away", "pick_team", "pick_prob", "basis", "basis_detail",
    "market_source", "market_url", "odds_home", "odds_away",
    "model_confidence", "model_rating_home", "model_rating_away", "model_evidence_urls",
    "hotspawn_url", "hotspawn_feed_url", "league_page_url",
    "hotspawn_pick_pct_home", "hotspawn_pick_pct_away",
    "kickoff_verified", "fixture_confirmed", "unresolved_reason",
]


def write_csv(picks: list[dict], unresolved: list[dict], path: str) -> None:
    by_id = {u.get("fixture_id"): u for u in unresolved}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_COLS)
    for row in picks:
        teams = row.get("teams") or []
        mkt = row.get("market") or {}
        mdl = row.get("model") or {}
        unres = by_id.get(row.get("hotspawn_fixture_id")) or {}
        checks = {c.get("field"): c for c in (row.get("verification") or {}).get("checks", [])}
        w.writerow([
            row.get("kickoff_utc"), row.get("status"), row.get("tournament"), row.get("tier"),
            row.get("points"),
            teams[0]["name"] if len(teams) > 0 else "",
            teams[1]["name"] if len(teams) > 1 else "",
            row.get("prob_home"), row.get("prob_away"), row.get("pick_team"), row.get("pick_prob"),
            row.get("basis"), row.get("basis_detail"),
            mkt.get("source_label"), mkt.get("source_url"), mkt.get("odds_home"), mkt.get("odds_away"),
            mdl.get("confidence"), mdl.get("rating_home"), mdl.get("rating_away"),
            " ".join(mdl.get("evidence_urls") or [])[:600],
            row.get("hotspawn_url"), row.get("hotspawn_feed_url"), row.get("league_page_url"),
            teams[0].get("hotspawn_pick_pct") if len(teams) > 0 else "",
            teams[1].get("hotspawn_pick_pct") if len(teams) > 1 else "",
            "yes" if row.get("kickoff_verified") else "no",
            "yes" if checks.get("fixture_exists", {}).get("ok") else "no",
            unres.get("reason", ""),
        ])
    from scripts.common import write_text
    write_text(path, buf.getvalue())


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--offline", action="store_true",
                    help="reuse committed data/*.json (no network) — used to rebuild the site only")
    ap.add_argument("--no-lines", action="store_true", help="skip external line sources")
    ap.add_argument("--no-probes", action="store_true")
    ap.add_argument("--shallow", action="store_true", help="skip the full-feed completeness scan")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    fetcher = Fetcher(cache_dir=os.path.join(args.out, "cache"))
    crash = os.path.join(args.out, "pipeline-error.txt")

    def guard(stage, fn):
        """A failing stage must never publish a half-truth, but it must also never hide why."""
        try:
            return fn(), None
        except Exception as exc:
            text = f"{stage} failed: {type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            log(f"!! {text.splitlines()[0]}")
            from scripts.common import write_text
            write_text(crash, text)
            print(text, file=sys.stderr)
            return None, text

    if args.offline:
        collected = read_json(os.path.join(args.out, "hotspawn.json"), {"matches": []})
        lines_data = read_json(os.path.join(args.out, "lines.json"), {})
    else:
        log("1/4 Hotspawn collection")
        collected, err = guard("hotspawn collection",
                               lambda: hs.collect(fetcher, out_dir=args.out, deep=not args.shallow))
        if collected is None:
            collected = {"matches": [], "error": err.splitlines()[0] if err else "collection failed"}
        write_json(os.path.join(args.out, "hotspawn.json"), collected)

        lines_data = {"oddsportal": {}, "polymarket": {}, "rows": [], "markets": []}
        if not args.no_lines:
            log("2/4 external market lines")
            queries = ["league of legends", "worlds 2026 lol", "league of legends worlds"]
            tourney_names = sorted({(c.get("lobby_tournament") or "") for c in collected.get("matches", [])})
            queries += [t for t in tourney_names if t][:25]
            op_res, _ = guard("OddsPortal", lambda: LN.collect_oddsportal(fetcher))
            rows, op_meta = op_res if op_res else ([], {"status": "collector crashed"})
            pm_res, _ = guard("Polymarket", lambda: LN.collect_polymarket(fetcher, queries[:20]))
            markets, pm_meta = pm_res if pm_res else ([], {"status": "collector crashed"})
            attach, attach_flags = LN.attach(markets, rows, collected.get("matches") or [])
            # Keep the payload reviewable: every row that attached to a fixture, plus a
            # transparency sample, instead of the full market firehose.
            lobby_names = set()
            for card in collected.get("matches") or []:
                for t in card.get("teams") or []:
                    lobby_names.add(canon_team(t))

            def relevant(mk):
                outs = [canon_team(o) for o in (mk.get("outcomes") or [])]
                return bool(set(outs) & lobby_names)

            keep = [mk for mk in markets if relevant(mk)]
            lines_data = {
                "generated_at": iso(utcnow()),
                "oddsportal": op_meta, "polymarket": pm_meta,
                "rows": rows,
                "markets": keep[:60],
                "market_counts": {"polymarket_total": len(markets),
                                   "polymarket_matching_a_lobby_team": len(keep),
                                   "oddsportal_rows": len(rows),
                                   "oddsportal_rows_with_price": sum(
                                       1 for r in rows if r.get("odds"))},
                "attach": attach, "attach_flags": attach_flags,
            }
        else:
            lines_data["attach"], lines_data["attach_flags"] = {}, []
            lines_data.setdefault("market_counts", {})
        if not args.no_probes:
            log("3/4 probing esports books / other line sources")
            probes, _ = guard("source probes", lambda: LN.probe_sources(fetcher))
            lines_data["probes"] = probes or []
        else:
            lines_data.setdefault("probes", [])
        write_json(os.path.join(args.out, "lines.json"), lines_data)

    log("4/4 resolving picks")
    resolved, err = guard("resolve", lambda: resolve(collected, lines_data, {}))
    if resolved is None:
        print(f"FATAL: resolve crashed; nothing published. {err}", file=sys.stderr)
        return 2
    resolved.setdefault("flags", [])
    write_json(os.path.join(args.out, "picks.json"), {
        "generated_at": resolved["generated_at"],
        "source": {"lobby": collected.get("lobby_url"), "totals": resolved.get("collected_totals"),
                   "feed_fixture_count": resolved.get("feed_fixture_count")},
        "picks": resolved["picks"],
    })
    write_json(os.path.join(args.out, "ratings.json"), resolved["ratings"])
    write_json(os.path.join(args.out, "unresolved.json"), {
        "generated_at": resolved["generated_at"],
        "count": len(resolved["unresolved"]),
        "items": resolved["unresolved"],
        "limitations": limitations(resolved, lines_data),
    })
    write_json(os.path.join(args.out, "flags.json"), {
        "generated_at": resolved["generated_at"],
        "count": len(resolved["flags"]),
        "items": resolved["flags"],
    })
    write_json(os.path.join(args.out, "sources.json"), {
        "generated_at": iso(utcnow()),
        "hosts": fetcher.ledger(),
        "probes": lines_data.get("probes") or [],
        "oddsportal": (lines_data.get("oddsportal") or {}),
        "polymarket": (lines_data.get("polymarket") or {}),
    })
    write_csv(resolved["picks"], resolved["unresolved"], os.path.join(args.out, "picks.csv"))
    summary = build_summary(resolved, lines_data)
    write_json(os.path.join(args.out, "summary.json"), summary)

    print(json.dumps(summary["headline"], indent=2))
    return 0


def limitations(resolved: dict, lines_data: dict) -> list[dict]:
    """Documented, data-driven limitations for the unresolved bucket."""
    probes = lines_data.get("probes") or []
    blocked = [p for p in probes if "no parseable" in p.get("verdict", "") or
               "unreachable" in p.get("verdict", "") or "no machine-readable" in p.get("verdict", "")]
    n_unres = len(resolved.get("unresolved") or [])
    leagues = resolved.get("leagues") or {}
    thin = sorted((s for s, d in leagues.items() if (d.get("results") or 0) < 3))
    return [
        {"title": "No published price exists for most of these leagues",
         "detail": ("Sub-tier LoL (national 2nd/3rd divisions, regional championships, academy "
                    "leagues) is not listed by Polymarket and is only sporadically listed by "
                    "sportsbook odds-comparison pages. Where no price exists the row falls back to "
                    "our own Elo line; where not even that exists it is listed as unresolved."),
         "affected_rows": n_unres},
        {"title": "Esports books probed but not usable programmatically",
         "detail": ("These were tried and are reported exactly as they responded, so the gap is "
                    "visible rather than hidden."),
         "sources": [{"label": p.get("label"), "url": p.get("url"), "result": p.get("verdict")}
                     for p in blocked],
         "affected_rows": None},
        {"title": "Some leagues publish too few finished series to rate a team",
         "detail": ("The Elo model needs completed, scored series. Leagues with fewer than three "
                    "verifiable finished series cannot produce a defensible rating for both teams."),
         "leagues": thin, "affected_rows": None},
        {"title": "Hotspawn's own pick share is excluded on purpose",
         "detail": ("The lobby's “X% picked” is a crowd-vote percentage, not a probability, and the "
                    "brief rules it out as a probability source. It is shown next to our number for "
                    "comparison only and is never an input."),
         "affected_rows": None},
        {"title": "Roster, patch and veto information is not published for these tiers",
         "detail": ("Our own line is a form/strength model. It cannot account for roster swaps, "
                    "stand-ins or patch swings in amateur leagues, which is why low-sample rows are "
                    "labelled “very low” confidence rather than being presented as a priced line."),
         "affected_rows": None},
    ]


def build_summary(resolved: dict, lines_data: dict) -> dict:
    picks = resolved["picks"]
    basis_counts = {}
    tier_counts = {}
    league_counts = {}
    for row in picks:
        basis_counts[row.get("basis") or "?"] = basis_counts.get(row.get("basis") or "?", 0) + 1
        tier_counts[row.get("tier") or "unlabelled"] = tier_counts.get(row.get("tier") or "unlabelled", 0) + 1
        lg = row.get("tournament") or "unlabelled"
        league_counts[lg] = league_counts.get(lg, 0) + 1
    conf = {}
    for row in picks:
        if row.get("basis") == "model":
            c = (row.get("model") or {}).get("confidence") or "?"
            conf[c] = conf.get(c, 0) + 1
    total = len(picks)
    resolved_n = basis_counts.get("market", 0) + basis_counts.get("model", 0)
    return {
        "generated_at": resolved["generated_at"],
        "refresh_hours": CRON_HOURS,
        "headline": {
            "matches_on_hotspawn_lol_lobby": total,
            "picks_resolved": resolved_n,
            "from_market_lines": basis_counts.get("market", 0),
            "from_our_own_model": basis_counts.get("model", 0),
            "unresolved": basis_counts.get("unresolved", 0),
            "coverage_pct": round(100.0 * resolved_n / total, 1) if total else 0.0,
            "leagues": len(league_counts),
            "rated_teams": len((resolved.get("ratings") or {}).get("teams") or {}),
            "verified_results_used": (resolved.get("ratings") or {}).get("results_used", 0),
            "flags": len(resolved["flags"]),
            "lobby_reported_totals": resolved.get("collected_totals"),
            "feed_only_fixtures": resolved.get("feed_only_count"),
        },
        "basis_counts": basis_counts,
        "tier_counts": tier_counts,
        "league_counts": dict(sorted(league_counts.items(), key=lambda kv: -kv[1])),
        "model_confidence": conf,
        "sources": {
            "oddsportal_rows": len(lines_data.get("rows") or []),
            "polymarket_markets": len(lines_data.get("markets") or []),
            "probes": [{"label": p.get("label"), "url": p.get("url"), "verdict": p.get("verdict")}
                       for p in (lines_data.get("probes") or [])],
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
