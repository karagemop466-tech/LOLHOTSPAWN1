"""CI-only reachability probe: which candidate sources can our runner actually read?

Run by ``.github/workflows/refresh.yml`` into ``data/diag-probe.json`` (and the same evidence as
text).  It is deliberately *not* part of the pick pipeline: it changes no number on the site.  Its
only job is to record the HTTP outcome of each candidate endpoint under each client fingerprint, so
that a parser or a source decision can be justified from evidence instead of a guess, and so that a
host that starts answering 403 is noticed in the published log rather than silently dropping rows.

Every finding that matters is also mirrored into ``COORDINATION.md`` / the site's Sources page.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from .common import (BROWSER_HEADERS, CURL_UA, BOT_CONTACT_UA, JSON_HEADERS, Fetcher,
                     html_to_lines, iso, log, utcnow, write_debug, write_json)

# (label, url, kind, header preset name)  kind: "json" | "html"
CANDIDATES: list[tuple[str, str, str, str]] = [
    ("hotspawn fixtures feed — browser UA",
     "https://www.hotspawn.com/wp-json/wp/v2/fixtures?search=league%20of%20legends"
     "&per_page=3&_fields=id,slug,link,title", "json", "browser"),
    ("hotspawn fixtures feed — curl UA",
     "https://www.hotspawn.com/wp-json/wp/v2/fixtures?search=league%20of%20legends"
     "&per_page=3&_fields=id,slug,link,title", "json", "curl"),
    ("hotspawn fixtures feed — bot-contact UA",
     "https://www.hotspawn.com/wp-json/wp/v2/fixtures?search=league%20of%20legends"
     "&per_page=3&_fields=id,slug,link,title", "json", "bot"),
    ("hotspawn fixtures feed — no query string",
     "https://www.hotspawn.com/wp-json/wp/v2/fixtures?per_page=3", "json", "browser"),
    ("hotspawn tournaments taxonomy",
     "https://www.hotspawn.com/wp-json/wp/v2/tournaments?per_page=5&_fields=id,slug,name,link",
     "json", "browser"),
    ("hotspawn lobby host serving wp-json",
     "https://play.hotspawn.com/wp-json/wp/v2/fixtures?search=league%20of%20legends"
     "&per_page=3&_fields=id,slug,link,title", "json", "browser"),
    ("hotspawn league page (Worlds)",
     "https://www.hotspawn.com/league-of-legends/tournament/worlds-2026-main-event",
     "html", "browser"),
    ("hotspawn match page",
     "https://www.hotspawn.com/matches/galions-vs-solary-em-2026-summer-main-event-1081205",
     "html", "browser"),
    ("wp-json root (is the block host-wide?)",
     "https://www.hotspawn.com/wp-json/", "json", "browser"),
    ("hotspawn fixtures feed — next_events param",
     "https://www.hotspawn.com/wp-json/wp/v2/fixtures?next_events=true&per_page=3"
     "&_fields=id,slug,link,title,date", "json", "browser"),
    ("lobby page 2 (does the SSR list paginate?)",
     "https://play.hotspawn.com/lol-pickems?page=2", "html", "browser"),
    ("lobby page, wide limit param",
     "https://play.hotspawn.com/lol-pickems?limit=400&tournament=all", "html", "browser"),
    ("oddsportal LoL landing (row markup sample)",
     "https://www.oddsportal.com/esports/league-of-legends/", "html", "browser"),
    ("oddsportal LoL results page",
     "https://www.oddsportal.com/esports/league-of-legends/results/", "html", "browser"),
    ("oddsportal Worlds tournament page",
     "https://www.oddsportal.com/esports/league-of-legends/league-of-legends-world-championship/",
     "html", "browser"),
    ("polymarket closed markets",
     "https://gamma-api.polymarket.com/markets?closed=true&limit=5"
     "&order=updatedAt&ascending=false", "json", "browser"),
    ("polymarket search (Worlds)",
     "https://gamma-api.polymarket.com/public-search?q=Worlds%20League%20of%20Legends"
     "&limit_per_type=8&events_status=all", "json", "browser"),
    ("lolesports official API",
     "https://esports-api.lolesports.com/persisted/gw/getScheduledGames?"
     "hlsg=en&max=10", "json", "browser"),
    ("liquipedia api (LoL Worlds 2026)",
     "https://liquipedia.net/leagueoflegends/api.php?action=parse&page=Worlds_2026"
     "&prop=wikitext&format=json&formatversion=2", "json", "browser"),
]

PRESETS = {
    "browser": dict(BROWSER_HEADERS),
    "curl": {"User-Agent": CURL_UA, "Accept": "*/*"},
    "bot": {"User-Agent": BOT_CONTACT_UA, **JSON_HEADERS},
}


def _preview_json(body: str) -> dict:
    out: dict = {}
    try:
        data = json.loads(body)
    except Exception as exc:
        return {"parse": f"invalid json: {type(exc).__name__}", "chars": len(body)}
    out["parse"] = "ok"
    out["type"] = type(data).__name__
    if isinstance(data, list):
        out["items"] = len(data)
        if data:
            first = data[0]
            out["first_keys"] = sorted(first.keys())[:14] if isinstance(first, dict) else str(first)[:120]
            out["first_preview"] = json.dumps(first, ensure_ascii=False)[:600]
    elif isinstance(data, dict):
        out["keys"] = sorted(data.keys())[:14]
        out["first_preview"] = json.dumps(data, ensure_ascii=False)[:600]
    return out


def _preview_html(body: str) -> dict:
    out = {
        "chars": len(body),
        "markers": {
            "hotspawn /matches/ anchors": len(re.findall(r"/matches/", body)),
            "oddsportal /esports/h2h/ anchors": len(re.findall(r"/esports/h2h/", body)),
            "HH:MM UTC stamps": len(re.findall(r"\b\d{1,2}:\d{2}\s*UTC\b", body)),
            "'Finished' text": body.count("Finished") + body.count("finished"),
            "score-like 'a : b'": len(re.findall(r"\b\d{1,2}\s*[:\-]\s*\d{1,2}\b", body)),
            "__NEXT_DATA__": "__NEXT_DATA__" in body,
            "self.__next_f": "self.__next_f" in body,
        },
    }
    lines = html_to_lines(body)
    text = "\n".join(lines)
    anchor = None
    for pat in ("/esports/h2h/", "/matches/", "UTC"):
        pos = text.find(pat)
        if pos != -1:
            anchor = pos
            out["anchor_pat"] = pat
            break
    if anchor is None:
        out["text_head"] = text[:1200]
    else:
        out["text_window"] = text[max(0, anchor - 900):anchor + 1600]
    return out


def run(fetcher: Fetcher | None = None, out_dir: str = "data",
        per_host_limit: int = 3) -> dict:
    """Probe every candidate; never raise — the pipeline must still publish."""
    fetcher = fetcher or Fetcher(cache_dir=None)
    now: datetime = utcnow()
    results: list[dict] = []
    by_preset: dict[str, dict] = {}
    for label, url, kind, preset in CANDIDATES:
        headers = dict(PRESETS.get(preset, {}))
        host = re.sub(r"^www\.", "", url.split("/")[2])
        entry: dict = {"label": label, "url": url, "kind": kind, "preset": preset,
                       "host": host}
        try:
            body = fetcher.get(url, attempts=1, use_cache=False, headers=headers)
        except Exception as exc:  # defensive: never break the run
            body = None
            entry["error"] = f"{type(exc).__name__}"
        if body is None:
            entry["outcome"] = "no body (blocked, error or empty)"
        else:
            entry["outcome"] = "ok"
            entry["chars"] = len(body)
            try:
                entry.update(_preview_json(body) if kind == "json" else _preview_html(body))
            except Exception as exc:
                entry["preview_error"] = f"{type(exc).__name__}"
        by_preset.setdefault(preset + " " + host, entry["outcome"])
        results.append(entry)
        log(f"  probe {label}: {entry['outcome']}")
    report = {
        "generated_at": iso(now),
        "purpose": ("evidence for which line/result sources are reachable from a GitHub runner; "
                    "no pick depends on anything in this file"),
        "summary": by_preset,
        "results": results,
    }
    write_json(json_path(out_dir, "diag-probe.json"), report)
    txt = [f"diag probe @ {report['generated_at']}",
           "reachable: host + client fingerprint -> outcome", ""]
    for r in results:
        txt.append(f"* {r['label']}")
        txt.append(f"  {r['url']}")
        txt.append(f"  outcome={r['outcome']} chars={r.get('chars')}")
        for key in ("items", "first_preview", "text_window", "text_head", "markers", "error"):
            if key in r:
                val = r[key]
                txt.append(f"  {key}: {json.dumps(val, ensure_ascii=False)[:1800] if isinstance(val, (dict, list)) else str(val)[:1800]}")
        txt.append("")
    write_debug("diag-probe.txt", "\n".join(txt), out_dir)
    return report


def json_path(out_dir: str, name: str) -> str:
    import os
    return os.path.join(out_dir, name)


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="probe candidate line sources from this machine")
    ap.add_argument("--out", default="data", help="directory for diag-probe.json/.txt")
    ap.add_argument("--cache", default="", help="optional cache directory")
    args = ap.parse_args(argv)
    rep = run(Fetcher(cache_dir=args.cache or None), out_dir=args.out)
    ok = sum(1 for r in rep["results"] if r["outcome"] == "ok")
    print(f"diag probe: {ok}/{len(rep['results'])} endpoints returned a body")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
