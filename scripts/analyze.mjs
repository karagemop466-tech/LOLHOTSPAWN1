#!/usr/bin/env node
/**
 * analyze.mjs — Stage 2 of the LoL Hotspawn pick'em pipeline.
 *
 * Inputs (from collect.mjs):
 *   data/raw/hotspawn_lol_fixtures.json   full LoL fixture list + history
 *   data/raw/hotspawn_lobby_check.json    SSR lobby cross-check (permalinks by id)
 *   data/raw/pinnacle_lol.json            Pinnacle moneylines (American odds)
 *   data/raw/polymarket_lol.json          Polymarket match markets
 *
 * Outputs:
 *   data/model/ratings.json               own Elo-style ratings (from real results)
 *   data/picks.json                       every match: state, market line, model line, pick, flags
 *   data/flags.json                       irregularities for the "Flagged for Review" page
 *   data/history/picks_latest.json        pick ledger for accuracy tracking after settlement
 *
 * Rules:
 *   - Hotspawn crowd "% picked" is NEVER used as a probability signal (requirement).
 *   - Hotspawn match RESULTS (final scores) are facts and are used to build our own
 *     Elo-style model, which originates an independent line for every match.
 *   - Pick source precedence: Pinnacle (devigged) > Polymarket (mid/last) > own model.
 *   - Anything unresolvable or irregular is flagged, never invented.
 */
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const RAW = path.join(ROOT, "data", "raw");
const NOW = Date.now();

/* ------------------------------------------------------------- small helpers */

const readJSON = async (p, fallback = null) => {
  try { return JSON.parse(await readFile(p, "utf8")); } catch { return fallback; }
};
const num = (x) => (x === null || x === undefined || x === "" ? null : Number(x));
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

function normName(s) {
  if (!s) return "";
  return (
    s
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/&/g, " and ")
      .replace(/[^a-z0-9]+/g, " ")
      .split(" ")
      .filter((t) => t && !["esports", "esport", "gaming", "team", "club"].includes(t))
      .join(" ")
      .trim()
  );
}
const tokens = (s) => new Set(normName(s).split(" ").filter(Boolean));
function jaccard(a, b) {
  const A = tokens(a), B = tokens(b);
  if (!A.size || !B.size) return 0;
  let inter = 0;
  for (const t of A) if (B.has(t)) inter++;
  return inter / (A.size + B.size - inter);
}
// character bigram Dice — catches near-miss spellings ("Sainz"/"Saints", "KOI"/"KOI")
function diceBigram(a, b) {
  if (a === b) return 1;
  if (a.length < 2 || b.length < 2) return 0;
  const bg = (s) => { const m = new Map(); for (let i = 0; i < s.length - 1; i++) { const g = s.slice(i, i + 2); m.set(g, (m.get(g) || 0) + 1); } return m; };
  const A = bg(a), B = bg(b);
  let inter = 0;
  for (const [g, cnt] of A) if (B.has(g)) inter += Math.min(cnt, B.get(g));
  return (2 * inter) / ((a.length - 1) + (b.length - 1));
}
// greedy token alignment scored by bigram Dice (handles typos + short tokens)
function tokenDiceSim(na, nb) {
  const ta = na.split(" ").filter(Boolean), tb = nb.split(" ").filter(Boolean);
  if (!ta.length || !tb.length) return 0;
  const used = new Set();
  let total = 0;
  for (const x of ta) {
    let best = 0, bi = -1;
    tb.forEach((y, i) => { if (used.has(i)) return; const d = diceBigram(x, y); if (d > best) { best = d; bi = i; } });
    if (bi >= 0) { used.add(bi); total += best; }
  }
  return total / Math.max(ta.length, tb.length);
}
function nameSim(a, b) {
  const na = normName(a), nb = normName(b);
  if (!na || !nb) return 0;
  if (na === nb) return 1;
  if ((na.includes(nb) || nb.includes(na)) && Math.min(na.length, nb.length) / Math.max(na.length, nb.length) >= 0.6) return 0.92;
  return Math.max(jaccard(a, b), tokenDiceSim(na, nb));
}
function slugify(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
const iso = (ms) => (ms ? new Date(ms).toISOString() : null);
const americanToDecimal = (a) => (a >= 0 ? 1 + a / 100 : 1 + 100 / Math.abs(a));

/* ------------------------------------------------------- load collected data */

const hsRaw = await readJSON(path.join(RAW, "hotspawn_lol_fixtures.json"));
if (!hsRaw || !Array.isArray(hsRaw.fixtures)) {
  console.error("FATAL: data/raw/hotspawn_lol_fixtures.json missing or malformed.");
  process.exit(2);
}
const lobby = await readJSON(path.join(RAW, "hotspawn_lobby_check.json"), null);
const pinnacle = await readJSON(path.join(RAW, "pinnacle_lol.json"), { leagues: [] });
const polymarket = await readJSON(path.join(RAW, "polymarket_lol.json"), { events: [] });

const fixtures = hsRaw.fixtures.map((f) => ({
  ...f,
  start_ms: num(f.scheduled_start_time) ?? (num(f.lock_time) ? num(f.lock_time) + 300000 : null),
  lock_ms: num(f.lock_time) ?? num(f.scheduled_start_time),
  t0: f.participants?.[0] ?? { id: "", name: "?" },
  t1: f.participants?.[1] ?? { id: "", name: "?" },
}));

const flags = [];
function flag(severity, title, detail, links = [], match_id = null) {
  flags.push({ severity, title, detail, links, match_id, ts: new Date(NOW).toISOString() });
}

/* ------------------------------------------------------- own Elo-style model */
/**
 * Built ONLY from actual played results (status=ended, scores present),
 * processed chronologically. Ratings keyed by hotspawn participant id.
 *   E = 1 / (1 + 10^((Ropp - R)/400))
 *   K_eff = 24 * mov * 0.5^(age_days/365)     mov = 1 + 0.25*(|game diff| - 1)
 * Prediction shrinks toward 50% when either side has little history:
 *   c = min(1, (min(n0,n1) + 2) / 10);  p = 0.5 + (E - 0.5) * c, clamped [3%, 97%]
 */
const ratings = new Map(); // id -> {r, n, name, last_ms}
function getRating(id, name) {
  if (!ratings.has(id)) ratings.set(id, { r: 1500, n: 0, name, last_ms: null });
  const e = ratings.get(id);
  if (name) e.name = name;
  return e;
}

const ended = fixtures
  .filter((f) => f.status === "ended" && f.start_ms && num(f.t0.score) != null && num(f.t1.score) != null && num(f.t0.score) !== num(f.t1.score))
  .sort((a, b) => a.start_ms - b.start_ms);

for (const f of ended) {
  const A = getRating(f.t0.id, f.t0.name);
  const B = getRating(f.t1.id, f.t1.name);
  const s0 = num(f.t0.score), s1 = num(f.t1.score);
  const E = 1 / (1 + Math.pow(10, (B.r - A.r) / 400));
  const S = s0 > s1 ? 1 : 0;
  const ageDays = Math.max(0, (NOW - f.start_ms) / 86400000);
  const mov = 1 + 0.25 * (Math.abs(s0 - s1) - 1);
  const K = 24 * mov * Math.pow(0.5, ageDays / 365);
  A.r = clamp(A.r + K * (S - E), 700, 2500);
  B.r = clamp(B.r + K * ((1 - S) - (1 - E)), 700, 2500);
  A.n++; B.n++;
  A.last_ms = f.start_ms; B.last_ms = f.start_ms;
}

function modelProb(f) {
  const A = ratings.get(f.t0.id) ?? { r: 1500, n: 0 };
  const B = ratings.get(f.t1.id) ?? { r: 1500, n: 0 };
  const info = Math.min(A.n, B.n);
  if (info === 0) return null; // no history for at least one side -> no model line
  const E = 1 / (1 + Math.pow(10, (B.r - A.r) / 400));
  const c = Math.min(1, (info + 2) / 10);
  const p0 = clamp(0.5 + (E - 0.5) * c, 0.03, 0.97);
  const confidence = info >= 10 ? "high" : info >= 3 ? "medium" : "low";
  return {
    p0: Math.round(p0 * 1000) / 1000,
    p1: Math.round((1 - p0) * 1000) / 1000,
    r0: Math.round(A.r), r1: Math.round(B.r), n0: A.n, n1: B.n,
    confidence,
  };
}

/* ---------------------------------------------------------- market: Pinnacle */

const pinnacleLines = []; // {teamA, teamB, startISO, pHome, pHomRaw, oddsHome, oddsAway, league, matchupId, url}
for (const lg of pinnacle.leagues || []) {
  const straightByMatch = new Map();
  for (const s of lg.straight || []) {
    if (s.period !== 0) continue; // period 0 = series/match winner
    const home = (s.prices || []).find((p) => p.designation === "home");
    const away = (s.prices || []).find((p) => p.designation === "away");
    if (!home || !away) continue;
    straightByMatch.set(s.matchupId, { home: home.price, away: away.price, cutoffAt: s.cutoffAt, status: s.status });
  }
  for (const m of lg.matchups || []) {
    if (m.type !== "matchup") continue;
    const parts = m.participants || [];
    const home = parts.find((p) => p.alignment === "home");
    const away = parts.find((p) => p.alignment === "away");
    if (!home || !away) continue;
    const line = straightByMatch.get(m.id);
    if (!line) continue;
    const dh = americanToDecimal(line.home);
    const da = americanToDecimal(line.away);
    const ih = 1 / dh, ia = 1 / da;
    pinnacleLines.push({
      teamHome: home.name, teamAway: away.name,
      startISO: m.startTime, start_ms: Date.parse(m.startTime ?? "") || null,
      pHome: ih / (ih + ia), pAway: ia / (ih + ia),
      oddsHome: line.home, oddsAway: line.away,
      decHome: Math.round(dh * 100) / 100, decAway: Math.round(da * 100) / 100,
      league: lg.name, league_id: lg.id, matchupId: m.id,
      bestOfX: m.bestOfX,
      // Pinnacle's web UI is a SPA without stable per-match URLs; the verifiable
      // source is the guest-API endpoint that serves this exact line.
      url: `https://guest.api.arcadia.pinnacle.com/0.1/leagues/${lg.id}/markets/straight`,
      matchups_url: `https://guest.api.arcadia.pinnacle.com/0.1/leagues/${lg.id}/matchups`,
      site_url: "https://www.pinnacle.com/en/esports",
    });
  }
}

/* --------------------------------------------------------- market: Polymarket */

const polyLines = [];
for (const ev of polymarket.events || []) {
  for (const m of ev.markets || []) {
    if (!m.outcomes || m.outcomes.length !== 2) continue;
    if (m.closed) continue;
    let prices = m.outcomePrices && m.outcomePrices.length === 2 ? m.outcomePrices : null;
    let p0 = null, p1 = null, kind = "outcomePrices";
    if (m.bestBid != null && m.bestAsk != null && m.bestBid > 0 && m.bestAsk < 1 && m.bestAsk >= m.bestBid) {
      p0 = (m.bestBid + m.bestAsk) / 2; p1 = 1 - p0; kind = "mid(bid/ask)";
    } else if (prices) {
      const s = prices[0] + prices[1];
      if (s > 0) { p0 = prices[0] / s; p1 = prices[1] / s; }
    }
    if (p0 == null) continue;
    const slugDate = (ev.slug.match(/(\d{4}-\d{2}-\d{2})/) || [])[1];
    polyLines.push({
      teamA: m.outcomes[0], teamB: m.outcomes[1],
      pA: p0, pB: p1, priceKind: kind,
      date: slugDate ?? (ev.endDate ? ev.endDate.slice(0, 10) : null),
      end_ms: ev.endDate ? Date.parse(ev.endDate) : null,
      volume: ev.volume ?? m.volume, liquidity: m.liquidity ?? ev.liquidity, spread: m.spread,
      eventTitle: ev.title, eventSlug: ev.slug, question: m.question,
      url: `https://polymarket.com/event/${ev.slug}`,
    });
  }
}

/* ------------------------------------------------- match markets to fixtures */

const weekStart = (() => { const d = new Date(NOW); const day = (d.getUTCDay() + 6) % 7; d.setUTCHours(0, 0, 0, 0); d.setUTCDate(d.getUTCDate() - day); return d.getTime(); })();
const weekEnd = weekStart + 7 * 86400000;

const openish = fixtures.filter((f) => f.status === "scheduled" && f.lock_ms && f.lock_ms > NOW - 3600000);
const TIME_WIN = 6 * 3600000;

function bestFixtureFor(nameA, nameB, startMs, pool) {
  let best = null;
  for (const f of pool) {
    const simAB = Math.min(nameSim(nameA, f.t0.name), nameSim(nameB, f.t1.name));
    const simBA = Math.min(nameSim(nameA, f.t1.name), nameSim(nameB, f.t0.name));
    const sim = Math.max(simAB, simBA);
    const flipped = simBA > simAB;
    if (sim < 0.66) continue;
    const dt = f.start_ms && startMs ? Math.abs(f.start_ms - startMs) : Number.MAX_SAFE_INTEGER;
    if (startMs && f.start_ms && dt > TIME_WIN) continue;
    const score = sim * 1e13 - dt;
    if (!best || score > best.score) best = { f, sim, flipped, dt, score };
  }
  return best;
}

const marketByFixture = new Map(); // fixture id -> {pinnacle?, polymarket?}
function putMarket(id, key, val) {
  if (!marketByFixture.has(id)) marketByFixture.set(id, {});
  marketByFixture.get(id)[key] = val;
}

for (const pl of pinnacleLines) {
  const hit = bestFixtureFor(pl.teamHome, pl.teamAway, pl.start_ms, openish);
  if (!hit) {
    flag("info", "Pinnacle line not matched to any Hotspawn fixture",
      `${pl.teamHome} vs ${pl.teamAway} (${pl.league}, ${pl.startISO}) — Pinnacle prices a match that is not (currently) in the Hotspawn open list. Not used.`,
      [pl.url]);
    continue;
  }
  const m = { ...pl };
  if (hit.flipped) {
    m.pHome = pl.pAway; m.pAway = pl.pHome;
    m.oddsHome = pl.oddsAway; m.oddsAway = pl.oddsHome;
    m.decHome = pl.decAway; m.decAway = pl.decHome;
    m.teamHome = pl.teamAway; m.teamAway = pl.teamHome;
    m.flipped = true;
  }
  m.match_quality = hit.sim >= 0.999 ? "exact" : `fuzzy(${hit.sim.toFixed(2)})`;
  putMarket(hit.f.id, "pinnacle", m);
  if (hit.sim < 0.999) {
    flag("needs-review", "Fuzzy name match: Pinnacle ↔ Hotspawn",
      `Pinnacle "${pl.teamHome} vs ${pl.teamAway}" matched Hotspawn fixture #${hit.f.id} "${hit.f.t0.name} vs ${hit.f.t1.name}" with similarity ${hit.sim.toFixed(2)}. Verify the teams are the same.`,
      [pl.url, `https://www.hotspawn.com/matches/x-${hit.f.id}`], hit.f.id);
  }
}

const polyUnmatched = [];
for (const pm of polyLines) {
  const startMs = pm.date ? Date.parse(pm.date + "T12:00:00Z") : pm.end_ms;
  const pool = openish.filter((f) => !marketByFixture.get(f.id)?.polymarket);
  let hit = bestFixtureFor(pm.teamA, pm.teamB, startMs, pool);
  if (!hit) {
    // Looser time window for Polymarket (event endDate can drift): ±36h, no start requirement
    const pool2 = openish;
    for (const f of pool2) {
      const sim = Math.max(
        Math.min(nameSim(pm.teamA, f.t0.name), nameSim(pm.teamB, f.t1.name)),
        Math.min(nameSim(pm.teamA, f.t1.name), nameSim(pm.teamB, f.t0.name))
      );
      if (sim >= 0.66 && f.start_ms && startMs && Math.abs(f.start_ms - startMs) <= 36 * 3600000) {
        if (!hit || sim > hit.sim) hit = { f, sim, flipped: nameSim(pm.teamA, f.t1.name) > nameSim(pm.teamA, f.t0.name), dt: Math.abs(f.start_ms - startMs) };
      }
    }
  }
  if (!hit) { polyUnmatched.push(pm); continue; } // Polymarket lists markets beyond hotspawn's slate; aggregated info flag below
  const m = { ...pm };
  if (hit.flipped) { m.pA = pm.pB; m.pB = pm.pA; m.teamA = pm.teamB; m.teamB = pm.teamA; m.flipped = true; }
  m.match_quality = hit.sim >= 0.999 ? "exact" : `fuzzy(${hit.sim.toFixed(2)})`;
  putMarket(hit.f.id, "polymarket", m);
  if (hit.sim < 0.999) {
    flag("needs-review", "Fuzzy name match: Polymarket ↔ Hotspawn",
      `Polymarket "${pm.teamA} vs ${pm.teamB}" (${pm.eventSlug}) matched fixture #${hit.f.id} "${hit.f.t0.name} vs ${hit.f.t1.name}" with similarity ${hit.sim.toFixed(2)}.`,
      [pm.url], hit.f.id);
  }
}
if (polyUnmatched.length) {
  flag("info", "Polymarket markets with no matching Hotspawn fixture",
    `${polyUnmatched.length} open Polymarket LoL market(s) did not correspond to any open Hotspawn fixture (Polymarket lists events outside the Hotspawn slate, or naming differs): ${polyUnmatched.slice(0, 10).map((p) => p.eventSlug).join(", ")}${polyUnmatched.length > 10 ? "…" : ""}. These are NOT used for any pick.`,
    polyUnmatched.slice(0, 5).map((p) => p.url));
}

/* ------------------------------------------------------- classify + build rows */

const permalinks = new Map(Object.entries(lobby?.permalinks ?? {})); // id -> url (scraped from SSR lobby)
function hotspawnUrl(f) {
  if (permalinks.has(f.id)) return { url: permalinks.get(f.id), constructed: false };
  const slug = `${slugify(f.t0.name)}-vs-${slugify(f.t1.name)}-${slugify(f.competition_name)}-${f.id}`;
  return { url: `https://www.hotspawn.com/matches/${slug}`, constructed: true };
}

function stateOf(f) {
  if (f.status === "ended") return "ended";
  if (f.status === "cancelled") return "cancelled";
  if (f.status === "scheduled") {
    if (f.lock_ms && f.lock_ms > NOW) return "open";
    return "locked";
  }
  if (["live", "inprogress", "in_progress", "started", "running"].includes(f.status)) return "live";
  return "unknown";
}

const rows = [];
for (const f of fixtures) {
  const state = stateOf(f);
  const inWeek = f.start_ms && f.start_ms >= weekStart && f.start_ms < weekEnd + 3 * 86400000;
  if (state === "ended" && f.start_ms && f.start_ms < weekStart) continue; // history (used by model only)
  if (state === "unknown") flag("needs-review", "Unknown fixture status", `Fixture #${f.id} ${f.t0.name} vs ${f.t1.name} has status "${f.status}" — not classified.`, [], f.id);
  const mk = marketByFixture.get(f.id) ?? {};
  const model = modelProb(f);
  const link = hotspawnUrl(f);
  rows.push({ f, state, inWeek, mk, model, link });
}

/* ------------------------------------------------------------- picks + flags */

const picks = [];
for (const r of rows) {
  const { f, state, mk, model, link } = r;
  const pin = mk.pinnacle ?? null;
  const poly = mk.polymarket ?? null;

  let basis = null, p0 = null, p1 = null, confidence = null;
  if (pin) {
    basis = "market-pinnacle";
    p0 = pin.pHome; p1 = pin.pAway;
    confidence = "high";
  } else if (poly) {
    basis = "market-polymarket";
    p0 = poly.pA; p1 = poly.pB;
    const liq = Number(poly.liquidity ?? poly.volume ?? 0);
    confidence = liq >= 1000 ? "medium" : "low";
    if (liq < 500) {
      flag("needs-review", "Thin Polymarket market used as line",
        `${f.t0.name} vs ${f.t1.name}: Polymarket market "${poly.eventSlug}" has liquidity/volume ≈ $${Math.round(liq)} — line may be unreliable.`,
        [poly.url, link.url], f.id);
    }
    if (poly.spread != null && poly.spread > 0.1) {
      flag("info", "Wide Polymarket spread", `${f.t0.name} vs ${f.t1.name}: spread ${poly.spread}.`, [poly.url], f.id);
    }
  } else if (model) {
    basis = "model-elo";
    p0 = model.p0; p1 = model.p1;
    confidence = model.confidence;
  }

  // cross-source divergence checks
  if (pin && model && Math.abs(pin.pHome - model.p0) > 0.25) {
    flag("needs-review", "Large divergence: Pinnacle vs own model",
      `${f.t0.name} vs ${f.t1.name}: Pinnacle implies ${Math.round(pin.pHome * 100)}% for ${pin.teamHome}, own model ${Math.round(model.p0 * 100)}% for ${f.t0.name}. Pick follows the market line; divergence may signal roster/news the model can't see (or a matching error).`,
      [pin.url, link.url], f.id);
  }
  if (pin && poly && Math.abs(pin.pHome - poly.pA) > 0.15) {
    flag("needs-review", "Large divergence: Pinnacle vs Polymarket",
      `${f.t0.name} vs ${f.t1.name}: Pinnacle ${Math.round(pin.pHome * 100)}% vs Polymarket ${Math.round(poly.pA * 100)}% for the same side. Pick follows Pinnacle (sharper book).`,
      [pin.url, poly.url, link.url], f.id);
  }
  if (state === "open" && !basis) {
    flag("needs-review", "UNRESOLVED: no market line and no model line",
      `${f.t0.name} vs ${f.t1.name} (${f.competition_name}, ${iso(f.start_ms)}): no bookmaker/prediction-market line found and neither team has any recorded match history in the Hotspawn results archive, so no independent probability can be originated without guessing. See Unresolved Picks page.`,
      [link.url], f.id);
  }
  if (state === "open" && basis === "model-elo" && model.confidence === "low") {
    flag("info", "Low-confidence model pick",
      `${f.t0.name} vs ${f.t1.name}: based on ${model.n0}/${model.n1} recorded series only.`,
      [link.url], f.id);
  }

  let pick = null;
  if (basis && p0 != null && (state === "open" || state === "locked" || state === "live")) {
    const side = p0 >= p1 ? 0 : 1;
    const pp = side === 0 ? p0 : p1;
    pick = {
      team_index: side,
      team_id: side === 0 ? f.t0.id : f.t1.id,
      team: side === 0 ? f.t0.name : f.t1.name,
      p: Math.round(pp * 1000) / 1000,
      basis,
      confidence: basis === "model-elo" ? model.confidence : confidence,
      margin: Math.round(Math.abs(p0 - p1) * 1000) / 1000,
    };
  }

  picks.push({
    id: f.id,
    state,
    competition_id: f.competition_id,
    competition: f.competition_name,
    tier: f.tier,
    stage: f.stage,
    offered_points: num(f.offered_points),
    start_utc: iso(f.start_ms),
    lock_utc: iso(f.lock_ms),
    start_ms: f.start_ms,
    lock_ms: f.lock_ms,
    team0: { id: f.t0.id, name: f.t0.name },
    team1: { id: f.t1.id, name: f.t1.name },
    team_history: {
      n0: ratings.get(f.t0.id)?.n ?? 0,
      n1: ratings.get(f.t1.id)?.n ?? 0,
    },
    score0: state === "ended" ? num(f.t0.score) : null,
    score1: state === "ended" ? num(f.t1.score) : null,
    hotspawn_url: link.url,
    hotspawn_url_constructed: link.constructed,
    market_pinnacle: pin ? {
      source: "Pinnacle", url: pin.url, matchups_url: pin.matchups_url, site_url: pin.site_url,
      league: pin.league, league_id: pin.league_id, matchup_id: pin.matchupId,
      odds0: pin.oddsHome, odds1: pin.oddsAway, dec0: pin.decHome, dec1: pin.decAway,
      p0: Math.round(pin.pHome * 1000) / 1000, p1: Math.round(pin.pAway * 1000) / 1000,
      match_quality: pin.match_quality, best_of: pin.bestOfX,
    } : null,
    market_polymarket: poly ? {
      source: "Polymarket", url: poly.url, event: poly.eventSlug, question: poly.question,
      p0: Math.round(poly.pA * 1000) / 1000, p1: Math.round(poly.pB * 1000) / 1000,
      price_kind: poly.priceKind, liquidity: poly.liquidity, volume: poly.volume, spread: poly.spread,
      match_quality: poly.match_quality,
    } : null,
    model: model ? {
      source: "own Elo-style model (Hotspawn results archive)",
      p0: model.p0, p1: model.p1, r0: model.r0, r1: model.r1, n0: model.n0, n1: model.n1,
      confidence: model.confidence,
    } : null,
    pick,
  });
}

/* ---------------------------------------------------------- inventory checks */

if (lobby && Array.isArray(lobby.match_ids) && lobby.match_ids.length) {
  const apiOpen = new Set(picks.filter((p) => p.state === "open" || p.state === "locked" || p.state === "live").map((p) => p.id));
  const lobbyIds = new Set(lobby.match_ids.map(String));
  const missingFromApi = [...lobbyIds].filter((id) => !apiOpen.has(id) && !picks.some((p) => p.id === id));
  if (missingFromApi.length) {
    flag("needs-review", "Lobby lists matches absent from fixtures API",
      `SSR lobby permalinks reference ids not returned by the fixtures API: ${missingFromApi.slice(0, 12).join(", ")}${missingFromApi.length > 12 ? "…" : ""}. Inventory may be incomplete.`,
      ["https://play.hotspawn.com/lol-pickems"]);
  }
} else if (!lobby) {
  flag("info", "Lobby SSR cross-check unavailable",
    "play.hotspawn.com/lol-pickems could not be fetched this run (soft failure); inventory relies on the fixtures API alone.",
    ["https://play.hotspawn.com/lol-pickems"]);
}

const openCount = picks.filter((p) => p.state === "open").length;
const resolvedCount = picks.filter((p) => p.state === "open" && p.pick).length;
if (openCount > 0 && resolvedCount === 0) {
  flag("needs-review", "ZERO resolved picks", "No open match received a market or model line this run — likely a data-source outage. Investigate before trusting the site.", []);
}

/* ------------------------------------------------------ pick ledger (history) */

const ledgerPath = path.join(ROOT, "data", "history", "picks_latest.json");
const ledger = (await readJSON(ledgerPath, {})) ?? {};
for (const p of picks) {
  if (!p.pick) continue;
  const prev = ledger[p.id];
  const entry = {
    first_seen: prev?.first_seen ?? new Date(NOW).toISOString(),
    last_updated: new Date(NOW).toISOString(),
    team_index: p.pick.team_index,
    team: p.pick.team,
    p: p.pick.p,
    basis: p.pick.basis,
    lock_utc: p.lock_utc,
    start_utc: p.start_utc,
    competition: p.competition,
    t0: p.team0.name, t1: p.team1.name,
    changes: (prev?.changes ?? 0) + (prev && prev.team_index !== p.pick.team_index ? 1 : 0),
  };
  ledger[p.id] = entry;
}
// settle ended matches, prune old
for (const [id, e] of Object.entries(ledger)) {
  const row = picks.find((p) => p.id === id);
  if (row && row.state === "ended") {
    const s0 = row.score0, s1 = row.score1;
    if (s0 != null && s1 != null && s0 !== s1) {
      const winner = s0 > s1 ? 0 : 1;
      e.settled = { winner_index: winner, winner: winner === 0 ? row.team0.name : row.team1.name, score: `${s0}-${s1}`, hit: winner === e.team_index };
    }
    if (row.start_ms && row.start_ms < NOW - 21 * 86400000) delete ledger[id];
  } else if (!row && e.start_utc && Date.parse(e.start_utc) < NOW - 21 * 86400000) {
    delete ledger[id];
  }
}

/* ------------------------------------------------------------------- outputs */

await mkdir(path.join(ROOT, "data", "model"), { recursive: true });
await mkdir(path.join(ROOT, "data", "history"), { recursive: true });

const ratingsOut = {};
for (const [id, e] of ratings) ratingsOut[id] = { name: e.name, r: Math.round(e.r), n: e.n, last: iso(e.last_ms) };
await writeFile(path.join(ROOT, "data", "model", "ratings.json"), JSON.stringify({ generated_at: iso(NOW), method: "Elo-style, K=24*mov*0.5^(age/365d), built from Hotspawn results archive (facts), shrinkage toward 50% for thin history", teams: ratingsOut }, null, 1));

const tournaments = {};
for (const p of picks) {
  if (!["open", "locked", "live"].includes(p.state)) continue;
  const t = (tournaments[p.competition] ??= { competition: p.competition, tier: p.tier, open: 0, resolved: 0, market: 0, model: 0 });
  t.open++;
  if (p.pick) t.resolved++;
  if (p.market_pinnacle || p.market_polymarket) t.market++;
  else if (p.model) t.model++;
}

const settledEntries = Object.values(ledger).filter((e) => e.settled);
const hitEntries = settledEntries.filter((e) => e.settled.hit);
const accuracy = {
  tracked: settledEntries.length,
  hits: hitEntries.length,
  rate: settledEntries.length ? Math.round((hitEntries.length / settledEntries.length) * 1000) / 10 : null,
  by_basis: {},
};
for (const e of settledEntries) {
  const b = (accuracy.by_basis[e.basis] ??= { tracked: 0, hits: 0 });
  b.tracked++;
  if (e.settled.hit) b.hits++;
}

const summary = {
  generated_at: iso(NOW),
  week: { start: iso(weekStart), end: iso(weekEnd) },
  accuracy,
  counts: {
    open: picks.filter((p) => p.state === "open").length,
    locked_or_live: picks.filter((p) => ["locked", "live"].includes(p.state)).length,
    ended_this_week: picks.filter((p) => p.state === "ended").length,
    cancelled: picks.filter((p) => p.state === "cancelled").length,
    picks_total: picks.filter((p) => p.pick).length,
    market_pinnacle: picks.filter((p) => p.market_pinnacle).length,
    market_polymarket_only: picks.filter((p) => !p.market_pinnacle && p.market_polymarket).length,
    model_only: picks.filter((p) => p.pick?.basis === "model-elo").length,
    unresolved_open: picks.filter((p) => p.state === "open" && !p.pick).length,
    flags_needs_review: flags.filter((x) => x.severity === "needs-review").length,
    flags_info: flags.filter((x) => x.severity === "info").length,
  },
  sources_ok: {
    hotspawn_fixtures: !!hsRaw,
    hotspawn_lobby: !!lobby,
    pinnacle_leagues: (pinnacle.leagues || []).length,
    pinnacle_lines: pinnacleLines.length,
    polymarket_lines: polyLines.length,
  },
};

await writeFile(path.join(ROOT, "data", "picks.json"), JSON.stringify({ summary, tournaments, matches: picks }, null, 1));
await writeFile(path.join(ROOT, "data", "flags.json"), JSON.stringify({ generated_at: iso(NOW), flags }, null, 1));
await writeFile(ledgerPath, JSON.stringify(ledger, null, 1));

// accuracy stats from ledger
const settled = Object.values(ledger).filter((e) => e.settled);
const hits = settled.filter((e) => e.settled.hit).length;
console.log(`\nAnalyze summary: ${JSON.stringify(summary.counts)}\nSettled tracked picks: ${settled.length}, hits: ${hits}`);
console.log(`Models built for ${ratings.size} teams from ${ended.length} ended fixtures.`);
