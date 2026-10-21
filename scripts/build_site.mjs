#!/usr/bin/env node
/**
 * build_site.mjs — Stage 3: render the static GitHub Pages site into docs/.
 *
 * Pages:
 *   index.html        Executive summary (mobile-first; links to every picks list)
 *   picks.html        Every open match: probabilities per team, the pick, line sources
 *   unresolved.html   Matches without a pick + the limitations behind each
 *   flagged.html      "Flagged for Review" — irregularities with source links
 *   results.html      Settled matches this week + pick accuracy tracking
 *   tournaments.html  Picks organized by tournament (category subpages via filters)
 *   methodology.html  Sources, formulas, precedence, verification policy, limitations
 *   data/picks.json   Machine-readable dataset (copy)
 *
 * Everything is server-rendered static HTML (readable without JS); assets/app.js
 * only adds filtering. Verifies internal links at the end; exits non-zero on breaks.
 */
import { readFile, writeFile, mkdir, copyFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DOCS = path.join(ROOT, "docs");
const readJSON = async (p, fb = null) => { try { return JSON.parse(await readFile(p, "utf8")); } catch { return fb; } };

const picksData = await readJSON(path.join(ROOT, "data", "picks.json"));
if (!picksData) { console.error("FATAL: data/picks.json missing — run analyze.mjs first."); process.exit(2); }
const flagsData = await readJSON(path.join(ROOT, "data", "flags.json"), { flags: [] });
const ledger = await readJSON(path.join(ROOT, "data", "history", "picks_latest.json"), {});
const collectLog = await readJSON(path.join(ROOT, "data", "raw", "collect_log.json"), {});

const { summary, tournaments, matches } = picksData;
const GEN_MS = Date.parse(summary.generated_at);
const NEXT_MS = GEN_MS + 6 * 3600 * 1000;

/* ------------------------------------------------------------------ helpers */

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (p) => (p == null ? "—" : `${(p * 100).toFixed(p >= 0.995 ? 0 : 1)}%`);
const dtf = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" });
const df = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
const fmtDT = (msOrIso) => { const ms = typeof msOrIso === "string" ? Date.parse(msOrIso) : msOrIso; return ms ? dtf.format(new Date(ms)) + " UTC" : "—"; };
const fmtDay = (ms) => (ms ? df.format(new Date(ms)) : "—");
const dayKey = (ms) => (ms ? new Date(ms).toISOString().slice(0, 10) : "unknown");
function countdown(ms) {
  if (!ms) return "—";
  const d = ms - Date.now();
  if (d <= 0) return "locked";
  const h = Math.floor(d / 3600000), m = Math.floor((d % 3600000) / 60000);
  if (h >= 48) return `locks in ${Math.floor(h / 24)}d ${h % 24}h`;
  if (h >= 1) return `locks in ${h}h ${String(m).padStart(2, "0")}m`;
  return `locks in ${m}m`;
}
const openM = matches.filter((m) => m.state === "open").sort((a, b) => (a.lock_ms ?? Infinity) - (b.lock_ms ?? Infinity));
const lockedM = matches.filter((m) => ["locked", "live"].includes(m.state)).sort((a, b) => (a.start_ms ?? 0) - (b.start_ms ?? 0));
const endedM = matches.filter((m) => m.state === "ended").sort((a, b) => (b.start_ms ?? 0) - (a.start_ms ?? 0));
const unresolved = openM.filter((m) => !m.pick);
const srcKey = (m) => (m.market_pinnacle ? "pinnacle" : m.market_polymarket ? "polymarket" : m.pick ? "model" : "none");
const srcBadge = (m) => {
  const k = srcKey(m);
  if (k === "pinnacle") return `<span class="badge src-mkt" title="Devigged Pinnacle moneyline">MARKET · PINNACLE</span>`;
  if (k === "polymarket") return `<span class="badge src-mkt" title="Polymarket prices">MARKET · POLYMARKET</span>`;
  if (k === "model") return `<span class="badge src-model" title="Own Elo-style model">OWN MODEL</span>`;
  return `<span class="badge src-none">NO LINE</span>`;
};
const tierBadge = (m) => (m.tier && !/waiting/i.test(m.tier) ? `<span class="badge tier">TIER ${esc(String(m.tier).toUpperCase())}</span>` : "");

function bars(m) {
  const pickIdx = m.pick ? m.pick.team_index : -1;
  const p0 = m.market_pinnacle ? m.market_pinnacle.p0 : m.market_polymarket ? m.market_polymarket.p0 : m.model ? m.model.p0 : null;
  const p1 = p0 == null ? null : 1 - p0;
  const row = (idx, t, p) => `
    <div class="team-row ${idx === pickIdx ? "picked" : ""}">
      <div class="team-name"><span class="nm">${esc(t.name)}</span>${idx === pickIdx ? '<span class="pick-tag">PICK</span>' : ""}</div>
      <div class="prob">${p == null ? "—" : pct(p)}</div>
      <div class="bar"><i style="width:${p == null ? 0 : Math.max(2, Math.round(p * 100))}%"></i></div>
    </div>`;
  return `<div class="teams">${row(0, m.team0, p0)}${row(1, m.team1, p1)}</div>`;
}

function linesBlock(m) {
  const L = [];
  if (m.market_pinnacle) {
    const p = m.market_pinnacle;
    L.push(`<div><b>Pinnacle</b> (devigged): ${pct(p.p0)} / ${pct(p.p1)} · odds ${p.odds0 > 0 ? "+" : ""}${p.odds0} / ${p.odds1 > 0 ? "+" : ""}${p.odds1}${p.match_quality && p.match_quality !== "exact" ? ` · <i>name match: ${esc(p.match_quality)}</i>` : ""} — <a href="${esc(p.url)}" rel="noopener" target="_blank">source ↗</a></div>`);
  }
  if (m.market_polymarket) {
    const p = m.market_polymarket;
    L.push(`<div><b>Polymarket</b> (${esc(p.price_kind)}): ${pct(p.p0)} / ${pct(p.p1)}${p.liquidity != null ? ` · liq $${Math.round(Number(p.liquidity)).toLocaleString("en-US")}` : ""} — <a href="${esc(p.url)}" rel="noopener" target="_blank">source ↗</a></div>`);
  }
  if (m.model) {
    L.push(`<div><b>Own model</b> (Elo-style): ${pct(m.model.p0)} / ${pct(m.model.p1)} · ratings ${m.model.r0} vs ${m.model.r1} · ${m.model.n0}/${m.model.n1} series played</div>`);
  }
  return L.length ? `<div class="lines">${L.join("")}</div>` : `<div class="lines"><b>No line source available.</b> See <a href="unresolved.html">Unresolved Picks</a>.</div>`;
}

function matchCard(m, { showState = false } = {}) {
  const conf = m.pick ? `<span class="badge conf-${esc(m.pick.confidence)}">${esc(m.pick.confidence.toUpperCase())} CONFIDENCE</span>` : "";
  const stateB = showState && m.state !== "open" ? `<span class="badge ${m.state === "live" ? "live" : "state"}">${esc(m.state.toUpperCase())}</span>` : "";
  const searchable = `${m.team0.name} ${m.team1.name} ${m.competition} ${m.tier ?? ""}`.toLowerCase();
  return `
  <article class="match" id="m-${esc(m.id)}" data-searchable="${esc(searchable)}" data-tour="${esc(m.competition_id)}" data-src="${srcKey(m)}" data-lock="${m.lock_ms ?? 0}">
    <div class="meta">
      <span>🕒 ${fmtDT(m.start_ms)}</span><span>· ${countdown(m.lock_ms)}</span>
      ${tierBadge(m)} ${stateB} ${conf}
      ${m.offered_points ? `<span>· ${m.offered_points} pts</span>` : ""}
    </div>
    <div class="meta" style="margin-bottom:8px"><span>🏆 <a href="picks.html?tour=${esc(m.competition_id)}">${esc(m.competition)}</a></span>${m.stage && !/waiting/i.test(m.stage) ? `<span>· ${esc(m.stage)}</span>` : ""}</div>
    ${bars(m)}
    ${linesBlock(m)}
    <div class="foot">
      <a href="${esc(m.hotspawn_url)}" rel="noopener" target="_blank">Hotspawn match ↗</a>
      ${m.hotspawn_url_constructed ? '<span class="small">(link constructed from slugs)</span>' : ""}
      ${srcBadge(m)}
    </div>
  </article>`;
}

/* ------------------------------------------------------------------- layout */

const NAV = [
  ["index.html", "Summary", "📊"],
  ["picks.html", "Picks", "✅"],
  ["unresolved.html", "Unresolved", "⚠️"],
  ["flagged.html", "Flagged", "🚩"],
  ["results.html", "Results", "📈"],
  ["tournaments.html", "Tournaments", "🏆"],
  ["methodology.html", "Method", "📖"],
];

function layout(title, active, body, desc = "") {
  const nav = NAV.map(([href, label, icon]) => `<a href="${href}" class="${href === active ? "active" : ""}">${icon} ${label}</a>`).join("");
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0b1020">
<meta name="description" content="${esc(desc)}">
<title>${esc(title)}</title>
<link rel="stylesheet" href="assets/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎯</text></svg>">
</head>
<body>
<header class="top"><div class="top-in">
  <a class="brand" href="index.html"><span class="logo">🎯</span> LoL Hotspawn Picks</a>
  <nav class="main">${nav}</nav>
</div></header>
<main class="wrap">
${body}
<footer class="bot">
  <p><b>LoL Hotspawn Picks</b> — independent analytics for the League of Legends matches listed on the Hotspawn pick'em lobby. Not affiliated with Hotspawn, Riot Games, or any bookmaker. Nothing here is betting advice.</p>
  <p>Probabilities come from external betting lines (Pinnacle, Polymarket) and our own Elo-style model built from real match results — never from Hotspawn crowd pick percentages. Data refreshes every 6 hours via GitHub Actions.</p>
  <p>Built ${fmtDT(GEN_MS)} · <a href="methodology.html">Methodology &amp; sources</a> · <a href="data/picks.json">Raw data (JSON)</a> · <a href="https://github.com/karagemop466-tech/LOLHOTSPAWN1" rel="noopener" target="_blank">GitHub repo</a></p>
</footer>
</main>
<script src="assets/app.js" defer></script>
</body>
</html>`;
}

/* -------------------------------------------------------------- index.html */

const c = summary.counts;
const acc = summary.accuracy ?? { tracked: 0, hits: 0, rate: null };
const soon = openM.filter((m) => m.pick).slice(0, 6);

const unresolvedNames = unresolved.slice(0, 12).map((m) => `<li><b>${esc(m.team0.name)} vs ${esc(m.team1.name)}</b> — ${esc(m.competition)} · ${fmtDT(m.start_ms)} <a href="unresolved.html#m-${esc(m.id)}">(why)</a></li>`).join("");

const indexBody = `
<div class="hero">
  <h1>League of Legends picks for every Hotspawn match</h1>
  <p class="sub">Win probabilities for all <b>${c.open} open LoL matches</b> on the Hotspawn pick'em lobby — originated from external betting lines (Pinnacle, Polymarket) and our own Elo-style model. Refreshed every 6 hours.</p>
  <span class="updated"><span class="dot"></span> Data updated <b>${fmtDT(GEN_MS)}</b> · next ≈ ${fmtDT(NEXT_MS)}</span>
</div>

<div class="cta-row">
  <a class="cta" href="picks.html">✅ View all picks &amp; probabilities <span class="big">→</span></a>
</div>
<div class="cta-row">
  <a class="cta alt" href="unresolved.html">⚠️ Unresolved picks <small>${c.unresolved_open} without a line — see limitations</small></a>
  <a class="cta alt" href="flagged.html">🚩 Flagged for review <small>${c.flags_needs_review} items</small></a>
  <a class="cta alt" href="results.html">📈 Results &amp; accuracy <small>${acc.tracked ? `${acc.hits}/${acc.tracked} correct (${acc.rate}%)` : "tracking builds up"}</small></a>
</div>

<div class="kpis">
  <div class="kpi acc"><div class="n">${c.open}</div><div class="l">Open LoL matches</div></div>
  <div class="kpi good"><div class="n">${c.market_pinnacle + c.market_polymarket_only}</div><div class="l">Picks from betting lines</div></div>
  <div class="kpi warn"><div class="n">${c.model_only}</div><div class="l">Picks from own model</div></div>
  <div class="kpi bad"><div class="n">${c.unresolved_open}</div><div class="l">Unresolved (no pick)</div></div>
  <div class="kpi"><div class="n">${c.ended_this_week}</div><div class="l">Settled this week</div></div>
</div>

<section class="card">
  <h2>Executive summary</h2>
  <p class="desc">Everything you need, in one place. Full pick list: <a href="picks.html"><b>picks.html</b></a>.</p>
  <ul style="margin:8px 0 0;padding-left:20px;color:var(--mut);font-size:14.5px">
    <li><b>Coverage:</b> ${c.picks_total} of ${c.open} open matches (${c.open ? Math.round((c.picks_total / c.open) * 100) : 0}%) carry a pick with a win probability for each team. ${c.market_pinnacle} priced by Pinnacle, ${c.market_polymarket_only} by Polymarket, ${c.model_only} by our own Elo-style model built from the full Hotspawn results archive.</li>
    <li><b>Picks are external:</b> Hotspawn crowd "% picked" is never used as a probability. Lines come from Pinnacle's guest odds API and Polymarket markets; where no market exists we originate our own line from real match results.</li>
    <li><b>Unresolved:</b> ${c.unresolved_open} open match${c.unresolved_open === 1 ? "" : "es"} could not be priced — no bookmaker/prediction market lists them and at least one team has no recorded series history. Details + limitations: <a href="unresolved.html">Unresolved Picks</a>.</li>
    <li><b>Quality control:</b> ${c.flags_needs_review} item(s) need manual review (name-match ambiguity, line divergences, thin markets) — <a href="flagged.html">Flagged for Review</a>. ${c.flags_info} informational note(s).</li>
    <li><b>Freshness:</b> GitHub Actions re-collects every 6h (within the 4–8h requirement). Last collect: ${esc(collectLog.fetched_at ? fmtDT(collectLog.fetched_at) : "unknown")}${collectLog.duration_s ? ` (took ${collectLog.duration_s}s)` : ""}.</li>
  </ul>
</section>

<section class="card">
  <h2>🔥 Closing soon — picks at a glance</h2>
  <p class="desc">Next ${soon.length} open matches by pick-lock time. <a href="picks.html?soon=1">All matches locking within 24h →</a></p>
  ${soon.map((m) => matchCard(m)).join("") || '<p class="small">No open matches with picks right now.</p>'}
</section>

<section class="card">
  <h2>⚠️ Unresolved picks &amp; limitations</h2>
  <p class="desc">Required disclosure: these open matches have <b>no pick</b> and why. Full list: <a href="unresolved.html">unresolved.html</a>.</p>
  ${unresolved.length ? `<ul style="margin:6px 0;padding-left:20px;color:var(--mut);font-size:14px">${unresolvedNames}${unresolved.length > 12 ? `<li>…and ${unresolved.length - 12} more on the <a href="unresolved.html">Unresolved page</a>.</li>` : ""}</ul>` : `<p style="color:var(--good);font-weight:700">✓ Every open match currently has a pick.</p>`}
  <p class="small" style="margin-top:8px">Why some matches stay unresolved: (1) low-tier leagues (e.g. amateur/regional divisions) are not priced by any established esports book or exchange we can verify; (2) Polymarket only lists major events; (3) our own model needs at least one recorded series for both teams — brand-new rosters have zero history, and inventing a number would violate our no-hallucination rule.</p>
</section>

<section class="card">
  <h2>📚 Where to find things</h2>
  <div class="grid2">
    <div>
      <p class="mb0"><a href="picks.html"><b>✅ Picks</b></a> — every open match, probability per team, the pick, and the line source with links. Filter by tournament/source; mobile-friendly cards.</p>
      <p><a href="tournaments.html"><b>🏆 Tournaments</b></a> — picks organized by category/tournament with coverage counts.</p>
      <p><a href="results.html"><b>📈 Results</b></a> — this week's settled matches and how our tracked picks performed.</p>
    </div>
    <div>
      <p class="mt0"><a href="unresolved.html"><b>⚠️ Unresolved</b></a> — matches without a pick, each with its specific limitation.</p>
      <p><a href="flagged.html"><b>🚩 Flagged for Review</b></a> — irregularities needing human eyes, with source links.</p>
      <p><a href="methodology.html"><b>📖 Methodology</b></a> — data sources, formulas, precedence rules, verification policy.</p>
    </div>
  </div>
</section>`;

/* -------------------------------------------------------------- picks.html */

const tourById = {};
for (const m of [...openM, ...lockedM]) tourById[m.competition_id] = m.competition;
const tourOptions2 = Object.entries(tourById)
  .map(([id, name]) => {
    const n = openM.filter((m) => m.competition_id === id).length;
    return `<option value="${esc(id)}">${esc(name)} (${n} open)</option>`;
  })
  .sort()
  .join("");

const groups = new Map();
for (const m of openM) {
  const k = dayKey(m.lock_ms ?? m.start_ms);
  if (!groups.has(k)) groups.set(k, []);
  groups.get(k).push(m);
}
let picksBody = "";
for (const [k, list] of [...groups.entries()].sort()) {
  const first = list[0];
  picksBody += `<div class="dayhdr" data-dayhdr="1">${fmtDay(first.lock_ms ?? first.start_ms)} <span>${list.length} match${list.length === 1 ? "" : "es"} · ${list.filter((m) => m.pick).length} with picks</span></div>`;
  picksBody += list.map((m) => matchCard(m)).join("");
}

const picksPage = `
<div class="hero">
  <h1>✅ All picks — ${c.open} open LoL matches</h1>
  <p class="sub">Every match currently pickable on the Hotspawn lobby, sorted by lock time. The <b style="color:var(--good)">PICK</b> tag marks our selection; percentages are each team's win probability from the best available line (Pinnacle → Polymarket → own model).</p>
  <span class="updated"><span class="dot"></span> Updated <b>${fmtDT(GEN_MS)}</b> · ${c.picks_total}/${c.open} with picks · ${c.unresolved_open} unresolved (<a href="unresolved.html">why</a>)</span>
</div>
<div class="filters">
  <input id="f-q" type="search" placeholder="Search team or tournament…" autocomplete="off">
  <select id="f-tour"><option value="">All tournaments</option>${tourOptions2}</select>
  <select id="f-src">
    <option value="">All sources</option>
    <option value="pinnacle">Pinnacle lines</option>
    <option value="polymarket">Polymarket lines</option>
    <option value="market">Any market line</option>
    <option value="model">Own model only</option>
    <option value="unresolved">Unresolved</option>
  </select>
  <select id="f-soon-wrap" style="display:none"></select>
  <label style="display:flex;align-items:center;gap:8px;background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:11px 12px;min-height:46px;font-size:15px">
    <input id="f-soon" type="checkbox" style="width:20px;height:20px;accent-color:var(--acc)"> Locks ≤ 24h
  </label>
</div>
<p class="count-line" id="f-count"></p>
${picksBody}
${lockedM.length ? `<h2 class="sec">🔒 Locked / in progress (${lockedM.length})</h2><p class="small">Picks can no longer be submitted on Hotspawn for these; lines shown for reference.</p>${lockedM.map((m) => matchCard(m, { showState: true })).join("")}` : ""}
`;

/* ---------------------------------------------------------- unresolved.html */

const pinLeaguesRaw = (await readJSON(path.join(ROOT, "data", "raw", "pinnacle_lol.json"), { leagues: [] })).leagues.map((l) => l.name);
picksData.summary.pinnacle_leagues_list = pinLeaguesRaw;

function unresolvedReason(m) {
  const r = [];
  r.push(`No Pinnacle moneyline: Pinnacle's guest API currently lists LoL leagues [${esc(pinLeaguesRaw.join("; ") || "none live at build time")}] — “${esc(m.competition)}” is not among them.`);
  r.push(`No Polymarket market: no open two-outcome LoL market matches “${esc(m.team0.name)} vs ${esc(m.team1.name)}” (Polymarket lists mainly tier-1 events).`);
  const h = m.team_history ?? { n0: 0, n1: 0 };
  if (!m.model) r.push(`Own model impossible: recorded series in the Hotspawn results archive — ${esc(m.team0.name)}: <b>${h.n0}</b>, ${esc(m.team1.name)}: <b>${h.n1}</b>. With zero history on one side, any probability would be invented, not derived.`);
  return r;
}

const unresolvedPage = `
<div class="hero">
  <h1>⚠️ Unresolved picks &amp; limitations</h1>
  <p class="sub">${c.unresolved_open} open match${c.unresolved_open === 1 ? "" : "es"} have <b>no pick</b>. We publish the reason for each instead of inventing probabilities. Every other open match has a pick on the <a href="picks.html">Picks page</a>.</p>
</div>
<section class="card">
  <h2>Why a match can be unresolvable</h2>
  <ul style="margin:6px 0;padding-left:20px;color:var(--mut);font-size:14.5px">
    <li><b>No market coverage.</b> Established esports books (Pinnacle and the sportsbooks aggregated by odds sites) price tier-1/tier-2 events; amateur and regional divisions (e.g. PRM 3rd Division, RIVALS LEAGUE, Tunisian Super League, Icelandic Esports League, Arabian Regional Championship) are not offered.</li>
    <li><b>No prediction-market coverage.</b> Polymarket lists only high-profile LoL matches (Worlds, major regional leagues).</li>
    <li><b>No history for our own line.</b> Our Elo-style model is built from real results in the Hotspawn archive. If either team has never played a recorded series, the model has nothing to rate — outputting 50/50 (or any number) would be fabricated precision.</li>
    <li><b>No manual input.</b> Per project requirements, nothing is filled in by hand or guessed; unresolvable matches stay unresolvable until a source appears (each refresh re-checks all sources).</li>
  </ul>
</section>
<h2 class="sec">Matches without a pick (${unresolved.length})</h2>
${unresolved.map((m) => `
  <article class="match" id="m-${esc(m.id)}">
    <div class="meta"><span>🕒 ${fmtDT(m.start_ms)}</span><span>· ${countdown(m.lock_ms)}</span>${tierBadge(m)}<span>· ${m.offered_points ?? "—"} pts</span></div>
    <div class="meta" style="margin-bottom:8px"><span>🏆 ${esc(m.competition)}</span></div>
    <div class="teams">
      <div class="team-row"><div class="team-name"><span class="nm">${esc(m.team0.name)}</span></div><div class="prob">—</div><div class="bar"><i style="width:0%"></i></div></div>
      <div class="team-row"><div class="team-name"><span class="nm">${esc(m.team1.name)}</span></div><div class="prob">—</div><div class="bar"><i style="width:0%"></i></div></div>
    </div>
    <div class="lines"><b>Why unresolved:</b><ul style="margin:4px 0 0;padding-left:18px">${unresolvedReason(m).map((x) => `<li>${x}</li>`).join("")}</ul></div>
    <div class="foot"><a href="${esc(m.hotspawn_url)}" rel="noopener" target="_blank">Hotspawn match ↗</a> <span class="badge src-none">NO LINE</span></div>
  </article>`).join("") || '<p style="color:var(--good);font-weight:700">✓ Every open match currently has a pick. Nothing is unresolved.</p>'}
`;

/* ------------------------------------------------------------- flagged.html */

const nf = flagsData.flags.filter((f) => f.severity === "needs-review");
const inf = flagsData.flags.filter((f) => f.severity !== "needs-review");
const flagCard = (f) => `
  <div class="flag ${esc(f.severity)}">
    <h3>${esc(f.title)}${f.match_id ? ` <span class="small">· match #${esc(f.match_id)}</span>` : ""}</h3>
    <p>${esc(f.detail).replace(/&lt;b&gt;/g, "<b>").replace(/&lt;\/b&gt;/g, "</b>")}</p>
    <div class="links">${(f.links || []).filter(Boolean).map((l) => `<a href="${esc(l)}" rel="noopener" target="_blank">${esc(l.replace(/^https?:\/\//, "").slice(0, 60))} ↗</a>`).join("")}</div>
  </div>`;
const flaggedPage = `
<div class="hero">
  <h1>🚩 Flagged for Review</h1>
  <p class="sub">Irregularities found by the automated pipeline. Per project rules these are <b>published, not blocking</b> — the site stays live and picks keep updating while a human reviews them. Raised ${fmtDT(GEN_MS)}.</p>
</div>
<div class="kpis">
  <div class="kpi bad"><div class="n">${nf.length}</div><div class="l">Needs review</div></div>
  <div class="kpi acc"><div class="n">${inf.length}</div><div class="l">Informational</div></div>
</div>
<h2 class="sec">Needs review (${nf.length})</h2>
${nf.map(flagCard).join("") || '<p class="small">None this run. ✓</p>'}
<h2 class="sec">Informational (${inf.length})</h2>
${inf.map(flagCard).join("") || '<p class="small">None this run. ✓</p>'}
`;

/* ------------------------------------------------------------- results.html */

const accByBasis = Object.entries(acc.by_basis || {}).map(([b, v]) => `<span class="pill">${esc(b)}: <b>${v.hits}/${v.tracked}</b></span>`).join("");
const resultsRows = endedM.map((m) => {
  const e = ledger[m.id];
  let pickCell = '<span class="small">— not tracked</span>';
  if (e) {
    if (e.settled) pickCell = `${esc(e.team)} <span class="badge ${e.settled.hit ? "hit" : "miss"}">${e.settled.hit ? "HIT ✓" : "MISS ✗"}</span> <span class="small">(${pct(e.p)}, ${esc(e.basis)})</span>`;
    else pickCell = `${esc(e.team)} <span class="badge state">pending</span> <span class="small">(${pct(e.p)}, ${esc(e.basis)})</span>`;
  }
  const winner = m.score0 > m.score1 ? m.team0.name : m.score1 > m.score0 ? m.team1.name : "—";
  return `<tr>
    <td>${fmtDT(m.start_ms)}</td>
    <td>${esc(m.competition)}</td>
    <td><a href="${esc(m.hotspawn_url)}" rel="noopener" target="_blank">${esc(m.team0.name)} ${m.score0}–${m.score1} ${esc(m.team1.name)}</a><br><span class="small">winner: <b>${esc(winner)}</b></span></td>
    <td>${pickCell}</td>
  </tr>`;
}).join("");
const resultsPage = `
<div class="hero">
  <h1>📈 Results &amp; pick accuracy</h1>
  <p class="sub">Settled Hotspawn LoL matches (current week onward) and how the picks we recorded before lock performed. Tracking accumulates with each 6-hourly run.</p>
</div>
<div class="kpis">
  <div class="kpi acc"><div class="n">${acc.tracked}</div><div class="l">Settled picks tracked</div></div>
  <div class="kpi good"><div class="n">${acc.hits}</div><div class="l">Correct</div></div>
  <div class="kpi"><div class="n">${acc.rate == null ? "—" : acc.rate + "%"}</div><div class="l">Hit rate</div></div>
  <div class="kpi"><div class="n">${endedM.length}</div><div class="l">Ended this week</div></div>
</div>
${accByBasis ? `<div class="pill-list">${accByBasis}</div>` : ""}
<section class="card">
  <h2>Settled matches</h2>
  <p class="desc">“Not tracked” = the match ended before this project recorded a pick for it (tracking started ${esc(Object.values(ledger).sort((a, b) => a.first_seen.localeCompare(b.first_seen))[0]?.first_seen?.slice(0, 10) || "—")}); accuracy stats only count tracked picks.</p>
  <div class="tablewrap"><table class="tbl">
    <thead><tr><th>Time (UTC)</th><th>Tournament</th><th>Match &amp; result</th><th>Our recorded pick</th></tr></thead>
    <tbody>${resultsRows || '<tr><td colspan="4" class="small">No settled matches recorded yet.</td></tr>'}</tbody>
  </table></div>
</section>`;

/* --------------------------------------------------------- tournaments.html */

const tourList = Object.values(tournaments || {}).sort((a, b) => b.open - a.open);
const tourCards = tourList.map((t) => {
  const rows = openM.filter((m) => m.competition === t.competition);
  const cid = rows[0]?.competition_id ?? "";
  const mkt = rows.filter((m) => m.market_pinnacle || m.market_polymarket).length;
  const mod = rows.filter((m) => m.pick && !m.market_pinnacle && !m.market_polymarket).length;
  const unr = rows.filter((m) => !m.pick).length;
  const next = rows.slice().sort((a, b) => (a.lock_ms ?? Infinity) - (b.lock_ms ?? Infinity))[0];
  return `<section class="card">
    <h2>${esc(t.competition)}</h2>
    <p class="desc">${t.tier && !/waiting/i.test(t.tier) ? `Tier ${esc(String(t.tier).toUpperCase())} · ` : ""}${t.open} open match${t.open === 1 ? "" : "es"}${next ? ` · next: ${fmtDT(next.start_ms)}` : ""}</p>
    <div class="pill-list">
      <span class="pill">Market lines: <b>${mkt}</b></span>
      <span class="pill">Own model: <b>${mod}</b></span>
      <span class="pill">Unresolved: <b>${unr}</b></span>
    </div>
    <p class="mb0"><a href="picks.html?tour=${esc(cid)}">View picks for this tournament →</a></p>
  </section>`;
}).join("");
const tournamentsPage = `
<div class="hero">
  <h1>🏆 Picks by tournament</h1>
  <p class="sub">Every Hotspawn LoL tournament with open matches, organized by category. Click through to the filtered pick list.</p>
</div>
${tourCards || '<p class="small">No open tournaments right now.</p>'}`;

/* --------------------------------------------------------- methodology.html */

const pinLeagues = pinLeaguesRaw;

const methodologyPage = `
<div class="hero">
  <h1>📖 Methodology &amp; sources</h1>
  <p class="sub">How every probability on this site is produced, verified, and refreshed — with links so you can check each step yourself.</p>
</div>

<section class="card">
  <h2>1. Match inventory (what we cover)</h2>
  <p class="desc">Primary: Hotspawn's own embedded public fixtures API — the same data play.hotspawn.com renders.</p>
  <ul style="color:var(--mut);font-size:14.5px;padding-left:20px">
    <li>Fixtures API: <a href="https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol" rel="noopener" target="_blank">phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol</a> — all LoL fixtures with status, tier, stage, lock time, points, participants, scores.</li>
    <li>SSR cross-check: <a href="https://play.hotspawn.com/lol-pickems" rel="noopener" target="_blank">play.hotspawn.com/lol-pickems</a> — rendered lobby; we scrape match permalinks + counts and reconcile against the API each run. Mismatches are flagged, never silently dropped.</li>
    <li>Open match = status <code>scheduled</code> with <code>lock_time</code> in the future. Every row links to its official Hotspawn match page.</li>
    <li><b>Not used as a probability input:</b> Hotspawn crowd “% picked”. It is collected for audit only and shown nowhere as a likelihood.</li>
  </ul>
</section>

<section class="card">
  <h2>2. Probability sources &amp; precedence</h2>
  <p class="desc">For each match we take the best available line. Order: sharpest book first, prediction market second, own model third.</p>
  <ol style="color:var(--mut);font-size:14.5px;padding-left:20px">
    <li><b>Pinnacle (market)</b> — guest odds API, no key needed:
      leagues <a href="https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues" rel="noopener" target="_blank">/0.1/sports/12/leagues</a> (filter <code>League of Legends *</code>${pinLeagues.length ? `; live now: ${esc(pinLeagues.join(", "))}` : ""}),
      matchups <code>/0.1/leagues/{id}/matchups</code>, moneylines <code>/0.1/leagues/{id}/markets/straight</code> (period 0 = series winner).
      American odds → decimal → implied, then <b>devig</b>: p(team) = (1/dec) / Σ(1/dec). Two-sided markets only; vig is removed proportionally.</li>
    <li><b>Polymarket (market)</b> — <a href="https://gamma-api.polymarket.com/events?closed=false&tag_slug=league-of-legends" rel="noopener" target="_blank">gamma-api.polymarket.com/events?closed=false&amp;tag_slug=league-of-legends</a>. Two-outcome team markets; probability = mid of best bid/ask when quoted, else last outcome prices, renormalized to 100%. Thin liquidity (&lt;$500) or wide spread (&gt;0.10) is flagged.</li>
    <li><b>Own model (originated line)</b> — Elo-style rating built exclusively from <b>actual results</b> in the Hotspawn fixtures archive (every ended LoL series with scores): E = 1/(1+10^((R_opp−R)/400)); K = 24 × margin-mult (1+0.25×(|Δgames|−1)) × recency 0.5^(age/365d). Predictions shrink toward 50% for thin history: p = 0.5 + (E−0.5)×min(1,(min(n)+2)/10), clamped to [3%,97%]. Ratings for every team: <a href="https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/model/ratings.json" rel="noopener" target="_blank">data/model/ratings.json</a>.</li>
  </ol>
  <p class="note mb0">The own-model line is computed for <b>every match with history</b> and shown alongside market lines — when both exist and disagree by &gt;25 points, the match is auto-flagged for review. The pick always follows the precedence above.</p>
</section>

<section class="card">
  <h2>3. Confidence labels</h2>
  <ul style="color:var(--mut);font-size:14.5px;padding-left:20px">
    <li><b>HIGH</b> — Pinnacle devigged line (sharp, high-limit book), or own model with ≥10 recorded series per side.</li>
    <li><b>MEDIUM</b> — Polymarket line with ≥$1,000 liquidity, or model with 3–9 series per side.</li>
    <li><b>LOW</b> — thin Polymarket market, or model with 1–2 series per side (early-season rosters).</li>
  </ul>
</section>

<section class="card">
  <h2>4. Refresh cadence &amp; pipeline</h2>
  <p class="desc">GitHub Actions runs every 6 hours (requirement: 4–8h) + on demand:</p>
  <ol style="color:var(--mut);font-size:14.5px;padding-left:20px">
    <li><b>collect</b> — fetch all four sources (3 retries each, browser UA); failures logged, pipeline degrades gracefully and flags gaps.</li>
    <li><b>analyze</b> — rebuild Elo from full results history, match markets to fixtures (exact normalized-name match first; fuzzy token similarity ≥0.66 + ±6h time window, and any fuzzy hit is flagged for review), generate picks + flags, update the pick ledger used for accuracy tracking.</li>
    <li><b>build</b> — render this static site (no client-side dependencies) and verify internal links.</li>
    <li><b>publish</b> — commit data + docs; GitHub Pages serves <code>docs/</code> from <code>main</code>. Run history: <a href="https://github.com/karagemop466-tech/LOLHOTSPAWN1/actions" rel="noopener" target="_blank">Actions log</a>.</li>
  </ol>
</section>

<section class="card">
  <h2>5. Verification policy</h2>
  <ul style="color:var(--mut);font-size:14.5px;padding-left:20px">
    <li>Every match row links to its official Hotspawn match page; every market line links to the exact Pinnacle matchup or Polymarket event.</li>
    <li>Values that cannot be confirmed from a source are left blank (“—”) and the match goes to <a href="unresolved.html">Unresolved</a> or <a href="flagged.html">Flagged</a> — never inferred.</li>
    <li>Inventory is reconciled against the rendered lobby each run; discrepancies are flagged with the specific IDs.</li>
  </ul>
</section>

<section class="card">
  <h2>6. Known limitations</h2>
  <ul style="color:var(--mut);font-size:14.5px;padding-left:20px">
    <li>Market coverage is concentrated on tier-1/2 events (${pinLeagues.length ? `Pinnacle currently prices: ${esc(pinLeagues.join(", "))}` : "Pinnacle coverage varies"}); hundreds of amateur-division matches have no market line anywhere we can verify.</li>
    <li>The own model measures teams as they appear in Hotspawn's archive — roster swaps, academy/main-team promotion, and smurf/stand-in games are invisible to it.</li>
    <li>Best-of-1 formats (most minor leagues) are high-variance; even correct probabilities lose often.</li>
    <li>Name matching across sources can mis-link similarly named teams; every fuzzy match is flagged for review rather than hidden.</li>
    <li>The Hotspawn SSR lobby is CDN-cached and occasionally 403s; the fixtures API is the authoritative inventory, the page is a cross-check.</li>
    <li>Polymarket prices move continuously; snapshots are point-in-time (timestamp on every page).</li>
  </ul>
</section>

<section class="card">
  <h2>7. Source register</h2>
  <div class="tablewrap"><table class="tbl">
    <thead><tr><th>Source</th><th>What it provides</th><th>Link</th></tr></thead>
    <tbody>
      <tr><td>Hotspawn fixtures API</td><td>Match inventory, tiers, lock times, full results history</td><td><a href="https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol" rel="noopener" target="_blank">api/v1/fixtures?sport_alias=lol</a></td></tr>
      <tr><td>Hotspawn LoL lobby</td><td>SSR cross-check, official match permalinks</td><td><a href="https://play.hotspawn.com/lol-pickems" rel="noopener" target="_blank">play.hotspawn.com/lol-pickems</a></td></tr>
      <tr><td>Pinnacle guest API</td><td>Sharp moneyline odds (devigged to probabilities)</td><td><a href="https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues" rel="noopener" target="_blank">guest.api.arcadia.pinnacle.com/0.1</a></td></tr>
      <tr><td>Polymarket gamma API</td><td>Prediction-market prices for major LoL matches</td><td><a href="https://gamma-api.polymarket.com/events?closed=false&tag_slug=league-of-legends" rel="noopener" target="_blank">gamma-api.polymarket.com</a></td></tr>
      <tr><td>Own Elo-style model</td><td>Originated line for matches without market coverage</td><td><a href="https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/model/ratings.json" rel="noopener" target="_blank">data/model/ratings.json</a></td></tr>
      <tr><td>Corroboration (not ingested)</td><td>Odds boards cross-checked manually during development</td><td><a href="https://bo5.gg/lol/betting/odds/" rel="noopener" target="_blank">bo5.gg</a> · <a href="https://egamersworld.com/lol/bets" rel="noopener" target="_blank">egamersworld.com/lol/bets</a></td></tr>
    </tbody>
  </table></div>
</section>`;

/* ------------------------------------------------------------------- render */

await mkdir(path.join(DOCS, "assets"), { recursive: true });
await mkdir(path.join(DOCS, "data"), { recursive: true });

const pages = [
  ["index.html", "LoL Hotspawn Picks — Executive Summary", indexBody, "Win probabilities and picks for every League of Legends match on the Hotspawn pick'em lobby, from Pinnacle/Polymarket lines and an own Elo-style model. Updated every 6 hours."],
  ["picks.html", "All Picks — LoL Hotspawn", picksPage, "Every open Hotspawn LoL match with win probabilities, the pick, and line sources."],
  ["unresolved.html", "Unresolved Picks — LoL Hotspawn", unresolvedPage, "Hotspawn LoL matches without a pick and the specific limitations behind each."],
  ["flagged.html", "Flagged for Review — LoL Hotspawn", flaggedPage, "Irregularities found by the automated pipeline, with source links."],
  ["results.html", "Results & Accuracy — LoL Hotspawn", resultsPage, "Settled Hotspawn LoL matches and recorded-pick accuracy."],
  ["tournaments.html", "Picks by Tournament — LoL Hotspawn", tournamentsPage, "Hotspawn LoL tournaments with open matches and coverage counts."],
  ["methodology.html", "Methodology & Sources — LoL Hotspawn", methodologyPage, "How probabilities are produced, verified and refreshed."],
];

for (const [file, title, body, desc] of pages) {
  await writeFile(path.join(DOCS, file), layout(title, file, body, desc));
}
await copyFile(path.join(ROOT, "data", "picks.json"), path.join(DOCS, "data", "picks.json"));

/* ------------------------------------------------------- internal link check */

let broken = 0;
for (const [file] of pages) {
  const html = await readFile(path.join(DOCS, file), "utf8");
  for (const m of html.matchAll(/href="([^"#]+)(#[^"]*)?"/g)) {
    const href = m[1];
    if (/^(https?:|mailto:|data:)/.test(href)) continue;
    const target = path.join(DOCS, href.split("?")[0]);
    try { await readFile(target); } catch {
      // missing local file
      console.error(`BROKEN LINK in ${file}: ${href}`);
      broken++;
    }
  }
}
console.log(`\nSite built: ${pages.length} pages into docs/ · open=${c.open} picks=${c.picks_total} unresolved=${c.unresolved_open} flags=${flagsData.flags.length}`);
if (broken) { console.error(`${broken} broken internal link(s).`); process.exit(1); }
