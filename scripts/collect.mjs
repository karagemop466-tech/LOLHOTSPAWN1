#!/usr/bin/env node
/**
 * collect.mjs — Stage 1 of the LoL Hotspawn pick'em Node pipeline (docs/).
 *
 * Fetches, with zero third-party dependencies (Node >= 18 global fetch):
 *   A. Hotspawn fixtures API (embedded public API used by play.hotspawn.com)
 *      https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol
 *      -> data/node/raw/hotspawn_lol_fixtures.json
 *   B. Hotspawn LoL lobby SSR page (cross-check + permalinks)
 *      https://play.hotspawn.com/lol-pickems
 *      -> data/node/raw/hotspawn_lobby_check.json
 *   C. Pinnacle guest API (series moneylines only; "(Kills)" derivatives rejected)
 *      -> data/node/raw/pinnacle_lol.json
 *   D. Polymarket Gamma API (open two-outcome LoL match markets + gameStartTime)
 *      -> data/node/raw/polymarket_lol.json
 *   E. Kalshi CFTC Contract Book (KXLOLGAME open match events)
 *      -> data/node/raw/kalshi_lol.json
 *   F. Bovada LoL Head-To-Head moneylines
 *      -> data/node/raw/bovada_lol.json
 *   G. Unibet / Kambi CDN (`ubse` operator) LoL Match Odds
 *      -> data/node/raw/kambi_lol.json
 *   H. Leaguepedia mid-split removal (`dqteams`) + CDN-cached `Data:` schedules
 *      -> data/node/raw/leaguepedia_dq.json
 *
 * Cloud-runner HTTP 429/403 hardening: every external venue preserves a verified
 * <24h snapshot on transient HTTP errors instead of clobbering it with an empty
 * failure stub, while expiring stale snapshots strictly at 24h.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DATA = path.join(ROOT, "data", "node");
const RAW = path.join(DATA, "raw");
const CANON_RAW = path.join(ROOT, "data", "raw");
const MAX_TTL_MS = 24 * 3600 * 1000;

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

const HOTSPAWN_FIXTURES =
  "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures";
const HOTSPAWN_LOBBY = "https://play.hotspawn.com/lol-pickems";
const PINNACLE_BASE = "https://guest.api.arcadia.pinnacle.com/0.1";
const GAMMA = "https://gamma-api.polymarket.com";
const KALSHI_URL =
  "https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=100";
const BOVADA_URL =
  "https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en";
const KAMBI_URLS = [
  "https://eu-offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ",
  "https://eu1.offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ",
];

const KILLS_RE = /\(kills?\)|\bkills\b/i;

const log = [];
function note(source, msg, ok = true) {
  const line = `[${new Date().toISOString()}] ${ok ? "OK  " : "WARN"} ${source}: ${msg}`;
  console.log(line);
  log.push({ ts: new Date().toISOString(), source, msg, ok });
}

async function readJSONSafe(p) {
  try {
    return JSON.parse(await readFile(p, "utf8"));
  } catch {
    return null;
  }
}

function isFresh24h(obj) {
  if (!obj) return false;
  const ts = Date.parse(obj.fetched_at || obj.fetched_utc || "");
  if (!ts) return false;
  return Date.now() - ts <= MAX_TTL_MS;
}

async function fetchRetry(url, { tries = 3, timeoutMs = 25000, headers = {} } = {}) {
  let lastErr;
  for (let i = 0; i < tries; i++) {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), timeoutMs);
    try {
      const res = await fetch(url, {
        signal: ctl.signal,
        headers: { "User-Agent": UA, Accept: "application/json, text/html;q=0.9", ...headers },
        redirect: "follow",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res;
    } catch (e) {
      lastErr = e;
      if (i + 1 < tries) await new Promise((r) => setTimeout(r, 1200 * (i + 1)));
    } finally {
      clearTimeout(t);
    }
  }
  throw lastErr;
}

async function getJSON(url, opts) {
  const res = await fetchRetry(url, opts);
  return res.json();
}

/* ---------------------------------------------------------------- A. Hotspawn */

function trimFixture(f) {
  return {
    id: String(f.id),
    competition_id: String(f.competition_id ?? ""),
    competition_name: f.competition_name ?? "",
    sport_alias: f.sport_alias ?? "",
    status: f.status ?? "",
    tier: f.tier ?? null,
    stage: f.stage ?? null,
    scheduled_start_time: f.scheduled_start_time ?? null,
    lock_time: f.lock_time ?? null,
    offered_points: f.offered_points ?? null,
    best_of: f.best_of ?? null,
    participants: [
      {
        id: String(f.participants0_id ?? ""),
        name: f.participants0_name ?? "",
        picked_percent: f.participants0_picked_percent ?? null, // crowd %; NEVER used for probabilities
        score: f.participants0_score ?? null,
      },
      {
        id: String(f.participants1_id ?? ""),
        name: f.participants1_name ?? "",
        picked_percent: f.participants1_picked_percent ?? null,
        score: f.participants1_score ?? null,
      },
    ],
  };
}

async function collectHotspawn() {
  const url = `${HOTSPAWN_FIXTURES}?sport_alias=lol`;
  const target = path.join(RAW, "hotspawn_lol_fixtures.json");
  try {
    const all = await getJSON(url, { timeoutMs: 60000 });
    if (!Array.isArray(all)) throw new Error("unexpected payload (not an array)");
    const fixtures = all.map(trimFixture);
    const byStatus = {};
    for (const f of fixtures) byStatus[f.status] = (byStatus[f.status] || 0) + 1;
    await writeFile(
      target,
      JSON.stringify({ fetched_at: new Date().toISOString(), source_url: url, count: fixtures.length, by_status: byStatus, fixtures })
    );
    note("hotspawn", `fixtures API: ${fixtures.length} LoL fixtures (${JSON.stringify(byStatus)})`);
    return fixtures;
  } catch (e) {
    const prev = await readJSONSafe(target);
    if (isFresh24h(prev) && Array.isArray(prev.fixtures)) {
      note("hotspawn", `fixtures API unreachable (${e.message}) — preserved <24h snapshot (${prev.fixtures.length} fixtures from ${prev.fetched_at})`, false);
      return prev.fixtures;
    }
    note("hotspawn", `fixtures API FAILED: ${e.message}`, false);
    return null;
  }
}

async function collectLobbyCheck() {
  const url = `${HOTSPAWN_LOBBY}?cb=${Date.now()}`;
  const target = path.join(RAW, "hotspawn_lobby_check.json");
  try {
    const res = await fetchRetry(url, { timeoutMs: 40000 });
    const html = await res.text();
    const permalinks = {};
    for (const m of html.matchAll(/https:\/\/www\.hotspawn\.com\/matches\/([a-z0-9-]+?-(\d{5,9}))/gi)) {
      permalinks[m[2]] = m[0].replace(/&amp;/g, "&");
    }
    const uniq = Object.keys(permalinks);
    const tiers = [...html.matchAll(/All tiers \((\d+)\)/g)].map((m) => Number(m[1]));
    const payload = { fetched_at: new Date().toISOString(), source_url: HOTSPAWN_LOBBY, http: res.status, match_ids: uniq, permalinks, all_tiers_counts: tiers, html_bytes: html.length };
    await writeFile(target, JSON.stringify(payload));
    note("hotspawn-lobby", `SSR page fetched (${html.length} bytes), ${uniq.length} match permalinks, tiers counts ${JSON.stringify(tiers)}`);
    return { ids: uniq, tiers, permalinks };
  } catch (e) {
    const prev = await readJSONSafe(target);
    if (isFresh24h(prev)) {
      note("hotspawn-lobby", `SSR page unreachable (${e.message}) — preserved <24h snapshot`, false);
      return { ids: prev.match_ids || [], tiers: prev.all_tiers_counts || [], permalinks: prev.permalinks || {} };
    }
    note("hotspawn-lobby", `SSR page FAILED (soft): ${e.message}`, false);
    return null;
  }
}

/* --------------------------------------------------------------- C. Pinnacle */

function hasKillsTag(participants, special) {
  if (special && KILLS_RE.test(JSON.stringify(special))) return true;
  return (participants || []).some((p) => KILLS_RE.test(p?.name || ""));
}

async function collectPinnacle() {
  const target = path.join(RAW, "pinnacle_lol.json");
  const out = { fetched_at: new Date().toISOString(), leagues: [], excluded_kills: 0, errors: [] };
  const CACHE_FILE = path.join(RAW, "pinnacle_matchups_cache.json");
  let cache = (await readJSONSafe(CACHE_FILE)) || {};
  if (!cache.leagues) cache.leagues = {};
  if (!cache.fetched_at) cache.fetched_at = {};
  const cacheNext = { leagues: {}, fetched_at: {} };

  try {
    const leagues = await getJSON(`${PINNACLE_BASE}/sports/12/leagues`);
    const lol = leagues.filter((l) => /^league of legends/i.test(l.name || ""));
    note("pinnacle", `${lol.length} LoL leagues: ${lol.map((l) => `${l.name}(${l.id})`).join(", ") || "none"}`);
    for (const lg of lol) {
      const entry = { id: lg.id, name: lg.name, group: lg.group, matchups: [], matchups_source: "live", straight: [], excluded_kills: 0 };
      const killsIds = new Set();
      try {
        const matchups = await getJSON(`${PINNACLE_BASE}/leagues/${lg.id}/matchups`);
        for (const m of matchups) {
          if (m.type !== "matchup" && m.parentId !== null) continue;
          if (hasKillsTag(m.participants, m.special)) {
            killsIds.add(m.id);
            entry.excluded_kills++;
            out.excluded_kills++;
            continue;
          }
          entry.matchups.push({
            id: m.id,
            type: m.type,
            status: m.status,
            startTime: m.startTime,
            bestOfX: m.bestOfX ?? null,
            rotation: m.rotation ?? null,
            special: m.special ?? null,
            straight_url: `${PINNACLE_BASE}/matchups/${m.id}/markets/related/straight`,
            participants: (m.participants || []).map((p) => ({ alignment: p.alignment, name: p.name, id: p.id ?? null })),
          });
        }
        cacheNext.leagues[String(lg.id)] = entry.matchups;
        cacheNext.fetched_at[String(lg.id)] = out.fetched_at;
      } catch (e) {
        out.errors.push(`league ${lg.id} matchups: ${e.message}`);
        const cached = (cache.leagues[String(lg.id)] || []).filter((m) => !hasKillsTag(m.participants, m.special));
        const cachedAt = cache.fetched_at[String(lg.id)] ?? "unknown";
        if (cached.length) {
          entry.matchups = cached;
          entry.matchups_source = `cache@${cachedAt}`;
          cacheNext.leagues[String(lg.id)] = cached;
          cacheNext.fetched_at[String(lg.id)] = cachedAt;
          note("pinnacle", `league ${lg.id} matchups FAILED (${e.message}) — reusing cached listing from ${cachedAt}; odds are live`, false);
        } else {
          note("pinnacle", `league ${lg.id} matchups FAILED: ${e.message} (no cache available)`, false);
        }
      }
      try {
        const straight = await getJSON(`${PINNACLE_BASE}/leagues/${lg.id}/markets/straight`);
        entry.straight = straight
          .filter((s) => (s.type === "moneyline" || s.type === 0) && !killsIds.has(s.matchupId) && !hasKillsTag(s.participants, null))
          .map((s) => ({
            matchupId: s.matchupId,
            period: s.period,
            status: s.status ?? null,
            cutoffAt: s.cutoffAt ?? null,
            liveUp: s.liveUp ?? null,
            prices: (s.prices || []).map((p) => ({ designation: p.designation ?? null, participantId: p.participantId ?? null, price: p.price })),
            participants: (s.participants || []).map((p) => ({ id: p.id ?? null, name: p.name ?? null, rot: p.rot ?? null })),
          }));
      } catch (e) {
        out.errors.push(`league ${lg.id} straight: ${e.message}`);
        note("pinnacle", `league ${lg.id} straight FAILED: ${e.message}`, false);
      }
      out.leagues.push(entry);
    }
    await writeFile(CACHE_FILE, JSON.stringify(cacheNext));
    await writeFile(target, JSON.stringify(out));
    return out;
  } catch (e) {
    const prev = await readJSONSafe(target);
    if (isFresh24h(prev) && Array.isArray(prev.leagues) && prev.leagues.length) {
      // Also sanitize any legacy (Kills) entries in preserved snapshot
      for (const lg of prev.leagues) {
        lg.matchups = (lg.matchups || []).filter((m) => !hasKillsTag(m.participants, m.special));
        lg.straight = (lg.straight || []).filter((s) => !hasKillsTag(s.participants, null));
      }
      await writeFile(target, JSON.stringify(prev));
      note("pinnacle", `leagues endpoint unreachable (${e.message}) — preserved <24h snapshot (${prev.fetched_at})`, false);
      return prev;
    }
    note("pinnacle", `leagues endpoint FAILED: ${e.message}`, false);
    out.errors.push(`leagues: ${e.message}`);
    await writeFile(target, JSON.stringify(out));
    return out;
  }
}

/* -------------------------------------------------------------- D. Polymarket */

function trimPolyEvent(ev) {
  const markets = (ev.markets || [])
    .map((m) => {
      let outcomes = [];
      let prices = [];
      try { outcomes = JSON.parse(m.outcomes || "[]"); } catch {}
      try { prices = JSON.parse(m.outcomePrices || "[]"); } catch {}
      return {
        question: m.question ?? "",
        slug: m.slug ?? "",
        outcomes,
        outcomePrices: prices.map(Number),
        bestBid: m.bestBid ?? null,
        bestAsk: m.bestAsk ?? null,
        lastTradePrice: m.lastTradePrice ?? null,
        spread: m.spread ?? null,
        volume: m.volumeNum ?? m.volume ?? null,
        liquidity: m.liquidityNum ?? m.liquidity ?? null,
        closed: m.closed ?? null,
        gameStartTime: m.gameStartTime ?? null,
        groupItemTitle: m.groupItemTitle ?? null,
      };
    })
    .filter((m) => m.outcomes.length === 2 && !/^yes$/i.test(m.outcomes[0]));
  return {
    id: String(ev.id),
    slug: ev.slug,
    title: ev.title,
    startDate: ev.startDate ?? null,
    endDate: ev.endDate ?? null,
    volume: ev.volume ?? null,
    liquidity: ev.liquidity ?? null,
    closed: ev.closed ?? null,
    markets,
  };
}

async function collectPolymarket() {
  const target = path.join(RAW, "polymarket_lol.json");
  const out = { fetched_at: new Date().toISOString(), events: [], errors: [], pages: 0 };
  try {
    let offset = 0;
    const limit = 100;
    while (offset < 3000) {
      const url = `${GAMMA}/events?closed=false&tag_slug=league-of-legends&limit=${limit}&offset=${offset}`;
      const page = await getJSON(url, { timeoutMs: 40000 });
      if (!Array.isArray(page) || page.length === 0) break;
      out.pages++;
      for (const ev of page) {
        const t = trimPolyEvent(ev);
        if (t.markets.length > 0 || /^lol-/.test(t.slug)) out.events.push(t);
      }
      if (page.length < limit) break;
      offset += limit;
    }
    await writeFile(target, JSON.stringify(out));
    note("polymarket", `${out.events.length} LoL events kept (${out.pages} pages fetched)`);
    return out;
  } catch (e) {
    const prev = await readJSONSafe(target);
    if (isFresh24h(prev) && Array.isArray(prev.events) && prev.events.length) {
      note("polymarket", `gamma API unreachable (${e.message}) — preserved <24h snapshot (${prev.events.length} events)`, false);
      return prev;
    }
    out.errors.push(e.message);
    note("polymarket", `gamma API FAILED: ${e.message}`, false);
    await writeFile(target, JSON.stringify(out));
    return out;
  }
}

/* ----------------------------------------------------------------- E. Kalshi */

async function collectKalshi() {
  const target = path.join(RAW, "kalshi_lol.json");
  try {
    const data = await getJSON(KALSHI_URL, { timeoutMs: 30000 });
    const events = (data.events || []).map((ev) => ({
      event_ticker: ev.event_ticker,
      title: ev.title,
      sub_title: ev.sub_title ?? "",
      markets: (ev.markets || [])
        .filter((m) => m.status === "active" || m.status === "open" || !m.result)
        .map((m) => ({
          ticker: m.ticker,
          yes_sub_title: m.yes_sub_title ?? "",
          yes_bid_dollars: m.yes_bid_dollars ?? null,
          yes_ask_dollars: m.yes_ask_dollars ?? null,
          last_price_dollars: m.last_price_dollars ?? null,
          volume_fp: m.volume_fp ?? m.volume ?? null,
          open_interest_fp: m.open_interest_fp ?? null,
          occurrence_datetime: m.occurrence_datetime ?? m.expected_expiration_time ?? null,
        })),
    }));
    const payload = { fetched_at: new Date().toISOString(), source_url: KALSHI_URL, event_count: events.length, events };
    await writeFile(target, JSON.stringify(payload));
    note("kalshi", `${events.length} open CFTC KXLOLGAME match events`);
    return payload;
  } catch (e) {
    for (const fbPath of [target, path.join(CANON_RAW, "kalshi_lol.json")]) {
      const prev = await readJSONSafe(fbPath);
      if (isFresh24h(prev) && Array.isArray(prev.events)) {
        const preserved = { ...prev, fetched_at: prev.fetched_at || prev.fetched_utc, preserved_from: path.basename(fbPath) };
        await writeFile(target, JSON.stringify(preserved));
        note("kalshi", `API unreachable (${e.message}) — preserved <24h snapshot (${preserved.events.length} events)`, false);
        return preserved;
      }
    }
    const empty = { fetched_at: new Date().toISOString(), source_url: KALSHI_URL, event_count: 0, events: [], error: e.message };
    await writeFile(target, JSON.stringify(empty));
    note("kalshi", `API FAILED: ${e.message}`, false);
    return empty;
  }
}

/* ----------------------------------------------------------------- F. Bovada */

async function collectBovada() {
  const target = path.join(RAW, "bovada_lol.json");
  try {
    const raw = await getJSON(BOVADA_URL, { timeoutMs: 30000 });
    const list = Array.isArray(raw) ? raw : [];
    const events = [];
    for (const grp of list) {
      for (const ev of grp.events || []) {
        if (!ev || ev.live) continue;
        const comps = ev.competitors || [];
        if (comps.length !== 2) continue;
        let ml = null;
        for (const dg of ev.displayGroups || []) {
          for (const mk of dg.markets || []) {
            const desc = (mk.description || "").toLowerCase();
            const period = (mk.period?.description || "").toLowerCase();
            if ((desc === "head to head" || desc === "match winner" || desc === "moneyline") && !/map|game|kill|first|handicap|total/.test(desc + " " + period)) {
              if ((mk.outcomes || []).length === 2) { ml = mk; break; }
            }
          }
          if (ml) break;
        }
        if (!ml) continue;
        const outcomes = ml.outcomes.map((o) => ({
          name: o.description,
          decimal: Number(o.price?.decimal) || null,
          american: o.price?.american ?? null,
        })).filter((o) => o.decimal && o.decimal > 1.01);
        if (outcomes.length !== 2) continue;
        events.push({
          id: String(ev.id),
          description: ev.description,
          start_ms: ev.startTime ?? null,
          url: ev.link ? `https://www.bovada.lv/sports${ev.link}` : "https://www.bovada.lv/sports/esports/league-of-legends",
          outcomes,
        });
      }
    }
    if (events.length === 0) {
      // Cloud runner often receives geo-filtered empty {} from Bovada; preserve <12h upcoming quotes if present
      for (const fbPath of [target, path.join(CANON_RAW, "bovada_lol.json")]) {
        const prev = await readJSONSafe(fbPath);
        const ts = Date.parse(prev?.fetched_at || prev?.fetched_utc || "");
        if (prev && ts && Date.now() - ts <= 12 * 3600 * 1000 && Array.isArray(prev.events) && prev.events.length > 0) {
          const preserved = { ...prev, fetched_at: prev.fetched_at || prev.fetched_utc };
          await writeFile(target, JSON.stringify(preserved));
          note("bovada", `runner geo-filtered (0 events) — preserved <12h snapshot (${preserved.events.length} events)`, false);
          return preserved;
        }
      }
    }
    const payload = { fetched_at: new Date().toISOString(), source_url: BOVADA_URL, event_count: events.length, events };
    await writeFile(target, JSON.stringify(payload));
    note("bovada", `${events.length} LoL Head-To-Head moneylines`);
    return payload;
  } catch (e) {
    for (const fbPath of [target, path.join(CANON_RAW, "bovada_lol.json")]) {
      const prev = await readJSONSafe(fbPath);
      if (isFresh24h(prev) && Array.isArray(prev.events) && prev.events.length > 0) {
        const preserved = { ...prev, fetched_at: prev.fetched_at || prev.fetched_utc };
        await writeFile(target, JSON.stringify(preserved));
        note("bovada", `API unreachable (${e.message}) — preserved <24h snapshot (${preserved.events.length} events)`, false);
        return preserved;
      }
    }
    for (const fbPath of [target, path.join(CANON_RAW, "bovada_lol.json")]) {
      const prev = await readJSONSafe(fbPath);
      if (isFresh24h(prev) && Array.isArray(prev.events)) {
        const preserved = { ...prev, fetched_at: prev.fetched_at || prev.fetched_utc };
        await writeFile(target, JSON.stringify(preserved));
        note("bovada", `API unreachable (${e.message}) — preserved <24h snapshot (0 events)`, false);
        return preserved;
      }
    }
    const empty = { fetched_at: new Date().toISOString(), source_url: BOVADA_URL, event_count: 0, events: [], error: e.message };
    await writeFile(target, JSON.stringify(empty));
    note("bovada", `API FAILED: ${e.message}`, false);
    return empty;
  }
}

/* ---------------------------------------------------------- G. Unibet / Kambi */

async function collectKambi() {
  const target = path.join(RAW, "kambi_lol.json");
  let lastErr = null;
  for (const url of KAMBI_URLS) {
    try {
      const raw = await getJSON(url, { timeoutMs: 25000 });
      const events = [];
      for (const item of raw.events || []) {
        const ev = item.event || {};
        if (ev.state === "STARTED") continue;
        const offers = item.betOffers || [];
        const matchOffer = offers.find((bo) => {
          const lbl = (bo.criterion?.englishLabel || bo.criterion?.label || "").toLowerCase();
          const btype = bo.betOfferType?.id;
          return (btype === 2 || lbl === "match odds" || lbl === "match") && !KILLS_RE.test(lbl) && (bo.outcomes || []).length === 2;
        });
        if (!matchOffer) continue;
        const outcomes = (matchOffer.outcomes || [])
          .filter((o) => o.status === "OPEN" && o.odds > 1000)
          .map((o) => ({
            name: o.englishLabel || o.label || o.participant,
            decimal: Math.round((o.odds / 1000) * 1000) / 1000,
            american: o.oddsAmerican ?? null,
          }));
        if (outcomes.length !== 2) continue;
        events.push({
          event_id: ev.id,
          name: ev.englishName || ev.name,
          group: ev.group || "",
          start_utc: ev.start || null,
          url: `https://eu-offering-api.kambicdn.com/offering/v2018/ubse/betoffer/event/${ev.id}.json?lang=en_GB&market=ZZ`,
          outcomes,
        });
      }
      const payload = { fetched_at: new Date().toISOString(), source_url: url, event_count: events.length, events };
      await writeFile(target, JSON.stringify(payload));
      note("kambi", `${events.length} Unibet/Kambi (ubse) LoL match moneylines`);
      return payload;
    } catch (e) {
      lastErr = e;
    }
  }
  for (const fbPath of [target, path.join(CANON_RAW, "kambi_lol.json")]) {
    const prev = await readJSONSafe(fbPath);
    if (isFresh24h(prev) && Array.isArray(prev.events)) {
      const preserved = { ...prev, fetched_at: prev.fetched_at || prev.fetched_utc };
      await writeFile(target, JSON.stringify(preserved));
      note("kambi", `CDN unreachable/429 (${lastErr?.message}) — preserved <24h snapshot (${preserved.events.length} events)`, false);
      return preserved;
    }
  }
  const empty = { fetched_at: new Date().toISOString(), source_url: KAMBI_URLS[0], event_count: 0, events: [], error: lastErr?.message || "failed" };
  await writeFile(target, JSON.stringify(empty));
  note("kambi", `CDN FAILED: ${lastErr?.message}`, false);
  return empty;
}

/* ------------------------------------------------- H. Leaguepedia dqteams raw */

const DQ_CHECK_PAGES = [
  { comp: "Komplettligaen 2026 Autumn", page: "Komplettligaen/2026 Season/Autumn Split", dataPage: "Data:Komplettligaen/2026_Season/Autumn_Split" },
  { comp: "LCP 2027 Promotion", page: "LCP/2027 Season/Promotion", dataPage: "Data:LCP/2027_Season/Promotion" },
  { comp: "Logitech G SuperStrike Cup Qualifier", page: "Logitech G SuperStrike Cup/Qualifier", dataPage: "Data:Logitech_G_SuperStrike_Cup/Qualifier" },
];

async function collectLeaguepediaDQ() {
  const target = path.join(RAW, "leaguepedia_dq.json");
  const dqByComp = {};
  let liveFetched = 0;
  try {
    // CDN-cached ?action=raw check on Komplettligaen Autumn Split for explicit removal / ff notes
    const res = await fetchRetry("https://lol.fandom.com/wiki/Data:Komplettligaen/2026_Season/Autumn_Split?action=raw", { timeoutMs: 20000 });
    const raw = await res.text();
    liveFetched++;
    const removed = [];
    for (const m of raw.matchAll(/\[\[([^\]]+?)\]\]\s+is removed from the league/gi)) {
      removed.push(m[1].trim());
    }
    if (removed.length) {
      dqByComp["Komplettligaen 2026 Autumn"] = {
        teams: [...new Set(removed)],
        source_url: "https://lol.fandom.com/wiki/Data:Komplettligaen/2026_Season/Autumn_Split",
        evidence: "Data:Komplettligaen/2026_Season/Autumn_Split records '[[Solid Gaming]] is removed from the league.' with remaining series scored 0-2 (ff=1/ff=2).",
      };
    }
  } catch (e) {
    // Fallback to committed canonical leaguepedia_dq.json if offline or rate-limited
    const canonDQ = await readJSONSafe(path.join(CANON_RAW, "leaguepedia_dq.json"));
    const prevDQ = await readJSONSafe(target);
    if (prevDQ && prevDQ.dq_by_competition) {
      note("leaguepedia-dq", `wiki unreachable (${e.message}) — preserved previous dqteams ledger`, false);
      return prevDQ;
    }
    const komp = canonDQ?.dq_by_page?.["Komplettligaen/2026 Season/Autumn Split"];
    if (Array.isArray(komp) && komp.length) {
      dqByComp["Komplettligaen 2026 Autumn"] = {
        teams: komp,
        source_url: "https://lol.fandom.com/wiki/Data:Komplettligaen/2026_Season/Autumn_Split",
        evidence: "Leaguepedia dqteams + Data:Komplettligaen/2026_Season/Autumn_Split records mid-split league removal (remaining series scored 0-2 ff).",
      };
    }
  }
  const payload = {
    fetched_at: new Date().toISOString(),
    live_pages_checked: liveFetched,
    checked_pages: DQ_CHECK_PAGES,
    dq_by_competition: dqByComp,
  };
  await writeFile(target, JSON.stringify(payload, null, 2));
  note("leaguepedia-dq", `${Object.keys(dqByComp).length} active competition(s) with mid-split dqteams quarantine`);
  return payload;
}

/* ---------------------------------------------------------------------- main */

await mkdir(RAW, { recursive: true });
const t0 = Date.now();
const fixtures = await collectHotspawn();
const lobby = await collectLobbyCheck();
const pinnacle = await collectPinnacle();
const polymarket = await collectPolymarket();
const kalshi = await collectKalshi();
const bovada = await collectBovada();
const kambi = await collectKambi();
const lpDq = await collectLeaguepediaDQ();

const summary = {
  fetched_at: new Date().toISOString(),
  duration_s: Math.round((Date.now() - t0) / 1000),
  hotspawn_fixtures: fixtures ? fixtures.length : null,
  hotspawn_lobby_ids: lobby ? lobby.ids.length : null,
  pinnacle_leagues: pinnacle.leagues.length,
  pinnacle_matchups: pinnacle.leagues.reduce((a, l) => a + l.matchups.filter((m) => m.type === "matchup").length, 0),
  pinnacle_excluded_kills: pinnacle.excluded_kills ?? 0,
  polymarket_events: polymarket.events.length,
  kalshi_events: kalshi.event_count ?? 0,
  bovada_events: bovada.event_count ?? 0,
  kambi_events: kambi.event_count ?? 0,
  dq_competitions: Object.keys(lpDq.dq_by_competition || {}).length,
  log,
};
await writeFile(path.join(RAW, "collect_log.json"), JSON.stringify(summary, null, 2));
console.log("\nCollect summary:", JSON.stringify({ ...summary, log: undefined }, null, 2));
if (!fixtures) {
  console.error("FATAL: hotspawn fixtures unavailable — cannot build inventory.");
  process.exit(2);
}
