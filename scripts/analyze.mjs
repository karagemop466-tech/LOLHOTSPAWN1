#!/usr/bin/env node
/**
 * analyze.mjs — Stage 2 of the LoL Hotspawn pick'em Node pipeline (docs/).
 *
 * Reads data/node/raw/* + read-only Leaguepedia external match records and produces:
 *   data/node/picks.json            (full audited inventory + picks + provenance)
 *   data/node/picks.csv             (flat export of all scheduled matches)
 *   data/node/flags.json            (irregularities & unverified items for review)
 *   data/node/model/ratings.json    (team Elo ratings + walk-forward calibration)
 *   data/node/history/ledger.json   (append-only pre-lock prediction ledger + Brier)
 *
 * HARD INVARIANTS:
 *   1. Hotspawn crowd fields (`picked_percent`, `offered_points`, `tier`) are NEVER
 *      read by any probability, consensus, or rating calculation.
 *   2. Pinnacle `(Kills)` derivative markets are strictly excluded.
 *   3. Multi-venue real-money consensus combines up to 5 independent venues:
 *        - Pinnacle guest API (Shin power de-vig, weight 1.00)
 *        - Unibet / Kambi `ubse` Match Odds (Shin power de-vig, weight 0.70)
 *        - Bovada Head-To-Head moneyline (Shin power de-vig, weight 0.50)
 *        - Kalshi CFTC `KXLOLGAME` binary contracts (midpoint normalized, weight 0.35–0.55)
 *        - Polymarket CLOB match markets (spread <= 0.12, liquidity-scaled weight 0.20–0.65)
 *   4. Self-originated Elo/Bradley-Terry ratings replay completed non-forfeit Leaguepedia +
 *      Hotspawn LoL series strictly BEFORE each fixture's scheduled start time (zero look-ahead).
 *   5. Competition-scoped entity resolution runs BEFORE global exact matching so cross-region
 *      homonyms (`Logitech G SuperStrike Cup Qualifier | paiN Gaming` -> Bulgarian `PNG`,
 *      `PRM 2nd Division 26-27 Fall | Phong Vũ Buffalo` -> `PvB (Swiss Team)`) never inherit
 *      unrelated Tier-1/VCS Elo ratings.
 *   6. Mid-split disqualified teams (`Solid Gaming` in `Komplettligaen 2026 Autumn`) emit a
 *      typed `settlement_pick` (`walkover-settlement`) with `p0 = null, p1 = null`.
 *   7. Zero-evidence matches (`min(n0, n1) === 0` and no market line) remain `unresolved`
 *      (`p0 = null, p1 = null, pick = null`) — never fabricated or inferred.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DATA = path.join(ROOT, "data", "node");
const RAW = path.join(DATA, "raw");
const CANON_DATA = path.join(ROOT, "data");
const DOCS_DATA = path.join(ROOT, "docs", "data");

const KILLS_RE = /\(kills?\)|\bkills\b/i;
const MAX_QUOTE_AGE_MS = 24 * 3600 * 1000;

async function readJSONSafe(p, fallback = null) {
  try {
    return JSON.parse(await readFile(p, "utf8"));
  } catch {
    return fallback;
  }
}

/* ----------------------------------------------------- Competition Mapping */

const COMP_TO_LP_PAGE = {
  "4 Nations 2026 Halloween Heist": "4 Nations/2026 Season/Halloween Heist",
  "Arabian League 2nd Division 2026 Summer": "Arabian League 2nd Division/2026 Season/Summer Split",
  "Arabian Regional Championship 2026: Lebanon-Libya-Syria-Palestine": "Arabian Regional Championship 2026/Qualifiers/LB-Li-SY-PS",
  "Arabian Regional Championship 2026: Qatar-Bahrain-Kuwait": "Arabian Regional Championship 2026/Qualifiers/QA-BH-KW",
  "Benelux Ascend Series 2026 Summer Playoffs": "Benelux Ascend Series/2026 Season/Summer Playoffs",
  "Benelux Ascend Series 2026 Summer Split": "Benelux Ascend Series/2026 Season/Summer Split",
  "Benelux Ascend Series 2027 Winter Promotion": "Benelux Ascend Series/2027 Season/Winter Promotion",
  "Benelux Ascend Series Rising 2026 Summer Playoffs": "Benelux Ascend Series Rising/2026 Season/Summer Playoffs",
  "FPL 2026 Summer Playoffs": "Finnish Pro League/2026 Season/Summer Playoffs",
  "Hitpoint 2nd Div Challengers 2026 Summer Playoffs": "Hitpoint 2nd Division Challengers/2026 Season/Summer Playoffs",
  "Icelandic Esports League 2026 Autumn": "Icelandic Esports League/2026 Season/Autumn Split",
  "Komplettligaen 2026 Autumn": "Komplettligaen/2026 Season/Autumn Split",
  "Komplettligaen 2026 Autumn Playoffs": "Komplettligaen/2026 Season/Autumn Playoffs",
  "LCP 2027 Promotion": "LCP/2027 Season/Promotion",
  "LGC Rising 2026 Playoffs": "LoL Game Changers/2026 Season/Playoffs",
  "LIT 2027 Winter Promotion": "LIT/2027 Season/Winter Promotion",
  "Legends Academy powered by Żabka Season 3 Playoffs": "Legends Academy/2026/Season 3 Playoffs",
  "LigaGG CELOL A 2026 Split 2": "LigaGG/CELOL Série A/2026 Season/Split 2",
  "LigaGG CELOL A 2026 Split 2 Playoffs": "LigaGG/CELOL Série A/2026 Season/Split 2 Playoffs",
  "LigaGG CELOL B 2026 Split 2": "LigaGG/CELOL Série B/2026 Season/Split 2",
  "LigaGG CELOL B 2026 Split 2 Playoffs": "LigaGG/CELOL Série B/2026 Season/Split 2 Playoffs",
  "Logitech G SuperStrike Cup Qualifier": "Logitech G SuperStrike Cup/Qualifier",
  "POP Esports Masters Season 7": "POP Esports Masters/Season 7",
  "PRM 2nd Division 26-27 Fall": "Prime League 2nd Division/2027 Season/Fall Split",
  "PRM 3rd Division 26-27 Fall": "Prime League 3rd Division/2027 Season/Fall Split",
  "RIVALS LEAGUE Season 2": "RIVALS LEAGUE/2026 Season/Season 2",
  "Superstrike League 2026": "Superstrike League 2026",
  "Tunisian Super League 2026": "Tunisian Super League/2026 Season",
  "Worlds 2026 Main Event": "2026 Season World Championship/Main Event",
};

function leaguepediaUrl(compName) {
  const page = COMP_TO_LP_PAGE[compName];
  if (page) return `https://lol.fandom.com/wiki/${encodeURIComponent(page).replace(/%2F/g, "/").replace(/%20/g, "_")}`;
  return `https://lol.fandom.com/wiki/Special:Search?query=${encodeURIComponent(compName || "")}`;
}

/* Competition-scoped homonym overrides (highest priority — prevents cross-region Elo contamination) */
const COMP_TEAM_OVERRIDES = {
  "Logitech G SuperStrike Cup Qualifier::pain gaming": {
    lp_name: "PNG",
    display_note: "Hotspawn mis-bound Bulgarian amateur tag 'PNG' (billy/Bla6ko/metko/ifo/anditobate) to Brazilian CBLOL 'paiN Gaming'; quarantined to PNG.",
    source_url: "https://lol.fandom.com/wiki/Logitech_G_SuperStrike_Cup/Qualifier",
    collision: true,
  },
  "PRM 2nd Division 26-27 Fall::phong vũ buffalo": {
    lp_name: "PvB (Swiss Team)",
    display_note: "Hotspawn mis-bound Swiss Prime League Div 2 team 'PvB (Swiss Team)' to defunct Vietnamese VCS 'Phong Vũ Buffalo'; resolved to PvB (Swiss Team).",
    source_url: "https://lol.fandom.com/wiki/Prime_League_2nd_Division/2027_Season/Fall_Split",
    collision: true,
  },
};

/* Market team name normalization & verified venue aliases */
const MARKET_ALIASES = {
  "bilibili": "bilibili gaming",
  "blg": "bilibili gaming",
  "top": "top esports",
  "tes": "top esports",
  "anyones legend": "anyone's legend",
  "anyone s legend": "anyone's legend",
  "al": "anyone's legend",
  "gen g": "gen.g",
  "geng": "gen.g",
  "gen.g esports": "gen.g",
  "jd gaming": "jdg",
  "jd gamingintel": "jdg",
  "beijing jdg": "jdg",
  "dplus": "dplus kia",
  "dk": "dplus kia",
  "damwon": "dplus kia",
  "cloud9 kia": "cloud9",
  "c9": "cloud9",
  "team liquid honda": "team liquid",
  "tl": "team liquid",
  "flyquest": "flyquest",
  "g2": "g2 esports",
  "fnatic": "fnatic",
  "kt": "kt rolster",
  "hanwha life": "hanwha life esports",
  "hle": "hanwha life esports",
  "weibo": "weibo gaming",
  "wbg": "weibo gaming",
  "ctbc flying oyster": "flying oyster",
  "cfo": "flying oyster",
  "movistar koi": "koi",
  "mad lions koi": "koi",
  "mkoi": "koi",
  "secret whales": "team secret whales",
  "tsw": "team secret whales",
  "lyon gaming": "lyon",
  "six karma": "lyon",
  /* Newly audited CFTC Kalshi alias (#1079080 LGC Rising 2026 Playoffs) */
  "rising bees": "vitality rising bees",
  "team vitality rising bees": "vitality rising bees",
};

function normMarketTeam(raw) {
  if (!raw) return "";
  let s = String(raw)
    .replace(/[øØ]/g, "o")
    .replace(/[æÆ]/g, "ae")
    .replace(/[ß]/g, "ss")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\([^)]*\)/g, " ")
    .replace(/['’`]/g, "'")
    .replace(/[^a-z0-9']+|\b(esports?|e-sports?|gaming|team|club|lol)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (MARKET_ALIASES[s]) {
    s = MARKET_ALIASES[s]
      .toLowerCase()
      .replace(/[^a-z0-9']+|\b(esports?|e-sports?|gaming|team|club|lol)\b/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }
  const rawClean = String(raw)
    .replace(/[øØ]/g, "o")
    .replace(/[æÆ]/g, "ae")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\([^)]*\)/g, " ")
    .replace(/['’`]/g, "'")
    .replace(/\s+/g, " ")
    .trim();
  if (MARKET_ALIASES[rawClean]) {
    return normMarketTeam(MARKET_ALIASES[rawClean]);
  }
  return s;
}

function sameMarketTeam(a, b) {
  const na = normMarketTeam(a);
  const nb = normMarketTeam(b);
  if (!na || !nb) return false;
  if (na === nb) return true;
  if (na.length >= 4 && nb.length >= 4 && (na.includes(nb) || nb.includes(na))) return true;
  return false;
}

function alignPair(qA, qB, hs0, hs1) {
  if (sameMarketTeam(qA, hs0) && sameMarketTeam(qB, hs1)) return [0, 1];
  if (sameMarketTeam(qA, hs1) && sameMarketTeam(qB, hs0)) return [1, 0];
  return null;
}

/* ----------------------------------------------------- De-vig & Math Utils */

function americanToDecimal(am) {
  const n = Number(am);
  if (!Number.isFinite(n) || n === 0) return null;
  return n > 0 ? 1 + n / 100 : 1 + 100 / Math.abs(n);
}

/**
 * Power (Shin-equivalent 2-way) de-vig: solves q0^k + q1^k = 1 for k >= 1
 * where q_i = 1 / decimal_i. Strips bookmaker overround while respecting
 * favourite-longshot bias.
 */
function powerDevig(dec0, dec1) {
  if (!(dec0 > 1.001 && dec1 > 1.001)) return null;
  // Reject symmetric unpriced placeholder lines like 1.80 / 1.80 on obscure promos when overround > 11%
  const q0 = 1 / dec0;
  const q1 = 1 / dec1;
  const overround = q0 + q1;
  if (overround < 0.96 || overround > 1.20) return null;
  if (Math.abs(dec0 - dec1) < 1e-6 && Math.abs(dec0 - 1.8) < 1e-3) return null;
  let lo = 0.5;
  let hi = 4.0;
  for (let i = 0; i < 48; i++) {
    const mid = 0.5 * (lo + hi);
    const s = Math.pow(q0, mid) + Math.pow(q1, mid);
    if (s > 1) lo = mid;
    else hi = mid;
  }
  const k = 0.5 * (lo + hi);
  const p0 = Math.pow(q0, k);
  const p1 = 1 - p0;
  if (!(p0 > 0.005 && p0 < 0.995)) return null;
  return { p0, p1, overround: Number(overround.toFixed(4)) };
}

function parseTimeMs(v) {
  if (v == null || v === "") return null;
  if (typeof v === "number") return v > 1e11 ? v : v * 1000;
  const s = String(v).trim();
  if (/^\d+$/.test(s)) {
    const n = Number(s);
    return n > 1e11 ? n : n * 1000;
  }
  // Leaguepedia UTC format: "YYYY-MM-DD HH:MM:SS"
  const iso = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(s) ? s.replace(" ", "T") + "Z" : s;
  const ms = Date.parse(iso);
  return Number.isFinite(ms) ? ms : null;
}

function slugifyHotspawn(t0, t1, comp, id) {
  const part = [t0, "vs", t1, comp]
    .join("-")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `https://www.hotspawn.com/matches/${part}-${id}`;
}

/* ----------------------------------------------------- Market Venue Loaders */

function buildPinnacleQuotes(pinRaw, nowMs) {
  const quotes = [];
  if (!pinRaw || !Array.isArray(pinRaw.leagues)) return { quotes, rejected_kills: 0, expired: false };
  const fetchedMs = parseTimeMs(pinRaw.fetched_at || pinRaw.fetched_utc);
  if (!fetchedMs || nowMs - fetchedMs > MAX_QUOTE_AGE_MS) {
    return { quotes, rejected_kills: 0, expired: true };
  }
  let rejectedKills = pinRaw.excluded_kills || 0;
  for (const lg of pinRaw.leagues) {
    const byId = new Map();
    for (const m of lg.matchups || []) {
      const names = (m.participants || []).map((p) => p.name || "").join(" ");
      if (KILLS_RE.test(names) || (m.special && KILLS_RE.test(JSON.stringify(m.special)))) {
        rejectedKills++;
        continue;
      }
      byId.set(m.id, m);
    }
    for (const s of lg.straight || []) {
      if (s.period !== 0) continue; // full-series moneyline ONLY (never map 1/2/3 or kills)
      const m = byId.get(s.matchupId);
      if (!m) continue;
      const home = (m.participants || []).find((p) => p.alignment === "home") || m.participants?.[0];
      const away = (m.participants || []).find((p) => p.alignment === "away") || m.participants?.[1];
      if (!home || !away) continue;
      const pHome = (s.prices || []).find((p) => p.designation === "home");
      const pAway = (s.prices || []).find((p) => p.designation === "away");
      if (!pHome || !pAway) continue;
      const dec0 = americanToDecimal(pHome.price);
      const dec1 = americanToDecimal(pAway.price);
      const dv = powerDevig(dec0, dec1);
      if (!dv) continue;
      quotes.push({
        venue: "pinnacle",
        venue_label: "Pinnacle",
        weight: 1.0,
        teamA: home.name,
        teamB: away.name,
        decA: Number(dec0.toFixed(3)),
        decB: Number(dec1.toFixed(3)),
        amA: pHome.price,
        amB: pAway.price,
        pA: dv.p0,
        pB: dv.p1,
        overround: dv.overround,
        start_ms: parseTimeMs(m.startTime),
        fetched_at: pinRaw.fetched_at || pinRaw.fetched_utc,
        matchup_id: m.id,
        league: lg.name,
        url: m.straight_url || `https://guest.api.arcadia.pinnacle.com/0.1/matchups/${m.id}/markets/related/straight`,
      });
    }
  }
  return { quotes, rejected_kills: rejectedKills, expired: false };
}

function buildKambiQuotes(kambiRaw, nowMs) {
  const quotes = [];
  if (!kambiRaw || !Array.isArray(kambiRaw.events)) return { quotes, expired: false };
  const fetchedMs = parseTimeMs(kambiRaw.fetched_at || kambiRaw.fetched_utc);
  if (!fetchedMs || nowMs - fetchedMs > MAX_QUOTE_AGE_MS) return { quotes, expired: true };
  for (const ev of kambiRaw.events) {
    if (KILLS_RE.test(ev.name || "")) continue;
    const outs = ev.outcomes || [];
    if (outs.length !== 2) continue;
    const dec0 = Number(outs[0].decimal);
    const dec1 = Number(outs[1].decimal);
    const dv = powerDevig(dec0, dec1);
    if (!dv) continue;
    quotes.push({
      venue: "kambi",
      venue_label: "Unibet (Kambi)",
      weight: 0.7,
      teamA: outs[0].name,
      teamB: outs[1].name,
      decA: dec0,
      decB: dec1,
      pA: dv.p0,
      pB: dv.p1,
      overround: dv.overround,
      start_ms: parseTimeMs(ev.start_utc),
      fetched_at: kambiRaw.fetched_at || kambiRaw.fetched_utc,
      event_id: ev.event_id,
      url: ev.url || `https://eu-offering-api.kambicdn.com/offering/v2018/ubse/betoffer/event/${ev.event_id}.json?lang=en_GB&market=ZZ`,
    });
  }
  return { quotes, expired: false };
}

function buildBovadaQuotes(bovRaw, nowMs) {
  const quotes = [];
  if (!bovRaw || !Array.isArray(bovRaw.events)) return { quotes, expired: false };
  const fetchedMs = parseTimeMs(bovRaw.fetched_at || bovRaw.fetched_utc);
  if (!fetchedMs || nowMs - fetchedMs > MAX_QUOTE_AGE_MS) return { quotes, expired: true };
  for (const ev of bovRaw.events) {
    if (KILLS_RE.test(ev.description || "")) continue;
    const outs = ev.outcomes || [];
    if (outs.length !== 2) continue;
    const dec0 = Number(outs[0].decimal);
    const dec1 = Number(outs[1].decimal);
    const dv = powerDevig(dec0, dec1);
    if (!dv) continue;
    quotes.push({
      venue: "bovada",
      venue_label: "Bovada",
      weight: 0.5,
      teamA: outs[0].name,
      teamB: outs[1].name,
      decA: dec0,
      decB: dec1,
      pA: dv.p0,
      pB: dv.p1,
      overround: dv.overround,
      start_ms: parseTimeMs(ev.start_utc || ev.start_ms),
      fetched_at: bovRaw.fetched_at || bovRaw.fetched_utc,
      url: ev.url || "https://www.bovada.lv/sports/esports/league-of-legends",
    });
  }
  return { quotes, expired: false };
}

function buildKalshiQuotes(kalshiRaw, nowMs) {
  const quotes = [];
  if (!kalshiRaw || !Array.isArray(kalshiRaw.events)) return { quotes, expired: false };
  const fetchedMs = parseTimeMs(kalshiRaw.fetched_at || kalshiRaw.fetched_utc);
  if (!fetchedMs || nowMs - fetchedMs > MAX_QUOTE_AGE_MS) return { quotes, expired: true };
  for (const ev of kalshiRaw.events) {
    const mkts = ev.markets || [];
    if (mkts.length !== 2) continue;
    const mids = mkts.map((m) => {
      const bid = Number(m.yes_bid_dollars);
      const ask = Number(m.yes_ask_dollars);
      const last = Number(m.last_price_dollars);
      if (Number.isFinite(bid) && Number.isFinite(ask) && bid > 0 && ask > 0 && ask - bid <= 0.20) {
        return { mid: 0.5 * (bid + ask), spread: ask - bid, bid, ask };
      }
      if (Number.isFinite(last) && last > 0.01 && last < 0.99) {
        return { mid: last, spread: 0.10, bid: null, ask: null };
      }
      return null;
    });
    if (!mids[0] || !mids[1]) continue;
    const sum = mids[0].mid + mids[1].mid;
    if (sum < 0.85 || sum > 1.18) continue;
    const pA = mids[0].mid / sum;
    const pB = 1 - pA;
    const vol = (Number(mkts[0].volume_fp ?? mkts[0].volume ?? 0) || 0) + (Number(mkts[1].volume_fp ?? mkts[1].volume ?? 0) || 0);
    const maxSpread = Math.max(mids[0].spread, mids[1].spread);
    const weight = maxSpread <= 0.04 ? 0.55 : 0.40;
    const tickerLower = String(ev.event_ticker || "").toLowerCase();
    quotes.push({
      venue: "kalshi",
      venue_label: "Kalshi CFTC",
      weight,
      teamA: mkts[0].yes_sub_title,
      teamB: mkts[1].yes_sub_title,
      bidA: mids[0].bid,
      askA: mids[0].ask,
      bidB: mids[1].bid,
      askB: mids[1].ask,
      pA,
      pB,
      spread: Number(maxSpread.toFixed(4)),
      volume: vol,
      overround: Number(sum.toFixed(4)),
      start_ms: parseTimeMs(mkts[0].occurrence_datetime),
      fetched_at: kalshiRaw.fetched_at || kalshiRaw.fetched_utc,
      event_ticker: ev.event_ticker,
      url: `https://kalshi.com/markets/kxlolgame/${tickerLower}`,
      api_url: `https://api.elections.kalshi.com/trade-api/v2/events/${ev.event_ticker}?with_nested_markets=true`,
    });
  }
  return { quotes, expired: false };
}

function buildPolymarketQuotes(polyRaw, nowMs) {
  const quotes = [];
  if (!polyRaw || !Array.isArray(polyRaw.events)) return { quotes, expired: false };
  const fetchedMs = parseTimeMs(polyRaw.fetched_at || polyRaw.fetched_utc);
  if (!fetchedMs || nowMs - fetchedMs > MAX_QUOTE_AGE_MS) return { quotes, expired: true };
  for (const ev of polyRaw.events) {
    if (ev.closed) continue;
    for (const m of ev.markets || []) {
      if (m.closed) continue;
      const qText = `${ev.title || ""} ${m.question || ""} ${m.groupItemTitle || ""}`;
      if (/map\s*[1-5]|game\s*[1-5]|first\s*blood|kills|handicap|over|under|total/i.test(qText)) continue;
      if (!Array.isArray(m.outcomes) || m.outcomes.length !== 2) continue;
      const pr0 = Number(m.outcomePrices?.[0]);
      const pr1 = Number(m.outcomePrices?.[1]);
      if (!(pr0 > 0.01 && pr1 > 0.01 && Math.abs(pr0 + pr1 - 1) < 0.08)) continue;
      const spread = m.spread == null ? 0.04 : Number(m.spread);
      if (spread > 0.14) continue;
      const liq = Number(m.liquidity ?? ev.liquidity ?? 0) || 0;
      const vol = Number(m.volume ?? ev.volume ?? 0) || 0;
      if (liq < 10 && vol < 10) continue;
      const depth = Math.max(liq, vol);
      const weight = depth >= 10000 ? 0.65 : depth >= 1000 ? 0.45 : 0.25;
      const sum = pr0 + pr1;
      const slugDateMatch = String(ev.slug || "").match(/(\d{4}-\d{2}-\d{2})$/);
      const polyStart = m.gameStartTime || (slugDateMatch ? `${slugDateMatch[1]}T12:00:00Z` : ev.endDate || ev.startDate);
      quotes.push({
        venue: "polymarket",
        venue_label: "Polymarket",
        weight,
        teamA: m.outcomes[0],
        teamB: m.outcomes[1],
        pA: pr0 / sum,
        pB: pr1 / sum,
        spread: Number(spread.toFixed(4)),
        liquidity: Math.round(liq),
        volume: Math.round(vol),
        start_ms: parseTimeMs(polyStart),
        fetched_at: polyRaw.fetched_at || polyRaw.fetched_utc,
        slug: ev.slug,
        url: `https://polymarket.com/event/${ev.slug}`,
      });
    }
  }
  return { quotes, expired: false };
}

function matchVenueQuotes(hsMatch, allQuotes) {
  const t0 = hsMatch.participants[0].name;
  const t1 = hsMatch.participants[1].name;
  const hsStart = parseTimeMs(hsMatch.scheduled_start_time);
  const byVenue = new Map();

  for (const q of allQuotes) {
    const align = alignPair(q.teamA, q.teamB, t0, t1);
    if (!align) continue;
    if (hsStart && q.start_ms) {
      const diffHrs = Math.abs(hsStart - q.start_ms) / 3600000;
      // Kalshi uses close_time (+48h settlement window) when occurrence_datetime is absent; sportsbooks/Polymarket match within 30h
      const maxHrs = q.venue === "kalshi" ? 96 : 30;
      if (diffHrs > maxHrs) continue;
    }
    const p0 = align[0] === 0 ? q.pA : q.pB;
    const p1 = 1 - p0;
    const aligned = {
      venue: q.venue,
      venue_label: q.venue_label,
      weight: q.weight,
      p0: Number(p0.toFixed(6)),
      p1: Number(p1.toFixed(6)),
      dec0: align[0] === 0 ? (q.decA ?? null) : (q.decB ?? null),
      dec1: align[0] === 0 ? (q.decB ?? null) : (q.decA ?? null),
      am0: align[0] === 0 ? (q.amA ?? null) : (q.amB ?? null),
      am1: align[0] === 0 ? (q.amB ?? null) : (q.amA ?? null),
      bid0: align[0] === 0 ? (q.bidA ?? null) : (q.bidB ?? null),
      ask0: align[0] === 0 ? (q.askA ?? null) : (q.askB ?? null),
      bid1: align[0] === 0 ? (q.bidB ?? null) : (q.bidA ?? null),
      ask1: align[0] === 0 ? (q.askB ?? null) : (q.askA ?? null),
      overround: q.overround ?? null,
      spread: q.spread ?? null,
      liquidity: q.liquidity ?? null,
      volume: q.volume ?? null,
      fetched_at: q.fetched_at,
      url: q.url,
      api_url: q.api_url ?? null,
    };
    const prev = byVenue.get(q.venue);
    if (!prev || (aligned.liquidity || 0) > (prev.liquidity || 0)) {
      byVenue.set(q.venue, aligned);
    }
  }
  return [...byVenue.values()];
}

/* --------------------------------- Entity Resolution & Pre-Kickoff Elo Model */

function baseLpName(name) {
  return String(name || "").replace(/\s*\([^)]*\)\s*$/, "").trim();
}

function buildEntityResolver(lpRows, aliasesObj) {
  const byPage = new Map();
  const globalCaseMap = new Map();
  const teamPages = new Map();

  for (const r of lpRows) {
    const pg = r.overview_page || "";
    if (!byPage.has(pg)) byPage.set(pg, new Set());
    for (const rawT of [r.team1, r.team2]) {
      if (!rawT) continue;
      const t = rawT.trim();
      const canonKey = t.toLowerCase();
      // Fold casing variants (e.g. "CRUEL FATE" and "Cruel Fate") to a single canonical key
      if (!globalCaseMap.has(canonKey)) globalCaseMap.set(canonKey, t);
      const canonicalName = globalCaseMap.get(canonKey);
      byPage.get(pg).add(canonicalName);
      if (!teamPages.has(canonicalName)) teamPages.set(canonicalName, new Set());
      if (pg) teamPages.get(canonicalName).add(pg);
    }
  }

  const explicitAliases = {};
  for (const [k, v] of Object.entries(aliasesObj?.aliases || {})) {
    const ck = v.trim().toLowerCase();
    explicitAliases[k.trim().toLowerCase()] = globalCaseMap.get(ck) || v.trim();
  }

  function canonicalizeLp(rawName) {
    if (!rawName) return "";
    const k = rawName.trim().toLowerCase();
    return globalCaseMap.get(k) || rawName.trim();
  }

  function resolveHotspawnTeam(compName, rawTeamName) {
    const rawTrim = String(rawTeamName || "").trim();
    const rawLow = rawTrim.toLowerCase();
    const overrideKey = `${compName}::${rawLow}`;
    if (COMP_TEAM_OVERRIDES[overrideKey]) {
      const ov = COMP_TEAM_OVERRIDES[overrideKey];
      return {
        canonical: canonicalizeLp(ov.lp_name),
        join_method: "competition-override",
        note: ov.display_note,
        collision: !!ov.collision,
        source_url: ov.source_url,
      };
    }

    const compPage = COMP_TO_LP_PAGE[compName];
    const pageTeams = compPage && byPage.get(compPage) ? [...byPage.get(compPage)] : [];

    // 1. Exact case-insensitive match within the specific competition page
    const exactInPage = pageTeams.find((t) => t.toLowerCase() === rawLow);
    if (exactInPage) {
      const pages = teamPages.get(exactInPage) ? [...teamPages.get(exactInPage)] : [];
      const multiPool =
        compName === "PRM 3rd Division 26-27 Fall" && exactInPage === "Rich Gang (Norwegian Team)"
          ? "Leaguepedia pools Rich Gang (Norwegian Team) across Komplettligaen and Prime League 3rd Division."
          : null;
      return { canonical: exactInPage, join_method: "competition-exact", note: multiPool, collision: false };
    }

    // 2. Unique parenthesized disambiguation within the competition page (e.g. Nameless -> Nameless (Benelux Team))
    const baseMatchesInPage = pageTeams.filter((t) => baseLpName(t).toLowerCase() === rawLow);
    if (baseMatchesInPage.length === 1) {
      const chosen = baseMatchesInPage[0];
      const multiPool =
        compName === "PRM 3rd Division 26-27 Fall" && chosen === "Rich Gang (Norwegian Team)"
          ? "Leaguepedia pools Rich Gang (Norwegian Team) across Komplettligaen and Prime League 3rd Division."
          : null;
      return {
        canonical: chosen,
        join_method: "competition-disambiguated",
        note: multiPool || `Resolved within '${compPage}' to '${chosen}'.`,
        collision: false,
      };
    }

    // 3. Explicit verified alias (data/aliases.json)
    if (explicitAliases[rawLow]) {
      return {
        canonical: explicitAliases[rawLow],
        join_method: "verified-alias",
        note: `Explicit alias '${rawTrim}' -> '${explicitAliases[rawLow]}'`,
        collision: false,
      };
    }

    // 4. Global case-insensitive exact match
    if (globalCaseMap.has(rawLow)) {
      return { canonical: globalCaseMap.get(rawLow), join_method: "global-exact", note: null, collision: false };
    }

    // 5. Hotspawn-only team name (falls back to Hotspawn completed series if any)
    return { canonical: rawTrim, join_method: "hotspawn-name", note: null, collision: false };
  }

  return { canonicalizeLp, resolveHotspawnTeam };
}

/**
 * Series win probability from per-map probability p under independent Bernoulli games:
 *   Bo1: p
 *   Bo2: p (2-way pick'em tie-broken / game-share expectation = p)
 *   Bo3: p^2 * (3 - 2p)
 *   Bo5: p^3 * (10 - 15p + 6p^2)
 */
function mapProbToSeriesProb(pMap, bestOf) {
  const bo = Number(bestOf) || 1;
  if (bo <= 2) return pMap;
  if (bo === 3) return pMap * pMap * (3 - 2 * pMap);
  if (bo >= 5) return pMap * pMap * pMap * (10 - 15 * pMap + 6 * pMap * pMap);
  return pMap;
}

/**
 * Builds chronological pre-kickoff Elo ratings across Leaguepedia + Hotspawn non-forfeit matches,
 * computing walk-forward out-of-sample Brier/log-loss and exact pre-kickoff snapshots for every
 * scheduled Hotspawn fixture (strictly T_history < T_fixture).
 */
function runPreKickoffElo(lpRows, hsFixtures, resolver) {
  const historyEvents = [];
  const seenPairDay = new Set();

  // 1. Leaguepedia non-forfeit completed series
  for (const r of lpRows) {
    if (r.ff != null && r.ff !== "" && r.ff !== 0 && r.ff !== "0") continue;
    const w = String(r.winner ?? "");
    if (w !== "1" && w !== "2") continue;
    const ms = parseTimeMs(r.utc);
    if (!ms) continue;
    const tA = resolver.canonicalizeLp(r.team1);
    const tB = resolver.canonicalizeLp(r.team2);
    if (!tA || !tB || tA === tB) continue;
    const dayKey = `${Math.floor(ms / 86400000)}::${[tA, tB].sort().join("|")}`;
    seenPairDay.add(dayKey);
    const s1 = Number(r.team1_score);
    const s2 = Number(r.team2_score);
    historyEvents.push({
      ms,
      tA,
      tB,
      winA: w === "1" ? 1 : 0,
      sA: Number.isFinite(s1) ? s1 : w === "1" ? 1 : 0,
      sB: Number.isFinite(s2) ? s2 : w === "2" ? 1 : 0,
      best_of: Number(r.best_of) || 1,
      source: "leaguepedia",
      comp: r.overview_page || "",
    });
  }

  // 2. Hotspawn ended (non-forfeit) series not already in Leaguepedia on the same day
  for (const f of hsFixtures) {
    if (f.status !== "ended") continue;
    const ms = parseTimeMs(f.scheduled_start_time);
    if (!ms) continue;
    const r0 = resolver.resolveHotspawnTeam(f.competition_name, f.participants[0].name);
    const r1 = resolver.resolveHotspawnTeam(f.competition_name, f.participants[1].name);
    const tA = r0.canonical;
    const tB = r1.canonical;
    if (!tA || !tB || tA === tB) continue;
    const s0 = Number(f.participants[0].score);
    const s1 = Number(f.participants[1].score);
    if (!(Number.isFinite(s0) && Number.isFinite(s1)) || s0 === s1) continue;
    const dayKey = `${Math.floor(ms / 86400000)}::${[tA, tB].sort().join("|")}`;
    if (seenPairDay.has(dayKey)) continue;
    seenPairDay.add(dayKey);
    historyEvents.push({
      ms,
      tA,
      tB,
      winA: s0 > s1 ? 1 : 0,
      sA: s0,
      sB: s1,
      best_of: Number(f.best_of) || 1,
      source: "hotspawn_ended",
      comp: f.competition_name || "",
    });
  }

  historyEvents.sort((a, b) => a.ms - b.ms);

  // Target fixtures sorted by scheduled start time for single-pass exact pre-kickoff evaluation
  const targets = hsFixtures.map((f) => {
    const ms = parseTimeMs(f.scheduled_start_time) ?? Number.MAX_SAFE_INTEGER;
    const r0 = resolver.resolveHotspawnTeam(f.competition_name, f.participants[0].name);
    const r1 = resolver.resolveHotspawnTeam(f.competition_name, f.participants[1].name);
    return { fixture: f, ms, r0, r1 };
  });
  targets.sort((a, b) => a.ms - b.ms);

  const state = new Map();
  function getTeam(name) {
    if (!state.has(name)) {
      state.set(name, { rating: 1500, n: 0, wins: 0, losses: 0, mapsW: 0, mapsL: 0, last_ms: null });
    }
    return state.get(name);
  }

  function shrunkRating(st) {
    // Empirical-Bayes shrinkage toward 1500 for small-sample rosters (tau = 6 series)
    const shrink = st.n / (st.n + 6);
    return 1500 + shrink * (st.rating - 1500);
  }

  function predictFromState(st0, st1, bestOf) {
    const eff0 = shrunkRating(st0);
    const eff1 = shrunkRating(st1);
    const pMap = 1 / (1 + Math.pow(10, (eff1 - eff0) / 400));
    // Dampen series amplification slightly (alpha = 0.72) because map outcomes within a LoL series are positively correlated
    const rawSeries = mapProbToSeriesProb(pMap, bestOf);
    const p0 = Math.min(0.96, Math.max(0.04, 0.72 * rawSeries + 0.28 * pMap));
    return { p0, p1: 1 - p0, pMap, eff0, eff1 };
  }

  // Out-of-sample walk-forward accumulators (evaluated strictly BEFORE updating ratings)
  const bins = Array.from({ length: 10 }, (_, i) => ({
    bin: `${i * 10}-${(i + 1) * 10}%`,
    n: 0,
    sum_p: 0,
    sum_y: 0,
  }));
  let oosN = 0;
  let oosBrier = 0;
  let oosLogLoss = 0;
  let oosCorrect = 0;

  const preKickoffByFixtureId = new Map();
  let hIdx = 0;

  for (const tgt of targets) {
    while (hIdx < historyEvents.length && historyEvents[hIdx].ms < tgt.ms) {
      const ev = historyEvents[hIdx++];
      const stA = getTeam(ev.tA);
      const stB = getTeam(ev.tB);
      if (stA.n >= 3 && stB.n >= 3) {
        const pred = predictFromState(stA, stB, ev.best_of);
        const y = ev.winA;
        oosN++;
        oosBrier += Math.pow(pred.p0 - y, 2);
        const pClip = Math.min(0.995, Math.max(0.005, pred.p0));
        oosLogLoss += -(y * Math.log(pClip) + (1 - y) * Math.log(1 - pClip));
        if ((pred.p0 >= 0.5 && y === 1) || (pred.p0 < 0.5 && y === 0)) oosCorrect++;
        const bIdx = Math.min(9, Math.floor(pred.p0 * 10));
        bins[bIdx].n++;
        bins[bIdx].sum_p += pred.p0;
        bins[bIdx].sum_y += y;
      }
      // Dynamic K-factor with map-margin multiplier
      const expA = 1 / (1 + Math.pow(10, (stB.rating - stA.rating) / 400));
      const kA = stA.n < 8 ? 38 : stA.n < 25 ? 28 : 22;
      const kB = stB.n < 8 ? 38 : stB.n < 25 ? 28 : 22;
      const margin = Math.min(1.35, 1 + 0.15 * Math.max(0, Math.abs(ev.sA - ev.sB) - 1));
      stA.rating += kA * margin * (ev.winA - expA);
      stB.rating += kB * margin * ((1 - ev.winA) - (1 - expA));
      stA.n++;
      stB.n++;
      if (ev.winA === 1) { stA.wins++; stB.losses++; } else { stB.wins++; stA.losses++; }
      stA.mapsW += ev.sA; stA.mapsL += ev.sB;
      stB.mapsW += ev.sB; stB.mapsL += ev.sA;
      stA.last_ms = ev.ms;
      stB.last_ms = ev.ms;
    }

    const st0 = { ...(state.get(tgt.r0.canonical) || { rating: 1500, n: 0, wins: 0, losses: 0, mapsW: 0, mapsL: 0, last_ms: null }) };
    const st1 = { ...(state.get(tgt.r1.canonical) || { rating: 1500, n: 0, wins: 0, losses: 0, mapsW: 0, mapsL: 0, last_ms: null }) };
    const pred = predictFromState(st0, st1, tgt.fixture.best_of);
    preKickoffByFixtureId.set(String(tgt.fixture.id), {
      r0: tgt.r0,
      r1: tgt.r1,
      st0,
      st1,
      pred,
    });
  }

  // Drain remaining history events for final current ratings snapshot
  while (hIdx < historyEvents.length) {
    const ev = historyEvents[hIdx++];
    const stA = getTeam(ev.tA);
    const stB = getTeam(ev.tB);
    const expA = 1 / (1 + Math.pow(10, (stB.rating - stA.rating) / 400));
    const kA = stA.n < 8 ? 38 : stA.n < 25 ? 28 : 22;
    const kB = stB.n < 8 ? 38 : stB.n < 25 ? 28 : 22;
    const margin = Math.min(1.35, 1 + 0.15 * Math.max(0, Math.abs(ev.sA - ev.sB) - 1));
    stA.rating += kA * margin * (ev.winA - expA);
    stB.rating += kB * margin * ((1 - ev.winA) - (1 - expA));
    stA.n++; stB.n++;
    if (ev.winA === 1) { stA.wins++; stB.losses++; } else { stB.wins++; stA.losses++; }
    stA.mapsW += ev.sA; stA.mapsL += ev.sB;
    stB.mapsW += ev.sB; stB.mapsL += ev.sA;
    stA.last_ms = ev.ms; stB.last_ms = ev.ms;
  }

  const calibration = {
    series_replayed: historyEvents.length,
    oos_evaluated: oosN,
    brier: oosN ? Number((oosBrier / oosN).toFixed(4)) : null,
    coinflip_brier: 0.25,
    log_loss: oosN ? Number((oosLogLoss / oosN).toFixed(4)) : null,
    accuracy: oosN ? Number((oosCorrect / oosN).toFixed(4)) : null,
    reliability_bins: bins.map((b) => ({
      bin: b.bin,
      n: b.n,
      mean_pred: b.n ? Number((b.sum_p / b.n).toFixed(4)) : null,
      empirical_win_rate: b.n ? Number((b.sum_y / b.n).toFixed(4)) : null,
    })),
  };

  return { preKickoffByFixtureId, currentRatings: state, calibration };
}

/* --------------------------------------------------------------------- Main */

const nowMs = Date.now();
const generatedAt = new Date(nowMs).toISOString();

const hsRaw = await readJSONSafe(path.join(RAW, "hotspawn_lol_fixtures.json"));
if (!hsRaw || !Array.isArray(hsRaw.fixtures)) {
  console.error("FATAL: missing data/node/raw/hotspawn_lol_fixtures.json");
  process.exit(2);
}
const lobbyRaw = (await readJSONSafe(path.join(RAW, "hotspawn_lobby_check.json"))) || {};
const pinRaw = await readJSONSafe(path.join(RAW, "pinnacle_lol.json"));
const polyRaw = await readJSONSafe(path.join(RAW, "polymarket_lol.json"));
const kalshiRaw = (await readJSONSafe(path.join(RAW, "kalshi_lol.json"))) || (await readJSONSafe(path.join(CANON_DATA, "raw", "kalshi_lol.json")));
const kambiRaw = (await readJSONSafe(path.join(RAW, "kambi_lol.json"))) || (await readJSONSafe(path.join(CANON_DATA, "raw", "kambi_lol.json")));
const bovRaw = (await readJSONSafe(path.join(RAW, "bovada_lol.json"))) || (await readJSONSafe(path.join(CANON_DATA, "raw", "bovada_lol.json")));
const dqRaw = (await readJSONSafe(path.join(RAW, "leaguepedia_dq.json"))) || {};
const lpRaw = (await readJSONSafe(path.join(CANON_DATA, "raw", "leaguepedia.json"))) || { matches: [] };
const aliasesRaw = (await readJSONSafe(path.join(CANON_DATA, "aliases.json"))) || { aliases: {} };

const pinBuilt = buildPinnacleQuotes(pinRaw, nowMs);
const kambiBuilt = buildKambiQuotes(kambiRaw, nowMs);
const bovBuilt = buildBovadaQuotes(bovRaw, nowMs);
const kalshiBuilt = buildKalshiQuotes(kalshiRaw, nowMs);
const polyBuilt = buildPolymarketQuotes(polyRaw, nowMs);

const allVenueQuotes = [
  ...pinBuilt.quotes,
  ...kambiBuilt.quotes,
  ...bovBuilt.quotes,
  ...kalshiBuilt.quotes,
  ...polyBuilt.quotes,
];

const resolver = buildEntityResolver(lpRaw.matches || [], aliasesRaw);
const { preKickoffByFixtureId, currentRatings, calibration } = runPreKickoffElo(
  lpRaw.matches || [],
  hsRaw.fixtures,
  resolver
);

// Build lookup of post-kickoff Leaguepedia official scores for stale scheduled cards (strictly audit/display note ONLY — NEVER used for pre-kickoff probability!)
const lpPostKickoffIndex = new Map();
for (const r of lpRaw.matches || []) {
  if (!r.overview_page || !r.winner) continue;
  const t1 = resolver.canonicalizeLp(r.team1);
  const t2 = resolver.canonicalizeLp(r.team2);
  const key = `${r.overview_page}::${[t1, t2].sort().join("|")}`;
  if (!lpPostKickoffIndex.has(key)) {
    lpPostKickoffIndex.set(key, {
      team1: t1,
      team2: t2,
      score1: r.team1_score,
      score2: r.team2_score,
      winner: r.winner === "1" ? t1 : t2,
      utc: r.utc,
      ff: r.ff,
    });
  }
}

// Keep all `scheduled` fixtures PLUS recent 21-day `ended`/`forfeited`/`cancelled` fixtures in active competitions
const activeComps = new Set(
  hsRaw.fixtures.filter((f) => f.status === "scheduled").map((f) => f.competition_name)
);
const RECENT_WINDOW_MS = 21 * 86400 * 1000;
const selectedFixtures = hsRaw.fixtures.filter((f) => {
  if (f.status === "scheduled") return true;
  const ms = parseTimeMs(f.scheduled_start_time) || 0;
  return activeComps.has(f.competition_name) && nowMs - ms <= RECENT_WINDOW_MS;
});

const permalinks = lobbyRaw.permalinks || {};
const dqByComp = dqRaw.dq_by_competition || {};

const matches = [];
const flags = [];

for (const f of selectedFixtures) {
  const id = String(f.id);
  const startMs = parseTimeMs(f.scheduled_start_time);
  const lockMs = parseTimeMs(f.lock_time) ?? startMs;
  const startIso = startMs ? new Date(startMs).toISOString() : null;
  const t0Name = f.participants[0].name;
  const t1Name = f.participants[1].name;

  let state = "open";
  if (f.status === "ended") state = "ended";
  else if (f.status === "forfeited") state = "forfeited";
  else if (f.status === "cancelled") state = "cancelled";
  else if (f.status === "live" || f.status === "running") state = "live";
  else if (startMs && nowMs - startMs > 6 * 3600 * 1000) state = "stale";
  else if (lockMs && nowMs >= lockMs) state = "locked";
  else state = "open";

  const hotspawnUrl = permalinks[id] || slugifyHotspawn(t0Name, t1Name, f.competition_name, id);
  const lpUrl = leaguepediaUrl(f.competition_name);
  const pk = preKickoffByFixtureId.get(id);
  const r0 = pk.r0;
  const r1 = pk.r1;
  const st0 = pk.st0;
  const st1 = pk.st1;

  // Check mid-split dqteams administrative removal (e.g. Solid Gaming in Komplettligaen 2026 Autumn)
  const compDq = dqByComp[f.competition_name];
  const dqTeamsLower = new Set((compDq?.teams || []).map((x) => x.toLowerCase()));
  const dq0 = dqTeamsLower.has(r0.canonical.toLowerCase()) || dqTeamsLower.has(t0Name.toLowerCase());
  const dq1 = dqTeamsLower.has(r1.canonical.toLowerCase()) || dqTeamsLower.has(t1Name.toLowerCase());

  // Match external market quotes (for scheduled/live matches; also record if matched on recent ended)
  const venues = f.status === "scheduled" ? matchVenueQuotes(f, allVenueQuotes) : [];
  const venueByKey = Object.fromEntries(venues.map((v) => [v.venue, v]));

  let marketConsensus = null;
  if (venues.length > 0) {
    let wSum = 0;
    let p0Weighted = 0;
    for (const v of venues) {
      wSum += v.weight;
      p0Weighted += v.weight * v.p0;
    }
    const p0c = Math.round((p0Weighted / wSum) * 1000) / 1000;
    const p1c = Math.round((1 - p0c) * 1000) / 1000;
    const p0s = venues.map((v) => v.p0);
    const spreadPp = Number(((Math.max(...p0s) - Math.min(...p0s)) * 100).toFixed(2));
    const sortedVenues = [...venues].sort((a, b) => b.weight - a.weight);
    marketConsensus = {
      p0: p0c,
      p1: p1c,
      venue_count: venues.length,
      spread_pp: spreadPp,
      primary_venue: sortedVenues[0].venue_label,
      primary_url: sortedVenues[0].url,
      venues: sortedVenues,
    };
  }

  const minN = Math.min(st0.n, st1.n);
  const modelP0 = Math.round(pk.pred.p0 * 1000) / 1000;
  const modelObj =
    minN >= 1 && !dq0 && !dq1
      ? {
          p0: modelP0,
          p1: Math.round((1 - modelP0) * 1000) / 1000,
          elo0: Number(st0.rating.toFixed(1)),
          elo1: Number(st1.rating.toFixed(1)),
          eff_elo0: Number(pk.pred.eff0.toFixed(1)),
          eff_elo1: Number(pk.pred.eff1.toFixed(1)),
          n0: st0.n,
          n1: st1.n,
          tier: minN >= 5 ? "established" : "provisional",
          rating_as_of: startIso,
          source_url: lpUrl,
        }
      : null;

  let p0 = null;
  let p1 = null;
  let pick = null;
  let pickSide = null;
  let settlementPick = null;
  let sourceCategory = "unresolved";
  let confidence = "unresolved";
  let unresolvedReason = null;

  if (dq0 || dq1) {
    const winIdx = dq0 ? 1 : 0;
    const winName = dq0 ? t1Name : t0Name;
    const removedName = dq0 ? t0Name : t1Name;
    sourceCategory = "unresolved";
    confidence = "settlement";
    settlementPick = {
      team_index: winIdx,
      team_name: winName,
      pick_type: "walkover-settlement",
      removed_team: removedName,
      source_url: compDq.source_url,
      evidence: compDq.evidence,
    };
    unresolvedReason = `${removedName} was removed mid-split from ${f.competition_name} (${compDq.evidence}); no sporting probability emitted — administrative walkover settlement favors ${winName}.`;
  } else if (marketConsensus) {
    p0 = marketConsensus.p0;
    p1 = marketConsensus.p1;
    const winIdx = p0 >= p1 ? 0 : 1;
    pickSide = winIdx === 0 ? "A" : "B";
    sourceCategory = marketConsensus.venue_count >= 2 ? "market_consensus" : `market_${marketConsensus.venues[0].venue}`;
    confidence = marketConsensus.venue_count >= 2 || venueByKey.pinnacle ? "high" : "medium";
    pick = {
      team_index: winIdx,
      team_name: winIdx === 0 ? t0Name : t1Name,
      probability: winIdx === 0 ? p0 : p1,
      source: sourceCategory,
      venue_count: marketConsensus.venue_count,
      primary_url: marketConsensus.primary_url,
    };
  } else if (modelObj) {
    p0 = modelObj.p0;
    p1 = modelObj.p1;
    const winIdx = p0 >= p1 ? 0 : 1;
    pickSide = winIdx === 0 ? "A" : "B";
    sourceCategory = modelObj.tier === "established" ? "model" : "model_provisional";
    confidence = minN >= 15 ? "medium" : "low";
    pick = {
      team_index: winIdx,
      team_name: winIdx === 0 ? t0Name : t1Name,
      probability: winIdx === 0 ? p0 : p1,
      source: sourceCategory,
      venue_count: 0,
      primary_url: lpUrl,
    };
  } else {
    sourceCategory = "unresolved";
    confidence = "unresolved";
    const zeroSides = [];
    if (st0.n === 0) zeroSides.push(`${t0Name}${r0.canonical !== t0Name ? ` [resolved: ${r0.canonical}]` : ""} (0 prior official matches)`);
    if (st1.n === 0) zeroSides.push(`${t1Name}${r1.canonical !== t1Name ? ` [resolved: ${r1.canonical}]` : ""} (0 prior official matches)`);
    unresolvedReason = `Unverified / insufficient pre-kickoff evidence: no external betting line and ${zeroSides.join(" & ")} prior to ${startIso || "kickoff"}. Left blank rather than inferred.`;
  }

  // Post-kickoff official Leaguepedia score audit note (for stale cards only — NEVER affects p0/p1/pick)
  let postKickoffAudit = null;
  if (state === "stale" || state === "locked") {
    const compPage = COMP_TO_LP_PAGE[f.competition_name];
    if (compPage && startMs && nowMs > startMs) {
      const pkKey = `${compPage}::${[r0.canonical, r1.canonical].sort().join("|")}`;
      const hit = lpPostKickoffIndex.get(pkKey);
      if (hit && parseTimeMs(hit.utc) && Math.abs(parseTimeMs(hit.utc) - startMs) <= 12 * 3600 * 1000) {
        postKickoffAudit = {
          winner: hit.winner,
          score_text: `${hit.team1} ${hit.score1}–${hit.score2} ${hit.team2}`,
          source_url: lpUrl,
        };
      }
    }
  }

  // Generate transparent review flags for docs/flagged.html
  if (f.status === "scheduled") {
    if (r0.collision || r1.collision) {
      const col = r0.collision ? r0 : r1;
      flags.push({
        id: `entity-collision-${id}`,
        match_id: id,
        severity: "high",
        kind: "entity-collision",
        competition: f.competition_name,
        matchup: `${t0Name} vs ${t1Name}`,
        state,
        detail: col.note,
        hotspawn_url: hotspawnUrl,
        source_url: col.source_url || lpUrl,
      });
    }
    if (dq0 || dq1) {
      flags.push({
        id: `dq-walkover-${id}`,
        match_id: id,
        severity: "high",
        kind: "mid-split-disqualification",
        competition: f.competition_name,
        matchup: `${t0Name} vs ${t1Name}`,
        state,
        detail: unresolvedReason,
        hotspawn_url: hotspawnUrl,
        source_url: compDq.source_url,
      });
    } else if (sourceCategory === "unresolved") {
      flags.push({
        id: `unverified-zero-history-${id}`,
        match_id: id,
        severity: state === "stale" ? "low" : "medium",
        kind: "unverified-zero-history",
        competition: f.competition_name,
        matchup: `${t0Name} vs ${t1Name}`,
        state,
        detail: unresolvedReason + (postKickoffAudit ? ` Post-kickoff official Leaguepedia result: ${postKickoffAudit.score_text}.` : ""),
        hotspawn_url: hotspawnUrl,
        source_url: lpUrl,
      });
    }
    if (marketConsensus && marketConsensus.spread_pp >= 6.0) {
      flags.push({
        id: `venue-divergence-${id}`,
        match_id: id,
        severity: "low",
        kind: "cross-venue-divergence",
        competition: f.competition_name,
        matchup: `${t0Name} vs ${t1Name}`,
        state,
        detail: `Cross-venue implied probability spread is ${marketConsensus.spread_pp.toFixed(1)} pp across ${marketConsensus.venue_count} independent venues.`,
        hotspawn_url: hotspawnUrl,
        source_url: marketConsensus.primary_url,
      });
    }
  }

  matches.push({
    id,
    competition_id: f.competition_id,
    competition_name: f.competition_name,
    leaguepedia_page: COMP_TO_LP_PAGE[f.competition_name] ?? null,
    leaguepedia_url: lpUrl,
    status: f.status,
    state,
    tier: f.tier,
    stage: f.stage,
    best_of: Number(f.best_of) || 1,
    offered_points: f.offered_points,
    scheduled_start_time: startMs,
    start_iso: startIso,
    lock_time: lockMs,
    hotspawn_url: hotspawnUrl,
    team0: {
      id: f.participants[0].id,
      name: t0Name,
      canonical_name: r0.canonical,
      join_method: r0.join_method,
      join_note: r0.note,
      n_matches: st0.n,
      elo: Number(st0.rating.toFixed(1)),
    },
    team1: {
      id: f.participants[1].id,
      name: t1Name,
      canonical_name: r1.canonical,
      join_method: r1.join_method,
      join_note: r1.note,
      n_matches: st1.n,
      elo: Number(st1.rating.toFixed(1)),
    },
    score0: f.participants[0].score,
    score1: f.participants[1].score,
    p0,
    p1,
    pick_side: pickSide,
    pick,
    settlement_pick: settlementPick,
    source_category: sourceCategory,
    confidence,
    unresolved_reason: unresolvedReason,
    post_kickoff_audit: postKickoffAudit,
    market_consensus: marketConsensus,
    market_pinnacle: venueByKey.pinnacle ?? null,
    market_kambi: venueByKey.kambi ?? null,
    market_bovada: venueByKey.bovada ?? null,
    market_kalshi: venueByKey.kalshi ?? null,
    market_polymarket: venueByKey.polymarket ?? null,
    model: modelObj,
  });
}

// Add competition-level audit notice for multi-roster org pooling (Rich Gang in PRM 3rd Division + Komplettligaen)
const rgMatches = matches.filter(
  (m) => m.status === "scheduled" && m.competition_name === "PRM 3rd Division 26-27 Fall" && (m.team0.name === "Rich Gang" || m.team1.name === "Rich Gang")
);
if (rgMatches.length) {
  flags.push({
    id: "org-pooling-rich-gang-prm3",
    match_id: rgMatches[0].id,
    severity: "low",
    kind: "multi-roster-org-pooling",
    competition: "PRM 3rd Division 26-27 Fall",
    matchup: `Rich Gang (${rgMatches.length} scheduled series: ${rgMatches.map((m) => "#" + m.id).join(", ")})`,
    state: "open",
    detail: "Leaguepedia uses a single page 'Rich Gang (Norwegian Team)' across Komplettligaen 2026 Autumn and Prime League 3rd Division 26-27 Fall; model rating pools both rosters' pre-kickoff matches.",
    hotspawn_url: rgMatches[0].hotspawn_url,
    source_url: "https://lol.fandom.com/wiki/Prime_League_3rd_Division/2027_Season/Fall_Split",
  });
}

// Sort scheduled matches chronologically, then ended matches newest-first
matches.sort((a, b) => {
  const aSched = a.status === "scheduled" ? 0 : 1;
  const bSched = b.status === "scheduled" ? 0 : 1;
  if (aSched !== bSched) return aSched - bSched;
  if (aSched === 0) return (a.scheduled_start_time || 0) - (b.scheduled_start_time || 0);
  return (b.scheduled_start_time || 0) - (a.scheduled_start_time || 0);
});

/* ------------------------------------------- Update Pre-Lock History Ledger */

const histDir = path.join(DATA, "history");
await mkdir(histDir, { recursive: true });
const picksLatestPath = path.join(histDir, "picks_latest.json");
const ledgerPath = path.join(histDir, "ledger.json");

const picksLatest = (await readJSONSafe(picksLatestPath)) || {};
const rawById = new Map(hsRaw.fixtures.map((f) => [String(f.id), f]));

// Update picks_latest.json ONLY while match is pre-lock (`state === "open"`)
for (const m of matches) {
  if (m.state === "open" && m.pick && m.p0 != null) {
    const prev = picksLatest[m.id];
    const changed = prev && prev.team_index !== m.pick.team_index ? 1 : 0;
    picksLatest[m.id] = {
      first_seen: prev?.first_seen || generatedAt,
      last_updated: generatedAt,
      team_index: m.pick.team_index,
      team: m.pick.team_name,
      p: m.pick.probability,
      basis: m.source_category,
      lock_utc: m.lock_time ? new Date(m.lock_time).toISOString() : m.start_iso,
      start_utc: m.start_iso,
      competition: m.competition_name,
      t0: m.team0.name,
      t1: m.team1.name,
      changes: (prev?.changes || 0) + changed,
    };
  }
}
await writeFile(picksLatestPath, JSON.stringify(picksLatest, null, 1));

// Reconcile all historical pre-lock predictions in picks_latest.json against official Hotspawn outcomes
const ledgerEntries = [];
for (const [id, pl] of Object.entries(picksLatest)) {
  const rf = rawById.get(String(id));
  const p0Val = pl.team_index === 0 ? Number(pl.p) : Number((1 - Number(pl.p)).toFixed(4));
  const p1Val = Number((1 - p0Val).toFixed(4));
  const hotspawnUrl =
    permalinks[id] || slugifyHotspawn(pl.t0 || "", pl.t1 || "", pl.competition || "", id);

  let outcome = null;
  if (rf && (rf.status === "ended" || rf.status === "forfeited" || rf.status === "cancelled")) {
    const s0 = rf.participants[0].score;
    const s1 = rf.participants[1].score;
    const hasScore = s0 != null && s1 != null && Number(s0) !== Number(s1);
    const winIdx = rf.status === "ended" && hasScore ? (Number(s0) > Number(s1) ? 0 : 1) : null;
    outcome = {
      status: rf.status,
      score0: s0,
      score1: s1,
      winner_index: winIdx,
      correct: winIdx == null ? null : winIdx === pl.team_index,
      brier: winIdx == null ? null : Number(Math.pow(p0Val - (winIdx === 0 ? 1 : 0), 2).toFixed(4)),
    };
  }

  ledgerEntries.push({
    id: String(id),
    recorded_at: pl.first_seen,
    competition_name: pl.competition,
    start_iso: pl.start_utc,
    team0: pl.t0,
    team1: pl.t1,
    p0: p0Val,
    p1: p1Val,
    pick_index: pl.team_index,
    pick_team: pl.team,
    source_category: pl.basis,
    hotspawn_url: hotspawnUrl,
    outcome,
  });
}

// Sort settled entries first (newest kickoff first), then upcoming entries
ledgerEntries.sort((a, b) => {
  const aSettled = a.outcome ? 0 : 1;
  const bSettled = b.outcome ? 0 : 1;
  if (aSettled !== bSettled) return aSettled - bSettled;
  return String(b.start_iso || "").localeCompare(String(a.start_iso || ""));
});
const settledLedger = ledgerEntries.filter((e) => e.outcome && e.outcome.winner_index != null);
const ledgerSummary = {
  updated_at: generatedAt,
  total_entries: ledgerEntries.length,
  settled_entries: settledLedger.length,
  correct_entries: settledLedger.filter((e) => e.outcome.correct).length,
  mean_brier: settledLedger.length
    ? Number((settledLedger.reduce((a, e) => a + e.outcome.brier, 0) / settledLedger.length).toFixed(4))
    : null,
  entries: ledgerEntries,
};
await writeFile(ledgerPath, JSON.stringify(ledgerSummary, null, 2));

/* ------------------------------------------- Summary, Ratings, CSV & Writes */

const scheduledRows = matches.filter((m) => m.status === "scheduled");
const activeRows = scheduledRows.filter((m) => m.state === "open" || m.state === "locked" || m.state === "live");
const staleRows = scheduledRows.filter((m) => m.state === "stale");

const countsBySource = {};
for (const m of scheduledRows) {
  const key = m.settlement_pick ? "walkover_settlement" : m.source_category;
  countsBySource[key] = (countsBySource[key] || 0) + 1;
}

const activeCountsBySource = {};
for (const m of activeRows) {
  const key = m.settlement_pick ? "walkover_settlement" : m.source_category;
  activeCountsBySource[key] = (activeCountsBySource[key] || 0) + 1;
}

const summary = {
  generated_at: generatedAt,
  raw_hotspawn_fetched_at: hsRaw.fetched_at,
  counts: {
    total_rows: matches.length,
    scheduled_total: scheduledRows.length,
    active_open_locked: activeRows.length,
    stale_scheduled: staleRows.length,
    ended_recent: matches.filter((m) => m.state === "ended").length,
    forfeited_recent: matches.filter((m) => m.state === "forfeited").length,
    cancelled_recent: matches.filter((m) => m.state === "cancelled").length,
    active_market: activeRows.filter((m) => m.market_consensus != null).length,
    active_model: activeRows.filter((m) => m.market_consensus == null && m.pick != null).length,
    active_unresolved: activeRows.filter((m) => m.pick == null).length,
    scheduled_market: scheduledRows.filter((m) => m.market_consensus != null).length,
    scheduled_model: scheduledRows.filter((m) => m.market_consensus == null && m.pick != null).length,
    scheduled_walkover_settlement: scheduledRows.filter((m) => m.settlement_pick != null).length,
    scheduled_unresolved: scheduledRows.filter((m) => m.pick == null && m.settlement_pick == null).length,
    by_source_scheduled: countsBySource,
    by_source_active: activeCountsBySource,
    flags: flags.length,
  },
  sources_ok: {
    hotspawn: true,
    pinnacle: !pinBuilt.expired && pinBuilt.quotes.length > 0,
    kambi: !kambiBuilt.expired && kambiBuilt.quotes.length > 0,
    kalshi: !kalshiBuilt.expired && kalshiBuilt.quotes.length > 0,
    polymarket: !polyBuilt.expired && polyBuilt.quotes.length > 0,
    bovada_reachable: !bovBuilt.expired,
    leaguepedia: (lpRaw.matches || []).length > 0,
  },
  venue_quote_counts: {
    pinnacle: pinBuilt.quotes.length,
    pinnacle_excluded_kills: pinBuilt.rejected_kills,
    kambi: kambiBuilt.quotes.length,
    bovada: bovBuilt.quotes.length,
    kalshi: kalshiBuilt.quotes.length,
    polymarket: polyBuilt.quotes.length,
  },
  calibration,
};

await mkdir(path.join(DATA, "model"), { recursive: true });
await mkdir(DOCS_DATA, { recursive: true });

const topTeams = [...currentRatings.entries()]
  .filter(([, st]) => st.n >= 3)
  .sort((a, b) => b[1].rating - a[1].rating)
  .map(([team, st]) => ({
    team,
    elo: Number(st.rating.toFixed(1)),
    series: st.n,
    wins: st.wins,
    losses: st.losses,
    maps: `${st.mapsW}-${st.mapsL}`,
    last_played: st.last_ms ? new Date(st.last_ms).toISOString().slice(0, 10) : null,
  }));

const ratingsPayload = {
  generated_at: generatedAt,
  methodology: "Chronological pre-kickoff Elo/Bradley-Terry (initial 1500, dynamic K=38/28/22 with map-margin multiplier, empirical-Bayes tau=6 shrinkage, correlated-series damping alpha=0.72). Zero Hotspawn crowd/tier/points inputs; zero post-kickoff look-ahead.",
  teams_rated: topTeams.length,
  calibration,
  teams: topTeams,
};

const picksPayload = { summary, matches };
const flagsPayload = { generated_at: generatedAt, count: flags.length, flags };

await writeFile(path.join(DATA, "picks.json"), JSON.stringify(picksPayload, null, 2));
await writeFile(path.join(DOCS_DATA, "picks.json"), JSON.stringify(picksPayload, null, 2));
await writeFile(path.join(DATA, "flags.json"), JSON.stringify(flagsPayload, null, 2));
await writeFile(path.join(DOCS_DATA, "flags.json"), JSON.stringify(flagsPayload, null, 2));
await writeFile(path.join(DATA, "model", "ratings.json"), JSON.stringify(ratingsPayload, null, 2));

// Flat CSV export of all 241 scheduled Hotspawn LoL matches
function csvCell(v) {
  if (v == null) return "";
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
const csvHeader = [
  "id",
  "state",
  "start_iso",
  "competition",
  "best_of",
  "team0",
  "team1",
  "p0",
  "p1",
  "pick",
  "settlement_pick",
  "source_category",
  "venue_count",
  "hotspawn_url",
  "primary_source_url",
];
const csvLines = [csvHeader.join(",")];
for (const m of scheduledRows) {
  csvLines.push(
    [
      m.id,
      m.state,
      m.start_iso ?? "",
      m.competition_name,
      m.best_of,
      m.team0.name,
      m.team1.name,
      m.p0 ?? "",
      m.p1 ?? "",
      m.pick?.team_name ?? "",
      m.settlement_pick?.team_name ?? "",
      m.source_category,
      m.market_consensus?.venue_count ?? 0,
      m.hotspawn_url,
      m.pick?.primary_url ?? m.settlement_pick?.source_url ?? m.leaguepedia_url,
    ]
      .map(csvCell)
      .join(",")
  );
}
const csvText = csvLines.join("\n") + "\n";
await writeFile(path.join(DATA, "picks.csv"), csvText);
await writeFile(path.join(DOCS_DATA, "picks.csv"), csvText);

console.log(
  `analyze.mjs complete: ${scheduledRows.length} scheduled (${summary.counts.active_market} active market, ${summary.counts.active_model} active model, ${summary.counts.active_unresolved} active unresolved, ${ staleRows.length } stale) | OOS Brier=${calibration.brier} (n=${calibration.oos_evaluated}) | flags=${flags.length}`
);
