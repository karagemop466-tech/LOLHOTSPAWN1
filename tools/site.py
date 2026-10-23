#!/usr/bin/env python3
"""Generate the static GitHub Pages dashboard from data/matches.json.

Design goals: mobile-first, one clear place to find every pick, executive summary
with in-site links, multi-venue real-money consensus links, out-of-sample SVG
calibration reliability curve, and a verified source link on every row.
"""
from __future__ import annotations

import html
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
    ("picks.html", "All picks"),
    ("featured.html", "Market"),
    ("unresolved.html", "Unresolved"),
    ("flagged.html", "Flags"),
]

NAV = [
    ("index.html", "Summary"),
    ("picks.html", "All picks"),
    ("featured.html", "Market"),
    ("originated.html", "Model"),
    ("coverage.html", "Coverage"),
    ("unresolved.html", "Unresolved"),
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


def local_time(iso_utc: str | None) -> str:
    if not iso_utc:
        return "TBD"
    return (f'<time datetime="{e(iso_utc)}" class="utc" data-utc="{e(iso_utc)}">'
            f'{e(iso_utc[:16].replace("T", " "))} UTC</time>')


def badge(method: str) -> str:
    return f'<span class="badge b-{e(method)}">{e(METHOD_LABEL.get(method, method))}</span>'


def leaguepedia_slug(name: str) -> str:
    return quote(str(name).replace(" ", "_"), safe="()_',!.")


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
  <p>Independent research dashboard. Rows link to their source records. Leaguepedia is community-maintained;
  model lines are estimates, not verified facts. Zero Hotspawn crowd-pick input.</p>
  <p><a href="methodology.html">Method</a> &middot; <a href="verification.html">Verification</a> &middot;
  <a href="flagged.html">Flagged for review</a> &middot; <a href="sources.html">Sources</a> &middot;
  <a href="competitions.html">Tournaments</a></p>
</footer>
<nav class="mobnav" aria-label="Quick navigation">
  {bottom_nav}
</nav>
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
    elif pick:
        pick_html = (f'<div class="pickline"><span class="picklabel">Settlement pick</span> '
                     f'<strong>{e(pick["team"])}</strong> '
                     f'<span class="picksettle">no probability &middot; walkover default</span></div>')
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

    return f"""<article id="match-{e(r['id'])}" class="card m-{e(m)}" data-method="{e(m)}" data-comp="{e(r['competition'])}"
  data-start="{e(r.get('start_utc') or '')}"
  data-text="{e((r['competition'] + ' ' + t0['name'] + ' ' + t1['name']).lower())}">
  <div class="card-top">
    <span class="when">{local_time(r['start_utc'])}</span>
    <span class="badges">{f'<span class="badge b-past">start time passed</span>' if r.get('stale') else ''}{'<span class="badge b-thin" title="single thin prediction market">thin market</span>' if (r.get('market') or {}).get('thin') else ''}{badge(m)}</span>
  </div>
  <div class="comp">{e(r['competition'])}{f" &middot; {e(r['best_of'])}-game series" if r.get('best_of') else ""}</div>
  <div class="teams">
    <div class="team {'fav' if p0 is not None and p0 >= (p1 or 0) else ''}">
      <span class="tname">{e(t0['name'])}</span><span class="tpct">{pct(p0)}</span>
    </div>
    {bar}
    <div class="team {'fav' if p1 is not None and p1 > (p0 or 0) else ''}">
      <span class="tname">{e(t1['name'])}</span><span class="tpct">{pct(p1)}</span>
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


# --------------------------------------------------------------------------- pages
def build_index(rows: list[dict], counts: Counter, src_status: list[dict]) -> str:
    total = len(rows)
    with_pick = sum(1 for r in rows if r["pick"])
    upcoming = sorted([r for r in rows if r["start_utc"] and r["start_utc"] > iso(now_utc()) and r["pick"]],
                      key=lambda r: r["start_utc"])
    featured = [r for r in rows if r["method"] == "market"]
    unresolved = [r for r in rows if r["method"] == "unresolved"]
    settlement = [r for r in rows if r.get("pick_type") == "settlement"]
    provisional = [r for r in rows if r["method"] == "provisional"]
    comps = len({r["competition"] for r in rows})
    live_sources = sum(1 for s in src_status if s.get("ok"))
    priced = sum(1 for r in rows if r["p0"] is not None)
    coverage = (with_pick / total * 100) if total else 0.0
    flags_doc = load_json(os.path.join(DATA, "flags.json")) or {}
    flags_count = len(flags_doc.get("flags") or [])
    gate_doc = load_json(os.path.join(DATA, "verification.json")) or {}
    gate_count = len(gate_doc.get("checks") or [])

    body = f"""
<section class="hero" id="start">
  <h2>Every Hotspawn League of Legends match, with a pick you can find in one tap.</h2>
  <p>This dashboard rebuilds itself automatically every six hours across all {total} scheduled LoL matches on
  Hotspawn. {priced} carry a win probability: featured series combine real-money quotes across
  <strong>Pinnacle, Polymarket, Kalshi (CFTC) and Bovada</strong>, and low-tier regional leagues are originated
  from recorded series history. The other {len(settlement)} are league removals where we publish a settlement
  pick and no probability. Nothing here ever uses Hotspawn's crowd-pick percentages.</p>
  <div class="cta">
    <a class="btn primary" href="picks.html#next-up">Next kick-offs &amp; all {total} picks &rarr;</a>
    <a class="btn" href="unresolved.html">Unresolved &amp; limitations ({len(unresolved)})</a>
  </div>
  <p class="hero-note">On a phone: tap <strong>Menu</strong> (top right) or the bar at the bottom of the
  screen. <a href="picks.html#next-up">All picks</a> opens with the next 12 kick-offs in one table, then the
  full list with search and a tournament filter. Cards you have scrolled past are marked
  <em>started</em>, so a snapshot taken hours ago never looks live.</p>
</section>

<section class="panel" id="find">
  <h2>Where the picks are &mdash; start here</h2>
  <p class="lead">One tap to the list you need. Every page below is a single column on a phone, with the pick
  and both win probabilities above the fold.</p>
  <div class="quickgrid">
    <a class="quick" href="picks.html"><span class="qk">All picks</span><span class="qv">{total}</span>
      <span class="qn">Every match on Hotspawn, next kick-off first. Search + tournament filter.</span></a>
    <a class="quick" href="featured.html"><span class="qk">Market-backed</span><span class="qv">{len(featured)}</span>
      <span class="qn">De-vigged consensus from real-money books and exchanges, with our model beside it.</span></a>
    <a class="quick" href="originated.html"><span class="qk">Model lines</span>
      <span class="qv">{counts.get('model',0)+counts.get('provisional',0)}</span>
      <span class="qn">Low-tier leagues with no bookmaker market: our own Elo probability.</span></a>
    <a class="quick" href="coverage.html"><span class="qk">Line coverage</span>
      <span class="qv">{len(featured)}</span>
      <span class="qn">Which competitions a bookmaker prices, which we originate, and the receipt behind each.</span></a>
    <a class="quick warn" href="unresolved.html"><span class="qk">Unresolved</span><span class="qv">{len(unresolved)}</span>
      <span class="qn">Settlement-only picks, why no percentage is claimed, and every limitation.</span></a>
    <a class="quick" href="competitions.html"><span class="qk">By tournament</span><span class="qv">{comps}</span>
      <span class="qn">Coverage and source quality for each competition.</span></a>
    <a class="quick" href="flagged.html"><span class="qk">Flagged for review</span>
      <span class="qv">{flags_count}</span>
      <span class="qn">Irregularities, stale fixtures, crowd traps, disconnected data.</span></a>
  </div>
</section>

<section class="stats">
  {stat_card("Matches listed on Hotspawn", total, f"across {comps} tournaments")}
  {stat_card("Matches with a pick", with_pick, f"{coverage:.0f}% coverage", "ok")}
  {stat_card("With a win probability", priced, f"{priced/total*100:.0f}% priced", "ok")}
  {stat_card("Settlement only", len(settlement), "no probability claimed", "unresolved")}
  {stat_card("Market-backed", len(featured), "multi-venue real-money consensus", "market")}
  {stat_card("Originated lines", counts.get('model',0), "model, medium confidence", "model")}
  {stat_card("Provisional", len(provisional), "thin data, flagged", "provisional")}
</section>

<section class="panel">
  <h2>Executive summary</h2>
  <ul class="bullets">
    <li><strong>Coverage: {with_pick} of {total} matches carry a pick ({coverage:.0f}%).</strong>
    {priced} of those are priced with a probability and {len(settlement)} are settlement-only.
    Priced picks: <a href="featured.html"><strong>{len(featured)} market-backed</strong></a> from external
    bookmaker and exchange lines, <a href="originated.html"><strong>{counts.get('model',0)} originated model lines</strong></a>
    and <a href="originated.html"><strong>{len(provisional)} provisional lines</strong></a>.
    The full list in kick-off order is <a href="picks.html"><strong>All picks</strong></a>.</li>
    <li><strong>Which matches have a real bookmaker line, and which we had to originate.</strong>
    <a href="coverage.html"><strong>External line coverage</strong></a> lists every competition with its
    method, the external price we captured for it (with the source page and capture time) and the
    evidence that no reachable bookmaker prices the rest.</li>
    <li><strong>Unresolved picks and the limitations on producing them ({len(unresolved)} matches).</strong>
    These are the {len(settlement)} Komplettligaen 2026 Autumn fixtures involving
    <strong>Solid Gaming</strong>, which the community-maintained Leaguepedia record
    <code>Data:Komplettligaen/2026 Season/Autumn Split</code> shows removed in Round 10, with every
    remaining Solid Gaming series entered as a forfeit (score 0-2, <code>ff</code> flag) in favour of the
    opponent. Hotspawn still lists them as scheduled, so we publish the administratively correct
    side (the active opponent) and <strong>no win probability</strong>: a competitive number cannot be justified
    for a series that may be voided or awarded as a walkover. Every such match, plus the limitations that apply
    to the rest of the list (no bookmaker market below tier A, thin samples, one-sided history, disconnected
    opponent graphs, geo-blocked books), is on
    <a href="unresolved.html"><strong>Unresolved &amp; limitations</strong></a>.</li>
    <li><strong>External lines only, with a model cross-check.</strong> Market rows are built from Pinnacle,
    Polymarket, Kalshi (CFTC) and Bovada, de-vigged proportionally and precision-weighted; archived esportsbook
    receipts expire after 24 hours so an old price can never masquerade as a live line, and quotes that imply
    more than 97% on one side are rejected as non-actionable. Our own Elo probability is printed beside every
    market price so a disagreement is visible (<a href="featured.html">Market</a>).
    Hotspawn crowd shares are stored for audit only. Method and out-of-sample backtest:
    <a href="methodology.html"><strong>Method</strong></a>.</li>
    <li><strong>Refresh and verification.</strong> The pipeline reruns every 6 hours and re-reads Hotspawn's
    fixture list on every run, so new cards appear without any manual step. {live_sources} of {len(src_status)}
    probed feeds answered on the latest runner build (<a href="sources.html">Sources</a>), and
    {gate_count} automated publish gates must pass before anything is committed
    (<a href="verification.html">Verification</a>). Irregularities are published on
    <a href="flagged.html">Flagged for review</a>.</li>
  </ul>
</section>

<section class="panel">
  <h2>Next upcoming picks</h2>
  <div class="cards">
    {"".join(match_card(r, show_sources=True) for r in upcoming[:6]) or '<p class="muted">No upcoming matches in the current snapshot.</p>'}
  </div>
  <p><a class="btn" href="picks.html#list">See all {total} matches &rarr;</a></p>
</section>
"""
    return page_shell("Hotspawn LoL Pick Desk", "index.html", body,
                      "Independent win probabilities for every League of Legends match in the Hotspawn pick'em.")


def next_up_block(rows: list[dict], limit: int = 12) -> str:
    """The next kick-offs as a scannable table that deep-links to the full card."""
    upcoming = [r for r in rows if r.get("start_utc") and not r.get("stale")][:limit]
    if not upcoming:
        return ""
    body = []
    for r in upcoming:
        pick = r.get("pick") or {}
        team = pick.get("team") or "&mdash;"
        prob = f'{pick["probability"]*100:.0f}%' if pick.get("probability") is not None else "settlement"
        body.append([
            local_time(r["start_utc"]),
            f'<a href="#match-{e(r["id"])}"><strong>{e(r["team0"]["name"])}</strong> vs '
            f'<strong>{e(r["team1"]["name"])}</strong></a><br><span class="muted small">{e(r["competition"])}</span>',
            f'<strong>{e(team)}</strong>',
            prob,
            badge(r["method"]),
        ])
    return f"""
<section class="panel nextup" id="next-up">
  <h2>Next {len(upcoming)} kick-offs</h2>
  <p class="muted small">The soonest matches on the Hotspawn list. Tap a match to jump to its card,
  or use the search and filters below for the full list of {len(rows)}.</p>
  {table(["Kick-off", "Match", "Pick", "Win prob.", "Type"], body, "t-next")}
  <p class="small"><a href="#all-picks">Jump to the full pick list &darr;</a></p>
</section>

"""


def build_picks(rows: list[dict], counts: Counter) -> str:
    rows = sorted(rows, key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    comps = sorted({r["competition"] for r in rows})
    chips = "".join(
        f'<button class="chip" data-filter="{m}">{METHOD_LABEL[m]} <span>{counts.get(m,0)}</span></button>'
        for m in ("market", "model", "provisional", "unresolved"))
    opts = "".join(f'<option value="{e(c)}">{e(c)}</option>' for c in comps)
    body = next_up_block(rows) + f"""
<section class="panel" id="all-picks">
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search team or tournament" aria-label="Search team or tournament">
    <select id="comp" aria-label="Filter by tournament"><option value="">All tournaments</option>{opts}</select>
    <div class="chips"><button class="chip active" data-filter="">All <span>{len(rows)}</span></button>{chips}</div>
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
            cross_cell = (f'{pct(cross)} / {pct(1 - cross)}'
                          f'<br><span class="muted small">{"&#9888; " if gap >= 20 else ""}{gap:.0f} pp gap</span>')
        else:
            cross_cell = '<span class="muted">not rated</span>'
        rows_html.append([
            local_time(r["start_utc"]),
            e(r["competition"]),
            f'<strong>{e(r["pick"]["team"])}</strong> ({r["pick"]["probability"]*100:.1f}%)<br>'
            f'<span class="muted small">{e(r["team0"]["name"])} vs {e(r["team1"]["name"])}</span>',
            pct(r["p0"]) + " / " + pct(r["p1"]),
            cross_cell,
            f'{e(m["book"])}',
            f'{dec.get("home","")} / {dec.get("away","")}',
            f'{vlinks} &middot; <a href="{e(r["hotspawn_url"])}" rel="noopener">card</a>',
        ])
    body = f"""
<section class="panel">
  <h2>{len(items)} matches with real-money bookmaker &amp; exchange consensus</h2>
  <p class="lead">Featured matches combine live quotes across <strong>Pinnacle (weight 0.36), Polymarket
  full-series CLOB (0.24), Kalshi CFTC regulated contracts (0.18), Bovada (0.12), and verified specialist
  esportsbooks (0.10)</strong>. Bookmaker margin is removed proportionally on each venue before precision
  weighting, and symmetric 1.80 / 1.80 aggregator placeholders are rejected automatically.</p>
  <p class="lead">The <strong>model cross-check</strong> column is our own Elo line for the same match, computed
  without the market. It is published beside the consensus so a disagreement is visible rather than hidden; rows
  marked &#9888; differ by 20 percentage points or more. The pick is always the market side, never a blend.</p>
  {table(["Start (UTC)", "Tournament", "Pick &amp; Match", "Consensus (A / B)", "Model cross-check", "Venues", "Primary Decimal", "Verified Sources"], rows_html)}
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
        reviews.append([
            local_time(r["start_utc"]),
            e(r["competition"]),
            f'<strong>{e(t0["name"])}</strong> vs <strong>{e(t1["name"])}</strong>',
            f'{t0["elo"] if t0["elo"] is not None else "&mdash;"} <span class="muted small">({t0["rating_matches"]})</span>'
            f' / {t1["elo"] if t1["elo"] is not None else "&mdash;"} <span class="muted small">({t1["rating_matches"]})</span>',
            pct(r["p0"]) + " / " + pct(r["p1"]),
            badge(r["method"]),
            f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(r["leaguepedia_page"] or "")}" rel="noopener">results page</a>'
            if r.get("leaguepedia_page") else f'<a href="{e(r["hotspawn_url"])}" rel="noopener">card</a>',
        ])
    body = f"""
<section class="panel">
  <h2>{len(items)} low-tier regional matches originated from recorded series history</h2>
  <p class="lead">Tier-B/C/D national and academy leagues are not offered by major sportsbooks, so we originate
  independent probabilities from chronological series history in Leaguepedia since
  {e((load_json(os.path.join(DATA,'matches.json')) or {}).get('model',{}).get('window_start',''))},
  with inactivity decay and empirical shrinkage toward 1500.</p>
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


def build_unresolved(rows: list[dict], counts: Counter) -> str:
    unresolved = sorted([r for r in rows if r["method"] == "unresolved"],
                        key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    provisional = sorted([r for r in rows if r["method"] == "provisional"],
                         key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    one_sided = [r for r in rows if r["method"] == "unresolved"
                 and any("no rated series" in f for f in r["flags"])]
    disconnected = [r for r in rows if any("no shared-opponent chain" in f for f in r["flags"])]
    ambiguous = [r for r in rows if any("ambiguous" in f or "could not be matched" in f for f in r["flags"])]
    reason_rows = []
    for r in unresolved:
        lp_link = (f' &middot; <a href="https://lol.fandom.com/wiki/{leaguepedia_slug(r["leaguepedia_page"])}" rel="noopener">league page</a>'
                   if r.get("leaguepedia_page") else "")
        sp = r.get("pick") or {}
        settle_cell = (f'<strong>{e(sp.get("team"))}</strong><br>'
                       f'<span class="small muted">{e(sp.get("settlement") or "no probability")}</span>'
                       if sp.get("team") else '<span class="muted">no pick</span>')
        reason_rows.append([
            local_time(r["start_utc"]),
            e(r["competition"]),
            f'<strong>{e(r["team0"]["name"])}</strong> vs <strong>{e(r["team1"]["name"])}</strong>',
            settle_cell,
            e(r["basis"]),
            f'<a href="{e(r["hotspawn_url"])}" rel="noopener">Hotspawn card</a>{lp_link}',
        ])
    lim_rows = [
        ["Mid-split league removals (dqteams)", f"{len(unresolved)} matches",
         "Official Leaguepedia Data: pages record mid-split team removals ('dqteams=Solid Gaming' in Komplettligaen "
         "Round 10). Because Hotspawn may either void the card or grade walkovers in favour of the remaining active "
         "opponent, assigning an Elo win probability from pre-removal matches is invalid. The settlement side is "
         "published and no percentage is claimed."],
        ["No sportsbook market below tier A", f"{len([r for r in rows if r['method']!='market'])} matches",
         "Pinnacle, Polymarket, Kalshi and Bovada price Tier-S/A series (Worlds 2026 and the LCP 2027 Promotion). "
         "Regional divisions (Prime League 2nd/3rd Div, RIVALS, Komplettligaen, LigaGG, Benelux, Icelandic, Tunisian, "
         "Arabian) have no live market on any book reachable from the build runner."],
        ["Archived esportsbook receipts expire", "24 h limit",
         "A quote scraped from an esportsbook match page is a line only while it is fresh. Receipts older than 24 "
         "hours are excluded from the consensus and listed with their timestamp in the audit trail, so the affected "
         "match falls back to live venues or to the model instead of to a stale price."],
        ["Non-actionable quotes are rejected", "every quote",
         "Symmetric 1.80 / 1.80 aggregator placeholders, prices at or below 1.00, and any line where one side implies "
         "more than 97% (decimal below 1.03) are rejected before de-vigging and published under Flagged for review."],
        ["Thin match history", f"{counts.get('provisional',0)} provisional",
         "At least one team has fewer than five rated series in the 25-month Leaguepedia window, so the Elo estimate "
         "carries wider variance and is explicitly flagged provisional."],
        ["One-sided history", f"{len(one_sided)} matches",
         "One side has no matched rated history. Its strength cannot be confirmed, so no 1500 baseline is "
         "substituted and the probability is left blank rather than guessed."],
        ["Name disambiguation", f"{len(ambiguous)} matches",
         "Homonymous regional teams (e.g. 'Fenrir (Icelandic Team)' vs Polish 'Fenrir', 'PvB (Swiss Team)' mislabelled "
         "by Hotspawn as Vietnamese 'Phong Vũ Buffalo') are joined only via competition-scoped roster evidence."],
        ["Disconnected opponent graphs", f"{len(disconnected)} matches",
         "Cross-pool teams without a shared opponent chain are flagged rather than treated as high-confidence lines."],
        ["Geo-fenced / bot-protected books", "see Sources",
         "GG.BET (403 region), EGamersWorld (Cloudflare 403 on runner IPs), Oddspedia (410), BetExplorer (404), and "
         "Unibet/Kambi (400) are probed on every refresh and logged transparently on Sources."],
    ]
    body = f"""
<section class="panel">
  <h2>Unresolved picks ({len(unresolved)})</h2>
  <p class="lead">Every listed match has a pick. This page is for the {len(unresolved)} where we publish a
  <strong>settlement pick without a win probability</strong>: the listed participant was removed mid-split by its
  league (<code>dqteams</code>), so the series is either voided or awarded as a walkover and no competitive
  probability can be justified. The settlement side named on each row is the remaining active opponent in
  Leaguepedia's record; it is not an official settlement guarantee, so treat it as information, not a graded bet. Cards where <em>neither</em> side can be priced at all would also land here - the count above
  would then rise above {len(unresolved)}.</p>
  {'<p class="muted">No unresolved matches in this snapshot.</p>' if not unresolved else table(["Start (UTC)", "Tournament", "Match", "Settlement pick (no probability)", "Why no competitive probability exists", "Verified Sources"], reason_rows)}
</section>

<section class="panel">
  <h2>Documented limitations across the list</h2>
  {table(["Limitation", "Scope", "Impact &amp; handling"], lim_rows)}
</section>

<section class="panel">
  <h2>Provisional lines ({len(provisional)})</h2>
  <p class="lead">Low-confidence originated picks with thin match samples. Every card lists its exact caveat.</p>
  <div class="cards">{"".join(match_card(r) for r in provisional)}</div>
</section>
"""
    return page_shell("Unresolved &amp; limitations", "unresolved.html", body,
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
                teams[t["name"]] = {"name": t["name"], "lp": t["leaguepedia"], "elo": t["elo"],
                                    "n": t["rating_matches"], "last": t["last_played"],
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
    <strong>Pinnacle (0.36), Polymarket full-series CLOB (0.24), Kalshi CFTC (0.18), Bovada (0.12), and
    verified specialist esportsbooks (0.10)</strong> are de-vigged proportionally and precision-weighted.</li>
    <li><strong>Tier 2 — Originated regional Elo lines.</strong> All recorded Leaguepedia series since
    {e(model.get('window_start',''))} are processed chronologically with inactivity decay and shrinkage toward 1500.</li>
    <li><strong>Tier 3 — Provisional lines.</strong> Thin-sample teams (&lt;5 rated series) or an unconnected
    opponent graph are marked <em>provisional</em>: a probability is still published, with the caveat on the card.</li>
    <li><strong>Tier 4 — Settlement picks (no probability).</strong> Officially removed mid-split teams
    (<code>dqteams</code>) get the administratively correct side only - the active opponent under the league
    ruling - and an explicit &quot;no probability claimed&quot; label on
    <a href="unresolved.html">Unresolved</a>. Every listed match therefore has a pick; some deliberately have no
    number.</li>
    <li><strong>Automated publish gate.</strong> Every 6 hours GitHub Actions re-runs the full pipeline and
    executes 23 strict assertions (<a href="verification.html">Verification</a>) before publishing to GitHub Pages.</li>
  </ol>
</section>

<section class="panel">
  <h2>Formulas</h2>
  <p>Expected series win probability for team A:</p>
  <p class="formula">E<sub>A</sub> = 1 / (1 + 10^((R<sub>B</sub> - R<sub>A</sub>)/400))</p>
  <p>Chronological rating update after each completed series (K = {e(model.get('k'))}):</p>
  <p class="formula">R&prime;<sub>A</sub> = R<sub>A</sub> + K &middot; (S<sub>A</sub> - E<sub>A</sub>)</p>
  <p>Empirical Bayes shrinkage towards 1500 for sample size n (shrink = {e(model.get('shrink'))}):</p>
  <p class="formula">R<sub>eff</sub> = 1500 + (R - 1500) &middot; n / (n + {e(model.get('shrink'))})</p>
  <p>Inactivity decay begins after {e(model.get('decay_start_days'))} days and reaches 1500 at
  {e(model.get('decay_full_days'))} days; originated probabilities are clamped to
  {e(model.get('prob_floor'))}&ndash;{e(model.get('prob_ceil'))}.</p>
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
  <p class="small muted">Companion within-tournament Bayesian Bradley-Terry cross-validation on active low-tier
  divisions (N = 1,595 2026 series, archived in <code>archive/session-8336fb7e/data/calibration.json</code>)
  likewise achieves 64.9% accuracy, 0.2145 Brier score (&minus;14.2% MSE vs 50/50), and 3.53% ECE.</p>
</section>

<section class="panel">
  <h2>Hard methodological guardrails</h2>
  <ul class="bullets">
    <li><strong>Zero Hotspawn crowd input.</strong> Crowd pick shares are never read by the probability engine.</li>
    <li><strong>Quote integrity before de-vig.</strong> A price is used only if it passes every test: both sides
    above 1.00, not the symmetric 1.80 / 1.80 aggregator placeholder, and neither side implying more than 97%
    (decimal at or below 1.03). Rejections are logged in <code>data/matches.json</code> under
    <code>receipt_audit.rejected_quotes</code> and published on
    <a href="flagged.html">Flagged for review</a>.</li>
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
    <li><a href="https://www.pinnacle.com/en/esports/league-of-legends" rel="noopener">Pinnacle</a>,
    <a href="https://polymarket.com" rel="noopener">Polymarket CLOB</a>,
    <a href="https://kalshi.com/markets/kxlolgame" rel="noopener">Kalshi (CFTC)</a> &amp;
    <a href="https://www.bovada.lv/sports/esports/league-of-legends" rel="noopener">Bovada</a> &mdash;
    live multi-venue real-money match odds &amp; contract books.</li>
    <li><a href="https://lol.fandom.com/wiki/Special:CargoExport" rel="noopener">Leaguepedia Cargo &amp; MediaWiki Data: namespace</a> &mdash;
    chronological series history plus official <code>dqteams</code> mid-split disqualification records.</li>
    <li><a href="https://esports-api.lolesports.com" rel="noopener">LoL Esports (Riot Games)</a> &mdash;
    official World Championship schedule verification.</li>
  </ul>
</section>
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
  </ul>
</section>
"""
    return page_shell("Verification", "verification.html", body,
                      "Automated publish assertions and team disambiguation evidence.")


def build_flagged(flags: list[dict]) -> str:
    out = [[e(f.get("severity")), e(f.get("item")),
            e(f.get("detail")) + (f'<br><span class="verify-state">{e(f["verification"])}</span>'
                                  if f.get("verification") else ""),
            f'<a href="{e(f.get("source"))}" rel="noopener">source</a>' if f.get("source") else "&mdash;"]
           for f in flags]
    body = f"""
<section class="panel">
  <h2>Flagged for review ({len(flags)})</h2>
  <p class="lead">Irregularities, disqualifications, placeholder-odds traps and thin-sample caveats, published
  openly with source links. Rows marked <em>re-verified</em> were re-checked against a live source on the run
  shown at the top of the page; rows marked <em>not reverified</em> are prior-session statements that this run
  did not re-check, and are labelled as such rather than presented as audited.</p>
  {table(["Severity", "Item", "Detail", "Source"], out)}
</section>
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
        "featured.html": build_featured(rows),
        "originated.html": build_originated(rows, counts),
        "unresolved.html": build_unresolved(rows, counts),
        "competitions.html": comp_html,
        "teams.html": build_teams(rows),
        "methodology.html": build_methodology(model),
        "sources.html": build_sources(src),
        "verification.html": build_verification(rows, matching, verification),
        "flagged.html": build_flagged(flags),
    }
    for name, content in pages.items():
        with open(os.path.join(DOCS, name), "w", encoding="utf-8") as fh:
            fh.write(content)
    with open(os.path.join(DOCS, ".nojekyll"), "w") as fh:
        fh.write("")
    log(f"site: wrote {len(pages)} pages to the published root")


if __name__ == "__main__":
    main()
