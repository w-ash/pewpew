# Archive verification report — critic: archive-load-bearing

- critic: archive-load-bearing (Phase 4)
- date: 2026-07-03
- scope: every [S###] cited in synthesis/architecture.md and synthesis/decisions/ADR-000..013
- status: COMPLETE

## Load-bearing set

150 unique source IDs extracted from architecture.md + ADR-*.md. All 150 have entries in
SOURCES.md (no dangling cites). Breakdown by type: code 49, docs 44, forum 17, product 15,
article 14, spec 6, datasheet 4, video 1 (101 non-code).

## Web sources — URL + archive status

Method: for each non-code entry lacking `archive:`: (a) curl liveness check (browser UA,
HEAD with GET-range fallback); (b) reuse an existing archive.org snapshot if one from
2025-01-01 or later existed (availability API), else request a fresh capture via
https://web.archive.org/save/<url> with >=10 s spacing.

Result: **99 of 101 non-code load-bearing entries now carry a real `archive:` snapshot URL;
2 are marked `archive: pending`** (see below). Verified programmatically at end of pass:
archived 99, pending 2, missing 0.

Notes from the pass:
- S054 (github.com/Aircoookie/WLED/issues/2416): HEAD returned 404 to curl but archive.org
  captured the page fine after GitHub's Aircoookie→wled org redirect — treated as alive,
  archive field added.
- S506 (manual.xlights.org): save redirected to /xlights landing page; snapshot recorded as
  https://web.archive.org/web/20260704012133/https://manual.xlights.org/xlights.
- S458 (python-sounddevice.readthedocs.io): snapshot resolved to the versioned page
  /en/0.5.3/ — same content the bare URL redirects to.

## Archive pending (rate-limited / blocked)

| S-ID | URL | status |
|---|---|---|
| S027 | https://forums.adafruit.com/viewtopic.php?t=207469 | origin 403s non-browser clients (anti-bot, not dead); archive.org save returned 520 twice; no prior wayback snapshot exists |
| S123 | https://www.tme.eu/Document/6e37dbd0c854ce14f428cca7891158c6/WS2816B-2020.pdf | origin 403s non-browser clients (anti-bot, not dead); archive.org save returned 520 twice; no prior wayback snapshot exists |

Both marked `- archive: pending (...)` in SOURCES.md so a later pass can grep for them
(`grep 'archive: pending' research/SOURCES.md`). Recommend a retry from a real browser or
via the authenticated Save-Page-Now API.

## Dead links

**None.** Every load-bearing web URL either resolved (HTTP 200, possibly after redirect) or
returned an anti-bot 403 to non-browser clients (S027, S123 — origins alive). No
`(dead as of 2026-07-03)` markers were needed.

## Code sources — excerpt check

Excerpt dirs present in research/excerpts/ covering load-bearing deep-dive sources:
S600, S615 (x3), S630 (x2), S645 (x3), S660 (x3), S670, S681, S682, S700, S715, S716
(19 dirs, each with LICENSE-NOTE.md; plus S683-sensor-board-dsp, not in the load-bearing set).

38 code sources are cited as ADR evidence; **27 lack excerpt dirs** (README archival rule
violation — excerpts NOT created by this critic per brief; follow-up required):

| S-ID | Citing ADRs |
|---|---|
| S001 | ADR-012 |
| S008 | ADR-008, ADR-012 |
| S011 | ADR-011, ADR-012 |
| S017 | ADR-011, ADR-012 |
| S019 | ADR-002, ADR-008 |
| S022 | ADR-006 |
| S026 | ADR-012 |
| S030 | ADR-011 |
| S035 | ADR-007, ADR-012 |
| S130 | ADR-013 |
| S208 | ADR-005, ADR-006 |
| S264 | ADR-010 |
| S300 | ADR-007 |
| S301 | ADR-007 |
| S364 | ADR-004, ADR-013 |
| S365 | ADR-003, ADR-004 |
| S367 | ADR-004, ADR-013 |
| S368 | ADR-004, ADR-013 |
| S406 | ADR-008 |
| S407 | ADR-008 |
| S451 | ADR-009, ADR-012 |
| S452 | ADR-009 |
| S453 | ADR-009 |
| S454 | ADR-009 |
| S457 | ADR-009 |
| S462 | ADR-009 |
| S552 | ADR-006, ADR-012 |

Missing excerpt dirs — code sources cited only in architecture.md, not as ADR evidence
(lower priority; README rule triggers on ADR citation) (11):
S034, S408, S461, S500, S511, S513, S514, S516, S517, S519, S520

Secondary observation (outside brief, no edit made): most RA-block code entries (S001,
S008, S011, S017, S019, S022, S026, S030, S034, S035, and other non-S6xx code sources)
have no `pinned:` field (35 pinned fields total in SOURCES.md vs 49+ code sources), while
the S6xx/S7xx deep-dive entries do. README requires `pinned:` for code sources "set at
read time"; the missing excerpts above cannot be cut until these are pinned.

## Fixes applied

All edits were to research/SOURCES.md only.

- First pass (84 entries) — added `- archive: <wayback-snapshot-url>`:
  S013 S016 S032 S050 S054 S055 S058 S059 S061 S063 S064 S068 S100 S101 S102 S105 S109
  S111 S112 S114 S115 S119 S121 S122 S126 S127 S128 S131 S133 S135 S150 S152 S157 S160
  S162 S165 S166 S203 S204 S205 S206 S207 S210 S211 S213 S214 S216 S251 S253 S258 S303
  S304 S305 S306 S308 S309 S311 S351 S352 S353 S355 S356 S357 S358 S359 S362 S363 S369
  S370 S400 S402 S403 S404 S405 S409 S410 S411 S412 S413 S414 S415 S416 S417 S418
- Second pass (15 entries) — added `- archive: <wayback-snapshot-url>`:
  S456 S458 S459 S504 S506 S508 S518 S550 S551 S553 S554 S555 S556 S680 S684
- Marked `- archive: pending (...)` with failure details on 2 entries: S027, S123.

Total: 101 SOURCES.md entries edited (99 snapshot URLs + 2 pending markers).

## Addendum — mesh + test/feedback synthesis pass

- date: 2026-07-10
- scope: every [S###] cited in ADR-014..019 (mesh tier + test/feedback/resilience)
- status: PARTIAL — archive.org Save-Page-Now was timing out during the pass; existing
  snapshots were applied, fresh captures deferred

Method: identical to the Phase 4 pass above (availability API, accept snapshots >=
2025-01-01, else SPN with polite spacing). SPN was largely unavailable (repeated read
timeouts on web.archive.org/save), so only 2 fresh captures landed.

Result: 149 unique S-IDs cited by ADR-014..019; 23 pinned code sources exempt; 2 already
archived. Of the 124 needing archives: **71 now carry real snapshot URLs** (65 existing
2025+ snapshots, 4 older snapshots annotated "predates accessed date", 2 fresh SPN
captures), **51 are marked `archive: pending`** (S806, S817, S851, S852, S860, S862, S867, S869, S870, S873,
… full list greppable via `grep -B6 'archive: pending' SOURCES.md`).

Special cases:
- S516/S517 (LedFx and FastLED tests directories) are repo-level code cites that entered
  SOURCES.md without `pinned:` fields — they need pins (per the archival rule), not
  archives. Left unmarked; resolve by pinning to the SHAs current at their 2026-07-03
  read date (git log of the RA-11 pass) or re-reading.

Next verification pass: re-run SPN for the 51 pending (the fetch script resumes from its
results file), refresh the 4 predates-accessed snapshots, and pin S516/S517.

## Addendum — pending-archive retry + excerpt-finding correction

- date: 2026-07-26
- scope: the 53 `archive: pending` entries, and the "27 lack excerpt dirs" finding above
- status: PARTIAL (archives), COMPLETE (pins)

### Correction: the excerpt finding above is wrong

The Phase-4 section reports **"38 code sources are cited as ADR evidence; 27 lack excerpt
dirs (README archival rule violation)"**. That is not a violation. The archival rule
(research/README.md) requires an excerpt only for code **cited with line anchors**
(`[S###:path#Lx-Ly]`) in an ADR; code cited at repo level needs a `pinned:` field and "no
excerpt required" — a scope the *same* Phase-4 pass set.

Checked all 27 against `synthesis/decisions/*.md`: **zero carry a line-anchored ADR cite.**
No excerpts are owed. The real gap was pins — 19 of the ADR-cited code sources had no
`pinned:` field, which is also why the original pass concluded the excerpts "cannot be cut
until these are pinned."

### Pins applied (19)

`pinned: owner/repo@<sha>` added for S001, S019, S022, S026, S035, S130, S300, S301, S364,
S365, S367, S368, S406, S407, S452, S454, S457, S516, S517 — closing the S516/S517 item the
mesh addendum left open.

SHAs resolved to each entry's `accessed:` date, not HEAD, via
`gh api "repos/OWNER/REPO/commits?until=<accessed>T23:59:59Z&per_page=1"`. Method validated:
it reproduced two pins set by hand in earlier passes (S035, S517) byte-for-byte. The two PR
entries (S130, S406) are pinned to their merge commits, which is what their "merged into
master" relevance claims actually rest on.

**Not closed:** ~40 further `type: code` entries still lack pins. None are ADR-cited, so the
archival rule does not trigger; several (PyPI, pastebin, wokwi) are not git repos and want an
`archive:` snapshot rather than a SHA. Tracked as a v0.1.x story.

### Archives: 47 of 53 resolved

Tooling: the earlier passes' fetch script was never committed, so this pass built
`research/tools/retry_archives.py` — availability API first (accepting snapshots ≥ 2025-01-01),
Save-Page-Now fallback at ≥10 s spacing, journalled after every entry so a rate-limited run
resumes instead of re-hammering SPN. Only the `- archive:` line of a resolved entry is
rewritten.

| Outcome | Count |
|---|---|
| Existing wayback snapshot reused | 30 |
| Fresh Save-Page-Now capture | 17 |
| **Still pending** | **6** |

Notable: **S123** (the WS2816B datasheet, pending since 2026-07-03 as an anti-bot 403)
captured successfully — the origin blocks non-browser clients, but SPN's fetcher got through.

Still pending after two full SPN passes — same failure code both times, so these are
domain-level refusals, not the transient outage the earlier addendum hit:

| S-ID | Domain | SPN status |
|---|---|---|
| S027 | forums.adafruit.com | 520 (×2) |
| S911 | usenix.org | 523 (×2) |
| S914 | link.aps.org | 520 (×2) |
| S1051 | devzone.nordicsemi.com | 520 (×2) |
| S1057 | devzone.nordicsemi.com | 520 (×2) |
| S1172 | sentry.io | 523 (×2) |

Retrying the script will not move these. They need a real-browser capture path; tracked as a
v0.1.x story. The 4 "predates accessed date" snapshots from the mesh pass were not revisited.
