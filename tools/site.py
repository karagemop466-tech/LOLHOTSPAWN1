#!/usr/bin/env python3
"""Generate the static GitHub Pages dashboard from data/matches.json.

Design goals: mobile-first, one clear place to find every pick, executive summary
with in-site links, and a source link on every row.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, ROOT, iso, load_json, log, now_utc

DOCS = os.path.join(ROOT, "docs")
SITE_URL = "https://karagemop466-tech.github.io/LOLHOTSPAWN1/"

METHOD_LABEL = {
    "market": "Market line",
    "model": "Model line",
    "provisional": "Provisional",
    "unresolved": "Unresolved",
}
METHOD_HELP = {
    "market": "Real bookmaker or prediction-market price, vig removed.",
    "model": "Our Elo line from recorded series results (both teams rated, connected).",
    "provisional": "Our Elo line with thin data - low confidence, shown but flagged.",
    "unresolved": "No defensible probability. Listed in the Unresolved section.",
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


def day_label(iso_utc: str | None) -> str:
    if not iso_utc:
        return "Date TBD"
    return iso_utc[:10]


def badge(method: str) -> str:
    return f'<span class="badge b-{e(method)}">{e(METHOD_LABEL.get(method, method))}</span>'


def page_shell(title: str, active: str, body: str, subtitle: str = "") -> str:
    nav_parts = []
    for href, label in NAV:
        cls = ' class="active"' if href == active else ""
        nav_parts.append(f'<a href="{e(href)}"{cls}>{e(label)}</a>')
    nav = "".join(nav_parts)
    meta = load_json(os.path.join(DATA, "matches.json")) or {}
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
    <p class="stamp">Data snapshot: <strong>{e(updated)} UTC</strong> &middot; refreshed automatically every 6 hours</p>
  </div>
  {body}
</main>
<footer class="wrap foot">
  <p>Independent research dashboard. Every row links to its source. Not betting advice.</p>
  <p><a href="methodology.html">Method</a> &middot; <a href="verification.html">Verification</a> &middot;
  <a href="flagged.html">Flagged for review</a> &middot; <a href="sources.html">Sources</a></p>
</footer>
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
    pick_html = ""
    if pick:
        pick_html = (f'<div class="pickline"><span class="picklabel">Pick</span> '
                     f'<strong>{e(pick["team"])}</strong> '
                     f'<span class="pickpct">{pick["probability"]*100:.0f}%</span></div>')
    else:
        pick_html = '<div class="pickline"><span class="picklabel">No pick</span> ' \
                    '<span class="muted">see Unresolved</span></div>'
    flags = ""
    if r["flags"]:
        flags = '<ul class="flags">' + "".join(f"<li>{e(f)}</li>" for f in r["flags"]) + "</ul>"
    sources = ""
    if show_sources:
        links = [f'<a href="{e(r["hotspawn_url"])}" rel="noopener">Hotspawn match card</a>']
        mk = r.get("market") or {}
        if mk.get("market_url"):
            links.append(f'<a href="{e(mk["market_url"])}" rel="noopener">{e(mk["book"])}</a>')
        if t0.get("leaguepedia"):
            links.append(f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(t0["leaguepedia"])}" '
                         f'rel="noopener">Leaguepedia: {e(t0["leaguepedia"])}</a>')
        if t1.get("leaguepedia"):
            links.append(f'<a href="https://lol.fandom.com/wiki/{leaguepedia_slug(t1["leaguepedia"])}" '
                         f'rel="noopener">Leaguepedia: {e(t1["leaguepedia"])}</a>')
        sources = '<div class="src">' + "".join(links) + "</div>"

    return f"""<article class="card m-{e(m)}" data-method="{e(m)}" data-comp="{e(r['competition'])}"
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
  <details class="why"><summary>Why this line</summary>
    <p>{e(r['basis'])}</p>
    {flags}
  </details>
  {sources}
</article>"""


def leaguepedia_slug(name: str) -> str:
    from urllib.parse import quote
    return quote(str(name).replace(" ", "_"), safe="()_',!.")


def stat_card(label: str, value, note: str = "", cls: str = "") -> str:
    return (f'<div class="stat {cls}"><div class="sv">{value}</div>'
            f'<div class="sl">{e(label)}</div>{f"<div class=sn>{e(note)}</div>" if note else ""}</div>')


def table(headers: list[str], rows: list[list[str]], cls: str = "") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td data-label=\"{headers[i]}\">{c}</td>"
                                     for i, c in enumerate(row)) + "</tr>" for row in rows)
    return f'<div class="tablewrap"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


# --------------------------------------------------------------------------- pages
def build_index(rows: list[dict], counts: Counter, src_status: list[dict]) -> str:
    total = len(rows)
    with_pick = sum(1 for r in rows if r["pick"])
    upcoming = sorted([r for r in rows if r["start_utc"] and r["start_utc"] > iso(now_utc())],
                      key=lambda r: r["start_utc"])
    next24 = [r for r in upcoming if r["start_utc"] < iso(now_utc())[:11] + "99"][:6]
    featured = [r for r in rows if r["method"] == "market"]
    unresolved = [r for r in rows if r["method"] == "unresolved"]
    provisional = [r for r in rows if r["method"] == "provisional"]
    comps = len({r["competition"] for r in rows})
    live_sources = sum(1 for s in src_status if s.get("ok"))

    body = f"""
<section class="hero">
  <h2>Every Hotspawn League of Legends match, with a line we can defend.</h2>
  <p>This dashboard rebuilds itself from the Hotspawn pick'em list every six hours. For each match we
  either de-vig a real bookmaker price or publish our own Elo line built from recorded series results.
  Nothing on this site uses Hotspawn's crowd-pick percentages.</p>
  <div class="cta">
    <a class="btn primary" href="picks.html">All {total} matches &amp; picks &rarr;</a>
    <a class="btn" href="featured.html">Market-backed picks ({len(featured)})</a>
    <a class="btn" href="originated.html">Our own lines ({counts.get('model',0)+counts.get('provisional',0)})</a>
    <a class="btn" href="unresolved.html">Unresolved &amp; limits ({len(unresolved)})</a>
  </div>
</section>

<section class="stats">
  {stat_card("Matches listed on Hotspawn", total, f"across {comps} tournaments")}
  {stat_card("Matches with a pick", with_pick, f"{with_pick/total*100:.0f}% coverage", "ok")}
  {stat_card("Market-backed", len(featured), "real bookmaker prices", "market")}
  {stat_card("Our own lines", counts.get('model',0), "model, medium confidence", "model")}
  {stat_card("Provisional", len(provisional), "thin data, flagged", "provisional")}
  {stat_card("Unresolved", len(unresolved), "no defensible price", "unresolved")}
</section>

<section class="panel">
  <h2>Where the picks live</h2>
  <p class="lead">Bookmark <a href="picks.html"><strong>All picks</strong></a> - it is the single page with
  every match on today's Hotspawn list, newest first. Everything below is a filtered view of the same data.</p>
  <ul class="linklist">
    <li><a href="picks.html">All picks &rarr;</a><span>Complete list, {total} matches, filterable and searchable.</span></li>
    <li><a href="featured.html">Market-backed picks &rarr;</a><span>{len(featured)} matches with a real bookmaker or prediction-market price and the vig removed.</span></li>
    <li><a href="originated.html">Our own lines &rarr;</a><span>{counts.get('model',0)+counts.get('provisional',0)} matches priced from our Elo model, with the inputs shown.</span></li>
    <li><a href="unresolved.html">Unresolved picks &amp; limitations &rarr;</a><span>{len(unresolved)} match(es) we refuse to price, plus every documented limitation and the provisional list.</span></li>
    <li><a href="competitions.html">By tournament &rarr;</a><span>Coverage and source quality for each of the {comps} tournaments.</span></li>
    <li><a href="verification.html">Verification &rarr;</a><span>Row-level checks, join evidence, and what is unverified.</span></li>
  </ul>
</section>

<section class="panel">
  <h2>Next matches</h2>
  <div class="cards">
    {"".join(match_card(r, show_sources=False) for r in upcoming[:6]) or '<p class="muted">No upcoming matches in the current snapshot.</p>'}
  </div>
  <p><a class="btn" href="picks.html">See the full list &rarr;</a></p>
</section>

<section class="panel">
  <h2>Executive summary</h2>
  <ul class="bullets">
    <li><strong>Coverage.</strong> {with_pick} of {total} matches have a pick. {len(featured)} come from market
    prices (Pinnacle moneylines, plus Polymarket where a live market exists); {counts.get('model',0)} come from
    our Elo model and {len(provisional)} are provisional model lines with thin data.</li>
    <li><strong>Unresolved.</strong> {len(unresolved)} match(es) cannot be priced from any verified source; they are
    listed on <a href="unresolved.html">Unresolved</a> with the exact reason, never guessed.</li>
    <li><strong>Independent of Hotspawn.</strong> Hotspawn's public pick percentages are not used as inputs anywhere
    in the maths - see <a href="methodology.html">Method</a>.</li>
    <li><strong>Sources.</strong> {live_sources} of {len(src_status)} checked data sources responded; the rest are
    documented as blocked on <a href="sources.html">Sources</a>.</li>
    <li><strong>Refresh cadence.</strong> A GitHub Actions job re-pulls Hotspawn, Pinnacle and Leaguepedia every 6
    hours and republishes this site. Snapshot time is shown at the top of every page.</li>
    <li><strong>Flagged for review.</strong> Data irregularities and unverified items are collected on
    <a href="flagged.html">Flagged for review</a>.</li>
  </ul>
</section>
"""
    return page_shell("Hotspawn LoL Pick Desk", "index.html", body,
                      "Independent win probabilities for every League of Legends match in the Hotspawn pick'em.")


def build_picks(rows: list[dict], counts: Counter) -> str:
    rows = sorted(rows, key=lambda r: (r.get("stale", False), r["start_utc"] or "9999"))
    comps = sorted({r["competition"] for r in rows})
    chips = "".join(
        f'<button class="chip" data-filter="{m}">{METHOD_LABEL[m]} <span>{counts.get(m,0)}</span></button>'
        for m in ("market", "model", "provisional", "unresolved"))
    opts = "".join(f'<option value="{e(c)}">{e(c)}</option>' for c in comps)
    body = f"""
<section class="panel">
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search team or tournament" aria-label="Search team or tournament">
    <select id="comp" aria-label="Filter by tournament"><option value="">All tournaments</option>{opts}</select>
    <div class="chips"><button class="chip active" data-filter="">All <span>{len(rows)}</span></button>{chips}</div>
  </div>
  <p class="muted small" id="count">{len(rows)} matches shown</p>
  <div class="cards" id="list">
    {"".join(match_card(r) for r in rows)}
  </div>
  <p class="empty" id="empty" hidden>No matches match that filter.</p>
</section>
"""
    return page_shell("All picks", "picks.html", body,
                      f"Every League of Legends match on the Hotspawn pick'em list ({len(rows)} matches), "
                      "soonest first. Tap a card for the reasoning and source links.")


def build_featured(rows: list[dict]) -> str:
    items = [r for r in rows if r["method"] == "market"]
    rows_html = []
    for r in items:
        m = r["market"]
        dec = m.get("decimal") or {}
        rows_html.append([
            local_time(r["start_utc"]),
            e(r["competition"]),
            f'{e(r["team0"]["name"])} vs {e(r["team1"]["name"])}',
            pct(r["p0"]) + " / " + pct(r["p1"]),
            f'{e(m["book"])}<br><span class="muted small">{e(m.get("kind",""))}</span>',
            (f'{dec.get("home","")} / {dec.get("away","")}' if dec else "market price"),
            f'<a href="{e(m.get("market_url") or m.get("source_url"))}" rel="noopener">line</a> &middot; '
            f'<a href="{e(r["hotspawn_url"])}" rel="noopener">card</a>',
        ])
    body = f"""
<section class="panel">
  <h2>{len(items)} matches with a real market price</h2>
  <p class="lead">These are the "featured" matches - fixtures that a bookmaker or prediction market actually
  prices. We convert American odds to decimal, remove the bookmaker margin proportionally, and publish the
  implied probability. The pick is simply the side above 50%.</p>
  {table(["Start (UTC)", "Tournament", "Match", "Our line (A / B)", "Book", "Decimal odds", "Sources"], rows_html)}
  <h3>How the de-vig works</h3>
  <p class="formula">p&#8321; = (1/o&#8321;) / (1/o&#8321; + 1/o&#8322;)</p>
  <p>This is the standard proportional method: it assumes the bookmaker's margin is spread evenly across both
  sides. The overround is shown per match in the raw
  <a href="https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/picks.csv">picks.csv</a>.</p>
  <div class="cards">{"".join(match_card(r) for r in items)}</div>
</section>
"""
    return page_shell("Market-backed picks", "featured.html", body,
                      "Matches with a real bookmaker or prediction-market price.")


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
            if r.get("leaguepedia_page") else '<span class="muted">no page</span>',
        ])
    body = f"""
<section class="panel">
  <h2>{len(items)} matches priced by our own model</h2>
  <p class="lead">No bookmaker prices these leagues, so we originate the line. The model is a plain Elo
  rating fitted on every recorded series in Leaguepedia since {e((load_json(os.path.join(DATA,'matches.json')) or {}).get('model',{}).get('window_start',''))},
  with a time decay for inactive teams and a shrinkage factor for teams with few results.</p>
  <div class="stats tight">
    {stat_card("Solid model lines", counts.get('model',0), "both teams rated, connected", "model")}
    {stat_card("Provisional lines", counts.get('provisional',0), "thin data - flagged", "provisional")}
  </div>
  {table(["Start (UTC)", "Tournament", "Match", "Elo (n) A / B", "Our line", "Status", "Results"], reviews)}
  <h3>Formula</h3>
  <p class="formula">P(A) = 1 / (1 + 10^((R<sub>B</sub> - R<sub>A</sub>) / 400))</p>
  <p>The rating inputs, the number of rated series behind each rating, and the join evidence to Leaguepedia are
  printed for every row. Probabilities are clamped to 5-95% so the desk never claims certainty.</p>
</section>
"""
    return page_shell("Our own lines", "originated.html", body,
                      "Elo-derived probabilities for matches with no bookmaker coverage.")


def build_unresolved(rows: list[dict], counts: Counter) -> str:
    unresolved = [r for r in rows if r["method"] == "unresolved"]
    provisional = [r for r in rows if r["method"] == "provisional"]
    one_sided = [r for r in rows if r["method"] == "provisional"
                 and any("no rated series" in f for f in r["flags"])]
    ambiguous = [r for r in rows if any("ambiguous" in f or "could not be matched" in f for f in r["flags"])]
    reason_rows = []
    for r in unresolved:
        reason_rows.append([local_time(r["start_utc"]), e(r["competition"]),
                            f'{e(r["team0"]["name"])} vs {e(r["team1"]["name"])}',
                            e(r["basis"]), f'<a href="{e(r["hotspawn_url"])}" rel="noopener">card</a>'])
    lim_rows = [
        ["No bookmaker market", f"{len([r for r in rows if r['method']!='market'])} matches",
         "Pinnacle (our sharp book) prices only the World Championship and EMEA Masters from this list. "
         "Tier-B/C/D national leagues have no published market on any book we could reach."],
        ["Thin match history", f"{counts.get('provisional',0)} provisional",
         "The two teams have fewer than five rated series each in the 25-month Leaguepedia window, so the "
         "Elo difference is noisy. We still publish a number but mark it provisional."],
        ["One-sided history", f"{len(one_sided)} matches",
         "One team has no recorded series at all. The model assigns that side the 1500 baseline; this is an "
         "assumption, not a measurement, and is flagged on every affected card."],
        ["Name matching", f"{len(ambiguous)} matches",
         "Leaguepedia disambiguates teams with a region suffix (e.g. 'Fenrir (Icelandic Team)'). We only join "
         "when the match is unique or the competition page confirms it; otherwise the team stays unmatched."],
        ["No shared opponents", "0-3 matches",
         "Elo ratings are only comparable inside one connected opponent graph. Cross-pool matches are flagged."],
        ["Book coverage blocked", "see Sources",
         "GG.BET returned a regional block, EGamersWorld served a Cloudflare challenge, Oddspedia returned 410, "
         "BetExplorer 404 and Unibet/Kambi 400 from the build runner. These are documented on Sources."],
    ]
    body = f"""
<section class="panel">
  <h2>Unresolved picks ({len(unresolved)})</h2>
  <p class="lead">A match lands here only when we have neither a market price nor a single rated series for
  either team. We would rather show nothing than invent a number.</p>
  {'<p class="muted">No unresolved matches in this snapshot.</p>' if not unresolved else table(["Start (UTC)", "Tournament", "Match", "Why it is unresolved", "Source"], reason_rows)}
</section>

<section class="panel">
  <h2>Limitations that apply to the rest of the list</h2>
  {table(["Limitation", "Scope", "What it means"], lim_rows)}
</section>

<section class="panel">
  <h2>Provisional lines ({len(provisional)})</h2>
  <p class="lead">These have a pick, but with low confidence. Each card lists the exact reason.</p>
  <div class="cards">{"".join(match_card(r) for r in provisional)}</div>
</section>
"""
    return page_shell("Unresolved &amp; limitations", "unresolved.html", body,
                      "What we cannot price, and why - plus every documented limitation.")


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
  <h2>Coverage by tournament</h2>
  <p class="lead">Every tournament on the Hotspawn LoL list, with how each match was priced and the
  Leaguepedia results page used to build the ratings.</p>
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
            e(t["lp"]) if t["lp"] else '<span class="muted">not matched</span>',
            str(t["elo"]) if t["elo"] is not None else "&mdash;",
            str(t["n"] or 0),
            e(t["last"] or "&mdash;"),
            f'<span class="join j-{e(t["join"])}">{e(t["join"])}</span>'] for t in ordered]
    body = f"""
<section class="panel">
  <h2>{len(ordered)} teams on the current list</h2>
  <p class="lead">Ratings are only comparable within a league's opponent graph. The join column shows how the
  Hotspawn name was matched to Leaguepedia - anything other than <em>exact</em> is also listed on
  <a href="verification.html">Verification</a>.</p>
  {table(["Team (Hotspawn)", "Leaguepedia team", "Elo", "Rated series", "Last played", "Join"], out)}
</section>
"""
    return page_shell("Teams", "teams.html", body, "Ratings and name-join evidence for every team on the list.")


def build_methodology(model: dict) -> str:
    body = f"""
<section class="panel">
  <h2>The pipeline</h2>
  <ol class="steps">
    <li><strong>Inventory.</strong> Every League of Legends fixture is pulled from Hotspawn's own pick'em
    fixtures API (the same JSON that renders <a href="https://play.hotspawn.com/lol-pickems" rel="noopener">play.hotspawn.com/lol-pickems</a>).</li>
    <li><strong>Market prices.</strong> Pinnacle's esports feed is filtered to League of Legends, then each
    matchup's moneyline is pulled. Polymarket is used only where a live two-sided market exists.</li>
    <li><strong>History.</strong> Every series result since {e(model.get('window_start',''))} comes from Leaguepedia's Cargo
    export of <code>MatchSchedule</code>, the community-maintained results database for LoL esports.</li>
    <li><strong>Our line.</strong> Elo is fitted over series results in chronological order, then decayed for
    inactivity and shrunk toward the mean for teams with few results.</li>
    <li><strong>Publish.</strong> The site is regenerated and verified by CI, then committed to GitHub Pages.</li>
  </ol>
</section>

<section class="panel">
  <h2>Formulas</h2>
  <p>Expected score for team A:</p>
  <p class="formula">E<sub>A</sub> = 1 / (1 + 10^((R<sub>B</sub> - R<sub>A</sub>)/400))</p>
  <p>Rating update after a series (K = {e(model.get('k'))}):</p>
  <p class="formula">R&prime;<sub>A</sub> = R<sub>A</sub> + K &middot; (S<sub>A</sub> - E<sub>A</sub>)</p>
  <p>Shrinkage towards the 1500 start rating for a team with n rated series:</p>
  <p class="formula">R<sub>eff</sub> = 1500 + (R - 1500) &middot; n / (n + {e(model.get('shrink'))})</p>
  <p>Time decay begins after {e(model.get('decay_start_days'))} days without a series and reaches the 1500 baseline
  after {e(model.get('decay_full_days'))} days.</p>
  <p>Probabilities are clamped to {e(model.get('prob_floor'))}-{e(model.get('prob_ceil'))}.</p>
</section>

<section class="panel">
  <h2>Out-of-sample backtest</h2>
  <p class="lead">The model is a live predictor, so we score it the way a bettor would: every series after
  {e((model.get('backtest') or {}).get('cutoff',''))} is predicted using only results recorded before it, then the rating is updated.</p>
  {table(["Sample", "Series", "Accuracy", "Brier", "Log loss"],
         [["All out-of-sample series",
           str((model.get('backtest') or {}).get('n', 0)),
           pct((model.get('backtest') or {}).get('accuracy')),
           str((model.get('backtest') or {}).get('brier', '—')),
           str((model.get('backtest') or {}).get('logloss', '—'))]])}
  {table(["Favourite bucket", "Series", "Predicted (avg)", "Actual win rate"],
         [[e(k), str(v['n']), pct(v['mean_predicted']), pct(v['accuracy'])]
          for k, v in ((model.get('backtest') or {}).get('buckets') or {}).items()])}
  <p class="small muted">A perfectly calibrated model has an actual win rate close to the predicted average
  in each bucket. Brier and log loss are lower-is-better; 0.25 is what a coin flip scores on Brier.</p>
</section>

<section class="panel">
  <h2>What we deliberately do not do</h2>
  <ul class="bullets">
    <li>We never use Hotspawn's crowd pick percentages as an input. They are captured in the raw data for
    transparency only.</li>
    <li>We never use Hotspawn's own editorial predictions as a probability.</li>
    <li>We do not fill in a missing price with a guess. Missing data means a provisional line with the
    limitation printed on the card, or an unresolved entry.</li>
    <li>We do not blend bookmaker and model numbers into one figure. Each row says which method produced it.</li>
  </ul>
</section>

<section class="panel">
  <h2>Refresh</h2>
  <p>A scheduled GitHub Actions workflow runs every 6 hours (cron <code>17 */6 * * *</code>), re-collects all
  sources, rebuilds the dataset and this site, runs the verification gate, and commits. The timestamp at the
  top of each page is the snapshot time in UTC.</p>
</section>
"""
    return page_shell("Method", "methodology.html", body,
                      "How each number on this site is produced, and what we refuse to do.")


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
  <h2>Sources checked on the last build</h2>
  <p class="lead">Every source is hit on each refresh so the table stays honest. A blocked source is left in
  the list rather than quietly dropped.</p>
  {table(["Source", "URL", "What it gives us", "HTTP", "Status", "Checked (UTC)"], out)}
  <h3>Primary sources in use</h3>
  <ul class="bullets">
    <li><a href="https://play.hotspawn.com/lol-pickems" rel="noopener">Hotspawn LoL pick'em</a> - the fixture
    list, via its public fixtures API.</li>
    <li><a href="https://www.pinnacle.com/en/esports/league-of-legends" rel="noopener">Pinnacle</a> - sharp
    bookmaker moneylines for the featured matches.</li>
    <li><a href="https://lol.fandom.com/wiki/Special:CargoExport" rel="noopener">Leaguepedia Cargo export</a> -
    series results used to fit the Elo model.</li>
    <li><a href="https://polymarket.com" rel="noopener">Polymarket</a> - prediction-market cross-check.</li>
    <li><a href="https://esports-api.lolesports.com" rel="noopener">LoL Esports (Riot)</a> - official schedule
    cross-check for the World Championship.</li>
  </ul>
</section>
"""
    return page_shell("Sources", "sources.html", body, "Every data source, its status, and what it provides.")


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
  <h2>Verification gate</h2>
  <p class="lead">Every build must pass these assertions before it can be committed. A failure stops the
  refresh instead of publishing a broken page.</p>
  {table(["Check", "Result", "Detail"], check_rows)}
</section>

<section class="panel">
  <h2>Row coverage</h2>
  <div class="stats tight">
    {stat_card("Rows checked", stats.get("rows_checked", len(rows)), "every match on the list")}
    {stat_card("Rows with a source link", stats.get("rows_with_source", 0), "Hotspawn card on every row", "ok")}
    {stat_card("Probabilities summing to 100%", stats.get("rows_prob_ok", 0), "A + B = 1 checked to 0.1pp", "market")}
    {stat_card("Unverified fields", stats.get("unverified", 0), "left blank, never inferred", "provisional")}
  </div>
</section>

<section class="panel">
  <h2>Name matches that are not exact</h2>
  <p class="lead">Leaguepedia disambiguates some teams with a region suffix. These are the joins that needed
  more than a literal string match, with the evidence used. Everything else matched exactly.</p>
  {table(["Hotspawn team", "Leaguepedia team", "Method", "Evidence"], joins) or '<p class="muted">All team names matched exactly in this build.</p>'}
</section>

<section class="panel">
  <h2>Raw data for line-by-line review</h2>
  <ul class="bullets">
    <li><a href="https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/picks.csv">data/picks.csv</a> - one row per match, with method, probability and source.</li>
    <li><a href="https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/matches.json">data/matches.json</a> - full record including Elo inputs and market prices.</li>
    <li><a href="https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/matching_report.json">data/matching_report.json</a> - every non-exact team join.</li>
    <li><a href="https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/verification.json">data/verification.json</a> - the machine-readable result of this gate.</li>
  </ul>
</section>
"""
    return page_shell("Verification", "verification.html", body,
                      "The checks every build must pass, and the evidence for each name match.")


def build_flagged(flags: list[dict]) -> str:
    out = [[e(f.get("severity")), e(f.get("item")), e(f.get("detail")),
            f'<a href="{e(f.get("source"))}" rel="noopener">source</a>' if f.get("source") else "&mdash;"]
           for f in flags]
    body = f"""
<section class="panel">
  <h2>Flagged for review ({len(flags)})</h2>
  <p class="lead">These items are published rather than hidden. None of them block the picks from being
  published; they are here so the assumptions are auditable.</p>
  {table(["Severity", "Item", "Detail", "Source"], out)}
</section>
"""
    return page_shell("Flagged for review", "flagged.html", body,
                      "Irregularities and unverified items, with links.")


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
    model = data.get("model") or {}
    comp_map = matching.get("competition_pages") or {}

    os.makedirs(os.path.join(DOCS, "assets"), exist_ok=True)
    pages = {
        "index.html": build_index(rows, counts, src),
        "picks.html": build_picks(rows, counts),
        "featured.html": build_featured(rows),
        "originated.html": build_originated(rows, counts),
        "unresolved.html": build_unresolved(rows, counts),
        "competitions.html": build_competitions(rows, comp_map),
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
    log(f"site: wrote {len(pages)} pages to docs/")


if __name__ == "__main__":
    main()
