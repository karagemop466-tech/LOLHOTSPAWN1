#!/usr/bin/env python3
"""Independent structural check of the published HTML (root pages and docs/).

Written separately from ``tools/verify.py`` so that the deploy gate has a second,
disagreeing opinion.  Checks:
  L1 every internal link resolves to a file that exists (and to a real anchor)
  L2 no duplicate DOM ids
  L3 every page declares a mobile viewport
  L4 every published match appears exactly once on picks.html
  L5 the executive summary links to each picks view
  L6 no unrendered template values (None / nan / undefined / {{ )
  L7 every referenced asset exists and every page has navigation
"""
from __future__ import annotations

import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS: list[str] = []
WARNS: list[str] = []


class Doc(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.links: list[str] = []
        self.assets: list[str] = []
        self.text: list[str] = []
        self.has_viewport = False
        self.has_nav = False
        self.h1 = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag in ("link", "script") and (a.get("href") or "").endswith((".css", ".js")):
            self.assets.append(a.get("href"))
        if tag == "meta" and (a.get("name") or "").lower() == "viewport":
            self.has_viewport = "width=device-width" in (a.get("content") or "")
        if tag == "nav":
            self.has_nav = True
        if tag == "h1":
            self.h1 += 1

    def handle_data(self, data):
        self.text.append(data)


def parse(path: str) -> Doc:
    doc = Doc()
    with open(path, encoding="utf-8") as fh:
        doc.feed(fh.read())
    return doc


def main() -> int:
    root_pages = sorted(f for f in os.listdir(ROOT) if f.endswith(".html"))
    docs_dir = os.path.join(ROOT, "docs")
    docs_pages = sorted(f for f in os.listdir(docs_dir) if f.endswith(".html")) if os.path.isdir(docs_dir) else []
    pages = {f: os.path.join(ROOT, f) for f in root_pages}
    pages.update({os.path.join("docs", f): os.path.join(docs_dir, f) for f in docs_pages})

    parsed = {name: parse(path) for name, path in pages.items()}

    for name, doc in parsed.items():
        base = os.path.dirname(os.path.join(ROOT, name))
        if not doc.has_viewport:
            FAILS.append(f"L3 {name}: no mobile viewport meta")
        if not doc.has_nav:
            FAILS.append(f"L7 {name}: no <nav> element")
        if doc.h1 != 1:
            WARNS.append(f"L7 {name}: {doc.h1} <h1> elements (expected 1)")
        seen = set()
        for i in doc.ids:
            if i in seen:
                FAILS.append(f"L2 {name}: duplicate id #{i}")
            seen.add(i)
        for href in doc.links + [a for a in doc.assets if a]:
            if href.startswith(("http://", "https://", "mailto:", "#", "javascript:")):
                if href.startswith("#") and len(href) > 1 and href[1:] not in doc.ids:
                    FAILS.append(f"L1 {name}: anchor {href} has no target")
                continue
            target, _, frag = href.partition("#")
            target = target.split("?", 1)[0]
            if not target:
                continue
            abs_target = os.path.normpath(os.path.join(base, target))
            if not os.path.exists(abs_target):
                FAILS.append(f"L1 {name}: link {href} -> missing {os.path.relpath(abs_target, ROOT)}")
                continue
            if frag:
                rel = os.path.relpath(abs_target, ROOT)
                if rel in parsed and frag not in parsed[rel].ids:
                    FAILS.append(f"L1 {name}: link {href} -> {rel} has no id #{frag}")
        blob = " ".join(doc.text)
        for bad in ("None", "nan", "NaN", "undefined"):
            if re.search(rf"\s{re.escape(bad)}\s", blob):
                FAILS.append(f"L6 {name}: rendered placeholder {bad!r}")
        if "{{" in blob or "}}" in blob:
            FAILS.append(f"L6 {name}: unrendered template braces")

    # L4 every match exactly once on the canonical picks page
    picks = parsed.get("picks.html")
    if picks is None:
        FAILS.append("L4 picks.html missing")
    else:
        with open(os.path.join(ROOT, "picks.html"), encoding="utf-8") as fh:
            html = fh.read()
        data = json.load(open(os.path.join(ROOT, "data", "matches.json"), encoding="utf-8"))
        for row in data["matches"]:
            n = len(re.findall(rf'id="match-{re.escape(str(row["id"]))}"', html))
            if n != 1:
                FAILS.append(f"L4 match {row['id']} appears {n} times on picks.html")

    # L5 executive summary links
    index = parsed.get("index.html")
    if index is None:
        FAILS.append("L5 index.html missing")
    else:
        hrefs = " ".join(index.links)
        for view in ("picks.html", "featured.html", "originated.html", "unresolved.html",
                     "flagged.html", "sources.html", "verification.html"):
            if view not in hrefs:
                FAILS.append(f"L5 executive summary does not link to {view}")

    print(f"pages={len(pages)} failures={len(FAILS)} warnings={len(WARNS)}")
    for f in FAILS[:40]:
        print("FAIL", f)
    for w in WARNS[:20]:
        print("WARN", w)
    with open(os.path.join(ROOT, "audit", "site_check.json"), "w", encoding="utf-8") as fh:
        json.dump({"pages": len(pages), "failures": FAILS, "warnings": WARNS}, fh, indent=2)
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
