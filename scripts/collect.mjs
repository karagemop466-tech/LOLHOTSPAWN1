#!/usr/bin/env node
/**
 * collect.mjs — Stage 1 of the LoL Hotspawn pick'em pipeline.
 *
 * Fetches, with no third-party dependencies (Node >= 18 global fetch):
 *   A. Hotspawn fixtures API (embedded public API used by play.hotspawn.com)
 *      https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol
 *      -> data/raw/hotspawn_lol_fixtures.json  (ALL LoL fixtures incl. ended history)
 *   B. Hotspawn LoL lobby SSR page (cross-check only; may be CDN-cached or 403)
 *      https://play.hotspawn.com/lol-pickems
 *      -> data/raw/hotspawn_lobby_check.json   (counts + match ids scraped from HTML)
 *   C. Pinnacle guest API (no auth needed on bulk endpoints; verified 2026-10-21)
 *      /0.1/sports/12/leagues                       -> LoL leagues
 *      /0.1/leagues/{id}/matchups                   -> teams + start times
 *      /0.1/leagues/{id}/markets/straight           -> moneyline odds (American)
 *      -> data/raw/pinnacle_lol.json
 *   D. Polymarket gamma API
 *      /events?closed=false&tag_slug=league-of-legends (paginated)
 *      -> data/raw/polymarket_lol.json
 *
 * Every fetch is retried 3x with backoff. Failures are recorded in
 * data/raw/collect_log.json and never crash the run (downstream degrades
 * gracefully and flags the gap).
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const RAW = path.join(ROOT, "data", "raw");

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

const HOTSPAWN_FIXTURES =
  "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures";
const HOTSPAWN_LOBBY = "https://play.hotspawn.com/lol-pickems";
const PINNACLE_BASE = "https://guest.api.arcadia.pinnacle.com/0.1";
const GAMMA = "https://gamma-api.polymarket.com";

const log = [];
function note(source, msg, ok = true) {
  const line = `[${new Date().toISOString()}] ${ok ? "OK  " : "WARN"} ${source}: ${msg}`;
  console.log(line);
  log.push({ ts: new Date().toISOString(), source, msg, ok });
}

async function fetchRetry(url, { tries = 3, timeoutMs = 30000, headers = {} } = {}) {
  let lastErr;
  for (let i = 0; i < tries; i++) {
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), timeoutMs);
      const res = await fetch(url, {
        signal: ctl.signal,
        headers: { "User-Agent": UA, Accept: "application/json, text/html;q=0.9", ...headers },
        redirect: "follow",
      });
      clearTimeout(t);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res;
    } catch (e) {
      lastErr = e;
      await new Promise((r) => setTimeout(r, 1500 * (i + 1)));
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
    scheduled_start_time: f.scheduled_start_time ?? null, // epoch ms (string)
    lock_time: f.lock_time ?? null, // epoch ms (string)
    offered_points: f.offered_points ?? null,
    best_of: f.best_of ?? null,
    participants: [
      {
        id: String(f.participants0_id ?? ""),
        name: f.participants0_name ?? "",
        picked_percent: f.participants0_picked_percent ?? null, // crowd %; NOT used for probabilities
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
  try {
    const all = await getJSON(url, { timeoutMs: 60000 });
    if (!Array.isArray(all)) throw new Error("unexpected payload (not an array)");
    const fixtures = all.map(trimFixture);
    const byStatus = {};
    for (const f of fixtures) byStatus[f.status] = (byStatus[f.status] || 0) + 1;
    await writeFile(
      path.join(RAW, "hotspawn_lol_fixtures.json"),
      JSON.stringify({ fetched_at: new Date().toISOString(), source_url: url, count: fixtures.length, by_status: byStatus, fixtures })
    );
    note("hotspawn", `fixtures API: ${fixtures.length} LoL fixtures (${JSON.stringify(byStatus)})`);
    return fixtures;
  } catch (e) {
    note("hotspawn", `fixtures API FAILED: ${e.message}`, false);
    return null;
  }
}

async function collectLobbyCheck() {
  // SSR cross-check of the rendered lobby. Soft failure only (CDN cache / 403 seen historically).
  const url = `${HOTSPAWN_LOBBY}?cb=${Date.now()}`;
  try {
    const res = await fetchRetry(url, { timeoutMs: 45000 });
    const html = await res.text();
    const permalinks = {};
    for (const m of html.matchAll(/https:\/\/www\.hotspawn\.com\/matches\/([a-z0-9-]+?-(\d{5,9}))/gi)) {
      permalinks[m[2]] = m[0].replace(/&amp;/g, "&");
    }
    const uniq = Object.keys(permalinks);
    const tiers = [...html.matchAll(/All tiers \((\d+)\)/g)].map((m) => Number(m[1]));
    await writeFile(
      path.join(RAW, "hotspawn_lobby_check.json"),
      JSON.stringify({ fetched_at: new Date().toISOString(), source_url: HOTSPAWN_LOBBY, http: res.status, match_ids: uniq, permalinks, all_tiers_counts: tiers, html_bytes: html.length })
    );
    note("hotspawn-lobby", `SSR page fetched (${html.length} bytes), ${uniq.length} match permalinks, tiers counts ${JSON.stringify(tiers)}`);
    return { ids: uniq, tiers, permalinks };
  } catch (e) {
    note("hotspawn-lobby", `SSR page FAILED (soft): ${e.message}`, false);
    return null;
  }
}

/* --------------------------------------------------------------- C. Pinnacle */

async function collectPinnacle() {
  const out = { fetched_at: new Date().toISOString(), leagues: [], errors: [] };
  // The guest /matchups endpoint intermittently returns 401 even after retries
  // (observed 2026-10-21). Matchup IDs are stable across fetches, so we cache
  // the last successful listing and fall back to it — odds always come from
  // the live /markets/straight response; only the team-name/start-time listing
  // may come from cache, and that is recorded for audit.
  const CACHE_FILE = path.join(RAW, "pinnacle_matchups_cache.json");
  let cache = {};
  try { cache = JSON.parse(await readFile(CACHE_FILE, "utf8")); } catch { cache = {}; }
  if (!cache.leagues) cache.leagues = {};
  if (!cache.fetched_at) cache.fetched_at = {};
  const cacheNext = { leagues: {}, fetched_at: {} };
  try {
    const leagues = await getJSON(`${PINNACLE_BASE}/sports/12/leagues`);
    const lol = leagues.filter((l) => /^league of legends/i.test(l.name || ""));
    note("pinnacle", `${lol.length} LoL leagues: ${lol.map((l) => `${l.name}(${l.id})`).join(", ") || "none"}`);
    for (const lg of lol) {
      const entry = { id: lg.id, name: lg.name, group: lg.group, matchups: [], matchups_source: "live", straight: [] };
      try {
        const matchups = await getJSON(`${PINNACLE_BASE}/leagues/${lg.id}/matchups`);
        entry.matchups = matchups
          .filter((m) => m.type === "matchup" || m.parentId === null)
          .map((m) => ({
            id: m.id,
            type: m.type,
            status: m.status,
            startTime: m.startTime,
            bestOfX: m.bestOfX ?? null,
            rotation: m.rotation ?? null,
            special: m.special ?? null,
            participants: (m.participants || []).map((p) => ({ alignment: p.alignment, name: p.name, id: p.id ?? null })),
          }));
        cacheNext.leagues[String(lg.id)] = entry.matchups;
        cacheNext.fetched_at[String(lg.id)] = out.fetched_at;
      } catch (e) {
        out.errors.push(`league ${lg.id} matchups: ${e.message}`);
        const cached = cache.leagues[String(lg.id)];
        const cachedAt = cache.fetched_at[String(lg.id)] ?? "unknown";
        if (Array.isArray(cached) && cached.length) {
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
          .filter((s) => s.type === "moneyline" || s.type === 0)
          .map((s) => ({
            matchupId: s.matchupId,
            period: s.period,
            status: s.status ?? null,
            cutoffAt: s.cutoffAt ?? null,
            liveUp: s.liveUp ?? null,
            prices: (s.prices || []).map((p) => ({ designation: p.designation ?? null, participantId: p.participantId ?? null, price: p.price })),
            // participant names ride along on each odds line — this allows the
            // analyzer to reconstruct head-to-head pairs even when the separate
            // /matchups endpoint intermittently 401s (observed 2026-10-21).
            participants: (s.participants || []).map((p) => ({ id: p.id ?? null, name: p.name ?? null, rot: p.rot ?? null })),
          }));
      } catch (e) {
        out.errors.push(`league ${lg.id} straight: ${e.message}`);
        note("pinnacle", `league ${lg.id} straight FAILED: ${e.message}`, false);
      }
      out.leagues.push(entry);
    }
    await writeFile(path.join(RAW, "pinnacle_matchups_cache.json"), JSON.stringify(cacheNext));
    await writeFile(path.join(RAW, "pinnacle_lol.json"), JSON.stringify(out));
    return out;
  } catch (e) {
    note("pinnacle", `leagues endpoint FAILED: ${e.message}`, false);
    out.errors.push(`leagues: ${e.message}`);
    await writeFile(path.join(RAW, "pinnacle_matchups_cache.json"), JSON.stringify(cacheNext));
    await writeFile(path.join(RAW, "pinnacle_lol.json"), JSON.stringify(out));
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
        groupItemTitle: m.groupItemTitle ?? null,
      };
    })
    // keep two-outcome team markets (match moneylines); drop Yes/No props
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
  const out = { fetched_at: new Date().toISOString(), events: [], errors: [], pages: 0 };
  try {
    let offset = 0;
    const limit = 100;
    while (offset < 3000) {
      const url = `${GAMMA}/events?closed=false&tag_slug=league-of-legends&limit=${limit}&offset=${offset}`;
      const page = await getJSON(url, { timeoutMs: 45000 });
      if (!Array.isArray(page) || page.length === 0) break;
      out.pages++;
      for (const ev of page) {
        const t = trimPolyEvent(ev);
        // keep only events that look like matches (>=1 two-outcome team market) or explicit lol-* match slugs
        if (t.markets.length > 0 || /^lol-/.test(t.slug)) out.events.push(t);
      }
      if (page.length < limit) break;
      offset += limit;
    }
    note("polymarket", `${out.events.length} LoL events kept (${out.pages} pages fetched)`);
  } catch (e) {
    out.errors.push(e.message);
    note("polymarket", `gamma API FAILED: ${e.message}`, false);
  }
  await writeFile(path.join(RAW, "polymarket_lol.json"), JSON.stringify(out));
  return out;
}

/* ---------------------------------------------------------------------- main */

await mkdir(RAW, { recursive: true });
const t0 = Date.now();
const [fixtures, lobby, pinnacle, polymarket] = [
  await collectHotspawn(),
  await collectLobbyCheck(),
  await collectPinnacle(),
  await collectPolymarket(),
];

const summary = {
  fetched_at: new Date().toISOString(),
  duration_s: Math.round((Date.now() - t0) / 1000),
  hotspawn_fixtures: fixtures ? fixtures.length : null,
  hotspawn_lobby_ids: lobby ? lobby.ids.length : null,
  pinnacle_leagues: pinnacle.leagues.length,
  pinnacle_matchups: pinnacle.leagues.reduce((a, l) => a + l.matchups.filter((m) => m.type === "matchup").length, 0),
  polymarket_events: polymarket.events.length,
  log,
};
await writeFile(path.join(RAW, "collect_log.json"), JSON.stringify(summary, null, 2));
console.log("\nCollect summary:", JSON.stringify({ ...summary, log: undefined }, null, 2));
if (!fixtures) {
  console.error("FATAL: hotspawn fixtures unavailable — cannot build inventory.");
  process.exit(2);
}
