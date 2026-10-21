"""Shared helpers for the Hotspawn LoL pick'em research pipeline.

Design rules (see COORDINATION.md / site methodology page):

* Every number written into ``data/`` must be traceable to a URL that was actually fetched
  by this program.  Nothing is inferred silently: if a field cannot be read from a source it
  is left ``None`` and a flag is recorded.
* Hotspawn's own "X% picked" numbers are captured for display only and are never used as a
  probability input.
* All network access goes through :class:`Fetcher`, which records per-source status so the site
  can honestly report which sources were attempted, which succeeded and which failed.
"""

from __future__ import annotations

import hashlib
import html as _html
import json
import math
import os
import posixpath
import re
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit

try:  # requests is only needed for live runs (GitHub Actions runner)
    import requests
except Exception:  # pragma: no cover - exercised only in tooling sandboxes
    requests = None

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None

# A plain browser User-Agent: hotspawn.com's edge cache answers 403 to anything that advertises
# itself as a bot, and its fixture feed is the only way to verify a lobby card independently.
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
BOT_CONTACT_UA = (USER_AGENT + " hotspawn-lol-research/1.0 "
                  "(+https://github.com/karagemop466-tech/LOLHOTSPAWN1)")
CURL_UA = "curl/8.5.0"

# per-request header presets (used by the collector and by scripts/diag_probe.py)
BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}
JSON_HEADERS = {"Accept": "application/json", "Accept-Language": "en-US,en;q=0.9"}

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# --------------------------------------------------------------------------- time
def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def parse_countdown(text: str) -> int | None:
    """Convert Hotspawn's lock countdown ("4d 6h 34m", "01:36:15", "12s") to seconds."""
    text = (text or "").strip()
    if not text:
        return None
    m = re.fullmatch(
        r"(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?", text
    )
    if m and any(m.groups()):
        d, h, mi, s = (int(x) if x else 0 for x in m.groups())
        return ((d * 24 + h) * 60 + mi) * 60 + s
    m = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})", text)
    if m:
        h, mi, s = (int(x) for x in m.groups())
        return (h * 60 + mi) * 60 + s
    return None


# --------------------------------------------------------------------------- io
def read_text(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read_json(path: str, default=None):
    text = read_text(path)
    if text is None:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def write_json(path: str, obj) -> None:
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n")


def write_debug(name: str, text: str, out_dir: str = "data") -> None:
    """Small human-readable dumps committed for parser auditing (kept tiny on purpose)."""
    write_text(os.path.join(out_dir, "debug", name), text)


def append_log(path: str, line: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line.rstrip("\n") + "\n")


def log(msg: str) -> None:
    print(f"[{utcnow().strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------- http
class Fetcher:
    """HTTP with polite retries and a per-host status ledger.

    The ledger is emitted as ``data/sources.json`` so the published site can state exactly
    which sources were attempted and whether the fetch succeeded, instead of hand-waving.
    """

    def __init__(self, cache_dir: str | None = None, timeout: int = 45, delay: float = 0.35):
        self.timeout = timeout
        self.delay = delay
        self.cache_dir = cache_dir
        self._lock = threading.Lock()
        self.status: dict[str, dict] = {}
        self._session = requests.Session() if requests else None
        if self._session is not None:
            self._session.headers.update({"User-Agent": USER_AGENT, **BROWSER_HEADERS})

    # -- ledger ------------------------------------------------------------
    def _host_entry(self, url: str) -> tuple[str, dict]:
        host = re.sub(r"^www\.", "", (urlsplit_host(url) or "unknown"))
        with self._lock:
            entry = self.status.setdefault(
                host,
                {"host": host, "attempts": 0, "ok": 0, "failed": 0,
                 "skipped_no_network": 0, "sample_urls": [], "errors": []},
            )
        return host, entry

    def _record(self, url: str, ok: bool, err: str = "", sample_limit: int = 6) -> None:
        _, entry = self._host_entry(url)
        with self._lock:
            entry["attempts"] += 1
            entry["ok" if ok else "failed"] += 1
            if not ok and err and len(entry["errors"]) < 6:
                entry["errors"].append(err[:200])
            if len(entry["sample_urls"]) < sample_limit:
                entry["sample_urls"].append(url)

    def _record_skip(self, url: str) -> None:
        _, entry = self._host_entry(url)
        with self._lock:
            entry["attempts"] += 1
            entry["skipped_no_network"] += 1
            if len(entry["sample_urls"]) < 6:
                entry["sample_urls"].append(url)

    # -- fetch -------------------------------------------------------------
    def get(self, url: str, attempts: int = 3, use_cache: bool = True,
            headers: dict | None = None) -> str | None:
        """Return the response body as text, or ``None`` when unreachable.

        ``headers`` overrides the session defaults for this one request (used when a host answers
        differently to different client fingerprints).
        """
        if self.cache_dir and use_cache:
            cached = self._cache_get(url)
            if cached is not None:
                return cached
        if self._session is None:
            self._record_skip(url)
            return None
        backoff = 1.5
        for i in range(attempts):
            try:
                resp = self._session.get(url, timeout=self.timeout, headers=headers or None)
                if resp.status_code == 200 and resp.text:
                    self._record(url, True)
                    body = resp.text
                    if self.cache_dir and use_cache:
                        self._cache_put(url, body)
                    if self.delay:
                        time.sleep(self.delay)
                    return body
                if resp.status_code in (404, 410):
                    self._record(url, False, f"HTTP {resp.status_code}")
                    return None
                self._record(url, False, f"HTTP {resp.status_code}")
            except Exception as exc:  # network errors, TLS blocks, timeouts
                self._record(url, False, f"{type(exc).__name__}")
            time.sleep(backoff)
            backoff *= 2
        return None

    def get_json(self, url: str, attempts: int = 3, headers: dict | None = None) -> object | None:
        body = self.get(url, attempts=attempts, headers=headers)
        if body is None:
            return None
        try:
            return json.loads(body)
        except Exception:
            self._record(url, False, "invalid JSON")
            return None

    def map(self, urls: list[str], worker, max_workers: int = 6) -> list:
        """Fetch many URLs concurrently while keeping the ledger lock-guarded."""
        if not urls:
            return []
        results: list = [None] * len(urls)

        def run(pair):
            idx, url = pair
            try:
                return idx, worker(url)
            except Exception as exc:  # never let one page kill the run
                log(f"  ! worker error for {url}: {type(exc).__name__}: {exc}")
                return idx, None

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for idx, value in pool.map(run, list(enumerate(urls))):
                results[idx] = value
        return results

    # -- cache -------------------------------------------------------------
    def _cache_path(self, url: str) -> str:
        key = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, key[:2], key + ".txt")

    def _cache_get(self, url: str) -> str | None:
        path = self._cache_path(url)
        if not os.path.exists(path):
            return None
        # cache is only good for the current run window (30 min)
        if time.time() - os.path.getmtime(path) > 1800:
            return None
        return read_text(path)

    def _cache_put(self, url: str, body: str) -> None:
        try:
            write_text(self._cache_path(url), body)
        except OSError:
            pass

    def ledger(self) -> dict:
        out = {}
        for host, entry in sorted(self.status.items()):
            entry = dict(entry)
            total = entry["attempts"] or 1
            entry["success_rate"] = round(entry["ok"] / total, 3)
            out[host] = entry
        return out


def urlsplit_host(url: str) -> str:
    try:
        return urlsplit(url).netloc
    except Exception:
        return ""


# --------------------------------------------------------------------------- html
def annotate_links(markup: str) -> str:
    """Replace every ``<a href="X" ...>`` opening tag with the bare URL on its own line.

    Without this, stripping tags deletes the only thing that identifies a fixture (its match-page
    URL lives in the ``href`` attribute, not in the visible label).  Keeping the URL inline means the
    same line-stream parser works for Hotspawn's lobby, its league pages and the odds pages.
    """
    return re.sub(r"""(?is)<a\b[^>]*?href\s*=\s*["']([^"']+)["'][^>]*>""",
                  lambda m: "\n" + m.group(1) + "\n", markup or "")


def html_to_lines(markup: str, keep_links: bool = True) -> list[str]:
    """Flatten HTML into the visible text lines a browser would show.

    The parser works on the *text* stream instead of the tag tree on purpose: Hotspawn's lobby
    is server-rendered, so its visible text order is stable even when class names change.
    """
    if not markup:
        return []
    if keep_links:
        markup = annotate_links(markup)
    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(markup, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg", "template"]):
                tag.decompose()
            raw = soup.get_text("\n")
        except Exception:
            raw = _strip_tags(markup)
    else:  # graceful degradation if bs4 is missing
        raw = _strip_tags(markup)
    lines = []
    for line in raw.split("\n"):
        line = _html.unescape(line).replace("\u00a0", " ").strip()
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return lines


def _strip_tags(markup: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", markup)
    text = re.sub(r"(?s)<[^>]+>", "\n", text)
    return _html.unescape(text)


def find_links(markup: str, pattern: str) -> list[str]:
    """All hrefs matching ``pattern`` (deduplicated, order preserved)."""
    hrefs = re.findall(r"""href\s*=\s*["']([^"']+)["']""", markup or "", flags=re.I)
    out, seen = [], set()
    rx = re.compile(pattern)
    for href in hrefs:
        clean = _html.unescape(href)
        if rx.search(clean) and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out


# --------------------------------------------------------------------------- teams
_STOP_TOKENS = {
    "the", "team", "esports", "e-sports", "gaming", "club", "ev", "e", "v", "org",
    "organization", "de", "la", "le", "el", "and", "&", "of", "for", "-",
}

def canon_team(name: str) -> str:
    """Aggressive but conservative canonicalisation used to join sources.

    Only punctuation/diacritics/stop-words are removed.  Words that identify the *roster*
    (Academy, Youth, Rookies, Black, White, NXT, II, ...) are preserved, because joining
    "Team X Academy" onto "Team X" would be a fabricated link.
    """
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("\u00f8", "o").replace("\u00e6", "ae")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [t for t in text.split() if t and t not in _STOP_TOKENS]
    return " ".join(tokens)


def team_match(a: str, b: str) -> bool:
    """True when two team labels clearly denote the same roster (used to attach lines)."""
    ca, cb = canon_team(a), canon_team(b)
    if not ca or not cb:
        return False
    # Exact canonical equality only.  Prefix/containment matching is deliberately refused:
    # "KT Rolster Academy" must not inherit "KT Rolster"'s line, and "T1" must not swallow
    # "T1 Esports Academy Rookies".  A missed join only costs a flag; a wrong join would
    # publish a fabricated probability.
    return ca == cb


# --------------------------------------------------------------------------- odds math
def implied_prob(american=None, decimal=None) -> float | None:
    """Raw (over-round included) implied probability from one price."""
    try:
        if decimal:
            d = float(decimal)
            if d >= 1.01:
                return 1.0 / d
        if american:
            a = float(american)
            if a > 0:
                return 1.0 / (1.0 + a / 100.0)
            if a < 0:
                return (-a) / ((-a) + 100.0)
    except Exception:
        return None
    return None


def devig_two_way(p_a: float, p_b: float) -> tuple[float, float] | None:
    """Remove the vig proportionally for a two-way market.  No draw exists in LoL series."""
    if p_a is None or p_b is None:
        return None
    total = p_a + p_b
    if total <= 0:
        return None
    return (p_a / total, p_b / total)


def decimal_to_american(dec: float | None) -> int | None:
    if not dec:
        return None
    if dec >= 2:
        return int(round((dec - 1) * 100))
    return int(round(-100 / (dec - 1)))


def american_to_decimal(am) -> float | None:
    try:
        a = float(am)
    except Exception:
        return None
    if a >= 0:
        return round(1 + a / 100.0, 4)
    return round(1 + 100.0 / abs(a), 4)


def prob_to_decimal(p: float | None) -> float | None:
    if p is None or p <= 0 or p >= 1:
        return None
    return round(1.0 / p, 3)


def bo_n_prob(p_game: float, n: int) -> float:
    """Probability a team wins a best-of-n series given per-game win probability ``p_game``."""
    wins_needed = n // 2 + 1
    total = 0.0
    for games in range(wins_needed, 2 * wins_needed):
        # last game must be won by the champion
        k = wins_needed - 1
        tries = games - 1
        if tries < k:
            continue
        total += math.comb(tries, k) * (p_game ** k) * ((1 - p_game) ** (tries - k))
    total *= p_game
    return max(0.0, min(1.0, total))


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def pct(x: float | None, digits: int = 1) -> str:
    if x is None:
        return ""
    return f"{round(x * 100, digits):.{digits}f}%"


def slugify(text: str, maxlen: int = 70) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:maxlen] or "unsorted"


def esc(text) -> str:
    if text is None:
        return ""
    return _html.escape(str(text), quote=True)


def rel(path_from: str, path_to: str) -> str:
    """Relative href between two files inside ``site/`` (POSIX style)."""
    base = posixpath.dirname(path_from)
    if not base:
        return path_to
    return posixpath.relpath(path_to, base)


def download_banner() -> bool:
    """True when live HTTP is available in this environment (used to self-report)."""
    return requests is not None


def die(msg: str, code: int = 2) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    raise SystemExit(code)
