#!/usr/bin/env python3
"""Retry archive.org snapshots for SOURCES.md entries marked `archive: pending`.

The archival rule (research/README.md) requires every load-bearing web source
to carry an `archive:` snapshot URL. Two verification passes left entries
marked pending — the first to anti-bot 403s, the second to a Save-Page-Now
outage. This resumes that work.

Per entry: check the wayback availability API first and reuse any snapshot at
or after --min-date; otherwise request a fresh capture via Save-Page-Now,
spaced by --spacing seconds. Results are journalled after every entry, so an
interrupted or rate-limited run resumes where it stopped instead of
re-hammering SPN.

Only the `- archive:` line of a resolved entry is rewritten; nothing else in
SOURCES.md is touched.

    python3 research/tools/retry_archives.py --dry-run     # list, no network
    python3 research/tools/retry_archives.py               # availability only
    python3 research/tools/retry_archives.py --save        # + Save-Page-Now
    python3 research/tools/retry_archives.py --only S806,S817

Sources whose origin 403s non-browser clients (S027, S123) will not resolve
here — they need a real-browser capture. The script reports them as blocked
rather than pretending otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # research/
SOURCES = ROOT / "SOURCES.md"

ENTRY_RE = re.compile(r"^### \[(S\d+)\]")
URL_RE = re.compile(r"^- url: (.+)$")
PENDING_RE = re.compile(r"^- archive: pending\b")
AVAIL_API = "https://archive.org/wayback/available"
SAVE_URL = "https://web.archive.org/save/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def parse_pending(text: str) -> dict[str, str]:
    """Map S-ID -> url for every entry whose archive field is pending."""
    pending: dict[str, str] = {}
    sid: str | None = None
    url: str | None = None
    for line in text.splitlines():
        m = ENTRY_RE.match(line)
        if m:
            sid, url = m.group(1), None
            continue
        if sid is None:
            continue
        u = URL_RE.match(line)
        if u and url is None:
            url = u.group(1).strip()
        elif PENDING_RE.match(line):
            if not url:
                sys.exit(f"{sid}: `archive: pending` with no url above it")
            pending[sid] = url
    return pending


def fetch(url: str, timeout: float) -> tuple[int, str, str]:
    """Return (status, final_url, body). Never raises on HTTP error status."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.url, resp.read(4096).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:  # timeout, DNS, TLS, redirect loop
        return 0, url, f"{type(e).__name__}: {e}"


def existing_snapshot(url: str, min_date: str, timeout: float) -> str | None:
    """Newest wayback snapshot at/after min_date (YYYYMMDD), or None."""
    query = f"{AVAIL_API}?{urllib.parse.urlencode({'url': url})}"
    status, _, body = fetch(query, timeout)
    if status != 200:
        return None
    try:
        snap = json.loads(body).get("archived_snapshots", {}).get("closest", {})
    except json.JSONDecodeError:
        return None
    if not snap.get("available") or snap.get("timestamp", "")[:8] < min_date:
        return None
    return snap.get("url")


def save_page_now(url: str, timeout: float) -> tuple[str | None, str]:
    """Request a fresh capture. Returns (snapshot_url, note)."""
    status, final, _ = fetch(SAVE_URL + url, timeout)
    if status == 200 and "/web/" in final:
        return final, "fresh SPN capture"
    return None, f"SPN status {status}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, help="resume journal (JSON); default: alongside SOURCES.md in a temp dir")
    ap.add_argument("--min-date", default="20250101", help="accept existing snapshots at/after this YYYYMMDD (default 20250101)")
    ap.add_argument("--spacing", type=float, default=10.0, help="seconds between Save-Page-Now requests (default 10)")
    ap.add_argument("--timeout", type=float, default=45.0, help="per-request timeout in seconds")
    ap.add_argument("--save", action="store_true", help="fall back to Save-Page-Now when no existing snapshot qualifies")
    ap.add_argument("--only", help="comma-separated S-IDs to attempt")
    ap.add_argument("--dry-run", action="store_true", help="list pending entries and exit; no network, no writes")
    args = ap.parse_args()

    text = SOURCES.read_text()
    pending = parse_pending(text)
    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        pending = {k: v for k, v in pending.items() if k in want}

    print(f"{len(pending)} pending entries")
    if args.dry_run:
        for sid, url in sorted(pending.items()):
            print(f"  {sid}  {url}")
        return

    journal = args.results or Path("/tmp") / "pewpew-retry-archives.json"
    results: dict[str, dict] = {}
    if journal.exists():
        results = json.loads(journal.read_text())
        print(f"resuming from {journal} ({len(results)} already attempted)")

    last_save = 0.0
    for sid, url in sorted(pending.items()):
        if results.get(sid, {}).get("snapshot"):
            continue
        snap = existing_snapshot(url, args.min_date, args.timeout)
        note = "existing snapshot"
        if not snap and args.save:
            wait = args.spacing - (time.monotonic() - last_save)
            if wait > 0:
                time.sleep(wait)
            snap, note = save_page_now(url, args.timeout)
            last_save = time.monotonic()
        elif not snap:
            note = "no qualifying snapshot (rerun with --save)"
        results[sid] = {"url": url, "snapshot": snap, "note": note}
        journal.write_text(json.dumps(results, indent=2, sort_keys=True))
        print(f"  {sid}: {'OK  ' if snap else 'MISS'} {note}")

    resolved = {sid: r["snapshot"] for sid, r in results.items() if r.get("snapshot")}
    if not resolved:
        print("\nnothing resolved; SOURCES.md unchanged")
        return

    out, sid = [], None
    written = 0
    for line in text.splitlines():
        m = ENTRY_RE.match(line)
        if m:
            sid = m.group(1)
        if sid in resolved and PENDING_RE.match(line):
            out.append(f"- archive: {resolved[sid]}")
            written += 1
        else:
            out.append(line)
    SOURCES.write_text("\n".join(out) + "\n")

    still = len(pending) - written
    print(f"\nSOURCES.md: {written} archive fields written, {still} still pending")
    print(f"journal: {journal}")


if __name__ == "__main__":
    main()
