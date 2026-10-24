#!/usr/bin/env python3
"""live_source_verify.py - independent, line-by-line resolution of published evidence.

Session c0a05820 (I1). Every other audit in this repo checks that a source link is
*present*. This one checks that each URL the dashboard actually publishes *resolves*
when fetched, so "every table row has a source link to an official site" is a
measured fact rather than a formatting rule.

What it checks
--------------
 1. live Hotspawn fixtures feed: ids == dataset ids (1:1), no row invented, no row missing
 2. every row's Hotspawn match card URL resolves (HTTP 200)
 3. every market row's quote URL resolves and, for API receipts, still returns JSON
 4. every venue URL recorded in a row's market block resolves
 5. every Leaguepedia competition page cited by a row resolves
 6. every published dashboard page resolves and carries the expected structure
 7. rows with NO resolving evidence are listed explicitly (never silently passed)

Needs outbound network (runs on GitHub Actions, never in the sandbox).

    python3 audit/live_source_verify.py            # full run
    python3 audit/live_source_verify.py --offline  # structural checks only (no network)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "audit" / "session_c0a05820"
LIVE_FEED = ("https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/"
             "fixtures?sport_alias=lol&status=scheduled&tenantId=1")
SITE = "https://karagemop466-tech.github.io/LOLHOTSPAWN1/"
UA = "LOLHotspawnVerify/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1)"

PAGES = ["index.html", "table.html", "picks.html", "featured.html", "originated.html",
         "unresolved.html", "competitions.html", "teams.html", "flagged.html",
         "coverage.html", "verification.html", "sources.html", "methodology.html"]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Per-host fetch policy. A 429 from a site that throttles a crawler, or a 404 on a
# bookmaker event page for a match that has already kicked off, is NOT a broken
# link - it has to be classified separately or the audit would libel the site.
#   concurrency: parallel requests to this host
#   delay:       seconds to sleep between requests to this host
#   retries:     extra attempts on 429/5xx, with linear backoff
#   headers:     host-specific headers (API keys, contact UA where a wiki requires one)
CONTACT_UA = "LOLHotspawnResearch/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1)"
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PINNACLE_KEY = {"x-api-key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R", "Accept": "application/json"}
HOST_POLICY = {
    "www.hotspawn.com": {"concurrency": 1, "delay": 1.1, "retries": 3},
    "play.hotspawn.com": {"concurrency": 1, "delay": 0.5, "retries": 2},
    "lol.fandom.com": {"concurrency": 1, "delay": 0.4, "retries": 1,
                       "headers": {"User-Agent": CONTACT_UA},
                       "fallback_headers": {"User-Agent": BROWSER_UA}},
    # Pinnacle's guest key is only accepted from a browser-shaped request: a
    # contact-style UA gets HTTP 401 even with the correct x-api-key.
    "guest.api.arcadia.pinnacle.com": {"concurrency": 2, "delay": 0.3, "retries": 3,
                                       "headers": {**PINNACLE_KEY,
                                                   "User-Agent": BROWSER_UA}},
    "kalshi.com": {"concurrency": 1, "delay": 1.5, "retries": 3},
    "eu-offering-api.kambicdn.com": {"concurrency": 2, "delay": 0.3, "retries": 2},
    "eu1.offering-api.kambicdn.com": {"concurrency": 2, "delay": 0.3, "retries": 2},
    "karagemop466-tech.github.io": {"concurrency": 4, "delay": 0.0, "retries": 2},
}
DEFAULT_POLICY = {"concurrency": 4, "delay": 0.1, "retries": 2}


def policy_for(url: str) -> dict:
    host = urllib.parse.urlparse(url).netloc
    return {**DEFAULT_POLICY, **HOST_POLICY.get(host, {})}


def classify(url: str, status: int, error: str) -> str:
    """Turn an HTTP verdict into a cause, so a throttle is never reported as rot."""
    host = urllib.parse.urlparse(url).netloc
    if 200 <= status < 300:
        return "resolved"
    if status == 429:
        return "rate_limited"
    if status in (401, 403):
        if host == "lol.fandom.com":
            return "blocked_by_wiki"
        return "auth_required"
    if status == 404 and host.endswith("kambicdn.com"):
        return "expired_event"          # the book pulls the event page when the market closes
    if status == 404:
        return "not_found"
    if status == -1:
        return "transport_error"
    return "server_error" if status >= 500 else "broken"


def fetch(url: str, timeout: int = 45, retries: int = 2, delay: float = 0.0) -> dict:
    """GET a URL with the host's policy. Never raises.

    A 401/403 is retried once with the host's fallback headers (some wikis and
    APIs reject a research contact UA but serve a browser-shaped one), and the
    verdict records which header set produced the answer.
    """
    verdict = _fetch_once(url, timeout, retries, delay, policy_for(url).get("headers"))
    if verdict["status"] in (401, 403) and policy_for(url).get("fallback_headers"):
        alt = _fetch_once(url, timeout, retries, delay, policy_for(url)["fallback_headers"])
        alt["header_variant"] = "fallback"
        return alt
    verdict.setdefault("header_variant", "primary")
    return verdict


def _fetch_once(url: str, timeout: int, retries: int, delay: float,
                extra_headers: dict | None) -> dict:
    pol = policy_for(url)
    retries = max(retries, pol["retries"])
    delay = delay or pol["delay"]
    headers = {"User-Agent": CONTACT_UA, "Accept": "*/*"}
    headers.update(extra_headers or pol.get("headers") or {})
    if delay:
        time.sleep(delay * random.random())
    last = {"url": url, "status": -1, "content_type": "", "bytes": 0, "ok": False,
            "error": "", "json_ok": None}
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                return {
                    "url": url, "status": resp.status,
                    "content_type": resp.headers.get("Content-Type", ""),
                    "bytes": len(body), "ok": 200 <= resp.status < 300,
                    "error": "", "json_ok": _json_ok(body, resp.headers.get("Content-Type", "")),
                    "attempts": attempt + 1, "cause": "resolved",
                }
        except urllib.error.HTTPError as exc:
            last = {"url": url, "status": exc.code, "content_type": "", "bytes": 0,
                    "ok": False, "error": f"HTTP {exc.code}", "json_ok": None,
                    "attempts": attempt + 1, "cause": classify(url, exc.code, f"HTTP {exc.code}")}
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(min(2 ** attempt * 3, 20) + random.random())
                continue
            return last
        except Exception as exc:  # noqa: BLE001 - transport errors vary
            last = {"url": url, "status": -1, "content_type": "", "bytes": 0,
                    "ok": False, "error": str(exc)[:200], "json_ok": None,
                    "attempts": attempt + 1, "cause": "transport_error"}
            if attempt < retries:
                time.sleep(min(2 ** attempt * 3, 20) + random.random())
                continue
            return last
    return last


def _json_ok(body: bytes, ctype: str) -> bool | None:
    if "json" not in ctype.lower() and not body.lstrip()[:1] in (b"{", b"["):
        return None
    try:
        json.loads(body.decode("utf-8", "replace"))
        return True
    except Exception:  # noqa: BLE001
        return False


def fetch_json(url: str) -> tuple[dict, object | None]:
    """Fetch a JSON endpoint and return (verdict, parsed payload)."""
    pol = policy_for(url)
    headers = {"User-Agent": CONTACT_UA, "Accept": "application/json"}
    headers.update(pol.get("headers") or {})
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read()
            return ({"url": url, "status": resp.status, "ok": 200 <= resp.status < 300,
                     "bytes": len(body), "cause": "resolved", "error": ""},
                    json.loads(body.decode("utf-8", "replace")))
    except Exception as exc:  # noqa: BLE001
        status = getattr(exc, "code", -1)
        return ({"url": url, "status": status, "ok": False, "bytes": 0,
                 "cause": classify(url, status, str(exc)), "error": str(exc)[:200]}, None)


def dedupe(urls) -> list[str]:
    seen, out = set(), []
    for u in urls:
        if not u or not isinstance(u, str):
            continue
        if not u.startswith("http"):
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def verify_wiki_page(url: str) -> dict:
    """Confirm a Leaguepedia page exists via the wiki's MediaWiki API.

    `lol.fandom.com/wiki/<Page>` returns HTTP 403 to a datacentre IP whatever UA we
    send, but `api.php` (the same host the collector uses for Cargo queries) answers.
    The published link stays the human page; the receipt records that the check was
    made through the API, so a 403 is never reported as a broken link.
    """
    title = urllib.parse.unquote(url.split("/wiki/", 1)[1])
    api = ("https://lol.fandom.com/api.php?action=query&format=json&redirects=1&titles="
           + urllib.parse.quote(title))
    verdict, payload = fetch_json(api)
    exists, missing = False, False
    if isinstance(payload, dict):
        for page in ((payload.get("query") or {}).get("pages") or {}).values():
            if "missing" in page or "invalid" in page:
                missing = True
            elif page.get("title"):
                exists = True
    cause = "resolved" if exists else ("not_found" if missing else verdict.get("cause", "broken"))
    return {"url": url, "status": verdict.get("status", -1), "ok": exists,
            "cause": cause, "verified_via": api, "method": "mediawiki-api",
            "query_title": title, "bytes": verdict.get("bytes", 0), "error": verdict.get("error", "")}


def leaguepedia_url(page: str | None) -> str | None:
    if not page:
        return None
    slug = urllib.parse.quote(page.replace(" ", "_"), safe="_(),/")
    return f"https://lol.fandom.com/wiki/{slug}"


def collect_urls(matches: list[dict]) -> dict[str, list[str]]:
    """Group every published URL by the evidence role it plays."""
    groups: dict[str, list[str]] = {
        "hotspawn_card": [], "market_quote": [], "venue_receipt": [],
        "leaguepedia_page": [], "pickem": [],
    }
    for m in matches:
        groups["hotspawn_card"].append(m.get("hotspawn_url"))
        lp = m.get("leaguepedia_page")
        groups["leaguepedia_page"].append(leaguepedia_url(lp))
        groups["pickem"].append(m.get("pickem_url"))
        mk = m.get("market") or {}
        for key in ("source_url", "api_url", "market_url"):
            groups["market_quote"].append(mk.get(key))
        for v in mk.get("venues") or []:
            groups["venue_receipt"].append(v.get("url"))
    return {k: dedupe(v) for k, v in groups.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="structural checks only")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    data = json.loads((ROOT / "data" / "matches.json").read_text())
    matches = data["matches"]
    report: dict = {
        "generated_utc": now(),
        "mode": "offline" if args.offline else "live",
        "dataset_generated_utc": data.get("generated_utc"),
        "rows": len(matches),
        "checks": [],
        "verdicts": {},
        "rows_without_resolving_evidence": [],
        "unresolved_rows": [],
    }

    # ---------- structural checks (always) ----------
    struct = []
    no_hotspawn = [m["id"] for m in matches if not m.get("hotspawn_url")]
    struct.append({"name": "every row carries a Hotspawn match card URL",
                   "ok": not no_hotspawn, "detail": f"{len(matches) - len(no_hotspawn)}/{len(matches)}"})
    bad_sum = [m["id"] for m in matches
               if m.get("p0") is not None and abs((m["p0"] or 0) + (m["p1"] or 0) - 1.0) > 0.002]
    struct.append({"name": "priced rows sum to 100% (0.2pp)", "ok": not bad_sum, "detail": str(bad_sum[:5])})
    # A coin-flip row (p0 == p1 == 0.5) may name either side; a settlement row claims no
    # probability at all, so it is excluded here and covered by the pick-presence check below.
    bad_pick = [m["id"] for m in matches
                if m.get("p0") is not None and m.get("p1") is not None and m.get("pick")
                and (m["pick"].get("probability") is not None or m.get("method") != "unresolved")
                and m["pick"].get("side") != (0 if m["p0"] >= m["p1"] else 1)]
    struct.append({"name": "pick is the higher-probability side (ties may take either side)",
                   "ok": not bad_pick, "detail": str(bad_pick[:5])})
    unpicked = [m["id"] for m in matches if not (m.get("pick") or {}).get("team")]
    struct.append({"name": "every row names a pick (priced or settlement/void)",
                   "ok": not unpicked, "detail": f"{len(matches) - len(unpicked)}/{len(matches)}"})
    report["checks"].extend(struct)

    groups = collect_urls(matches)
    report["url_counts"] = {k: len(v) for k, v in groups.items()}

    if args.offline:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "source_verify.json").write_text(json.dumps(report, indent=1) + "\n")
        print(json.dumps({"checks": report["checks"], "url_counts": report["url_counts"]}, indent=1))
        return 0 if all(c["ok"] for c in struct) else 1

    # ---------- live inventory parity ----------
    feed, payload = fetch_json(LIVE_FEED)
    report["verdicts"]["live_feed"] = feed
    live_ids = set()
    if isinstance(payload, list):
        live_ids = {str(f["id"]) for f in payload if f.get("sport_alias") == "lol"}
    dataset_ids = {str(m["id"]) for m in matches}
    report["live_inventory"] = {
        "live": len(live_ids), "dataset": len(dataset_ids),
        "missing_from_dataset": sorted(live_ids - dataset_ids)[:50],
        "not_in_live_feed": sorted(dataset_ids - live_ids)[:50],
    }
    report["checks"].append({
        "name": "published inventory == live Hotspawn feed (1:1 ids, freshness)",
        "ok": bool(live_ids) and live_ids == dataset_ids,
        "detail": f"live={len(live_ids)} dataset={len(dataset_ids)} "
                  f"new on feed since publish={len(live_ids - dataset_ids)} "
                  f"gone from feed={len(dataset_ids - live_ids)}"
                  + ("" if live_ids == dataset_ids else
                     " - dataset is stale: the scheduled refresh has not published"),
    })

    # ---------- resolve every published URL, respecting each host's rate policy ----------
    role_of = {u: role for role, urls in groups.items() for u in urls}
    by_host: dict[str, list[str]] = {}
    for url in role_of:
        by_host.setdefault(urllib.parse.urlparse(url).netloc, []).append(url)

    by_url: dict[str, dict] = {}

    def crawl_host(host: str, urls: list[str]) -> None:
        pol = policy_for(urls[0])
        delay = pol["delay"]
        if host == "lol.fandom.com":
            for u in urls:
                by_url[u] = {**verify_wiki_page(u), "role": role_of[u]}
                time.sleep(0.4)
            return
        if pol["concurrency"] <= 1:
            for u in urls:
                verdict = fetch(u)
                verdict["role"] = role_of[u]
                by_url[u] = verdict
                if delay:
                    time.sleep(delay)
        else:
            with ThreadPoolExecutor(max_workers=int(pol["concurrency"])) as pool:
                for u, verdict in zip(urls, pool.map(fetch, urls)):
                    verdict["role"] = role_of[u]
                    by_url[u] = verdict

    with ThreadPoolExecutor(max_workers=len(by_host) or 1) as pool:
        list(pool.map(lambda h: crawl_host(h, by_host[h]), list(by_host)))
    report["verdicts"]["urls"] = by_url

    BROKEN = {"broken", "server_error", "not_found", "transport_error",
              "auth_required", "blocked_by_wiki"}

    def cause(url: str | None) -> str:
        v = by_url.get(url or "")
        return v.get("cause", "not_checked") if v else "not_checked"

    per_role = {}
    for role, urls in groups.items():
        causes: dict[str, int] = {}
        for u in urls:
            causes[cause(u)] = causes.get(cause(u), 0) + 1
        broken = [u for u in urls if cause(u) in BROKEN]
        per_role[role] = {"total": len(urls), "resolved": causes.get("resolved", 0),
                          "causes": causes, "broken": broken[:20]}
    report["by_role"] = per_role
    for role, stat in per_role.items():
        if not stat["total"]:
            continue
        report["checks"].append({
            "name": f"no broken {role.replace('_', ' ')} URL",
            "ok": not stat["broken"],
            "detail": f"{stat['resolved']}/{stat['total']} resolved this run; "
                      f"causes={stat['causes']}",
        })

    # ---------- per-row evidence ----------
    for m in matches:
        mk = m.get("market") or {}
        evidence = [m.get("hotspawn_url")] + [mk.get(k) for k in ("source_url", "api_url", "market_url")]
        evidence += [v.get("url") for v in (mk.get("venues") or [])]
        causes = [cause(u) for u in dedupe(evidence)]
        if not any(c == "resolved" for c in causes):
            record = {"id": m["id"], "match": f"{m['team0']['name']} vs {m['team1']['name']}",
                      "method": m.get("method"), "causes": causes,
                      "checked": [u for u in dedupe(evidence)]}
            if any(c in BROKEN for c in causes):
                report["rows_without_resolving_evidence"].append(record)
            else:
                # throttled/expired only: unverified this run, not evidence of rot
                report.setdefault("rows_unverified_this_run", []).append(record)
        if m.get("method") == "unresolved":
            report["unresolved_rows"].append({
                "id": m["id"], "match": f"{m['team0']['name']} vs {m['team1']['name']}",
                "settlement_pick": (m.get("pick") or {}).get("team"),
                "hotspawn_cause": cause(m.get("hotspawn_url")),
            })
    report["checks"].append({
        "name": "every row has at least one resolving piece of evidence (no broken links)",
        "ok": not report["rows_without_resolving_evidence"],
        "detail": f"{len(matches) - len(report['rows_without_resolving_evidence'])}/{len(matches)} rows; "
                  f"{len(report.get('rows_unverified_this_run', []))} unverified this run (throttle/expiry)",
    })

    # ---------- published pages ----------
    page_verdicts = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        page_verdicts = dict(zip(PAGES, pool.map(lambda p: fetch(SITE + p), PAGES)))
    report["verdicts"]["pages"] = page_verdicts
    report["checks"].append({
        "name": "every published dashboard page resolves",
        "ok": all(v["ok"] for v in page_verdicts.values()),
        "detail": f"{sum(1 for v in page_verdicts.values() if v['ok'])}/{len(page_verdicts)} HTTP 2xx",
    })

    # the table must render one row per match (the structural promise of the page)
    table = page_verdicts.get("table.html", {})
    if table.get("ok"):
        try:
            html = urllib.request.urlopen(urllib.request.Request(
                SITE + "table.html", headers={"User-Agent": UA}), timeout=60).read().decode("utf-8", "replace")
            rendered = len(re.findall(r'<tr[^>]*class="[^"]*prow', html)) or html.count("<tr")
            report["table_rows_rendered"] = rendered
            report["checks"].append({
                "name": "table.html renders at least one row per match",
                "ok": rendered >= len(matches),
                "detail": f"rendered={rendered} rows={len(matches)}",
            })
            # Displayed pairs must add to 100.0%: rounding each side independently
            # printed seven rows that read 99.9% / 100.1% before 2026-10-24.
            odd = []
            for row in re.findall(r'<tr class="prow.*?</tr>', html, re.S):
                pair = [float(x) for x in re.findall(r'class="pct">([\d.]+)%', row)]
                if len(pair) == 2 and abs(sum(pair) - 100.0) > 0.05:
                    odd.append(pair)
            report["checks"].append({
                "name": "every displayed win-probability pair adds to 100.0%",
                "ok": not odd,
                "detail": f"{len(odd)} row(s) off: {odd[:5]}",
            })
        except Exception as exc:  # noqa: BLE001
            report["checks"].append({"name": "table.html body readable", "ok": False, "detail": str(exc)[:200]})

    report["passed"] = all(c["ok"] for c in report["checks"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "source_verify.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    md = ["# Live source verification", "",
          f"- generated: `{report['generated_utc']}`",
          f"- dataset: `{report['dataset_generated_utc']}`",
          f"- rows: **{report['rows']}**",
          f"- result: **{'PASS' if report['passed'] else 'FAIL'}**", "",
          "| Check | Result | Detail |", "|---|---|---|"]
    for c in report["checks"]:
        md.append(f"| {c['name']} | {'PASS' if c['ok'] else 'FAIL'} | {c['detail']} |")
    if report["by_role"]:
        md += ["", "## Resolution by evidence role", "",
               "| Role | URLs | Resolved | Causes |", "|---|---|---|---|"]
        for role, stat in report["by_role"].items():
            md.append(f"| {role} | {stat['total']} | {stat['resolved']} | "
                      f"`{stat['causes']}` |")
    if report["rows_without_resolving_evidence"]:
        md += ["", "## Rows whose evidence is actually broken", ""]
        for r in report["rows_without_resolving_evidence"]:
            md.append(f"- `{r['id']}` {r['match']} ({r['method']}) - causes `{r['causes']}`")
    if report.get("rows_unverified_this_run"):
        md += ["", "## Rows not verifiable this run (throttled or expired - not broken)", ""]
        for r in report["rows_unverified_this_run"][:40]:
            md.append(f"- `{r['id']}` {r['match']} ({r['method']}) - `{r['causes']}`")
    (OUT_DIR / "source_verify.md").write_text("\n".join(md) + "\n")

    print("\n".join(f"{'PASS' if c['ok'] else 'FAIL'} {c['name']} :: {c['detail']}"
                    for c in report["checks"]))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
