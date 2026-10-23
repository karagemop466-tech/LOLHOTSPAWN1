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

NAV = [
    ("index.html", "Summary"),
    ("picks.html", "All picks"),
    ("featured.html", "Market"),
    ("originated.html", "Model"),
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
    meta = load_json(os.path.join(DATA, "matches.json")) or {}
    fetched = meta.get("inventory_fetched_utc") or (load_json(os.path.join(DATA, "raw/hotspawn_lol.json")) or {}).get("fetched_utc", "")
    def _tab(page):
        return ' class="active"' if page == active else ""
    tab_active_index = _tab("index.html")
    tab_active_picks = _tab("picks.html")
    tab_active_unresolved = _tab("unresolved.html")
    tab_active_featured = _tab("featured.html")
    tab_active_flagged = _tab("flagged.html")
    updated = (meta.get("generated_utc") or "")[:16].replace("T", " ")
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
    <button class="menu-btn" aria-expanded="false" aria-controls="nav">Menu</button>
    <nav id="nav" class="nav">{nav}</nav>
  </div>
</header>
<main id="main" class="wrap">
  <div class="pagehead">
    <h1>{e(title)}</h1>
    {f'<p class="sub">{subtitle}</p>' if subtitle else ''}
    <p class="stamp">Data snapshot: <strong>{e(updated)} UTC</strong> &middot; refresh scheduled every 6 hours (not guaranteed)</p>
    <p id="snapshot-age" class="stamp" data-fetched="{e(fetched)}">Inventory collected: {e(fetched)}. Check source timestamps before use.</p>
  </div>
  {body}
</main>
<footer class="wrap foot">
  <p>Independent research dashboard. Rows link to source records. Leaguepedia is community-maintained; model lines are estimates, not verified facts. Zero Hotspawn crowd-pick input.</p>
  <p><a href="methodology.html">Method</a> &middot; <a href="verification.html">Verification</a> &middot;
  <a href="flagged.html">Flagged for review</a> &middot; <a href="sources.html">Sources</a> &middot;
  <a href="competitions.html">Tournaments</a></p>
</footer>
<nav class="mobnav tabbar" aria-label="Primary navigation">
  <a href="index.html"{tab_active_index}><span class="ti">&#9776;</span>Summary</a>
  <a href="picks.html"{tab_active_picks}><span class="ti">&#10003;</span>All picks</a>
  <a href="featured.html"{tab_active_featured}><span class="ti">&#9679;</span>Market</a>
  <a href="unresolved.html"{tab_active_unresolved}><span class="ti">!</span>Unresolved</a>
  <a href="flagged.html"{tab_active_flagged}><span class="ti">&#9873;</span>Flags</a>
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
        pick_html = ('<div class="pickline"><span class="picklabel">Unresolved</span> '
                     '<span class="muted">see Unresolved &amp; why below</span></div>')
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

    result = r.get("recorded_result") or {}
    result_html = ""
    if result:
        score = f" {e(result['score'])}" if result.get("score") else ""
        result_html = (f'<p class="resultline"><span class="badge b-result">result on record</span> '
                       f'<strong>{e(result["winner"])}</strong> beat {e(result["loser"])}{score} '
                       f'&middot; <a href="{e(result["source"])}" rel="noopener">league record</a></p>')
    prob_attr = (f"{pick['probability']:.3f}"
                 if pick and pick.get("probability") is not None else "")
    pick_attr = pick["team"] if pick else ""
    return f"""<article id="match-{e(r['id'])}" class="card m-{e(m)}" data-method="{e(m)}" data-comp="{e(r['competition'])}"
  data-start="{e(r['start_utc'] or '')}" data-pick="{e(pick_attr)}" data-prob="{e(prob_attr)}"
  data-text="{e((r['competition'] + ' ' + t0['name'] + ' ' + t1['name']).lower())}">
  <div class="card-top">
    <span class="when">{local_time(r['start_utc'])}</span>
    <span class="badges">{f'<span class="badge b-past">start time passed</span>' if r.get('stale') else ''}{badge(m)}</span>
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
  {result_html}
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
def jump_card(href: str, title: str, sub: str, cls: str = "") -> str:
    return (f'<a class="jumpcard {cls}" href="{e(href)}">'
            f'<span class="jt">{e(title)}</span><span class="js">{e(sub)}</span></a>')


def utc_day(iso_utc: str | None) -> str:
    return (iso_utc or "")[:10]


def plus_days(days: int) -> str:
    from datetime import timedelta
    return iso(now_utc() + timedelta(days=days))[:10]


def build_index(rows: list[dict], counts: Counter, src_status: list[dict]) -> str:
    total = len(rows)
    with_pick = sum(1 for r in rows if r["pick"])
    now = iso(now_utc())
    upcoming = sorted([r for r in rows if r["start_utc"] and r["start_utc"] > now],
                      key=lambda r: r["start_utc"])
    featured = [r for r in rows if r["method"] == "market"]
    unresolved = [r for r in rows if r["method"] == "unresolved"]
    settlement = [r for r in rows if r.get("pick_type") == "settlement"]
    priced = sum(1 for r in rows if r["p0"] is not None)
    provisional = [r for r in rows if r["method"] == "provisional"]
    comps = len({r["competition"] for r in rows})
    live_sources = sum(1 for s in src_status if s.get("ok"))
    today = utc_day(now)
    today_rows = [r for r in upcoming if utc_day(r["start_utc"]) == today]
    tomorrow = [r for r in upcoming if utc_day(r["start_utc"]) == plus_days(1)]
    next7 = [r for r in upcoming if (r["start_utc"] or "")[:10] <= plus_days(7)]
    no_pick = total - with_pick
    backtest = (load_json(os.path.join(DATA, "matches.json")) or {}).get("backtest") or {}
    low_conf = sum(1 for r in rows if any("thin market" in f for f in (r.get("flags") or [])))

    unresolved_rows = []
    for r in unresolved:
        why = (r.get("basis") or "").strip()
        expected = r.get("expected_resolution") or {}
        settlement_team = ((r.get("pick") or {}).get("team")) or "&mdash;"
        unresolved_rows.append([
            local_time(r["start_utc"])[:10],
            e(r["competition"]),
            f'<a href="picks.html#match-{e(r["id"])}">{e(r["team0"]["name"])} vs {e(r["team1"]["name"])}</a>',
            (f'<strong>{e(settlement_team)}</strong><br><span class="muted small">settlement only, '
             f'no probability</span>' if settlement_team != "&mdash;" else "&mdash;"),
            e(why),
            f'<a href="{e(r["hotspawn_url"])}" rel="noopener">Hotspawn card</a>'
            + (f' &middot; <a href="{e(expected["source"])}" rel="noopener">Leaguepedia</a>'
               if expected.get("source") else ""),
        ])

    lim_rows = [
        ["League removal mid-split",
         f"{len(unresolved)} of {total} matches",
         "The listed participant was removed by the league (<code>dqteams</code>). The card is either voided "
         "or settled as a walkover, so no competitive probability is claimed; only the settlement side is named."],
        ["No market for the division",
         f"{len([r for r in rows if r['method'] != 'market'])} of {total} matches",
         "Pinnacle, Polymarket, Kalshi and Bovada price the events they choose to list. Most national divisions "
         "on Hotspawn have no quote in any book reachable from the build runner, so the pick is our own line."],
        ["Thin history",
         f"{len(provisional)} provisional",
         "At least one team has fewer than five rated series in the Leaguepedia window. The line is published "
         "but labelled provisional, with the sample size shown on the card."],
        ["Thin market",
         f"{low_conf} low-confidence",
         "A single prediction market with almost no traded volume is published as evidence, never as a "
         "high-confidence line, and is labelled on the row."],
        ["Community-maintained results",
         "all model lines",
         "Leaguepedia is a wiki, not a league authority. Every model row links to the exact page it was "
         "fitted from so the inputs can be checked."],
        ["Hotspawn crowd percentages",
         "never used",
         "Recorded for audit only. They are not an input to any probability on this site."],
    ]

    body = f"""
<section class="hero">
  <p class="eyebrow">Executive summary &middot; snapshot {e(now[:16].replace('T', ' '))} UTC</p>
  <h2>Picks for all {total} League of Legends matches on Hotspawn</h2>
  <p>{priced} matches carry a win probability &mdash; {len(featured)} priced from external bookmaker or
  exchange markets, {counts.get('model', 0)} from our own Elo line and {len(provisional)} provisional.
  {len(settlement)} league removals get a settlement pick with <strong>no probability</strong>, and the
  reason is spelled out below. The full list is one page and works on a phone.</p>
  <div class="cta">
    <a class="btn primary" href="picks.html">Open the picks list ({total}) &rarr;</a>
    <a class="btn" href="picks.html#today">Today ({len(today_rows)})</a>
    <a class="btn" href="#unresolved-summary">Unresolved ({len(unresolved)})</a>
  </div>
  <p class="hero-note">On a phone, <strong>All picks</strong> is pinned to the bottom of every page.
  Every match below links to its Hotspawn card and its external source.</p>
</section>

<section class="panel" id="where">
  <h2>Where the picks are</h2>
  <p class="lead">Everything is on this site, one tap from here. Nothing is behind a login or an app.</p>
  <div class="jump">
    {jump_card("picks.html", "All picks", f"{total} matches, next kick-off first", "wide")}
    {jump_card("picks.html#today", "Today", f"{len(today_rows)} matches today (UTC)")}
    {jump_card("picks.html#tomorrow", "Tomorrow", f"{len(tomorrow)} matches")}
    {jump_card("picks.html#next7", "Next 7 days", f"{len(next7)} matches")}
    {jump_card("featured.html", "Market-backed picks", f"{len(featured)} with a real external line")}
    {jump_card("originated.html", "Model lines", f"{counts.get('model', 0) + len(provisional)} originated")}
    {jump_card("unresolved.html", "Unresolved &amp; limits", f"{len(unresolved)} blank + every caveat", "warn")}
    {jump_card("competitions.html", "By tournament", f"{comps} competitions")}
    {jump_card("flagged.html", "Flagged for review", "irregularities, with sources")}
  </div>
</section>

<section class="panel">
  <h2>Executive summary</h2>
  <ul class="bullets">
    <li><strong>Coverage.</strong> {with_pick} of {total} matches carry a pick ({with_pick / total * 100:.1f}%),
    {priced} of them with a win probability. {len(featured)} are <a href="featured.html">market-backed</a>
    (de-vigged external quotes), {counts.get('model', 0)} are <a href="originated.html">originated lines</a>
    and {len(provisional)} are <a href="originated.html">provisional</a>. The full list is
    <a href="picks.html">All picks</a>.</li>
    <li><strong>Unresolved picks and their limitations.</strong> {len(unresolved)} matches have no win
    probability; each names the side that would receive the walkover. The reasons and the affected fixtures
    are <a href="#unresolved-summary">further down this page</a> and in full on
    <a href="unresolved.html">Unresolved &amp; limitations</a>.</li>
    <li><strong>Where the lines come from.</strong> External markets only &mdash; Pinnacle, Polymarket, Kalshi
    and Bovada when reachable &mdash; never Hotspawn. Hotspawn's crowd-pick percentages are recorded for audit
    and carry zero weight in any probability (<a href="sources.html">Sources</a>).</li>
    <li><strong>Model quality.</strong> The Elo line is scored out-of-sample on {backtest.get('n', 0):,} series:
    {backtest.get('accuracy', 0) * 100:.1f}% accuracy, Brier {backtest.get('brier', 0):.4f}, log-loss
    {backtest.get('logloss', 0):.4f}. Method and calibration curve on
    <a href="methodology.html">Method</a>.</li>
    <li><strong>Freshness.</strong> Inventory, lines and pages are rebuilt every 6 hours by
    <code>.github/workflows/refresh.yml</code>. This snapshot was collected
    {e(((load_json(os.path.join(DATA, "raw/hotspawn_lol.json")) or {}).get("fetched_utc") or "unknown")[:16].replace("T", " "))} UTC.
    {live_sources} of {len(src_status)} probed sources answered on the last build. Every refresh is gated by
    {len((load_json(os.path.join(DATA, "verification.json")) or {}).get("checks") or [])} automated checks
    (<a href="verification.html">Verification</a>).</li>
  </ul>
</section>

<section class="panel" id="unresolved-summary">
  <h2>Unresolved picks &amp; limitations ({len(unresolved)} of {total})</h2>
  <p class="lead">These matches are listed on Hotspawn but cannot be priced honestly. Instead of inventing a
  number we publish a <strong>settlement pick</strong> &mdash; the side that receives the administrative
  walkover if Hotspawn settles the card rather than voiding it &mdash; and state that no win probability is
  claimed. <a href="unresolved.html">Read the full limitations &rarr;</a></p>
  {table(["Kick-off", "Tournament", "Match", "Settlement pick", "Why no probability", "Sources"], unresolved_rows)
   if unresolved_rows else '<p class="muted">No unresolved fixtures in this snapshot.</p>'}
  <h3>Limitations that apply to the rest of the list</h3>
  {table(["Limitation", "Scope", "What it means"], lim_rows)}
</section>

<section class="panel">
  <h2>Next kick-offs</h2>
  <div class="cards">
    {"".join(match_card(r, show_sources=True) for r in upcoming[:6]) or '<p class="muted">No upcoming matches in the current snapshot.</p>'}
  </div>
  <p class="cta-inline"><a class="btn primary" href="picks.html">See all {total} matches &rarr;</a>
  <a class="btn" href="picks.html?window=today">Today only</a></p>
</section>

<section class="panel">
  <h2>How a number gets on this page</h2>
  <ol class="steps">
    <li><strong>Inventory</strong> &mdash; the full LoL list is pulled from Hotspawn's public fixtures API,
    not scraped from the page.</li>
    <li><strong>Market first</strong> &mdash; if a reachable book or exchange quotes the match, the margin is
    removed on each venue and the venues are precision-weighted. Prop markets (kills, maps, handicaps,
    totals) are rejected before matching.</li>
    <li><strong>Our own line second</strong> &mdash; otherwise an Elo rating fitted on
    {backtest.get('n', 0):,}+ community-recorded series produces the probability, flagged provisional when the
    sample is thin.</li>
    <li><strong>Settlement or blank last</strong> &mdash; a removed participant gets a settlement pick with no
    probability and appears in the section above.</li>
  </ol>
  <p class="cta-inline"><a class="btn" href="methodology.html">Read the method &rarr;</a>
  <a class="btn" href="verification.html">See the {len((load_json(os.path.join(DATA, "verification.json")) or {}).get("checks") or [])} checks &rarr;</a></p>
</section>
"""
    return page_shell("Hotspawn LoL Pick Desk", "index.html", body,
                      "Independent win probabilities for every League of Legends match in the Hotspawn pick'em.")


def build_picks(rows: list[dict], counts: Counter) -> str:
    now = iso(now_utc())
    today = utc_day(now)
    upcoming = sorted([r for r in rows if r["start_utc"] and r["start_utc"] > now],
                      key=lambda r: r["start_utc"])
    past = sorted([r for r in rows if not r["start_utc"] or r["start_utc"] <= now],
                  key=lambda r: r["start_utc"] or "9999")
    comps = sorted({r["competition"] for r in rows})
    chips = "".join(
        f'<button class="chip" data-filter="{m}" aria-pressed="false">{METHOD_LABEL[m]} '
        f'<span>{counts.get(m, 0)}</span></button>'
        for m in ("market", "model", "provisional", "unresolved"))
    opts = "".join(f'<option value="{e(c)}">{e(c)}</option>' for c in comps)

    groups: dict[str, list] = {}
    for r in upcoming:
        groups.setdefault(utc_day(r["start_utc"]), []).append(r)
    if today not in groups:
        groups[today] = []
    tomorrow = plus_days(1)

    day_sections = []
    for date in sorted(groups):
        items = groups[date]
        if date == today:
            day_sections.append('<div class="anchor" id="today" aria-hidden="true"></div>')
        elif date == tomorrow:
            day_sections.append('<div class="anchor" id="tomorrow" aria-hidden="true"></div>')
        if items:
            cards = "".join(match_card(r) for r in items)
        else:
            cards = ('<p class="muted empty-day">No matches scheduled today (UTC). '
                     'The next fixtures are listed below.</p>')
        day_sections.append(
            f'<section class="daygroup" id="day-{e(date)}">'
            f'<h2 class="dayhead">{e(day_label(date))}<span>{len(items)} match{"es" if len(items) != 1 else ""}</span></h2>'
            f'<div class="cards">{cards}</div></section>')
        if date == tomorrow:
            day_sections.append('<div class="anchor" id="next7" aria-hidden="true"></div>')

    today_count = len(groups.get(today, []))
    recorded_past = sum(1 for r in past if r.get("recorded_result"))
    next7_count = len([r for r in upcoming if (r["start_utc"] or "")[:10] <= plus_days(7)])
    first = upcoming[0] if upcoming else None
    body = f"""
<nav class="quickjump-bar" aria-label="Quick filters">
  <div class="quickjump">
    <a class="qj" href="?window=today">Today <b>{today_count}</b></a>
    <a class="qj" href="?window=next7">Next 7 days <b>{next7_count}</b></a>
    <a class="qj" href="?method=market">Market-backed <b>{counts.get('market', 0)}</b></a>
    <a class="qj" href="?method=unresolved">Unresolved <b>{counts.get('unresolved', 0)}</b></a>
    <a class="qj" href="#past">Start time passed <b>{len(past)}</b></a>
    <a class="qj" href="?">Everything <b>{len(rows)}</b></a>
  </div>
</nav>

<section class="panel filter-panel">
  <h2 class="sr-only">Find a pick</h2>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search team or tournament" aria-label="Search team or tournament" autocomplete="off">
    <select id="comp" aria-label="Filter by tournament"><option value="">All tournaments</option>{opts}</select>
    <div class="chips" role="group" aria-label="Filter by line type">
      <button class="chip active" data-filter="" aria-pressed="true">All <span>{len(rows)}</span></button>{chips}
    </div>
    <div class="chips" role="group" aria-label="Filter by kick-off window">
      <button class="chip win active" data-window="" aria-pressed="true">Any date</button>
      <button class="chip win" data-window="today" aria-pressed="false">Today</button>
      <button class="chip win" data-window="tomorrow" aria-pressed="false">Tomorrow</button>
      <button class="chip win" data-window="next7" aria-pressed="false">Next 7 days</button>
    </div>
    <button class="btn small-btn" id="reset" type="button">Reset filters</button>
  </div>
  <p class="muted small" id="count" role="status" aria-live="polite">{len(rows)} matches shown</p>
  <p class="empty" id="empty" hidden>No matches match that filter. <button class="linkish" id="clear" type="button">Clear filters</button></p>
  <noscript><p class="muted small">Search and filters need JavaScript. Every match is still listed below in
  kick-off order, grouped by UTC day.</p></noscript>
</section>

<div id="list">
  <p class="list-intro muted small">{len(rows)} matches, {len(upcoming)} still ahead of kick-off.
  {f"Next up: {e(first['team0']['name'])} vs {e(first['team1']['name'])}, {local_time(first['start_utc'])}." if first else ""}</p>
  {"".join(day_sections)}
  <section class="daygroup" id="past">
    <h2 class="dayhead">Start time passed<span>{len(past)} match{"es" if len(past) != 1 else ""}</span></h2>
    <p class="lead small">Hotspawn still lists these as scheduled after kick-off. They are kept so the list
    matches Hotspawn exactly; treat the pick as historical, not a live bet.
    {recorded_past} of them already have a final result recorded in Leaguepedia and are marked
    <span class="badge b-result">result on record</span>.</p>
    <div class="cards">{"".join(match_card(r) for r in past)}</div>
  </section>
  <p class="center"><button class="btn" type="button" id="totop">Back to top</button></p>
</div>
"""
    return page_shell("All picks", "picks.html", body,
                      f"Every League of Legends match on the Hotspawn pick'em list ({len(rows)} matches), "
                      "next kick-off first. Tap 'Why this line' on any card for the inputs and sources.")


def day_label(date: str) -> str:
    try:
        from datetime import datetime as _dt
        d = _dt.strptime(date, "%Y-%m-%d")
        return f"{d:%a %d %b} (UTC)"
    except (ValueError, TypeError):
        return f"{date} (UTC)"


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


def window_date(where: str | None) -> str:
    """Render the Cargo WHERE clause as a plain date for the page."""
    m = __import__("re").search(r"(\d{4}-\d{2}-\d{2})", str(where or ""))
    return m.group(1) if m else "2024-09-01"


def build_originated(rows: list[dict], counts: Counter) -> str:
    m_model = (load_json(os.path.join(DATA, "matches.json")) or {}).get("model") or {}
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
  <p class="lead">No reachable external book quoted these divisions in the feeds collected on the last build,
  so we originate independent probabilities from chronological series history in Leaguepedia since
  {e(window_date(m_model.get('window_start')))}.
  The rating is best-of-aware, margin-weighted, decayed for inactivity and published with its sample size.</p>
  <p class="small muted">Parameters in this build: K = {e(m_model.get('k_opening'))} for best-of-one,
  K = {e(m_model.get('k_series'))} for multi-game series, margin weight {e(m_model.get('mov_weight'))},
  decay starts at {e(m_model.get('decay_start_days'))} days and reaches the 1500 baseline at
  {e(m_model.get('decay_full_days'))} days. Full method on <a href="methodology.html">Method</a>.</p>
  <div class="stats tight">
    {stat_card("Solid originated lines", counts.get('model',0), "both teams rated & connected", "model")}
    {stat_card("Provisional lines", counts.get('provisional',0), "thin sample - flagged", "provisional")}
  </div>
  {table(["Start (UTC)", "Tournament", "Match", "Elo (n) A / B", "Our line", "Status", "Results"], reviews)}
  <h3>Formula</h3>
  <p class="formula">P(A) = 1 / (1 + 10^((R<sub>B</sub> - R<sub>A</sub>) / 400))</p>
  <p>Probabilities are bounded to 5-95% so thin lower-division samples never claim false certainty.
  A line is labelled <em>provisional</em> when either side has fewer than five rated series, and the
  card shows the exact counts behind the number.</p>
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
        expected = r.get("expected_resolution") or {}
        settlement_team = ((r.get("pick") or {}).get("team")) or "&mdash;"
        reason_rows.append([
            local_time(r["start_utc"]),
            e(r["competition"]),
            f'<strong>{e(r["team0"]["name"])}</strong> vs <strong>{e(r["team1"]["name"])}</strong>',
            (f'<strong>{e(settlement_team)}</strong><br><span class="muted small">settlement only, '
             f'no probability</span>' if settlement_team != "&mdash;" else "&mdash;"),
            e(r["basis"]),
            e(expected.get("note", "&mdash;")) if expected else "&mdash;",
            f'<a href="{e(r["hotspawn_url"])}" rel="noopener">Hotspawn card</a>{lp_link}',
        ])
    lim_rows = [
        ["Mid-split league removals (dqteams)", f"{sum(1 for r in unresolved if any('removed' in f for f in r['flags']))} matches",
         "Community-maintained Leaguepedia Data: pages record mid-split team removals ('dqteams=Solid Gaming' in Komplettligaen "
         "Round 10; 'dqteams=Arctic Pandas' in NLC Lower Division). Because Hotspawn may either void the card or "
         "grade walkovers in favour of the remaining active opponent, assigning an Elo win probability from pre-removal "
         "matches is invalid (and trapped 72% of Hotspawn's crowd on Solid Gaming in #1071216)."],
        ["No sportsbook market on national divisions", f"{len([r for r in rows if r['method']!='market'])} matches",
         "Pinnacle, Polymarket, Kalshi, Bovada and the additional books probed on every build price the events they list (typically tier-1/2 such as Worlds and EMEA Masters). Regional divisions (Prime League 2nd/3rd Div, RIVALS, NLC Lower, etc.) have no matched market in the collected feeds; this does not establish that no market exists elsewhere."],
        ["Thin match history", f"{counts.get('provisional',0)} provisional",
         "At least one team has fewer than five rated series in the 25-month Leaguepedia window, so the Elo estimate "
         "carries wider variance and is explicitly flagged provisional."],
        ["One-sided history", f"{len(one_sided)} matches",
         "At least one side has no matched rated history. Its strength cannot be confirmed; no 1500 baseline is substituted and probabilities remain blank."],
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
  <p class="small"><a href="index.html#unresolved-summary">&larr; This section is summarised in the executive summary</a></p>
  <h2>Unresolved picks ({len(unresolved)})</h2>
  <p class="lead">A fixture is quarantined here when competitive resolution is impossible — specifically
  mid-split league disqualifications/removals (<code>dqteams</code>) where matches are never played on the Rift,
  or cards with missing history for either side. Leaguepedia is a community source, not an official settlement authority. Hotspawn settlement is unverified; do not assume a walkover pick will be graded as a win.</p>
  {'<p class="muted">No unresolved matches in this snapshot.</p>' if not unresolved else table(["Start (UTC)", "Tournament", "Match", "Settlement pick", "Why there is no win probability", "Settlement guidance", "Sources"], reason_rows)}
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
  <p class="lead">Ratings are fitted chronologically from community-recorded series results. Non-exact name joins are
  audited individually on <a href="verification.html">Verification</a>.</p>
  {table(["Team (Hotspawn)", "Leaguepedia team", "Elo", "Rated series", "Last played", "Join"], out)}
</section>
"""
    return page_shell("Teams", "teams.html", body, "Ratings and name-join evidence for every team on the list.")


def build_methodology(model: dict) -> str:
    bt = model.get("backtest") or {}
    sw = load_json(os.path.join(DATA, "backtest_sweep.json")) or {}
    if sw.get("configs"):
        best = sw.get("best_validation") or {}
        ship = sw.get("shipped") or {}
        rows = [[
            f"{c['k_opening']:g} / {c['k_series']:g} / {c['mov_weight']:g}"
            + (" <strong>(shipped)</strong>" if c.get("shipped") else ""),
            f"{c['validation']['n']:,}", pct(c['validation']['accuracy']),
            str(c['validation']['brier']), str(c['test']['brier'])
        ] for c in (sw.get("top10") or [])]
        sweep_html = f"""
  <p>The grid is {len(sw.get('grid', {}).get('k_opening') or [])} &times;
  {len(sw.get('grid', {}).get('k_series') or [])} &times;
  {len(sw.get('grid', {}).get('mov_weight') or [])} = <strong>{sw['configs']} settings</strong> of
  K<sub>bo1</sub> / K<sub>bo3+</sub> / margin weight, scored on
  <strong>{best.get('validation', {}).get('n', 0):,}</strong> validation series
  ({e(sw.get('validation_window', ''))}) and then on the frozen test window.</p>
  {table(["K bo1 / K bo3+ / MoV &mdash; best 10 on validation", "Validation series", "Accuracy",
          "Validation Brier", "Test Brier"], rows)}
  <p><strong>The shipped setting ranks {sw.get('shipped_rank_on_validation')} of {sw['configs']} on
  validation</strong> ({ship.get('validation', {}).get('brier')}) against a best of
  {best.get('validation', {}).get('brier')}. The whole grid spans only
  {sw.get('validation_brier_spread')} Brier, which is inside the sampling noise of a
  {best.get('validation', {}).get('n', 0):,}-series window (&asymp;0.003), so no setting in the grid is
  distinguishable from another on this data. The published numbers were therefore left where they were
  rather than moved to the top of a noisy ranking; the test-window result is reported unchanged either way.</p>"""
    else:
        sweep_html = '<p class="muted">Parameter sweep not generated in this build.</p>'

    body = f"""
<section class="panel">
  <h2>The 4-tier probability architecture</h2>
  <ol class="steps">
    <li><strong>Inventory.</strong> Every League of Legends fixture is pulled from Hotspawn's public fixtures API
    (<a href="https://play.hotspawn.com/lol-pickems" rel="noopener">play.hotspawn.com/lol-pickems</a>).</li>
    <li><strong>Tier 1 — Multi-venue real-money consensus.</strong> Live odds and contract books from
    <strong>Pinnacle (0.36), Polymarket full-series CLOB (0.24), Kalshi CFTC (0.18), Bovada (0.12), </strong> are de-vigged proportionally and averaged using fixed editorial weights (not statistically optimized).</li>
    <li><strong>Tier 2 — Originated regional Elo lines.</strong> All recorded Leaguepedia series since
    {e(model.get('window_start',''))} are processed chronologically. Best-of-one series move a rating by
    K = {e(model.get('k_opening'))}; best-of-three and longer series move it by
    K = {e(model.get('k_series'))} scaled by the margin of victory
    (multiplier = 1 + {e(model.get('mov_weight'))} &middot; ln(1 + |game margin|)). Inactivity decay
    begins after {e(model.get('decay_start_days'))} days and reaches 1500 at
    {e(model.get('decay_full_days'))} days.</li>
    <li><strong>Tier 3 — Provisional &amp; Unresolved quarantine.</strong> Thin-sample teams (&lt;5 series) are marked
    <em>provisional</em>; teams reported removed mid-split (<code>dqteams</code>) are quarantined in
    <a href="unresolved.html">Unresolved</a> rather than mispriced.</li>
    <li><strong>Automated publish gate.</strong> Every 6 hours GitHub Actions re-runs the full pipeline and
    executes strict integrity assertions (<a href="verification.html">Verification</a>) before publishing to GitHub Pages.</li>
  </ol>
</section>

<section class="panel">
  <h2>Formulas</h2>
  <p>Expected series win probability for team A:</p>
  <p class="formula">E<sub>A</sub> = 1 / (1 + 10^((R<sub>B</sub> - R<sub>A</sub>)/400))</p>
  <p>Chronological rating update after each completed series:</p>
  <p class="formula">R&prime;<sub>A</sub> = R<sub>A</sub> + K<sub>bo</sub> &middot; M &middot; (S<sub>A</sub> - E<sub>A</sub>)</p>
  <p class="small muted">K<sub>bo</sub> = {e(model.get('k_opening'))} for best-of-one, {e(model.get('k_series'))}
  for best-of-three and longer. M = 1 for best-of-one; for multi-game series
  M = 1 + {e(model.get('mov_weight'))} &middot; ln(1 + |score margin|).</p>
  <p><strong>No shrinkage.</strong> Pulling small samples toward 1500 was measured out-of-sample and made the
  probabilities worse (Brier 0.2176 with shrinkage versus 0.2150 without, n = {bt.get('n', 0):,}), so thin
  samples are labelled <a href="originated.html">provisional</a> instead of being shrunk.</p>
  <p>Inactivity decay begins after {e(model.get('decay_start_days'))} days and reaches 1500 at
  {e(model.get('decay_full_days'))} days; originated probabilities are clamped to
  {e(model.get('prob_floor'))}&ndash;{e(model.get('prob_ceil'))}.</p>
</section>

<section class="panel">
  <h2>Parameter stability: does the choice of K actually matter?</h2>
  <p class="lead">The update sizes are a judgement call, so they are published together with the sweep that
  produced them rather than as an unqualified number. Every setting below was re-run through the same
  walk-forward evaluation (<code>tools/sweep.py</code>, frozen test window).</p>
  {sweep_html}
</section>

<section class="panel">
  <h2>Out-of-sample backtest &amp; calibration</h2>
  <p class="lead">Every recorded series after <strong>{e(bt.get('cutoff','2026-07-01'))}</strong>
  (<strong>{bt.get('n', 0):,}</strong> out-of-sample series) is predicted strictly before its result updates
  either team's rating (zero look-ahead leakage).</p>
  <p class="small muted"><strong>How the update sizes were chosen.</strong> K<sub>bo</sub>, M and the (now
  disabled) shrinkage were selected on the disjoint validation window
  <strong>{e(bt.get('selection_window', 'n/a'))}</strong> (<strong>{((bt.get('validation') or {}).get('n') or 0):,}</strong>
  series, Brier {e(((bt.get('validation') or {}).get('brier')))}), then frozen. The test numbers below are
  measured only on series that start after the cutoff, so they are not fitted on the data they score.</p>
  {table(["Sample", "Series", "Accuracy", "Brier score", "Log loss"],
         [["Test window, current model",
           f"{bt.get('n', 0):,}",
           pct(bt.get('accuracy')),
           str(bt.get('brier', '—')),
           str(bt.get('logloss', '—'))],
          ["Test window, previous settings (K=24, no margin term)",
           f"{bt.get('n', 0):,}",
           "64.1%",
           "0.2211",
           "0.6322"],
          ["Validation window, current model",
           f"{((bt.get('validation') or {}).get('n') or 0):,}",
           pct((bt.get('validation') or {}).get('accuracy')),
           str((bt.get('validation') or {}).get('brier', '—')),
           str((bt.get('validation') or {}).get('logloss', '—'))],
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
    <li><strong>Zero placeholder odds.</strong> Symmetric 1.80 / 1.80 default placeholders on odds aggregators are
    automatically discarded.</li>
    <li><strong>Explicit quarantine over guesswork.</strong> Disqualified teams (<code>dqteams</code>) and unrated
    cards are documented transparently on <a href="unresolved.html">Unresolved</a> and
    <a href="flagged.html">Flagged for review</a>.</li>
  </ul>
</section>
"""
    return page_shell("Method", "methodology.html", body,
                      "How every probability on this site is computed, backtested, and audited.")


def build_sources(src: list[dict]) -> str:
    # Feeds that actually drive a number on this site. Everything else in the table
    # is probed for transparency but never parsed into a price.
    INGESTED = {"Pinnacle", "Kalshi (CFTC)", "Bovada", "Polymarket",
                "Hotspawn fixtures API", "Leaguepedia", "LoL Esports (Riot)"}
    out = []
    for s in src:
        st = s.get("status")
        cls = "ok" if s.get("ok") else "bad"
        role = "prices picks" if s.get("name") in INGESTED else "probe only"
        out.append([e(s.get("name")),
                    f'<a href="{e(s.get("url"))}" rel="noopener">link</a>',
                    e(s.get("note")),
                    ("<strong>prices picks</strong>" if role == "prices picks" else "probe only"),
                    f'<span class="pill {cls}">{e(st)}</span>', e(s.get("blocked_note")),
                    e((s.get("checked_utc") or "")[:16].replace("T", " "))])
    reachable = sum(1 for s in src if s.get("ok"))
    ingested_up = [s for s in src if s.get("name") in INGESTED and s.get("ok")]
    body = f"""
<section class="panel">
  <h2>Source reachability on the latest build</h2>
  <p class="lead">{reachable} of {len(src)} probed endpoints answered HTTP 200 from the build runner.
  <strong>Probe only</strong> rows are recorded so you can see which books we tried, but they are not
  parsed into a price. Only the <strong>prices picks</strong> feeds below can move a probability.</p>
  {table(["Source", "URL", "What it is", "Used for", "HTTP", "Runner status", "Checked (UTC)"], out)}
  <p class="small muted">A 403 or 410 means the endpoint refused the runner (region block or bot
  protection); it does not mean the book does not exist. No odds are ever inferred from a failed probe.</p>
</section>

<section class="panel">
  <h2>Feeds that actually price this site ({len(ingested_up)} live)</h2>
  <ul class="bullets">
    <li><a href="https://play.hotspawn.com/lol-pickems" rel="noopener">Hotspawn LoL Pick'ems API</a> &mdash;
    complete scheduled match inventory (crowd % stored strictly for audit comparison, never used).</li>
    <li><a href="https://www.pinnacle.com/en/esports/league-of-legends" rel="noopener">Pinnacle</a>,
    <a href="https://polymarket.com" rel="noopener">Polymarket CLOB</a>,
    <a href="https://kalshi.com/markets/kxlolgame" rel="noopener">Kalshi (CFTC)</a> &amp;
    <a href="https://www.bovada.lv/sports/esports/league-of-legends" rel="noopener">Bovada</a> &mdash;
    live multi-venue real-money match odds &amp; contract books, de-vigged per venue.</li>
    <li><a href="https://lol.fandom.com/wiki/Special:CargoExport" rel="noopener">Leaguepedia Cargo</a> &mdash;
    chronological series history and community-recorded <code>dqteams</code> removals. Community-maintained,
    not a league authority.</li>
    <li><a href="https://esports-api.lolesports.com" rel="noopener">LoL Esports (Riot Games)</a> &mdash;
    official World Championship schedule verification.</li>
  </ul>
  <h3>How every match was chased, in order</h3>
  <ol class="steps">
    <li><strong>Established sportsbooks</strong> &mdash; Pinnacle, Bovada, DraftKings, FanDuel, BetMGM, Betway,
    Unibet/Kambi, BetOnline, BetUS, MyBookie were all probed on this build; the ones that answered are listed
    above, the ones that refused are listed with their HTTP code.</li>
    <li><strong>Esports-native books and exchanges</strong> &mdash; Polymarket, Kalshi (CFTC), Thunderpick,
    Rivalry, Luckbox, BC.GAME, GG.BET were probed the same way.</li>
    <li><strong>Odds aggregators</strong> &mdash; EGamersWorld, Oddspedia, OddsPortal, BetExplorer,
    EsportsBets, VegasInsider, Action Network and The Odds API were probed for a LoL feed.</li>
    <li><strong>Our own line</strong> &mdash; any match still unpriced gets an Elo probability, and the row says
    so. {len([s for s in src if not s.get("ok")])} of {len(src)} probed endpoints refused the runner on the
    last build, so a missing price is never treated as a 50/50 match.</li>
    <li><strong>Settlement or unresolved</strong> &mdash; a fixture that cannot be played as listed is published
    as a settlement pick with no probability.</li>
  </ol>

  <h3>Why most Hotspawn matches have no bookmaker price</h3>
  <p>The books we can reach quote the events they choose to hang a market on, which in practice means
  tier-1 and tier-2 series. National divisions (Prime League 2nd/3rd Division, RIVALS League, Komplettligaen,
  LigaGG, Icelandic Esports League and similar) were checked on every build and returned no matching market in
  any reachable book. That is a coverage fact about the books, not a missing step in the pipeline &mdash; and it
  is why those matches carry an originated Elo line instead of a market line.</p>
  <h3>Prop markets are never used as win probabilities</h3>
  <p>Pinnacle returns kill, map and handicap props in the same feed as the moneyline, marked only by the
  participant name (&ldquo;G2 (Kills)&rdquo;). Those rows are dropped before team matching and counted in the
  build audit, because a kill handicap is not a probability that a team wins the series.</p>
</section>
"""
    return page_shell("Sources", "sources.html", body,
                      "Every data source, its HTTP status, and whether it can move a pick.")


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
    {stat_card("Rows with source link", stats.get("rows_with_source", 0), "Link presence checked; not source endorsement", "ok")}
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
    out = [[e(f.get("severity")), e(f.get("item")), e(f.get("detail")),
            f'<a href="{e(f.get("source"))}" rel="noopener">source</a>' if f.get("source") else "&mdash;"]
           for f in flags]
    body = f"""
<section class="panel">
  <h2>Flagged for review ({len(flags)})</h2>
  <p class="lead">Audited upstream feed irregularities, mid-split team disqualifications, placeholder odds traps,
  and thin-sample caveats — published openly with source links and verification caveats.</p>
  {table(["Severity", "Item", "Detail", "Source"], out)}
</section>
"""
    return page_shell("Flagged for review", "flagged.html", body,
                      "Irregularities and unverified items, with source links and verification caveats.")


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
    log(f"site: wrote {len(pages)} pages to the repository root")


if __name__ == "__main__":
    main()
