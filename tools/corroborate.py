#!/usr/bin/env python3
"""External-book corroboration for every priced Hotspawn LoL match.

What this stage does
--------------------
1. Reads the manual external-book receipts in ``data/receipts/external_odds/*.json``.
   Those are captures of published decimal prices (book URL + UTC capture time +
   the verbatim page text). They exist because the GitHub Actions runner is
   blocked by the sites that actually price tier-2 LoL (see the runner-side probe
   in ``data/probe/sources_probe.json``).
2. Validates every receipt against the published dataset: the fixture id must
   exist, the two team names must be the two teams on that fixture, every price
   must be a real decimal > 1.0, and symmetric 1.80/1.80-style aggregator
   defaults are quarantined as ``placeholder`` instead of being treated as a line.
3. De-vigs each usable receipt and compares the implied probability with the
   probability this repository published, producing an agreed / divergent verdict.
4. Writes ``data/corroboration.json`` (machine-readable) and ``coverage.html``
   (the "how every match was priced and what external evidence exists" page).

Hard rules
----------
* Receipts are **corroboration only**. This stage never edits a pick, a
  probability or a method. It cannot make a match look priced when it is not.
* A price that is not in a receipt is never inferred, averaged in, or invented.
* A missing receipt is reported as "no external price found", not as an error.
"""
from __future__ import annotations

import glob
import html
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, ROOT, iso, load_json, log, norm_name, now_utc, save_json
# Load the canonical page shell from tools/site.py by path: `site` is a stdlib module name,
# so a plain import would pick up the standard library instead of this repository's builder.
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "lol_site", os.path.join(os.path.dirname(os.path.abspath(__file__)), "site.py"))
_lol_site = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_lol_site)
page_shell = _lol_site.page_shell  # shared nav, mobile bottom nav, app.js

RECEIPT_DIR = os.path.join(DATA, "receipts", "external_odds")
OUT_JSON = os.path.join(DATA, "corroboration.json")
OUT_HTML = os.path.join(ROOT, "coverage.html")   # GitHub Pages serves the branch root
DIVERGENCE_PP = 8.0          # external vs our line, percentage points (allows normal pre-kickoff movement)
PLACEHOLDER_DECIMAL = 1.80   # aggregator "no price yet" default, rejected by tools/model.py too
RECEIPT_MAX_AGE_HOURS = 24   # a captured quote corroborates a *current* line only while it is fresh
                             # (must match tools/model.py RECEIPT_MAX_AGE_HOURS)


def age_hours(captured_utc: str | None) -> float | None:
    """Age of a receipt capture in hours, or None when the timestamp is unusable."""
    if not captured_utc:
        return None
    try:
        dt = datetime.strptime(str(captured_utc)[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    return round((datetime.now(timezone.utc).replace(tzinfo=None) - dt).total_seconds() / 3600.0, 2)

NAV = [
    ("index.html", "Summary"),
    ("picks.html", "All picks"),
    ("featured.html", "Market"),
    ("originated.html", "Model"),
    ("coverage.html", "Coverage"),
    ("unresolved.html", "Unresolved"),
    ("competitions.html", "Tournaments"),
    ("teams.html", "Teams"),
    ("methodology.html", "Method"),
    ("verification.html", "Verify"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flags"),
]


# --------------------------------------------------------------------------- helpers
def e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def pct(value) -> str:
    return "&mdash;" if value is None else f"{value * 100:.1f}%"


def pp(value) -> str:
    if value is None:
        return "&mdash;"
    return f"{value:+.1f} pp"


GENERIC_TOKENS = {"team", "teams", "esports", "esport", "gaming", "club", "gg", "lol", "e", "v"}
RECEIPT_ALIASES = {"team secret": "team secret whales", "secret whales": "team secret whales",
                   "lyon gaming": "lyon", "l s": "los", "l o s": "los"}


def same(a: str, b: str) -> bool:
    """Tolerant team-name equality, same rule as the model's bookmaker join.

    Book pages write "Gen.G Esports" where Hotspawn writes "Gen.G", so an exact
    string compare would silently drop a valid receipt. The extra tokens must all
    be generic org words, and the shorter name must still be distinctive.
    """
    na = RECEIPT_ALIASES.get(norm_name(a), norm_name(a))
    nb = RECEIPT_ALIASES.get(norm_name(b), norm_name(b))
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = na.split(), nb.split()
    if ta == tb:
        return True
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    short_text = " ".join(short)
    long_enough = len(short_text) >= 4 or (len(short_text) >= 2 and any(c.isdigit() for c in short_text))
    return long_enough and (set(long_) - set(short)) <= GENERIC_TOKENS


def devig(d0: float, d1: float) -> tuple[float, float, float]:
    inv = 1.0 / d0 + 1.0 / d1
    return (1.0 / d0) / inv, (1.0 / d1) / inv, inv - 1.0


def is_placeholder(d0: float, d1: float) -> bool:
    return abs(d0 - PLACEHOLDER_DECIMAL) < 1e-4 and abs(d1 - PLACEHOLDER_DECIMAL) < 1e-4


def load_receipts() -> tuple[list[dict], list[str]]:
    problems: list[str] = []
    captures: list[dict] = []
    sources: dict[str, dict] = {}
    observations: list[dict] = []
    for path in sorted(glob.glob(os.path.join(RECEIPT_DIR, "*.json"))):
        doc = load_json(path) or {}
        for src in doc.get("sources") or []:
            sources[src.get("key")] = src
        for cap in doc.get("captures") or []:
            cap = dict(cap)
            cap["_file"] = os.path.basename(path)
            captures.append(cap)
        for obs in doc.get("coverage_observations") or []:
            obs = dict(obs)
            obs["_file"] = os.path.basename(path)
            observations.append(obs)
    if not captures:
        problems.append("no external receipts found")
    return [{"captures": captures, "sources": sources, "observations": observations}][0], problems


PAGE_STYLE = """<style>
/* page-scoped only: keeps this audit page readable on a phone without touching the shared stylesheet */
.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.pill.warn{background:var(--warn-weak);color:var(--warn)}
.pill.no{background:#eef1f6;color:var(--muted)}
.tightlist{margin:6px 0 12px;padding-left:20px}
.tightlist li{margin:4px 0}
</style>"""


# --------------------------------------------------------------------------- core
def build() -> dict:
    doc = load_json(os.path.join(DATA, "matches.json")) or {}
    matches = doc.get("matches") or []
    if not matches:
        raise SystemExit("corroborate: data/matches.json missing or empty - run model.py first")
    by_id = {str(m.get("id")): m for m in matches}

    receipts, problems = load_receipts()
    captures = receipts["captures"]
    sources = receipts["sources"]
    observations = receipts["observations"]

    rows: list[dict] = []
    off_list: list[dict] = []       # genuinely bad receipts: malformed / wrong teams / unparseable
    historic: list[dict] = []       # archived evidence for a fixture Hotspawn no longer lists
    expired: list[dict] = []        # a real receipt, but older than the pricing window
    for cap in captures:
        fid = str(cap.get("fixture_id") or "")
        match = by_id.get(fid)
        base = {
            "fixture_id": fid,
            "source": cap.get("source"),
            "source_name": (sources.get(cap.get("source")) or {}).get("name") or cap.get("source"),
            "page_url": cap.get("page_url"),
            "captured_utc": cap.get("captured_utc"),
            "verbatim": cap.get("verbatim", ""),
            "receipt_file": cap.get("_file"),
            "age_hours": age_hours(cap.get("captured_utc")),
        }
        if match is None:
            # Not an error: Hotspawn rotates fixtures off the list, so an archived capture of a
            # delisted card is history, not a broken receipt. It stays in the ledger, excluded
            # from pricing, and is never counted as a rejection.
            historic.append({**base, "status": "historic",
                             "reason": "fixture is no longer listed by Hotspawn; retained as archived evidence"})
            continue
        t0, t1 = match["team0"]["name"], match["team1"]["name"]
        page_teams = cap.get("page_teams") or []
        dec = cap.get("decimal") or []
        base.update({
            "competition": match.get("competition"),
            "start_utc": match.get("start_utc"),
            "our_team0": t0, "our_team1": t1,
            "our_p0": match.get("p0"), "our_p1": match.get("p1"),
            "our_method": match.get("method"),
            "our_pick": (match.get("pick") or {}).get("team"),
            "hotspawn_url": match.get("hotspawn_url"),
        })
        if len(page_teams) != 2 or len(dec) != 2:
            off_list.append({**base, "status": "malformed",
                             "reason": "receipt needs exactly two teams and two decimal prices"})
            continue
        try:
            d0, d1 = float(dec[0]), float(dec[1])
        except (TypeError, ValueError):
            off_list.append({**base, "status": "malformed", "reason": "non-numeric decimal price"})
            continue
        if min(d0, d1) <= 1.0:
            off_list.append({**base, "status": "malformed",
                             "reason": f"decimal price <= 1.0 ({d0}/{d1}) - not a valid quote"})
            continue
        aligned = same(page_teams[0], t0) and same(page_teams[1], t1)
        swapped = same(page_teams[0], t1) and same(page_teams[1], t0)
        base["name_match"] = "exact" if (same(page_teams[0], t0) and norm_name(page_teams[0]) == norm_name(t0)) else "tolerant"
        if not (aligned or swapped):
            off_list.append({**base, "status": "unmatched",
                             "reason": f"receipt teams {page_teams} are not this fixture's teams "
                                       f"({t0} vs {t1})"})
            continue
        if swapped:
            # normalise to fixture order (team0 first) so a comparison is like-for-like
            page_teams = [page_teams[1], page_teams[0]]
            d0, d1 = d1, d0

        row = {**base, "page_team0": page_teams[0], "page_team1": page_teams[1],
               "decimal": [d0, d1], "swapped": swapped}

        conflict = cap.get("conflict")
        if is_placeholder(d0, d1):
            row.update({"status": "placeholder",
                        "reason": "symmetric 1.80/1.80 is the aggregator's 'no price' default, not a line",
                        "ext_p0": None, "ext_p1": None, "delta_pp": None, "verdict": "not usable"})
            if conflict:
                row["conflict"] = conflict
                row["verdict"] = "conflicting / not reproducible"
            rows.append(row)
            continue

        ext_p0, ext_p1, overround = devig(d0, d1)
        our_p0 = match.get("p0")
        delta = None if our_p0 is None else (ext_p0 - float(our_p0)) * 100.0
        verdict = "unpriced by us"
        if delta is not None:
            verdict = "agrees" if abs(delta) <= DIVERGENCE_PP else "diverges"
        if conflict:
            verdict = "conflicting / not reproducible"
        row.update({"status": "usable", "ext_p0": round(ext_p0, 4), "ext_p1": round(ext_p1, 4),
                    "overround": round(overround, 4),
                    "delta_pp": None if delta is None else round(delta, 2),
                    "verdict": verdict})
        if conflict:
            row["conflict"] = conflict
        age = row.get("age_hours")
        if age is None or age > RECEIPT_MAX_AGE_HOURS:
            # The quote is real but it is no longer a current price: it cannot corroborate a
            # line quoted today. Kept and shown as expired instead of silently "usable", and
            # it is never a rejection - an ageing archive is not a data error.
            row.update({
                "status": "expired",
                "verdict": "expired (archival evidence only)",
                "reason": (f"captured {age if age is not None else 'at an unknown time'} h ago; "
                           f"the current-line window is {RECEIPT_MAX_AGE_HOURS} h"),
            })
            expired.append(row)
        rows.append(row)

    # ---- per-competition coverage matrix
    comp: dict[str, dict] = {}
    for m in matches:
        name = m.get("competition") or "(unnamed)"
        c = comp.setdefault(name, {
            "competition": name, "fixtures": 0, "future": 0,
            "method": {}, "external_priced": 0, "external_sources": set(),
            "conflicting": 0, "conflicting_sources": set(),
            "hotspawn_url": m.get("hotspawn_url"),
        })
        c["fixtures"] += 1
        c["method"][m.get("method")] = c["method"].get(m.get("method"), 0) + 1
    now_iso = iso(now_utc())
    for m in matches:
        if (m.get("start_utc") or "9999") > now_iso:
            comp[m.get("competition") or "(unnamed)"]["future"] += 1
    for row in rows:
        c = comp.get(row.get("competition") or "")
        if not c:
            continue
        if "conflict" in row:
            c["conflicting"] += 1
            c["conflicting_sources"].add(row.get("source_name") or row.get("source") or "?")
        if row["status"] != "usable":
            continue
        c["external_priced"] += 1
        c["external_sources"].add(row.get("source_name") or row.get("source") or "?")

    coverage = []
    for c in sorted(comp.values(), key=lambda x: (-x["fixtures"], x["competition"])):
        coverage.append({
            "competition": c["competition"],
            "fixtures": c["fixtures"],
            "future": c["future"],
            "method": c["method"],
            "external_priced": c["external_priced"],
            "external_sources": sorted(c["external_sources"]),
            "conflicting": c["conflicting"],
            "conflicting_sources": sorted(c["conflicting_sources"]),
            "hotspawn_url": c["hotspawn_url"],
        })

    # ---- audit: published consensus rows that lean on an archived (not same-day) quote
    archived_src = os.path.join(ROOT, "archive", "session-8336fb7e", "data", "book_receipts.json")
    archived_doc = load_json(archived_src) or {}
    archived_quotes = archived_doc.get("quotes") or {}
    archived_rows = []
    for m in matches:
        market = m.get("market") or {}
        venue_names = [v.get("name") for v in (market.get("venues") or [])]
        if "Esportsbook" not in venue_names:
            continue
        q = archived_quotes.get(str(m.get("id"))) or {}
        archived_rows.append({
            "fixture_id": m.get("id"),
            "competition": m.get("competition"),
            "match": f'{m["team0"]["name"]} vs {m["team1"]["name"]}',
            "published_book": market.get("book"),
            "venues": venue_names,
            "quote": ([q.get("decimal0"), q.get("decimal1")] if q else None),
            "observed_at": q.get("observed_at"),
            "source_url": q.get("source_url"),
            "hotspawn_url": m.get("hotspawn_url"),
        })

    unresolved = []
    for m in matches:
        if m.get("method") != "unresolved":
            continue
        unresolved.append({
            "fixture_id": m.get("id"),
            "competition": m.get("competition"),
            "match": f'{m["team0"]["name"]} vs {m["team1"]["name"]}',
            "start_utc": m.get("start_utc"),
            "reason": m.get("basis"),
            "flags": m.get("flags") or [],
            "hotspawn_url": m.get("hotspawn_url"),
            "leaguepedia_page": m.get("leaguepedia_page"),
        })

    usable = [r for r in rows if r["status"] == "usable"]
    deltas = [abs(r["delta_pp"]) for r in usable if r["delta_pp"] is not None]
    summary = {
        "matches": len(matches),
        "priced_by_us": sum(1 for m in matches if m.get("p0") is not None),
        "unresolved_by_us": sum(1 for m in matches if m.get("method") == "unresolved"),
        "method_counts": {},
        "receipts": len(rows) + len(off_list) + len(historic),
        "usable_receipts": len(usable),
        "placeholders": sum(1 for r in rows if r["status"] == "placeholder"),
        "rejected_receipts": len(off_list),
        "historic_receipts": len(historic),
        "expired_receipts": len(expired),
        "receipt_window_hours": RECEIPT_MAX_AGE_HOURS,
        "agrees": sum(1 for r in usable if r["verdict"] == "agrees"),
        "diverges": sum(1 for r in usable if r["verdict"] == "diverges"),
        "conflicting": sum(1 for r in rows if "conflict" in r),
        "max_delta_pp": round(max(deltas), 2) if deltas else None,
        "mean_delta_pp": round(sum(deltas) / len(deltas), 2) if deltas else None,
        "divergence_threshold_pp": DIVERGENCE_PP,
        "competitions_with_external_price": sum(1 for c in coverage if c["external_priced"]),
        "competitions_without_external_price": sum(1 for c in coverage if not c["external_priced"]),
        "competitions_conflicting_only": sum(1 for c in coverage if c["conflicting"] and not c["external_priced"]),
    }
    for m in matches:
        summary["method_counts"][m.get("method")] = summary["method_counts"].get(m.get("method"), 0) + 1

    return {
        "generated_utc": now_utc().isoformat().replace("+00:00", "Z"),
        "data_generated_utc": doc.get("generated_utc"),
        "rules": {
            "corroboration_only": True,
            "divergence_threshold_pp": DIVERGENCE_PP,
            "placeholder_decimal": PLACEHOLDER_DECIMAL,
            "receipt_max_age_hours": RECEIPT_MAX_AGE_HOURS,
            "no_inference": "a price absent from a receipt is never inferred or averaged in",
            "classification": ("every capture lands in exactly one bucket: usable (fresh, matched, "
                               "non-placeholder), expired (fresh window passed), historic (fixture no "
                               "longer listed) or rejected (malformed / wrong teams). Only malformed or "
                               "mismatched receipts and divergences fail the publish gate."),
        },
        "sources": list(sources.values()),
        "coverage_observations": observations,
        "summary": summary,
        "archived_venue_audit": {
            "source_file": os.path.relpath(archived_src, ROOT),
            "observed_at": archived_doc.get("observed_at"),
            "rows_using_archived_quote": len(archived_rows),
            "rows": archived_rows,
        },
        "unresolved_ledger": unresolved,
        "coverage": coverage,
        "rows": rows,
        "rejected": off_list,
        "historic": historic,
        "expired": expired,
        "problems": problems,
    }


# --------------------------------------------------------------------------- html
def render(doc: dict) -> str:
    s = doc["summary"]
    rows = doc["rows"]
    coverage = doc["coverage"]
    sources = {x.get("key"): x for x in doc.get("sources") or []}

    stat_cards = f"""
<section class="stats tight">
  <div class="stat"><div class="sv">{s['matches']}</div><div class="sl">Hotspawn matches mirrored</div>
    <div class="sn">{s['priced_by_us']} priced &middot; {s['unresolved_by_us']} unresolved</div></div>
  <div class="stat market"><div class="sv">{s['competitions_with_external_price']}</div>
    <div class="sl">competitions with an external price</div>
    <div class="sn">{s['competitions_without_external_price']} have none anywhere we can reach</div></div>
  <div class="stat ok"><div class="sv">{s['agrees']}</div><div class="sl">receipts that agree with our line</div>
    <div class="sn">&le; {DIVERGENCE_PP:.0f} pp &middot; max gap {s['max_delta_pp'] if s['max_delta_pp'] is not None else '&mdash;'} pp</div></div>
  <div class="stat provisional"><div class="sv">{s['placeholders'] + s['rejected_receipts']}</div>
    <div class="sl">receipts unusable</div>
    <div class="sn">{s['placeholders']} placeholder &middot; {s['rejected_receipts']} malformed/wrong teams</div></div>
  <div class="stat"><div class="sv">{s['expired_receipts'] + s['historic_receipts']}</div>
    <div class="sl">archived receipts (not current prices)</div>
    <div class="sn">{s['expired_receipts']} past the {s['receipt_window_hours']} h window &middot;
      {s['historic_receipts']} for delisted fixtures</div></div>
</section>
"""

    # sourcing method table
    mc = s["method_counts"]
    method_rows = "".join(
        f"<tr><td><span class=\"badge b-{e(k)}\">{e(k)}</span></td><td class=\"num\">{v}</td>"
        f"<td>{e(explain_method(k))}</td></tr>"
        for k, v in sorted(mc.items(), key=lambda kv: -kv[1])
    )

    # coverage matrix
    cov_rows = []
    for c in coverage:
        ext = ", ".join(c["external_sources"]) if c["external_sources"] else "&mdash;"
        n = c["external_priced"]
        if n:
            pill = f'<span class="pill ok">{n} match{"es" if n != 1 else ""} priced externally</span>'
        elif c.get("conflicting"):
            pill = '<span class="pill warn">external price seen but not reproducible</span>'
            ext = ", ".join(c["conflicting_sources"]) + " (conflicting reading)"
        else:
            pill = '<span class="pill no">no external book prices this competition</span>'
        cov_rows.append(
            "<tr>"
            f'<td data-label="Competition"><a href="{e(c["hotspawn_url"])}">{e(c["competition"])}</a></td>'
            f'<td data-label="Matches" class="num">{c["fixtures"]}</td>'
            f'<td data-label="Upcoming" class="num">{c["future"]}</td>'
            f'<td data-label="Our method">{e(", ".join(f"{k} {v}" for k, v in sorted(c["method"].items(), key=lambda kv: -kv[1])))}</td>'
            f'<td data-label="External line">{pill}<br><span class="muted small">{e(ext) if ext != "&mdash;" else ""}</span></td>'
            "</tr>"
        )

    # receipt table
    rec_rows = []
    for r in rows:
        our = f'{pct(r.get("our_p0"))} <span class="muted small">{e(r.get("our_team0"))}</span>' \
            if r.get("our_p0") is not None else '<span class="muted">unpriced</span>'
        ext = (f'{pct(r.get("ext_p0"))} <span class="muted small">{e(r.get("page_team0"))}</span>'
               if r.get("ext_p0") is not None else '<span class="muted">no usable price</span>')
        quote = "/".join(f"{d:.3g}" for d in r.get("decimal") or []) or "&mdash;"
        verdict = r.get("verdict") or r.get("status")
        cls = {"agrees": "ok", "diverges": "warn", "conflicting / not reproducible": "bad"}.get(verdict, "no")
        rec_rows.append(
            "<tr>"
            f'<td data-label="Match"><a href="{e(r.get("hotspawn_url"))}">{e(r.get("our_team0"))} vs {e(r.get("our_team1"))}</a>'
            f'<br><span class="muted small">{e(r.get("competition"))} &middot; {e((r.get("start_utc") or "")[:16].replace("T", " "))} UTC</span></td>'
            f'<td data-label="Our line">{our}<br><span class="muted small">{e(r.get("our_method"))}</span></td>'
            f'<td data-label="External line">{ext}<br><span class="muted small">{e(r.get("source_name"))} {e(quote)}</span></td>'
            f'<td data-label="Gap" class="num">{pp(r.get("delta_pp"))}</td>'
            f'<td data-label="Verdict"><span class="pill {cls}">{e(verdict)}</span></td>'
            f'<td data-label="Receipt"><a href="{e(r.get("page_url"))}">source page</a>'
            f'<br><span class="muted small">captured {e((r.get("captured_utc") or "")[:16].replace("T", " "))}Z</span></td>'
            "</tr>"
        )
    for r in doc["rejected"]:
        rec_rows.append(
            "<tr class=\"rowbad\">"
            f'<td data-label="Match"><span class="muted">{e(r.get("fixture_id"))}</span></td>'
            "<td data-label=\"Our line\">&mdash;</td>"
            f'<td data-label="External line">{e(r.get("source_name"))}</td>'
            "<td data-label=\"Gap\" class=\"num\">&mdash;</td>"
            f'<td data-label="Verdict"><span class="pill bad">{e(r.get("status"))}</span></td>'
            f'<td data-label="Receipt"><a href="{e(r.get("page_url"))}">source page</a><br>'
            f'<span class="muted small">{e(r.get("reason"))}</span></td>'
            "</tr>"
        )
    for r in doc.get("historic") or []:
        rec_rows.append(
            "<tr>"
            f'<td data-label="Match"><span class="muted">fixture #{e(r.get("fixture_id"))} (delisted)</span></td>'
            "<td data-label=\"Our line\">&mdash;</td>"
            f'<td data-label="External line">{e(r.get("source_name"))}</td>'
            "<td data-label=\"Gap\" class=\"num\">&mdash;</td>"
            '<td data-label="Verdict"><span class="pill no">historic</span></td>'
            f'<td data-label="Receipt"><a href="{e(r.get("page_url"))}">source page</a><br>'
            f'<span class="muted small">{e(r.get("reason"))}'
            f' &middot; captured {e((r.get("captured_utc") or "")[:16].replace("T", " "))}Z</span></td>'
            "</tr>"
        )

    obs_rows = "".join(
        f'<tr><td data-label="Source"><a href="{e(o.get("url"))}">{e((sources.get(o.get("source")) or {}).get("name") or o.get("source"))}</a></td>'
        f'<td data-label="What it showed">{e(o.get("observation"))}<br>'
        f'<span class="muted small">verbatim: &ldquo;{e(o.get("verbatim"))}&rdquo; &middot; captured '
        f'{e((o.get("captured_utc") or "")[:16].replace("T", " "))}Z</span></td>'
        f'<td data-label="Capture"><a href="{e(o.get("url"))}">open page</a></td></tr>'
        for o in doc["coverage_observations"]
    )

    src_rows = "".join(
        f'<tr><td data-label="Source"><a href="{e(v.get("url"))}">{e(v.get("name"))}</a></td>'
        f'<td data-label="Kind">{e(v.get("kind"))}</td>'
        f'<td data-label="Reachable from the Actions runner">{e(v.get("runner_reachable"))}</td>'
        f'<td data-label="Note">{e(v.get("note"))}</td></tr>'
        for v in sources.values()
    )

    gaps = [c for c in coverage if not c["external_priced"] and not c.get("conflicting")]
    conflicts = [c for c in coverage if not c["external_priced"] and c.get("conflicting")]
    gap_list = "".join(
        f'<li><strong>{e(c["competition"])}</strong> &mdash; {c["fixtures"]} matches '
        f'({c["future"]} still upcoming): {e(", ".join(f"{k} {v}" for k, v in sorted(c["method"].items(), key=lambda kv: -kv[1])))}</li>'
        for c in gaps
    )

    conflict_block = ""
    if conflicts:
        conflict_block = (
            '<p class="muted small">One competition did show an external price that we could not reproduce; '
            'it is listed here rather than counted as covered: '
            + "; ".join(f'<strong>{e(c["competition"])}</strong> ({e(", ".join(c["conflicting_sources"]))})'
                        for c in conflicts)
            + '.</p>'
        )

    def quote_text(a: dict) -> str:
        q = a.get("quote")
        if not q or None in q:
            return "&mdash;"
        return f"{q[0]:.3g} / {q[1]:.3g}"

    archived_rows_html = "".join(
        f'<tr><td data-label="Match"><a href="{e(a["hotspawn_url"])}">{e(a["match"])}</a>'
        f'<br><span class="muted small">{e(a["competition"])}</span></td>'
        f'<td data-label="Published as">{e(a["published_book"])} &middot; venues {e(", ".join(a["venues"]))}</td>'
        f'<td data-label="Archived quote">{quote_text(a)}'
        f'<br><span class="muted small">captured {e((a.get("observed_at") or "")[:16].replace("T", " "))}Z</span></td>'
        f'<td data-label="Receipt"><a href="{e(a.get("source_url"))}">archived source</a></td></tr>'
        for a in doc["archived_venue_audit"]["rows"]
    )
    archived_block = ""
    if doc["archived_venue_audit"]["rows"]:
        archived_block = f"""<section class="panel">
  <h2>5. Audit: the archived fifth venue</h2>
  <p>{doc['archived_venue_audit']['rows_using_archived_quote']} published rows are labelled
  &ldquo;5-Venue Consensus&rdquo; only because a fifth venue &mdash; an aggregator quote stored on
  {e((doc['archived_venue_audit'].get('observed_at') or '')[:16].replace('T', ' '))}Z &mdash; is still being read
  from <code>{e(doc['archived_venue_audit']['source_file'])}</code>. That quote is
  <strong>not a same-day reading</strong>, and on 2026-10-23 the same aggregator published a
  different (placeholder) price for the LCP card below. It is therefore <em>excluded</em> from the
  corroboration table above and flagged here rather than counted as live evidence.</p>
  <div class="tablewrap">
  <table class="table stack">
    <thead><tr><th>Match</th><th>Published as</th><th>Archived quote</th><th>Receipt</th></tr></thead>
    <tbody>{archived_rows_html}</tbody>
  </table>
  </div>
</section>
"""

    unresolved_rows = "".join(
        f'<tr><td data-label="Match"><a href="{e(u["hotspawn_url"])}">{e(u["match"])}</a>'
        f'<br><span class="muted small">{e(u["competition"])} &middot; {e((u["start_utc"] or "")[:16].replace("T", " "))} UTC</span></td>'
        f'<td data-label="Why it is unresolved">{e(u["reason"])}</td>'
        f'<td data-label="Source"><a href="{e(u["hotspawn_url"])}">Hotspawn card</a>'
        f'<br><span class="muted small">official removal recorded on Leaguepedia: {e(u["leaguepedia_page"])}</span></td></tr>'
        for u in doc["unresolved_ledger"]
    )

    body = f"""
{stat_cards}

<section class="panel">
  <h2>Read this first</h2>
  <p>Every one of the {s['matches']} cards on <a href="https://play.hotspawn.com/lol-pickems">Hotspawn's
  League of Legends pick'em lobby</a> is mirrored here and carries a probability. Only
  <strong>{s['method_counts'].get('market', 0)}</strong> of them are priced by real bookmakers, because
  real bookmakers only price the international events. {s['method_counts'].get('model', 0)} carry our own
  Elo line and {s['method_counts'].get('provisional', 0)} are provisional (thin data);
  {s['unresolved_by_us']} are deliberately unresolved and listed on
  <a href="unresolved.html">Unresolved</a> with their limitations.</p>
  <p>This page is the audit: it shows <em>where the external evidence exists</em>, what it said when it was
  captured, how far it sits from the number we published, and &mdash; for the competitions with no book
  coverage at all &mdash; the evidence that no reachable book prices them.</p>
  <p class="muted small">Receipts are corroboration only: they are read after the picks are built and cannot
  change a pick, a probability or a method. A price that is not in a receipt is never inferred.</p>
</section>

<section class="panel">
  <h2>1. How each match was priced</h2>
  <table class="table">
    <thead><tr><th>Method</th><th class="num">Matches</th><th>What it means</th></tr></thead>
    <tbody>{method_rows}</tbody>
  </table>
</section>

<section class="panel">
  <h2>2. External line coverage by competition</h2>
  <p class="muted small">"Priced externally" means at least one capture in this repository shows a real
  decimal price for a match in that competition. "{s['competitions_without_external_price']}" of the
  {len(coverage)} competitions have no external price anywhere we can reach &mdash; established
  sportsbooks, esportsbooks and odds aggregators included.</p>
  <div class="tablewrap">
  <table class="table stack">
    <thead><tr><th>Competition</th><th class="num">Matches</th><th class="num">Upcoming</th>
      <th>Our method</th><th>External line</th></tr></thead>
    <tbody>{"".join(cov_rows)}</tbody>
  </table>
  </div>
</section>

<section class="panel">
  <h2>3. Corroboration, match by match</h2>
  <p class="muted small">Our line is de-vigged from the sharpest available market; the external line is
  de-vigged from the captured page. "Agrees" means the two are within {DIVERGENCE_PP:.0f} percentage points.
  Mean absolute gap across all usable receipts: <strong>{s['mean_delta_pp'] if s['mean_delta_pp'] is not None else '&mdash;'} pp</strong>,
  largest <strong>{s['max_delta_pp'] if s['max_delta_pp'] is not None else '&mdash;'} pp</strong>.</p>
  <div class="tablewrap">
  <table class="table stack">
    <thead><tr><th>Match</th><th>Our line</th><th>External line</th><th class="num">Gap</th>
      <th>Verdict</th><th>Receipt</th></tr></thead>
    <tbody>{"".join(rec_rows)}</tbody>
  </table>
  </div>
</section>

<section class="panel">
  <h2>4. No external market: what we checked and what it showed</h2>
  <p>For the {len(gaps)} competitions with no external price, the pick is our own line
  (<a href="methodology.html">method</a>) and the limitation is published rather than hidden:</p>
  <ul class="tightlist">{gap_list}</ul>
  {conflict_block}
  <div class="tablewrap">
  <table class="table stack">
    <thead><tr><th>Source</th><th>What it showed</th><th>Capture</th></tr></thead>
    <tbody>{obs_rows or '<tr><td colspan="3" class="muted">no coverage observations recorded</td></tr>'}</tbody>
  </table>
  </div>
</section>

{archived_block}

<section class="panel">
  <h2>6. Matches with no pick at all, and why</h2>
  <p class="muted small">These {len(doc['unresolved_ledger'])} cards are the only ones on the list without a
  probability. Giving them a number would require inventing one, because the league itself removed one of
  the participants. They are kept on the site, with the official reason and its source, instead of being
  filled in.</p>
  <div class="tablewrap">
  <table class="table stack">
    <thead><tr><th>Match</th><th>Why it is unresolved</th><th>Source</th></tr></thead>
    <tbody>{unresolved_rows}</tbody>
  </table>
  </div>
</section>

<section class="panel">
  <h2>7. Sources behind this page</h2>
  <div class="tablewrap">
  <table class="table stack">
    <thead><tr><th>Source</th><th>Kind</th><th>Reachable from the build runner</th><th>Note</th></tr></thead>
    <tbody>{src_rows}</tbody>
  </table>
  </div>
  <p class="muted small">Receipt files live in <code>data/receipts/external_odds/</code> and are validated on
  every build by <code>tools/corroborate.py</code> (fixture exists, teams match, price &gt; 1.0, placeholders
  quarantined). Machine-readable output: <a href="data/corroboration.json">data/corroboration.json</a>.</p>
</section>
"""
    return page_shell(
        "External line coverage",
        "coverage.html",
        PAGE_STYLE + body,
        "Which Hotspawn League of Legends matches a real bookmaker priced, which ones we had to originate, "
        "and the evidence behind both.",
    )


def explain_method(method: str) -> str:
    return {
        "market": "De-vigged real-money market line (Pinnacle, Polymarket, Kalshi, Bovada, Unibet).",
        "model": "Our own Elo line from recorded series results; both teams rated and connected.",
        "provisional": "Our Elo line with thin data - shown with a low-confidence flag.",
        "unresolved": "No defensible line: participant removed mid-split (official dqteams) or no rating path.",
    }.get(method, method)


def main() -> None:
    doc = build()
    save_json(OUT_JSON, doc)
    html_text = render(doc)
    with open(OUT_HTML, "w", encoding="utf-8") as fh:
        fh.write(html_text)
    s = doc["summary"]
    log(f"corroborate: {s['usable_receipts']} usable receipts "
        f"({s['agrees']} agree / {s['diverges']} diverge / {s['placeholders']} placeholder), "
        f"{s['competitions_with_external_price']}/{len(doc['coverage'])} competitions priced externally")
    for p in doc["problems"]:
        log(f"corroborate WARNING: {p}")


if __name__ == "__main__":
    main()
