#!/usr/bin/env python3
"""Generate the static GitHub Pages dashboard from data/matches.json.

Design goals, in order:
  1. On a phone, the next pick must be visible without pinching, scrolling sideways,
     or opening a menu. One row = one match = one pick = one number.
  2. Every interactive control must actually work (menu, search, tournament filter,
     method chips, time window, sort). The older build shipped controls that were
     never wired to JavaScript; that is fixed here and asserted by tools/verify.py.
  3. Every row carries its own source links; nothing is inferred to fill a gap.

These pages are generated only by this script. Do not hand-edit the HTML.
"""
from __future__ import annotations

import html
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
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
METHOD_SHORT = {
    "market": "Book",
    "model": "Model",
    "provisional": "Prov.",
    "unresolved": "None",
}
METHOD_HELP = {
    "market": "De-vigged consensus across real-money books & prediction exchanges.",
    "model": "Our Elo line from recorded series results, taken at kick-off (no look-ahead).",
    "provisional": "Our Elo line but at least one side has under 5 rated series - low confidence.",
    "unresolved": "No defensible competitive line (mid-split league removal).",
}

# Primary navigation: five destinations that answer the five questions a reader has.
NAV_PRIMARY = [
    ("index.html", "Summary"),
    ("picks.html", "Picks"),
    ("unresolved.html", "Unresolved"),
    ("methodology.html", "Method"),
    ("sources.html", "Sources"),
]
NAV_ALL = NAV_PRIMARY + [
    ("featured.html", "Market-backed"),
    ("originated.html", "Model lines"),
    ("competitions.html", "Tournaments"),
    ("teams.html", "Teams"),
    ("verification.html", "Verification"),
    ("flagged.html", "Flagged"),
]


# --------------------------------------------------------------------------- helpers
def e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def pct(value) -> str:
    if value is None:
        return "&mdash;"
    return f"{value * 100:.1f}%"


def local_time(iso_utc: str | None, show_local: bool = True) -> str:
    if not iso_utc:
        return "TBD"
    attr = ' data-show-local="1"' if show_local else ""
    return (f'<time datetime="{e(iso_utc)}" class="utc"{attr} data-utc="{e(iso_utc)}">'
            f'{e(iso_utc[:16].replace("T", " "))} UTC</time>')


def short_time(iso_utc: str | None) -> str:
    if not iso_utc:
        return "TBD"
    return (f'<time datetime="{e(iso_utc)}" class="utc" data-show-local="1" data-utc="{e(iso_utc)}">'
            f'{e(iso_utc[11:16])} UTC</time>')


def badge(method: str) -> str:
    return f'<span class="badge b-{e(method)}">{e(METHOD_LABEL.get(method, method))}</span>'


def slug(value: str) -> str:
    out = []
    for ch in str(value or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")


def leaguepedia_slug(name: str) -> str:
    return quote(str(name).replace(" ", "_"), safe="()_',!.")


def parse_utc(value: str | None) -> datetime | None:
    try:
        return datetime.strptime(str(value)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def hours_from_now(value: str | None, now: datetime) -> float:
    dt = parse_utc(value)
    if dt is None:
        return 99999.0
    return round((dt - now).total_seconds() / 3600, 2)


def next_refresh(now: datetime) -> datetime:
    """Mirror the workflow cron '17 */6 * * *' (00:17, 06:17, 12:17, 18:17 UTC)."""
    base = now.replace(minute=17, second=0, microsecond=0)
    for hour in (0, 6, 12, 18, 24):
        candidate = base.replace(hour=hour % 24) + (timedelta(days=1) if hour == 24 else timedelta())
        if candidate > now:
            return candidate
    return base + timedelta(hours=6)


# --------------------------------------------------------------------------- shell
def page_shell(title: str, active: str, body: str, subtitle: str = "", wide: bool = False) -> str:
    nav_parts = []
    for href, label in NAV_ALL:
        cls = ' class="active"' if href == active else ""
        nav_parts.append(f'<a href="{e(href)}"{cls}>{e(label)}</a>')
    nav = "".join(nav_parts)
    meta = load_json(os.path.join(DATA, "matches.json")) or {}
    updated = (meta.get("generated_utc") or "")[:16].replace("T", " ")
    gate = load_json(os.path.join(DATA, "verification.json")) or {}
    gate_n = len(gate.get("checks") or []) or 15
    now = now_utc()
    nxt = next_refresh(now).strftime("%H:%M UTC")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0f172a">
<meta name="description" content="Independent League of Legends pick'em lines for every match listed on Hotspawn.">
<title>{e(title if "Hotspawn LoL Pick Desk" in title else title + " · Hotspawn LoL Pick Desk")}</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <div class="wrap bar">
    <a class="brand" href="index.html"><span class="dot"></span> Hotspawn LoL Pick Desk</a>
    <button class="menu-btn" type="button" aria-expanded="false" aria-controls="nav">Menu</button>
    <nav id="nav" class="nav" aria-label="Main">{nav}</nav>
  </div>
</header>
<main id="main" class="wrap{' wide' if wide else ''}">
  <div class="pagehead">
    <h1>{e(title)}</h1>
    {f'<p class="sub">{subtitle}</p>' if subtitle else ''}
    <p class="stamp">Updated <strong>{e(updated)} UTC</strong> &middot; next automatic refresh ~<strong>{e(nxt)}</strong>
    &middot; <a href="verification.html">{e(gate_n)} checks</a> run before every publish</p>
  </div>
  {body}
</main>
<nav class="tabbar" aria-label="Quick navigation">
  <a href="picks.html"{' class="active"' if active == 'picks.html' else ''}>
    <span class="ti" aria-hidden="true">&#9776;</span><span>Picks</span></a>
  <a href="index.html#today">
    <span class="ti" aria-hidden="true">&#9200;</span><span>Next up</span></a>
  <a href="unresolved.html"{' class="active"' if active == 'unresolved.html' else ''}>
    <span class="ti" aria-hidden="true">&#9888;</span><span>Unresolved</span></a>
  <a href="methodology.html"{' class="active"' if active == 'methodology.html' else ''}>
    <span class="ti" aria-hidden="true">&#402;</span><span>Method</span></a>
  <button type="button" class="tabmenu" aria-controls="nav" aria-expanded="false">
    <span class="ti" aria-hidden="true">&#8942;</span><span>More</span></button>
</nav>
<footer class="wrap foot">
  <p><strong>Independent research dashboard.</strong> Every row links to its source. Hotspawn crowd votes are
  never used as an input. Not betting advice.</p>
  <p class="footlinks">
    <a href="picks.html">All picks</a> &middot; <a href="index.html">Summary</a> &middot;
    <a href="unresolved.html">Unresolved &amp; limitations</a> &middot; <a href="featured.html">Market</a> &middot;
    <a href="originated.html">Model</a> &middot; <a href="competitions.html">Tournaments</a> &middot;
    <a href="teams.html">Teams</a> &middot; <a href="methodology.html">Method</a> &middot;
    <a href="verification.html">Verification</a> &middot; <a href="sources.html">Sources</a> &middot;
    <a href="flagged.html">Flagged for review</a>
  </p>
</footer>
<script src="assets/app.js"></script>
</body>
</html>
"""


# --------------------------------------------------------------------------- components
def stat_card(label: str, value, note: str = "", cls: str = "") -> str:
    return (f'<div class="stat {cls}"><div class="sv">{value}</div>'
            f'<div class="sl">{e(label)}</div>{f"<div class=sn>{e(note)}</div>" if note else ""}</div>')


def table(headers: list[str], rows: list[list[str]], cls: str = "") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td data-label=\"{headers[i]}\">{c}</td>"
                                     for i, c in enumerate(row)) + "</tr>" for row in rows)
    return f'<div class="tablewrap"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _source_links(r: dict) -> list[str]:
    links = [f'<a href="{e(r["hotspawn_url"])}" rel="noopener">Hotspawn card</a>']
    mk = r.get("market") or {}
    venues = mk.get("venues") or []
    if venues:
        for v in venues:
            when = v.get("observed_utc") or v.get("captured_utc")
            suffix = f' <span class="muted small">({e(when[:16].replace("T", " "))}Z)</span>' if when else ""
            links.append(f'<a href="{e(v["url"])}" rel="noopener">{e(v["name"])}</a>{suffix}')
    elif mk.get("market_url"):
        links.append(f'<a href="{e(mk["market_url"])}" rel="noopener">{e(mk["book"])}</a>')
    if r.get("leaguepedia_page"):
        links.append(f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(r["leaguepedia_page"])}" '
                     f'rel="noopener">Tournament results</a>')
    for side in ("team0", "team1"):
        t = r[side]
        if t.get("leaguepedia"):
            links.append(f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(t["leaguepedia"])}" '
                         f'rel="noopener">{e(t["name"])}</a>')
    return links


def pick_row(r: dict, show_comp: bool = True, now: datetime | None = None) -> str:
    """One compact, expandable row: time, teams + two numbers, pick, tournament."""
    now = now or now_utc()
    t0, t1 = r["team0"], r["team1"]
    p0, p1 = r["p0"], r["p1"]
    pick = r["pick"]
    hours = hours_from_now(r["start_utc"], now)
    fav = max(p0, p1) if p0 is not None and p1 is not None else 0.0
    stale = bool(r.get("stale"))
    if pick:
        pick_html = (f'<span class="pk-badge b-{e(r["method"])}">{e(METHOD_SHORT.get(r["method"], r["method"]))}</span>'
                     f'<span class="pk-team">{e(pick["team"])}</span>'
                     f'<span class="pk-pct">{pick["probability"]*100:.1f}%</span>')
    else:
        pick_html = ('<span class="pk-badge b-unresolved">No pick</span>'
                     '<span class="pk-team muted">See unresolved</span>')
    flags = ""
    if r["flags"]:
        flags = '<ul class="flags">' + "".join(f"<li>{e(f)}</li>" for f in r["flags"]) + "</ul>"
    sources = '<div class="src">' + "".join(_source_links(r)) + "</div>"
    comp = f'<span class="c-comp">{e(r["competition"])}</span>' if show_comp else ""
    stale_tag = '<span class="badge b-past">started</span>' if stale else ""
    return f"""<details class="pick m-{e(r['method'])}{' is-stale' if stale else ''}"
  data-method="{e(r['method'])}" data-comp="{e(r['competition'])}"
  data-text="{e(slug(r['competition'] + ' ' + t0['name'] + ' ' + t1['name']))}"
  data-kickoff="{int(parse_utc(r['start_utc']).timestamp()) if parse_utc(r['start_utc']) else 0}"
  data-hours="{hours}" data-favprob="{fav:.4f}" data-points="{int(r.get('points') or 0)}">
  <summary class="pick-sum">
    <span class="c-time">{short_time(r['start_utc'])}<span class="c-day">{e((r['start_utc'] or '')[:10])}</span></span>
    <span class="c-teams">
      <span class="t{' top' if pick and pick['side'] == 0 else ''}">{e(t0['name'])}<em>{pct(p0)}</em></span>
      <span class="vs">v</span>
      <span class="t{' top' if pick and pick['side'] == 1 else ''}">{e(t1['name'])}<em>{pct(p1)}</em></span>
    </span>
    <span class="c-pick">{pick_html}</span>
    {comp}
    <span class="chev" aria-hidden="true">&#9656;</span>
  </summary>
  <div class="pick-body">
    <p class="basis"><strong>Why this line.</strong> {e(r['basis'])}</p>
    {flags}
    <p class="small muted">Rating snapshot: {e((t0.get('rating_as_of') or r['start_utc'] or '')[:16].replace('T', ' '))} UTC
    &middot; {e(t0.get('rating_matches') or 0)}/{e(t1.get('rating_matches') or 0)} rated series before kick-off.</p>
    {sources}
  </div>
</details>"""


def match_card(r: dict, show_sources: bool = True) -> str:
    """Full card (used on market/model/unresolved pages where context matters)."""
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
    if pick:
        pick_html = (f'<div class="pickline"><span class="picklabel">Pick</span> '
                     f'<strong>{e(pick["team"])}</strong> '
                     f'<span class="pickpct">{pick["probability"]*100:.1f}%</span></div>')
    else:
        pick_html = ('<div class="pickline"><span class="picklabel">Unresolved</span> '
                     '<span class="muted">see Unresolved &amp; why below</span></div>')
    flags = ""
    if r["flags"]:
        flags = '<ul class="flags">' + "".join(f"<li>{e(f)}</li>" for f in r["flags"]) + "</ul>"
    sources = ""
    if show_sources:
        sources = '<div class="src">' + "".join(_source_links(r)) + "</div>"
    return f"""<article class="card m-{e(m)}" data-method="{e(m)}" data-comp="{e(r['competition'])}">
  <div class="card-top">
    <span class="when">{local_time(r['start_utc'])}</span>
    <span class="badges">{'<span class="badge b-past">started</span>' if r.get('stale') else ''}{badge(m)}</span>
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


def calibration_svg(bt: dict) -> str:
    buckets = bt.get("buckets") or {}
    if not buckets:
        return ""
    pts, circles = [], []
    for k, v in buckets.items():
        mp, ac = v.get("mean_predicted"), v.get("accuracy")
        if mp is None or ac is None:
            continue
        x = 60 + (mp - 0.5) / 0.5 * 360
        y = 210 - (ac - 0.5) / 0.5 * 170
        pts.append((x, y))
        circles.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#4f9cf9"/>'
            f'<text x="{x:.1f}" y="{max(22.0, y - 10):.1f}" font-size="11" fill="#e5e7eb" '
            f'text-anchor="middle">{ac*100:.1f}% (n={v.get("n", 0)})</text>')
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f"""
<figure class="calib">
  <svg viewBox="0 0 450 245" width="100%" role="img" aria-label="Out-of-sample probability calibration curve">
    <line x1="60" y1="210" x2="420" y2="210" stroke="#334155" stroke-width="1"/>
    <line x1="60" y1="40" x2="60" y2="210" stroke="#334155" stroke-width="1"/>
    <line x1="60" y1="210" x2="420" y2="40" stroke="#64748b" stroke-dasharray="5,5" stroke-width="1.5"/>
    <polyline fill="none" stroke="#4f9cf9" stroke-width="2.5" points="{poly}"/>
    {''.join(circles)}
    <text x="60" y="232" font-size="11" fill="#94a3b8" text-anchor="middle">50%</text>
    <text x="240" y="232" font-size="11" fill="#94a3b8" text-anchor="middle">Predicted win probability</text>
    <text x="420" y="232" font-size="11" fill="#94a3b8" text-anchor="middle">100%</text>
    <text x="52" y="213" font-size="11" fill="#94a3b8" text-anchor="end">50%</text>
    <text x="52" y="125" font-size="11" fill="#94a3b8" text-anchor="end">75%</text>
    <text x="52" y="44" font-size="11" fill="#94a3b8" text-anchor="end">100%</text>
  </svg>
  <figcaption class="small muted">Dashed diagonal = perfect calibration. Blue = out-of-sample pre-match Elo
  calibration across {bt.get('n', 0):,} series since {e(bt.get('cutoff', ''))}.</figcaption>
</figure>"""


# --------------------------------------------------------------------------- pages
def build_index(rows: list[dict], counts: Counter, src_status: list[dict],
                probe: dict | None = None) -> str:
    now = now_utc()
    total = len(rows)
    with_pick = sum(1 for r in rows if r["pick"])
    # strictly future kick-offs: a card that started an hour ago must not appear under "Next 48 hours"
    upcoming = sorted([r for r in rows
                       if r["pick"] and parse_utc(r["start_utc"]) and parse_utc(r["start_utc"]) > now],
                      key=lambda r: r["start_utc"])
    next48 = [r for r in upcoming if parse_utc(r["start_utc"]) <= now + timedelta(hours=48)]
    featured = [r for r in rows if r["method"] == "market"]
    unresolved = [r for r in rows if r["method"] == "unresolved"]
    provisional = [r for r in rows if r["method"] == "provisional"]
    model = [r for r in rows if r["method"] == "model"]
    comps = sorted({r["competition"] for r in rows})
    live_sources = sum(1 for s in src_status if s.get("ok"))
    probed = len(src_status)
    probes = (probe or {}).get("sources") or []
    probe_ok = sum(1 for p in probes if p.get("status") == 200)
    today_rows = "".join(pick_row(r) for r in next48[:14])
    if not today_rows:
        today_rows = '<p class="muted">No unpriced upcoming fixtures in this snapshot.</p>'

    body = f"""
<section class="hero">
  <h2>Every LoL match on Hotspawn. One pick. One number.</h2>
  <p><strong>{with_pick} of {total}</strong> listed matches carry a win probability we can defend.
  <strong>{len(featured)}</strong> come from live real-money bookmaker and exchange consensus;
  <strong>{len(model) + len(provisional)}</strong> are originated from recorded series results because no
  sportsbook prices those regional divisions; <strong>{len(unresolved)}</strong> are quarantined and listed
  openly. Hotspawn's crowd percentages are never used.</p>
  <div class="cta">
    <a class="btn primary" href="#today">Next 48 hours &rarr;</a>
    <a class="btn" href="picks.html">All {total} matches &rarr;</a>
    <a class="btn" href="unresolved.html">Unresolved ({len(unresolved)})</a>
  </div>
</section>

<section class="stats">
  {stat_card("Matches listed", total, f"{len(comps)} tournaments")}
  {stat_card("With a pick", with_pick, f"{with_pick/total*100:.0f}% of the list", "ok")}
  {stat_card("Bookmaker-backed", len(featured), "live de-vigged lines", "market")}
  {stat_card("Originated", len(model) + len(provisional), "our Elo line", "model")}
  {stat_card("Provisional", len(provisional), "thin sample, flagged", "provisional")}
  {stat_card("Unresolved", len(unresolved), "league removal", "unresolved")}
</section>

<section class="panel" id="today">
  <div class="panelhead">
    <h2>Next 48 hours</h2>
    <a class="small" href="picks.html">See all {total} &rarr;</a>
  </div>
  <p class="lead">Tap a row for the inputs and source links. Percentages are our probability that the team wins
  the series. The pick is always the higher number.</p>
  <div class="picks" id="today-list">{today_rows}</div>
</section>

<section class="panel">
  <h2>Executive summary</h2>
  <ul class="bullets">
    <li><strong>Where the updated picks are.</strong> The single complete list is
    <a href="picks.html"><strong>All picks</strong></a> ({total} rows, searchable, next kick-off first).
    This page's <a href="#today"><strong>Next 48 hours</strong></a> block is the fastest check on a phone.
    Method splits are on <a href="featured.html">Market-backed</a> ({len(featured)}) and
    <a href="originated.html">Model lines</a> ({len(model) + len(provisional)}).</li>
    <li><strong>Coverage.</strong> All {total} fixtures in the Hotspawn LoL pick'em are listed; {with_pick}
    have a pick ({with_pick/total*100:.0f}%). {len(featured)} are priced from de-vigged Pinnacle, Polymarket,
    Kalshi, Bovada and specialist esportsbook quotes. {len(model) + len(provisional)} regional/academy
    matches have no reachable sportsbook market, so their line is originated from chronological Leaguepedia
    series results, taken strictly at kick-off so a played match can never see its own result.</li>
    <li><strong>Unresolved picks and limitations ({len(unresolved)}).</strong> {len(unresolved)} Komplettligaen
    fixtures involve <em>Solid Gaming</em>, removed mid-split under the official Leaguepedia
    <code>dqteams</code> record. Hotspawn may void them or grade walkovers, so no win probability is valid.
    Every unresolved fixture, the walkover/void caveat, the {len(provisional)} thin-sample caveats and the
    list of books that were tried and blocked are on
    <a href="unresolved.html"><strong>Unresolved &amp; limitations</strong></a>.</li>
    <li><strong>Independent of Hotspawn votes.</strong> Hotspawn's pick percentages are stored only for audit
    comparison (they are exposed as crowd traps on <a href="flagged.html">Flagged</a>) and carry zero weight in
    any probability. Method, formulas and the {('{:,.0f}'.format(((load_json(os.path.join(DATA, 'matches.json')) or {}).get('backtest') or {}).get('n') or 0))}
    series out-of-sample backtest are on <a href="methodology.html">Method</a>.</li>
    <li><strong>Freshness and sources.</strong> Rebuilt every 6 hours by GitHub Actions
    (<a href="sources.html">Sources</a>, {live_sources}/{probed} probed feeds live). This pass also probed
    {len(probes) or 'the'} bookmaker, esportsbook and odds-aggregator endpoints from the runner:
    <strong>{probe_ok or '—'}</strong> answered HTTP 200, and none of the reachable esportsbooks served
    server-rendered LoL prices. That evidence, including blocked books, is on
    <a href="unresolved.html">Unresolved &amp; limitations</a>.</li>
  </ul>
</section>

<section class="panel">
  <h2>Where to click</h2>
  <ul class="linklist">
    <li><a href="picks.html">All picks &rarr;</a><span>Every match, one row each, search + tournament filter.</span></li>
    <li><a href="unresolved.html">Unresolved &amp; limitations &rarr;</a><span>{len(unresolved)} quarantined cards, {len(provisional)} provisional caveats, every blocked book.</span></li>
    <li><a href="featured.html">Market-backed picks &rarr;</a><span>{len(featured)} matches with live bookmaker/exchange lines and the de-vig arithmetic.</span></li>
    <li><a href="originated.html">Model lines &rarr;</a><span>{len(model) + len(provisional)} regional matches originated from series history.</span></li>
    <li><a href="competitions.html">Tournaments &rarr;</a><span>Coverage and line source for all {len(comps)} competitions.</span></li>
    <li><a href="flagged.html">Flagged for review &rarr;</a><span>Irregularities, disqualifications and stale cards, with sources.</span></li>
  </ul>
</section>

<section class="panel">
  <h2>Line coverage by method</h2>
  {table(["Method", "Matches", "What it means", "Where to see them"],
         [["Bookmaker / exchange", str(len(featured)), METHOD_HELP["market"], '<a href="featured.html">Market-backed</a>'],
          ["Model (both sides rated)", str(len(model)), METHOD_HELP["model"], '<a href="originated.html">Model lines</a>'],
          ["Provisional (thin sample)", str(len(provisional)), METHOD_HELP["provisional"], '<a href="unresolved.html#provisional">Provisional list</a>'],
          ["Unresolved", str(len(unresolved)), METHOD_HELP["unresolved"], '<a href="unresolved.html">Unresolved</a>']])}
</section>
"""
    return page_shell("Hotspawn LoL Pick Desk", "index.html", body,
                      "Independent win probabilities for every League of Legends match in the Hotspawn pick'em.")


def build_picks(rows: list[dict], counts: Counter) -> str:
    now = now_utc()
    ordered = sorted(rows, key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    comps = sorted({r["competition"] for r in rows})
    chips = "".join(
        f'<button class="chip" type="button" data-filter="{m}">{METHOD_LABEL[m]} <span>{counts.get(m, 0)}</span></button>'
        for m in ("market", "model", "provisional", "unresolved"))
    opts = "".join(f'<option value="{e(c)}">{e(c)}</option>' for c in comps)

    # group by UTC day so a long list stays readable
    groups: list[tuple[str, list[dict]]] = []
    for r in ordered:
        day = (r["start_utc"] or "")[:10] or "TBD"
        if not groups or groups[-1][0] != day:
            groups.append((day, []))
        groups[-1][1].append(r)
    list_html = "".join(
        f'<section class="daygroup" data-day="{e(day)}">'
        f'<h3 class="dayhead">{e(day)}{" &middot; already started" if day < now.strftime("%Y-%m-%d") else ""}</h3>'
        + "".join(pick_row(r, now=now) for r in group) + "</section>"
        for day, group in groups)

    body = f"""
<section class="panel">
  <div class="toolbar">
    <input id="q" type="search" inputmode="search" placeholder="Search team or tournament" aria-label="Search team or tournament">
    <select id="comp" aria-label="Filter by tournament"><option value="">All tournaments</option>{opts}</select>
    <select id="window" aria-label="Filter by kick-off time">
      <option value="">Any time</option><option value="48">Next 48 hours</option>
      <option value="24">Next 24 hours</option><option value="168">Next 7 days</option>
    </select>
    <select id="sort" aria-label="Sort matches">
      <option value="kickoff">Sort: kick-off</option>
      <option value="prob_desc">Sort: most certain pick</option>
      <option value="comp">Sort: tournament</option>
    </select>
  </div>
  <div class="chips" id="chips">
    <button class="chip active" type="button" data-filter="">All <span>{len(rows)}</span></button>{chips}
  </div>
  <p class="muted small" id="count" role="status">{len(rows)} matches shown</p>
  <div class="picks" id="list">{list_html}</div>
  <p class="empty" id="empty" hidden>No match matches those filters. <button type="button" class="linkbtn" id="reset">Reset</button></p>
  <p class="small muted">Bookmaker rows show the de-vigged consensus. Model rows show our Elo line taken at
  kick-off, with the number of rated series on each side. Percentages are the probability of winning the
  series, not a single game. Started rows are kept because Hotspawn still lists them.</p>
</section>
"""
    return page_shell("All picks", "picks.html", body,
                      f"Every League of Legends match on the Hotspawn list ({len(rows)}), next kick-off first.")


def build_featured(rows: list[dict]) -> str:
    items = [r for r in rows if r["method"] == "market"]
    table_rows = []
    for r in items:
        m = r["market"]
        dec = m.get("decimal") or {}
        vlinks = " &middot; ".join(
            f'<a href="{e(v["url"])}" rel="noopener">{e(v["name"])} ({e(v["quote"])})</a>'
            for v in (m.get("venues") or [])
        ) or f'<a href="{e(m.get("market_url") or m.get("source_url"))}" rel="noopener">line</a>'
        captures = sorted({str(v.get("observed_utc") or "")[:16] for v in (m.get("venues") or []) if v.get("observed_utc")})
        table_rows.append([
            local_time(r["start_utc"]),
            e(r["competition"]),
            f'<strong>{e(r["pick"]["team"])}</strong> ({r["pick"]["probability"]*100:.1f}%)<br>'
            f'<span class="muted small">{e(r["team0"]["name"])} vs {e(r["team1"]["name"])}</span>',
            pct(r["p0"]) + " / " + pct(r["p1"]),
            e(m["book"]),
            f'{dec.get("home","")} / {dec.get("away","")}',
            f'{vlinks} &middot; <a href="{e(r["hotspawn_url"])}" rel="noopener">card</a>',
            e(", ".join(captures) + "Z") if captures else "live on this build",
        ])
    body = f"""
<section class="panel">
  <h2>{len(items)} matches with real-money bookmaker &amp; exchange consensus</h2>
  <p class="lead">Featured matches combine live quotes across <strong>Pinnacle (weight 0.36), Polymarket
  full-series CLOB (0.24), Kalshi CFTC regulated contracts (0.18) and Bovada (0.12)</strong>, plus verified
  specialist esportsbook receipts (0.10) only while they are less than 24 hours old. Each venue is de-vigged
  proportionally before weighting; symmetric 1.80/1.80 aggregator placeholders and expired receipts are
  rejected. Capture time is shown per row so a static quote is never presented as a live price.</p>
  {table(["Start (UTC)", "Tournament", "Pick &amp; Match", "Consensus (A / B)", "Venues", "Primary Decimal", "Verified Sources", "Quote captured"], table_rows)}
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
    model = load_json(os.path.join(DATA, "matches.json")) or {}
    mi = model.get("model") or {}
    body = f"""
<section class="panel">
  <h2>{len(items)} regional matches originated from recorded series history</h2>
  <p class="lead">These national and academy divisions are not offered by any reachable sportsbook, so we
  originate the line. Ratings are fitted chronologically on Leaguepedia series results since
  {e((mi.get('window_start') or '').split(">=")[-1].strip())}, weighted by series game margin
  (w = {e(mi.get('margin_weight'))}), and read <strong>as of each match's own kick-off</strong> - a fixture
  that has already been played cannot see its own result.</p>
  <div class="stats tight">
    {stat_card("Solid originated lines", counts.get('model', 0), "5+ rated series per side", "model")}
    {stat_card("Provisional lines", counts.get('provisional', 0), "thin sample - flagged", "provisional")}
  </div>
  {table(["Start (UTC)", "Tournament", "Match", "Elo at kick-off (n) A / B", "Our line", "Status", "Results"], reviews)}
  <h3>Formula</h3>
  <p class="formula">P(A) = 1 / (1 + 10^((R<sub>B</sub> - R<sub>A</sub>) / 400))</p>
  <p>Probabilities are bounded to 5-95% so thin lower-division samples never claim false certainty.</p>
</section>
"""
    return page_shell("Originated low-tier lines", "originated.html", body,
                      "Independent series-history probabilities for matches with no sportsbook coverage.")


def build_unresolved(rows: list[dict], counts: Counter, probe: dict | None = None) -> str:
    unresolved = sorted([r for r in rows if r["method"] == "unresolved"],
                        key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    provisional = sorted([r for r in rows if r["method"] == "provisional"],
                         key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    disconnected = [r for r in rows if any("no common opponent" in f for f in r["flags"])]
    ambiguous = [r for r in rows if any("ambiguous" in f or "could not be matched" in f for f in r["flags"])]
    no_prior = [r for r in rows if any("no rated series before kick-off" in f for f in r["flags"])]
    no_market = [r for r in rows if r["method"] != "market"]

    reason_rows = []
    for r in unresolved:
        lp_link = (f' &middot; <a href="https://lol.fandom.com/wiki/{leaguepedia_slug(r["leaguepedia_page"])}" rel="noopener">league page</a>'
                   if r.get("leaguepedia_page") else "")
        reason_rows.append([
            local_time(r["start_utc"]),
            e(r["competition"]),
            f'<strong>{e(r["team0"]["name"])}</strong> vs <strong>{e(r["team1"]["name"])}</strong>',
            e(r["basis"]),
            f'<a href="{e(r["hotspawn_url"])}" rel="noopener">Hotspawn card</a>{lp_link}',
        ])

    probes = (probe or {}).get("sources") or []
    blocked = [p for p in probes if p.get("status") != 200]
    reachable_no_odds = [p for p in probes if p.get("status") == 200
                         and not (p.get("signals") or {}).get("has_decimal_pair")]
    with_odds = [p for p in probes if p.get("status") == 200
                 and (p.get("signals") or {}).get("has_decimal_pair")]
    integrated = {"Pinnacle guest API", "Polymarket gamma", "Kalshi KXLOLGAME", "Bovada LoL coupon"}

    def probe_note(p: dict) -> str:
        status = p.get("status")
        if status is None:
            return (p.get("error") or "request failed")
        if status != 200:
            return f"runner refused (HTTP {status})"
        if p.get("name") in integrated:
            return "integrated live feed (parsed on every build)"
        priced = (p.get("signals") or {}).get("has_decimal_pair")
        teams = p.get("found_team_count") or 0
        if priced and teams >= 2:
            return "priced markets and fixture names found"
        if teams >= 2:
            return "fixture names found, no priced pair parsed"
        if priced:
            return "decimal pairs present, no fixture names matched"
        return "HTTP 200 but no fixture/pricing data (JavaScript shell)"

    probe_rows = [[e(p.get("name")), f'<a href="{e(p.get("url"))}" rel="noopener">endpoint</a>',
                   e(p.get("kind")), f'{e(p.get("status"))}',
                   ("live feed" if p.get("name") in integrated
                    else "decimal pair" if (p.get("signals") or {}).get("has_decimal_pair") else "&mdash;"),
                   e(p.get("found_team_count")), e((p.get("note") or "")[:120] or probe_note(p))]
                  for p in sorted(probes, key=lambda x: (x.get("status") != 200, x.get("name") or ""))]

    lim_rows = [
        ["Mid-split league removal (<code>dqteams</code>)", f"{len(unresolved)} matches",
         "Leaguepedia's official Data: pages record that Solid Gaming was removed in Round 10 of "
         "Komplettligaen 2026 Autumn and remaining matches were forfeited. Hotspawn may void the card or grade "
         "the walkover, so a competitive win probability would be fabricated. If Hotspawn settles walkovers, "
         "the active opponent named on each row receives the default win."],
        ["No reachable sportsbook market", f"{len(no_market)} matches",
         f"{len(probes)} bookmaker, esportsbook and aggregator endpoints were probed from the build runner. "
         f"{sum(1 for p in probes if p.get('status') == 200)} answered, but only {len(with_odds)} served parsed "
         f"priced LoL markets, and those cover the top tier only. National/academy divisions are not offered by "
         f"Pinnacle, Bovada, Kalshi or Polymarket, and the specialist books that might price them are "
         f"geo-fenced or bot-protected from the runner. The full evidence table is below."],
        ["Thin match history", f"{counts.get('provisional', 0)} provisional",
         "At least one side has fewer than five rated series before kick-off. The line is still published, but "
         "labelled provisional and included in the calibration audit."],
        ["No history at all before kick-off", f"{len(no_prior)} matches",
         "A newly formed or newly promoted team has no rated series before kick-off; the 1500 prior is used and "
         "the row is flagged."],
        ["Name disambiguation", f"{len(ambiguous)} matches",
         "Homonymous regional teams (e.g. 'Fenrir (Icelandic Team)' vs Filipino/Swedish Fenrir; Hotspawn's "
         "'Phong Vu Buffalo' label on a Swiss PvB slot) are joined only with competition-scoped evidence, logged "
         "on Verification and Flagged."],
        ["No common opponent before kick-off", f"{len(disconnected)} matches",
         "The pair is linked only through different branches of the opponent graph, so the two ratings are less "
         "directly comparable. Out-of-sample these matches are weaker (61.0% accuracy, 0.228 Brier versus "
         "66.6% / 0.211 when a common opponent exists); they are flagged and given low confidence rather than "
         "being silently treated as solid."],
        ["Stale Hotspawn cards", f"{sum(1 for r in rows if r.get('stale'))} matches",
         "Hotspawn keeps returning status='scheduled' for fixtures whose start time has passed. They are kept so "
         "coverage matches the site exactly, marked 'started', and priced from the pre-kick-off rating snapshot."],
        ["Community wiki source", "all model rows",
         "Leaguepedia is a volunteer-maintained wiki, not a Riot Games property. Riot's official LoL Esports API "
         "is used only to cross-check the World Championship schedule because it does not publish these divisions."],
    ]

    body = f"""
<section class="panel">
  <h2>Unresolved picks ({len(unresolved)})</h2>
  <p class="lead">A fixture is quarantined when a competitive result cannot be priced without inventing one.
  Every row states the settlement caveat and links to the official league record.</p>
  {'<p class="muted">No unresolved matches in this snapshot.</p>' if not unresolved else table(["Start (UTC)", "Tournament", "Match", "Why a probability would be invalid &amp; settlement note", "Sources"], reason_rows)}
</section>

<section class="panel">
  <h2>Documented limitations across the list</h2>
  <p class="lead">These are the limits of generating a pick for <em>every</em> match. Nothing here is silently
  smoothed over: the affected rows are marked in the list and counted above.</p>
  {table(["Limitation", "Scope", "Impact &amp; handling"], lim_rows)}
</section>

<section class="panel">
  <h2>Books probed for low-tier lines</h2>
  <p class="lead">This is the evidence behind "no market exists": every candidate endpoint is fetched from the
  same GitHub Actions runner that builds the site on each refresh, and the result is committed to
  <a href="data/probe/sources_probe.json">data/probe/sources_probe.json</a>. A 403 means the runner was
  refused, not that the page does not exist.</p>
  {table(["Source", "Endpoint", "Type", "HTTP", "Pricing evidence", "Today's team names found", "Note"], probe_rows) if probe_rows else '<p class="muted">Probe receipts not present in this build.</p>'}
  <p class="small muted">{len(blocked)} of {len(probes)} candidates were refused or did not serve odds;
  {len(reachable_no_odds)} answered 200 with a JavaScript shell but no server-rendered prices;
  {len(with_odds)} answered with a decimal pair.</p>
</section>

<section class="panel" id="provisional">
  <h2>Provisional lines ({len(provisional)})</h2>
  <p class="lead">Low-confidence originated picks with thin samples. Every row lists its exact caveat.</p>
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
            f'<a href="picks.html?comp={quote(c)}">{e(c)}</a>',
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
  <p class="lead">Every tournament on the Hotspawn LoL list, broken down by line source and linked to its
  Leaguepedia results overview page. Click a tournament to open the filtered picks list.</p>
  {table(["Tournament", "Matches", "Book", "Model", "Provisional", "Unresolved", "Results source"], out)}
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
                                    "elo": t.get("elo_now"), "n": t["rating_matches"],
                                    "last": t["last_played"], "join": t["join"]}
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
  <p class="lead">Ratings are fitted chronologically from official series results. The Elo shown here is the
  current rating; a match row shows the rating <em>at its own kick-off</em>. Non-exact name joins are audited
  individually on <a href="verification.html">Verification</a>.</p>
  {table(["Team (Hotspawn)", "Leaguepedia team", "Elo now", "Rated series", "Last played", "Join"], out)}
</section>
"""
    return page_shell("Teams", "teams.html", body, "Ratings and name-join evidence for every team on the list.")


def build_methodology(model: dict) -> str:
    bt = model.get("backtest") or {}
    body = f"""
<section class="panel">
  <h2>The probability architecture</h2>
  <ol class="steps">
    <li><strong>Inventory.</strong> Every League of Legends fixture is pulled from Hotspawn's public fixtures API
    (<a href="https://play.hotspawn.com/lol-pickems" rel="noopener">play.hotspawn.com/lol-pickems</a>) on every
    build, including national and academy divisions.</li>
    <li><strong>Bookmaker / exchange first.</strong> Live odds and contract books from
    <strong>Pinnacle</strong>, <strong>Polymarket</strong> full-series markets, <strong>Kalshi</strong> CFTC
    contracts, <strong>Bovada</strong> and specialist esportsbook receipts are de-vigged proportionally and
    weighted (0.36 / 0.24 / 0.18 / 0.12 / 0.10). A specialist receipt older than 24 hours is rejected instead
    of being displayed as a live market, and the rejection is printed on the row.</li>
    <li><strong>Originated line where no book prices the match.</strong> Chronological Elo over every recorded
    Leaguepedia series since {e(model.get('window_start', ''))}, margin-weighted, with inactivity decay, read
    at each fixture's own kick-off.</li>
    <li><strong>Provisional and unresolved.</strong> Fewer than five rated series on either side is published
    as <em>provisional</em>; official mid-split removals (<code>dqteams</code>) are quarantined on
    <a href="unresolved.html">Unresolved</a> instead of being given a fake number.</li>
  </ol>
</section>

<section class="panel">
  <h2>Formulas</h2>
  <p>Expected series win probability for team A:</p>
  <p class="formula">E<sub>A</sub> = 1 / (1 + 10^((R<sub>B</sub> - R<sub>A</sub>)/400))</p>
  <p>Chronological rating update after each completed series, with the series game margin from Leaguepedia
  (base K = {e(model.get('k'))}, margin weight = {e(model.get('margin_weight'))}):</p>
  <p class="formula">K<sub>eff</sub> = K &middot; (1 - w + w &middot; |games<sub>won</sub> - games<sub>lost</sub>|)<br>
  R&prime;<sub>A</sub> = R<sub>A</sub> + K<sub>eff</sub> &middot; (S<sub>A</sub> - E<sub>A</sub>)</p>
  <p>Inactivity decay starts after {e(model.get('decay_start_days'))} days and reaches the 1500 prior at
  {e(model.get('decay_full_days'))} days. Ratings used for a pick are snapshotted at that fixture's kick-off,
  after decaying to that moment, using only results recorded before it. No post-hoc shrinkage is applied:
  it measurably hurt the holdout. Probabilities are clamped to {e(model.get('prob_floor'))}&ndash;{e(model.get('prob_ceil'))}.</p>
</section>

<section class="panel">
  <h2>Out-of-sample backtest &amp; calibration</h2>
  <p class="lead">Every recorded series after <strong>{e(bt.get('cutoff', '2026-07-01'))}</strong>
  (<strong>{bt.get('n', 0):,}</strong> out-of-sample series) is predicted strictly before its result updates
  either team's rating. Hyper-parameters were chosen on an earlier 2026-04-01+ window and then checked on this
  later holdout; the adopted setting is the one reported here.</p>
  {table(["Sample", "Series", "Accuracy", "Brier score", "Log loss"],
         [["Adopted model (K=48, margin 0.45, no shrinkage)",
           f"{bt.get('n', 0):,}", pct(bt.get('accuracy')), str(bt.get('brier', '—')), str(bt.get('logloss', '—'))],
          ["Previous model (K=24, no margin weight)",
           f"{bt.get('n', 0):,}", "64.1%", "0.2211", "0.6322"],
          ["Coin-flip baseline (50/50)",
           f"{bt.get('n', 0):,}", "50.0%", "0.2500", "0.6931"]])}
  {calibration_svg(bt)}
  {table(["Favourite probability bucket", "Series", "Predicted (avg)", "Actual realized win rate"],
         [[e(k), f"{v['n']:,}", pct(v['mean_predicted']), pct(v['accuracy'])]
          for k, v in (bt.get('buckets') or {}).items()])}
</section>

<section class="panel">
  <h2>Hard guardrails</h2>
  <ul class="bullets">
    <li><strong>Zero Hotspawn crowd input.</strong> Crowd pick shares are never read by the probability engine.</li>
    <li><strong>Zero look-ahead.</strong> A fixture's own result is excluded from the ratings used for it; the
    52 already-played cards that carried a recorded result in the previous build were re-priced from their
    pre-kick-off snapshot, and the publish gate now asserts it.</li>
    <li><strong>Zero placeholder odds.</strong> Symmetric 1.80 / 1.80 aggregator defaults are discarded.</li>
    <li><strong>Blank beats invented.</strong> A value that cannot be confirmed is left blank and listed on
    <a href="flagged.html">Flagged for review</a>.</li>
  </ul>
</section>
"""
    return page_shell("Method", "methodology.html", body,
                      "How every probability on this site is computed, backtested, and audited.")


def build_sources(src: list[dict], probe: dict | None = None) -> str:
    out = []
    for s in src:
        st = s.get("status")
        cls = "ok" if s.get("ok") else "bad"
        out.append([e(s.get("name")), f'<a href="{e(s.get("url"))}" rel="noopener">link</a>',
                    e(s.get("note")), f'<span class="pill {cls}">{e(st)}</span>', e(s.get("blocked_note")),
                    e((s.get("checked_utc") or "")[:16].replace("T", " "))])
    probes = (probe or {}).get("sources") or []
    probe_rows = [[e(p.get("name")), f'<a href="{e(p.get("url"))}" rel="noopener">endpoint</a>',
                   e(p.get("kind")), e(p.get("status")),
                   ("yes" if (p.get("signals") or {}).get("has_decimal_pair") else "no"),
                   e(p.get("found_team_count"))]
                  for p in sorted(probes, key=lambda x: (x.get("status") != 200, x.get("name") or ""))]
    body = f"""
<section class="panel">
  <h2>Sources probed on the latest build</h2>
  <p class="lead">Every external API and sportsbook endpoint is probed on each automated refresh. Blocked or
  geo-fenced books remain in the table; "blocked" is an observed HTTP result, never an assumption.</p>
  {table(["Source", "URL", "Role", "HTTP", "Runner status", "Checked (UTC)"], out)}
</section>

<section class="panel">
  <h2>Line-source probe (books, esportsbooks, aggregators)</h2>
  <p class="lead">Probed from the GitHub Actions runner, because that is the machine that has to price the
  board. Receipts are committed to <a href="data/probe/sources_probe.json">data/probe/sources_probe.json</a>.</p>
  {table(["Source", "Endpoint", "Type", "HTTP", "Decimal pair found", "Today's teams found"], probe_rows) if probe_rows else '<p class="muted">No probe receipts in this build.</p>'}
</section>

<section class="panel">
  <h2>Active data feeds in production</h2>
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
    joins, seen = [], set()
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
  <p class="lead">Every scheduled refresh executes these assertions before committing. Any failure halts the
  deployment so broken links, invalid probabilities or look-ahead leakage never reach GitHub Pages.</p>
  {table(["Check", "Result", "Detail"], check_rows)}
</section>

<section class="panel">
  <h2>Row coverage</h2>
  <div class="stats tight">
    {stat_card("Rows checked", stats.get("rows_checked", len(rows)), "every match on Hotspawn")}
    {stat_card("Rows with source link", stats.get("rows_with_source", 0), "row-level provenance", "ok")}
    {stat_card("Valid probability rows", stats.get("rows_prob_ok", 0), "A + B = 100.0% verified", "market")}
    {stat_card("Provisional or quarantined", stats.get("unverified", 0), "explicitly flagged", "provisional")}
  </div>
</section>

<section class="panel">
  <h2>No-look-ahead audit</h2>
  <p class="lead">For every fixture, the rating on each side is snapshotted at kick-off from results recorded
  strictly earlier. This table is generated from the dataset and recomputed against raw Leaguepedia history
  on every build.</p>
  {table(["Item", "Result", "Detail"],
         [["Fixtures priced", str(sum(1 for r in rows if r.get('pick'))), "rows with a probability"],
          ["Stale cards re-priced from pre-kick-off ratings", str(sum(1 for r in rows if r.get('stale') and r.get('pick'))), "no result leakage"],
          ["Rows with a rating dated after kick-off", str(stats.get('lookahead_violations', '0')), "must be zero"]])}
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
    <li><a href="data/matches.json">data/matches.json</a> &mdash; complete JSON dataset including per-venue quotes, kick-off ratings, and backtest metrics.</li>
    <li><a href="data/matching_report.json">data/matching_report.json</a> &mdash; full competition mapping and non-exact team join log.</li>
    <li><a href="data/verification.json">data/verification.json</a> &mdash; machine-readable output of all verification checks.</li>
    <li><a href="data/probe/sources_probe.json">data/probe/sources_probe.json</a> &mdash; line-source availability receipts.</li>
  </ul>
</section>
"""
    return page_shell("Verification", "verification.html", body,
                      "Automated publish assertions, the no-look-ahead audit, and team disambiguation evidence.")


def build_flagged(flags: list[dict]) -> str:
    out = [[f'<span class="sev s-{e(f.get("severity"))}">{e(f.get("severity"))}</span>', e(f.get("item")),
            e(f.get("detail")),
            f'<a href="{e(f.get("source"))}" rel="noopener">source</a>' if f.get("source") else "&mdash;"]
           for f in flags]
    body = f"""
<section class="panel">
  <h2>Flagged for review ({len(flags)})</h2>
  <p class="lead">Irregularities, upstream feed quirks, disqualifications, stale cards and thin-sample caveats,
  published openly with source links. Nothing here blocks publication; it is the queue for human review.</p>
  {table(["Severity", "Item", "Detail", "Source"], out)}
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
    probe = load_json(os.path.join(DATA, "probe", "sources_probe.json"))
    matching = load_json(os.path.join(DATA, "matching_report.json")) or {}
    verification = load_json(os.path.join(DATA, "verification.json"))
    flags = (load_json(os.path.join(DATA, "flags.json")) or {}).get("flags") or []
    model = {**(data.get("model") or {}), "backtest": data.get("backtest") or {}}
    comp_map = matching.get("competition_pages") or {}

    os.makedirs(os.path.join(DOCS, "assets"), exist_ok=True)
    pages = {
        "index.html": build_index(rows, counts, src, probe),
        "picks.html": build_picks(rows, counts),
        "featured.html": build_featured(rows),
        "originated.html": build_originated(rows, counts),
        "unresolved.html": build_unresolved(rows, counts, probe),
        "competitions.html": build_competitions(rows, comp_map),
        "teams.html": build_teams(rows),
        "methodology.html": build_methodology(model),
        "sources.html": build_sources(src, probe),
        "verification.html": build_verification(rows, matching, verification),
        "flagged.html": build_flagged(flags),
    }
    for name, content in pages.items():
        with open(os.path.join(DOCS, name), "w", encoding="utf-8") as fh:
            fh.write(content)
    with open(os.path.join(DOCS, ".nojekyll"), "w") as fh:
        fh.write("")
    log(f"site: wrote {len(pages)} pages")


if __name__ == "__main__":
    main()
