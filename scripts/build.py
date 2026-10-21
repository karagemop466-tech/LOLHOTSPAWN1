#!/usr/bin/env python3
"""Static mobile-first GitHub Pages generator for Hotspawn LoL Pick'ems.

Builds 9 clean, accessible, zero-external-dependency HTML pages directly from verified
JSON outputs in `data/`:
  - `index.html`       : Upfront Executive Summary, quick links, urgent slate, unresolved caveats
  - `picks.html`       : Complete open LoL Pick'ems board (search, filter, sort, CSV/JSON export)
  - `featured.html`    : Tier-1 Sportsbook & Prediction Market consensus picks (4-venue breakdown)
  - `originated.html`  : Tier-2 Originated low-tier LoL regional picks (10 leagues)
  - `unresolved.html`  : Dedicated Unresolved Picks, Stale API Rows & Structural Limitations
  - `tournaments.html` : Directory of all 27 competitions with official organizer & wiki links
  - `teams.html`       : Directory of all 204 competition-scoped team ratings & W-L records
  - `methodology.html` : Quantitative specification, SVG calibration curves & API architecture
  - `flagged.html`     : Flagged for Review — upstream anomalies, forfeits, misbindings & traps
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote


def esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def fmt_utc(iso_str: str) -> str:
    if not iso_str or len(iso_str) < 16:
        return esc(iso_str or "—")
    # e.g. `2026-10-23T17:00:00Z` -> `Oct 23 · 17:00 UTC`
    months = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
    }
    mm = months.get(iso_str[5:7], iso_str[5:7])
    dd = iso_str[8:10]
    hhmm = iso_str[11:16]
    return f"{mm} {dd} · {hhmm} UTC"


def status_badge(status: str) -> str:
    if status == "market_consensus":
        return '<span class="badge badge-market">4-Venue Consensus</span>'
    if status == "esportsbook_line":
        return '<span class="badge badge-market">Esportsbook Line</span>'
    if status == "originated":
        return '<span class="badge badge-orig">Originated BT</span>'
    if status == "unresolved":
        return '<span class="badge badge-unres">Unresolved / Caveat</span>'
    return '<span class="badge badge-neutral">Past-Lock Stale</span>'


def render_sources_chips(sources: list[dict[str, str]]) -> str:
    chips = [
        f'<a class="src-chip" href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["label"])} ↗</a>'
        for s in sources
        if s.get("url")
    ]
    return '<div class="source-links">' + "".join(chips) + "</div>"


def render_pick_card(row: dict[str, Any]) -> str:
    st = row["status"]
    card_cls = (
        "card-market"
        if st in ("market_consensus", "esportsbook_line")
        else ("card-orig" if st == "originated" else "card-unres")
    )
    p0 = row["team0_prob"]
    p1 = row["team1_prob"]
    pick = row["pick"]
    t0, t1 = row["team0"], row["team1"]
    fav_prob = max(p0 or 0.5, p1 or 0.5)
    delta = (row["hotspawn_crowd_display_only"] or {}).get("model_minus_crowd_team0_pp") or 0.0

    meta_bits = []
    if row["best_of_display"]:
        meta_bits.append(esc(row["best_of_display"]))
    if row["tier_display"]:
        meta_bits.append(f"Tier {esc(row['tier_display'])}")
    if row["offered_points"]:
        meta_bits.append(f"{row['offered_points']} pts")
    meta_str = " · ".join(meta_bits)

    if pick:
        pick_pct = (p0 if pick == t0 else p1) * 100.0
        conf = esc(row["confidence"])
        banner_html = (
            f'<div class="pick-banner">'
            f'<span class="pick-winner">PICK: {esc(pick)} ({pick_pct:.1f}%)</span>'
            f'<span>{status_badge(st)} <span class="badge badge-neutral">{conf}</span></span>'
            f"</div>"
        )
    else:
        lean_note = (
            f"Defensive Card Lean: {esc(row['defensive_lean'])}"
            if row.get("defensive_lean")
            else "No Credible Edge"
        )
        banner_html = (
            f'<div class="pick-banner">'
            f'<span class="pick-winner">UNRESOLVED — {lean_note}</span>'
            f"<span>{status_badge(st)}</span>"
            f"</div>"
        )

    if p0 is not None and p1 is not None:
        w0 = max(min(p0 * 100.0, 96.0), 4.0)
        w1 = 100.0 - w0
        bar_a_cls = "prob-fill-a" if p0 >= p1 else "prob-fill-a dog"
        bar_b_cls = "prob-fill-b" if p0 >= p1 else "prob-fill-b fav"
        odds0 = f"Fair {row['team0_fair_odds']:.2f}x" if row.get("team0_fair_odds") else ""
        odds1 = f"Fair {row['team1_fair_odds']:.2f}x" if row.get("team1_fair_odds") else ""
        ci = row.get("ci90_team0")
        ci_note = f" · 90% range [{ci[0]*100:.0f}%, {ci[1]*100:.0f}%]" if ci else ""
        probs_html = f"""
        <div class="matchup-row">
          <div class="side-box">
            <span class="team-label {'is-pick' if pick == t0 else ''}">{esc(t0)}</span>
            <span class="prob-big">{p0*100:.1f}%</span>
            <span class="odds-sub">{esc(odds0)}</span>
          </div>
          <span class="vs-tag">vs</span>
          <div class="side-box right">
            <span class="team-label {'is-pick' if pick == t1 else ''}">{esc(t1)}</span>
            <span class="prob-big">{p1*100:.1f}%</span>
            <span class="odds-sub">{esc(odds1)}</span>
          </div>
        </div>
        <div class="prob-track" role="img" aria-label="{esc(t0)} {p0*100:.1f}% versus {esc(t1)} {p1*100:.1f}%">
          <div class="{bar_a_cls}" style="width:{w0:.1f}%"></div>
          <div class="{bar_b_cls}" style="width:{w1:.1f}%"></div>
        </div>
        <div class="evidence-line">{esc(row['evidence_summary'])}{esc(ci_note)}</div>
        """
    else:
        probs_html = f"""
        <div class="matchup-row">
          <div class="side-box"><span class="team-label">{esc(t0)}</span><span class="odds-sub">Removed / Unpriced</span></div>
          <span class="vs-tag">vs</span>
          <div class="side-box right"><span class="team-label">{esc(t1)}</span><span class="odds-sub">Active Opponent</span></div>
        </div>
        <div class="evidence-line">{esc(row['unresolved_reason'])}</div>
        """

    admin_html = ""
    for an in row.get("admin_notes") or []:
        admin_html += f'<div><span class="badge badge-flag">{esc(an["badge"])}</span></div>'

    search_blob = f"{row['id']} {row['competition']} {row['region']} {t0} {t1} {pick or ''} {row['stage_display']}"
    return f"""
    <article class="pick-card {card_cls} pick-item"
      data-comp="{esc(row['competition'])}"
      data-status="{esc(st)}"
      data-hours="{row['hours_until_lock']}"
      data-favprob="{fav_prob:.4f}"
      data-points="{row['offered_points']}"
      data-delta="{delta}"
      data-kickoff="{row['scheduled_ms']}"
      data-search="{esc(search_blob)}">
      <div class="card-top">
        <span class="comp-title">{esc(row['competition'])}{' · ' + esc(row['stage_display']) if row['stage_display'] else ''}</span>
        <span><time data-utc="{esc(row['scheduled_utc'])}" data-show-local="1">{fmt_utc(row['scheduled_utc'])}</time>{' · ' + meta_str if meta_str else ''}</span>
      </div>
      {banner_html}
      {admin_html}
      {probs_html}
      {render_sources_chips(row['sources'])}
    </article>
    """


def render_pick_table_row(row: dict[str, Any]) -> str:
    st = row["status"]
    t0, t1 = row["team0"], row["team1"]
    p0, p1 = row["team0_prob"], row["team1_prob"]
    pick = row["pick"]
    fav_prob = max(p0 or 0.5, p1 or 0.5)
    delta = (row["hotspawn_crowd_display_only"] or {}).get("model_minus_crowd_team0_pp") or 0.0
    search_blob = f"{row['id']} {row['competition']} {row['region']} {t0} {t1} {pick or ''} {row['stage_display']}"

    p0_txt = f"{p0*100:.1f}%" if p0 is not None else "—"
    p1_txt = f"{p1*100:.1f}%" if p1 is not None else "—"
    pick_cell = (
        f"<strong>{esc(pick)}</strong><br><span class='odds-sub'>{esc(row['confidence'])}</span>"
        if pick
        else f"<span class='badge badge-unres'>Unresolved</span><br><span class='odds-sub'>{esc('Lean: ' + row['defensive_lean']) if row.get('defensive_lean') else '—'}</span>"
    )
    fmt_cell = " · ".join(
        x for x in [esc(row["best_of_display"]) or "—", f"{row['offered_points']} pts" if row["offered_points"] else ""] if x
    )

    return f"""
    <tr class="pick-row"
      data-comp="{esc(row['competition'])}"
      data-status="{esc(st)}"
      data-hours="{row['hours_until_lock']}"
      data-favprob="{fav_prob:.4f}"
      data-points="{row['offered_points']}"
      data-delta="{delta}"
      data-kickoff="{row['scheduled_ms']}"
      data-search="{esc(search_blob)}">
      <td><time data-utc="{esc(row['scheduled_utc'])}" data-show-local="1">{fmt_utc(row['scheduled_utc'])}</time><div class="odds-sub">#{esc(row['id'])}</div></td>
      <td><strong>{esc(row['competition'])}</strong><div class="odds-sub">{esc(row['region'])}{' · ' + esc(row['stage_display']) if row['stage_display'] else ''}</div></td>
      <td>{fmt_cell}</td>
      <td><strong>{esc(t0)}</strong> vs <strong>{esc(t1)}</strong><div class="odds-sub">{esc(row['evidence_summary'])}</div></td>
      <td><strong>{p0_txt}</strong> / <strong>{p1_txt}</strong></td>
      <td>{pick_cell}</td>
      <td>{status_badge(st)}</td>
      <td>{render_sources_chips(row['sources'])}</td>
    </tr>
    """


def render_dual_board(
    rows: list[dict[str, Any]],
    competitions: list[str],
    show_tier_select: bool = True,
    default_view_label: str = "matches",
) -> str:
    comp_opts = '<option value="all">All Competitions (' + str(len(rows)) + ")</option>"
    counts_by_c: dict[str, int] = {}
    for r in rows:
        counts_by_c[r["competition"]] = counts_by_c.get(r["competition"], 0) + 1
    for c in competitions:
        if counts_by_c.get(c):
            comp_opts += f'<option value="{esc(c)}">{esc(c)} ({counts_by_c[c]})</option>'

    tier_ctrl = (
        """
        <select id="filter-tier" class="select-control" aria-label="Filter by pricing tier">
          <option value="all">All Pricing Tiers</option>
          <option value="market">Sportsbook &amp; Exchange Lines</option>
          <option value="originated">Originated Low-Tier BT</option>
          <option value="unresolved">Unresolved / Caveats</option>
        </select>
        """
        if show_tier_select
        else ""
    )

    cards_html = "".join(render_pick_card(r) for r in rows)
    rows_html = "".join(render_pick_table_row(r) for r in rows)

    return f"""
    <div class="filter-bar">
      <input id="filter-search" class="input-control" type="search" placeholder="Search team, league, stage, or fixture ID…" aria-label="Search matches">
      <select id="filter-comp" class="select-control" aria-label="Filter by competition">
        {comp_opts}
      </select>
      {tier_ctrl}
      <select id="filter-window" class="select-control" aria-label="Filter by kickoff window">
        <option value="all">All Kickoff Dates</option>
        <option value="48h">Locking in Next 48 Hours</option>
        <option value="7d">Next 7 Days</option>
        <option value="high">High Confidence (&ge;65%)</option>
      </select>
      <select id="filter-sort" class="select-control" aria-label="Sort order">
        <option value="kickoff">Sort: Soonest Lock</option>
        <option value="prob_desc">Sort: Highest Win %</option>
        <option value="points_desc">Sort: Points Value</option>
        <option value="edge_desc">Sort: Crowd Divergence</option>
      </select>
    </div>

    <div class="filter-meta">
      <div>Showing <strong id="visible-count">{len(rows)}</strong> of {len(rows)} {esc(default_view_label)}</div>
      <div class="btn-group">
        <button type="button" class="mini-btn active" data-set-view="responsive-dual">Auto Layout</button>
        <button type="button" class="mini-btn" data-set-view="view-mode-cards">Cards</button>
        <button type="button" class="mini-btn" data-set-view="view-mode-table">Compact Table</button>
        <a class="mini-btn" href="data/picks.csv" download>Download CSV</a>
        <a class="mini-btn" href="data/picks.json" target="_blank" rel="noopener">Raw JSON</a>
      </div>
    </div>

    <div id="dual-view-root" class="responsive-dual">
      <div class="mobile-cards-container">
        <div id="picks-cards-list" class="cards-grid two-col">
          {cards_html}
        </div>
      </div>
      <div class="desktop-table-container">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Kickoff (UTC)</th>
                <th>Competition</th>
                <th>Format</th>
                <th>Matchup &amp; Evidence</th>
                <th>Win Prob (A / B)</th>
                <th>Recommended Pick</th>
                <th>Method</th>
                <th>Verified Sources</th>
              </tr>
            </thead>
            <tbody id="picks-table-body">
              {rows_html}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """


def build_svg_reliability(calibration: dict[str, Any]) -> str:
    """Render clean inline SVG walk-forward reliability curve (`Predicted %` vs `Empirical Win %`)."""
    bins = calibration.get("reliability_bins") or []
    w, h, pad = 500, 320, 52
    pw, ph = w - 2 * pad, h - 2 * pad

    def sx(p: float) -> float:
        return pad + ((p - 0.5) / 0.5) * pw

    def sy(p: float) -> float:
        return h - pad - ((p - 0.5) / 0.5) * ph

    grid = []
    for tick in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        x, y = sx(tick), sy(tick)
        lbl = f"{int(tick*100)}%"
        grid.append(f'<line x1="{pad}" y1="{y:.1f}" x2="{w-pad}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        grid.append(f'<line x1="{x:.1f}" y1="{pad}" x2="{x:.1f}" y2="{h-pad}" stroke="#e2e8f0" stroke-width="1"/>')
        grid.append(f'<text x="{pad-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#64748b">{lbl}</text>')
        grid.append(f'<text x="{x:.1f}" y="{h-pad+18}" text-anchor="middle" font-size="11" fill="#64748b">{lbl}</text>')

    pts = []
    markers = []
    for b in bins:
        mp = b["mean_predicted"]
        ew = min(max(b["empirical_win_rate"], 0.5), 1.0)
        hw = b["ci95_half_width"]
        x, y = sx(mp), sy(ew)
        y_lo = sy(max(0.5, ew - hw))
        y_hi = sy(min(1.0, ew + hw))
        pts.append(f"{x:.1f},{y:.1f}")
        markers.append(f'<line x1="{x:.1f}" y1="{y_lo:.1f}" x2="{x:.1f}" y2="{y_hi:.1f}" stroke="#93c5fd" stroke-width="2"/>')
        markers.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#1d4ed8" stroke="#ffffff" stroke-width="1.5">'
            f"<title>{esc(b['label'])} (n={b['count']}): Predicted {mp*100:.1f}%, Actual {b['empirical_win_rate']*100:.1f}%</title></circle>"
        )

    poly = f'<polyline fill="none" stroke="#1d4ed8" stroke-width="2.5" points="{" ".join(pts)}"/>' if pts else ""
    return f"""
    <svg viewBox="0 0 {w} {h}" role="img" aria-label="Out-of-sample reliability diagram across {calibration['n_walkforward_matches']} LoL matches">
      <rect width="{w}" height="{h}" fill="#ffffff" rx="8"/>
      {''.join(grid)}
      <line x1="{sx(0.5):.1f}" y1="{sy(0.5):.1f}" x2="{sx(1.0):.1f}" y2="{sy(1.0):.1f}" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="5,4"/>
      {poly}
      {''.join(markers)}
      <text x="{w/2:.0f}" y="22" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">
        Walk-Forward Calibration (N = {calibration['n_walkforward_matches']:,} Pre-Match 2026 Series)
      </text>
      <text x="{w/2:.0f}" y="{h-8}" text-anchor="middle" font-size="11" fill="#475569">Predicted Favorite Win Probability</text>
    </svg>
    """


def build_svg_lambda_sweep(calibration: dict[str, Any]) -> str:
    """Render clean inline SVG showing U-shaped out-of-sample Log-Loss minimum at lambda=1.50."""
    sweep = calibration.get("lambda_sweep") or []
    w, h, pad = 500, 320, 56
    pw, ph = w - 2 * pad, h - 2 * pad
    vals = [r["log_loss"] for r in sweep]
    ymin, ymax = min(vals) - 0.002, max(vals) + 0.002

    def sx(idx_i: int) -> float:
        return pad + (idx_i / max(len(sweep) - 1, 1)) * pw

    def sy(val: float) -> float:
        return h - pad - ((val - ymin) / max(ymax - ymin, 1e-6)) * ph

    elems = []
    for k in range(5):
        v = ymin + (k / 4.0) * (ymax - ymin)
        y = sy(v)
        elems.append(f'<line x1="{pad}" y1="{y:.1f}" x2="{w-pad}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        elems.append(f'<text x="{pad-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#64748b">{v:.4f}</text>')

    pts = [f"{sx(i):.1f},{sy(r['log_loss']):.1f}" for i, r in enumerate(sweep)]
    elems.append(f'<polyline fill="none" stroke="#047857" stroke-width="2.5" points="{" ".join(pts)}"/>')

    for i, r in enumerate(sweep):
        x, y = sx(i), sy(r["log_loss"])
        is_sel = r["selected"]
        r_px = 6.5 if is_sel else 4.5
        col = "#b91c1c" if is_sel else "#047857"
        elems.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r_px}" fill="{col}" stroke="#ffffff" stroke-width="1.5"/>')
        elems.append(f'<text x="{x:.1f}" y="{h-pad+18}" text-anchor="middle" font-size="11" fill="#475569">λ={r["lambda"]}</text>')
        if is_sel:
            elems.append(
                f'<text x="{x:.1f}" y="{y-12:.1f}" text-anchor="middle" font-size="11" font-weight="700" fill="#b91c1c">'
                f'Optimal λ*={r["lambda"]} ({r["log_loss"]:.4f})</text>'
            )

    return f"""
    <svg viewBox="0 0 {w} {h}" role="img" aria-label="Regularization parameter lambda out-of-sample log-loss curve">
      <rect width="{w}" height="{h}" fill="#ffffff" rx="8"/>
      {''.join(elems)}
      <text x="{w/2:.0f}" y="22" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">
        Out-of-Sample Proper Scoring Sweep (Chronological Log-Loss vs λ)
      </text>
      <text x="{w/2:.0f}" y="{h-8}" text-anchor="middle" font-size="11" fill="#475569">L2 Prior Precision Hyperparameter (λ)</text>
    </svg>
    """


def build_svg_market_vs_crowd(market_rows: list[dict[str, Any]]) -> str:
    """Horizontal dot-comparison SVG comparing 4-Venue Real-Money Probability vs Hotspawn Crowd %."""
    rows = [r for r in market_rows if r["hotspawn_crowd_display_only"]["team0_picked_pct"] is not None]
    row_h = 36
    pad_l, pad_r, pad_t, pad_b = 185, 32, 44, 38
    w = 640
    h = pad_t + pad_b + len(rows) * row_h
    pw = w - pad_l - pad_r

    def sx(pct: float) -> float:
        return pad_l + (pct / 100.0) * pw

    items = []
    for pct in (0, 25, 50, 75, 100):
        x = sx(pct)
        items.append(f'<line x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{h-pad_b}" stroke="#e2e8f0" stroke-width="1"/>')
        items.append(f'<text x="{x:.1f}" y="{h-pad_b+18}" text-anchor="middle" font-size="11" fill="#64748b">{pct}%</text>')

    for idx_r, r in enumerate(rows):
        y = pad_t + idx_r * row_h + 18
        m_pct = (r["team0_prob"] or 0.0) * 100.0
        c_pct = float(r["hotspawn_crowd_display_only"]["team0_picked_pct"] or 0.0)
        label = f"{r['team0']} (vs {r['team1'][:10]})"
        items.append(f'<text x="{pad_l-10}" y="{y+4}" text-anchor="end" font-size="11.5" font-weight="600" fill="#0f172a">{esc(label)}</text>')
        items.append(f'<line x1="{sx(m_pct):.1f}" y1="{y}" x2="{sx(c_pct):.1f}" y2="{y}" stroke="#cbd5e1" stroke-width="2.5"/>')
        items.append(f'<circle cx="{sx(c_pct):.1f}" cy="{y}" r="5" fill="#dc2626"><title>Hotspawn Crowd: {c_pct:.0f}% (Ignored)</title></circle>')
        items.append(f'<circle cx="{sx(m_pct):.1f}" cy="{y}" r="5.5" fill="#1d4ed8"><title>Real-Money Consensus: {m_pct:.1f}%</title></circle>')

    return f"""
    <svg viewBox="0 0 {w} {h}" role="img" aria-label="Real-money market probability versus Hotspawn crowd pick percentage">
      <rect width="{w}" height="{h}" fill="#ffffff" rx="8"/>
      <text x="{pad_l}" y="20" font-size="13" font-weight="700" fill="#0f172a">Real-Money Market Consensus (Blue) vs. Hotspawn Crowd Vote (Red — Ignored)</text>
      <circle cx="{pad_l}" cy="33" r="4.5" fill="#1d4ed8"/><text x="{pad_l+9}" y="37" font-size="11" fill="#334155">Sharp De-Vigged Market</text>
      <circle cx="{pad_l+155}" cy="33" r="4.5" fill="#dc2626"/><text x="{pad_l+164}" y="37" font-size="11" fill="#334155">Hotspawn Crowd % (Never Used)</text>
      {''.join(items)}
    </svg>
    """


def page_shell(
    filename: str,
    title: str,
    description: str,
    counts: dict[str, Any],
    ref_iso: str,
    body_html: str,
) -> str:
    nav_items = [
        ("index.html", "Executive Summary", None),
        ("picks.html", "All Open Picks", counts["open_total"]),
        ("featured.html", "Sportsbook Lines", counts["tier1_market_total"]),
        ("originated.html", "Low-Tier Originated", counts["tier2_originated_total"]),
        ("unresolved.html", "Unresolved & Limits", counts["tier3_unresolved_open_total"]),
        ("tournaments.html", "Tournaments", counts["competitions_total"]),
        ("teams.html", "Teams", counts["teams_verified_total"]),
        ("methodology.html", "Methodology", None),
        ("flagged.html", "Flagged Audit", counts["flagged_irregularities_count"]),
    ]
    nav_links = []
    for href, label, badge_n in nav_items:
        cls = "nav-link active" if href == filename else "nav-link"
        cnt_html = f'<span class="nav-count">{badge_n}</span>' if badge_n is not None else ""
        nav_links.append(f'<a class="{cls}" href="{href}">{esc(label)}{cnt_html}</a>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} — Hotspawn LoL Pick'ems Quant Hub</title>
  <meta name="description" content="{esc(description)}">
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <header class="site-header">
    <div class="header-inner">
      <div class="brand-row">
        <a class="brand" href="index.html">
          <span class="brand-mark">LoL</span>
          <span>Hotspawn Pick'ems Quant Hub</span>
        </a>
        <span class="status-pill">
          <span class="status-dot"></span>
          <span>Auto-Refreshed q4h · Snapshot <time data-utc="{esc(ref_iso)}">{fmt_utc(ref_iso)}</time></span>
        </span>
      </div>
      <nav class="nav-scroller" aria-label="Primary navigation">
        {''.join(nav_links)}
      </nav>
    </div>
  </header>

  <main class="container">
    {body_html}
  </main>

  <footer class="site-footer">
    <div>
      <strong>Zero-Crowd Probability Guarantee:</strong> Hotspawn crowd pick percentages are never used in any probability,
      rating, or pick formula. All probabilities derive strictly from de-vigged real-money external betting markets
      (Pinnacle, Polymarket, Kalshi, specialist esportsbooks) or pre-match official Leaguepedia/organizer match records.
    </div>
    <div style="margin-top:8px;">
      Data feeds: <a href="data/picks.json">data/picks.json</a> ·
      <a href="data/picks.csv">data/picks.csv</a> ·
      <a href="data/calibration.json">data/calibration.json</a> ·
      <a href="data/flagged.json">data/flagged.json</a> ·
      Live target: <a href="https://play.hotspawn.com/lol-pickems" target="_blank" rel="noopener noreferrer">play.hotspawn.com/lol-pickems ↗</a>
    </div>
  </footer>

  <script src="assets/app.js" defer></script>
</body>
</html>
"""


def build_all_pages(data_dir: Path = Path("data"), out_dir: Path = Path(".")) -> list[str]:
    picks_doc = json.loads((data_dir / "picks.json").read_text(encoding="utf-8"))
    calibration = json.loads((data_dir / "calibration.json").read_text(encoding="utf-8"))
    teams_list = json.loads((data_dir / "teams_index.json").read_text(encoding="utf-8"))
    flagged_doc = json.loads((data_dir / "flagged.json").read_text(encoding="utf-8"))

    summary = picks_doc["summary"]
    counts = summary["counts"]
    ref_iso = summary["reference_snapshot_at"]
    all_rows: list[dict[str, Any]] = picks_doc["picks"]

    open_rows = [r for r in all_rows if r["is_open"]]
    market_rows = [r for r in open_rows if r["status"] in ("market_consensus", "esportsbook_line")]
    originated_rows = [r for r in open_rows if r["status"] == "originated"]
    unresolved_open = [r for r in open_rows if r["status"] == "unresolved"]
    stale_rows = [r for r in all_rows if not r["is_open"]]
    open_comps = sorted({r["competition"] for r in open_rows})

    written: list[str] = []

    # ------------------------------------------------------------------
    # 1. index.html — Upfront Executive Summary & Mobile Command Center
    # ------------------------------------------------------------------
    urgent_preview = market_rows + [r for r in originated_rows if 0 < r["hours_until_lock"] <= 48.0][:8]
    tourn_rows_html = []
    for t in summary["tournaments"]:
        if t["open_count"] == 0:
            continue
        comp_q = quote(t["competition"])
        tourn_rows_html.append(f"""
        <tr>
          <td><a href="picks.html?comp={comp_q}"><strong>{esc(t['competition'])}</strong></a><div class="odds-sub">{esc(t['region'])}</div></td>
          <td><strong>{t['open_count']}</strong></td>
          <td>{t['market_count']}</td>
          <td>{t['originated_count']}</td>
          <td>{t['unresolved_open_count']}</td>
          <td><span class="badge {'badge-market' if t['market_count'] else 'badge-orig'}">{esc(t['primary_method'])}</span></td>
          <td>
            <div class="source-links">
              <a class="src-chip" href="picks.html?comp={comp_q}">View Picks →</a>
              <a class="src-chip" href="{esc(t['leaguepedia_url'])}" target="_blank" rel="noopener noreferrer">Leaguepedia ↗</a>
              <a class="src-chip" href="{esc(t['organizer_url'])}" target="_blank" rel="noopener noreferrer">Official ↗</a>
            </div>
          </td>
        </tr>
        """)

    index_body = f"""
    <section class="exec-card">
      <span class="eyebrow">Executive Summary · Live Hotspawn LoL Pick'ems Intelligence</span>
      <h1>Independent Win Probabilities &amp; Verified Picks Across All {counts['open_total']} Open LoL Matches</h1>
      <p class="lead">
        Hotspawn crowd votes are <strong>completely excluded</strong> from every model calculation. We price high-tier matches
        directly from de-vigged real-money sportsbooks &amp; prediction exchanges (<strong>Pinnacle, Polymarket, Kalshi, and specialist LoL esportsbooks</strong>),
        originate calibrated lines for unlisted low-tier regional leagues using <strong>{counts['official_matches_modeled']:,} verified 2026 match records</strong>,
        and isolate every unresolvable fixture and upstream data defect transparently.
      </p>

      <div class="cta-grid">
        <a class="cta-btn primary" href="picks.html">
          <span>All Open Picks ({counts['actionable_open_picks']} Actionable)</span>
          <span>→</span>
        </a>
        <a class="cta-btn" href="picks.html?window=48h">
          <span>Locking Next 48h ({counts['urgent_48h_open']} Urgent)</span>
          <span>→</span>
        </a>
        <a class="cta-btn" href="featured.html">
          <span>Sportsbook &amp; Exchange Picks ({counts['tier1_market_total']})</span>
          <span>→</span>
        </a>
        <a class="cta-btn" href="originated.html">
          <span>Low-Tier Originated Picks ({counts['tier2_originated_total']})</span>
          <span>→</span>
        </a>
        <a class="cta-btn warn" href="unresolved.html">
          <span>Unresolved &amp; Limitations ({counts['tier3_unresolved_open_total']} Open + {counts['stale_past_lock_total']} Stale)</span>
          <span>→</span>
        </a>
        <a class="cta-btn danger" href="flagged.html">
          <span>Flagged Irregularities ({counts['flagged_irregularities_count']} Alerts)</span>
          <span>→</span>
        </a>
      </div>

      <div class="kpi-grid">
        <div class="kpi-box">
          <div class="kpi-value">{counts['actionable_open_picks']} / {counts['open_total']}</div>
          <div class="kpi-label">Open Matches Resolved</div>
          <div class="kpi-sub">96.4% actionable coverage across {counts['competitions_open']} active leagues</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-value">{counts['tier1_market_total']}</div>
          <div class="kpi-label">Sportsbook &amp; Exchange Picks</div>
          <div class="kpi-sub">9 four-venue consensus + 1 specialist esportsbook (LCP)</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-value">{counts['tier2_originated_total']}</div>
          <div class="kpi-label">Originated Low-Tier Picks</div>
          <div class="kpi-sub">{summary['calibration_headline']['accuracy_pct']}% OOS accuracy · Brier {summary['calibration_headline']['brier']} (−{summary['calibration_headline']['brier_improvement_pct']}%)</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-value">{counts['tier3_unresolved_open_total']} + {counts['stale_past_lock_total']}</div>
          <div class="kpi-label">Unresolved Open + Stale API Rows</div>
          <div class="kpi-sub">1 removed team, 6 dead-even 50/50s, 69 past-lock orphans</div>
        </div>
      </div>

      <div class="callout callout-danger">
        <strong>Critical Live Pick'em Trap Alert (#1071216 — Komplettligaen 2026 Autumn):</strong>
        Official Norwegian league records confirm <strong>Solid Gaming was removed from the league in Round 10</strong>
        (<code>dqteams=Solid Gaming</code>), and all 4 prior Solid Gaming fixtures on Hotspawn went unplayed. Yet
        <strong>72% of Hotspawn users picked Solid Gaming</strong> vs. DMG Esports Norway!
        <strong>Never pick Solid Gaming</strong> — select active <strong>DMG Esports Norway</strong> (pushes if voided; wins full points if settled as walkover).
        <a href="flagged.html"><strong>Read full forensic report →</strong></a>
      </div>

      <div class="callout callout-warn">
        <strong>Summary of Unresolved Picks &amp; Structural Model Limitations (<a href="unresolved.html">Full Section &amp; Table →</a>):</strong>
        <ul class="exec-list">
          <li><strong>1 Removed-Team Phantom Fixture (#1071216):</strong> <em>Solid Gaming vs DMG Esports Norway</em> — Solid Gaming was administratively removed in Round 10; no on-Rift gameplay probability exists.</li>
          <li><strong>6 Pure Statistical Dead Heats (&plusmn;0.5% of 50.0%):</strong> Three matches in <em>PRM 2nd Division</em> (#1079030, #1079038, #1079053) and three in <em>PRM 3rd Division</em> (#1075770, #1075791, #1075802) have zero sportsbook coverage and posterior probabilities between <strong>49.8% and 50.5%</strong>. Rather than faking edge or using crowd votes, we quarantine them in <a href="unresolved.html">Unresolved &amp; Limitations</a> alongside slight statistical leans for full-card submission.</li>
          <li><strong>{counts['stale_past_lock_total']} Orphaned Past-Lock API Rows:</strong> Hotspawn's <code>status=scheduled</code> feed still returns {counts['stale_past_lock_total']} already-locked historical matches (Aug 26 – Oct 21); we verified official Leaguepedia final scores on <strong>{counts['stale_with_official_score']}/{counts['stale_past_lock_total']}</strong> of them.</li>
          <li><strong>Key Low-Tier Limitations:</strong> Unannounced amateur stand-ins/substitutions, pre-game draft &amp; Blue/Red side selection unknown days ahead, patch meta shifts, and wide credible intervals (&plusmn;18–30 pp) early in regional group stages.</li>
        </ul>
      </div>
    </section>

    <section class="section-block" id="featured-preview">
      <div class="section-head">
        <div>
          <h2>Featured Real-Money Market &amp; Urgent Upcoming Picks</h2>
          <p class="section-sub">All 10 sportsbook/exchange-priced matches plus next locking regional fixtures (<a href="picks.html">open full 195-match board →</a>)</p>
        </div>
      </div>
      <div class="cards-grid two-col">
        {''.join(render_pick_card(r) for r in urgent_preview)}
      </div>
    </section>

    <section class="section-block" id="active-competitions">
      <div class="section-head">
        <div>
          <h2>Active Open Competitions Breakdown ({counts['competitions_open']} Tournaments)</h2>
          <p class="section-sub">Tap any tournament to open its filtered Pick'em board (<a href="tournaments.html">see all 27 competitions including past-lock archive →</a>)</p>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Competition</th>
              <th>Open</th>
              <th>Market</th>
              <th>Originated</th>
              <th>Unresolved</th>
              <th>Pricing Tier</th>
              <th>Links</th>
            </tr>
          </thead>
          <tbody>
            {''.join(tourn_rows_html)}
          </tbody>
        </table>
      </div>
    </section>
    """
    (out_dir / "index.html").write_text(
        page_shell("index.html", "Executive Summary & Live Picks", "Independent LoL Pick'ems win probabilities and verified picks", counts, ref_iso, index_body),
        encoding="utf-8",
    )
    written.append("index.html")

    # ------------------------------------------------------------------
    # 2. picks.html — All 195 Open Upcoming LoL Matches
    # ------------------------------------------------------------------
    picks_body = f"""
    <section class="exec-card">
      <span class="eyebrow">Master Open Pick'em Board</span>
      <h1>All {counts['open_total']} Open LoL Matches ({counts['actionable_open_picks']} Actionable + {counts['tier3_unresolved_open_total']} Caveats)</h1>
      <p class="lead">
        Filter by league, pricing tier, or lock window below. Every match displays Team A and Team B win probabilities,
        recommended winner pick, series format, and direct official verification links.
      </p>
    </section>
    {render_dual_board(open_rows, open_comps, show_tier_select=True, default_view_label="open matches")}
    """
    (out_dir / "picks.html").write_text(
        page_shell("picks.html", "All Open LoL Picks", "Complete filterable board of all open Hotspawn LoL Pick'ems", counts, ref_iso, picks_body),
        encoding="utf-8",
    )
    written.append("picks.html")

    # ------------------------------------------------------------------
    # 3. featured.html — Tier-1 Real-Money Sportsbook & Exchange Picks
    # ------------------------------------------------------------------
    venue_matrix_rows = []
    for r in market_rows:
        vmap = {v["venue_key"]: v for v in (r["market_detail"] or {}).get("venues", [])}
        pin_v = vmap.get("pinnacle")
        pol_v = vmap.get("polymarket")
        kal_v = vmap.get("kalshi")
        ebk_v = vmap.get("esportsbook")
        crowd_pct = r["hotspawn_crowd_display_only"]["team0_picked_pct"]
        venue_matrix_rows.append(f"""
        <tr>
          <td><time data-utc="{esc(r['scheduled_utc'])}" data-show-local="1">{fmt_utc(r['scheduled_utc'])}</time><div class="odds-sub">{esc(r['competition'])}</div></td>
          <td><strong>{esc(r['team0'])}</strong> vs <strong>{esc(r['team1'])}</strong><div class="odds-sub">{esc(r['best_of_display'])} · {r['offered_points']} pts</div></td>
          <td>{f"{pin_v['p0']*100:.1f}% ({pin_v['am0']:+d}/{pin_v['am1']:+d})" if pin_v else "—"}</td>
          <td>{f"{pol_v['p0']*100:.1f}% (${pol_v['volume_usd']:,.0f})" if pol_v else "—"}</td>
          <td>{f"{kal_v['p0']*100:.1f}%" if kal_v else "—"}</td>
          <td>{f"{ebk_v['p0']*100:.1f}% ({ebk_v['dec0']:.3g}/{ebk_v['dec1']:.3g})" if ebk_v else "—"}</td>
          <td><strong>{r['team0_prob']*100:.1f}% / {r['team1_prob']*100:.1f}%</strong></td>
          <td><strong>{esc(r['pick'])}</strong><div class="odds-sub">Crowd: {f"{crowd_pct:.0f}% {esc(r['team0'])}" if crowd_pct is not None else "—"}</div></td>
          <td>{render_sources_chips(r['sources'])}</td>
        </tr>
        """)

    featured_body = f"""
    <section class="exec-card">
      <span class="eyebrow">Tier-1 External Market Consensus</span>
      <h1>Sportsbook &amp; Prediction Exchange Picks ({len(market_rows)} Open Matches)</h1>
      <p class="lead">
        Nine high-profile matches across <strong>Worlds 2026 Swiss Stage Round 1</strong> and the <strong>EMEA Masters 2026 Summer Grand Final</strong>
        are priced simultaneously on <strong>four real-money venues</strong> (Pinnacle, Polymarket CLOB, Kalshi CFTC Exchange, and specialist esportsbooks).
        The 10th match — <strong>LCP 2027 Promotion: Ground Zero Gaming vs Frank Esports</strong> — is absent on Polymarket and Kalshi
        yet resolved directly from live specialist LoL esportsbook decimal odds (<code>1.025 vs 10.50</code> &rarr; <strong>91.1% vs 8.9%</strong>).
      </p>
      <div class="chart-card">
        {build_svg_market_vs_crowd(market_rows)}
      </div>
    </section>

    <section class="section-block">
      <div class="section-head">
        <h2>Cross-Venue Real-Money Odds Comparison Table (Team A Perspective)</h2>
      </div>
      <div class="table-wrap" style="margin-bottom:20px;">
        <table class="data-table">
          <thead>
            <tr>
              <th>Kickoff</th>
              <th>Matchup</th>
              <th>Pinnacle (De-Vig)</th>
              <th>Polymarket CLOB</th>
              <th>Kalshi Exchange</th>
              <th>Esportsbook</th>
              <th>Sharp Consensus</th>
              <th>Pick (vs Crowd)</th>
              <th>Official Sources</th>
            </tr>
          </thead>
          <tbody>
            {''.join(venue_matrix_rows)}
          </tbody>
        </table>
      </div>
      <div class="cards-grid two-col">
        {''.join(render_pick_card(r) for r in market_rows)}
      </div>
    </section>
    """
    (out_dir / "featured.html").write_text(
        page_shell("featured.html", "Sportsbook & Exchange Picks", "De-vigged Pinnacle, Polymarket, Kalshi & esportsbook LoL picks", counts, ref_iso, featured_body),
        encoding="utf-8",
    )
    written.append("featured.html")

    # ------------------------------------------------------------------
    # 4. originated.html — Tier-2 Originated Low-Tier Regional Picks
    # ------------------------------------------------------------------
    orig_comps = sorted({r["competition"] for r in originated_rows})
    jump_pills = "".join(
        f'<a class="mini-btn" href="originated.html?comp={quote(c)}">{esc(c)} ({sum(1 for r in originated_rows if r["competition"] == c)})</a>'
        for c in orig_comps
    )
    originated_body = f"""
    <section class="exec-card">
      <span class="eyebrow">Tier-2 Quantitative Line Origination</span>
      <h1>Originated Low-Tier Regional LoL Picks ({len(originated_rows)} Decisive Matches Across {len(orig_comps)} Leagues)</h1>
      <p class="lead">
        None of these European ERL 2nd/3rd division, UK 4 Nations, Nordic, MENA, or Brazilian Série B fixtures appear on Polymarket,
        Kalshi, or Pinnacle. Each line is originated strictly from official pre-match tournament and 2026 split match records via our
        walk-forward-validated Bayesian Bradley–Terry + Series Combinatorics model (<code>λ* = 1.50</code>, OOS Brier <code>0.2145</code>).
      </p>
      <div class="btn-group">{jump_pills}</div>
    </section>
    {render_dual_board(originated_rows, orig_comps, show_tier_select=False, default_view_label="originated low-tier matches")}
    """
    (out_dir / "originated.html").write_text(
        page_shell("originated.html", "Originated Low-Tier Picks", "Bayesian Bradley-Terry originated probabilities for regional LoL leagues", counts, ref_iso, originated_body),
        encoding="utf-8",
    )
    written.append("originated.html")

    # ------------------------------------------------------------------
    # 5. unresolved.html — Unresolved Picks, Limitations & Stale Rows
    # ------------------------------------------------------------------
    stale_table_rows = []
    for r in stale_rows:
        stale_table_rows.append(f"""
        <tr>
          <td><time data-utc="{esc(r['scheduled_utc'])}">{fmt_utc(r['scheduled_utc'])}</time><div class="odds-sub">#{esc(r['id'])}</div></td>
          <td><strong>{esc(r['competition'])}</strong><div class="odds-sub">{esc(r['region'])}</div></td>
          <td><strong>{esc(r['team0'])}</strong> vs <strong>{esc(r['team1'])}</strong></td>
          <td>{esc(r['stale_official_result'])}</td>
          <td>{render_sources_chips(r['sources'])}</td>
        </tr>
        """)

    unresolved_body = f"""
    <section class="exec-card">
      <span class="eyebrow">Transparency &amp; Epistemic Boundaries</span>
      <h1>Unresolved Picks ({len(unresolved_open)} Open) &amp; Structural Limitations</h1>
      <p class="lead">
        Honest quantitative modeling requires refusing to fabricate edges when a team has been removed from a league
        or when two unpriced amateur squads rate within &plusmn;0.5% of an exact 50/50 coin flip. Below are all
        <strong>{len(unresolved_open)} open unresolved fixtures</strong>, our defensive card-submission leans, the
        <strong>6 fundamental limitations</strong> of low-tier LoL modeling, and all <strong>{len(stale_rows)} past-lock orphaned rows</strong>
        still served as <code>scheduled</code> by Hotspawn's API.
      </p>
    </section>

    <section class="section-block">
      <div class="section-head">
        <h2>Part 1 — Open Unresolved / Indeterminate Matches ({len(unresolved_open)} Fixtures)</h2>
      </div>
      <div class="cards-grid two-col">
        {''.join(render_pick_card(r) for r in unresolved_open)}
      </div>
    </section>

    <section class="section-block">
      <div class="exec-card">
        <h2>Part 2 — Six Structural Limitations of Low-Tier LoL Origination</h2>
        <ul class="exec-list">
          <li><strong>1. Zero Sportsbook Liquidity &amp; Aggregator Dummy Odds:</strong> Below EMEA Masters and ERL 1st divisions, major books post zero markets (and aggregators display fake symmetric <code>1.80 / 1.80</code> placeholders that must be rejected).</li>
          <li><strong>2. Unannounced Pre-Lock Amateur Substitutions:</strong> Prime League Div 2/3, UK 4 Nations, RIVALS League, and Tunisian/Arabian division teams routinely field 6–8 player rosters with emergency solo-queue substitutes announced only inside the tournament lobby minutes before game start.</li>
          <li><strong>3. Unknown Pre-Draft Side Selection &amp; Champion Draft:</strong> Blue-side vs. Red-side selection and draft matchups shift single-game LoL win probability by 3–5 percentage points, which is fundamentally unobservable days ahead of lock.</li>
          <li><strong>4. Mid-Split Administrative Removals, Disbandments &amp; Forfeits:</strong> Regional leagues experience frequent mid-season withdrawals (e.g., <em>Solid Gaming</em> in Komplettligaen Round 10), roster-ineligibility forfeits (<em>Team Reds</em> in Arabian League 2nd Div), and slot transfers (<em>reGOLD eSport</em>, <em>The Bandits Prime</em>).</li>
          <li><strong>5. Upstream Feed Entity Misbindings:</strong> Automated tournament feeds occasionally bind shared acronyms to historical teams from different continents (e.g., German squad <em>PvB Nation</em> mislabeled as defunct Vietnamese team <em>Phong Vũ Buffalo</em>).</li>
          <li><strong>6. Finite-Sample Statistical Uncertainty Floor:</strong> Early in a regional split (4–10 games played), true posterior uncertainty spans roughly &plusmn;15–30 percentage points even under optimal Bayesian shrinkage (<code>λ* = 1.50</code>); any matchup landing inside <code>[49.5%, 50.5%]</code> is genuinely indistinguishable from a fair coin toss.</li>
        </ul>
      </div>
    </section>

    <section class="section-block" id="stale-past-lock">
      <div class="section-head">
        <div>
          <h2>Part 3 — Past-Lock Orphaned Hotspawn API Rows ({len(stale_rows)} Fixtures)</h2>
          <p class="section-sub">Already past <code>lock_time</code> (unpickable on Hotspawn), audited line-by-line against official Leaguepedia match results ({counts['stale_with_official_score']}/{len(stale_rows)} completed scores recovered)</p>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Original Scheduled UTC</th>
              <th>Competition</th>
              <th>Matchup</th>
              <th>Verified Official Leaguepedia Status / Score</th>
              <th>Official Sources</th>
            </tr>
          </thead>
          <tbody>
            {''.join(stale_table_rows)}
          </tbody>
        </table>
      </div>
    </section>
    """
    (out_dir / "unresolved.html").write_text(
        page_shell("unresolved.html", "Unresolved Picks & Limitations", "Unresolved LoL matches, structural modeling limits, and stale feed audit", counts, ref_iso, unresolved_body),
        encoding="utf-8",
    )
    written.append("unresolved.html")

    # ------------------------------------------------------------------
    # 6. tournaments.html — All 27 Competitions Directory
    # ------------------------------------------------------------------
    all_tourn_rows = []
    for t in summary["tournaments"]:
        comp_q = quote(t["competition"])
        board_href = f"picks.html?comp={comp_q}" if t["open_count"] > 0 else "unresolved.html#stale-past-lock"
        all_tourn_rows.append(f"""
        <tr>
          <td><strong>{esc(t['competition'])}</strong><div class="odds-sub">{esc(t['circuit'])}</div></td>
          <td>{esc(t['region'])}</td>
          <td>{esc(t['format_note'])}</td>
          <td><strong>{t['open_count']}</strong> / {t['total_rows']}</td>
          <td>{t['market_count']} mkt · {t['originated_count']} orig · {t['unresolved_open_count']} unres · {t['stale_count']} stale</td>
          <td><span class="badge {'badge-market' if t['market_count'] else ('badge-orig' if t['open_count'] else 'badge-neutral')}">{esc(t['primary_method'])}</span></td>
          <td>
            <div class="source-links">
              <a class="src-chip" href="{board_href}">Picks →</a>
              <a class="src-chip" href="{esc(t['leaguepedia_url'])}" target="_blank" rel="noopener noreferrer">Leaguepedia ↗</a>
              <a class="src-chip" href="{esc(t['organizer_url'])}" target="_blank" rel="noopener noreferrer">Organizer ↗</a>
            </div>
          </td>
        </tr>
        """)
    tournaments_body = f"""
    <section class="exec-card">
      <span class="eyebrow">Tournament Coverage Matrix</span>
      <h1>All {counts['competitions_total']} LoL Competitions on Hotspawn ({counts['competitions_open']} Active Open + {counts['competitions_total'] - counts['competitions_open']} Past-Lock)</h1>
      <p class="lead">
        100% of all 27 competitions in Hotspawn's LoL feed are mapped to canonical Leaguepedia <code>Data:</code> match schedules
        and primary regional tournament organizers.
      </p>
    </section>
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Competition</th>
            <th>Region</th>
            <th>Verified Format</th>
            <th>Open / Total</th>
            <th>Breakdown</th>
            <th>Method</th>
            <th>Official Links</th>
          </tr>
        </thead>
        <tbody>
          {''.join(all_tourn_rows)}
        </tbody>
      </table>
    </div>
    """
    (out_dir / "tournaments.html").write_text(
        page_shell("tournaments.html", "All 27 LoL Tournaments", "Tournament coverage directory across international, ERL, and regional LoL leagues", counts, ref_iso, tournaments_body),
        encoding="utf-8",
    )
    written.append("tournaments.html")

    # ------------------------------------------------------------------
    # 7. teams.html — All 204 Competition-Scoped Verified Teams
    # ------------------------------------------------------------------
    team_comp_opts = '<option value="all">All Competitions (' + str(len(teams_list)) + ")</option>"
    for c in sorted({t["competition"] for t in teams_list}):
        team_comp_opts += f'<option value="{esc(c)}">{esc(c)}</option>'

    team_rows_html = []
    for t in teams_list:
        note = t.get("admin_note")
        note_badge = f'<span class="badge badge-flag">{esc(note["badge"])}</span>' if note else ""
        search_str = f"{t['team_name']} {' '.join(t['canonical_aliases'])} {t['competition']} {t['region']}"
        team_rows_html.append(f"""
        <tr class="pick-row"
          data-comp="{esc(t['competition'])}"
          data-status="originated"
          data-hours="24"
          data-favprob="{0.5 + t['theta_map']*0.1:.4f}"
          data-points="10"
          data-delta="0"
          data-kickoff="0"
          data-search="{esc(search_str)}">
          <td><strong>{esc(t['team_name'])}</strong> {note_badge}<div class="odds-sub">Aliases: {esc(', '.join(t['canonical_aliases']))}</div></td>
          <td>{esc(t['competition'])}<div class="odds-sub">{esc(t['region'])}</div></td>
          <td><strong>{t['theta_map']:+.2f}</strong> &plusmn; {t['theta_se']:.2f}</td>
          <td><strong>{esc(t['current_series_wl'])}</strong> ({esc(t['current_game_wl'])} games)</td>
          <td>{esc(t['prior_2026_series_wl'])} ({esc(t['prior_2026_game_wl'])} games)</td>
          <td>
            <div class="source-links">
              <a class="src-chip" href="{esc(t['leaguepedia_tournament_url'])}" target="_blank" rel="noopener noreferrer">Split Page ↗</a>
              <a class="src-chip" href="{esc(t['team_reference_url'])}" target="_blank" rel="noopener noreferrer">Team Page ↗</a>
            </div>
          </td>
        </tr>
        """)
    teams_body = f"""
    <section class="exec-card">
      <span class="eyebrow">Entity-Isolated Team Ratings</span>
      <h1>All {len(teams_list)} Competition-Scoped LoL Team Profiles</h1>
      <p class="lead">
        Teams are isolated strictly by <code>(competition, participant_id)</code> so homonymous clubs across different countries
        (such as five distinct regional <em>Rich Gang</em> squads or German <em>PvB Nation</em> vs. historical Vietnamese <em>Phong Vũ Buffalo</em>)
        never contaminate each other's ratings.
      </p>
    </section>
    <div class="filter-bar">
      <input id="filter-search" class="input-control" type="search" placeholder="Search team name, alias, country, or competition…" aria-label="Search teams">
      <select id="filter-comp" class="select-control" aria-label="Filter teams by competition">{team_comp_opts}</select>
    </div>
    <div class="filter-meta"><div>Showing <strong id="visible-count">{len(teams_list)}</strong> of {len(teams_list)} verified team profiles</div></div>
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Team &amp; Canonical Aliases</th>
            <th>Competition &amp; Region</th>
            <th>BT Rating (θ̂ &plusmn; SE)</th>
            <th>Current Split Record</th>
            <th>Prior 2026 Split Record</th>
            <th>Verified Sources</th>
          </tr>
        </thead>
        <tbody id="picks-table-body">
          {''.join(team_rows_html)}
        </tbody>
      </table>
    </div>
    """
    (out_dir / "teams.html").write_text(
        page_shell("teams.html", "Verified Team Ratings", "Competition-scoped Bradley-Terry LoL team ratings and 2026 W-L records", counts, ref_iso, teams_body),
        encoding="utf-8",
    )
    written.append("teams.html")

    # ------------------------------------------------------------------
    # 8. methodology.html — Mathematical Model, Walk-Forward Proof & Spec
    # ------------------------------------------------------------------
    rel_rows = "".join(
        f"<tr><td><strong>{esc(b['label'])}</strong></td><td>{b['count']}</td>"
        f"<td>{b['mean_predicted']*100:.1f}%</td><td><strong>{b['empirical_win_rate']*100:.1f}%</strong> (&plusmn;{b['ci95_half_width']*100:.1f}%)</td></tr>"
        for b in calibration["reliability_bins"]
    )
    methodology_body = f"""
    <section class="exec-card">
      <span class="eyebrow">Quantitative Architecture &amp; Validation</span>
      <h1>Methodology, Walk-Forward Calibration &amp; Automated Refresh Pipeline</h1>
      <p class="lead">
        Every probability on this dashboard is reproducible from committed primary source snapshots via
        <code>python3 scripts/refresh.py</code>, running automatically every 4 hours on GitHub Actions
        (<code>cron: '17 */4 * * *'</code>).
      </p>

      <h2>1. Strict Three-Tier Probability Waterfall</h2>
      <ul class="exec-list">
        <li><strong>Tier 1 — External Real-Money Markets (<code>featured.html</code>, {counts['tier1_market_total']} open matches):</strong>
          De-vigged full-match moneyline consensus across <strong>Pinnacle</strong> (weight 0.42), <strong>Polymarket CLOB</strong> (0.28),
          <strong>Kalshi CFTC Exchange</strong> (0.20), and verified <strong>specialist esportsbooks</strong> (0.10), normalized over active venues.
          Tier-2 ratings are <em>never</em> blended into Tier-1 market probabilities.</li>
        <li><strong>Tier 2 — Bayesian Bradley–Terry + Series Combinatorics (<code>originated.html</code>, {counts['tier2_originated_total']} open matches):</strong>
          Invoked strictly when zero valid external betting lines exist. Fits L2-regularized game log-strengths by Newton–Raphson
          to machine precision (<code>||∇L||∞ &lt; 10⁻¹³</code>), marginalizes posterior skill variance via MacKay's probit-logistic integral,
          and applies exact series combinatorics for verified <code>Bo1</code>, <code>Bo2</code>, <code>Bo3</code>, and <code>Bo5</code> formats.</li>
        <li><strong>Tier 3 — Explicit Unresolved Quarantine (<code>unresolved.html</code>, {counts['tier3_unresolved_open_total']} open matches):</strong>
          Quarantines removed-team phantom fixtures and pure <code>[49.5%, 50.5%]</code> statistical dead heats without ever touching Hotspawn crowd votes.</li>
      </ul>

      <div class="formula-box">
L(θ) = -Σ_m [ w_1m log σ(θ_i - θ_j) + w_2m log σ(θ_j - θ_i) ] + (λ / 2) ||θ||₂²,   λ* = 1.50
Σ = H(θ̂)⁻¹,   v_ij = Σ_ii + Σ_jj - 2 Σ_ij
p_game(i &gt; j | D) = σ( (θ̂_i - θ̂_j) / sqrt(1 + (π / 8) v_ij) )
P_Bo1(p) = p,   P_Bo3(p) = p²(3 - 2p),   P_Bo5(p) = p³(10 - 15p + 6p²)
      </div>

      <h2>2. Out-of-Sample Walk-Forward Empirical Calibration (N = {calibration['n_walkforward_matches']:,} Matches)</h2>
      <p class="lead">
        Evaluating strictly out-of-sample day-by-day (<code>train_date &lt; match_date</code>) across all {calibration['n_walkforward_matches']:,}
        completed non-forfeit 2026 series reduces Brier score by <strong>{calibration['brier_skill_improvement_pct']}%</strong>
        (<code>{calibration['brier_score']}</code> vs. <code>0.2500</code> coin flip), cuts log-loss from <code>0.6931</code> to
        <strong><code>{calibration['log_loss']}</code></strong>, and achieves <strong>{calibration['accuracy']*100:.1f}%</strong> winner accuracy
        with Expected Calibration Error (ECE) of <strong>{calibration['expected_calibration_error']*100:.2f}%</strong>.
      </p>

      <div class="chart-grid">
        <div class="chart-card">{build_svg_reliability(calibration)}</div>
        <div class="chart-card">{build_svg_lambda_sweep(calibration)}</div>
      </div>

      <div class="table-wrap" style="margin-top:16px;">
        <table class="data-table">
          <thead>
            <tr>
              <th>Predicted Favorite Bucket</th>
              <th>Out-of-Sample Matches</th>
              <th>Mean Predicted Win %</th>
              <th>Actual Empirical Win % (95% CI)</th>
            </tr>
          </thead>
          <tbody>{rel_rows}</tbody>
        </table>
      </div>

      <h2 style="margin-top:24px;">3. Reverse-Engineered Hotspawn Architecture</h2>
      <ul class="exec-list">
        <li><strong>Primary JSON REST Feed:</strong> <code>GET https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&amp;status=scheduled&amp;tenantId=1</code></li>
        <li><strong>Multi-Sport Lobby Feed:</strong> <code>GET https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?status=scheduled&amp;tenantId=1</code> ({counts['all_sports_scheduled_total']} total scheduled rows: 264 LoL + 75 CS2)</li>
        <li><strong>Angular SSR Hydration &amp; Permalinks:</strong> <code>script#ng-state</code> on <code>https://play.hotspawn.com/lol-pickems</code> &amp; <code>/lobby</code> plus <code>/api/v1/admin/gamification/fixtures/permalinks</code></li>
      </ul>
    </section>
    """
    (out_dir / "methodology.html").write_text(
        page_shell("methodology.html", "Methodology & Calibration", "Bayesian Bradley-Terry specification, walk-forward calibration, and API architecture", counts, ref_iso, methodology_body),
        encoding="utf-8",
    )
    written.append("methodology.html")

    # ------------------------------------------------------------------
    # 9. flagged.html — Flagged for Review (Forensic Data Audit)
    # ------------------------------------------------------------------
    flag_cards_html = []
    for flg in flagged_doc["flags"]:
        sev_cls = "callout-danger" if flg["severity"] in ("CRITICAL", "HIGH") else "callout-warn"
        ids_preview = ", ".join(f"#{x}" for x in flg["affected_fixture_ids"][:8])
        flag_cards_html.append(f"""
        <article class="callout {sev_cls}">
          <div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:6px;margin-bottom:6px;">
            <span class="badge badge-flag">{esc(flg['flag_id'])} · {esc(flg['severity'])} · {esc(flg['category'])}</span>
            <span class="badge badge-neutral">{esc(flg['competition'])}</span>
          </div>
          <h3>{esc(flg['title'])}</h3>
          <p style="margin:6px 0;">{esc(flg['detail'])}</p>
          <p style="margin:6px 0;"><strong>Pipeline Action:</strong> {esc(flg['resolution'])}</p>
          <div style="font-size:0.78rem;margin-bottom:8px;"><strong>Sample Fixture IDs:</strong> <code>{esc(ids_preview)}</code></div>
          <div class="source-links">
            <a class="src-chip" href="{esc(flg['source_url'])}" target="_blank" rel="noopener noreferrer">Primary Proof ↗</a>
            <a class="src-chip" href="{esc(flg['secondary_url'])}" target="_blank" rel="noopener noreferrer">Secondary Verification ↗</a>
          </div>
        </article>
        """)

    div_rows_html = []
    for d in flagged_doc["crowd_divergences"]:
        div_rows_html.append(f"""
        <tr>
          <td><code>#{esc(d['id'])}</code></td>
          <td><strong>{esc(d['competition'])}</strong></td>
          <td><strong>{esc(d['match'])}</strong></td>
          <td>{status_badge(d['pricing_tier'])}</td>
          <td><strong>{esc(d['pick'])}</strong></td>
          <td><strong>{d['model_team0_pct']:.1f}%</strong></td>
          <td>{d['crowd_team0_pct']:.0f}%</td>
          <td><strong>{d['delta_pp']:+.1f} pp</strong></td>
          <td><a class="src-chip" href="{esc(d['source_url'])}" target="_blank" rel="noopener noreferrer">Source ↗</a></td>
        </tr>
        """)

    flagged_body = f"""
    <section class="exec-card">
      <span class="eyebrow">Forensic Quality Control</span>
      <h1>Flagged for Review — Upstream Data Irregularities &amp; Crowd Traps ({len(flagged_doc['flags'])} Findings)</h1>
      <p class="lead">
        Line-by-line verification of all {counts['lol_scheduled_total']} Hotspawn fixtures uncovered active removed teams,
        intercontinental acronym misbindings, overturned forfeit rulings, dummy aggregator odds, and extreme crowd biases.
      </p>
      {''.join(flag_cards_html)}
    </section>

    <section class="section-block">
      <div class="section-head">
        <div>
          <h2>Largest Sharp Model vs. Hotspawn Crowd Divergences (&ge;15 pp Gap)</h2>
          <p class="section-sub">Empirical proof of why Hotspawn crowd pick percentages are strictly excluded from all probability formulas</p>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Fixture</th>
              <th>Competition</th>
              <th>Matchup</th>
              <th>Method</th>
              <th>Pick</th>
              <th>Model Team A %</th>
              <th>Crowd Team A %</th>
              <th>Model − Crowd</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {''.join(div_rows_html)}
          </tbody>
        </table>
      </div>
    </section>
    """
    (out_dir / "flagged.html").write_text(
        page_shell("flagged.html", "Flagged Irregularities Audit", "Upstream data defects, league removals, forfeits, and crowd traps", counts, ref_iso, flagged_body),
        encoding="utf-8",
    )
    written.append("flagged.html")

    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    return written


if __name__ == "__main__":
    built = build_all_pages()
    print(f"Built {len(built)} static HTML pages: {', '.join(built)}")
