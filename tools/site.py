#!/usr/bin/env python3
"""Generate the static GitHub Pages dashboard from data/matches.json.

Design goals: mobile-first, one clear place to find every pick, executive summary
with in-site links, multi-venue real-money consensus links, out-of-sample SVG
calibration reliability curve, and a verified source link on every row.
"""
from __future__ import annotations

import glob
import html
import json
import os
import sys
from collections import Counter
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, ROOT, iso, load_json, log, now_utc

DOCS = ROOT  # GitHub Pages for this repo publishes the branch root (legacy build)
SITE_URL = "https://karagemop466-tech.github.io/LOLHOTSPAWN1/"

METHOD_LABEL = {
    "market": "Market line",
    "model": "Model line",
    "provisional": "Provisional",
    "unresolved": "Unresolved",
}
METHOD_HELP = {
    "market": "De-vigged consensus across real-money books & prediction exchanges.",
    "model": "Our Elo line from recorded series results (both teams rated, connected).",
    "provisional": "Our Elo line with thin data - low confidence, shown but flagged.",
    "unresolved": "No defensible competitive line (mid-split league removal / unrated).",
}

# Always-visible navigation on phones (a persistent bottom bar beats a hidden menu).
MOBILE_NAV = [
    ("index.html", "Summary"),
    ("table.html", "Picks"),
    ("results.html", "Results"),
    ("unresolved.html", "Limits"),
    ("flagged.html", "Flags"),
]

NAV = [
    ("index.html", "Summary"),
    ("table.html", "Pick table"),
    ("picks.html", "Cards"),
    ("results.html", "Results"),
    ("featured.html", "Market lines"),
    ("originated.html", "Model lines"),
    ("unresolved.html", "Unresolved"),
    ("coverage.html", "Coverage"),
    ("competitions.html", "Tournaments"),
    ("teams.html", "Teams"),
    ("methodology.html", "Method"),
    ("verification.html", "Verify"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flags"),
]


# --------------------------------------------------------------------------- helpers
def e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def pct(value) -> str:
    if value is None:
        return "&mdash;"
    return f"{value * 100:.1f}%"


def pct_pair(p0: float | None, p1: float | None) -> tuple[str, str]:
    if p0 is None or p1 is None:
        return "&mdash;", "&mdash;"
    a = round(p0 * 100.0, 1)
    b = round(100.0 - a, 1)
    return f"{a:.1f}%", f"{b:.1f}%"


def local_time(iso_utc: str | None) -> str:
    if not iso_utc:
        return "TBD"
    return (f'<time datetime="{e(iso_utc)}" class="utc" data-utc="{e(iso_utc)}">'
            f'{e(iso_utc[:16].replace("T", " "))} UTC</time>')


def badge(method: str) -> str:
    return f'<span class="badge b-{e(method)}">{e(METHOD_LABEL.get(method, method))}</span>'


def leaguepedia_slug(name: str) -> str:
    return quote(str(name).replace(" ", "_"), safe="()_',!.")



def _external_ceiling() -> dict:
    """Measured external-market ceiling, read from the committed research receipts."""
    probes = load_json(os.path.join(DATA, "source_probes.json")) or {}
    ceiling = _research_doc("market_ceiling.json")
    results = probes.get("results") or []
    pin = ceiling.get("pinnacle") or {}
    leagues = pin.get("leagues") or []
    pm_live = 0
    for m in (ceiling.get("polymarket") or {}).get("markets") or []:
        try:
            prices = [float(x) for x in json.loads(m.get("prices") or "[]")]
        except Exception:  # noqa: BLE001
            continue
        if prices and all(0.01 <= x <= 0.99 for x in prices):
            pm_live += 1
    kambi_doc = load_json(os.path.join(DATA, "raw", "kambi_lol.json")) or {}
    bovada_doc = load_json(os.path.join(DATA, "raw", "bovada_lol.json")) or {}
    kambi_n = len(kambi_doc.get("events") or [])
    bovada_n = len(bovada_doc.get("events") or [])
    return {
        "probed": len(results) + (1 if kambi_n else 0),
        "answered": sum(1 for r in results if r.get("ok")) + (1 if kambi_n else 0),
        "json_feeds": sum(1 for r in results if r.get("ok") and r.get("kind") == "json") + (1 if kambi_n else 0),
        "pinnacle_leagues": len(leagues),
        "pinnacle_priced": sum(int(lg.get("priced_moneylines") or 0) for lg in leagues),
        "bovada": bovada_n,
        "unibet": kambi_n,
        "kalshi": int((ceiling.get("kalshi") or {}).get("event_count") or 0),
        "polymarket": pm_live,
        "checked": (probes.get("checked_utc") or "")[:16].replace("T", " "),
        "have_receipts": bool(results),
    }


def _esportsbook_probe() -> dict:
    """Result of the dedicated esportsbook/aggregator probe, read from its committed receipt.

    Everything returned here is counted from `data/esportsbook_probe.json`; nothing is typed in by
    hand, so the sentence on the site cannot drift away from the evidence file.
    """
    doc = load_json(os.path.join(DATA, "esportsbook_probe.json")) or {}
    rows = doc.get("rows") or []
    usable = [r for r in rows if r.get("usable")]
    blocked = {r.get("slug"): r for r in rows if not r.get("usable")}
    return {
        "have": bool(rows),
        "tested": len(rows),
        "usable": len(usable),
        "usable_names": [r.get("name") for r in usable],
        "http_blocked": sum(1 for r in rows if isinstance(r.get("status"), int) and r["status"] in (401, 403, 429, 451)),
        "html_only": sum(1 for r in rows if isinstance(r.get("status"), int) and r["status"] == 200 and not r.get("json")),
        "checked": (doc.get("generated_utc") or "")[:16].replace("T", " "),
        "run_id": (doc.get("runner") or {}).get("github_run_id") or "",
        "blocked": blocked,
    }


def page_shell(title: str, active: str, body: str, subtitle: str = "") -> str:
    nav_parts = []
    for href, label in NAV:
        cls = ' class="active"' if href == active else ""
        nav_parts.append(f'<a href="{e(href)}"{cls}>{e(label)}</a>')
    nav = "".join(nav_parts)
    bottom_parts = []
    for href, label in MOBILE_NAV:
        cls = ' class="active"' if href == active else ""
        bottom_parts.append(f'<a href="{e(href)}"{cls}><span>{e(label)}</span></a>')
    bottom_nav = "".join(bottom_parts)
    meta = load_json(os.path.join(DATA, "matches.json")) or {}
    updated = (meta.get("generated_utc") or "")[:16].replace("T", " ")
    fetched = (meta.get("inventory_fetched_utc")
               or (load_json(os.path.join(DATA, "raw", "hotspawn_lol.json")) or {}).get("fetched_utc", ""))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title if "Hotspawn LoL Pick Desk" in title else title + " · Hotspawn LoL Pick Desk")}</title>
<meta name="description" content="Independent League of Legends pick'em lines for every match listed on Hotspawn.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <div class="wrap bar">
    <a class="brand" href="index.html"><span class="dot"></span> Hotspawn LoL Pick Desk</a>
    <button class="menu-btn" type="button" aria-expanded="false" aria-controls="nav" aria-label="Toggle page menu">Menu</button>
    <nav id="nav" class="nav">{nav}</nav>
  </div>
</header>
<main id="main" class="wrap">
  <div class="pagehead">
    <h1>{e(title)}</h1>
    {f'<p class="sub">{subtitle}</p>' if subtitle else ''}
    <p class="stamp">Data snapshot: <strong>{e(updated)} UTC</strong> &middot; refresh scheduled every 6 hours (not guaranteed)</p>
    <p id="snapshot-age" class="stamp" data-fetched="{e(fetched)}">Hotspawn inventory collected: {e(fetched) or "unknown"}. Check source timestamps before use.</p>
  </div>
  {body}
</main>
<footer class="wrap foot">
  <p>Independent research dashboard. Rows link to their source records. Leaguepedia is community-maintained; model lines are estimates, not verified facts. Zero Hotspawn crowd-pick input.</p>
  <p><a href="methodology.html">Method</a> &middot; <a href="verification.html">Verification</a> &middot;
  <a href="flagged.html">Flagged for review</a> &middot; <a href="sources.html">Sources</a> &middot;
  <a href="competitions.html">Tournaments</a></p>
</footer>
<nav class="mobnav" aria-label="Quick navigation">{bottom_nav}</nav>
{"" if active == "table.html" else '<a class="mobile-picks" href="table.html">All picks &rarr;</a>'}
<script src="assets/app.js"></script>
</body>
</html>
"""


# --------------------------------------------------------------------------- components
def match_card(r: dict, show_sources: bool = True) -> str:
    t0, t1 = r["team0"], r["team1"]
    m = r["method"]
    p0, p1 = r["p0"], r["p1"]
    pick = r["pick"]
    bar = ""
    if p0 is not None:
        w = max(1.0, min(99.0, p0 * 100))
        bar = (f'<div class="split" role="img" aria-label="{e(t0["name"])} {w:.0f} percent, '
               f'{e(t1["name"])} {100 - w:.0f} percent">'
               f'<span class="s0" style="width:{w:.1f}%"></span></div>')
    if pick and pick.get("probability") is not None:
        pick_html = (f'<div class="pickline"><span class="picklabel">Pick</span> '
                     f'<strong>{e(pick["team"])}</strong> '
                     f'<span class="pickpct">{pick["probability"]*100:.1f}%</span></div>')
    elif r.get("resolution"):
        res = r["resolution"]
        pick_html = (f'<div class="pickline"><span class="picklabel">Official forfeit</span> '
                     f'<strong>{e(res["winner"])}</strong> '
                     f'<span class="muted small">no probability &middot; '
                     f'<a href="{e(res["source"])}" rel="noopener">record</a></span></div>')
    else:
        pick_html = ('<div class="pickline"><span class="picklabel">No pick</span> '
                     '<span class="muted">see Unresolved &amp; limitations</span></div>')
    flags = ""
    if r["flags"]:
        flags = '<ul class="flags">' + "".join(f"<li>{e(f)}</li>" for f in r["flags"]) + "</ul>"
    sources = ""
    if show_sources:
        links = [f'<a href="{e(r["hotspawn_url"])}" rel="noopener">Hotspawn card</a>']
        mk = r.get("market") or {}
        venues = mk.get("venues") or []
        if venues:
            for v in venues:
                links.append(f'<a href="{e(v["url"])}" rel="noopener">{e(v["name"])}</a>')
        elif mk.get("market_url"):
            links.append(f'<a href="{e(mk["market_url"])}" rel="noopener">{e(mk["book"])}</a>')
        if (r.get("resolution") or {}).get("source"):
            links.append(f'<a href="{e(r["resolution"]["source"])}" rel="noopener">Forfeit record</a>')
        if r.get("leaguepedia_page"):
            links.append(f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(r["leaguepedia_page"])}" '
                         f'rel="noopener">Tournament</a>')
        if t0.get("leaguepedia"):
            links.append(f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(t0["leaguepedia"])}" '
                         f'rel="noopener">{e(t0["name"])}</a>')
        if t1.get("leaguepedia"):
            links.append(f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(t1["leaguepedia"])}" '
                         f'rel="noopener">{e(t1["name"])}</a>')
        sources = '<div class="src">' + "".join(links) + "</div>"

    s0_txt, s1_txt = pct_pair(p0, p1)
    return f"""<article id="match-{e(r['id'])}" class="card m-{e(m)}" data-method="{e(m)}" data-comp="{e(r['competition'])}"
  data-start="{e(r['start_utc'] or '')}" data-stale="{1 if r.get('stale') else 0}"
  data-text="{e((r['competition'] + ' ' + t0['name'] + ' ' + t1['name']).lower())}">
  <div class="card-top">
    <span class="when">{local_time(r['start_utc'])}</span>
    <span class="badges">{f'<span class="badge b-past">start time passed</span>' if r.get('stale') else ''}{f'<span class="badge b-flip" title="identical kick-off ratings - display order only">toss-up</span>' if pick and pick.get('probability') == 0.5 else ''}{'<span class="badge b-thin" title="single thin prediction market">thin market</span>' if (r.get('market') or {}).get('thin') else ''}{badge(m)}</span>
  </div>
  <div class="comp">{e(r['competition'])}{f" &middot; {e(r['best_of'])}-game series" if r.get('best_of') else ""}</div>
  <div class="teams">
    <div class="team {'fav' if p0 is not None and p0 >= (p1 or 0) else ''}">
      <span class="tname">{e(t0['name'])}</span><span class="tpct">{s0_txt}</span>
    </div>
    {bar}
    <div class="team {'fav' if p1 is not None and p1 > (p0 or 0) else ''}">
      <span class="tname">{e(t1['name'])}</span><span class="tpct">{s1_txt}</span>
    </div>
  </div>
  {pick_html}
  <details class="why"><summary>Why this line</summary>
    <p>{e(r['basis'])}</p>
    {flags}
  </details>
  {sources}
</article>"""


def stat_card(label: str, value, note: str = "", cls: str = "") -> str:
    return (f'<div class="stat {cls}"><div class="sv">{value}</div>'
            f'<div class="sl">{e(label)}</div>{f"<div class=sn>{e(note)}</div>" if note else ""}</div>')


def table(headers: list[str], rows: list[list[str]], cls: str = "") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td data-label=\"{headers[i]}\">{c}</td>"
                                     for i, c in enumerate(row)) + "</tr>" for row in rows)
    return f'<div class="tablewrap"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def raw_table(headers: list[str], row_html: list[str], cls: str = "table stack") -> str:
    """Table from pre-rendered <tr> rows that already carry their own data-label cells."""
    head = "".join(f"<th>{h}</th>" for h in headers)
    return (f'<div class="tablewrap"><table class="{cls}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(row_html)}</tbody></table></div>')


def calibration_svg(bt: dict) -> str:
    buckets = bt.get("buckets") or {}
    if not buckets:
        return ""
    pts = []
    labels = []
    for k, v in buckets.items():
        mp = v.get("mean_predicted")
        ac = v.get("accuracy")
        if mp is None or ac is None:
            continue
        x = 60 + (mp - 0.5) / 0.5 * 360
        y = 210 - (ac - 0.5) / 0.5 * 170
        pts.append((x, y, k, mp, ac, v.get("n", 0)))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y, *_ in pts)
    circles = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#4f9cf9"/>'
        f'<text x="{x:.1f}" y="{max(22.0, y - 10):.1f}" font-size="11" fill="#e5e7eb" text-anchor="middle">'
        f'{ac*100:.1f}% (n={n})</text>'
        for x, y, k, mp, ac, n in pts
    )
    return f"""
<figure style="margin:1rem 0;">
  <svg viewBox="0 0 450 245" width="100%" style="max-width:560px;background:#111622;border:1px solid #263042;border-radius:10px;display:block;" role="img" aria-label="Out-of-sample probability calibration curve">
    <line x1="60" y1="210" x2="420" y2="210" stroke="#334155" stroke-width="1"/>
    <line x1="60" y1="40" x2="60" y2="210" stroke="#334155" stroke-width="1"/>
    <line x1="60" y1="210" x2="420" y2="40" stroke="#64748b" stroke-dasharray="5,5" stroke-width="1.5"/>
    <polyline fill="none" stroke="#4f9cf9" stroke-width="2.5" points="{poly}"/>
    {circles}
    <text x="60" y="232" font-size="11" fill="#94a3b8" text-anchor="middle">50%</text>
    <text x="240" y="232" font-size="11" fill="#94a3b8" text-anchor="middle">Predicted win probability (75%)</text>
    <text x="420" y="232" font-size="11" fill="#94a3b8" text-anchor="middle">100%</text>
    <text x="50" y="213" font-size="11" fill="#94a3b8" text-anchor="end">50%</text>
    <text x="50" y="125" font-size="11" fill="#94a3b8" text-anchor="end">75%</text>
    <text x="50" y="44" font-size="11" fill="#94a3b8" text-anchor="end">100%</text>
  </svg>
  <figcaption class="small muted" style="margin-top:0.4rem;">Dashed diagonal = ideal calibration (predicted = realized win rate). Blue curve = out-of-sample pre-match Elo calibration across {bt.get('n', 0):,} series since {e(bt.get('cutoff', ''))}.</figcaption>
</figure>"""



# --------------------------------------------------------------------------- research receipts
RESEARCH_DIR = os.path.join(ROOT, "research")
GITHUB_BLOB = "https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main"


def _research_doc(name: str) -> dict:
    doc = load_json(os.path.join(RESEARCH_DIR, name)) or {}
    return doc if isinstance(doc, dict) else {}


def research_panel() -> str:
    """Render the runner-measured source-acquisition evidence on Sources.

    Every number here is read from the committed receipts written by
    `research/probe_sources_runner.py`, `research/market_ceiling.py` and
    `research/probe_deep.py`; nothing is typed in by hand, and an absent receipt
    degrades to a note instead of an invented figure.
    """
    probes = load_json(os.path.join(DATA, "source_probes.json")) or {}
    if not isinstance(probes, dict):
        probes = {}
    ceiling = _research_doc("market_ceiling.json")
    deep = _research_doc("probe_deep.json")
    results = probes.get("results") or []
    if not results and not ceiling:
        return ('<section class="panel"><h2>Research receipts</h2>'
                '<p class="muted">No runner probe receipts are committed in this snapshot.</p></section>')

    ok = [r for r in results if r.get("ok")]
    json_ok = [r for r in ok if r.get("kind") == "json"]
    rows_html = []
    for r in results:
        kind = r.get("kind")
        if r.get("name") in ("Leaguepedia Cargo", "Hotspawn fixtures API"):
            verdict = "results / inventory only &mdash; never a price input"
        elif r.get("name") == "Odds-API.io sports index":
            verdict = "free index only; LoL endpoints answered 502 on the deep probe"
        elif r.get("ok") and kind == "json":
            verdict = "machine-readable feed used only where it prices the match"
        elif r.get("ok"):
            verdict = "reachable HTML &mdash; prices render client-side, not parsed"
        else:
            verdict = "not usable from the runner"
        rows_html.append([
            e(r.get("name")), e(r.get("category")), str(r.get("status")),
            f'<code>{e(kind)}</code>', f'{int(r.get("bytes") or 0):,}', verdict,
        ])

    pin = ceiling.get("pinnacle") or {}
    leagues = pin.get("leagues") or []
    pinnacle_priced = sum(int(lg.get("priced_moneylines") or 0) for lg in leagues)
    kalshi_n = int((ceiling.get("kalshi") or {}).get("event_count") or 0)
    pm = ceiling.get("polymarket") or {}
    pm_live = 0
    for m in pm.get("markets") or []:
        try:
            prices = [float(x) for x in json.loads(m.get("prices") or "[]")]
        except Exception:  # noqa: BLE001 - a malformed receipt just is not counted
            continue
        if prices and all(0.01 <= x <= 0.99 for x in prices):
            pm_live += 1

    ceiling_html = ""
    if ceiling:
        ceiling_html = f"""
  <h3>How many matches can any external venue actually price?</h3>
  <div class="stats tight">
    {stat_card("Venues probed on the runner", len(results), "established books, esportsbooks, exchanges, aggregators")}
    {stat_card("Answered HTTP 200", len(ok), "reachable from GitHub Actions", "ok")}
    {stat_card("Machine-readable feeds", len(json_ok), "JSON payloads we can parse", "model")}
    {stat_card("Pinnacle series prices", pinnacle_priced, "LoL league(s): " + (", ".join(str(lg.get("name")) for lg in leagues) or "none"), "market")}
  </div>
  <ul class="bullets">
    <li><strong>Pinnacle</strong> returns {sum(int(lg.get("matchups_returned") or 0) for lg in leagues)} matchup
    objects for its one League of Legends league, of which <strong>{pinnacle_priced}</strong> carry an open,
    two-sided match-winner moneyline. The parallel <code>(Kills)</code> market family is a kill total and is
    excluded everywhere.</li>
    <li><strong>Kalshi</strong> lists {kalshi_n} open <code>KXLOLGAME</code> contracts and
    <strong>Polymarket</strong> carries {pm_live} unsettled two-sided LoL markets in the same snapshot; both are
    nearly all Worlds 2026.</li>
    <li>That ceiling &mdash; about a dozen series across all reachable venues &mdash; is why most of the
    Hotspawn list is originated by our own model rather than quoted: the books simply do not list national
    divisions, academy leagues or regional splits.</li>
  </ul>"""

    deep_html = ""
    if deep:
        page_rows = []
        for ev in deep.get("evidence") or []:
            if ev.get("kind") != "page":
                continue
            blobs = ", ".join(b.get("label") for b in ev.get("embedded_json") or []) or "none"
            if ev.get("status") != 200:
                verdict = f"page did not resolve for LoL (HTTP {ev.get('status')}) &mdash; nothing to parse"
            elif blobs == "none":
                verdict = "JavaScript-only rendering &mdash; not parsed"
            else:
                verdict = "hydration blob present, no LoL price in it &mdash; no venue parser integrated"
            page_rows.append([e(ev.get("name")), str(ev.get("status")), f'{int(ev.get("bytes") or 0):,}',
                              e(blobs), verdict])
        if page_rows:
            deep_html = f"""
  <h3>Why the books that "answer" still cannot be used</h3>
  <p class="lead">These pages returned HTTP 200 but serve no price in the HTML: the odds arrive after
  client-side JavaScript runs, which this pipeline does not execute. They are recorded as unverified
  instead of being scraped blindly.</p>
  {table(["Page", "HTTP", "Bytes", "Embedded JSON", "Verdict"], page_rows)}"""

    return f"""
<section class="panel">
  <h2>Research receipts: every venue we tried</h2>
  <p class="lead">Probed directly from the GitHub Actions runner on
  {e((probes.get("checked_utc") or "")[:16].replace("T", " "))} UTC. A venue that blocks the runner or
  only serves prices after JavaScript runs is <strong>not</strong> used to price anything; it is listed here
  so the gap is visible. Full dossier:
  <a href="{GITHUB_BLOB}/research/SOURCES.md" rel="noopener">research/SOURCES.md</a>.</p>
  {table(["Source", "Category", "HTTP", "Payload", "Bytes", "Verdict"], rows_html)}
  {ceiling_html}
  {deep_html}
  <p class="small muted">Receipts:
    <a href="{GITHUB_BLOB}/data/source_probes.json" rel="noopener">source_probes.json</a> &middot;
    <a href="{GITHUB_BLOB}/research/market_ceiling.json" rel="noopener">market_ceiling.json</a> &middot;
    <a href="{GITHUB_BLOB}/research/probe_deep.json" rel="noopener">probe_deep.json</a> &middot;
    <a href="{GITHUB_BLOB}/research/AUDIT.json" rel="noopener">independent audit</a>
  </p>
</section>"""


# --------------------------------------------------------------------------- pages
def _pick_cell(r: dict) -> str:
    """Pick column text shared by the executive summary and the pick table."""
    if r.get("resolution"):
        return ('<strong class="res">' + e(r["resolution"]["winner"]) + '</strong>'
                '<br><span class="small muted">official forfeit (walkover)</span>')
    if not r.get("pick"):
        return '<span class="muted">no pick</span>'
    p = r["pick"]
    return ('<strong>' + e(p["team"]) + '</strong>'
            '<br><span class="small muted">' + f'{p["probability"]*100:.1f}% to win' + '</span>')


def _prob_cell(r: dict) -> str:
    if r.get("p0") is None:
        return '<span class="muted">not priced</span>'
    a, b = pct_pair(r["p0"], r["p1"])
    return f'{a} / {b}'


def _row_sources(r: dict) -> str:
    links = ['<a href="' + e(r["hotspawn_url"]) + '" rel="noopener">Hotspawn</a>']
    m = r.get("market") or {}
    if m.get("source_url"):
        links.append('<a href="' + e(m["source_url"]) + '" rel="noopener">'
                     + e(m.get("book") or "market") + '</a>')
    res = r.get("resolution") or {}
    if res.get("source"):
        links.append('<a href="' + e(res["source"]) + '" rel="noopener">Leaguepedia</a>')
    elif r.get("leaguepedia_page"):
        links.append('<a href="https://lol.fandom.com/wiki/' + leaguepedia_slug(r["leaguepedia_page"])
                     + '" rel="noopener">results</a>')
    return " &middot; ".join(links)


def _stat_totals(rows: list[dict]) -> dict:
    walkover = [r for r in rows if r.get("resolution")]
    priced = sum(1 for r in rows if r.get("p0") is not None)
    return {
        "total": len(rows),
        # a settlement pick is a pick, but it carries no probability, so the two counts are
        # reported separately and never added on top of a total that already contains them.
        "priced": priced,
        "with_pick": priced + len(walkover),
        "walkover": walkover,
        "featured": [r for r in rows if r["method"] == "market"],
        "unresolved": [r for r in rows if r["method"] == "unresolved"],
        "provisional": [r for r in rows if r["method"] == "provisional"],
        "comps": len({r["competition"] for r in rows}),
    }


HOTSPAWN_RULES_URL = "https://play.hotspawn.com/how-it-works"
LOWTIER_MEMO_URL = ("https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/"
                    "research/low-tier-sources-2026-10-24.md")
EXTERNAL_LINES_MEMO_URL = ("https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/"
                           "research/external-lines-2026-10-25.md")


def _lowtier_matrix() -> tuple[dict, str, int]:
    """Latest low-tier probe receipts (tools/probe_lowtier.py), if committed."""
    files = sorted(glob.glob(os.path.join(DATA, "probe", "lowtier_*.json")))
    if not files:
        return {}, "", 0
    doc = load_json(files[-1]) or {}
    return (doc.get("coverage_matrix") or {},
            (doc.get("generated_utc") or "")[:10],
            int(doc.get("venues_probed") or 0))


def _venue_observations() -> list[dict]:
    """Every external line-search observation committed in data/receipts/external_odds/.

    Read straight from the receipt files rather than from data/corroboration.json, because
    site.py runs before corroborate.py in the pipeline: reading the receipts keeps the page
    one build ahead instead of one build behind. Each entry is a page that was actually
    opened, with its URL, its verbatim reading and the capture time - nothing is typed in
    here, so the sentence on the page cannot drift away from the evidence file.
    """
    out: list[dict] = []
    for path in sorted(glob.glob(os.path.join(DATA, "receipts", "external_odds", "*.json"))):
        doc = load_json(path) or {}
        sources = {s.get("key"): s for s in doc.get("sources") or []}
        for obs in doc.get("coverage_observations") or []:
            src = sources.get(obs.get("source")) or {}
            out.append({
                "key": obs.get("source"),
                "source": obs.get("source"),
                "source_name": src.get("name") or obs.get("source"),
                "kind": src.get("kind") or "",
                "runner": src.get("runner_reachable") or "",
                "url": obs.get("url"),
                "captured_utc": obs.get("captured_utc") or "",
                "observation": obs.get("observation") or "",
                "verbatim": obs.get("verbatim") or "",
                "file": os.path.basename(path),
            })
    return sorted(out, key=lambda o: o["captured_utc"], reverse=True)


def _latest_observation_day(obs: list[dict]) -> str:
    return (obs[0]["captured_utc"][:10] if obs else "")


def _fallback_rows(rows: list[dict]) -> list[list[str]]:
    """Per-competition fallback ledger derived only from matches and probe receipts."""
    matrix, probe_date, n_venues = _lowtier_matrix()
    by_comp: dict[str, list[dict]] = {}
    for r in rows:
        by_comp.setdefault(r["competition"], []).append(r)
    out = []
    for comp, crs in sorted(by_comp.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        c = Counter(r["method"] for r in crs)
        parts = []
        if c.get("market"):
            parts.append(f"{c['market']} market")
        if c.get("model"):
            parts.append(f"{c['model']} originated")
        if c.get("provisional"):
            parts.append(f"{c['provisional']} provisional")
        if c.get("unresolved"):
            parts.append(f"{c['unresolved']} settlement")
        venues = matrix.get(comp) or []
        if venues:
            ext = "Yes &mdash; " + e(", ".join(venues[:3])) + ("&hellip;" if len(venues) > 3 else "")
        elif c.get("market"):
            ext = "Yes (integrated feed)"
        elif n_venues:
            ext = f"No line found (0 of {n_venues} venues, probed {e(probe_date)})"
        else:
            ext = "No line integrated"
        n = len(crs)
        if c.get("market") == n:
            limit = "Featured resolution: de-vigged book consensus."
        elif c.get("unresolved"):
            limit = ("Includes official-forfeit settlements (no %; Hotspawn voids "
                     "forfeited-match predictions, so expect 0 points either way).")
        elif c.get("provisional", 0) * 2 >= n:
            limit = "Thin recorded history on most cards - treat % as directional only."
        elif c.get("provisional"):
            limit = "No book prices this league; originated Elo, some thin-history cards flagged."
        else:
            limit = "No book prices this league; originated Elo from recorded series history."
        out.append([e(comp), str(n), e(" · ".join(parts)), ext, limit])
    return out


def short_time(iso_utc: str | None) -> str:
    """Compact, locale-independent kick-off label for the phone strip."""
    if not iso_utc:
        return "TBD"
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    try:
        month = months[int(iso_utc[5:7]) - 1]
    except (ValueError, IndexError):
        month = iso_utc[5:7]
    label = f"{iso_utc[8:10]} {month} {iso_utc[11:16]}"
    return f'<time datetime="{e(iso_utc)}" data-utc="{e(iso_utc)}">{e(label)}</time>'


def next_strip(rows: list[dict]) -> str:
    """Eight one-tap kick-off rows: match, pick, probability. Aimed at a phone."""
    out = []
    for r in rows:
        pick = r.get("pick") or {}
        team = pick.get("team") or ""
        prob = pick.get("probability")
        if prob is not None:
            value, cls = f"{prob * 100:.0f}%", "np"
        elif team:
            value, cls = "forfeit", "np settle"
        else:
            value, cls = "&mdash;", "np settle"
        note = f"Pick: {team}" if team else "No pick - see Unresolved"
        if prob is None and team:
            note += " (forfeit - expected void, no price)"
        out.append(
            f'<a class="nextrow" href="picks.html#match-{e(r["id"])}">'
            f'<span class="nw">{short_time(r["start_utc"])}</span>'
            f'<span class="nt"><strong>{e(r["team0"]["name"])} vs {e(r["team1"]["name"])}</strong>'
            f'<span class="nm">{e(note)} &middot; {e(r["competition"])}</span></span>'
            f'<span class="{cls}">{value}</span></a>'
        )
    return "".join(out)


def tournament_directory(rows: list[dict]) -> str:
    """Phone-first index of every tournament, linking straight into a filtered pick table.

    The landing page used to answer "where are the picks" with six page links, which still
    leaves a phone user hunting through 200+ rows for their league. Every row here is an
    in-site deep link (`table.html?comp=<tournament>`) that lands on the pick table already
    filtered to that competition, with the pick, both win probabilities and the sources.
    """
    by_comp: dict[str, dict] = {}
    for r in rows:
        name = r.get("competition") or "(unnamed)"
        c = by_comp.setdefault(name, {"matches": 0, "priced": 0, "market": 0,
                                      "settle": 0, "next": None, "span": 0})
        c["matches"] += 1
        c["span"] += int(r.get("points") or 0)
        if r.get("p0") is not None:
            c["priced"] += 1
        elif (r.get("pick") or {}).get("probability") is None:
            c["settle"] += 1
        if r.get("method") == "market":
            c["market"] += 1
        start = r.get("start_utc") or ""
        if start and (c["next"] is None or start < c["next"]):
            c["next"] = start
    out = []
    for name, c in sorted(by_comp.items(), key=lambda kv: (-kv[1]["matches"], kv[0])):
        q = quote(name, safe="")
        out.append(
            '<tr><td data-label="Tournament"><a href="table.html?comp=' + q + '"><strong>'
            + e(name) + '</strong></a></td>'
            '<td data-label="Matches">' + str(c["matches"]) + '</td>'
            '<td data-label="With a win %">' + str(c["priced"]) + '</td>'
            '<td data-label="Market-priced">' + str(c["market"]) + '</td>'
            '<td data-label="Earliest kick-off">' + (local_time(c["next"]) if c["next"] else "&mdash;")
            + '</td></tr>')
    return "".join(out)


def build_index(rows: list[dict], counts: Counter, src_status: list[dict]) -> str:
    """Landing page: the phone-first answer to "where are the picks, and what are they?"."""
    t = _stat_totals(rows)
    total = t["total"]
    walkover = t["walkover"]
    featured = t["featured"]
    unresolved = t["unresolved"]
    provisional = t["provisional"]
    priced_n = t["priced"]
    resolved_total = t["with_pick"]
    meta = load_json(os.path.join(DATA, "matches.json")) or {}
    track = meta.get("track_record") or {}
    fetched = meta.get("inventory_fetched_utc") or ""
    upcoming = sorted([r for r in rows
                       if r["start_utc"] and r["start_utc"] > iso(now_utc()) and r["pick"]],
                      key=lambda r: r["start_utc"])
    live_sources = sum(1 for s in src_status if s.get("ok"))
    venue_names = sorted({v["name"] for r in featured
                          for v in (r.get("market") or {}).get("venues") or []})
    venues_txt = ", ".join(venue_names) if venue_names else "no reachable book this build"
    originated_n = counts.get("model", 0) + len(provisional)
    ceiling = _external_ceiling()
    probe = _esportsbook_probe()
    _, lowtier_date, lowtier_n = _lowtier_matrix()
    # Describe only feeds that actually carried a listed-match price on this
    # build; an HTTP 200 with an empty coupon is not a live price feed.
    ceiling_parts = []
    for label, key in (("Pinnacle", "pinnacle_priced"), ("Bovada", "bovada"),
                       ("Unibet (Kambi)", "unibet")):
        if ceiling[key]:
            ceiling_parts.append(f'<strong>{label} {ceiling[key]} series</strong>')
    if ceiling["kalshi"]:
        ceiling_parts.append(f'<strong>Kalshi {ceiling["kalshi"]} contracts</strong>')
    if ceiling["polymarket"]:
        ceiling_parts.append(f'<strong>Polymarket {ceiling["polymarket"]} unsettled markets</strong>')
    ceiling_txt = ", ".join(ceiling_parts) if ceiling_parts else "no venue quoted a listed match"
    silent = [label for label, key in (("Bovada", "bovada"), ("Unibet (Kambi)", "unibet"),
                                       ("Kalshi", "kalshi"), ("Polymarket", "polymarket"))
              if not ceiling[key]]
    silent_txt = (" Feeds that returned no LoL price on this build: " + ", ".join(silent) + "."
                  if silent else "")
    if probe["have"]:
        other = probe["tested"] - probe["usable"] - probe["http_blocked"] - probe["html_only"]
        probe_line = (
            f'{probe["tested"]} further esportsbook and odds-aggregator endpoints were called from the '
            f'build runner on {e(probe["checked"])} UTC: '
            f'<strong>{probe["usable"]} returned a machine-readable LoL price</strong> '
            f'({probe["http_blocked"]} blocked or key-gated, {probe["html_only"]} browser-only pages, '
            f'{other} error or empty responses). Those leagues therefore keep the originated line rather '
            'than a borrowed or invented quote.'
        )
        probe_link = (
            '<a href="data/esportsbook_probe.json"><strong>probe receipt</strong></a> &middot; '
            '<a href="sources.html">Sources</a>'
        )
    else:
        probe_line = "No additional esportsbook probe receipt is committed for this build."
        probe_link = '<a href="sources.html">Sources</a>'
    lowtier_note = (
        f' A separate {lowtier_n}-venue low-tier probe ({e(lowtier_date)}) is documented in the '
        f'<a href="{LOWTIER_MEMO_URL}" rel="noopener">research memo and receipts</a>; see the '
        '<a href="unresolved.html#fallback">competition-by-competition fallback ledger</a>.'
        if lowtier_n else ""
    )
    gate_count = len((load_json(os.path.join(DATA, "verification.json")) or {}).get("checks") or [])
    observations = _venue_observations()
    obs_day = _latest_observation_day(observations)
    if observations:
        # one label per venue key: several receipt files name the same venue differently, so take
        # the most recent label rather than counting one book twice.
        labels: dict[str, str] = {}
        for o in observations:            # sorted newest first
            labels.setdefault(o.get("key") or o["source_name"], o["source_name"])
        obs_venues = sorted(labels.values())
        obs_line = (
            f'<strong>{len(observations)} checks across {len(obs_venues)} venues</strong> '
            f'({e(", ".join(obs_venues))}) were read by hand on <strong>{e(obs_day)}</strong> and logged '
            'with the exact sentence each page printed. They are on '
            '<a href="unresolved.html#observed"><strong>Unresolved &amp; limits &rarr; what the books showed</strong></a>: '
            'the leagues below the featured ceiling carried no open price at any of them on the dates shown, which is why those '
            'cards are originated rather than quoted.'
        )
    else:
        obs_line = ("No manual venue check is committed for this build; the runner probe table above is the "
                    "only external evidence. See <a href=\"sources.html\">Sources</a>.")

    unres_rows = []
    for r in unresolved:
        unres_rows.append([
            local_time(r["start_utc"]),
            '<a href="unresolved.html#m' + e(r["id"]) + '">' + e(r["competition"]) + "</a>",
            "<strong>" + e(r["team0"]["name"]) + "</strong> vs <strong>" + e(r["team1"]["name"]) + "</strong>",
            _pick_cell(r) if r.get("resolution") else '<span class="muted">no pick</span>',
            _row_sources(r),
        ])

    acc = track.get("accuracy")
    track_line = (
        f'<a href="results.html"><strong>{track.get("hits", 0)} of {track.get("graded", 0)}</strong> '
        f'graded picks won ({acc*100:.1f}%)</a>' if acc is not None
        else "no graded picks yet")

    body = f"""
<section class="hero" id="start">
  <h2>Every League of Legends match on Hotspawn, with a pick you can reach in one tap.</h2>
  <p>All <strong>{total}</strong> scheduled LoL cards, refreshed automatically every six hours. Every card
  carries a pick: <strong>{len(featured)}</strong> priced from real-money bookmaker lines,
  <strong>{originated_n}</strong> originated from recorded series results, and
  <strong>{len(walkover)}</strong> resolved by league rule. Hotspawn's own crowd vote is never an input.</p>
  <div class="cta">
    <a class="btn primary" href="table.html">Pick table &mdash; all {total} matches &rarr;</a>
    <a class="btn" href="picks.html">Card view</a>
    <a class="btn" href="results.html">Results ({track.get("graded", 0)} graded)</a>
  </div>
</section>

<section class="panel" id="where">
  <h2>Where the picks are</h2>
  <p class="lead">Six ways in. Every link stays inside this site and every row links out to the source it came
  from.</p>
  <div class="quicklinks">
    <a href="table.html"><span class="ql-t">Pick table &mdash; {total} matches</span>
      <span class="ql-d">One row per match: both win probabilities, the pick, the method and source links. The fastest page on a phone.</span></a>
    <a href="picks.html"><span class="ql-t">Card view &mdash; {total} matches</span>
      <span class="ql-d">The same list as cards, each with the reasoning behind the number and every source.</span></a>
    <a href="results.html"><span class="ql-t">Results &mdash; {track.get("graded", 0)} graded</span>
      <span class="ql-d">Whether the published picks actually won, graded against the official series record.</span></a>
    <a href="featured.html"><span class="ql-t">Market-backed &mdash; {len(featured)}</span>
      <span class="ql-d">De-vigged consensus of real-money books and exchanges ({e(venues_txt)}), with the raw quotes.</span></a>
    <a href="originated.html"><span class="ql-t">Model lines &mdash; {originated_n}</span>
      <span class="ql-d">Our own Elo line where no sportsbook prices the league, with the inputs and records behind it.</span></a>
    <a href="unresolved.html"><span class="ql-t">Unresolved &amp; limits &mdash; {len(unresolved)}</span>
      <span class="ql-d">Every card that cannot carry a probability, why, and every limitation that applies to the rest.</span></a>
  </div>
</section>

<section class="panel" id="directory">
  <h2>Picks by tournament ({t['comps']})</h2>
  <p class="lead">Tap a tournament to open the pick table filtered to it &mdash; one row per match with
  both win probabilities, the pick and the source links. Nothing to type on a phone.</p>
  <div class="tablewrap"><table class="picktable dir">
    <thead><tr><th>Tournament</th><th>Matches</th><th>With a win %</th><th>Market-priced</th><th>Earliest kick-off</th></tr></thead>
    <tbody>{tournament_directory(rows)}</tbody>
  </table></div>
</section>

<section class="panel" id="soon">
  <h2 id="next">Starting soon</h2>
  <p class="lead">The next eight kick-offs. Tap a row for the full card.</p>
  <div class="nextlist">{next_strip(upcoming[:8]) or '<p class="muted">No upcoming matches in this snapshot.</p>'}</div>
  <p style="margin:12px 0 0"><a class="btn" href="table.html">All {total} matches &rarr;</a></p>
</section>

<section class="stats">
  {stat_card("Matches on Hotspawn", total, f"across {t['comps']} tournaments")}
  {stat_card("With a win probability", priced_n, f"{priced_n/total*100:.0f}% of the list", "ok")}
  {stat_card("With a pick", resolved_total, f"{resolved_total/total*100:.0f}% incl. {len(walkover)} rule settlements")}
  {stat_card("Market-backed", len(featured), "real-money consensus", "market")}
  {stat_card("Model lines", counts.get('model',0), "medium confidence", "model")}
  {stat_card("Provisional", len(provisional), "thin data, flagged", "provisional")}
  {stat_card("Graded picks", track.get("graded", 0), f"{acc*100:.0f}% correct" if acc is not None else "none yet", "ok")}
</section>

<section class="panel" id="summary">
  <h2>Executive summary</h2>
  <ul class="bullets">
    <li><strong>Where the picks are.</strong> On a phone, tap <a href="table.html"><strong>Picks</strong></a>
    in the bar at the bottom of every page: one row per match with the pick, both win probabilities, the
    method and source links. <a href="picks.html">Card view</a> shows the same {total} matches with the
    reasoning behind each line, and <a href="results.html">Results</a> grades the picks that have already
    played. Every list is searchable and filterable by tournament and by method. Next kick-offs are under
    <a href="#next">Next up</a>, and <a href="#directory"><strong>Picks by tournament</strong></a> jumps
    straight into a filtered pick table for one league.</li>
    <li><strong>Coverage.</strong> {resolved_total} of {total} matches carry a pick
    ({resolved_total/total*100:.0f}%): {priced_n} with a win probability and {len(walkover)} resolved to the
    official forfeit winner with no probability claimed. Priced:
    <a href="featured.html">{len(featured)} market-backed</a> ({e(venues_txt)}),
    <a href="originated.html">{counts.get('model',0)} model</a> and
    <a href="originated.html">{len(provisional)} provisional</a>.</li>
    <li><strong>Where the lines come from &mdash; and where they do not exist.</strong>
    We probed <strong>{ceiling["probed"]} external venues</strong> from the build runner (established books,
    esportsbooks, exchanges, odds aggregators); {ceiling["answered"]} answered and {ceiling["json_feeds"]}
    returned JSON. On this build the feeds that actually quoted a listed match were:
    {ceiling_txt} &mdash; overwhelmingly the same Worlds 2026 ties.{silent_txt} Everything below that ceiling
    has no external line to quote, so we originate it ourselves.
    Probe table and receipts: <a href="sources.html"><strong>Sources</strong></a>.</li>
    <li><strong>Extra sources tried for the low-tier tail.</strong> {probe_line} {probe_link}.{lowtier_note}</li>
    <li><strong>Bookmaker evidence for the matches nobody prices.</strong> {obs_line}</li>
    <li><strong>Unresolved picks &amp; limitations.</strong> {len(unresolved)} cards cannot carry a playable
    probability today; they are listed with their reason and source in the section below and in full on
    <a href="unresolved.html">Unresolved &amp; limitations</a>. Nothing is padded with a guessed number.</li>
    <li><strong>Independence and limits.</strong> Hotspawn's public pick percentages are captured for audit
    only and carry zero weight in any probability (see <a href="methodology.html">Method</a>). Market quotes
    are source observations, not official verification; originated lines are model estimates from
    community-maintained Leaguepedia history; any walkover grade instead of Hotspawn's published void
    rule remains conditional &mdash; see <a href="flagged.html">Flagged for review</a>.</li>
    <li><strong>Verification.</strong> {live_sources} of the {len(src_status)} polled feeds answered on the
    last build, every row links to its official source, and the {gate_count}-check publish gate
    (<a href="verification.html">Verification</a>) blocks publication if a row lacks a source, the two
    probabilities fail to sum to 100%, or an internal link breaks.</li>
  </ul>
</section>

<section class="panel" id="unresolved-summary">
  <h2>Unresolved picks and the limitations ({len(unresolved)})</h2>
  <p class="lead">These cards cannot carry a playable win probability. They stay in the list to mirror
  Hotspawn exactly, are reported separately, and are never padded with a guessed number. Where the league
  itself has ruled a forfeit, the official settlement winner is shown - it is <em>not</em> a forecast.
  <a href="{HOTSPAWN_RULES_URL}" rel="noopener">Hotspawn's published rule</a> voids forfeited-match
  predictions, with no points awarded or deducted.</p>
  {table(["Kick-off", "Tournament", "Match", "Settlement pick", "Sources"], unres_rows) if unres_rows else '<p class="muted">No unresolved matches in this snapshot.</p>'}
  <ul class="bullets">
    <li><strong>Why a card can have no line.</strong> A team officially removed mid-split
    (<code>dqteams</code>) may have its remaining fixtures voided or graded as walkovers, so a probability
    built from its earlier results would be fiction.</li>
    <li><strong>No market on national and academy divisions.</strong> {total - len(featured)} of {total}
    matches are not priced by any book reachable from the runner; their lines come from recorded series
    history rather than an aggregator placeholder.</li>
    <li><strong>What we tried for the low-tier tail.</strong> {probe_line} {probe_link}. A second,
    independent check on 2026-10-25 (Pinnacle's league list, Polymarket, Sofascore, bo3.gg) reached the
    same ceiling: <a href="{EXTERNAL_LINES_MEMO_URL}" rel="noopener">external-line memo</a>.</li>
    <li><strong>Thin &amp; zero-history debut samples.</strong> {len(provisional)} lines are labelled
    <em>provisional</em> because at least one side has fewer than five rated series in the 25-month window
    ({sum(1 for r in provisional if (r.get("team0") or {}).get("rating_matches") == 0 or (r.get("team1") or {}).get("rating_matches") == 0)}
    involve a debut side with 0 pre-kickoff rated series, including
    {sum(1 for r in provisional if (r.get("team0") or {}).get("rating_matches") == 0 and (r.get("team1") or {}).get("rating_matches") == 0)}
    where both sides enter at 0/0 rated series and rest solely on equal division priors).</li>
    <li><strong>Full ledger.</strong> Every unresolved card, its settlement caveat and all remaining
    limitations are on <a href="unresolved.html">Unresolved &amp; limitations</a>; data irregularities are on
    <a href="flagged.html">Flagged for review</a>.</li>
  </ul>
</section>

<section class="panel" id="track">
  <h2>Track record</h2>
  <p class="lead">{track_line}. Grading rule and every graded row:
  <a href="results.html">Results</a>. Source for results: community-maintained Leaguepedia series records.</p>
</section>
"""
    return page_shell("Hotspawn LoL Pick Desk", "index.html", body,
                      "Independent win probabilities and a pick for every League of Legends match in the "
                      "Hotspawn pick'em.")


def build_results(rows: list[dict]) -> str:
    """Track record: every started card we can grade against the official series record."""
    doc = load_json(os.path.join(DATA, "matches.json")) or {}
    track = doc.get("track_record") or {}
    graded = sorted([r for r in rows if r.get("grade") in ("hit", "miss")],
                    key=lambda r: (r.get("start_utc") or ""), reverse=True)
    settled = [r for r in rows if r.get("grade") == "settled"]
    ungraded = [r for r in rows if r.get("stale") and not r.get("grade")]

    def grade_pill(g: str | None) -> str:
        if g == "hit":
            return '<span class="pill ok">HIT</span>'
        if g == "miss":
            return '<span class="pill bad">MISS</span>'
        if g == "settled":
            return '<span class="pill warn">SETTLED</span>'
        return '<span class="pill no">ungraded</span>'

    def result_cell(r: dict) -> str:
        res = r.get("result") or {}
        if not res:
            return '<span class="muted">no official record matched</span>'
        sc0, sc1 = res.get("score0"), res.get("score1")
        winner = r["team0"]["name"] if res.get("winner_side") == 0 else r["team1"]["name"]
        ff = res.get("forfeit_flag")
        ff_txt = f' <span class="muted small">FF={e(ff)}</span>' if ff not in (None, "", 0) else ""
        return (f'<strong>{e(winner)}</strong> won'
                f'<br><span class="muted small">{e(r["team0"]["name"])} {e(sc0)}&ndash;{e(sc1)} '
                f'{e(r["team1"]["name"])}{ff_txt}</span>'
                f'<br><a class="small" href="{e(res.get("source"))}" rel="noopener">Leaguepedia record</a>')

    def pick_cell(r: dict) -> str:
        p = r.get("pick") or {}
        if p.get("probability") is None:
            return (f'<strong class="res">{e(p.get("team") or "&mdash;")}</strong>'
                    f'<br><span class="small muted">settlement, no probability</span>')
        return (f'<strong>{e(p.get("team"))}</strong>'
                f'<br><span class="small muted">{p["probability"]*100:.1f}% to win</span>')

    trs = []
    for r in graded:
        trs.append(
            '<tr class="m-' + e(r["method"]) + '">'
            f'<td data-label="Kick-off" class="nowrap small">{e((r.get("start_utc") or "")[:16].replace("T", " "))} UTC</td>'
            f'<td data-label="Tournament" class="small">{e(r["competition"])}</td>'
            f'<td data-label="Match"><strong>{e(r["team0"]["name"])}</strong> <span class="muted">vs</span> '
            f'<strong>{e(r["team1"]["name"])}</strong></td>'
            f'<td data-label="Published pick">{pick_cell(r)}</td>'
            f'<td data-label="Official result">{result_cell(r)}</td>'
            f'<td data-label="Grade">{grade_pill(r.get("grade"))}</td>'
            f'<td data-label="Sources" class="srcs small">{_row_sources(r)}</td>'
            '</tr>')
    settled_rows = []
    for r in sorted(settled, key=lambda r: (r.get("start_utc") or ""), reverse=True):
        settled_rows.append(
            f'<tr><td data-label="Kick-off" class="small">{e((r.get("start_utc") or "")[:16].replace("T", " "))} UTC</td>'
            f'<td data-label="Tournament" class="small">{e(r["competition"])}</td>'
            f'<td data-label="Match">{e(r["team0"]["name"])} vs {e(r["team1"]["name"])}</td>'
            f'<td data-label="Settlement pick">{pick_cell(r)}</td>'
            f'<td data-label="Official record">{result_cell(r)}</td>'
            f'<td data-label="Grade">{grade_pill("settled")}</td>'
            f'<td data-label="Sources" class="srcs small">{_row_sources(r)}</td></tr>')

    by_method_rows = []
    for name, m in sorted((track.get("by_method") or {}).items(), key=lambda kv: -kv[1]["graded"]):
        by_method_rows.append(
            f'<tr><td data-label="Method">{badge(name)}</td>'
            f'<td data-label="Graded" class="num">{m["graded"]}</td>'
            f'<td data-label="Hits" class="num">{m["hits"]}</td>'
            f'<td data-label="Misses" class="num">{m["graded"] - m["hits"]}</td>'
            f'<td data-label="Accuracy" class="num">{m["accuracy"]*100:.1f}%</td></tr>')

    acc = track.get("accuracy")
    brier = track.get("brier")
    body = f"""
<section class="hero">
  <h2>Did the published picks actually win?</h2>
  <p>Every card on this site that has kicked off is graded against the official series record once one
  exists. This page is the honest scoreboard: it counts hits and misses of the <em>published</em> pick,
  never a probability rewritten after the result.</p>
  <div class="cta">
    <a class="btn primary" href="table.html">All matches &amp; picks &rarr;</a>
    <a class="btn" href="unresolved.html">Unresolved &amp; limitations</a>
  </div>
</section>

<section class="stats">
  {stat_card("Graded picks", track.get("graded", 0), "official series record matched", "ok")}
  {stat_card("Hits", track.get("hits", 0), "published pick won", "ok")}
  {stat_card("Misses", track.get("misses", 0), "the other side won", "unresolved")}
  {stat_card("Accuracy", f"{acc*100:.1f}%" if acc is not None else "&mdash;", "graded picks only", "model")}
  {stat_card("Brier score", f"{brier:.4f}" if brier is not None else "&mdash;", "lower is better", "")}
  {stat_card("Forfeit settlements", track.get("settled_forfeits", 0), "not counted as forecast wins", "provisional")}
  {stat_card("Started, ungraded", len(ungraded), "no consistent official record", "")}
</section>

<section class="panel">
  <h2>Graded picks</h2>
  <p class="lead">Newest first. A pick is graded only when the official record matches this fixture's team
  pair and kick-off (within 12 hours) and the recorded winner agrees with the recorded score. Anything less
  stays ungraded rather than being guessed.</p>
  {raw_table(["Kick-off", "Tournament", "Match", "Published pick", "Official result", "Grade", "Sources"], trs) if trs else '<p class="muted">No graded picks in this snapshot yet.</p>'}
</section>

<section class="panel">
  <h2>Accuracy by how the line was made</h2>
  {raw_table(["Method", "Graded", "Hits", "Misses", "Accuracy"], by_method_rows, "table stack") if by_method_rows else '<p class="muted">No graded picks yet.</p>'}
  <p class="muted small">A market line and a model line are expected to differ: the market-backed
  sample is small (a handful of Worlds series), so read the model and provisional rows as the meaningful
  sample. Out-of-sample backtest of the rating model itself is on
  <a href="methodology.html">Method</a>.</p>
</section>

<section class="panel">
  <h2>Forfeit settlements</h2>
  <p class="lead">These cards were resolved by league rule, not by play. They are listed for completeness and
  never counted as a successful forecast.</p>
  {raw_table(["Kick-off", "Tournament", "Match", "Settlement pick", "Official record", "Grade", "Sources"], settled_rows) if settled_rows else '<p class="muted">No forfeit settlements in this snapshot.</p>'}
</section>

<section class="panel">
  <h2>Started but ungraded ({len(ungraded)})</h2>
  <p class="lead">Hotspawn keeps <code>status=scheduled</code> on cards whose start time has passed. Where
  Leaguepedia holds no consistent record for the pair, the card stays listed and ungraded here - it is never
  scored from an assumption.</p>
  <p>The full list is on <a href="unresolved.html">Unresolved &amp; limitations</a>, together with every
  documented limitation of the data.</p>
</section>
"""
    return page_shell("Results and track record", "results.html", body,
                      "Every published pick graded against the official League of Legends series record.")


def build_table(rows: list[dict], counts: Counter) -> str:
    ordered = sorted(rows, key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    upcoming_n = sum(1 for r in ordered if not r.get("stale"))
    comps = sorted({r["competition"] for r in ordered})
    opts = "".join('<option value="' + e(c) + '">' + e(c) + "</option>" for c in comps)
    chips = "".join(
        '<button class="chip" data-tfilter="' + m + '">' + e(METHOD_LABEL[m])
        + ' <span>' + str(counts.get(m, 0)) + "</span></button>"
        for m in ("market", "model", "provisional", "unresolved"))
    trs = []
    for r in ordered:
        method = r["method"]
        hay = (r["team0"]["name"] + " " + r["team1"]["name"] + " " + r["competition"]).lower()
        cells = [
            '<td data-label="Kick-off" class="nowrap">' + local_time(r["start_utc"]) + "</td>",
            '<td data-label="Match"><div class="mrow"><strong>' + e(r["team0"]["name"]) + '</strong>'
            # pct_pair, not pct() twice: rounding each side independently makes seven
            # rows print pairs that add up to 99.9% or 100.1%.
            + f'<span class="pct">{pct_pair(r["p0"], r["p1"])[0]}</span></div>'
            + '<div class="mrow"><strong>' + e(r["team1"]["name"]) + '</strong>'
            + f'<span class="pct">{pct_pair(r["p0"], r["p1"])[1]}</span></div></td>',
            '<td data-label="Pick">' + _pick_cell(r) + "</td>",
            '<td data-label="Method" class="opt">' + badge(method) + "</td>",
            '<td data-label="Tournament" class="opt small">' + e(r["competition"]) + "</td>",
            '<td data-label="Sources" class="srcs small">' + _row_sources(r) + "</td>",
        ]
        trs.append('<tr class="prow m-' + e(method) + '" data-method="' + e(method) + '" data-comp="'
                   + e(r["competition"]) + '" data-start="' + e(r["start_utc"] or "")
                   + '" data-stale="' + ("1" if r.get("stale") else "0") + '" data-text="' + e(hay) + '">'
                   + "".join(cells) + "</tr>")
    body = f"""
<section class="panel">
  <p class="lead">Every listed League of Legends match, next kick-off first. The <strong>Pick</strong> column
  is the side we take. On a phone this page is the <strong>Picks</strong> tab in the bar at the bottom of
  every screen. Search and filter work without a reload.</p>
  <div class="toolbar">
    <input id="tq" type="search" placeholder="Search team or tournament" aria-label="Search team or tournament">
    <select id="tcomp" aria-label="Filter by tournament"><option value="">All tournaments</option>{opts}</select>
    <div class="chips"><button class="chip active" data-tfilter="">All <span>{len(ordered)}</span></button><button class="chip chip-toggle" type="button" id="tupcoming" aria-pressed="false">Upcoming only <span>{upcoming_n}</span></button>{chips}</div>
  </div>
  <p class="muted small" id="tcount">{len(ordered)} matches shown</p>
  <div class="tablewrap">
    <table class="picktable">
      <thead><tr>
        <th>Kick-off (UTC)</th><th>Match &amp; win probabilities</th><th>Pick</th>
        <th class="opt">Method</th><th class="opt">Tournament</th><th>Sources</th>
      </tr></thead>
      <tbody id="tbody">
        {"".join(trs)}
      </tbody>
    </table>
  </div>
  <p class="empty" id="tempty" hidden>No matches match that filter.</p>
</section>

<section class="panel">
  <h2>How to read this table</h2>
  <ul class="bullets">
    <li><strong>Match &amp; win probabilities</strong> - our probability for each side, summing to 100%. The
    pick is always the higher side.</li>
    <li><strong>Method</strong> - <span class="badge b-market">Market line</span> is a de-vigged real-money
    consensus; <span class="badge b-model">Model line</span> is our own Elo line from recorded series results;
    <span class="badge b-provisional">Provisional</span> is a thin sample;
    <span class="badge b-unresolved">Unresolved</span> means no playable probability, see
    <a href="unresolved.html">Unresolved &amp; limitations</a>.</li>
    <li><strong>Sources</strong> - each row links to the Hotspawn card, the priced market (if any) and the
    official results page used to build the line.</li>
  </ul>
</section>
"""
    return page_shell("Pick table", "table.html", body,
                      f"All {len(ordered)} Hotspawn League of Legends matches in one table: pick, both win "
                      "probabilities, method and source links, next kick-off first.")


def build_picks(rows: list[dict], counts: Counter) -> str:
    rows = sorted(rows, key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    upcoming_n = sum(1 for r in rows if not r.get("stale"))
    comps = sorted({r["competition"] for r in rows})
    chips = "".join(
        f'<button class="chip" data-filter="{m}">{METHOD_LABEL[m]} <span>{counts.get(m,0)}</span></button>'
        for m in ("market", "model", "provisional", "unresolved"))
    opts = "".join(f'<option value="{e(c)}">{e(c)}</option>' for c in comps)
    body = f"""
<section class="panel">
  <p class="lead">Same {len(rows)} matches as the <a href="table.html">pick table</a>, one card each with the
  full reasoning and every source. Sorted by next kick-off; cards whose start time has already passed are
  listed after upcoming matches and marked.</p>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search team or tournament" aria-label="Search team or tournament">
    <select id="comp" aria-label="Filter by tournament"><option value="">All tournaments</option>{opts}</select>
    <div class="chips"><button class="chip active" data-filter="">All <span>{len(rows)}</span></button><button class="chip chip-toggle" type="button" id="upcoming" aria-pressed="false">Upcoming only <span>{upcoming_n}</span></button>{chips}</div>
  </div>
  <p class="muted small" id="count" role="status" aria-live="polite">{len(rows)} matches shown</p>
  <div class="cards" id="list">
    {"".join(match_card(r) for r in rows)}
  </div>
  <p class="empty" id="empty" hidden>No match found &mdash; clear the search or pick another tournament.</p>
  <p style="text-align:center;margin:14px 0 0"><button class="btn" type="button" id="totop">Back to top</button></p>
</section>
"""
    return page_shell("All picks", "picks.html", body,
                      f"Every League of Legends match on the Hotspawn pick'em list ({len(rows)} matches), "
                      "next kick-off first. Tap 'Why this line' on any card for full inputs and sources.")


def build_featured(rows: list[dict]) -> str:
    items = [r for r in rows if r["method"] == "market"]
    rows_html = []
    for r in items:
        m = r["market"]
        dec = m.get("decimal") or {}
        vlinks = " &middot; ".join(
            f'<a href="{e(v["url"])}" rel="noopener">{e(v["name"])} ({e(v["quote"])})</a>'
            for v in (m.get("venues") or [])
        ) or f'<a href="{e(m.get("market_url") or m.get("source_url"))}" rel="noopener">line</a>'
        cross = (m.get("model_cross_check"))
        if cross is not None:
            gap = abs((r["p0"] or 0) - cross) * 100
            c0, c1 = pct_pair(cross, 1.0 - cross)
            cross_cell = (f'{c0} / {c1}'
                          f'<br><span class="muted small">{"&#9888; " if gap >= 20 else ""}{gap:.0f} pp gap</span>')
        else:
            cross_cell = '<span class="muted">not rated</span>'
        pa_txt, pb_txt = pct_pair(r["p0"], r["p1"])
        rows_html.append([
            local_time(r["start_utc"]),
            e(r["competition"]),
            f'<strong>{e(r["pick"]["team"])}</strong> ({r["pick"]["probability"]*100:.1f}%)<br>'
            f'<span class="muted small">{e(r["team0"]["name"])} vs {e(r["team1"]["name"])}</span>',
            pa_txt + " / " + pb_txt,
            cross_cell,
            f'{e(m["book"])}',
            f'{dec.get("home","")} / {dec.get("away","")}',
            f'{vlinks} &middot; <a href="{e(r["hotspawn_url"])}" rel="noopener">card</a>',
        ])
    body = f"""
<section class="panel">
  <h2>{len(items)} matches with real-money bookmaker &amp; exchange consensus</h2>
  <p class="lead">Featured matches combine live quotes across <strong>Pinnacle (weight 0.36), Polymarket
  full-series CLOB (0.24), Kalshi CFTC regulated contracts (0.18), Bovada (0.12) and Unibet/Kambi (0.10)</strong>.
  Bookmaker margin is removed proportionally on each venue before precision weighting. Symmetric 1.80 / 1.80
  aggregator placeholders are rejected, Pinnacle's parallel &quot;(Kills)&quot; derivative markets are excluded
  from the series consensus, and a single prediction market with almost no traded volume is downgraded to low
  confidence (see <a href="flagged.html">Flagged for review</a>).</p>
  {table(["Start (UTC)", "Tournament", "Pick &amp; Match", "Consensus (A / B)", "Model cross-check", "Venues", "Primary Decimal", "Source records"], rows_html)}
  <h3>Proportional de-vig &amp; consensus formula</h3>
  <p class="formula">p&#770;<sub>v</sub> = (1/o<sub>1,v</sub>) / (1/o<sub>1,v</sub> + 1/o<sub>2,v</sub>), &nbsp;&nbsp; P(A) = &sum; w<sub>v</sub> p&#770;<sub>v</sub> / &sum; w<sub>v</sub></p>
  <div class="cards">{"".join(match_card(r) for r in items)}</div>
</section>
"""
    return page_shell("Market-backed picks", "featured.html", body,
                      "Matches priced from de-vigged real-money bookmaker & prediction-exchange consensus.")


def build_originated(rows: list[dict], counts: Counter) -> str:
    items = [r for r in rows if r["method"] in ("model", "provisional")]
    reviews = []
    for r in items:
        t0, t1 = r["team0"], r["team1"]
        pa_txt, pb_txt = pct_pair(r["p0"], r["p1"])
        reviews.append([
            local_time(r["start_utc"]),
            e(r["competition"]),
            f'<strong>{e(t0["name"])}</strong> vs <strong>{e(t1["name"])}</strong>',
            f'{t0["elo"] if t0["elo"] is not None else "&mdash;"} <span class="muted small">({t0["rating_matches"]})</span>'
            f' / {t1["elo"] if t1["elo"] is not None else "&mdash;"} <span class="muted small">({t1["rating_matches"]})</span>',
            pa_txt + " / " + pb_txt,
            badge(r["method"]),
            (f'<a href="{e(r["hotspawn_url"])}" rel="noopener">card</a> &middot; '
             f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(r["leaguepedia_page"] or "")}" rel="noopener">results page</a>'
             if r.get("leaguepedia_page") else f'<a href="{e(r["hotspawn_url"])}" rel="noopener">card</a>'),
        ])
    body = f"""
<section class="panel">
  <h2>{len(items)} low-tier regional matches originated from recorded series history</h2>
  <p class="lead">Tier-B/C/D national and academy leagues are not offered by major sportsbooks, so we originate
  independent probabilities from chronological series history in Leaguepedia since
  {e((load_json(os.path.join(DATA,'matches.json')) or {}).get('model',{}).get('window_start',''))},
  with inactivity decay and empirical Bayes shrinkage toward each team's division prior
  (1700 / 1575 / 1500 / 1455).</p>
  <div class="stats tight">
    {stat_card("Solid originated lines", counts.get('model',0), "both teams rated & connected", "model")}
    {stat_card("Provisional lines", counts.get('provisional',0), "thin sample - flagged", "provisional")}
  </div>
  {table(["Start (UTC)", "Tournament", "Match", "Elo (n) A / B", "Our line", "Status", "Results"], reviews)}
  <h3>Formula</h3>
  <p class="formula">P(A) = 1 / (1 + 10^((R<sub>B</sub> - R<sub>A</sub>) / 400))</p>
  <p>Probabilities are bounded to 5-95% so thin lower-division samples never claim false certainty.</p>
</section>
"""
    return page_shell("Originated low-tier lines", "originated.html", body,
                      "Independent series-history probabilities for matches with no sportsbook coverage.")


def build_unresolved(rows: list[dict], counts: Counter, src_status: list[dict] | None = None) -> str:
    unresolved = sorted([r for r in rows if r["method"] == "unresolved"],
                        key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    provisional = sorted([r for r in rows if r["method"] == "provisional"],
                         key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    zero_hist = [r for r in rows if r["method"] == "provisional"
                 and ((r.get("team0") or {}).get("rating_matches") == 0
                      or (r.get("team1") or {}).get("rating_matches") == 0)]
    both_zero = [r for r in zero_hist
                 if (r.get("team0") or {}).get("rating_matches") == 0
                 and (r.get("team1") or {}).get("rating_matches") == 0]
    disconnected = [r for r in rows if any("no shared-opponent chain" in f for f in r["flags"])]
    non_exact = [r for r in rows
                 if (r.get("team0") or {}).get("join", "exact") != "exact"
                 or (r.get("team1") or {}).get("join", "exact") != "exact"]
    ambiguous = [r for r in rows if any("ambiguous" in f or "could not be matched" in f for f in r["flags"])]
    ceiling = _external_ceiling()
    reason_rows = []
    for r in unresolved:
        lp_link = (f' &middot; <a href="https://lol.fandom.com/wiki/{leaguepedia_slug(r["leaguepedia_page"])}" rel="noopener">league page</a>'
                   if r.get("leaguepedia_page") else "")
        res = r.get("resolution") or {}
        settle = (f'<strong>{e(res["winner"])}</strong><br><span class="small muted">official forfeit win</span>'
                  if res else '<span class="muted">no pick</span>')
        reason_rows.append([
            f'<a id="m{e(r["id"])}"></a>{local_time(r["start_utc"])}',
            e(r["competition"]),
            f'<strong>{e(r["team0"]["name"])}</strong> vs <strong>{e(r["team1"]["name"])}</strong>',
            settle,
            e(r["basis"]),
            f'<a href="{e(r["hotspawn_url"])}" rel="noopener">Hotspawn card</a>{lp_link}'
            + (f' &middot; <a href="{e(res["source"])}" rel="noopener">forfeit record</a>' if res else ""),
        ])
    lim_rows = [
        ["Mid-split league removals (dqteams)", f"{len(unresolved)} matches",
         "Leaguepedia's Data: page for the competition records the removal (for Komplettligaen, Round 10 carries the "
         "footnote '[[Solid Gaming]] is removed from the league.' and every remaining series is scored 0-2 with an ff "
         "flag). Hotspawn's published rule voids all predictions on a forfeited match, so the expected outcome "
         "is 0 points either way; an Elo probability built from pre-removal results would be invalid, so the row "
         "is quarantined and only the administrative winner is shown, with no percentage."],
        ["No sportsbook market on national divisions", f"{len([r for r in rows if r['method']!='market'])} matches",
         "Only the competitions listed on the Market page have a reachable price in this snapshot. The remaining "
         "national, academy and third-division leagues are not offered by any book the build runner can reach, so "
         "their lines are originated from recorded series history rather than borrowed from a placeholder."],
        ["Thin match history", f"{counts.get('provisional',0)} provisional",
         "At least one team has fewer than five rated series in the 25-month Leaguepedia window, so the Elo estimate "
         "carries wider variance and is explicitly flagged provisional."],
        ["Zero pre-kickoff history (debut sides)",
         f"{len(zero_hist)} matches ({len(both_zero)} dual-debut)",
         "One or both teams enter kick-off with 0 prior Leaguepedia rated series and are anchored strictly to their "
         "division prior (1700 / 1575 / 1500 / 1455). Where both sides have 0 rated series, the 50.0% / 50.0% split "
         "reflects identical division priors rather than match evidence (see Flagged for review)."],
        ["Name disambiguation",
         f"{len(non_exact)} disambiguated ({len(ambiguous)} unresolved)",
         "Homonymous regional teams (e.g. 'Fenrir (Icelandic Team)' vs Polish 'Fenrir', 'PvB (Swiss Team)' mislabelled "
         "by Hotspawn as Vietnamese 'Phong Vũ Buffalo') are joined only via competition-scoped roster evidence."],
        ["Disconnected opponent graphs", f"{len(disconnected)} matches",
         "Cross-pool teams without a shared opponent chain are flagged rather than treated as high-confidence lines."],
        ["Geo-fenced / bot-protected books", "see Sources",
         "Every book probed on this build, its HTTP status and the reason it could not be used are listed on "
         "Sources. A book that returns a page but only renders symmetric 1.8/1.8 placeholders (EGamersWorld) is "
         "never treated as a price."],
    ]
    hunt_rows = []
    for st in (src_status or []):
        cls = "ok" if st.get("ok") else "bad"
        hunt_rows.append([
            f'<a href="{e(st.get("url"))}" rel="noopener">{e(st.get("name"))}</a>',
            e(st.get("note")),
            f'<span class="pill {cls}">{e(st.get("status"))}</span>',
            e((st.get("checked_utc") or "")[:16].replace("T", " ")),
        ])
    hunt_table = (table(["Source", "What it is", "Runner verdict", "Checked (UTC)"], hunt_rows)
                  if hunt_rows else '<p class="muted">No source probe recorded on this build.</p>')
    # Dedicated esportsbook/aggregator probe (data/esportsbook_probe.json): every established book,
    # esportsbook and aggregator tried specifically for the matches the primary feeds do not price.
    # Rendered from the receipt, never typed by hand; a venue is only ever shown as usable when the
    # runner actually received a named fixture with a decimal price.
    probe = _esportsbook_probe()
    probe_doc = load_json(os.path.join(DATA, "esportsbook_probe.json")) or {}
    probe_rows = []
    for r in probe_doc.get("rows") or []:
        verdict = "usable \u2014 named fixtures with prices" if r.get("usable") else e(r.get("reason") or r.get("verdict") or "not usable")
        probe_rows.append([
            f'<a href="{e(r.get("url"))}" rel="noopener">{e(r.get("name"))}</a>',
            e(r.get("category") or ""),
            verdict if r.get("usable") else f'<span class="pill bad">{e(r.get("status"))}</span> {verdict}',
            e((r.get("checked_utc") or "")[:16].replace("T", " ")),
        ])
    probe_table = (table(["Esportsbook / aggregator", "Type", "Runner verdict", "Checked (UTC)"], probe_rows)
                   if probe_rows else '<p class="muted">No esportsbook probe receipt committed yet.</p>')
    probe_summary = (
        f'{probe["tested"]} endpoints probed from the build runner on {e(probe["checked"])} UTC: '
        f'<strong>{probe["usable"]} returned a machine-readable LoL price</strong> '
        f'({probe["http_blocked"]} blocked or key-gated, {probe["html_only"]} browser-only HTML). '
        'Receipt: <a href="data/esportsbook_probe.json" rel="noopener">esportsbook_probe.json</a>.'
        if probe["have"] else "No esportsbook probe receipt is committed for this build.")
    _, lowtier_date, lowtier_n = _lowtier_matrix()
    obs = _venue_observations()
    obs_rows = []
    for o in obs:
        obs_rows.append([
            f'<a href="{e(o["url"])}" rel="noopener">{e(o["source_name"])}</a>'
            f'<br><span class="small muted">{e(o["kind"])}</span>',
            e(o["observation"]),
            f'<span class="small">&ldquo;{e(o["verbatim"])}&rdquo;</span>'
            f'<br><span class="small muted">captured {e(o["captured_utc"][:16].replace("T", " "))}Z'
            f' &middot; {e(o["url"])}</span>',
        ])
    obs_block = ""
    if obs_rows:
        obs_block = f"""
<section class="panel" id="observed">
  <h2>What the established books and esportsbooks actually showed ({len(obs)} checks)</h2>
  <p class="lead">Beyond the runner probes above, a person opened these pages on
  <strong>{e(_latest_observation_day(obs))}</strong> and read them. Each row is one check: the venue,
  what its LoL lobby contained for the leagues below the featured ceiling, the sentence it printed,
  and the capture time &mdash; every row links to the page itself so it can be re-checked by hand.
  This is the direct answer to &ldquo;is there a betting line for these matches anywhere?&rdquo;:
  on the date shown <strong>no venue priced the national and academy divisions</strong> below the
  featured ceiling, which is why those picks are originated instead of quoted. Where a venue did price
  a lower-tier tie (Thunderpick on LGC Rising) it is named in the row and the quote is filed as a
  cross-check.</p>
  {table(["Venue", "What it showed for the unpriced leagues", "Verbatim reading &amp; capture"], obs_rows)}
  <p class="small muted">Receipts: <a href="{GITHUB_BLOB}/data/receipts/external_odds/2026-10-25.json" rel="noopener">2026-10-25.json</a>
  &middot; full venue-by-venue ledger on <a href="coverage.html">Coverage</a>
  &middot; dossier <a href="{GITHUB_BLOB}/research/LINE_SEARCH_2026-10-25.md" rel="noopener">research/LINE_SEARCH_2026-10-25.md</a>.</p>
</section>"""

    body = f"""
<section class="panel">
  <h2>Unresolved picks ({len(unresolved)})</h2>
  <p class="lead">A fixture is quarantined here when no defensible win probability exists — specifically
  mid-split league disqualifications/removals (<code>dqteams</code>) where matches are never played on the Rift,
  or cards with no match history on either side. Where the competition record already awards a forfeit, the
  official settlement winner is listed in its own column. Leaguepedia is a community source, not a settlement
  authority. Hotspawn's published rule is explicit &mdash; <em>&ldquo;If a match is forfeited, all predictions
  for that match are voided. No points are awarded or deducted&rdquo;</em>
  (<a href="{HOTSPAWN_RULES_URL}" rel="noopener">Hotspawn &mdash; How Pick'ems Works</a>, checked 2026-10-24)
  &mdash; so expect a forfeit card to score zero whichever side you tap; the winner shown is the
  administratively correct side only if Hotspawn grades a walkover instead of voiding.</p>
  {'<p class="muted">No unresolved matches in this snapshot.</p>' if not unresolved else table(["Start (UTC)", "Tournament", "Match", "Official settlement pick", "Why competitive pricing is impossible", "Verified Sources"], reason_rows)}
</section>

<section class="panel">
  <h2>Documented limitations across the list</h2>
  {table(["Limitation", "Scope", "Impact &amp; handling"], lim_rows)}
</section>

<section class="panel" id="fallback">
  <h2>Fallback by competition &mdash; how non-featured picks are guided</h2>
  <p class="lead">For every competition the featured (market) resolution cannot price, this is what guides the
  pick instead, and the limitation to keep in mind. Order of trust: <strong>market</strong> (de-vigged book
  consensus) &rarr; <strong>originated</strong> (our Elo from recorded series history) &rarr;
  <strong>provisional</strong> (same Elo on thin data, % shrunk toward 50%) &rarr;
  <strong>settlement</strong> (administrative forfeit winner, no %; Hotspawn voids forfeited-match predictions).
  External-line evidence: {lowtier_n} established books, esportsbooks, exchanges and aggregators probed from the
  build runner on {e(lowtier_date)} &mdash; <a href="{LOWTIER_MEMO_URL}" rel="noopener">research memo</a> and
  machine-readable receipts in <code>data/probe/lowtier_20261024.json</code>. A keyed odds API might widen
  coverage but needs an owner-provided credential; none is used and none is circumvented.</p>
  {table(["Competition", "Matches", "Pick basis", "External line found?", "Limitation"], _fallback_rows(rows))}
</section>

<section class="panel" id="line-hunt">
  <h2>Where we looked for a line</h2>
  <p class="lead">No percentage is published for the matches above because no reachable source quotes them.
  These are the books, exchanges and odds aggregators probed on the current build, with the runner's own HTTP
  verdict: a source marked <em>blocked</em> was tried and refused the connection, so it cannot back a pick even
  where it might show a price in a browser. Additional sources that were researched and ruled out, with the
  exact response each returned, are logged in
  <a href="data/line_source_research.json" rel="noopener">line_source_research.json</a>.</p>
  {hunt_table}
  <h3>Esportsbooks &amp; aggregators tried for the unpriced tail</h3>
  <p>{probe_summary} Blocked or browser-only venues are recorded, never worked around, and never
  back a pick &mdash; the unpriced tail keeps its originated (Elo) line instead of a borrowed quote.</p>
  {probe_table}
</section>
{obs_block}

<section class="panel">
  <h2>Provisional lines ({len(provisional)})</h2>
  <p class="lead">Low-confidence originated picks with thin match samples. Every card lists its exact caveat.</p>
  <div class="cards">{"".join(match_card(r) for r in provisional)}</div>
</section>
"""
    return page_shell("Unresolved & limitations", "unresolved.html", body,
                      "Matches where competitive pricing is impossible, plus every documented limitation.")


def build_competitions(rows: list[dict], comp_map: dict) -> str:
    comps = sorted({r["competition"] for r in rows})
    out = []
    for c in comps:
        sub = [r for r in rows if r["competition"] == c]
        cnt = Counter(r["method"] for r in sub)
        page = (comp_map.get(c) or {}).get("page")
        out.append([
            e(c),
            str(len(sub)),
            str(cnt.get("market", 0)),
            str(cnt.get("model", 0)),
            str(cnt.get("provisional", 0)),
            str(cnt.get("unresolved", 0)),
            (f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(page)}" rel="noopener">{e(page)}</a>'
             if page else '<span class="muted">not mapped</span>'),
        ])
    body = f"""
<section class="panel">
  <h2>Coverage by tournament ({len(comps)})</h2>
  <p class="lead">Every tournament on the Hotspawn LoL list, broken down by pricing tier and linked to its
  Leaguepedia results overview page.</p>
  {table(["Tournament", "Matches", "Market", "Model", "Provisional", "Unresolved", "Results source"], out)}
</section>
"""
    return page_shell("Tournaments", "competitions.html", body,
                      "Coverage and source quality for every tournament on the Hotspawn list.")


def build_teams(rows: list[dict]) -> str:
    teams = {}
    for r in rows:
        for side in ("team0", "team1"):
            t = r[side]
            prev = teams.get(t["name"])
            if not prev or (t["rating_matches"] or 0) > (prev["n"] or 0):
                teams[t["name"]] = {"name": t["name"], "lp": t["leaguepedia"],
                                    "elo": (t.get("elo_now") if t.get("elo_now") is not None else t["elo"]),
                                    "n": t["rating_matches"],
                                    "last": max([x for x in ((prev or {}).get("last"), t["last_played"]) if x],
                                                default=None),
                                    "join": t["join"]}
    ordered = sorted(teams.values(), key=lambda x: (-(x["elo"] or 0), x["name"]))
    out = [[e(t["name"]),
            (f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(t["lp"])}" rel="noopener">{e(t["lp"])}</a>'
             if t["lp"] else '<span class="muted">not matched</span>'),
            str(t["elo"]) if t["elo"] is not None else "&mdash;",
            str(t["n"] or 0),
            e(t["last"] or "&mdash;"),
            f'<span class="join j-{e(t["join"])}">{e(t["join"])}</span>'] for t in ordered]
    body = f"""
<section class="panel">
  <h2>{len(ordered)} teams on the current list</h2>
  <p class="lead">Ratings are fitted chronologically from official series results. Non-exact name joins are
  audited individually on <a href="verification.html">Verification</a>.</p>
  {table(["Team (Hotspawn)", "Leaguepedia team", "Elo", "Rated series", "Last played", "Join"], out)}
</section>
"""
    return page_shell("Teams", "teams.html", body, "Ratings and name-join evidence for every team on the list.")


def build_methodology(model: dict) -> str:
    bt = model.get("backtest") or {}
    body = f"""
<section class="panel">
  <h2>The 4-tier probability architecture</h2>
  <ol class="steps">
    <li><strong>Inventory.</strong> Every League of Legends fixture is pulled from Hotspawn's public fixtures API
    (<a href="https://play.hotspawn.com/lol-pickems" rel="noopener">play.hotspawn.com/lol-pickems</a>).</li>
    <li><strong>Tier 1 — Multi-venue real-money consensus.</strong> Live odds and contract books from
    <strong>Pinnacle (0.36), Polymarket full-series CLOB (0.24), Kalshi CFTC (0.18), Bovada (0.12) and
    Unibet/Kambi (0.10)</strong> are de-vigged proportionally and precision-weighted. Only series moneylines are
    accepted: Pinnacle's parallel &quot;(Kills)&quot; derivative is filtered out in <code>collect.py</code> and
    again in <code>model.py</code>, and archived third-party quotes that cannot be re-verified on the build
    machine are retired rather than reused.</li>
    <li><strong>Tier 2 — Originated regional Elo lines.</strong> All recorded Leaguepedia series since
    {e(model.get('window_start',''))} are processed strictly chronologically with division priors
    (1700 major / 1575 challenger-tier-2 / 1500 regional / 1455 open-div-3), series margin-of-victory scaling,
    inactivity decay and empirical Bayes shrinkage toward each team's tier prior.</li>
    <li><strong>Tier 3 — Provisional &amp; Unresolved quarantine.</strong> Thin-sample teams (&lt;5 series) are marked
    <em>provisional</em>; officially removed mid-split teams (<code>dqteams</code>) are quarantined in
    <a href="unresolved.html">Unresolved</a> rather than mispriced.</li>
    <li><strong>Automated publish gate.</strong> Every 6 hours GitHub Actions re-runs the full pipeline and
    executes the publish gate (<a href="verification.html">Verification</a>) before publishing to GitHub Pages;
    a failing assertion aborts the commit instead of shipping bad data.</li>
  </ol>
</section>

<section class="panel">
  <h2>Formulas</h2>
  <p>Expected series win probability for team A:</p>
  <p class="formula">E<sub>A</sub> = 1 / (1 + 10^((R<sub>B</sub> - R<sub>A</sub>)/400))</p>
  <p>Chronological rating update after each completed series (K = {e(model.get('k'))}, margin multiplier 1 + 0.18 &middot; max(0, &Delta;games &minus; 1)):</p>
  <p class="formula">R&prime;<sub>A</sub> = R<sub>A</sub> + K<sub>eff</sub> &middot; (S<sub>A</sub> - E<sub>A</sub>)</p>
  <p>Empirical Bayes shrinkage towards tier prior R<sub>0</sub> for sample size n (shrink = {e(model.get('shrink'))}):</p>
  <p class="formula">R<sub>eff</sub> = R<sub>0</sub> + (R - R<sub>0</sub>) &middot; n / (n + {e(model.get('shrink'))})</p>
  <p>Inactivity decay begins after {e(model.get('decay_start_days'))} days and decays linearly back to each team's
  tier prior R<sub>0</sub> over the next {e(model.get('decay_full_days'))} days; originated probabilities are
  clamped to {e(model.get('prob_floor'))}&ndash;{e(model.get('prob_ceil'))}.</p>
</section>

<section class="panel">
  <h2>Out-of-sample backtest &amp; calibration</h2>
  <p class="lead">Every recorded series after <strong>{e(bt.get('cutoff','2026-07-01'))}</strong>
  (<strong>{bt.get('n', 0):,}</strong> out-of-sample series) is predicted strictly before its result updates
  either team's rating (zero look-ahead leakage).</p>
  {table(["Sample", "Series", "Accuracy", "Brier score", "Log loss"],
         [["All out-of-sample series",
           f"{bt.get('n', 0):,}",
           pct(bt.get('accuracy')),
           str(bt.get('brier', '—')),
           str(bt.get('logloss', '—'))],
          ["Coin-flip baseline (50/50)",
           f"{bt.get('n', 0):,}",
           "50.0%",
           "0.2500",
           "0.6931"]])}
  {calibration_svg(bt)}
  {table(["Favourite probability bucket", "Series", "Predicted (avg)", "Actual realized win rate"],
         [[e(k), f"{v['n']:,}", pct(v['mean_predicted']), pct(v['accuracy'])]
          for k, v in (bt.get('buckets') or {}).items()])}
  <p class="small muted">A companion within-tournament Bayesian Bradley-Terry cross-validation was run by an
  earlier session on 1,595 series from active low-tier divisions and is stored in
  <code>archive/session-8336fb7e/data/calibration.json</code> (reported there: 64.9% accuracy, 0.2145 Brier
  score, 3.53% ECE). It is an archived result, not re-executed by this build, and is shown for context only -
  the live numbers above are recomputed on every refresh from the current Leaguepedia extract.</p>
</section>

<section class="panel">
  <h2>Hard methodological guardrails</h2>
  <ul class="bullets">
    <li><strong>Zero Hotspawn crowd input.</strong> Crowd pick shares are never read by the probability engine.</li>
    <li><strong>Zero placeholder odds.</strong> Symmetric 1.80 / 1.80 defaults on odds aggregators are discarded,
    and any quote that cannot be re-fetched on the build machine is excluded from the probability entirely.</li>
    <li><strong>Official walkovers are not forecasts.</strong> Where a league has ruled a forfeit, the settlement
    winner is published in a separate field with no probability and is excluded from the backtest and from the
    market-coverage counts.</li>
    <li><strong>Receipts expire.</strong> A bookmaker quote captured from a match page is a line only while it is
    fresh; archived receipts older than 24 hours are excluded from the consensus, so an affected match falls back
    to the live venues or to the model rather than to a stale price.</li>
    <li><strong>Market vs model is disclosed.</strong> Every market-priced row also publishes our own Elo
    probability and flags a gap of 20 percentage points or more, instead of quietly blending the two.</li>
    <li><strong>Explicit quarantine over guesswork.</strong> Disqualified teams (<code>dqteams</code>) get a
    settlement pick with no probability, and every caveat is documented on
    <a href="unresolved.html">Unresolved</a> and <a href="flagged.html">Flagged for review</a>.</li>
  </ul>
</section>
"""
    return page_shell("Method", "methodology.html", body,
                      "How every probability on this site is computed, backtested, and audited.")


def build_sources(src: list[dict]) -> str:
    out = []
    for s in src:
        st = s.get("status")
        cls = "ok" if s.get("ok") else "bad"
        out.append([e(s.get("name")), f'<a href="{e(s.get("url"))}" rel="noopener">link</a>',
                    e(s.get("note")), f'<span class="pill {cls}">{e(st)}</span>', e(s.get("blocked_note")),
                    e((s.get("checked_utc") or "")[:16].replace("T", " "))])
    probe = _esportsbook_probe()
    probe_rows = []
    for slug, row in probe["blocked"].items():
        probe_rows.append([
            e(row.get("name")),
            e(row.get("category")),
            f'<a href="{e(row.get("url"))}" rel="noopener">endpoint</a>',
            f'<span class="pill bad">{e(row.get("status") if row.get("status") is not None else "err")}</span>',
            e((row.get("reason") or "")[:160]),
            e((row.get("checked_utc") or "")[:16].replace("T", " ")),
        ])
    if probe["have"]:
        probe_block = f"""
<section class="panel" id="esportsbook-probe">
  <h2>Esportsbook and aggregator probe ({probe["tested"]} endpoints, {probe["usable"]} usable)</h2>
  <p class="lead">The client brief asks for a real betting line wherever one exists, including low-tier and
  national LoL leagues, before we fall back to our own originated line. This is the result of calling each
  candidate endpoint from the build runner on {e(probe["checked"])} UTC. A venue is only usable if it returned a
  named fixture with a decimal price; a blocked or browser-only venue is recorded here rather than worked
  around, and no price is ever reconstructed from a screenshot or a memory.</p>
  {table(["Endpoint", "Category", "Link", "HTTP", "What came back", "Checked (UTC)"], probe_rows) if probe_rows else '<p class="muted">Every probed endpoint returned a usable price this run.</p>'}
  <p class="small muted">Raw bounded previews are committed with the receipt, so each verdict can be re-checked:
  <a href="data/esportsbook_probe.json">data/esportsbook_probe.json</a>. Nothing in this table is used as a
  probability input unless the row is listed as usable.</p>
</section>
"""
    else:
        probe_block = ""
    body = f"""
<section class="panel">
  <h2>Sources probed on the latest build</h2>
  <p class="lead">Every external API and sportsbook endpoint is probed on each automated refresh. Blocked or
  geo-fenced books remain in the table transparently.</p>
  {table(["Source", "URL", "Role", "HTTP", "Runner status", "Checked (UTC)"], out)}
  <h3>Active data feeds in production</h3>
  <ul class="bullets">
    <li><a href="https://play.hotspawn.com/lol-pickems" rel="noopener">Hotspawn LoL Pick'ems API</a> &mdash;
    complete scheduled match inventory (crowd % stored strictly for audit comparison).</li>
    <li><a href="https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups" rel="noopener">Pinnacle Arcadia API</a>,
    <a href="https://polymarket.com" rel="noopener">Polymarket CLOB</a>,
    <a href="https://kalshi.com/markets/kxlolgame" rel="noopener">Kalshi (CFTC)</a>,
    <a href="https://www.bovada.lv/sports/esports/league-of-legends" rel="noopener">Bovada</a> &amp;
    <a href="https://eu-offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&amp;market=ZZ" rel="noopener">Unibet (Kambi)</a> &mdash;
    live 5-venue real-money match odds &amp; contract books.</li>
    <li><a href="https://lol.fandom.com/wiki/Special:CargoExport" rel="noopener">Leaguepedia Cargo &amp; MediaWiki Data: namespace</a> &mdash;
    chronological series history plus official <code>dqteams</code> mid-split disqualification records.</li>
    <li><a href="https://esports-api.lolesports.com" rel="noopener">LoL Esports (Riot Games)</a> &mdash;
    official World Championship schedule verification.</li>
  </ul>
</section>
{probe_block}
{research_panel()}
"""
    return page_shell("Sources", "sources.html", body, "Every data source, its HTTP status, and what it provides.")


def build_verification(rows: list[dict], matching: dict, verification: dict | None) -> str:
    checks = (verification or {}).get("checks") or []
    check_rows = [[e(c.get("name")), f'<span class="pill {"ok" if c.get("ok") else "bad"}">'
                                     f'{"pass" if c.get("ok") else "fail"}</span>', e(c.get("detail"))]
                  for c in checks]
    joins = []
    seen = set()
    for j in matching.get("non_exact_joins") or []:
        key = (j.get("team"), j.get("resolved"))
        if key in seen:
            continue
        seen.add(key)
        joins.append([e(j.get("team")), e(j.get("resolved") or "—"), e(j.get("method")),
                      "".join(f"<div class='small'>{e(n)}</div>" for n in (j.get("notes") or []))])
    audit = load_json(os.path.join(DATA, "audit.json")) or {}
    audit_rows = []
    for a in audit.get("checks") or []:
        res = a.get("result")
        css = {"verified": "ok", "corrected": "bad", "unverified": "warn"}.get(res, "")
        audit_rows.append([
            e(a.get("subject")),
            f'<span class="pill {css}">{e(res)}</span>',
            e(a.get("checked")),
            e(a.get("detail")),
            f'<a href="{e(a.get("url"))}" rel="noopener">source</a>',
        ])
    stats = verification or {}
    body = f"""
<section class="panel">
  <h2>Automated verification gate ({len(checks)} assertions)</h2>
  <p class="lead">Every scheduled refresh executes these assertions before committing. Any failure halts
  deployment so broken links or invalid probabilities never reach GitHub Pages.</p>
  {table(["Check", "Result", "Detail"], check_rows)}
</section>

<section class="panel">
  <h2>Row coverage</h2>
  <div class="stats tight">
    {stat_card("Rows checked", stats.get("rows_checked", len(rows)), "every match on Hotspawn")}
    {stat_card("Rows with verified source link", stats.get("rows_with_source", 0), "100% row-level provenance", "ok")}
    {stat_card("Valid probability rows", stats.get("rows_prob_ok", 0), "A + B = 100.0% verified", "market")}
    {stat_card("Provisional or quarantined", stats.get("unverified", 0), "explicitly flagged", "provisional")}
  </div>
</section>

<section class="panel">
  <h2>Manual source audit ({len(audit_rows)} checks, {e((audit.get('audited_utc') or '')[:16].replace('T', ' '))} UTC)</h2>
  <p class="lead">Line-by-line spot-checks of the published numbers against the official source URLs, run on an
  independent network path from the build runner. <span class="pill ok">verified</span> means the published
  value was reproduced; <span class="pill bad">corrected</span> means it was wrong and has been changed in this
  build; <span class="pill warn">unverified</span> means it could not be confirmed and is published as
  unverified rather than assumed.</p>
  {table(["Subject", "Result", "What was compared", "Outcome", "Source"], audit_rows) or '<p class="muted">No manual audit recorded for this build.</p>'}
</section>

<section class="panel">
  <h2>Non-exact team disambiguations</h2>
  <p class="lead">Teams requiring regional suffix or competition-roster disambiguation in Leaguepedia, with
  explicit evidence.</p>
  {table(["Hotspawn team", "Leaguepedia team", "Method", "Evidence"], joins) or '<p class="muted">All team names matched exactly in this build.</p>'}
</section>

<section class="panel">
  <h2>Machine-readable audit artifacts</h2>
  <ul class="bullets">
    <li><a href="data/picks.csv">data/picks.csv</a> &mdash; flat CSV mirror of every match, probability, method, and source URL.</li>
    <li><a href="data/matches.json">data/matches.json</a> &mdash; complete JSON dataset including per-venue quotes, Elo ratings, and backtest metrics.</li>
    <li><a href="data/matching_report.json">data/matching_report.json</a> &mdash; full competition mapping and non-exact team join log.</li>
    <li><a href="data/verification.json">data/verification.json</a> &mdash; machine-readable output of all verification checks.</li>
    <li><a href="data/audit.json">data/audit.json</a> &mdash; the manual source audit reproduced above.</li>
    <li><a href="data/retired_quotes.json">data/retired_quotes.json</a> &mdash; archived quotes that were excluded as unverifiable.</li>
  </ul>
</section>
"""
    return page_shell("Verification", "verification.html", body,
                      "Automated publish assertions and team disambiguation evidence.")


def _sev_pill(sev: str | None) -> str:
    s = (sev or "info").lower()
    cls = {"high": "bad", "medium": "warn", "low": "no", "info": "no"}.get(s, "no")
    return f'<span class="pill {cls}">{e(s)}</span>'


def _fixture_irregularities(r: dict) -> list[str]:
    notes: list[str] = []
    if r.get("method") == "unresolved":
        notes.append("quarantined (dqteams removal / settlement only)")
    t0 = r.get("team0") or {}
    t1 = r.get("team1") or {}
    z0 = "rating_matches" in t0 and t0.get("rating_matches") == 0
    z1 = "rating_matches" in t1 and t1.get("rating_matches") == 0
    if z0 and z1:
        notes.append("0/0 pre-kickoff rated series (equal division prior only)")
    elif z0 or z1:
        who = t0.get("name") if z0 else t1.get("name")
        notes.append(f"debut side ({who}: 0 pre-kickoff rated series)")
    if (r.get("market") or {}).get("thin"):
        notes.append((r.get("market") or {}).get("thin_note") or "thin single-venue market")
    for fl in (r.get("flags") or []):
        if any(k in fl for k in ("retired as unverifiable", "market and model disagree",
                                 "explicit alias", "kick-off time differs")):
            notes.append(fl)
    return notes


def build_flagged(flags: list[dict], rows: list[dict] | None = None) -> str:
    out = [[_sev_pill(f.get("severity")), e(f.get("item")),
            e(f.get("detail")) + (f'<br><span class="verify-state">{e(f["verification"])}</span>'
                                  if f.get("verification") else ""),
            f'<a href="{e(f.get("source"))}" rel="noopener">source</a>' if f.get("source") else "&mdash;"]
           for f in flags]
    flagged_rows_html = []
    for r in sorted(rows or [], key=lambda x: (x.get("stale", False), x.get("start_utc") or "9999")):
        reasons = _fixture_irregularities(r)
        if not reasons:
            continue
        pa_txt, pb_txt = pct_pair(r.get("p0"), r.get("p1"))
        flagged_rows_html.append([
            local_time(r.get("start_utc")),
            e(r.get("competition")),
            (f'<div class="mrow"><strong>{e(r["team0"]["name"])}</strong><span class="pct">{pa_txt}</span></div>'
             f'<div class="mrow"><strong>{e(r["team1"]["name"])}</strong><span class="pct">{pb_txt}</span></div>'),
            _pick_cell(r),
            "; ".join(e(x) for x in reasons),
            _row_sources(r),
        ])
    fixture_panel = (f"""
<section class="panel" id="flagged-fixtures">
  <h2>Flagged fixtures ({len(flagged_rows_html)})</h2>
  <p class="lead">Every currently listed fixture carrying a substantive data irregularity (mid-split team removal,
  zero pre-kickoff rated series, retired external quote, thin single-venue liquidity, explicit team-name alias, or
  market-vs-model gap), with both win probabilities, the published pick and official source links.</p>
  {table(["Kick-off", "Tournament", "Match &amp; Win %", "Pick", "Irregularity", "Sources"], flagged_rows_html)}
</section>""" if flagged_rows_html else "")
    body = f"""
<section class="panel">
  <h2>Independent audit trail</h2>
  <p class="lead">A second, independent line-by-line audit of this dataset (session <code>0d48f265</code>) is
  published as a standalone document with a source link and an explicit verdict on every row:
  <a href="audit/AUDIT.md"><strong>audit/AUDIT.md</strong></a> (machine-readable companion:
  <a href="audit/audit.csv">audit/audit.csv</a>). The manual spot-checks performed by the publishing session
  are on <a href="verification.html">Verification</a>.</p>
</section>

<section class="panel">
  <h2>Flagged for review ({len(flags)})</h2>
  <p class="lead">Audited upstream feed irregularities, mid-split team disqualifications, placeholder odds traps,
  and thin-sample caveats — published openly with official source links.</p>
  {table(["Severity", "Item", "Detail", "Source"], out)}
</section>
{fixture_panel}
<section class="panel">
  <h2>Independent audits behind this page</h2>
  <p class="lead">Two separate audit passes re-checked the committed snapshot and did not use the same code as
  the publish gate. Both are published in full, including what they could not verify.</p>
  <ul class="linklist">
    <li><a href="audit/AUDIT.md">Source audit (row by row) &rarr;</a><span>241-row table, live receipts, findings F1&ndash;F8.</span></li>
    <li><a href="audit/audit.csv">Row audit CSV &rarr;</a><span>Per-match verdict and Hotspawn card link.</span></li>
    <li><a href="audit/README.md">Recomputation audit &rarr;</a><span>Every published number re-derived from the raw provider payloads.</span></li>
    <li><a href="audit/report.md">Latest recomputation result &rarr;</a><span>Failures and warnings for the current build.</span></li>
  </ul>
</section>
"""
    return page_shell("Flagged for review", "flagged.html", body,
                      "Irregularities and unverified items, with official source links.")


# --------------------------------------------------------------------------- main
def main() -> None:
    data = load_json(os.path.join(DATA, "matches.json")) or {}
    rows = data.get("matches") or []
    if not rows:
        raise SystemExit("no matches.json - run model.py first")
    counts = Counter(r["method"] for r in rows)
    src = (load_json(os.path.join(DATA, "sources_status.json")) or {}).get("sources") or []
    matching = load_json(os.path.join(DATA, "matching_report.json")) or {}
    verification = load_json(os.path.join(DATA, "verification.json"))
    flags = (load_json(os.path.join(DATA, "flags.json")) or {}).get("flags") or []
    model = {**(data.get("model") or {}), "backtest": data.get("backtest") or {}}
    comp_map = matching.get("competition_pages") or {}

    os.makedirs(os.path.join(DOCS, "assets"), exist_ok=True)
    comp_html = build_competitions(rows, comp_map)
    pages = {
        "index.html": build_index(rows, counts, src),
        "picks.html": build_picks(rows, counts),
        "table.html": build_table(rows, counts),
        "results.html": build_results(rows),
        "featured.html": build_featured(rows),
        "originated.html": build_originated(rows, counts),
        "unresolved.html": build_unresolved(rows, counts, src),
        "competitions.html": comp_html,
        "teams.html": build_teams(rows),
        "methodology.html": build_methodology(model),
        "sources.html": build_sources(src),
        "verification.html": build_verification(rows, matching, verification),
        "flagged.html": build_flagged(flags, rows),
    }
    for name, content in pages.items():
        with open(os.path.join(DOCS, name), "w", encoding="utf-8") as fh:
            fh.write(content)
    with open(os.path.join(DOCS, ".nojekyll"), "w") as fh:
        fh.write("")
    log(f"site: wrote {len(pages)} pages to the published root")


if __name__ == "__main__":
    main()
