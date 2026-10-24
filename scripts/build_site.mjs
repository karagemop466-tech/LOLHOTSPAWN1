#!/usr/bin/env node
/**
 * build_site.mjs — Stage 3 of the LoL Hotspawn pick'em Node pipeline (docs/).
 *
 * Renders the 10-page mobile-first companion dashboard under docs/:
 *   index.html        Executive summary, KPIs, navigation hub & unresolved summary
 *   table.html        Compact filterable table of all 241 scheduled LoL matches
 *   picks.html        All active picked match cards (market + model)
 *   featured.html     Multi-venue market-consensus series & per-venue de-vig table
 *   originated.html   Self-originated pre-kickoff Elo/Bradley-Terry picks
 *   tournaments.html  Per-competition breakdown across all 29 active tournaments
 *   unresolved.html   Unresolved picks, walkover settlements & structural limitations
 *   flagged.html      Flagged for Review (homonyms, DQ walkovers, unverified items)
 *   results.html      Pre-lock prediction ledger & official ended/forfeited results
 *   methodology.html  Equations, 22,372-series walk-forward SVG calibration & venue audit
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DATA = path.join(ROOT, "data", "node");
const DOCS = path.join(ROOT, "docs");
const REPO_URL = "https://github.com/karagemop466-tech/LOLHOTSPAWN1";
const CANON_LIVE_URL = "https://karagemop466-tech.github.io/LOLHOTSPAWN1/";

function esc(v) {
  if (v == null) return "";
  return String(v)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function pct1(p) {
  if (p == null || !Number.isFinite(p)) return "—";
  return `${(p * 100).toFixed(1)}%`;
}

function fmtUtc(iso) {
  if (!iso) return "TBD";
  return iso.slice(0, 16).replace("T", " ") + " UTC";
}

function methodShort(m) {
  if (m.settlement_pick) return "walkover";
  if (m.market_consensus) return "market";
  if (m.source_category === "model") return "model";
  if (m.source_category === "model_provisional") return "provisional";
  return "unresolved";
}

function methodBadge(m) {
  if (m.settlement_pick) {
    return `<span class="badge b-unres">Walkover DQ Settlement</span>`;
  }
  if (m.market_consensus) {
    const vc = m.market_consensus.venue_count;
    return `<span class="badge b-market">Market (${vc} ${vc === 1 ? "venue" : "venues"})</span>`;
  }
  if (m.source_category === "model") {
    return `<span class="badge b-model">Model Elo</span>`;
  }
  if (m.source_category === "model_provisional") {
    return `<span class="badge b-prov">Provisional Elo</span>`;
  }
  return `<span class="badge b-unres">Unresolved</span>`;
}

function stateBadge(state) {
  const label = state === "stale" ? "stale (>6h)" : state;
  return `<span class="badge b-state">${esc(label)}</span>`;
}

/* ---------------------------------------------------------- Shared Shell */

function renderShell({ activePage, title, description, summary, bodyHtml }) {
  const c = summary.counts;
  const navItems = [
    { href: "index.html", label: "Overview", cnt: null },
    { href: "table.html", label: "All 241 Table", cnt: c.scheduled_total },
    { href: "picks.html", label: "Active Picks", cnt: c.active_market + c.active_model },
    { href: "featured.html", label: "Market Lines", cnt: c.scheduled_market },
    { href: "originated.html", label: "Model Picks", cnt: c.scheduled_model },
    { href: "tournaments.html", label: "Tournaments", cnt: null },
    { href: "unresolved.html", label: "Unresolved", cnt: c.active_unresolved + c.scheduled_walkover_settlement },
    { href: "flagged.html", label: "Flagged", cnt: c.flags },
    { href: "results.html", label: "Results", cnt: null },
    { href: "methodology.html", label: "Methodology", cnt: null },
  ];

  const navLinks = navItems
    .map((it) => {
      const cls = it.href === activePage ? ' class="active" aria-current="page"' : "";
      const cnt = it.cnt != null ? `<span class="nav-cnt">${it.cnt}</span>` : "";
      return `<a href="${it.href}"${cls}><span>${esc(it.label)}</span>${cnt}</a>`;
    })
    .join("");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${esc(title)} — LoL Hotspawn Pick'em Companion Audit</title>
  <meta name="description" content="${esc(description)}">
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="index.html">
        <span class="brand-dot" aria-hidden="true"></span>
        <span>Hotspawn LoL Pick'ems · Audit Suite</span>
      </a>
      <button id="nav-toggle" class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">
        Menu ▾
      </button>
      <nav id="site-nav" class="site-nav" aria-label="Primary navigation">
        ${navLinks}
      </nav>
    </div>
  </header>
  <div id="stale-snapshot-alert" class="stale-alert" hidden></div>
  <div class="fresh-bar" data-generated-at="${esc(summary.generated_at)}">
    <div class="fresh-inner">
      <span>Snapshot: <time class="mono" data-utc="${esc(summary.generated_at)}">${esc(fmtUtc(summary.generated_at))}</time> · Auto-refresh every 6h</span>
      <span>Zero Hotspawn crowd/tier/points inputs · <a href="${CANON_LIVE_URL}">Canonical Root Dashboard ↗</a> · <a href="data/picks.csv">CSV</a> · <a href="data/picks.json">JSON</a></span>
    </div>
  </div>
  <main>
${bodyHtml}
  </main>
  <footer class="site-footer">
    <div class="footer-inner">
      <span>Independent quantitative companion for <a href="https://play.hotspawn.com/lol-pickems">Hotspawn LoL Pick'ems</a>.</span>
      <span><a href="unresolved.html">Unresolved &amp; Limitations</a> · <a href="flagged.html">Flagged for Review</a> · <a href="methodology.html">Methodology &amp; Calibration</a> · <a href="${REPO_URL}">GitHub Source</a></span>
    </div>
  </footer>
  <script src="assets/app.js"></script>
</body>
</html>
`;
}

/* ---------------------------------------------------------- Match Card UI */

function renderSourceLinks(m) {
  const links = [`<a class="src-link" href="${esc(m.hotspawn_url)}" target="_blank" rel="noopener">Hotspawn #${esc(m.id)} ↗</a>`];
  if (m.market_pinnacle?.url) {
    links.push(`<a class="src-link" href="${esc(m.market_pinnacle.url)}" target="_blank" rel="noopener">Pinnacle ↗</a>`);
  }
  if (m.market_kambi?.url) {
    links.push(`<a class="src-link" href="${esc(m.market_kambi.url)}" target="_blank" rel="noopener">Unibet/Kambi ↗</a>`);
  }
  if (m.market_kalshi?.url) {
    links.push(`<a class="src-link" href="${esc(m.market_kalshi.url)}" target="_blank" rel="noopener">Kalshi CFTC ↗</a>`);
  }
  if (m.market_polymarket?.url) {
    links.push(`<a class="src-link" href="${esc(m.market_polymarket.url)}" target="_blank" rel="noopener">Polymarket ↗</a>`);
  }
  if (m.market_bovada?.url) {
    links.push(`<a class="src-link" href="${esc(m.market_bovada.url)}" target="_blank" rel="noopener">Bovada ↗</a>`);
  }
  if (m.settlement_pick?.source_url) {
    links.push(`<a class="src-link" href="${esc(m.settlement_pick.source_url)}" target="_blank" rel="noopener">Official DQ Ledger ↗</a>`);
  } else if (m.leaguepedia_url) {
    links.push(`<a class="src-link" href="${esc(m.leaguepedia_url)}" target="_blank" rel="noopener">Leaguepedia ↗</a>`);
  }
  return links.join("");
}

function renderPickedCard(m, idPrefix = "m-") {
  // Exact 1-decimal complementary display so p0_str + p1_str === 100.0%
  const p0Num = m.p0;
  const p0Disp = pct1(p0Num);
  const p1Disp = pct1(1 - p0Num);
  const w0 = Math.round(p0Num * 100);
  const w1 = 100 - w0;
  const winIdx = m.pick.team_index;

  let metaDetail = "";
  if (m.market_consensus) {
    const vParts = m.market_consensus.venues.map((v) => {
      const oddsStr = v.dec0 && v.dec1 ? ` (${v.dec0.toFixed(2)}/${v.dec1.toFixed(2)})` : "";
      return `${esc(v.venue_label)}${oddsStr}`;
    });
    metaDetail = `De-vigged consensus across ${vParts.join(" + ")} · spread ${m.market_consensus.spread_pp.toFixed(1)} pp.`;
  } else if (m.model) {
    metaDetail = `Pre-kickoff Elo ${m.model.elo0.toFixed(0)} (${m.model.n0} series) vs ${m.model.elo1.toFixed(0)} (${m.model.n1} series) · Bo${m.best_of}.`;
  }

  const staleAttr = m.state === "stale" ? "1" : "0";
  const searchStr = `${m.id} ${m.competition_name} ${m.team0.name} ${m.team1.name} ${m.team0.canonical_name} ${m.team1.canonical_name}`;

  return `<article class="card" id="${idPrefix}${esc(m.id)}" data-item="1" data-method="${methodShort(m)}" data-comp="${esc(m.competition_name)}" data-stale="${staleAttr}" data-search="${esc(searchStr)}">
    <div class="card-top">
      <span class="card-comp">${esc(m.competition_name)} · Bo${m.best_of}</span>
      <span>${methodBadge(m)} ${stateBadge(m.state)}</span>
    </div>
    <div class="card-top">
      <time class="mono" data-utc="${esc(m.start_iso || "")}">${esc(fmtUtc(m.start_iso))}</time>
      <span class="mono">#${esc(m.id)}</span>
    </div>
    <div class="team-rows">
      <div class="team-row${winIdx === 0 ? " is-pick" : ""}">
        <span class="team-name-wrap">
          <span class="team-name">${esc(m.team0.name)}</span>
          ${winIdx === 0 ? '<span class="badge b-pick">★ PICK</span>' : ""}
        </span>
        <span class="team-prob">${p0Disp}</span>
      </div>
      <div class="team-row${winIdx === 1 ? " is-pick" : ""}">
        <span class="team-name-wrap">
          <span class="team-name">${esc(m.team1.name)}</span>
          ${winIdx === 1 ? '<span class="badge b-pick">★ PICK</span>' : ""}
        </span>
        <span class="team-prob">${p1Disp}</span>
      </div>
    </div>
    <div class="prob-bar" aria-hidden="true">
      <div class="${winIdx === 0 ? "prob-seg-win" : "prob-seg0"}" style="width:${w0}%"></div>
      <div class="${winIdx === 1 ? "prob-seg-win" : "prob-seg1"}" style="width:${w1}%"></div>
    </div>
    <div class="card-meta">${metaDetail}</div>
    <div class="card-links">${renderSourceLinks(m)}</div>
  </article>`;
}

function renderUnresolvedCard(m, idPrefix = "m-") {
  const settleNote = m.settlement_pick
    ? `<div><span class="badge b-pick">Walkover Settlement → ${esc(m.settlement_pick.team_name)}</span></div>`
    : `<div><span class="badge b-unres">No Sporting Pick — Left Blank (Unverified / 0 Prior Matches)</span></div>`;

  return `<article class="card unres-card" id="${idPrefix}${esc(m.id)}">
    <div class="card-top">
      <span class="card-comp">${esc(m.competition_name)} · Bo${m.best_of}</span>
      <span>${methodBadge(m)} ${stateBadge(m.state)}</span>
    </div>
    <div class="card-top">
      <time class="mono" data-utc="${esc(m.start_iso || "")}">${esc(fmtUtc(m.start_iso))}</time>
      <span class="mono">#${esc(m.id)}</span>
    </div>
    <div class="team-rows">
      <div class="team-row${m.settlement_pick?.team_index === 0 ? " is-pick" : ""}">
        <span class="team-name">${esc(m.team0.name)}</span>
        <span class="team-prob">—</span>
      </div>
      <div class="team-row${m.settlement_pick?.team_index === 1 ? " is-pick" : ""}">
        <span class="team-name">${esc(m.team1.name)}</span>
        <span class="team-prob">—</span>
      </div>
    </div>
    ${settleNote}
    <div class="card-meta">${esc(m.unresolved_reason || "Insufficient pre-kickoff evidence.")}</div>
    <div class="card-links">${renderSourceLinks(m)}</div>
  </article>`;
}

/* ---------------------------------------------------------- Page Builders */

function buildIndexPage(picks, flags) {
  const s = picks.summary;
  const c = s.counts;
  const scheduled = picks.matches.filter((m) => m.status === "scheduled");
  const mktRows = scheduled.filter((m) => m.market_consensus != null);
  const activeUnres = scheduled.filter((m) => (m.state === "open" || m.state === "locked" || m.state === "live") && !m.pick);
  const dqWalkovers = scheduled.filter((m) => m.settlement_pick != null);

  const mktPreview = mktRows.map((m) => renderPickedCard(m, "idx-m-")).join("\n");
  const unresPreview = activeUnres.length
    ? activeUnres.map((m) => renderUnresolvedCard(m, "idx-u-")).join("\n")
    : `<div class="empty-state">Zero items this run. ✓</div>`;

  const bodyHtml = `
    <section class="page-hero">
      <h1>Executive Summary — Hotspawn League of Legends Pick'ems</h1>
      <p>Complete line-by-line coverage of all <strong>${c.scheduled_total}</strong> listed Hotspawn LoL matches across <strong>29</strong> competitions. Probabilities come exclusively from de-vigged real-money bookmaker &amp; CFTC/CLOB prediction markets (${c.scheduled_market} series across up to 4 independent venues) and strictly pre-kickoff Leaguepedia + Hotspawn Elo/Bradley-Terry ratings (${c.scheduled_model} series). Hotspawn crowd percentages, tiers, and offered points are never used as probability inputs.</p>
    </section>

    <section class="kpi-grid" aria-label="Coverage metrics">
      <div class="kpi">
        <div class="kpi-val">${c.scheduled_total}</div>
        <div class="kpi-lbl">Scheduled LoL Inventory</div>
        <div class="kpi-sub">${c.active_open_locked} active · ${c.stale_scheduled} stale (&gt;6h)</div>
      </div>
      <div class="kpi">
        <div class="kpi-val">${c.scheduled_market}</div>
        <div class="kpi-lbl">Market-Consensus Picks</div>
        <div class="kpi-sub">Pinnacle · Unibet · Kalshi · Polymarket</div>
      </div>
      <div class="kpi">
        <div class="kpi-val">${c.scheduled_model}</div>
        <div class="kpi-lbl">Originated Model Picks</div>
        <div class="kpi-sub">Pre-kickoff Leaguepedia Elo</div>
      </div>
      <div class="kpi">
        <div class="kpi-val">${c.active_unresolved}</div>
        <div class="kpi-lbl">Active Unresolved</div>
        <div class="kpi-sub">+ ${c.scheduled_walkover_settlement} DQ walkovers · ${c.scheduled_unresolved - c.active_unresolved} stale debut</div>
      </div>
      <div class="kpi">
        <div class="kpi-val">${s.calibration.brier?.toFixed(4) ?? "—"}</div>
        <div class="kpi-lbl">Walk-Forward OOS Brier</div>
        <div class="kpi-sub">${s.calibration.oos_evaluated.toLocaleString()} pre-kickoff series (vs 0.2500)</div>
      </div>
      <div class="kpi">
        <div class="kpi-val">${c.flags}</div>
        <div class="kpi-lbl">Flagged for Review</div>
        <div class="kpi-sub">Homonyms, DQs &amp; zero-history</div>
      </div>
    </section>

    <div class="sec-head">
      <h2>Where to Find Updated Picks &amp; Audits</h2>
      <span>Organized by source category &amp; mobile workflow</span>
    </div>
    <section class="hub-grid">
      <a class="hub-card" href="table.html">
        <div class="hub-title">Compact All-241 Picks Table →</div>
        <div class="hub-desc">Single-screen sortable/filterable table of every scheduled match with win %, pick badge, CSV export, and source links.</div>
      </a>
      <a class="hub-card" href="picks.html">
        <div class="hub-title">All Active Picks (${c.active_market + c.active_model}) →</div>
        <div class="hub-desc">Card view for every open/locked match with a verified probability, split bar, and venue/Elo provenance.</div>
      </a>
      <a class="hub-card" href="featured.html">
        <div class="hub-title">Market-Backed Picks (${c.scheduled_market}) →</div>
        <div class="hub-desc">Worlds 2026 Swiss Round 2 (4 venues) + LGC Rising Playoffs (Kalshi CFTC + Polymarket) side-by-side de-vig matrix.</div>
      </a>
      <a class="hub-card" href="originated.html">
        <div class="hub-title">Self-Originated Model (${c.scheduled_model}) →</div>
        <div class="hub-desc">ERL 2nd/3rd-division, LCP 2027 Promotion (#1081423), CELOL, Arabian &amp; Nordic matches priced via pre-kickoff Elo.</div>
      </a>
      <a class="hub-card" href="tournaments.html">
        <div class="hub-title">By Tournament (29) →</div>
        <div class="hub-desc">Per-competition match tables, coverage counts, and direct Leaguepedia tournament links.</div>
      </a>
      <a class="hub-card" href="unresolved.html">
        <div class="hub-title">Unresolved &amp; Limitations (${c.active_unresolved + c.scheduled_walkover_settlement}) →</div>
        <div class="hub-desc">Zero-history amateur debuts left blank (never guessed), Solid Gaming DQ walkover settlements, and feed limitations.</div>
      </a>
      <a class="hub-card" href="flagged.html">
        <div class="hub-title">Flagged for Review (${c.flags}) →</div>
        <div class="hub-desc">Cross-region homonym quarantines (#1083097 PNG vs paiN Gaming; #1079031 PvB), DQs, and multi-roster org pooling.</div>
      </a>
      <a class="hub-card" href="results.html">
        <div class="hub-title">Results &amp; Methodology →</div>
        <div class="hub-desc">Pre-lock prediction ledger, official Hotspawn scores, and <span class="mono">methodology.html</span> calibration curves.</div>
      </a>
    </section>

    <div class="sec-head">
      <h2>Multi-Venue Market Consensus Picks (${mktRows.length})</h2>
      <a href="featured.html">Full per-venue odds comparison →</a>
    </div>
    <section class="cards-grid">
      ${mktPreview}
    </section>

    <div class="sec-head" id="unresolved-summary">
      <h2>Unresolved Picks &amp; Limitations Summary</h2>
      <a href="unresolved.html">Open full Unresolved &amp; Limitations page →</a>
    </div>
    <div class="callout warn">
      <h3>Strict Non-Fabrication Policy</h3>
      <p>Whenever at least one team has <strong>0 prior official matches</strong> in both Leaguepedia and Hotspawn prior to kickoff and no external sportsbook or CFTC/CLOB line exists, win probabilities are left blank (<code>—</code>) rather than filled with arbitrary priors. Currently: <strong>${activeUnres.length}</strong> active amateur qualifier fixtures (<a href="unresolved.html">Logitech G SuperStrike Cup Qualifier</a>, including <code>#1083097</code> where Hotspawn mis-bound Bulgarian amateur <code>PNG</code> to Brazilian CBLOL <code>paiN Gaming</code>), <strong>${dqWalkovers.length}</strong> administrative walkover settlements (<a href="unresolved.html#walkover-settlements">Solid Gaming mid-split removal</a> in Komplettligaen 2026 Autumn), and <strong>${c.scheduled_unresolved - activeUnres.length}</strong> stale past-kickoff debut cards. All irregularities are documented with official receipts on <a href="flagged.html">Flagged for Review</a>.</p>
    </div>
    <section class="cards-grid">
      ${unresPreview}
    </section>
  `;

  return renderShell({
    activePage: "index.html",
    title: "Executive Summary",
    description: "Mobile-first quantitative LoL pick'em companion dashboard for Hotspawn with multi-venue market consensus and pre-kickoff Elo ratings.",
    summary: s,
    bodyHtml,
  });
}

function buildTablePage(picks) {
  const s = picks.summary;
  const scheduled = picks.matches.filter((m) => m.status === "scheduled");
  const comps = [...new Set(scheduled.map((m) => m.competition_name))].sort();
  const compOpts = comps.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");

  const rowsHtml = scheduled
    .map((m) => {
      const p0Disp = m.p0 != null ? pct1(m.p0) : "—";
      const p1Disp = m.p0 != null ? pct1(1 - m.p0) : "—";
      let pickCell = `<span class="badge b-unres">— Unverified</span>`;
      if (m.pick) {
        pickCell = `<span class="badge b-pick">★ ${esc(m.pick.team_name)} (${pct1(m.pick.probability)})</span>`;
      } else if (m.settlement_pick) {
        pickCell = `<span class="badge b-prov">Walkover → ${esc(m.settlement_pick.team_name)}</span>`;
      }
      const staleAttr = m.state === "stale" ? "1" : "0";
      const searchStr = `${m.id} ${m.competition_name} ${m.team0.name} ${m.team1.name} ${m.pick?.team_name || ""}`;
      return `<tr id="row-${esc(m.id)}" data-item="1" data-method="${methodShort(m)}" data-comp="${esc(m.competition_name)}" data-stale="${staleAttr}" data-search="${esc(searchStr)}">
        <td data-label="Start" class="mono"><time data-utc="${esc(m.start_iso || "")}">${esc(fmtUtc(m.start_iso))}</time><br>${stateBadge(m.state)}</td>
        <td data-label="Tournament">${esc(m.competition_name)} <span class="mono">(Bo${m.best_of})</span></td>
        <td data-label="Team A"><strong>${esc(m.team0.name)}</strong></td>
        <td data-label="Win % A" class="num">${p0Disp}</td>
        <td data-label="Team B"><strong>${esc(m.team1.name)}</strong></td>
        <td data-label="Win % B" class="num">${p1Disp}</td>
        <td data-label="Pick">${pickCell}</td>
        <td data-label="Basis">${methodBadge(m)}</td>
        <td data-label="Sources"><div class="card-links" style="border:0;padding:0">${renderSourceLinks(m)}</div></td>
      </tr>`;
    })
    .join("\n");

  const bodyHtml = `
    <section class="page-hero">
      <h1>Complete Scheduled LoL Picks Table (${scheduled.length})</h1>
      <p>Every scheduled fixture in the Hotspawn LoL feed, line by line, with win probabilities, explicit pick badge, blank unverified cells where pre-kickoff evidence is absent, and clickable official source receipts.</p>
    </section>

    <div class="toolbar">
      <div class="toolbar-row">
        <input id="q" class="input-search" type="search" placeholder="Search team, tournament, or match ID…" aria-label="Search matches">
        <select id="comp" class="select-comp" aria-label="Filter by tournament">
          <option value="">All 29 tournaments (${scheduled.length})</option>
          ${compOpts}
        </select>
        <button id="upcoming-btn" class="pill-btn" type="button" aria-pressed="false">Hide stale (&gt;6h past start)</button>
      </div>
      <div class="toolbar-row">
        <button class="pill-btn active" type="button" data-method-filter="">All (${scheduled.length})</button>
        <button class="pill-btn" type="button" data-method-filter="market">Market (${s.counts.scheduled_market})</button>
        <button class="pill-btn" type="button" data-method-filter="model">Established Elo (${s.counts.by_source_scheduled.model || 0})</button>
        <button class="pill-btn" type="button" data-method-filter="provisional">Provisional Elo (${s.counts.by_source_scheduled.model_provisional || 0})</button>
        <button class="pill-btn" type="button" data-method-filter="walkover">Walkover DQ (${s.counts.scheduled_walkover_settlement})</button>
        <button class="pill-btn" type="button" data-method-filter="unresolved">Unresolved (${s.counts.scheduled_unresolved})</button>
        <span id="visible-count" class="toolbar-count">${scheduled.length} / ${scheduled.length} shown</span>
      </div>
    </div>

    <div class="table-wrap">
      <table class="data-table mobile-cards">
        <thead>
          <tr>
            <th>Kickoff (UTC)</th>
            <th>Tournament</th>
            <th>Team A</th>
            <th class="num">P(A)</th>
            <th>Team B</th>
            <th class="num">P(B)</th>
            <th>Recommended Pick</th>
            <th>Source Tier</th>
            <th>Official Receipts</th>
          </tr>
        </thead>
        <tbody id="filter-list">
          ${rowsHtml}
        </tbody>
      </table>
    </div>
    <div id="empty-state" class="empty-state" hidden>No matches match the current filter criteria.</div>
  `;

  return renderShell({
    activePage: "table.html",
    title: "All 241 Picks Table",
    description: "Compact sortable and filterable table of all 241 scheduled Hotspawn League of Legends matches.",
    summary: s,
    bodyHtml,
  });
}

function buildPicksPage(picks) {
  const s = picks.summary;
  const activePicked = picks.matches.filter(
    (m) => (m.state === "open" || m.state === "locked" || m.state === "live") && m.pick != null
  );
  const comps = [...new Set(activePicked.map((m) => m.competition_name))].sort();
  const compOpts = comps.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");

  const cardsHtml = activePicked.map((m) => renderPickedCard(m, "m-")).join("\n");

  const bodyHtml = `
    <section class="page-hero">
      <h1>Active LoL Picks (${activePicked.length})</h1>
      <p>Every open or recently locked Hotspawn LoL match carrying a verified probability pair. Active zero-evidence amateur debuts (${s.counts.active_unresolved}) are isolated on <a href="unresolved.html">Unresolved Picks</a> rather than guessed; stale cards (&gt;6h past scheduled start) remain accessible on <a href="table.html">All 241 Table</a>.</p>
    </section>

    <div class="toolbar">
      <div class="toolbar-row">
        <input id="q" class="input-search" type="search" placeholder="Search team, tournament, or match ID…" aria-label="Search active picks">
        <select id="comp" class="select-comp" aria-label="Filter by tournament">
          <option value="">All active tournaments (${comps.length})</option>
          ${compOpts}
        </select>
      </div>
      <div class="toolbar-row">
        <button class="pill-btn active" type="button" data-method-filter="">All Picked (${activePicked.length})</button>
        <button class="pill-btn" type="button" data-method-filter="market">Market Consensus (${s.counts.active_market})</button>
        <button class="pill-btn" type="button" data-method-filter="model">Established Elo (${s.counts.by_source_active.model || 0})</button>
        <button class="pill-btn" type="button" data-method-filter="provisional">Provisional Elo (${s.counts.by_source_active.model_provisional || 0})</button>
        <span id="visible-count" class="toolbar-count">${activePicked.length} / ${activePicked.length} shown</span>
      </div>
    </div>

    <section id="filter-list" class="cards-grid">
      ${cardsHtml}
    </section>
    <div id="empty-state" class="empty-state" hidden>No active picks match your search filter.</div>
  `;

  return renderShell({
    activePage: "picks.html",
    title: "Active Picks",
    description: "Card view of all active Hotspawn LoL matches with market-consensus and pre-kickoff Elo win probabilities.",
    summary: s,
    bodyHtml,
  });
}

function buildFeaturedPage(picks) {
  const s = picks.summary;
  const mktRows = picks.matches.filter((m) => m.status === "scheduled" && m.market_consensus != null);

  const matrixRows = mktRows
    .map((m) => {
      const pin = m.market_pinnacle ? `${pct1(m.market_pinnacle.p0)} / ${pct1(m.market_pinnacle.p1)}` : "—";
      const kam = m.market_kambi ? `${pct1(m.market_kambi.p0)} / ${pct1(m.market_kambi.p1)}` : "—";
      const bov = m.market_bovada ? `${pct1(m.market_bovada.p0)} / ${pct1(m.market_bovada.p1)}` : "—";
      const kal = m.market_kalshi ? `${pct1(m.market_kalshi.p0)} / ${pct1(m.market_kalshi.p1)}` : "—";
      const pol = m.market_polymarket ? `${pct1(m.market_polymarket.p0)} / ${pct1(m.market_polymarket.p1)}` : "—";
      return `<tr>
        <td class="mono">${esc(fmtUtc(m.start_iso))}</td>
        <td><strong>${esc(m.team0.name)}</strong> vs <strong>${esc(m.team1.name)}</strong><br><span class="mono" style="color:var(--text-dim)">${esc(m.competition_name)} · Bo${m.best_of}</span></td>
        <td class="num">${pin}</td>
        <td class="num">${kam}</td>
        <td class="num">${bov}</td>
        <td class="num">${kal}</td>
        <td class="num">${pol}</td>
        <td class="num"><strong>${pct1(m.p0)} / ${pct1(1 - m.p0)}</strong></td>
        <td><span class="badge b-pick">★ ${esc(m.pick.team_name)}</span></td>
        <td><div class="card-links" style="border:0;padding:0">${renderSourceLinks(m)}</div></td>
      </tr>`;
    })
    .join("\n");

  const cardsHtml = mktRows.map((m) => renderPickedCard(m, "feat-")).join("\n");

  const bodyHtml = `
    <section class="page-hero">
      <h1>Multi-Venue Market Consensus Picks (${mktRows.length})</h1>
      <p>Real-money bookmaker moneylines (Pinnacle &amp; Unibet/Kambi, de-vigged via Shin power method; <code>(Kills)</code> derivatives excluded) combined with regulated CFTC binary event contracts (Kalshi <code>KXLOLGAME</code>) and Polymarket CLOB orderbooks.</p>
    </section>

    <div class="sec-head">
      <h2>Side-by-Side De-Vigged Implied Win Probabilities (Team A / Team B)</h2>
      <span>Weights: Pinnacle 1.00 · Unibet/Kambi 0.70 · Kalshi CFTC 0.40–0.55 · Polymarket 0.25–0.65</span>
    </div>
    <div class="table-wrap" style="margin-bottom:1.5rem">
      <table class="data-table">
        <thead>
          <tr>
            <th>Kickoff (UTC)</th>
            <th>Series</th>
            <th class="num">Pinnacle</th>
            <th class="num">Unibet/Kambi</th>
            <th class="num">Bovada</th>
            <th class="num">Kalshi CFTC</th>
            <th class="num">Polymarket</th>
            <th class="num">Consensus</th>
            <th>Pick</th>
            <th>Receipts</th>
          </tr>
        </thead>
        <tbody>
          ${matrixRows}
        </tbody>
      </table>
    </div>

    <div class="sec-head">
      <h2>Market Cards</h2>
    </div>
    <section class="cards-grid">
      ${cardsHtml}
    </section>
  `;

  return renderShell({
    activePage: "featured.html",
    title: "Market-Backed Consensus Picks",
    description: "Multi-venue sportsbook and CFTC/CLOB prediction-market consensus for Hotspawn LoL matches.",
    summary: s,
    bodyHtml,
  });
}

function buildOriginatedPage(picks) {
  const s = picks.summary;
  const origRows = picks.matches.filter(
    (m) => m.status === "scheduled" && m.market_consensus == null && m.pick != null
  );
  const comps = [...new Set(origRows.map((m) => m.competition_name))].sort();
  const compOpts = comps.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  const cardsHtml = origRows.map((m) => renderPickedCard(m, "orig-")).join("\n");

  const bodyHtml = `
    <section class="page-hero">
      <h1>Self-Originated LoL Model Picks (${origRows.length})</h1>
      <p>Low-tier European Regional League (ERL 2nd/3rd division), LCP 2027 Promotion (<code>#1081423 Ground Zero Gaming vs Frank Esports</code>), Brazilian LigaGG CELOL, Nordic, and MENA matches lacking sportsbook moneylines. Priced strictly from pre-kickoff Leaguepedia + Hotspawn series records using empirical-Bayes shrunk Elo/Bradley-Terry ratings.</p>
    </section>

    <div class="toolbar">
      <div class="toolbar-row">
        <input id="q" class="input-search" type="search" placeholder="Search team, tournament, or match ID…" aria-label="Search originated picks">
        <select id="comp" class="select-comp" aria-label="Filter by tournament">
          <option value="">All model-priced tournaments (${comps.length})</option>
          ${compOpts}
        </select>
        <button id="upcoming-btn" class="pill-btn" type="button" aria-pressed="false">Hide stale (&gt;6h past start)</button>
      </div>
      <div class="toolbar-row">
        <button class="pill-btn active" type="button" data-method-filter="">All Model (${origRows.length})</button>
        <button class="pill-btn" type="button" data-method-filter="model">Established (≥5 series/side)</button>
        <button class="pill-btn" type="button" data-method-filter="provisional">Provisional (1–4 series/side)</button>
        <span id="visible-count" class="toolbar-count">${origRows.length} / ${origRows.length} shown</span>
      </div>
    </div>

    <section id="filter-list" class="cards-grid">
      ${cardsHtml}
    </section>
    <div id="empty-state" class="empty-state" hidden>No originated model picks match your filter.</div>
  `;

  return renderShell({
    activePage: "originated.html",
    title: "Self-Originated Model Picks",
    description: "Pre-kickoff Leaguepedia Elo/Bradley-Terry probabilities for low-tier Hotspawn LoL matches without betting lines.",
    summary: s,
    bodyHtml,
  });
}

function buildTournamentsPage(picks) {
  const s = picks.summary;
  const scheduled = picks.matches.filter((m) => m.status === "scheduled");
  const byComp = new Map();
  for (const m of scheduled) {
    if (!byComp.has(m.competition_name)) byComp.set(m.competition_name, []);
    byComp.get(m.competition_name).push(m);
  }
  const sortedComps = [...byComp.entries()].sort((a, b) => a[0].localeCompare(b[0]));

  const summaryRows = sortedComps
    .map(([comp, list], idx) => {
      const mkt = list.filter((m) => m.market_consensus != null).length;
      const mod = list.filter((m) => m.market_consensus == null && m.pick != null).length;
      const dq = list.filter((m) => m.settlement_pick != null).length;
      const unr = list.filter((m) => m.pick == null && m.settlement_pick == null).length;
      const lpUrl = list[0].leaguepedia_url;
      return `<tr>
        <td><a href="#comp-${idx}"><strong>${esc(comp)}</strong></a></td>
        <td class="num">${list.length}</td>
        <td class="num">${mkt}</td>
        <td class="num">${mod}</td>
        <td class="num">${dq}</td>
        <td class="num">${unr}</td>
        <td><a class="src-link" href="${esc(lpUrl)}" target="_blank" rel="noopener">Leaguepedia ↗</a></td>
      </tr>`;
    })
    .join("\n");

  const sectionsHtml = sortedComps
    .map(([comp, list], idx) => {
      const rows = list
        .map((m) => {
          const pDisp = m.p0 != null ? `${pct1(m.p0)} / ${pct1(1 - m.p0)}` : "— / —";
          const pickTxt = m.pick
            ? `<span class="badge b-pick">★ ${esc(m.pick.team_name)}</span>`
            : m.settlement_pick
            ? `<span class="badge b-prov">Walkover → ${esc(m.settlement_pick.team_name)}</span>`
            : `<span class="badge b-unres">— Unresolved</span>`;
          return `<tr>
            <td class="mono">${esc(fmtUtc(m.start_iso))} ${stateBadge(m.state)}</td>
            <td><strong>${esc(m.team0.name)}</strong> vs <strong>${esc(m.team1.name)}</strong> (Bo${m.best_of})</td>
            <td class="num">${pDisp}</td>
            <td>${pickTxt}</td>
            <td>${methodBadge(m)}</td>
            <td><div class="card-links" style="border:0;padding:0">${renderSourceLinks(m)}</div></td>
          </tr>`;
        })
        .join("\n");

      return `<section id="comp-${idx}">
        <div class="sec-head">
          <h2>${esc(comp)} (${list.length})</h2>
          <a class="src-link" href="${esc(list[0].leaguepedia_url)}" target="_blank" rel="noopener">Official Leaguepedia Wiki ↗</a>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Kickoff (UTC)</th>
                <th>Matchup</th>
                <th class="num">Win % (A / B)</th>
                <th>Pick</th>
                <th>Basis</th>
                <th>Sources</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </section>`;
    })
    .join("\n");

  const bodyHtml = `
    <section class="page-hero">
      <h1>Coverage by Tournament (${sortedComps.length} Active Competitions)</h1>
      <p>Breakdown of all ${scheduled.length} scheduled Hotspawn LoL matches across every Tier-1, ERL, Promotion, Academy, LATAM, and MENA competition.</p>
    </section>

    <div class="table-wrap" style="margin-bottom:1.75rem">
      <table class="data-table">
        <thead>
          <tr>
            <th>Competition</th>
            <th class="num">Scheduled</th>
            <th class="num">Market</th>
            <th class="num">Model</th>
            <th class="num">DQ Walkover</th>
            <th class="num">Unresolved</th>
            <th>Reference</th>
          </tr>
        </thead>
        <tbody>${summaryRows}</tbody>
      </table>
    </div>

    ${sectionsHtml}
  `;

  return renderShell({
    activePage: "tournaments.html",
    title: "Tournaments",
    description: "Per-tournament coverage matrix and match picks across all 29 active Hotspawn LoL competitions.",
    summary: s,
    bodyHtml,
  });
}

function buildUnresolvedPage(picks) {
  const s = picks.summary;
  const scheduled = picks.matches.filter((m) => m.status === "scheduled");
  const activeWithoutPick = scheduled.filter(
    (m) => (m.state === "open" || m.state === "locked" || m.state === "live") && !m.pick
  );
  const dqWalkovers = scheduled.filter((m) => m.settlement_pick != null && m.state === "stale");
  const staleUnres = scheduled.filter(
    (m) => m.state === "stale" && !m.pick && !m.settlement_pick
  );

  const activeHtml = activeWithoutPick.length
    ? activeWithoutPick.map((m) => renderUnresolvedCard(m, "m-")).join("\n")
    : `<div class="empty-state">Zero items this run. ✓</div>`;

  const dqHtml = dqWalkovers.length
    ? dqWalkovers.map((m) => renderUnresolvedCard(m, "dq-")).join("\n")
    : `<div class="empty-state">Zero items this run. ✓</div>`;

  const staleHtml = staleUnres.length
    ? staleUnres.map((m) => renderUnresolvedCard(m, "st-")).join("\n")
    : `<div class="empty-state">Zero items this run. ✓</div>`;

  const bodyHtml = `
    <section class="page-hero">
      <h1>Unresolved Picks &amp; Limitations</h1>
      <p>Transparent accounting of every match where a sporting win probability cannot be verified from external betting markets or pre-kickoff match history, alongside administrative mid-split disqualification settlements and feed limitations.</p>
    </section>

    <div class="sec-head">
      <h2>1. Active Unresolved Matches (${activeWithoutPick.length})</h2>
      <span>Zero pre-kickoff history &amp; zero market lines — probabilities intentionally left blank</span>
    </div>
    <section class="cards-grid">
      ${activeHtml}
    </section>

    <div class="sec-head" id="walkover-settlements">
      <h2>2. Mid-Split Disqualification Walkover Settlements (${dqWalkovers.length})</h2>
      <span>Official league removal — administrative walkover settlement only, no sporting probability</span>
    </div>
    <section class="cards-grid">
      ${dqHtml}
    </section>

    <div class="sec-head" id="stale-unresolved">
      <h2>3. Stale Past-Kickoff Debut Cards (${staleUnres.length})</h2>
      <span>Hotspawn status remains 'scheduled' &gt;6h after kickoff; 0 prior matches at kickoff</span>
    </div>
    <section class="cards-grid">
      ${staleHtml}
    </section>

    <div class="sec-head" id="limitations">
      <h2>4. Documented Structural &amp; Data Limitations</h2>
    </div>
    <div class="callout">
      <h3>Known Feed &amp; Modeling Constraints</h3>
      <ul>
        <li><strong>Amateur open qualifiers with zero match history:</strong> Grassroots open qualifiers (such as Round 1 of <em>Logitech G SuperStrike Cup Qualifier</em>) feature newly formed 5-stacks with zero prior official series on Leaguepedia or Hotspawn and no regulated bookmaker lines. Per strict non-fabrication policy, these rows remain blank (<code>—</code>) rather than guessed.</li>
        <li><strong>Cross-region acronym collisions in upstream Hotspawn feed:</strong> Hotspawn occasionally binds amateur/regional short tags to Tier-1 homonyms (e.g., Bulgarian <code>PNG</code> bound to Brazilian CBLOL <code>paiN Gaming</code> on <code>#1083097</code>; Swiss <code>PvB (Swiss Team)</code> bound to defunct Vietnamese VCS <code>Phong Vũ Buffalo</code> on <code>#1079031</code>). Competition-scoped entity resolution quarantines these before rating lookup.</li>
        <li><strong>Multi-roster organization pooling on Leaguepedia:</strong> In <em>PRM 3rd Division 26-27 Fall</em>, Leaguepedia records the academy roster under <code>Rich Gang (Norwegian Team)</code> alongside the organization's Komplettligaen squad; pre-kickoff Elo reflects pooled org history and is flagged on <a href="flagged.html">Flagged for Review</a>.</li>
        <li><strong>Stale upstream Hotspawn cards:</strong> 65 lower-tier fixtures remain in <code>status="scheduled"</code> on Hotspawn more than 6 hours after scheduled start because upstream tournament admins have not settled the card yet. Pre-kickoff probabilities are preserved without post-kickoff look-ahead.</li>
        <li><strong>Sportsbook coverage ceiling on grassroots ERLs:</strong> Regulated esportsbooks and prediction markets price Tier-1 (Worlds) and select Tier-2 (LGC Rising) events (~4% of scheduled volume); the remaining ~93% rely on self-originated pre-kickoff Elo models, which carry wider epistemic uncertainty (OOS Brier <code>${s.calibration.brier?.toFixed(4)}</code>).</li>
      </ul>
    </div>
  `;

  return renderShell({
    activePage: "unresolved.html",
    title: "Unresolved Picks & Limitations",
    description: "Unresolved zero-history matches, mid-split disqualification walkover settlements, and structural limitations.",
    summary: s,
    bodyHtml,
  });
}

function buildFlaggedPage(picks, flagsObj) {
  const s = picks.summary;
  const list = flagsObj.flags || [];

  const rowsHtml = list.length
    ? list
        .map((f) => {
          const sevCls =
            f.severity === "high" ? "b-unres" : f.severity === "medium" ? "b-prov" : "b-model";
          return `<tr id="flag-${esc(f.id)}">
            <td><span class="badge ${sevCls}">${esc(f.severity.toUpperCase())}</span><br><span class="mono" style="font-size:0.74rem;color:var(--text-dim)">${esc(f.kind)}</span></td>
            <td><strong>${esc(f.matchup)}</strong><br><span style="color:var(--text-muted)">${esc(f.competition)}</span> · ${stateBadge(f.state)}</td>
            <td>${esc(f.detail)}</td>
            <td>
              <div class="card-links" style="border:0;padding:0">
                <a class="src-link" href="${esc(f.hotspawn_url)}" target="_blank" rel="noopener">Hotspawn #${esc(f.match_id)} ↗</a>
                <a class="src-link" href="${esc(f.source_url)}" target="_blank" rel="noopener">Official Source ↗</a>
              </div>
            </td>
          </tr>`;
        })
        .join("\n")
    : `<tr><td colspan="4">Zero items this run. ✓</td></tr>`;

  const bodyHtml = `
    <section class="page-hero">
      <h1>Flagged for Review (${list.length})</h1>
      <p>Every upstream entity-resolution collision, mid-split league disqualification, unverified zero-history debut, cross-venue market spread, and multi-roster pooling notice — each backed by official Hotspawn and Leaguepedia/bookmaker source links.</p>
    </section>

    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Severity / Type</th>
            <th>Matchup &amp; Competition</th>
            <th>Forensic Finding &amp; Resolution</th>
            <th>Verification Links</th>
          </tr>
        </thead>
        <tbody>
          ${rowsHtml}
        </tbody>
      </table>
    </div>
  `;

  return renderShell({
    activePage: "flagged.html",
    title: "Flagged for Review",
    description: "Audit log of entity-resolution collisions, mid-split disqualifications, and unverified Hotspawn LoL items.",
    summary: s,
    bodyHtml,
  });
}

function buildResultsPage(picks, ledgerObj) {
  const s = picks.summary;
  const ended = picks.matches.filter((m) => m.state === "ended" || m.state === "forfeited");
  const entries = ledgerObj.entries || [];

  const ledgerRows = entries.slice(0, 120).map((e) => {
    let statusCell = `<span class="badge b-state">awaiting official score</span>`;
    if (e.outcome) {
      const hasS = e.outcome.score0 != null && e.outcome.score1 != null;
      const scTxt = hasS ? `${e.outcome.score0}–${e.outcome.score1}` : e.outcome.status;
      if (e.outcome.correct === true) {
        statusCell = `<span class="badge b-pick">✓ Hit (${esc(scTxt)}, Brier ${e.outcome.brier.toFixed(3)})</span>`;
      } else if (e.outcome.correct === false) {
        statusCell = `<span class="badge b-unres">✗ Miss (${esc(scTxt)}, Brier ${e.outcome.brier.toFixed(3)})</span>`;
      } else {
        statusCell = `<span class="badge b-prov">${esc(e.outcome.status)} (${esc(scTxt)})</span>`;
      }
    }
    const p0Val = e.p0 ?? 0.5;
    return `<tr>
      <td class="mono">${esc(fmtUtc(e.start_iso))}</td>
      <td>${esc(e.competition_name)}</td>
      <td><strong>${esc(e.team0)}</strong> vs <strong>${esc(e.team1)}</strong></td>
      <td class="num">${pct1(p0Val)} / ${pct1(1 - p0Val)}</td>
      <td><span class="badge b-pick">${esc(e.pick_team || "")}</span></td>
      <td>${statusCell}</td>
      <td><a class="src-link" href="${esc(e.hotspawn_url)}" target="_blank" rel="noopener">Hotspawn #${esc(e.id)} ↗</a></td>
    </tr>`;
  }).join("\n");

  const endedRows = ended.map((m) => {
    const has = m.score0 !== null && m.score0 !== undefined && m.score1 !== null && m.score1 !== undefined;
    const scoreLine = has
      ? `${esc(m.team0.name)} ${esc(m.score0)}–${esc(m.score1)} ${esc(m.team1.name)}`
      : `${esc(m.team0.name)} vs (no official score) ${esc(m.team1.name)}`;
    return `<tr>
      <td class="mono">${esc(fmtUtc(m.start_iso))}</td>
      <td>${esc(m.competition_name)}</td>
      <td>${scoreLine}</td>
      <td>${stateBadge(m.state)}</td>
      <td><div class="card-links" style="border:0;padding:0">${renderSourceLinks(m)}</div></td>
    </tr>`;
  }).join("\n");

  const hitRate =
    ledgerObj.settled_entries > 0
      ? `${((ledgerObj.correct_entries / ledgerObj.settled_entries) * 100).toFixed(1)}% (${ledgerObj.correct_entries}/${ledgerObj.settled_entries})`
      : "Awaiting settled matches";

  const bodyHtml = `
    <section class="page-hero">
      <h1>Official Results &amp; Pre-Lock Prediction Ledger</h1>
      <p>Append-only ledger of pre-lock probability snapshots reconciled strictly against official Hotspawn <code>ended</code>/<code>forfeited</code> scores. Missing official scores are never inferred or filled in.</p>
    </section>

    <section class="kpi-grid">
      <div class="kpi">
        <div class="kpi-val">${ledgerObj.total_entries}</div>
        <div class="kpi-lbl">Tracked Pre-Lock Entries</div>
      </div>
      <div class="kpi">
        <div class="kpi-val">${ledgerObj.settled_entries}</div>
        <div class="kpi-lbl">Officially Settled</div>
      </div>
      <div class="kpi">
        <div class="kpi-val">${esc(hitRate)}</div>
        <div class="kpi-lbl">Realized Pick Accuracy</div>
      </div>
      <div class="kpi">
        <div class="kpi-val">${ledgerObj.mean_brier != null ? ledgerObj.mean_brier.toFixed(4) : "—"}</div>
        <div class="kpi-lbl">Realized Ledger Brier</div>
      </div>
      <div class="kpi">
        <div class="kpi-val">${ended.length}</div>
        <div class="kpi-lbl">Recent Official Results (21d)</div>
      </div>
      <div class="kpi">
        <div class="kpi-val">${s.calibration.brier?.toFixed(4) ?? "—"}</div>
        <div class="kpi-lbl">Historical OOS Brier (22.4k)</div>
      </div>
    </section>

    <div class="sec-head">
      <h2>Pre-Lock Prediction Ledger (Latest 120 Entries)</h2>
      <a href="methodology.html">Calibration details →</a>
    </div>
    <div class="table-wrap" style="margin-bottom:1.75rem">
      <table class="data-table">
        <thead>
          <tr>
            <th>Kickoff (UTC)</th>
            <th>Competition</th>
            <th>Matchup</th>
            <th class="num">Pre-Lock Win %</th>
            <th>Pre-Lock Pick</th>
            <th>Official Settlement</th>
            <th>Receipt</th>
          </tr>
        </thead>
        <tbody>${ledgerRows}</tbody>
      </table>
    </div>

    <div class="sec-head">
      <h2>Recent Official Hotspawn Results &amp; Forfeits (${ended.length})</h2>
    </div>
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Kickoff (UTC)</th>
            <th>Competition</th>
            <th>Official Result</th>
            <th>Status</th>
            <th>Receipts</th>
          </tr>
        </thead>
        <tbody>${endedRows}</tbody>
      </table>
    </div>
  `;

  return renderShell({
    activePage: "results.html",
    title: "Results & Pre-Lock Ledger",
    description: "Official Hotspawn LoL match outcomes and pre-lock prediction Brier ledger.",
    summary: s,
    bodyHtml,
  });
}

function buildCalibrationSvg(bins) {
  const W = 440;
  const H = 280;
  const pad = 42;
  const plotW = W - 2 * pad;
  const plotH = H - 2 * pad;

  const pts = bins
    .filter((b) => b.n > 0 && b.mean_pred != null && b.empirical_win_rate != null)
    .map((b) => {
      const x = pad + b.mean_pred * plotW;
      const y = pad + (1 - b.empirical_win_rate) * plotH;
      return { x: x.toFixed(1), y: y.toFixed(1), n: b.n, pred: b.mean_pred, emp: b.empirical_win_rate };
    });

  const polyPoints = pts.map((p) => `${p.x},${p.y}`).join(" ");
  const circles = pts
    .map(
      (p) =>
        `<circle cx="${p.x}" cy="${p.y}" r="4.5" fill="#10b981" stroke="#0b101b" stroke-width="1.5"><title>Pred ${(p.pred * 100).toFixed(1)}% vs Realized ${(p.emp * 100).toFixed(1)}% (n=${p.n})</title></circle>`
    )
    .join("");

  return `<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:480px;background:#0b101b;border:1px solid var(--border);border-radius:8px;display:block" role="img" aria-label="Out-of-sample reliability calibration curve">
    <line x1="${pad}" y1="${H - pad}" x2="${W - pad}" y2="${pad}" stroke="#64748b" stroke-dasharray="4 4" stroke-width="1.5"/>
    <line x1="${pad}" y1="${H - pad}" x2="${W - pad}" y2="${H - pad}" stroke="#364c78" stroke-width="1"/>
    <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${H - pad}" stroke="#364c78" stroke-width="1"/>
    <polyline fill="none" stroke="#38bdf8" stroke-width="2" points="${polyPoints}"/>
    ${circles}
    <text x="${W / 2}" y="${H - 10}" fill="#9cb0d1" font-size="11" text-anchor="middle">Predicted Pre-Kickoff Win Probability</text>
    <text x="14" y="${H / 2}" fill="#9cb0d1" font-size="11" text-anchor="middle" transform="rotate(-90 14 ${H / 2})">Empirical Win Rate</text>
    <text x="${pad}" y="${H - pad + 14}" fill="#6f84a8" font-size="10">0%</text>
    <text x="${W - pad - 18}" y="${H - pad + 14}" fill="#6f84a8" font-size="10">100%</text>
  </svg>`;
}

function buildMethodologyPage(picks) {
  const s = picks.summary;
  const cal = s.calibration;

  const binRows = (cal.reliability_bins || [])
    .map(
      (b) => `<tr>
      <td class="mono">${esc(b.bin)}</td>
      <td class="num">${b.n.toLocaleString()}</td>
      <td class="num">${b.mean_pred != null ? pct1(b.mean_pred) : "—"}</td>
      <td class="num">${b.empirical_win_rate != null ? pct1(b.empirical_win_rate) : "—"}</td>
      <td class="num">${b.mean_pred != null && b.empirical_win_rate != null ? `${((b.empirical_win_rate - b.mean_pred) * 100).toFixed(2)} pp` : "—"}</td>
    </tr>`
    )
    .join("\n");

  const bodyHtml = `
    <section class="page-hero">
      <h1>Methodology, Walk-Forward Calibration &amp; Venue Audit</h1>
      <p>Full technical specification of the 6-hour scheduled Hotspawn LoL ingestion pipeline, Shin power de-vigging, 5-venue consensus weighting, strict pre-kickoff Elo/Bradley-Terry ratings, and competition-scoped entity disambiguation.</p>
    </section>

    <div class="sec-head">
      <h2>1. Strict Independence from Hotspawn Signals</h2>
    </div>
    <div class="callout">
      <p>Hotspawn's public API exposes <code>participants0_picked_percent</code>, <code>participants1_picked_percent</code>, <code>offered_points</code>, and <code>tier</code>. Zero Hotspawn crowd or gamification fields are ever read by any probability, consensus, or rating function in <code>scripts/analyze.mjs</code>. Every published win probability derives solely from external real-money markets or external historical match outcomes.</p>
    </div>

    <div class="sec-head">
      <h2>2. Tier-1 &amp; Tier-2 Multi-Venue Market Consensus</h2>
    </div>
    <div class="table-wrap" style="margin-bottom:1.25rem">
      <table class="data-table">
        <thead>
          <tr>
            <th>Venue</th>
            <th>Endpoint / Feed</th>
            <th class="num">Consensus Weight</th>
            <th>De-Vig &amp; Derivative Safeguards</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Pinnacle</strong></td>
            <td class="mono">guest.api.arcadia.pinnacle.com/0.1</td>
            <td class="num">1.00</td>
            <td>Shin power de-vig (<code>q0^k + q1^k = 1</code>) on <code>period=0</code> series moneylines; <code>(Kills)</code> props strictly rejected.</td>
          </tr>
          <tr>
            <td><strong>Unibet / Kambi</strong></td>
            <td class="mono">eu-offering-api.kambicdn.com (ubse)</td>
            <td class="num">0.70</td>
            <td>Shin power de-vig on pre-match <code>Match Odds</code> (criterion type 2); per-event JSON receipts linked.</td>
          </tr>
          <tr>
            <td><strong>Kalshi CFTC</strong></td>
            <td class="mono">api.elections.kalshi.com (KXLOLGAME)</td>
            <td class="num">0.40–0.55</td>
            <td>Regulated US CFTC binary contracts; bid/ask midpoint normalized across both team contracts (includes Tier-2 LGC Rising).</td>
          </tr>
          <tr>
            <td><strong>Bovada</strong></td>
            <td class="mono">bovada.lv/services/sports/event/coupon</td>
            <td class="num">0.50</td>
            <td>Shin power de-vig on pre-match <code>Head To Head</code> moneylines when available from runner region.</td>
          </tr>
          <tr>
            <td><strong>Polymarket CLOB</strong></td>
            <td class="mono">gamma-api.polymarket.com</td>
            <td class="num">0.25–0.65</td>
            <td>Liquidity-scaled CLOB match winner contracts (<code>spread &le; 0.14</code>); map/over-under/odd-even derivatives excluded.</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p style="font-size:0.86rem;color:var(--text-muted)"><strong>Evaluated &amp; excluded external venues:</strong> Rivalry (<code>rivalry.com/operationally-closed</code> — operations permanently ceased), Midnite (0 LoL markets listed), Bet365 / DraftKings / GG.bet / Thunderpick (commercial anti-bot / Cloudflare blocks without public JSON receipts), and aggregator placeholders (<code>1.80 / 1.80</code> symmetric unpriced templates rejected). Analytical LoL reference portals consulted for cross-verification include <a href="https://lol.fandom.com/wiki/League_of_Legends_Esports_Wiki" target="_blank" rel="noopener">Leaguepedia</a>, <a href="https://gol.gg/tournament/list/" target="_blank" rel="noopener">Games of Legends (gol.gg)</a>, and <a href="https://bo3.gg/lol" target="_blank" rel="noopener">bo3.gg</a>.</p>

    <div class="sec-head">
      <h2>3. Self-Originated Pre-Kickoff Elo / Bradley-Terry Model</h2>
    </div>
    <div class="callout">
      <ul>
        <li><strong>Dataset:</strong> <code>${cal.series_replayed.toLocaleString()}</code> completed non-forfeit Leaguepedia + Hotspawn LoL series replayed in strict chronological order; administrative forfeits (<code>ff</code>) are excluded from skill updates.</li>
        <li><strong>Zero look-ahead:</strong> Every Hotspawn fixture at timestamp <code>T</code> is scored exclusively from ratings accumulated across matches with <code>t &lt; T</code>.</li>
        <li><strong>Competition-scoped entity disambiguation:</strong> Teams are resolved inside their specific Leaguepedia tournament page before global matching, preventing cross-region homonym contamination (such as Bulgarian amateur <code>PNG</code> vs Brazilian <code>paiN Gaming</code> on <code>#1083097</code>, or Swiss <code>PvB (Swiss Team)</code> vs Vietnamese <code>Phong Vũ Buffalo</code> on <code>#1079031</code>).</li>
        <li><strong>Empirical-Bayes shrinkage &amp; series transform:</strong> Ratings initialize at <code>1500</code> with dynamic <code>K = 38 / 28 / 22</code>, shrink toward <code>1500</code> via <code>n / (n + 6)</code>, and map to Bo3/Bo5 series probabilities with correlated-game damping (<code>&alpha; = 0.72</code>). Full current ratings JSON: <a href="${REPO_URL}/blob/main/data/node/model/ratings.json" target="_blank" rel="noopener">data/node/model/ratings.json ↗</a>.</li>
      </ul>
    </div>

    <div class="sec-head">
      <h2>4. Out-of-Sample Walk-Forward Calibration (${cal.oos_evaluated.toLocaleString()} Series)</h2>
      <span>Brier ${cal.brier?.toFixed(4)} (coinflip 0.2500) · Log-Loss ${cal.log_loss?.toFixed(4)} · Accuracy ${pct1(cal.accuracy)}</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:1.25rem;align-items:start">
      <div>${buildCalibrationSvg(cal.reliability_bins || [])}</div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Predicted Bin</th>
              <th class="num">Series (n)</th>
              <th class="num">Mean Pred</th>
              <th class="num">Realized Win %</th>
              <th class="num">Calibration Gap</th>
            </tr>
          </thead>
          <tbody>${binRows}</tbody>
        </table>
      </div>
    </div>
  `;

  return renderShell({
    activePage: "methodology.html",
    title: "Methodology & Calibration",
    description: "Mathematical specification, 22,372-series walk-forward calibration curve, and external venue audit.",
    summary: s,
    bodyHtml,
  });
}

/* ------------------------------------------------------------------- Write */

await mkdir(DOCS, { recursive: true });
const picks = JSON.parse(await readFile(path.join(DATA, "picks.json"), "utf8"));
const flags = JSON.parse(await readFile(path.join(DATA, "flags.json"), "utf8"));
const ledger = JSON.parse(await readFile(path.join(DATA, "history", "ledger.json"), "utf8"));

const pages = [
  ["index.html", buildIndexPage(picks, flags)],
  ["table.html", buildTablePage(picks)],
  ["picks.html", buildPicksPage(picks)],
  ["featured.html", buildFeaturedPage(picks)],
  ["originated.html", buildOriginatedPage(picks)],
  ["tournaments.html", buildTournamentsPage(picks)],
  ["unresolved.html", buildUnresolvedPage(picks)],
  ["flagged.html", buildFlaggedPage(picks, flags)],
  ["results.html", buildResultsPage(picks, ledger)],
  ["methodology.html", buildMethodologyPage(picks)],
];

for (const [name, html] of pages) {
  await writeFile(path.join(DOCS, name), html);
}
console.log(`build_site.mjs complete: wrote ${pages.length} HTML pages to docs/`);
