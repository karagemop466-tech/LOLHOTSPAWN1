#!/usr/bin/env python3
"""Diagnostics: inspect the Angular SSR ng-state payload of play.hotspawn.com/lol-pickems."""
import json
import re
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace")


def main():
    html = fetch("https://play.hotspawn.com/lol-pickems")
    m = re.search(r'id="ng-state"[^>]*>(.*?)</script>', html, re.S)
    print("html bytes:", len(html), "| ng-state found:", bool(m))
    if not m:
        return
    raw = m.group(1)
    print("ng-state bytes:", len(raw))
    state = json.loads(raw)
    print("top-level keys:", list(state.keys())[:40])

    def walk(node, path="", depth=0):
        if depth > 6:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    print(f"LIST {path}.{k} len={len(v)} keys={list(v[0].keys())[:25]}")
                    sample = {kk: vv for kk, vv in list(v[0].items())[:18]
                              if not isinstance(vv, (dict, list))}
                    print("  sample:", json.dumps(sample)[:900])
                elif isinstance(v, (dict, list)):
                    walk(v, f"{path}.{k}", depth + 1)
        elif isinstance(node, list):
            for i, v in enumerate(node[:3]):
                walk(v, f"{path}[{i}]", depth + 1)

    walk(state)


if __name__ == "__main__":
    main()
