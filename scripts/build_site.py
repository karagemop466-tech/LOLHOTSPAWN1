"""Render the static GitHub Pages site from ``data/*.json``.

    python -m scripts.build_site --data data --site site

Everything is generated (no manual editing): the executive summary, the full pick list, one
subpage per league and per tier, the unresolved-picks page with its limitations, the
flagged-for-review page, methodology and source ledger.  Each generated file is written only
if its content changed, so refresh commits stay small.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.common import (  # noqa: E402
    MONTH_NAMES, esc, iso, parse_iso, pct, slugify, utcnow, write_text,
)

SITE_TITLE = "Hotspawn LoL Pick'ems — Lines & Probabilities"
BASE_CSS = "assets/style.css"
BASE_JS = "assets/app.js"
NAV = [
    ("index.html", "Executive summary"),
    ("picks.html", "All picks"),
    ("leagues.html", "Leagues"),
    ("unresolved.html", "Unresolved picks"),
    ("flagged.html", "Flagged for review"),
    ("methodology.html", "Methodology"),
    ("sources.html", "Sources ledger"),
    ("data.html", "Download data"),
]


# --------------------------------------------------------------------------- utils
def write_if_changed(path: str, text: str) -> bool:
    old = None
    try:
        with open(path, encoding="utf-8") as fh:
            old = fh.read()
    except OSError:
        pass
    if old == text:
        return False
    write_text(path, text)
    return True


def fmt_when(kickoff: str | None, now) -> str:
    dt = parse_iso(kickoff)
    if not dt:
        return "TBD"
    delta = (dt - now).total_seconds()
    label = f"{dt.strftime('%H:%M UTC')} · {dt.day} {MONTH_NAMES[dt.month - 1]}"
    if delta <= 0:
        return f"started · {label}"
    hours = delta / 3600
    if hours < 1:
        return f"in {int(delta // 60)} min · {label}"
    if hours < 48:
        return f"in {int(hours)}h {int(delta % 3600 // 60)}m · {label}"
    return f"in {int(hours // 24)}d {int(hours % 24)}h · {label}"


DEFAULT_DESC = ("Hotspawn League of Legends pick'em lobby: every listed match with a win "
                "probability for both team, from external betting lines or our own "
                "self-originated model. Auto-refreshed.")


def layout(rel_prefix: str, title: str, body: str, *, updated: str, summary: dict,
           desc: str = "", active: str = "") -> str:
    def href(target: str) -> str:
        return (rel_prefix + target) if target else target

    nav = "\n".join(
        f'<a class="navlink{" is-active" if target == active else ""}" '
        f'href="{esc(href(target))}">{esc(label)}</a>'
        for target, label in NAV
    )
    cov = summary.get("headline", {})
    meta_desc = desc or DEFAULT_DESC
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0b0f16">
<title>{esc(title)}</title>
<meta name="description" content="{esc(meta_desc)}">
<link rel="stylesheet" href="{esc(href(BASE_CSS))}">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="brand">
    <span class="mark">LoL</span>
    <span>
      <b>{esc(SITE_TITLE)}</b>
      <small>updated {esc(updated)} · auto-refresh every {esc(str(summary.get('refresh_hours', 6)))}h ·
      {esc(str(cov.get('picks_resolved', 0)))}/{esc(str(cov.get('matches_on_hotspawn_lol_lobby', 0)))} picks resolved</small>
    </span>
  </div>
  <nav class="nav" aria-label="Site sections">{nav}</nav>
</header>
<main id="main">
{body}
</main>
<footer class="foot">
  <p>Data is collected and rebuilt by GitHub Actions every {esc(str(summary.get('refresh_hours', 6)))} hours
  (<code>.github/workflows/refresh.yml</code>) — no manual step. Probabilities come from external
  betting lines or our own model, never from Hotspawn's pick share.</p>
  <p>Unofficial research project. No bets are placed here; nothing on this site is betting advice.
  18+ / 21+. <a href="{esc(href('methodology.html'))}">Methodology &amp; limitations</a> ·
  <a href="{esc(href('sources.html'))}">Source ledger</a> ·
  <a href="{esc(href('flagged.html'))}">Flagged for review</a></p>
</footer>
<script src="{esc(href(BASE_JS))}" defer></script>
</body></html>
"""


def prob_bar(home: float | None, away: float | None) -> str:
    if home is None or away is None:
        return '<div class="bar empty"><span>no line — unresolved</span></div>'
    ph = round(home * 100, 1)
    pa = round(away * 100, 1)
    if ph + pa > 100:
        pa = round(100 - ph, 1)
    return (f'<div class="bar" role="img" aria-label="{ph}% home, {pa}% away">'
            f'<span class="seg home" style="width:{ph}%">{ph}%</span>'
            f'<span class="seg away" style="width:{pa}%">{pa}%</span></div>')


def source_links(row: dict) -> str:
    links = []
    if row.get("hotspawn_url"):
        links.append(("Hotspawn match page (lists this pick'em)", row["hotspawn_url"], "HS"))
    if row.get("hotspawn_feed_url"):
        links.append(("Hotspawn fixture feed record (official)", row["hotspawn_feed_url"], "FEED"))
    if row.get("league_page_url"):
        links.append(("Hotspawn league page (kickoff & results)", row["league_page_url"], "LEAGUE"))
    mkt = row.get("market") or {}
    if mkt.get("source_url"):
        links.append((f"{mkt.get('source_label') or 'market line'}", mkt["source_url"], "LINE"))
    for extra in (mkt.get("all_sources") or [])[1:]:
        if extra.get("url"):
            links.append((f"{extra.get('source')} price", extra["url"], extra.get("source") or "LINE"))
    for url in ((row.get("model") or {}).get("evidence_urls") or [])[:3]:
        links.append(("Scoreline used by the model", url, "RESULT"))
    out = []
    for title, url, short in links:
        out.append(f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener nofollow" '
                   f'title="{esc(title)}">{esc(short)}</a>')
    return '<span class="srcs">' + "".join(out) + "</span>"


BADGE = {
    "market": ('badge-market', "MARKET LINE"),
    "model": ('badge-model', "OUR OWN LINE"),
    "unresolved": ('badge-none', "UNRESOLVED"),
}


def pick_row(row: dict, now) -> str:
    teams = row.get("teams") or []
    home = teams[0] if len(teams) > 0 else {"name": "?"}
    away = teams[1] if len(teams) > 1 else {"name": "?"}
    basis = row.get("basis") or "unresolved"
    cls, label = BADGE.get(basis, BADGE["unresolved"])
    ph, pa = row.get("prob_home"), row.get("prob_away")
    pick_name, pick_prob = row.get("pick_team"), row.get("pick_prob")
    mdl = row.get("model") or {}
    mkt = row.get("market") or {}
    conf = mdl.get("confidence") if basis == "model" else None
    ver = row.get("verification") or {}
    ver_ok = bool(ver.get("all_ok"))
    kickoff = row.get("kickoff_utc")
    dt = parse_iso(kickoff)
    sort_ts = int(dt.timestamp()) if dt else 4102444800

    bits = []
    if mkt.get("odds_home"):
        bits.append(f'prices {mkt["odds_home"]} / {mkt.get("odds_away")}')
    if conf:
        bits.append(f"confidence {conf}")
    if mkt.get("source_spread") is not None:
        bits.append(f"spread between sources {pct(mkt.get('source_spread'))}")
    if basis == "model" and mdl.get("head_to_head_series"):
        bits.append(f"{mdl['head_to_head_series']} direct series in sample")
    line_html = f'<span class="line">{esc(" · ".join(bits))}</span>' if bits else ""

    why = esc(row.get("basis_detail") or "")
    pick_html = esc(pick_name or "none — unresolved")
    prob_html = f' <b>{esc(pct(pick_prob))}</b>' if pick_prob is not None else ""

    if mkt:
        mkt_html = (
            f'<p class="note">{esc(mkt.get("source_label"))}: raw implied '
            f'{esc(pct(mkt.get("implied_home_raw")))} / {esc(pct(mkt.get("implied_away_raw")))} '
            f'&rarr; de-vigged {esc(pct(mkt.get("prob_home")))} / {esc(pct(mkt.get("prob_away")))} '
            f'(orientation: {esc(mkt.get("orientation") or "as published")})</p>'
        )
    else:
        mkt_html = ""

    check_rows = []
    for c in (ver.get("checks") or []):
        url = c.get("source_url")
        link = (f'<a href="{esc(url)}" target="_blank" rel="noopener nofollow">open</a>'
                if url else "&mdash;")
        val = c.get("value")
        check_rows.append(
            "<tr>"
            f'<td>{esc(c.get("field"))}</td>'
            f'<td>{esc("" if val is None else val)}</td>'
            f'<td class="{"ok" if c.get("ok") else "no"}">{"yes" if c.get("ok") else "NO"}</td>'
            f"<td>{link}</td>"
            "</tr>")
    checks = "".join(check_rows)

    search = " ".join([home.get("name", ""), away.get("name", ""),
                      row.get("tournament") or ""]).lower()
    tier_cls = slugify(row.get("tier") or "na")
    points = row.get("points") if row.get("points") is not None else "—"
    mult = ""
    if row.get("multiplier"):
        mv = float(row["multiplier"])
        mult = f" ×{int(mv)}" if abs(mv - round(mv)) < 1e-9 else f" ×{mv:g}"

    return f"""<article class="pick {esc(basis)} {esc(row.get('status') or '')}"
   data-basis="{esc(basis)}" data-status="{esc(row.get('status'))}"
   data-tier="{esc(row.get('tier') or 'unlabelled')}"
   data-league="{esc(row.get('tournament') or 'unlabelled')}"
   data-ts="{sort_ts}" data-search="{esc(search)}">
  <header class="pick-head">
    <span class="when">{esc(fmt_when(kickoff, now))}</span>
    <span class="league">{esc(row.get('tournament') or 'unlabelled')}</span>
    <span class="chip tier-{esc(tier_cls)}">{esc(row.get('tier') or '—')}</span>
    <span class="chip">{esc(str(points))} pts{esc(mult)}</span>
    <span class="badge {cls}">{esc(label)}{esc(' · ' + conf if conf else '')}</span>
    <span class="badge badge-verify{' ok' if ver_ok else ' warn'}"
          title="{'all fixture/kickoff checks passed' if ver_ok else 'one or more checks could not be confirmed — see Flagged for review'}"
          >{'verified' if ver_ok else 'unverified'}</span>
  </header>
  <div class="vs">
    <div class="side{' winner' if pick_name == home.get('name') and pick_prob is not None else ''}">
      <span class="tname">{esc(home.get('name'))}</span><span class="pp">{esc(pct(ph) if ph is not None else '—')}</span>
    </div>
    <div class="side{' winner' if pick_name == away.get('name') and pick_prob is not None else ''}">
      <span class="tname">{esc(away.get('name'))}</span><span class="pp">{esc(pct(pa) if pa is not None else '—')}</span>
    </div>
  </div>
  {prob_bar(ph, pa)}
  <p class="pickline"><b>PICK:</b> {pick_html}{prob_html}
     <span class="why">{why}</span>{line_html}
  </p>
  <details class="meta"><summary>sources &amp; verification</summary>
    <p class="srcline">{source_links(row)}</p>
    <table class="mini"><thead><tr><th>check</th><th>value</th><th>ok</th><th>source</th></tr></thead>
      <tbody>{checks or '<tr><td colspan="4">no checks recorded</td></tr>'}</tbody></table>
    <p class="note"><b>Hotspawn crowd pick share — display only, never used as a probability:</b>
       {esc(home.get('name'))} {esc(str(home.get('hotspawn_pick_pct')))}% ·
       {esc(away.get('name'))} {esc(str(away.get('hotspawn_pick_pct')))}%</p>
    {mkt_html}
  </details>
</article>"""


def picks_table(rows: list[dict], now, empty_msg: str) -> str:
    if not rows:
        return f'<p class="empty">{esc(empty_msg)}</p>'
    return "\n".join(pick_row(r, now) for r in rows)


FILTERS = """
<div class="filters" role="group" aria-label="filter picks">
  <button class="fbtn is-active" data-filter="basis" data-value="all">all</button>
  <button class="fbtn" data-filter="basis" data-value="market">market line</button>
  <button class="fbtn" data-filter="basis" data-value="model">our own line</button>
  <button class="fbtn" data-filter="basis" data-value="unresolved">unresolved</button>
  <button class="fbtn" data-filter="status" data-value="closing soon">closing soon</button>
  <button class="fbtn" data-filter="status" data-value="today">next 24h</button>
  <label class="searchwrap"><span class="visually-hidden">search team or league</span>
    <input class="search" type="search" placeholder="search team / league" autocomplete="off"></label>
</div>"""


# --------------------------------------------------------------------------- pages
def page_index(site: str, data: dict, now) -> str:
    picks, unresolved, flags = data["picks"], data["unresolved"], data["flags"]
    summary = data["summary"]
    cov = summary["headline"]
    rel = ""
    soon = [p for p in picks if p.get("status") in ("closing soon", "locked", "today")]
    soon.sort(key=lambda r: r.get("kickoff_utc") or "9999")
    market_rows = [p for p in picks if p.get("basis") == "market"]
    model_rows = [p for p in picks if p.get("basis") == "model"]
    unres_rows = [p for p in picks if p.get("basis") == "unresolved"]
    by_tier = summary.get("tier_counts") or {}
    tiers_html = " ".join(
        f'<a class="chip chip-link" href="tiers/{slugify(t)}-picks.html">{esc(t)} ({n})</a>'
        for t, n in sorted(by_tier.items(), key=lambda kv: -kv[1])
    ) or "<em>none this window</em>"
    leagues_html = "".join(
        f'<li><a href="leagues/{slugify(name)}.html">{esc(name)}</a> <span class="muted">{n} picks</span></li>'
        for name, n in list((summary.get("league_counts") or {}).items())[:60]
    )
    lim_html = "".join(
        f'<h4>{esc(l.get("title"))}</h4><p>{esc(l.get("detail"))}'
        + (f' <span class="muted">affected rows: {l.get("affected_rows")}</span>' if l.get("affected_rows") else "")
        + "</p>"
        for l in (data["unresolved"].get("limitations") or [])
    )
    top_flags = "".join(
        f'<tr><td>{esc(f.get("match"))}</td><td>{esc(f.get("field"))}</td><td>{esc(f.get("reason"))}</td></tr>'
        for f in (flags.get("items") or [])[:8]
    )
    body = f"""
<section class="hero">
  <h1>Executive summary</h1>
  <p class="lede">Every League of Legends match Hotspawn is offering a pick&#39;em for this week,
  each with a win probability for both teams. Probabilities come from <b>external betting lines</b>
  when one exists and from <b>our own originated line</b> (series-level Elo over verified scorelines)
  when a book does not cover the match. Hotspawn's own crowd pick share is never used as a probability.</p>
  <p class="stamp">Snapshot generated <b>{esc(iso(now))}</b> · refreshed automatically every
  {esc(str(summary.get('refresh_hours', 6)))} hours · next update runs on the schedule in
  <code>.github/workflows/refresh.yml</code>.</p>
</section>

<section class="cta">
  <h2>Where the picks are</h2>
  <div class="cards">
    <a class="card primary" href="picks.html#closing"><b>All picks → closing soon</b>
       <span>The full updated list, newest lock first. Tap a row for sources.</span></a>
    <a class="card" href="picks.html"><b>All {cov.get('matches_on_hotspawn_lol_lobby')} picks</b>
       <span>Filter by market / model / unresolved, or search a team.</span></a>
    <a class="card" href="leagues.html"><b>By league ({len(summary.get('league_counts') or {})})</b>
       <span>One subpage per tournament listed on Hotspawn.</span></a>
    <a class="card" href="unresolved.html"><b>Unresolved picks ({cov.get('unresolved')})</b>
       <span>Which matches have no pick yet and exactly why.</span></a>
    <a class="card" href="flagged.html"><b>Flagged for review ({cov.get('flags')})</b>
       <span>Irregularities and values we could not confirm.</span></a>
    <a class="card" href="methodology.html"><b>How lines are built</b>
       <span>Sources, devig maths, model formula, limitations.</span></a>
  </div>
</section>

<section class="stats">
  <h2>Numbers behind the summary</h2>
  <dl>
    <div><dt>Matches on the LoL lobby</dt><dd>{esc(str(cov.get('matches_on_hotspawn_lol_lobby')))}</dd></div>
    <div><dt>Picks we resolved</dt><dd>{esc(str(cov.get('picks_resolved')))}
        <small>{esc(str(cov.get('coverage_pct')))}% coverage</small></dd></div>
    <div><dt>From betting lines</dt><dd>{esc(str(cov.get('from_market_lines')))}</dd></div>
    <div><dt>From our own model</dt><dd>{esc(str(cov.get('from_our_own_model')))}</dd></div>
    <div><dt>Unresolved</dt><dd>{esc(str(cov.get('unresolved')))}</dd></div>
    <div><dt>Leagues covered</dt><dd>{esc(str(cov.get('leagues')))}</dd></div>
    <div><dt>Teams rated</dt><dd>{esc(str(cov.get('rated_teams')))}</dd></div>
    <div><dt>Verified scorelines used</dt><dd>{esc(str(cov.get('verified_results_used')))}</dd></div>
    <div><dt>Rows flagged</dt><dd>{esc(str(cov.get('flags')))}</dd></div>
    <div><dt>Lobby's own weekly count</dt><dd>{esc(str((cov.get('lobby_reported_totals') or {}).get('matches_this_week')))}
        <small>all titles; LoL tab: {esc(str((cov.get('lobby_reported_totals') or {}).get('tiers_count')))}</small></dd></div>
    <div><dt>Hotspawn fixture feed</dt><dd>{esc(str(cov.get('feed_fixture_count')))} LoL fixtures
        <small>{esc(str(cov.get('feed_upcoming_not_in_lobby')))} upcoming but not on the pick'em
        lobby</small></dd></div>
  </dl>
</section>

<section id="closing">
  <h2>Closing next — pick these first</h2>
  <p class="muted">Sorted by lock time (UTC). <b>PICK</b> is the team we would take and the % is our
  estimated chance that the team wins the series.</p>
  {picks_table(soon[:12], now, "No match is inside the 3-hour closing window right now.")}
  <p><a class="more" href="picks.html">All picks →</a></p>
</section>

<section id="from-lines">
  <h2>Picks priced from external betting lines</h2>
  <p class="muted">De-vigged from Polymarket prices or sportsbook odds-comparison pages
  ({esc(str((summary.get('sources') or {}).get('oddsportal_rows')))} comparison rows and
  {esc(str((summary.get('sources') or {}).get('polymarket_markets')))} market rows collected this run).</p>
  {picks_table(market_rows[:20], now, "No external market covered these matches in this window.")}
  <p><a class="more" href="picks.html?basis=market">Show all market-priced picks →</a></p>
</section>

<section id="from-model">
  <h2>Picks we originate ourselves</h2>
  <p class="muted">Low-tier fixtures with no published price. Confidence band reflects how many
  verified finished series both teams have. Distribution of confidence this run:
  {esc(", ".join(f"{k}: {v}" for k, v in (summary.get('model_confidence') or {}).items()) or "n/a")}.</p>
  {picks_table(model_rows[:20], now, "No model-only picks in this window.")}
  <p><a class="more" href="picks.html?basis=model">Show all model-originated picks →</a></p>
</section>

<section id="unresolved-summary" class="warnbox">
  <h2>Unresolved picks &amp; limitations</h2>
  <p><b>{cov.get('unresolved')}</b> of {cov.get('matches_on_hotspawn_lol_lobby')} matches
  ({round(100 * (cov.get('unresolved') or 0) / max(1, cov.get('matches_on_hotspawn_lol_lobby') or 1), 1)}%)
  have no probability yet. Full list with per-match reasons:
  <a href="unresolved.html">Unresolved picks →</a>.</p>
  {lim_html}
  {picks_table(unres_rows[:6], now, "")}
</section>

<section id="flags-summary">
  <h2>Flagged irregularities (top of list)</h2>
  <p class="muted">Everything here is published in full on
  <a href="flagged.html">Flagged for review</a>. Flags never block publishing; they mark values we
  could not confirm from an official source, which are left blank in the tables.</p>
  <table class="mini"><thead><tr><th>match</th><th>field</th><th>reason</th></tr></thead>
  <tbody>{top_flags or '<tr><td colspan="3">No flags this run.</td></tr>'}</tbody></table>
</section>

<section>
  <h2>Tiers and leagues in this window</h2>
  <p>{tiers_html}</p>
  <ul class="leaguelist">{leagues_html}</ul>
</section>
"""
    return layout(rel, f"Executive summary — {SITE_TITLE}", body, updated=iso(now), summary=summary, active="index.html")


def page_picks(site: str, data: dict, now) -> str:
    summary = data["summary"]
    cov = summary["headline"]
    picks = sorted(data["picks"], key=lambda r: (r.get("kickoff_utc") or "9999"))
    body = f"""
<section class="pagehead">
  <h1>All picks — {len(picks)} matches</h1>
  <p class="muted">One card per Hotspawn LoL pick'em, ordered by lock time (UTC). The team with the
  larger % is the pick. Under <b>sources &amp; verification</b> each row links to the official
  Hotspawn pages plus the betting-line page or the scorelines behind our model line.</p>
  <p class="chips">
    <span class="chip chip-ok">{cov.get('from_market_lines')} market-priced</span>
    <span class="chip chip-self">{cov.get('from_our_own_model')} self-originated</span>
    <span class="chip chip-warn">{cov.get('unresolved')} unresolved</span>
    <a class="chip chip-link" href="unresolved.html">unresolved + why →</a>
    <a class="chip chip-link" href="flagged.html">flags ({cov.get('flags')}) →</a>
    <a class="chip chip-link" href="data.html">CSV / JSON →</a>
  </p>
</section>
{FILTERS}
<div id="list" class="list">{picks_table(picks, now, "No picks in this snapshot yet.")}</div>
<p class="count"><span id="shown">{len(picks)}</span> of {len(picks)} shown ·
<a href="index.html">← executive summary</a></p>
"""
    return layout("", "All picks — " + SITE_TITLE, body, updated=iso(now), summary=summary, active="picks.html")


def page_leagues(site: str, data: dict, now) -> str:
    summary = data["summary"]
    items = sorted((summary.get("league_counts") or {}).items(), key=lambda kv: -kv[1])
    lis = "".join(
        f'<li><a href="leagues/{slugify(name)}.html">{esc(name)}</a> <span class="muted">{n} picks</span></li>'
        for name, n in items)
    body = f"""
<section class="pagehead">
  <h1>Leagues ({len(items)})</h1>
  <p class="muted">Subpages by category — one per tournament currently listed on the Hotspawn LoL
  pick'em lobby. Each page repeats the same table restricted to that league.</p>
</section>
<ul class="leaguelist">{lis or '<li>none</li>'}</ul>
"""
    return layout("", "Leagues — " + SITE_TITLE, body, updated=iso(now), summary=summary, active="leagues.html")


def page_generic_picks(site: str, data: dict, now, title: str, rows: list[dict], intro: str) -> str:
    summary = data["summary"]
    body = f"""
<section class="pagehead">
  <h1>{esc(title)}</h1>
  <p class="muted">{intro}</p>
  <p><a class="chip chip-link" href="../picks.html">← all picks</a>
     <a class="chip chip-link" href="../leagues.html">all leagues</a></p>
</section>
{FILTERS if title.startswith("Tier") else ""}
<div id="list" class="list">{picks_table(rows, now, "Nothing in this category right now.")}</div>
"""
    return layout("../", title + " — " + SITE_TITLE, body, updated=iso(now), summary=summary,
                active="leagues.html")


def page_unresolved(site: str, data: dict, now) -> str:
    summary = data["summary"]
    unres = data["unresolved"]
    cov = summary["headline"]
    rows = [p for p in data["picks"] if p.get("basis") == "unresolved"]
    items = unres.get("items") or []
    lis = "".join(
        f'<tr><td>{esc(i.get("kickoff_utc") or "TBD")}</td><td>{esc(i.get("match"))}</td>'
        f'<td>{esc(i.get("tournament"))}</td><td>{esc(i.get("tier") or "—")}</td>'
        f'<td>{esc(i.get("reason"))}</td>'
        f'<td>{"yes" if i.get("model_available") else "no"} / '
        f'{"yes" if i.get("market_available") else "no"}</td>'
        f'<td><a href="{esc(i.get("hotspawn_url"))}" target="_blank" rel="noopener nofollow">match page</a></td></tr>'
        for i in items)
    lim_blocks = []
    for l in (unres.get("limitations") or []):
        parts = [f'<div class="limit"><h3>{esc(l.get("title"))}</h3><p>{esc(l.get("detail"))}</p>']
        if l.get("affected_rows") is not None:
            parts.append(f'<p class="muted">rows affected in this snapshot: '
                         f'{esc(str(l.get("affected_rows")))}</p>')
        for lg in (l.get("leagues") or [])[:40]:
            parts.append(f'<p class="muted">league with too little sample: <code>{esc(lg)}</code></p>')
        if l.get("sources"):
            src_rows = []
            for src in l["sources"]:
                url = esc(src.get("url") or "")
                src_rows.append('<tr><td><a href="' + url + '" target="_blank" rel="noopener nofollow">'
                                + esc(src.get("label")) + '</a></td><td>' + esc(src.get("result"))
                                + '</td></tr>')
            parts.append('<table class="mini"><thead><tr><th>source attempted</th>'
                         '<th>what it returned</th></tr></thead><tbody>' + "".join(src_rows)
                         + '</tbody></table>')
        parts.append("</div>")
        lim_blocks.append("".join(parts))
    lim = "".join(lim_blocks)
    body = f"""
<section class="pagehead">
  <h1>Unresolved picks — {len(items)}</h1>
  <p class="muted">Matches Hotspawn lists for which we could not produce a defensible probability in
  this snapshot. These are <b>not</b> hidden: the table is blank on purpose, and the reason is
  recorded per match together with the source that was missing. This section is summarised on the
  <a href="index.html#unresolved-summary">executive summary</a>.</p>
  <p class="chips"><span class="chip chip-warn">{cov.get('unresolved')} unresolved</span>
     <span class="chip">{cov.get('matches_on_hotspawn_lol_lobby')} listed on the lobby</span></p>
</section>
<h2>Why each one is open</h2>
<table class="rows"><thead><tr><th>kickoff (UTC)</th><th>match</th><th>league</th><th>tier</th>
<th>reason</th><th>model / market seen?</th><th>source</th></tr></thead>
<tbody>{lis or '<tr><td colspan="7">Nothing unresolved — every listed match has a pick.</td></tr>'}</tbody></table>
<h2>The cards themselves</h2>
<div class="list">{picks_table(rows, now, "No unresolved cards.")}</div>
<h2>Limitations of this method</h2>
{lim}
"""
    return layout("", "Unresolved picks — " + SITE_TITLE, body, updated=iso(now), summary=summary, active="unresolved.html")


def page_flagged(site: str, data: dict, now) -> str:
    summary = data["summary"]
    flags = data["flags"]
    items = flags.get("items") or []
    groups = flags.get("groups") or items

    def sample_of(f):
        ids = f.get("fixture_ids") or []
        names = [m for m in (f.get("matches") or []) if m]
        if not ids and not names:
            return ""
        bits = [esc(m) for m in names[:3]]
        if ids:
            bits.append("+" + str(max(0, int(f.get("count") or 1) - 3)) + " more ids: "
                        + esc(", ".join(str(i) for i in ids[:6])))
        return "; ".join(bits)

    def link_of(f):
        url = f.get("source_url")
        if not url:
            return "—"
        return (f'<a href="{esc(url)}" target="_blank" rel="noopener nofollow">source</a>')

    def cell_sample(f):
        txt = sample_of(f)
        if not txt:
            return ""
        return '<div class="muted small">' + txt + "</div>"

    rows = ""
    for f in groups:
        rows += ("<tr><td>" + esc(f.get("field")) + "</td><td>" + esc(f.get("count") or 1)
                 + "</td><td>" + esc(f.get("reason")) + cell_sample(f) + "</td><td>"
                 + link_of(f) + "</td></tr>")
    grouped: dict[str, list] = {}
    for f in items:
        grouped.setdefault(f.get("field") or "other", []).append(f)
    body = f"""
<section class="pagehead">
  <h1>Flagged for review — {len(items)}</h1>
  <p class="muted">Anything we could not confirm against an official source, or where two sources
  disagreed. Values are left blank rather than filled in. Fixing a flag never required a manual
  step: the pipeline re-tests every row on each refresh, so a row disappears from this page once
  the source resolves it.</p>
  <p class="chips">{"".join(f'<span class="chip">{esc(k)}: {len(v)}</span>' for k, v in sorted(grouped.items())) or '<span class="chip chip-ok">no flags</span>'}</p>
</section>
<p class="muted">{esc(str(len(items)))} flag instances collapsed into {esc(str(len(groups)))}
rows, because one blocked source produces one identical flag per match.</p>
<table class="rows"><thead><tr><th>field</th><th>rows</th><th>reason</th><th>source checked</th></tr></thead>
<tbody>{rows or '<tr><td colspan="4">No flags in this snapshot.</td></tr>'}</tbody></table>
<p class="muted">Flags are published, not blocking: the site ships with them. See
<a href="unresolved.html">Unresolved picks</a> for matches with no probability at all.</p>
"""
    return layout("", "Flagged for review — " + SITE_TITLE, body, updated=iso(now), summary=summary, active="flagged.html")


def page_methodology(site: str, data: dict, now) -> str:
    summary = data["summary"]
    ratings = data["ratings"]
    params = ratings.get("params") or {}
    body = f"""
<section class="pagehead"><h1>Methodology, maths and limitations</h1>
<p class="muted">Written by the pipeline, not by hand, so it always matches the code in
<code>scripts/</code>.</p></section>

<h2>1 · What counts as a match</h2>
<p>The list of matches is exactly what Hotspawn offers pick'ems for in the League of Legends tab,
read from the server-rendered lobby <a href="https://play.hotspawn.com/lol-pickems" target="_blank"
rel="noopener nofollow">play.hotspawn.com/lol-pickems</a>. Every id is then re-checked against
Hotspawn's own fixture feed (<a href="https://www.hotspawn.com/wp-json/wp/v2/fixtures"
target="_blank" rel="noopener nofollow">/wp-json/wp/v2/fixtures</a>), and the kickoff is verified
against the <code>HH:MM UTC</code> stamp on the league page
(<code>hotspawn.com/league-of-legends/tournament/&lt;slug&gt;</code>). The lobby only publishes a
relative “Locks in” countdown, so a match whose absolute time cannot be cross-checked is flagged
rather than published as fact.</p>

<h2>2 · Probability from betting lines</h2>
<p>Where an external price exists it is always preferred. Decimal odds are converted to raw implied
probability (1/odds) and the over-round is removed proportionally (multiplicative de-vig) — a two-way
market, since a League of Legends series cannot draw. If two sources price the same fixture their
difference is published as a spread. A price is only attached when both team labels match the fixture;
if a source page contains several fixtures for the same pair the price is <b>not</b> attached and the
row is flagged instead of guessed.</p>

<h2>3 · Our own line (model) for matches nobody prices</h2>
<p>Formula: <code>p = 1 / (1 + 10 ** -(R_a - R_b) / {esc(str(params.get('scale')))})</code> at series
level, with ratings produced from verified finished series scorelines only. Parameters: K = {esc(str(params.get('K')))},
margin-of-victory factor <code>{esc(str(params.get('mv_factor')))}</code>, {esc(str(params.get('passes')))} relaxation
passes, shrinkage weight n₀ = {esc(str(params.get('shrink_n')))} games.
{esc(str(ratings.get('results_used')))} finished series were used; {esc(str(ratings.get('results_skipped')))}
rows were dropped for missing/ambiguous scorelines; {esc(str(len(ratings.get('teams') or {})))} teams carry a rating.</p>
<p>Confidence bands are sample-size driven, not opinion: <i>high</i> ≥ 6 finished series each and a
direct meeting, <i>medium</i> ≥ 6 each, <i>low</i> ≥ 3, <i>very low</i> below that, <i>none</i> when a
team has no verifiable result — in which case the row is unresolved, never imputed.</p>

<h2>4 · Explicitly excluded</h2>
<ul>
<li><b>Hotspawn's "X% picked" is never an input.</b> It is a crowd poll, published on the cards for
comparison only.</li>
<li>No odds are read from Hotspawn itself, and no line is invented for a match with no evidence:
those rows stay blank and appear under <a href="unresolved.html">Unresolved picks</a>.</li>
<li>No manual entry: the same code path runs on the schedule, so the published snapshot is
reproducible from <code>scripts/</code> alone.</li>
</ul>

<h2>5 · Known limitations</h2>
<ol>
<li>Sub-tier LoL is thinly priced: regional 2nd/3rd divisions, academy and high-school leagues and
some emerging-region championships are not on Polymarket and only sporadically on odds-comparison
pages. Books that were probed and could not be read programmatically are listed with the exact
outcome on the <a href="sources.html">sources ledger</a>.</li>
<li>A form model cannot see roster changes, stand-ins, patch swings, veto order or side preference,
which matters most in exactly the leagues where we have to use it.</li>
<li>Ratings are comparable <i>inside</i> a league; cross-league scale relies on shared opponents only
and is not calibrated, so tier-to-tier comparisons should be read as soft.</li>
<li>Hotspawn labels many fixtures “Waiting for Information”; if the fixture is never played the
pick'em simply voids. Kickoff for those rows can move after this snapshot.</li>
<li>The lobby is weekly (resets with Hotspawn's own reset); matches outside the window are not
listed as missing picks.</li>
</ol>

<h2>6 · Reproduce it</h2>
<pre><code>pip install -r requirements.txt
python -m scripts.pipeline --out data
python -m scripts.build_site --data data --site site
python -m scripts.verify --data data --site site</code></pre>
"""
    return layout("", "Methodology — " + SITE_TITLE, body, updated=iso(now), summary=summary, active="methodology.html")


def page_sources(site: str, data: dict, now) -> str:
    summary = data["summary"]
    src = data["sources"]
    hosts = src.get("hosts") or {}
    host_rows = "".join(
        f'<tr><td><code>{esc(h)}</code></td><td>{esc(v.get("attempts"))}</td>'
        f'<td>{esc(v.get("ok"))}</td><td>{esc(v.get("failed"))}</td>'
        f'<td>{esc(v.get("skipped_no_network"))}</td>'
        f'<td>{esc((v.get("errors") or ["—"])[0] or "—")}</td></tr>'
        for h, v in sorted(hosts.items(), key=lambda kv: -kv[1].get("attempts", 0)))
    probe_rows = "".join(
        f'<tr><td><a href="{esc(p.get("url"))}" target="_blank" rel="noopener nofollow">{esc(p.get("label"))}</a></td>'
        f'<td>{esc(p.get("verdict"))}</td><td>{esc(str(p.get("bytes")))}</td></tr>'
        for p in (src.get("probes") or []))
    op = src.get("oddsportal") or {}
    pm = src.get("polymarket") or {}
    pmq = "".join(f'<tr><td>{esc(q.get("query"))}</td><td>{esc(q.get("events"))}</td>'
                  f'<td>{esc(q.get("error") or "ok")}</td>'
                  f'<td><a href="{esc(q.get("url"))}" target="_blank" rel="noopener nofollow">query</a></td></tr>'
                  for q in (pm.get("queries") or []))
    diag_rows = ""
    for r in (data.get("diag") or {}).get("results") or []:
        readable = r.get("outcome") == "ok"
        badge = "badge-ok" if readable else "badge-warn"
        verdict = "readable" if readable else "blocked"
        note = str((r.get("error") or r.get("outcome") or ""))[:70]
        diag_rows += ("<tr><td>" + esc(r.get("label"))
                      + '</td><td><a href="' + esc(r.get("url"))
                      + '" target="_blank" rel="noopener nofollow">' + esc(r.get("host"))
                      + '</a></td><td><span class="badge ' + badge + '">' + verdict
                      + "</span></td><td>" + esc(str(r.get("chars") or "—"))
                      + '</td><td class="mono small">' + esc(note) + "</td></tr>")
    diag_block = ""
    if diag_rows:
        diag_block = (
            '<h2>Endpoint reachability probe</h2><p class="muted">Ran in the same job as this '
            'snapshot (' + esc(str((data.get("diag") or {}).get("generated_at"))) + '). It changes '
            'no number on this site: it records, per endpoint and per client fingerprint, whether a '
            'GitHub runner can read the page at all — the evidence behind every "source blocked" '
            'note in <a href="methodology.html">Methodology</a>.</p>'
            '<table class="mini"><thead><tr><th>endpoint</th><th>host</th><th>result</th>'
            '<th>bytes</th><th>note</th></tr></thead><tbody>' + diag_rows + "</tbody></table>")

    body = f"""
<section class="pagehead"><h1>Source ledger</h1>
<p class="muted">Every host this snapshot fetched, with success/failure counts recorded by the fetcher
itself — so “we looked, it wasn't there” and “we could not look” are distinguishable.</p></section>
<h2>Parsed line sources</h2>
<table class="mini"><tbody>
<tr><td>OddsPortal (LoL odds comparison)</td><td>{esc(str(op.get('status')))}</td>
    <td>{esc(str(op.get('rows')))} rows</td>
    <td><a href="https://www.oddsportal.com/esports/league-of-legends/" target="_blank" rel="noopener nofollow">index</a></td></tr>
<tr><td>Polymarket (public gamma API)</td><td>{esc(str(pm.get('status')))}</td>
    <td>{esc(str(pm.get('markets')))} markets / {esc(str(pm.get('events')))} events</td>
    <td><a href="https://gamma-api.polymarket.com/public-search?q=league%20of%20legends" target="_blank" rel="noopener nofollow">api</a></td></tr>
</tbody></table>
{f'<h3>Polymarket queries</h3><table class="mini"><thead><tr><th>query</th><th>events</th><th>error</th><th>link</th></tr></thead><tbody>{pmq}</tbody></table>' if pmq else ''}
<h2>Per-host fetch ledger</h2>
<table class="mini"><thead><tr><th>host</th><th>attempts</th><th>ok</th><th>failed</th>
<th>no-network</th><th>first error</th></tr></thead><tbody>{host_rows or '<tr><td colspan="6">offline build</td></tr>'}</tbody></table>
{diag_block}
<h2>Esports books / line sources probed but not parsed</h2>
<p class="muted">These are the "established betting site → esports book → betting line" attempts
recorded exactly as they answered. Anything that failed to deliver a parseable LoL odds table is a
documented limitation, not a silent gap.</p>
<table class="mini"><thead><tr><th>source</th><th>verdict</th><th>bytes</th></tr></thead>
<tbody>{probe_rows or '<tr><td colspan="3">probes skipped in this run</td></tr>'}</tbody></table>
"""
    return layout("", "Sources ledger — " + SITE_TITLE, body, updated=iso(now), summary=summary, active="sources.html")


def page_data(site: str, data: dict, now, prefix: str = "") -> str:
    summary = data["summary"]
    files = [("data/picks.json", "one row per pick'em, full detail"),
             ("data/picks.csv", "same table flattened for spreadsheets"),
             ("data/unresolved.json", "unresolved picks + limitations"),
             ("data/flags.json", "flagged irregularities"),
             ("data/ratings.json", "team ratings + model parameters"),
             ("data/sources.json", "fetch ledger"),
             ("data/summary.json", "executive-summary numbers"),
             ("data/hotspawn.json", "raw collection (lobby cards, league fixtures, results)")]
    lis = "".join(
        f'<li><a href="{esc(prefix + href)}">{esc(href.split("/")[-1])}</a> '
        f'<span class="muted">{esc(desc)}</span></li>'
        for href, desc in files)
    body = f"""
<section class="pagehead"><h1>Download the data</h1>
<p class="muted">Machine-readable copies of exactly what this site is rendered from, generated
{esc(iso(now))}. Nothing is hand-edited.</p></section>
<ul class="leaguelist">{lis}</ul>
"""
    return layout("", "Data — " + SITE_TITLE, body, updated=iso(now), summary=summary, active="data.html")


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--site", default=".",
                    help="output root; defaults to the repo root because Pages here builds main:/")
    args = ap.parse_args()

    def load(name, default=None):
        return json.load(open(os.path.join(args.data, name), encoding="utf-8")) \
            if os.path.exists(os.path.join(args.data, name)) else default

    data = {
        "picks": (load("picks.json", {}) or {}).get("picks") or [],
        "unresolved": load("unresolved.json", {"items": [], "limitations": []}) or {"items": [], "limitations": []},
        "flags": load("flags.json", {"items": []}) or {"items": []},
        "ratings": load("ratings.json", {"teams": {}}) or {"teams": {}},
        "sources": load("sources.json", {}) or {},
        "diag": load("diag-probe.json", {}) or {},
        "summary": load("summary.json", {"headline": {}}) or {"headline": {}},
    }
    data["summary"].setdefault("refresh_hours", 6)
    data["summary"].setdefault("headline", {})
    for key, default in [("matches_on_hotspawn_lol_lobby", 0), ("picks_resolved", 0),
                         ("from_market_lines", 0), ("from_our_own_model", 0), ("unresolved", 0),
                         ("flags", 0), ("leagues", 0), ("coverage_pct", 0)]:
        data["summary"]["headline"].setdefault(key, default)
    data["summary"]["generated_at"] = data["summary"].get("generated_at") or iso(utcnow())
    now = parse_iso(data["summary"]["generated_at"]) or utcnow()

    os.makedirs(args.site, exist_ok=True)
    write_text(os.path.join(args.site, ".nojekyll"), "# static site - do not run Jekyll\n")
    os.makedirs(os.path.join(args.site, "assets"), exist_ok=True)

    changed = []
    if write_if_changed(os.path.join(args.site, "index.html"), page_index(args.site, data, now)):
        changed.append("index.html")
    if write_if_changed(os.path.join(args.site, "picks.html"), page_picks(args.site, data, now)):
        changed.append("picks.html")
    if write_if_changed(os.path.join(args.site, "leagues.html"), page_leagues(args.site, data, now)):
        changed.append("leagues.html")
    if write_if_changed(os.path.join(args.site, "unresolved.html"), page_unresolved(args.site, data, now)):
        changed.append("unresolved.html")
    if write_if_changed(os.path.join(args.site, "flagged.html"), page_flagged(args.site, data, now)):
        changed.append("flagged.html")
    if write_if_changed(os.path.join(args.site, "methodology.html"), page_methodology(args.site, data, now)):
        changed.append("methodology.html")
    if write_if_changed(os.path.join(args.site, "sources.html"), page_sources(args.site, data, now)):
        changed.append("sources.html")
    if write_if_changed(os.path.join(args.site, "data.html"), page_data(args.site, data, now)):
        changed.append("data.html")

    # category subpages: leagues + tiers
    counts = {"leagues": 0, "tiers": 0}
    keep = set()
    for group, subdir in (("tournament", "leagues"), ("tier", "tiers")):
        os.makedirs(os.path.join(args.site, subdir), exist_ok=True)
        buckets: dict[str, list] = {}
        for row in data["picks"]:
            buckets.setdefault(str(row.get(group) or "unlabelled"), []).append(row)
        for name, rows in buckets.items():
            fname = f"{slugify(name)}{'-picks' if group == 'tier' else ''}.html"
            keep.add(f"{subdir}/{fname}")
            title = (f"{name} — {len(rows)} picks" if group == "tournament"
                     else f"Tier {name} — {len(rows)} picks")
            intro = (f"Every Hotspawn LoL pick'em in {name} this window, with our probability for "
                     f"both teams and the source of that number.") if group == "tournament" else \
                    (f"Hotspawn labels these matches tier {name}. Tier comes from the lobby listing; "
                     f"it is presentation only and is never used to compute a probability.")
            html = page_generic_picks(os.path.join(args.site, subdir), data, now, title, rows, intro)
            if write_if_changed(os.path.join(args.site, subdir, fname), html):
                changed.append(f"{subdir}/{fname}")
            if group == "tournament":
                counts["leagues"] += 1
            else:
                counts["tiers"] += 1

    # drop stale category pages so no broken links survive a re-shuffle
    for subdir in ("leagues", "tiers"):
        path = os.path.join(args.site, subdir)
        if not os.path.isdir(path):
            continue
        for fname in os.listdir(path):
            if f"{subdir}/{fname}" not in keep:
                os.remove(os.path.join(path, fname))
                print(f"removed stale {subdir}/{fname}")

    for src_name, dst in (("style.css", os.path.join(args.site, "assets", "style.css")),
                          ("app.js", os.path.join(args.site, "assets", "app.js"))):
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", src_name)
        if os.path.exists(src):
            with open(src, encoding="utf-8") as fh:
                content = fh.read()
            if write_if_changed(dst, content):
                changed.append(f"assets/{src_name}")

    # Publish the machine-readable snapshot next to the pages (data/ at the site root).
    out_data = os.path.join(args.site, "data")
    os.makedirs(out_data, exist_ok=True)
    for name in ("picks.json", "picks.csv", "unresolved.json", "flags.json", "ratings.json",
                 "sources.json", "summary.json", "hotspawn.json"):
        src = os.path.join(args.data, name)
        dst = os.path.join(out_data, name)
        if os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
            shutil.copyfile(src, dst)
    print(f"site built: {len(changed)} file(s) written; {counts['leagues']} league pages, "
          f"{counts['tiers']} tier pages; {len(data['picks'])} picks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
