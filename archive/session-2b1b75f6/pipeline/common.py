"""Shared helpers for the Hotspawn LoL pick pipeline.

No third-party dependencies: only the Python standard library is used, so the
collector can run unchanged on a GitHub Actions runner or locally.
"""
from __future__ import annotations

import gzip
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = ("LOLHotspawnPicks/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1; "
      "open-source esports odds research; contact via GitHub issues)")
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0.0.0 Safari/537.36")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get(url: str, headers: dict | None = None, retries: int = 3, timeout: int = 60,
             gz: bool = True) -> bytes:
    """GET a URL with retries. Raises the last error after `retries` attempts."""
    h = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.8"}
    if gz:
        h["Accept-Encoding"] = "gzip"
    h.update(headers or {})
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    try:
                        raw = gzip.decompress(raw)
                    except OSError:
                        pass
                return raw
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (400, 401, 403, 404, 406, 422):
                raise
            time.sleep(2 * (attempt + 1))
        except Exception as e:  # network hiccup / timeout
            last = e
            time.sleep(2 * (attempt + 1))
    raise last  # type: ignore[misc]


def get_json(url: str, headers: dict | None = None, **kw):
    return json.loads(http_get(url, headers, **kw))


# ---------------------------------------------------------------- team matching
_SUFFIXES = re.compile(
    r"\b(esports?|e-sports?|esport|gaming|gg|team|club|academy|acad|org|organization|"
    r"organization|official|main|roster|the)\b")
_PUNCT = re.compile(r"[^a-z0-9 ]+")


_TRANSLIT = {
    "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe", "ß": "ss",
    "ł": "l", "Ł": "l", "đ": "d", "Đ": "d", "ð": "d", "Ð": "d", "þ": "th", "Þ": "th",
    "ı": "i", "İ": "i", "å": "a", "Å": "a", "ę": "e", "Ę": "e", "ą": "a", "Ą": "a",
}


def norm_team(name: str) -> str:
    """Normalise a team name to a comparison key."""
    name = "".join(_TRANSLIT.get(ch, ch) for ch in (name or ""))
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = _PUNCT.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _SUFFIXES.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def token_set(name: str) -> set[str]:
    return {t for t in norm_team(name).split() if t}


def name_similarity(a: str, b: str) -> float:
    """0..1 similarity of two team names (exact-normalised or token containment)."""
    na, nb = norm_team(a), norm_team(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = set(na.split()), set(nb.split())
    if not ta or not tb:
        return 0.0
    if ta <= tb or tb <= ta:
        return 0.9
    inter = len(ta & tb)
    return inter / max(len(ta), len(tb))


# ------------------------------------------------------------------- odds maths
def american_to_decimal(price: float) -> float | None:
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if p == 0:
        return None
    return 1.0 + (100.0 / abs(p)) if p < 0 else 1.0 + (p / 100.0)


def decimal_to_prob(dec: float) -> float:
    return 1.0 / float(dec)


def devig_two_way(p1: float, p2: float) -> tuple[float, float]:
    """Proportional (multiplicative) de-vig of a two-way market."""
    total = p1 + p2
    if total <= 0:
        return 0.5, 0.5
    return p1 / total, p2 / total


def median(values: list[float]) -> float:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return 0.0
    n = len(vals)
    mid = n // 2
    return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2


def pct(p: float, digits: int = 1) -> str:
    return f"{100.0 * p:.{digits}f}%"
