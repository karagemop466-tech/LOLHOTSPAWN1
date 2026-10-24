#!/usr/bin/env node
/**
 * test_node_pipeline.mjs — Independent verification tests for session 6669f798
 * covering the secondary Node pipeline (scripts/*.mjs -> docs/* & data/node/*).
 */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const picks = JSON.parse(await readFile(path.join(ROOT, "data", "node", "picks.json"), "utf8"));
const flags = JSON.parse(await readFile(path.join(ROOT, "data", "node", "flags.json"), "utf8"));
const ratings = JSON.parse(await readFile(path.join(ROOT, "data", "node", "model", "ratings.json"), "utf8"));
const analyzeSrc = await readFile(path.join(ROOT, "scripts", "analyze.mjs"), "utf8");

const scheduled = picks.matches.filter((m) => m.status === "scheduled");
const byId = new Map(scheduled.map((m) => [m.id, m]));

// 1. Complete 241-fixture inventory reconciliation
const hsRaw = JSON.parse(await readFile(path.join(ROOT, "data", "node", "raw", "hotspawn_lol_fixtures.json"), "utf8"));
const rawSchedIds = hsRaw.fixtures.filter((f) => f.status === "scheduled").map((f) => String(f.id)).sort();
const pubSchedIds = scheduled.map((m) => m.id).sort();
assert.deepEqual(pubSchedIds, rawSchedIds, "scheduled match IDs must reconcile 1:1 with Hotspawn raw feed");

// 2. Zero Hotspawn crowd/tier/points leakage in probability/Elo functions
const strippedSrc = analyzeSrc.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, "");
assert.equal(strippedSrc.includes("picked_percent"), false, "picked_percent must never appear anywhere in analyze.mjs executable code");
const modelSection = strippedSrc.slice(0, strippedSrc.indexOf("const nowMs = Date.now();"));
assert.equal(modelSection.includes("offered_points"), false, "offered_points must never appear in model/consensus logic");

// 3. Multi-venue market consensus: all 8 Worlds Round 2 series have 4 independent venues, #1079080 has 2 venues (Kalshi + Polymarket)
const mktRows = scheduled.filter((m) => m.market_consensus != null);
assert.equal(mktRows.length, 9, "expected 9 market-backed series (8 Worlds + 1 LGC Rising)");
for (const m of mktRows) {
  if (m.competition_name === "Worlds 2026 Main Event") {
    assert.ok(m.market_consensus.venue_count >= 4, `Worlds match #${m.id} should match >=4 live venues`);
  }
  if (m.id === "1079080") {
    assert.equal(m.market_consensus.venue_count, 2, "LGC Rising #1079080 should match Kalshi CFTC + Polymarket");
    assert.ok(m.market_kalshi, "#1079080 must include Kalshi CFTC KXLOLGAME-26OCT271300RBMR");
    assert.ok(m.market_polymarket, "#1079080 must include Polymarket lol-rb-mr-2026-10-27");
  }
}

// 4. Cross-region homonym quarantines (#1083097 PNG vs paiN Gaming; #1079031 PvB vs Phong Vũ Buffalo)
const png = byId.get("1083097");
assert.ok(png, "#1083097 present");
assert.equal(png.team0.canonical_name, "PNG", "#1083097 must quarantine paiN Gaming -> Bulgarian PNG");
assert.equal(png.p0, null, "#1083097 must leave probability blank (0 prior matches)");
assert.equal(png.pick, null, "#1083097 must have no sporting pick");

const pvb = byId.get("1079031");
assert.ok(pvb, "#1079031 present");
assert.equal(pvb.team1.canonical_name, "PvB (Swiss Team)", "#1079031 must resolve Phong Vũ Buffalo -> PvB (Swiss Team)");
assert.ok(pvb.p0 > 0 && pvb.p0 < 1, "#1079031 priced from Swiss PvB Elo");

// 5. LCP 2027 Promotion #1081423 resolved via pre-kickoff Elo
const lcp = byId.get("1081423");
assert.ok(lcp, "#1081423 present");
assert.equal(lcp.pick.team_name, "Frank Esports", "#1081423 Frank Esports favored on pre-kickoff Elo");

// 6. Mid-split disqualification walkover settlements (Solid Gaming in Komplettligaen 2026 Autumn)
for (const dqId of ["1071170", "1071200", "1071206", "1071186"]) {
  const m = byId.get(dqId);
  assert.ok(m, `#${dqId} present`);
  assert.equal(m.p0, null, `#${dqId} DQ walkover must have p0=null`);
  assert.equal(m.p1, null, `#${dqId} DQ walkover must have p1=null`);
  assert.equal(m.pick, null, `#${dqId} DQ walkover must have pick=null`);
  assert.equal(m.settlement_pick?.pick_type, "walkover-settlement", `#${dqId} must carry typed walkover-settlement`);
  assert.notEqual(m.settlement_pick?.team_name, "Solid Gaming", `#${dqId} settlement winner must be active opponent`);
}

// 7. Calibration & Brier sanity
assert.ok(ratings.calibration.oos_evaluated > 20000, "walk-forward calibration must evaluate >20k series");
assert.ok(ratings.calibration.brier < 0.24, `OOS Brier (${ratings.calibration.brier}) must beat 0.2500 coinflip`);
assert.ok(flags.count >= 10, "flagged items populated with receipts");

const totalQuotes = mktRows.reduce((a, m) => a + m.market_consensus.venue_count, 0);
console.log(`PASS session_6669f798 test_node_pipeline.mjs: ${scheduled.length} scheduled, ${mktRows.length} market (${totalQuotes} venue quotes joined), OOS Brier=${ratings.calibration.brier}`);
