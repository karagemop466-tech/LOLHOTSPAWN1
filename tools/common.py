"""Shared HTTP + utility helpers for the Hotspawn LoL pick pipeline."""
from __future__ import annotations

import gzip
import io
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
CONTACT_UA = "LOLHotspawnResearch/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1)"


def ensure_dirs() -> None:
    for d in (DATA, RAW):
        os.makedirs(d, exist_ok=True)


def http_get(url: str, headers: dict | None = None, timeout: int = 60,
             retries: int = 3, backoff: float = 3.0) -> tuple[int, bytes]:
    """GET with retries. Returns (status, body). Status -1 means transport failure."""
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        hdrs.update(headers)
    last: tuple[int, bytes] = (-1, b"")
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                return resp.status, raw
        except urllib.error.HTTPError as exc:
            last = (exc.code, exc.read() or b"")
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(backoff * (attempt + 1) + random.random())
                continue
            return last
        except Exception as exc:  # noqa: BLE001 - transport errors vary
            last = (-1, str(exc).encode())
            if attempt < retries:
                time.sleep(backoff * (attempt + 1) + random.random())
                continue
    return last


def get_json(url: str, headers: dict | None = None, timeout: int = 60,
             retries: int = 3) -> tuple[int, object | None, str]:
    st, body = http_get(url, headers=headers, timeout=timeout, retries=retries)
    if st != 200:
        return st, None, body[:300].decode("utf-8", "replace")
    try:
        return st, json.loads(body), ""
    except Exception as exc:  # noqa: BLE001
        return st, None, f"json error: {exc}"


def save_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=False)
        fh.write("\n")
    os.replace(tmp, path)


def load_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def norm_name(value: str | None) -> str:
    """Normalise a team name for join keys (accents, punctuation, org suffixes)."""
    if not value:
        return ""
    s = unicodedata.normalize("NFKD", value)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[\u2018\u2019']", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch_ms_to_iso(ms) -> str | None:
    if ms in (None, "", 0):
        return None
    try:
        return iso(datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc))
    except (TypeError, ValueError):
        return None


def log(msg: str) -> None:
    print(f"[{now_utc().strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)
