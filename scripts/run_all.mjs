#!/usr/bin/env node
/**
 * run_all.mjs — orchestrator: collect -> analyze -> build site -> append run log.
 * Used by GitHub Actions (every 6h + manual dispatch) and locally.
 */
import { execFileSync } from "node:child_process";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const step = (script) => {
  console.log(`\n=== ${script} ===`);
  execFileSync(process.execPath, [path.join(ROOT, "scripts", script)], { stdio: "inherit", cwd: ROOT });
};

const t0 = Date.now();
step("collect.mjs");
step("analyze.mjs");
step("build_site.mjs");

// run history log (append-only, capped)
const picks = JSON.parse(await readFile(path.join(ROOT, "data", "node", "picks.json"), "utf8"));
const histDir = path.join(ROOT, "data", "node", "history");
await mkdir(histDir, { recursive: true });
const runsPath = path.join(histDir, "runs.jsonl");
let lines = [];
try { lines = (await readFile(runsPath, "utf8")).split("\n").filter(Boolean); } catch {}
lines.push(JSON.stringify({ ts: new Date().toISOString(), dur_s: Math.round((Date.now() - t0) / 1000), counts: picks.summary.counts, sources_ok: picks.summary.sources_ok }));
if (lines.length > 300) lines = lines.slice(-300);
await writeFile(runsPath, lines.join("\n") + "\n");
console.log(`\nrun_all done in ${Math.round((Date.now() - t0) / 1000)}s`);
