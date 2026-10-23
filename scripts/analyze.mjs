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
const DATA = path.join(ROOT, "data", "node");
const RAW = path.join(DATA, "raw");
const NOW = Date.now();

/* ------------------------------------------------------------- small helpers */

const readJSON = async (p, fallback = null) => {
  try { return JSON.parse(await readFile(p, "utf8")); } catch { return fallback; }
};
const num = (x) => (x === null || x === undefined || x === "" ? null : Number(x));
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

// Fold characters that NFD does NOT decompose (Ø, Æ, Œ, Đ, Ł, Þ, ß …) before stripping.
const CHAR_FOLD = { "ø": "o", "æ": "ae", "œ": "oe", "ß": "ss", "đ": "d", "ð": "d", "ł": "l", "þ": "th", "ı": "i", "ŀ": "l" };
// Conservative alias table for well-established LoL orgs whose short tags appear in
// some sources (Pinnacle/Polymarket) and full names in others (Hotspawn archive).
// Applied AFTER token filtering; only exact full-string matches are folded.
const ALIASES = {
  hle: "hanwha life", blg: "bilibili gaming", ig: "invictus gaming", tes: "top esports",
  jdg: "jd gaming", edg: "edward gaming", wbg: "weibo gaming", fpx: "funplus phoenix",
  rng: "royal never give up", kt: "kt rolster", dk: "dplus kia", al: "anyone s legend",
  cfo: "ctbc flying oyster", kc: "karmine corp", mkoi: "movistar koi", tsw: "secret whales",
  "team secret whales": "secret whales", drx: "drx", brion: "brion esports",
  "gen g": "gen g", t1: "t1", g2: "g2",
};
function normName(s) {
  if (!s) return "";
  const folded = s.toLowerCase().replace(/[øæœßđðłþıŀ]/g, (ch) => CHAR_FOLD[ch] ?? ch);
  const base = folded
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, " ")
    .split(" ")
    .filter((t) => t && !["esports", "esport", "gaming", "team", "club"].includes(t))
    .join(" ")
    .trim();
  return ALIASES[base] ?? base;
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
// Ratings are keyed by NORMALIZED NAME, not participant id: the Hotspawn archive
// contains duplicate participant ids for the same org (e.g. "Gen.G" vs "Gen.G Esports"
// across seasons), which would fragment history. normName + alias folding unifies them.
const ratingKey = (id, name) => normName(name) || `id:${id}`;
const ratings = new Map(); // key -> {r, n, name, last_ms}
function getRating(id, name) {
  const k = ratingKey(id, name);
  if (!ratings.has(k)) ratings.set(k, { r: 1500, n: 0, name, last_ms: null });
  const e = ratings.get(k);
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
  const A = ratings.get(ratingKey(f.t0.id, f.t0.name)) ?? { r: 1500, n: 0 };
  const B = ratings.get(ratingKey(f.t1.id, f.t1.name)) ?? { r: 1500, n: 0 };
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
      listing: lg.matchups_source ?? "live",
      // Pinnacle's web UI is a SPA without stable per-match URLs; the verifiable
      // source is the guest-API endpoint that serves this exact line.
      url: `https://guest.api.arcadia.pinnacle.com/0.1/leagues/${lg.id}/markets/straight`,
      matchups_url: `https://guest.api.arcadia.pinnacle.com/0.1/leagues/${lg.id}/matchups`,
      site_url: "https://www.pinnacle.com/en/esports",
    });
  }

  // Fallback: when the /matchups listing failed (Pinnacle guest API
  // intermittently returns 401), reconstruct head-to-head pairs directly from
  // the straight odds lines: two moneyline entries sharing a matchupId carry
  // the two participant names between them, and each entry's prices carry
  // home/away designation + participantId. Odds remain 100% official Pinnacle
  // data; only startTime/bestOf metadata is unavailable on reconstructed rows.
  const coveredIds = new Set((lg.matchups || []).map((m) => m.id));
  const rebuild = new Map();
  for (const s of lg.straight || []) {
    if (s.period !== 0 || coveredIds.has(s.matchupId)) continue;
    if (!rebuild.has(s.matchupId)) rebuild.set(s.matchupId, []);
    rebuild.get(s.matchupId).push(s);
  }
  for (const [mid, rows] of rebuild) {
    // names come from per-side odds rows (type 0), which carry participants[]
    // and prices[].participantId + home/away designation
    const namesById = new Map();
    for (const s of rows) for (const p of s.participants || []) if (p.id != null && p.name) namesById.set(String(p.id), p.name);
    const usable = rows.filter((s) => s.liveUp !== true);
    const side = (desig) => {
      for (const s of usable) for (const pr of s.prices || []) {
        if (pr.designation === desig && pr.price != null && pr.participantId != null && namesById.has(String(pr.participantId))) {
          return { price: pr.price, name: namesById.get(String(pr.participantId)) };
        }
      }
      return null;
    };
    const h = side("home"), a = side("away");
    if (!h || !a || h.name === a.name) continue; // never infer ambiguous pairs
    const dh = americanToDecimal(h.price);
    const da = americanToDecimal(a.price);
    const ih = 1 / dh, ia = 1 / da;
    pinnacleLines.push({
      teamHome: h.name, teamAway: a.name,
      startISO: null, start_ms: null,
      pHome: ih / (ih + ia), pAway: ia / (ih + ia),
      oddsHome: h.price, oddsAway: a.price,
      decHome: Math.round(dh * 100) / 100, decAway: Math.round(da * 100) / 100,
      league: lg.name, league_id: lg.id, matchupId: mid,
      bestOfX: null,
      listing: "none (reconstructed from odds lines)",
      reconstructed_from_lines: true,
      url: `https://guest.api.arcadia.pinnacle.com/0.1/leagues/${lg.id}/markets/straight`,
      matchups_url: `https://guest.api.arcadia.pinnacle.com/0.1/leagues/${lg.id}/matchups`,
      site_url: "https://www.pinnacle.com/en/esports",
    });
  }
}
if (pinnacleLines.some((l) => l.reconstructed_from_lines)) {
  console.error(`Reconstructed ${pinnacleLines.filter((l) => l.reconstructed_from_lines).length} Pinnacle line(s) from straight odds (matchups endpoint unavailable).`);
}

/* --------------------------------------------------------- market: Polymarket */

const polyLines = [];
const SUBMARKET_RE = /game\s*\d|map\s*\d|handicap|total|first|kills?|dragon|baron|turret|tower/i;
for (const ev of polymarket.events || []) {
  // One series-moneyline market per event: drop per-game/prop sub-markets,
  // prefer a question that looks like "A vs. B".
  const cands = (ev.markets || []).filter(
    (m) => m.outcomes?.length === 2 && !m.closed && !SUBMARKET_RE.test(m.question || "")
  );
  if (!cands.length) continue;
  cands.sort((a, b) => (/ vs\.? /i.test(b.question || "") ? 1 : 0) - (/ vs\.? /i.test(a.question || "") ? 1 : 0));
  const m = cands[0];
  const prices = m.outcomePrices && m.outcomePrices.length === 2 ? m.outcomePrices : null;
  let p0 = null, p1 = null, kind = "outcomePrices";
  const spread = m.spread != null ? Number(m.spread) : null;
  // Mid of book only when the book is tight; otherwise renormalized last/outcome prices.
  if (spread != null && spread <= 0.06 && m.bestBid != null && m.bestAsk != null && m.bestBid > 0 && m.bestAsk < 1 && m.bestAsk >= m.bestBid) {
    p0 = (m.bestBid + m.bestAsk) / 2; p1 = 1 - p0; kind = `mid(bid/ask, spread ${spread})`;
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
    volume: ev.volume ?? m.volume, liquidity: m.liquidity ?? ev.liquidity, spread,
    eventTitle: ev.title, eventSlug: ev.slug, question: m.question,
    url: `https://polymarket.com/event/${ev.slug}`,
  });
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
  const uniqSlugs = [...new Set(polyUnmatched.map((p) => p.eventSlug))];
  flag("info", "Polymarket markets with no matching Hotspawn fixture",
    `${uniqSlugs.length} open Polymarket LoL event(s) did not correspond to any open Hotspawn fixture (Polymarket lists events outside the Hotspawn slate, or naming differs): ${uniqSlugs.slice(0, 10).join(", ")}${uniqSlugs.length > 10 ? "…" : ""}. These are NOT used for any pick.`,
    uniqSlugs.slice(0, 5).map((s) => `https://polymarket.com/event/${s}`));
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
  if (f.status === "forfeited") return "forfeited";
  if (f.status === "cancelled") return "cancelled";
  if (f.status === "scheduled") {
    if (f.lock_ms && f.lock_ms > NOW) return "open";
    // Lock passed but still "scheduled": either about to start / in progress,
    // or a stale zombie fixture Hotspawn never settled (>24h past start).
    if (f.start_ms && f.start_ms < NOW - 24 * 3600000) return "stale";
    return "locked";
  }
  if (["live", "inprogress", "in_progress", "started", "running"].includes(f.status)) return "live";
  return "unknown";
}

const rows = [];
const staleList = [];
for (const f of fixtures) {
  const state = stateOf(f);
  const inWeek = f.start_ms && f.start_ms >= weekStart && f.start_ms < weekEnd + 3 * 86400000;
  if ((state === "ended" || state === "forfeited") && f.start_ms && f.start_ms < weekStart) continue; // history (used by model only)
  if (state === "cancelled" && !(f.start_ms && f.start_ms >= weekStart && f.start_ms < weekEnd)) continue; // show only this week's cancellations
  if (state === "stale") { staleList.push(f); } // kept in data for audit, excluded from pick display
  if (state === "unknown") flag("needs-review", "Unknown fixture status", `Fixture #${f.id} ${f.t0.name} vs ${f.t1.name} has status "${f.status}" — not classified.`, [], f.id);
  const mk = marketByFixture.get(f.id) ?? {};
  const model = modelProb(f);
  const link = hotspawnUrl(f);
  rows.push({ f, state, inWeek, mk, model, link });
}

/* ------------------------------------------------------------- picks + flags */

const picks = [];
const lowConf = [];
for (const r of rows) {
  const { f, state, mk, model, link } = r;
  const pin = mk.pinnacle ?? null;
  const poly = mk.polymarket ?? null;

  // cross-source start-time discrepancy (Hotspawn schedule metadata has proven
  // unreliable for some events; Pinnacle/Polymarket independently corroborated
  // different start times — e.g. Worlds 2026 group stage, verified 2026-10-21)
  let startDiscrepancy = null;
  if (pin && pin.start_ms && f.start_ms) {
    const deltaMin = Math.round((pin.start_ms - f.start_ms) / 60000);
    if (Math.abs(deltaMin) > 90) {
      startDiscrepancy = { hotspawn_utc: iso(f.start_ms), pinnacle_utc: iso(pin.start_ms), delta_min: deltaMin };
      if (state === "open") {
        flag("needs-review", "Start-time discrepancy: Hotspawn vs Pinnacle",
          `${f.t0.name} vs ${f.t1.name} (${f.competition_name}): Hotspawn lists start ${iso(f.start_ms)} UTC (pick lock ${iso(f.lock_ms)} UTC), Pinnacle lists ${iso(pin.start_ms)} UTC (Δ ${deltaMin > 0 ? "+" : ""}${deltaMin} min). The Hotspawn lock still governs pick'em submission, but the real-world start time per the independent market source differs — displayed times may be wrong on one of the platforms.`,
          [pin.url, link.url], f.id);
      }
    }
  }

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
    lowConf.push({ id: f.id, name: `${f.t0.name} vs ${f.t1.name}`, comp: f.competition_name, n0: model.n0, n1: model.n1, url: link.url });
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
    forfeit: state === "forfeited",
    competition_id: f.competition_id,
    competition: f.competition_name,
    tier: f.tier,
    stage: f.stage,
    offered_points: num(f.offered_points),
    start_utc: iso(f.start_ms),
    lock_utc: iso(f.lock_ms),
    start_ms: f.start_ms,
    lock_ms: f.lock_ms,
    start_discrepancy: startDiscrepancy,
    team0: { id: f.t0.id, name: f.t0.name },
    team1: { id: f.t1.id, name: f.t1.name },
    team_history: {
      n0: ratings.get(ratingKey(f.t0.id, f.t0.name))?.n ?? 0,
      n1: ratings.get(ratingKey(f.t1.id, f.t1.name))?.n ?? 0,
    },
    // Final scores are facts for both settled states: Hotspawn records official
    // walkover scores on forfeited fixtures too (verified live 2026-10-23:
    // #1071216 participants0_score=0 / participants1_score=1). Mapping them lets
    // the ledger grade forfeits instead of leaving the pick "pending" forever.
    score0: (state === "ended" || state === "forfeited") ? num(f.t0.score) : null,
    score1: (state === "ended" || state === "forfeited") ? num(f.t1.score) : null,
    hotspawn_url: link.url,
    hotspawn_url_constructed: link.constructed,
    market_pinnacle: pin ? {
      source: "Pinnacle", url: pin.url, matchups_url: pin.matchups_url, site_url: pin.site_url,
      league: pin.league, league_id: pin.league_id, matchup_id: pin.matchupId,
      odds0: pin.oddsHome, odds1: pin.oddsAway, dec0: pin.decHome, dec1: pin.decAway,
      p0: Math.round(pin.pHome * 1000) / 1000, p1: Math.round(pin.pAway * 1000) / 1000,
      match_quality: pin.match_quality, best_of: pin.bestOfX,
      listing: pin.listing ?? "live",
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

/* ------------------------------------------------- aggregated info: low-conf */
if (lowConf.length) {
  flag("info", `${lowConf.length} model-only picks have LOW confidence (thin history)`,
    `These picks come solely from our own Elo-style model where one or both sides have fewer than 3 recorded series (new season, new rosters, amateur divisions). They are shown with a LOW badge on the Picks page. Examples: ${lowConf.slice(0, 12).map((x) => `${x.name} (${x.n0}/${x.n1} series)`).join("; ")}${lowConf.length > 12 ? "; …" : ""}.`,
    lowConf.slice(0, 8).map((x) => x.url));
}
if (staleList.length) {
  flag("info", `${staleList.length} stale Hotspawn fixtures excluded from picks`,
    `These fixtures still carry status "scheduled" although their start time passed more than 24h ago (Hotspawn never settled or cancelled them — likely postponed/abandoned, e.g. ${staleList.slice(0, 4).map((f) => `${f.t0.name} v ${f.t1.name} (${f.competition_name}, ${iso(f.start_ms)})`).join("; ")}). They cannot be picked on Hotspawn (lock passed) and are excluded from the site's match lists; kept in data/picks.json with state="stale" for audit.`,
    ["https://play.hotspawn.com/lol-pickems"]);
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

const ledgerPath = path.join(DATA, "history", "picks_latest.json");
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
  if (row && (row.state === "ended" || row.state === "forfeited")) {
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

await mkdir(path.join(DATA, "model"), { recursive: true });
await mkdir(path.join(DATA, "history"), { recursive: true });

const ratingsOut = {};
for (const [id, e] of ratings) ratingsOut[id] = { name: e.name, r: Math.round(e.r), n: e.n, last: iso(e.last_ms) };
await writeFile(path.join(DATA, "model", "ratings.json"), JSON.stringify({ generated_at: iso(NOW), method: "Elo-style, K=24*mov*0.5^(age/365d), built from Hotspawn results archive (facts), shrinkage toward 50% for thin history", teams: ratingsOut }, null, 1));

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
    stale: picks.filter((p) => p.state === "stale").length,
    ended_this_week: picks.filter((p) => ["ended", "forfeited"].includes(p.state)).length,
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

await writeFile(path.join(DATA, "picks.json"), JSON.stringify({ summary, tournaments, matches: picks }, null, 1));
await writeFile(path.join(DATA, "flags.json"), JSON.stringify({ generated_at: iso(NOW), flags }, null, 1));
await writeFile(ledgerPath, JSON.stringify(ledger, null, 1));

// accuracy stats from ledger
const settled = Object.values(ledger).filter((e) => e.settled);
const hits = settled.filter((e) => e.settled.hit).length;
console.log(`\nAnalyze summary: ${JSON.stringify(summary.counts)}\nSettled tracked picks: ${settled.length}, hits: ${hits}`);
console.log(`Models built for ${ratings.size} teams from ${ended.length} ended fixtures.`);
