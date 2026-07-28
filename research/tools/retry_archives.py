#!/usr/bin/env python3
"""Retry archive.org snapshots for SOURCES.md entries marked `archive: pending`.

The archival rule (research/README.md) requires every load-bearing web source
to carry an `archive:` snapshot URL. Two verification passes left entries
marked pending — the first to anti-bot 403s, the second to a Save-Page-Now
outage. This resumes that work.

Per entry: check the wayback availability API first and reuse a snapshot taken
**at or after that entry's own `accessed:` date**; otherwise request a fresh
capture via Save-Page-Now, spaced by --spacing seconds. Results are journalled
atomically after every entry, so an interrupted or rate-limited run resumes
where it stopped instead of re-hammering SPN.

The accessed-date cutoff is the point. A snapshot older than the read cannot
evidence what was read — it yields an `archive:` field that satisfies a grep
and proves nothing. An earlier version of this script used a flat 2025-01-01
cutoff and wrote 19 such fields.

Only the `- archive:` line of a selected, resolved entry is rewritten; nothing
else in SOURCES.md is touched.

    python3 research/tools/retry_archives.py --dry-run     # list, no network
    python3 research/tools/retry_archives.py               # availability only
    python3 research/tools/retry_archives.py --save        # + Save-Page-Now
    python3 research/tools/retry_archives.py --only S806,S817
    python3 research/tools/retry_archives.py --stale --save   # fix pre-read snapshots

Sources whose origin 403s non-browser clients (S027, S123) will not resolve
here — they need a real-browser capture. The script reports them as blocked
rather than pretending otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # research/
SOURCES = ROOT / "SOURCES.md"

ENTRY_RE = re.compile(r"^### \[(S\d+)\]")
URL_RE = re.compile(r"^- url: (.+)$")
ACCESSED_RE = re.compile(r"^- accessed: (.+)$")
ARCHIVE_RE = re.compile(r"^- archive: (.+)$")
PENDING_RE = re.compile(r"^- archive: pending\b")
AVAIL_API = "https://archive.org/wayback/available"
SAVE_URL = "https://web.archive.org/save/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def parse_entries(text: str, mode: str) -> dict[str, dict]:
    """Map S-ID -> {url, accessed} for entries this run should work on.

    mode "pending" — entries still marked `archive: pending`.
    mode "stale"   — entries whose snapshot predates their own `accessed:`
                     date. A snapshot older than the read cannot evidence what
                     was read, so those archive fields are not yet valid.
    """
    out: dict[str, dict] = {}
    sid = url = accessed = archive = None

    def flush() -> None:
        if not sid:
            return
        if mode == "pending" and archive and archive.startswith("pending"):
            out[sid] = {"url": url, "accessed": accessed}
        elif mode == "stale" and archive and not archive.startswith("pending"):
            snap = re.search(r"/web/(\d{8})", archive)
            if snap and accessed and snap.group(1) < accessed.replace("-", ""):
                out[sid] = {"url": url, "accessed": accessed, "old_snapshot": archive}

    for line in text.splitlines():
        m = ENTRY_RE.match(line)
        if m:
            flush()
            sid, url, accessed, archive = m.group(1), None, None, None
            continue
        if sid is None:
            continue
        if (u := URL_RE.match(line)) and url is None:
            url = u.group(1).strip()
        elif a := ACCESSED_RE.match(line):
            accessed = a.group(1).strip()
        elif ar := ARCHIVE_RE.match(line):
            archive = ar.group(1).strip()
    flush()

    for s, rec in out.items():
        if not rec["url"]:
            sys.exit(f"{s}: archive field with no url above it")
    return out


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


def normalize(snapshot_url: str) -> str:
    """research/README.md specifies the field as https://web.archive.org/...

    The availability API answers with http://; writing that back put 31
    scheme-inconsistent entries into SOURCES.md.
    """
    if snapshot_url.startswith("http://web.archive.org/"):
        return "https://" + snapshot_url[len("http://"):]
    return snapshot_url


def existing_snapshot(url: str, min_date: str, timeout: float) -> str | None:
    """Newest wayback snapshot at/after min_date (YYYYMMDD), or None.

    min_date is the entry's own `accessed:` date, not a global constant. A
    snapshot predating the read cannot evidence what was read — accepting one
    produces an archive field that looks compliant and proves nothing.
    """
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
    return normalize(snap.get("url", "")) or None


SNAPSHOT_RE = re.compile(r"^https?://web\.archive\.org/web/\d{8,}")


def save_page_now(url: str, min_date: str, timeout: float) -> tuple[str | None, str]:
    """Request a fresh capture. Returns (snapshot_url, note).

    Two checks, both load-bearing:

    - The response must be an actual /web/<timestamp>/ snapshot URL. A substring
      test for "/web/" would pass SPN's job-queued page for any source URL that
      itself contains "/web/", writing a /save/ URL in as the archive of record.
    - The returned snapshot must itself meet min_date. Save Page Now does *not*
      always capture: for a recently-archived page it redirects to the existing
      snapshot instead. Trusting the redirect marked three pre-read snapshots
      as "fresh capture" while leaving them exactly as stale as before.
    """
    status, final, _ = fetch(SAVE_URL + urllib.parse.quote(url, safe=":/?&=%#+,;@!$'()*~"), timeout)
    if status != 200:
        return None, f"SPN status {status}"
    m = SNAPSHOT_RE.match(final)
    if not m:
        return None, "SPN returned 200 but no snapshot URL"
    stamp = re.search(r"/web/(\d{8})", final)
    if stamp and stamp.group(1) < min_date:
        return None, f"SPN redirected to an existing {stamp.group(1)} snapshot, older than {min_date}"
    return normalize(final), "fresh SPN capture"


def load_journal(path: Path) -> dict:
    """Read the resume journal, tolerating a torn write from an interrupt."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"warning: unreadable journal {path} ({e}); starting fresh", file=sys.stderr)
        return {}


def save_journal(path: Path, results: dict) -> None:
    """Write atomically — an interrupt mid-write must not destroy the journal."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(results, indent=2, sort_keys=True))
    os.replace(tmp, path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, help="resume journal (JSON); default in the system temp dir")
    ap.add_argument("--spacing", type=float, default=10.0, help="seconds between Save-Page-Now requests (default 10)")
    ap.add_argument("--timeout", type=float, default=45.0, help="per-request timeout in seconds")
    ap.add_argument("--save", action="store_true", help="fall back to Save-Page-Now when no existing snapshot qualifies")
    ap.add_argument("--only", help="comma-separated S-IDs to attempt")
    ap.add_argument("--stale", action="store_true",
                    help="work on entries whose snapshot predates their accessed date, instead of pending ones")
    ap.add_argument("--force", action="store_true", help="re-attempt entries the journal already resolved")
    ap.add_argument("--min-date", default=None,
                    help="override the per-entry accessed date as the snapshot cutoff (YYYYMMDD); "
                         "the default — each entry's own accessed date — is almost always what you want")
    ap.add_argument("--dry-run", action="store_true", help="list selected entries and exit; no network, no writes")
    args = ap.parse_args()

    text = SOURCES.read_text()
    mode = "stale" if args.stale else "pending"
    selected = parse_entries(text, mode)
    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        selected = {k: v for k, v in selected.items() if k in want}

    print(f"{len(selected)} {mode} entries")
    if args.dry_run:
        for sid, rec in sorted(selected.items()):
            extra = f"  (snapshot {rec['old_snapshot']})" if rec.get("old_snapshot") else ""
            print(f"  {sid}  accessed {rec['accessed']}  {rec['url']}{extra}")
        return

    journal = args.results or Path(tempfile.gettempdir()) / f"pewpew-retry-archives-{mode}.json"
    results = load_journal(journal)
    if results:
        print(f"resuming from {journal} ({len(results)} already attempted)")

    last_save = 0.0
    for sid, rec in sorted(selected.items()):
        if results.get(sid, {}).get("snapshot") and not args.force:
            continue
        url = rec["url"]
        cutoff = args.min_date or (rec["accessed"] or "").replace("-", "") or "19700101"
        snap = existing_snapshot(url, cutoff, args.timeout)
        note = f"existing snapshot >= {cutoff}"
        if not snap and args.save:
            wait = args.spacing - (time.monotonic() - last_save)
            if wait > 0:
                time.sleep(wait)
            snap, note = save_page_now(url, cutoff, args.timeout)
            last_save = time.monotonic()
        elif not snap:
            note = f"no snapshot at/after {cutoff} (rerun with --save)"
        results[sid] = {"url": url, "accessed": rec["accessed"], "snapshot": snap, "note": note}
        save_journal(journal, results)
        print(f"  {sid}: {'OK  ' if snap else 'MISS'} {note}")

    # Only entries selected THIS run may be rewritten — a journal carried over
    # from a wider run must not silently edit entries outside --only.
    resolved = {sid: results[sid]["snapshot"]
                for sid in selected
                if results.get(sid, {}).get("snapshot")}
    if not resolved:
        print("\nnothing resolved; SOURCES.md unchanged")
        print(f"journal: {journal}")
        return

    out, sid, written = [], None, 0
    for line in text.splitlines():
        if m := ENTRY_RE.match(line):
            sid = m.group(1)
        if sid in resolved and ARCHIVE_RE.match(line):
            out.append(f"- archive: {resolved[sid]}")
            written += 1
        else:
            out.append(line)
    SOURCES.write_text("\n".join(out) + "\n")

    print(f"\nSOURCES.md: {written} archive fields written, {len(selected) - written} still {mode}")
    print(f"journal: {journal}")


if __name__ == "__main__":
    main()
