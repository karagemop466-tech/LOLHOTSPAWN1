#!/usr/bin/env python3
"""mobile_audit.py - static phone-readability audit of the published pages.

Session c0a05820 (I2). The brief is "readable and accessible on a phone". jsdom
cannot compute layout, so this audits the properties that actually decide whether a
360 px viewport works, on every generated page:

  viewport meta · no fixed widths over 360 px · every <table> inside a scroll
  wrapper · a breakpoint at or below 480 px · 16 px base type · tap targets that
  reach 40 px · stacked-card labels on table cells · a one-tap bottom nav ·
  direct in-site links to every picks list from the landing page.

    python3 audit/mobile_audit.py [--dir .] [--json out.json]
Exit 0 = every page passes, 1 = at least one failure (listed, never silent).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PAGES = ["index.html", "table.html", "picks.html", "featured.html", "originated.html",
         "unresolved.html", "competitions.html", "teams.html", "flagged.html",
         "coverage.html", "verification.html", "sources.html", "methodology.html"]

PICKS_LINKS = ["table.html", "picks.html", "featured.html", "originated.html",
               "unresolved.html", "flagged.html"]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_css(text: str) -> list[str]:
    """Return rule bodies with @media blocks flattened (blocks are tracked separately)."""
    return re.findall(r"\{([^{}]*)\}", text)


def css_failures(css: str) -> list[str]:
    fails: list[str] = []
    if not re.search(r"@media\s*\(max-width:\s*(\d+)px\)", css):
        fails.append("no max-width media query at all")
    else:
        bps = [int(n) for n in re.findall(r"@media\s*\(max-width:\s*(\d+)px\)", css)]
        if min(bps) > 480:
            fails.append(f"smallest breakpoint is {min(bps)}px (>480)")
    if ".tablewrap" not in css or "overflow-x:auto" not in css.replace(" ", ""):
        fails.append("no .tablewrap{overflow-x:auto} scroll container")
    body = re.search(r"body\{[^}]*\}", css)
    if not body:
        fails.append("no body rule")
    else:
        fs = re.search(r"font:\s*(\d+)px", body.group(0)) or re.search(r"font-size:\s*(\d+)px", body.group(0))
        if not fs:
            fails.append("body font size not declared in px")
        elif int(fs.group(1)) < 16:
            fails.append(f"body font size is {fs.group(1)}px (<16)")
    # fixed widths that would overflow a 360 px phone
    widths = [(int(w), sel) for sel, w in []]
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel, bodytxt = m.group(1).strip(), m.group(2)
        for w in re.finditer(r"(?<!max-)(?<!min-)width:\s*(\d{3,})px", bodytxt):
            val = int(w.group(1))
            if val > 360:
                widths.append((val, sel))
    if widths:
        fails.append("fixed width >360px: " + ", ".join(f"{s} ({w}px)" for w, s in widths[:4]))
    if ".mobnav" not in css:
        fails.append("no .mobnav bottom navigation rule")
    # tap targets
    if not re.search(r"(min-height|padding)\s*:\s*(4[0-9]|[5-9][0-9]|\d{3,})px", css):
        fails.append("no rule giving a >=40px tap target")
    return fails


def page_failures(html: str, name: str, css: str) -> list[str]:
    fails: list[str] = []
    if not re.search(r'<meta[^>]+name="viewport"[^>]+width=device-width', html):
        fails.append("missing viewport meta with width=device-width")
    if not re.search(r'<html[^>]+lang="', html):
        fails.append("missing <html lang>")
    tables = len(re.findall(r"<table\b", html))
    wraps = len(re.findall(r'class="[^"]*tablewrap[^"]*"', html))
    if tables and wraps < tables:
        fails.append(f"{tables} table(s) but only {wraps} scroll wrapper(s)")
    if tables:
        cells = len(re.findall(r"<td\b", html))
        labelled = len(re.findall(r"<td[^>]*data-label=", html))
        if cells and labelled < cells:
            fails.append(f"{cells - labelled}/{cells} table cells lack data-label (no stacked card layout)")
    if 'assets/style.css' not in html:
        fails.append("stylesheet not linked")
    if "app.js" not in html:
        fails.append("assets/app.js not linked")
    if 'class="mobnav' not in html:
        fails.append("no bottom mobile nav rendered")
    if name == "index.html":
        missing = [p for p in PICKS_LINKS if f'href="{p}"' not in html]
        if missing:
            fails.append("exec summary missing in-site links: " + ", ".join(missing))
        if f'class="cta"' not in html:
            fails.append("no hero call-to-action row")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    root = Path(args.dir).resolve()
    css = (root / "assets" / "style.css").read_text(encoding="utf-8")

    report = {"generated_utc": now(), "root": str(root), "pages": {}, "css": {}}
    css_fails = css_failures(css)
    report["css"] = {"ok": not css_fails, "failures": css_fails}

    failures = 0
    for name in PAGES:
        path = root / name
        if not path.exists():
            report["pages"][name] = {"ok": False, "failures": ["page missing"]}
            failures += 1
            continue
        f = page_failures(path.read_text(encoding="utf-8"), name, css)
        report["pages"][name] = {"ok": not f, "failures": f}
        failures += 1 if f else 0

    report["passed"] = failures == 0 and not css_fails
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, indent=1) + "\n")

    print(f"css: {'PASS' if not css_fails else 'FAIL ' + '; '.join(css_fails)}")
    for name, r in report["pages"].items():
        print(f"{'PASS' if r['ok'] else 'FAIL'} {name}" + ("" if r["ok"] else " :: " + "; ".join(r["failures"])))
    print("RESULT:", "PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
