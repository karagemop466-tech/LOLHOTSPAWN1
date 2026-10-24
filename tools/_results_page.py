def build_results(rows: list[dict]) -> str:
    """Track record: every started card we can grade against the official series record."""
    doc = load_json(os.path.join(DATA, "matches.json")) or {}
    track = doc.get("track_record") or {}
    graded = sorted([r for r in rows if r.get("grade") in ("hit", "miss")],
                    key=lambda r: (r.get("start_utc") or ""), reverse=True)
    settled = [r for r in rows if r.get("grade") == "settled"]
    ungraded = [r for r in rows if r.get("stale") and not r.get("grade")]

    def grade_pill(g: str | None) -> str:
        if g == "hit":
            return '<span class="pill ok">HIT</span>'
        if g == "miss":
            return '<span class="pill bad">MISS</span>'
        if g == "settled":
            return '<span class="pill warn">SETTLED</span>'
        return '<span class="pill no">ungraded</span>'

    def result_cell(r: dict) -> str:
        res = r.get("result") or {}
        if not res:
            return '<span class="muted">no official record matched</span>'
        sc0, sc1 = res.get("score0"), res.get("score1")
        winner = r["team0"]["name"] if res.get("winner_side") == 0 else r["team1"]["name"]
        ff = res.get("forfeit_flag")
        ff_txt = f' <span class="muted small">FF={e(ff)}</span>' if ff not in (None, "", 0) else ""
        return (f'<strong>{e(winner)}</strong> won'
                f'<br><span class="muted small">{e(r["team0"]["name"])} {e(sc0)}&ndash;{e(sc1)} '
                f'{e(r["team1"]["name"])}{ff_txt}</span>'
                f'<br><a class="small" href="{e(res.get("source"))}" rel="noopener">Leaguepedia record</a>')

    def pick_cell(r: dict) -> str:
        p = r.get("pick") or {}
        if p.get("probability") is None:
            return (f'<strong class="res">{e(p.get("team") or "&mdash;")}</strong>'
                    f'<br><span class="small muted">settlement, no probability</span>')
        return (f'<strong>{e(p.get("team"))}</strong>'
                f'<br><span class="small muted">{p["probability"]*100:.1f}% to win</span>')

    trs = []
    for r in graded:
        trs.append(
            '<tr class="m-' + e(r["method"]) + '">'
            f'<td data-label="Kick-off" class="nowrap small">{e((r.get("start_utc") or "")[:16].replace("T", " "))} UTC</td>'
            f'<td data-label="Tournament" class="small">{e(r["competition"])}</td>'
            f'<td data-label="Match"><strong>{e(r["team0"]["name"])}</strong> <span class="muted">vs</span> '
            f'<strong>{e(r["team1"]["name"])}</strong></td>'
            f'<td data-label="Published pick">{pick_cell(r)}</td>'
            f'<td data-label="Official result">{result_cell(r)}</td>'
            f'<td data-label="Grade">{grade_pill(r.get("grade"))}</td>'
            f'<td data-label="Sources" class="srcs small">{_row_sources(r)}</td>'
            '</tr>')
    settled_rows = []
    for r in sorted(settled, key=lambda r: (r.get("start_utc") or ""), reverse=True):
        settled_rows.append(
            f'<tr><td data-label="Kick-off" class="small">{e((r.get("start_utc") or "")[:16].replace("T", " "))} UTC</td>'
            f'<td data-label="Tournament" class="small">{e(r["competition"])}</td>'
            f'<td data-label="Match">{e(r["team0"]["name"])} vs {e(r["team1"]["name"])}</td>'
            f'<td data-label="Settlement pick">{pick_cell(r)}</td>'
            f'<td data-label="Official record">{result_cell(r)}</td>'
            f'<td data-label="Grade">{grade_pill("settled")}</td>'
            f'<td data-label="Sources" class="srcs small">{_row_sources(r)}</td></tr>')

    by_method_rows = []
    for name, m in sorted((track.get("by_method") or {}).items(), key=lambda kv: -kv[1]["graded"]):
        by_method_rows.append(
            f'<tr><td>{badge(name)}</td><td class="num">{m["graded"]}</td><td class="num">{m["hits"]}</td>'
            f'<td class="num">{m["graded"] - m["hits"]}</td>'
            f'<td class="num">{m["accuracy"]*100:.1f}%</td></tr>')

    acc = track.get("accuracy")
    brier = track.get("brier")
    body = f"""
<section class="hero">
  <h2>Did the published picks actually win?</h2>
  <p>Every card on this site that has kicked off is graded against the official series record once one
  exists. This page is the honest scoreboard: it counts hits and misses of the <em>published</em> pick,
  never a probability rewritten after the result.</p>
  <div class="cta">
    <a class="btn primary" href="table.html">All matches &amp; picks &rarr;</a>
    <a class="btn" href="unresolved.html">Unresolved &amp; limitations</a>
  </div>
</section>

<section class="stats">
  {stat_card("Graded picks", track.get("graded", 0), "official series record matched", "ok")}
  {stat_card("Hits", track.get("hits", 0), "published pick won", "ok")}
  {stat_card("Misses", track.get("misses", 0), "the other side won", "unresolved")}
  {stat_card("Accuracy", f"{acc*100:.1f}%" if acc is not None else "&mdash;", "graded picks only", "model")}
  {stat_card("Brier score", f"{brier:.4f}" if brier is not None else "&mdash;", "lower is better", "")}
  {stat_card("Forfeit settlements", track.get("settled_forfeits", 0), "not counted as forecast wins", "provisional")}
  {stat_card("Started, ungraded", len(ungraded), "no consistent official record", "")}
</section>

<section class="panel">
  <h2>Graded picks</h2>
  <p class="lead">Newest first. A pick is graded only when the official record matches this fixture's team
  pair and kick-off (within 12 hours) and the recorded winner agrees with the recorded score. Anything less
  stays ungraded rather than being guessed.</p>
  {table(["Kick-off", "Tournament", "Match", "Published pick", "Official result", "Grade", "Sources"], trs) if trs else '<p class="muted">No graded picks in this snapshot yet.</p>'}
</section>

<section class="panel">
  <h2>Accuracy by how the line was made</h2>
  {table(["Method", "Graded", "Hits", "Misses", "Accuracy"], by_method_rows) if by_method_rows else '<p class="muted">No graded picks yet.</p>'}
  <p class="muted small">A market line and a model line are expected to differ: the market-backed
  sample is small (a handful of Worlds series), so read the model and provisional rows as the meaningful
  sample. Out-of-sample backtest of the rating model itself is on
  <a href="methodology.html">Method</a>.</p>
</section>

<section class="panel">
  <h2>Forfeit settlements</h2>
  <p class="lead">These cards were resolved by league rule, not by play. They are listed for completeness and
  never counted as a successful forecast.</p>
  {table(["Kick-off", "Tournament", "Match", "Settlement pick", "Official record", "Grade", "Sources"], settled_rows) if settled_rows else '<p class="muted">No forfeit settlements in this snapshot.</p>'}
</section>

<section class="panel">
  <h2>Started but ungraded ({len(ungraded)})</h2>
  <p class="lead">Hotspawn keeps <code>status=scheduled</code> on cards whose start time has passed. Where
  Leaguepedia holds no consistent record for the pair, the card stays listed and ungraded here - it is never
  scored from an assumption.</p>
  <p>The full list is on <a href="unresolved.html">Unresolved &amp; limitations</a>, together with every
  documented limitation of the data.</p>
</section>
"""
    return page_shell("Results &amp; track record", "results.html", body,
                      "Every published pick graded against the official League of Legends series record.")


