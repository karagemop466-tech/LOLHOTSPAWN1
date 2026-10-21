"""Render the mobile-first GitHub Pages dashboard from data/*.json.

Pages produced (repo root, so GitHub Pages serves them directly):
  index.html        executive summary + in-site links + next picks
  picks.html        every priced match (pick + probability + source links)
  unresolved.html   matches with no external market + the limitation for each
  tournaments.html  coverage per competition
  methodology.html  how probabilities are produced, cadence, limitations
  sources.html      every data source actually queried this run
  flagged.html      irregularities / items for human review
  assets/style.css, assets/app.js, data/*.json
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


# Sources that were checked while building this pipeline (2026-10-21) and did not
# yield a usable, linkable price feed from a GitHub Actions runner. Kept here so the
# "we looked" evidence is published alongside the picks.
CHECKED_NO_FEED = [
    ("1xBet", "sportsbook",
     "Public LineFeed returns an HTML interstitial (bot/geo gate) instead of prices.",
     "https://1xbet.com/en/line/esports"),
    ("Betano", "sportsbook", "HTTP 403 from the runner IP.", "https://www.betano.de/esports/"),
    ("Marathonbet", "sportsbook", "HTTP 403 from the runner IP.", "https://www.marathonbet.com/en/betting/Esports/"),
    ("GG.Bet", "sportsbook",
     "HTTP 403 — site refuses visitors from the runner region.",
     "https://www.gg.bet/en/league-of-legends"),
    ("Oddspedia", "odds aggregator", "HTTP 403/410 on the public match-list endpoints.",
     "https://oddspedia.com/esports/league-of-legends"),
    ("BetExplorer", "odds aggregator", "No League of Legends esports section served (HTTP 404).",
     "https://www.betexplorer.com/esports/"),
    ("bo3.gg", "esports data", "API reachable, but it exposes no odds endpoint and ignores league filters.",
     "https://bo3.gg/lol/matches"),
    ("Prime League (official ERL site)", "league site", "HTTP 403 from the runner IP.",
     "https://www.primeleague.gg/en/leagues/prm/26-27/fall/3rd-division"),
    ("Leaguepedia (Fandom API)", "results", "Rate-limited from the runner IP (HTTP 200 + ratelimited payload).",
     "https://lol.fandom.com/wiki/Special:CargoTables"),
    ("Liquipedia API", "results",
     "Reachable, but it exposes wiki pages rather than a structured results feed for the amateur divisions.",
     "https://liquipedia.net/leagueoflegends/"),
    ("OddsPortal", "odds aggregator",
     "Reachable (HTTP 200) but no public API; scraping was not implemented, so it contributes no price.",
     "https://www.oddsportal.com/esports/league-of-legends/"),
]


NAV = [
    ("index.html", "Summary"),
    ("picks.html", "Picks"),
    ("unresolved.html", "Unresolved"),
    ("tournaments.html", "Leagues"),
    ("methodology.html", "Method"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged"),
]


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def esc(v):
    return html.escape(str(v)) if v is not None else ""


def fmt_time(iso_ts):
    if not iso_ts:
        return "TBD"
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return esc(iso_ts)
    return dt.strftime("%a %d %b %H:%M UTC")


def bar(p, side="team1"):
    width = max(2.0, min(100.0, 100.0 * p))
    cls = "bar-fill" if side == "team1" else "bar-fill alt"
    return f'<div class="bar"><span class="{cls}" style="width:{width:.1f}%"></span></div>'


def layout(title, body, meta, active=""):
    nav = "".join(
        f'<a class="nav-link{" active" if href == active else ""}" href="{href}">{label}</a>'
        for href, label in NAV)
    generated = meta.get("generated_at", "")
    gen_display = fmt_time(generated)
    counts = meta.get("counts", {})
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · LoL Pick'em Board</title>
<meta name="description" content="League of Legends picks and win probabilities for every match in the Hotspawn Play pick'em lobby, built from external bookmaker and prediction-market prices.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="topbar">
  <div class="wrap topbar-inner">
    <a class="brand" href="index.html">
      <span class="brand-mark">LoL</span>
      <span class="brand-text">Pick'em Board<small>Hotspawn lobby coverage</small></span>
    </a>
    <div class="stamp" title="Data collection timestamp">
      <span class="dot"></span>Updated {esc(gen_display)}
    </div>
  </div>
  <nav class="wrap nav">{nav}</nav>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap footer">
  <p><strong>{counts.get("matches", 0)}</strong> matches tracked ·
     <strong>{counts.get("resolved", 0)}</strong> priced ·
     <strong>{counts.get("unresolved", 0)}</strong> unresolved ·
     refreshed every 4 hours from GitHub Actions.</p>
  <p class="muted">Probabilities are derived from external bookmaker prices and prediction markets.
     Match list comes from Hotspawn Play. Crowd pick percentages are shown for context only and are
     never used in any probability. Betting involves risk; this is research, not advice.</p>
</footer>
<script src="assets/app.js"></script>
</body>
</html>
"""


def pick_card(m, compact=False):
    p = m["pick"]
    t1, t2 = m["team1"], m["team2"]
    p1 = m["prob_team1"]
    p2 = m["prob_team2"]
    fav_first = p["side"] == "team1"
    left_name = t1["name"] if fav_first else t2["name"]
    left_p = p1 if fav_first else p2
    right_name = t2["name"] if fav_first else t1["name"]
    right_p = p2 if fav_first else p1
    srcs = "".join(
        f'<a class="src" href="{esc(q["url"])}" target="_blank" rel="noopener">{esc(q["book"])}'
        f' <span class="src-odds">{q["decimal_team1"]:.2f} / {q["decimal_team2"]:.2f}</span></a>'
        for q in m["quotes"])
    hs = (f'<a class="ghost" href="{esc(m["hotspawn_url"])}" target="_blank" rel="noopener">Hotspawn match</a>'
          if m.get("hotspawn_url") else "")
    edge = abs(0.5 - left_p)
    return f"""
<article class="card pick" data-teams="{esc(t1["name"])} {esc(t2["name"])}"
  data-league="{esc(m["tournament"])}" data-prob="{left_p:.4f}" data-edge="{edge:.4f}"
  data-time="{esc(m["start_utc"] or "")}">
  <div class="card-head">
    <div>
      <h3>{esc(left_name)} <span class="vs">vs</span> {esc(right_name)}</h3>
      <p class="meta">{esc(m["tournament"])} · Tier {esc(m["tier"].upper() if m["tier"] else "—")} · <span data-utc="{esc(m["start_utc"] or "")}">{esc(fmt_time(m["start_utc"]))}</span></p>
    </div>
    <span class="pill conf-{esc(p["confidence"])}">{esc(p["confidence"].title())} confidence</span>
  </div>
  <div class="probs">
    <div class="prob-row">
      <span class="team">{esc(t1["name"])}</span>
      <span class="num">{p1 * 100:.1f}%</span>
    </div>
    {bar(p1, "team1")}
    <div class="prob-row">
      <span class="team">{esc(t2["name"])}</span>
      <span class="num">{p2 * 100:.1f}%</span>
    </div>
    {bar(p2, "alt")}
  </div>
  <div class="pickline">
    <span class="label">Pick</span>
    <strong>{esc(p["team"])}</strong>
    <span class="pill pickpill">{p["probability_display"]}</span>
    <span class="muted small">{esc(len(m["quotes"]))} source{'s' if len(m["quotes"]) != 1 else ''}</span>
  </div>
  <div class="sources">{srcs}{hs}</div>
</article>"""


def unresolved_row(m):
    return f"""
<article class="card unresolved">
  <div class="card-head">
    <div>
      <h3>{esc(m["team1"]["name"])} <span class="vs">vs</span> {esc(m["team2"]["name"])}</h3>
      <p class="meta">{esc(m["tournament"])} · Tier {esc(m["tier"].upper() if m["tier"] else "—")} · {esc(fmt_time(m["start_utc"]))}</p>
    </div>
    <span class="pill no">No external market</span>
  </div>
  <p class="reason">No sportsbook or prediction market queried lists this match, so no probability is published.
     We do not substitute Hotspawn crowd percentages or an invented number.</p>
  <div class="sources">
    <a class="ghost" href="{esc(m["hotspawn_url"])}" target="_blank" rel="noopener">Hotspawn match</a>
    <a class="ghost" href="sources.html">Sources checked</a>
  </div>
</article>"""


def page_index(matches, meta, tournaments):
    counts = meta["counts"]
    resolved = [m for m in matches if m["status"] == "resolved"]
    upcoming = resolved[:8]
    top = sorted(resolved, key=lambda m: -m["pick"]["probability"])[:5]
    cards = "".join(pick_card(m) for m in upcoming) or '<p class="muted">No priced matches in this snapshot.</p>'
    strongest = "".join(
        f'<li><a href="picks.html"><strong>{esc(m["pick"]["team"])}</strong></a> '
        f'<span class="muted">over {esc(m["team2"]["name"] if m["pick"]["side"]=="team1" else m["team1"]["name"])}'
        f' · {m["pick"]["probability_display"]} · {esc(m["tournament"])}</span></li>'
        for m in top)
    coverage = [t for t in tournaments if t["matches"]]
    priced_leagues = [t for t in coverage if t["resolved"]]
    league_rows = "".join(
        f'<tr><td>{esc(t["tournament"])}</td><td class="num">{t["matches"]}</td>'
        f'<td class="num">{t["resolved"]}</td><td class="num">{t["unresolved"]}</td></tr>'
        for t in coverage[:12])
    return f"""
<section class="hero">
  <h1>Every LoL pick'em match, one board</h1>
  <p class="lede">We mirror the full League of Legends list in the Hotspawn Play pick'em lobby, then price each
  match from <strong>external</strong> bookmaker and prediction-market data. Where no market exists we say so
  instead of guessing.</p>
  <div class="statgrid">
    <a class="stat" href="picks.html"><span class="n">{counts["resolved"]}</span><span class="l">Priced picks</span></a>
    <a class="stat" href="unresolved.html"><span class="n">{counts["unresolved"]}</span><span class="l">Unresolved</span></a>
    <a class="stat" href="tournaments.html"><span class="n">{counts["tournaments"]}</span><span class="l">Leagues</span></a>
    <a class="stat" href="picks.html"><span class="n">{counts["matches"]}</span><span class="l">Matches tracked</span></a>
  </div>
  <div class="cta">
    <a class="btn primary" href="picks.html">See all picks →</a>
    <a class="btn" href="unresolved.html">Why some have no pick</a>
  </div>
</section>

<section class="panel">
  <h2>Executive summary</h2>
  <ul class="summary-list">
    <li><strong>Coverage.</strong> {counts["matches"]} matches across {counts["tournaments"]} competitions are listed in the
      Hotspawn LoL pick'em lobby right now. The full list, refreshed from the lobby every 4 hours, is on
      <a href="picks.html">Picks</a> and <a href="unresolved.html">Unresolved</a>.</li>
    <li><strong>Priced matches.</strong> {counts["resolved"]} matches have a verifiable external market
      ({", ".join(esc(s["book"]) for s in meta["sources"] if s["status"] == "ok") or "no source available this run"}).
      Each pick shows the probability, the books used, the raw decimal odds and a link to the source.</li>
    <li><strong>Unresolved matches.</strong> {counts["unresolved"]} matches have no external market at all — mostly
      amateur and semi-pro leagues (e.g. PRM 3rd Division, Tunisian Super League, Icelandic league). They are listed
      with their limitation on <a href="unresolved.html">Unresolved</a>; no number is invented for them.</li>
    <li><strong>Not used as an input.</strong> Hotspawn's crowd pick percentages and Hotspawn's own picks never enter a
      probability. Only external sportsbook prices and prediction-market prices do.</li>
    <li><strong>Method &amp; audit.</strong> De-vigging, source blending and matching rules are documented on
      <a href="methodology.html">Method</a>; per-source status is on <a href="sources.html">Sources</a>; open
      irregularities are on <a href="flagged.html">Flagged</a>.</li>
  </ul>
</section>

<section class="panel">
  <h2>Next picks</h2>
  <p class="muted">Soonest kickoff first. All times UTC.</p>
  {cards}
</section>

<section class="panel">
  <h2>Strongest external-market leans</h2>
  <ul class="ranked">{strongest or '<li class="muted">None yet.</li>'}</ul>
</section>

<section class="panel">
  <h2>Where the picks live</h2>
  <p>Every list in this dashboard is one tap away from the menu at the top of the page.</p>
  <div class="linkgrid">
    <a class="linkcard" href="picks.html"><strong>Picks</strong><span>Pick + win probability for each priced match</span></a>
    <a class="linkcard" href="unresolved.html"><strong>Unresolved</strong><span>Matches with no external market + why</span></a>
    <a class="linkcard" href="tournaments.html"><strong>Leagues</strong><span>Coverage per competition</span></a>
    <a class="linkcard" href="methodology.html"><strong>Method</strong><span>How each probability is produced</span></a>
    <a class="linkcard" href="sources.html"><strong>Sources</strong><span>What was queried, with links</span></a>
    <a class="linkcard" href="flagged.html"><strong>Flagged</strong><span>Irregularities for review</span></a>
  </div>
</section>

<section class="panel">
  <h2>League coverage</h2>
  <p class="muted">{len(priced_leagues)} of {len(coverage)} competitions currently have at least one externally priced match.</p>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Competition</th><th class="num">Matches</th><th class="num">Priced</th><th class="num">Unresolved</th></tr></thead>
      <tbody>{league_rows}</tbody>
    </table>
  </div>
  <p class="muted small"><a href="tournaments.html">Full coverage table →</a></p>
</section>
"""


def page_picks(matches, meta, tournaments):
    resolved = [m for m in matches if m["status"] == "resolved"]
    cards = "".join(pick_card(m) for m in resolved)
    options = "".join(
        f'<option value="{esc(t["tournament"])}">{esc(t["tournament"])} ({t["resolved"]}/{t["matches"]})</option>'
        for t in sorted(tournaments, key=lambda x: x["tournament"] or ""))
    return f"""
<section class="panel">
  <h1>Picks ({len(resolved)})</h1>
  <p class="lede">Every match that has a verifiable external market. Probability is de-vigged from the
  bookmaker or prediction-market prices listed on each card.</p>
  <div class="controls">
    <input id="search" type="search" placeholder="Filter by team or league…" aria-label="Filter picks">
    <select id="league"><option value="">All competitions</option>{options}</select>
    <select id="sort">
      <option value="time">Soonest kickoff</option>
      <option value="prob">Highest probability</option>
      <option value="edge">Closest to 50/50</option>
    </select>
  </div>
  <div id="picklist" class="cardlist">{cards or '<p class="muted">No priced matches in this snapshot.</p>'}</div>
</section>
"""


def page_unresolved(matches, meta, tournaments):
    un = [m for m in matches if m["status"] == "unresolved"]
    by_league = {}
    for m in un:
        by_league.setdefault(m["tournament"], []).append(m)
    groups = []
    for league, rows in sorted(by_league.items(), key=lambda kv: (-len(kv[1]), kv[0] or "")):
        tier = rows[0]["tier"]
        groups.append(f"""
<section class="panel">
  <h2>{esc(league)} <span class="pill tier">{esc(tier.upper() if tier else "—")} tier</span>
    <span class="muted small">{len(rows)} match{'es' if len(rows) != 1 else ''} without an external market</span></h2>
  <div class="cardlist">{''.join(unresolved_row(m) for m in rows)}</div>
</section>""")
    return f"""
<section class="panel">
  <h1>Unresolved picks ({len(un)})</h1>
  <p class="lede">These matches are on Hotspawn's LoL board but no external market prices them. We list them
  explicitly rather than filling the gap with a guess.</p>
  <h2>Limitations</h2>
  <ul class="summary-list">
    <li><strong>No listed market.</strong> Priced coverage comes from Bovada, Pinnacle and Polymarket. In this run
      those books published {meta["counts"]["resolved"]} League of Legends series markets in total, all in the
      tier-1/tier-2 competitions. Regional third divisions, national leagues and academy splits are not offered.</li>
    <li><strong>Community/prediction markets are thin.</strong> Polymarket only lists LoL series it expects volume on;
      a match with no order book gives no usable price.</li>
    <li><strong>Why we don't fall back to Hotspawn.</strong> The Hotspawn lobby shows a crowd pick percentage. That is a
      popularity poll, not a price, and the brief excludes it. Publishing it as a probability would be misleading.</li>
    <li><strong>What would resolve them.</strong> A verified bookmaker line (any regulated sportsbook or esports book),
      a liquid prediction market, or an official league results feed strong enough to originate a line. When one of
      these appears, the match moves to <a href="picks.html">Picks</a> automatically on the next refresh.</li>
  </ul>
</section>
{''.join(groups)}
"""


def page_tournaments(matches, meta, tournaments):
    rows = "".join(
        f'<tr><td>{esc(t["tournament"])}</td><td><span class="pill tier">{esc((t["tier"] or "—").upper())}</span></td>'
        f'<td class="num">{t["matches"]}</td><td class="num">{t["resolved"]}</td>'
        f'<td class="num">{t["unresolved"]}</td>'
        f'<td class="num">{100 * t["resolved"] / max(1, t["matches"]):.0f}%</td></tr>'
        for t in tournaments)
    return f"""
<section class="panel">
  <h1>League coverage</h1>
  <p class="lede">How many matches each competition contributes to the Hotspawn LoL lobby, and how many we can
  price from external markets.</p>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Competition</th><th>Tier</th><th class="num">Matches</th><th class="num">Priced</th>
      <th class="num">Unresolved</th><th class="num">Priced %</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</section>
"""


def page_methodology(meta):
    return f"""
<section class="panel prose">
  <h1>Methodology</h1>
  <h2>1. Match universe (Hotspawn)</h2>
  <p><code>https://play.hotspawn.com/lol-pickems</code> is an Angular SSR page. Its hydrated state is embedded in
  <code>&lt;script id="ng-state"&gt;</code>; the collector reads the match list from that JSON. We take
  <em>only</em> the fixtures: id, teams, competition, tier, kickoff, points. Crowd percentages are stored for
  display and are excluded from every calculation.</p>

  <h2>2. External prices</h2>
  <p>Three sources are queried on every refresh:</p>
  <ul>
    <li><strong>Bovada</strong> — public pre-match coupon for League of Legends, Head-to-Head moneyline, full series.</li>
    <li><strong>Pinnacle</strong> — guest API, sport 12 (E Sports) filtered to League of Legends leagues, full-series moneyline.</li>
    <li><strong>Polymarket</strong> — Gamma API, <code>league-of-legends</code> tag, open series markets. The traded price is used directly.</li>
  </ul>
  <p>Each two-way price is converted to implied probability (<code>1/decimal</code>) and de-vigged proportionally:
  <code>p = implied / (implied_a + implied_b)</code>. Multiple sources are combined with the median, which is robust
  to a single stale or mispriced book. The published probability is the median for the favourite; dispersion
  (max − min across sources) sets confidence: ≤5pp high, ≤12pp medium, otherwise low.</p>

  <h2>3. Matching</h2>
  <p>Team names are normalised (case, accents, punctuation, and generic suffixes such as “Esports”, “Gaming”,
  “Team”). A pair matches when both sides match exactly or one name contains the other (e.g. “LYON” /
  “Lyon Gaming”). Name variants are flagged on the review page. Kickoff timestamps must agree within 48 hours
  when both sides have one.</p>

  <h2>4. When nothing is listed</h2>
  <p>No price means no probability. The match is published on <a href="unresolved.html">Unresolved</a> with the
  reason. We do not fall back to Hotspawn crowd data, and we do not interpolate a number to fill the table.</p>

  <h2>5. Freshness</h2>
  <p>A GitHub Actions workflow runs every 4 hours (<code>17 */4 * * *</code> UTC), refetches both the lobby and the
  markets, rebuilds these pages and commits them. The timestamp in the header is the generation time of the
  snapshot you are reading. Hotspawn adds matches continuously, so a match that appears after a run will show up
  on the next one (within 4 hours).</p>

  <h2>6. Known limits</h2>
  <ul>
    <li>Books publish lines close to kickoff. Early in a day the priced-match count is lower.</li>
    <li>Polymarket prices are last-trade/mid prices, not bookmaker lines; they are labelled per card.</li>
    <li>Pinnacle’s guest API is undocumented and may change; the Sources page shows its live status each run.</li>
    <li>No model-driven probabilities are published. Any number shown is traceable to a linked external price.</li>
  </ul>

  <h2>7. Data files</h2>
  <p>Every page is generated from the JSON in <a href="data/matches.json">data/matches.json</a>,
  <a href="data/unresolved.json">data/unresolved.json</a>, <a href="data/quotes.json">data/quotes.json</a> and
  <a href="data/sources.json">data/sources.json</a>. Snapshot generated {esc(meta["generated_at"])}.</p>
</section>
"""


def page_sources(meta):
    checked = "".join(
        f'<tr><td><a href="{esc(url)}" target="_blank" rel="noopener">{esc(name)}</a></td>'
        f'<td>{esc(kind)}</td><td class="small">{esc(note)}</td></tr>'
        for name, kind, note, url in CHECKED_NO_FEED)
    rows = []
    for s in meta["sources"]:
        cls = {"ok": "good", "empty": "warn"}.get(s["status"], "bad")
        rows.append(f"""<tr>
  <td><a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["book"])}</a></td>
  <td>{esc(s["kind"].replace("_", " "))}</td>
  <td><span class="pill {cls}">{esc(s["status"])}</span></td>
  <td class="num">{s["quotes"]}</td>
  <td class="small">{esc(s.get("error") or "")}</td>
</tr>""")
    return f"""
<section class="panel">
  <h1>Sources</h1>
  <p class="lede">Live status of every endpoint queried in the snapshot generated {esc(meta["generated_at"])}.</p>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Source</th><th>Type</th><th>Status</th><th class="num">Quotes</th><th>Notes</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
  <h2>Fixture source</h2>
  <p><a href="{esc(meta["hotspawn_source"])}" target="_blank" rel="noopener">Hotspawn Play — League of Legends lobby</a>
  (match list only; retrieved {esc(meta["hotspawn_retrieved_at"])}).</p>
  <h2>Checked, no usable public feed</h2>
  <p class="lede">Books and data services that were tested while building this pipeline. None of them gave a
  linkable, machine-readable price feed from this environment, so none of them contribute a number. They are
  listed so you can see the search was broader than the three working sources.</p>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Source</th><th>Type</th><th>Result</th></tr></thead>
      <tbody>{checked}</tbody>
    </table>
  </div>
  <h2>What we deliberately do not use</h2>
  <ul>
    <li>Hotspawn crowd pick percentages (popularity, not a price).</li>
    <li>Hotspawn editorial predictions.</li>
    <li>Any unlinked or reconstructed number.</li>
  </ul>
</section>
"""


def page_flagged(matches, meta):
    variants = [m for m in matches if m["status"] == "resolved"
                and any(q["name_match"] == "variant" for q in m["quotes"])]
    high_disp = [m for m in matches if m["status"] == "resolved"
                 and m["pick"]["dispersion"] > 0.12]
    single = [m for m in matches if m["status"] == "resolved" and len(m["quotes"]) == 1]
    missing_url = [m for m in matches if not m["hotspawn_url"]]

    def block(title, items, describe):
        if not items:
            return f'<h2>{title}</h2><p class="muted">None in this snapshot.</p>'
        lis = "".join(
            f'<li>{describe(m)}</li>' for m in items[:40])
        more = (f'<p class="muted small">Showing {min(40, len(items))} of {len(items)}.</p>'
                if len(items) > 40 else "")
        return f'<h2>{title} ({len(items)})</h2><ul class="summary-list">{lis}</ul>{more}'

    v_html = block("Team-name variants across sources", variants,
                   lambda m: f'{esc(m["team1"]["name"])} vs {esc(m["team2"]["name"])} — '
                             f'{esc(m["tournament"])}; '
                             + ", ".join(f'<a href="{esc(q["url"])}" target="_blank" rel="noopener">{esc(q["book"])}'
                                         f' (“{esc(q["home"])} / {esc(q["away"])}”)</a>' for q in m["quotes"]
                                         if q["name_match"] == "variant"))
    d_html = block("Sources disagree by more than 12 points", high_disp,
                   lambda m: f'{esc(m["team1"]["name"])} vs {esc(m["team2"]["name"])} — '
                             f'dispersion {m["pick"]["dispersion"]*100:.1f}pp across '
                             f'{len(m["quotes"])} sources')
    s_html = block("Priced by a single source", single,
                   lambda m: f'{esc(m["team1"]["name"])} vs {esc(m["team2"]["name"])} — '
                             f'only {esc(m["quotes"][0]["book"])} lists it '
                             f'({m["pick"]["probability_display"]} {esc(m["pick"]["team"])})')
    u_html = block("No public Hotspawn match page link in the lobby payload", missing_url,
                   lambda m: f'{esc(m["team1"]["name"])} vs {esc(m["team2"]["name"])} — '
                             f'{esc(m["tournament"])}')
    return f"""
<section class="panel">
  <h1>Flagged for review</h1>
  <p class="lede">Everything the pipeline could not resolve cleanly. None of these are hidden from the picks
  tables; they are listed here so a human can check them.</p>
  {v_html}
  {d_html}
  {s_html}
  {u_html}
  <h2>Standing limitations</h2>
  <ul class="summary-list">
    <li>{meta["counts"]["unresolved"]} matches have no external market anywhere we can query — see
      <a href="unresolved.html">Unresolved</a>.</li>
    <li>Pinnacle's guest endpoint is undocumented; if it changes, the run reports <code>error</code> on
      <a href="sources.html">Sources</a> and the affected picks lose one source rather than silently keeping stale prices.</li>
    <li>Polymarket prices are prediction-market mid/last prices, not bookmaker lines.</li>
  </ul>
</section>
"""


def main():
    matches = load("matches.json")["matches"]
    meta = load("meta.json")
    tournaments = load("tournaments.json")

    pages = {
        "index.html": ("Executive summary", page_index(matches, meta, tournaments), "index.html"),
        "picks.html": ("Picks", page_picks(matches, meta, tournaments), "picks.html"),
        "unresolved.html": ("Unresolved", page_unresolved(matches, meta, tournaments), "unresolved.html"),
        "tournaments.html": ("League coverage", page_tournaments(matches, meta, tournaments), "tournaments.html"),
        "methodology.html": ("Methodology", page_methodology(meta), "methodology.html"),
        "sources.html": ("Sources", page_sources(meta), "sources.html"),
        "flagged.html": ("Flagged for review", page_flagged(matches, meta), "flagged.html"),
    }
    for name, (title, body, active) in pages.items():
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
            f.write(layout(title, body, meta, active))
    with open(os.path.join(ROOT, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")
    print("wrote", ", ".join(pages))


if __name__ == "__main__":
    main()
