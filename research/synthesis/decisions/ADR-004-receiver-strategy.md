# ADR-004: Receiver strategy — stock WLED first, custom firmware later

Status: Proposed (2026-07-03)

## Context

Portable/room tiers need network receivers that turn DDP frames into pixel
waveforms (P-6, R-1). Options: adopt stock firmware (WLED), commercial
Ethernet controllers, or write pewpew receiver firmware. Custom firmware
would unlock device-side interpolation+dithering (ADR-002 tier 4) but is a
whole embedded project; the engine must not block on it.

## Decision

- **Day one: stock WLED as the dumb receiver.** It already implements the
  needed contract: DDP ingest with offset + Push render flag, realtime
  preemption of local effects, timeout fallback to local state (P-6).
- **Room backbone: Ethernet pixel controllers** (Falcon F16v5 /
  QuinLED-Octa class) fed DDP/sACN (ADR-013).
- **Existing Pixelblaze output expanders reused** as host-driven serial
  sinks (UPXL, open/MIT).
- **Phase 4: pewpew receiver firmware (ESP32-S3)** adding what stock WLED
  cannot: keyframe interpolation + ≥400 Hz temporal dithering device-side.
- Sender-side caveats codified in the WLED sink: pin receiver brightness to
  255 or compensate for its scaling (WLED applies master brightness to
  realtime data; its gamma is off by default), and don't rely on the DDP
  timecode flag.

## Consequences

- pewpew is useful on the user's existing fleet immediately; receiver
  quality improves later without engine changes (sinks abstract it).
- Until Phase 4, 8-bit sinks get only host-side dithering (ADR-002 tier 3)
  — effective on slow fades, not full depth.
- Local-effect fallback behavior (hold last frame, revert after timeout)
  is inherited from WLED's realtime-lock contract and becomes the spec for
  the custom receiver too.
- **OTA/field-update story.** Stock-WLED receivers already carry their own
  update path (browser install via install.wled.me, integrated OTA from the
  device web UI [S754]). The Phase-4 pewpew receiver must not regress this:
  it adopts esp-idf's dual OTA app partitions with rollback for safe field
  updates and bad-flash recovery [S756], and esp-web-tools (Web Serial +
  Improv provisioning — the path WLED/Tasmota installers use) for initial
  flash and recovery [S755]. This is well-trodden ecosystem practice, not
  new research; it becomes a Phase-4 work item.

## Evidence

- [S645:wled00/e131.cpp#L20-L93][S645:wled00/udp.cpp#L410-L456] WLED's DDP
  ingest honors offset+Push and re-arms a realtime timeout on every packet,
  then falls back to local state — the exact preempt/hold/revert contract
  (P-6).
- [S253][S162] The realtime-lock/hold-then-revert policy is WLED's
  documented contract for stream loss. Caveat: both IDs are the same WLED
  doc page — a single source, not two. The policy is independently
  corroborated as field practice by sACN's normative 2.5 s data-loss
  timeout [S157] and ArtSync's 4 s fallback semantics [S159].
- [S645:wled00/wled.h#L453-L454] WLED still applies master brightness to
  realtime data (gamma off by default) — the sender-side caveat.
- [S682:README.md#L13-L78][S365] UPXL protocol is open (MIT), CRC-framed,
  DRAW_ALL latch — the expanders are reusable dumb sinks from any host.
- [S359] Falcon F16v5: 16×1,024 px over Ethernet+DDP with e-fuses — the
  backbone class exists off the shelf.
- [S600][S054][S251] Device-side interpolate+dither below the engine is
  proven (Fadecandy) and absent from every current receiver — the Phase-4
  lever.

## Rejected alternatives

- **Custom receiver firmware first** — months of embedded work before any
  light; stock WLED already implements the streaming contract
  [S645:wled00/udp.cpp#L410-L456].
- **Pixelblaze as a network receiver** — no standard pixel-stream input;
  its websocket is a control channel, not a frame transport [S681][S682].
- **ESPixelStick** — V4 in beta since 2023, development scattered; niche
  lost to WLED [S364].
- **Host bit-bangs pixels directly** (Pi GPIO) — Pi 5's RP1 broke legacy
  pixel output, and a network architecture makes it moot (R-8)
  [S367][S368].

## Amendment (2026-11-04) — board addressing and health

A bench board on DHCP got a new address after each power cycle (three
addresses in a row; the bench notes are not in this repo). The host kept
streaming to the old address; UDP got no answer, so nothing failed, and the board left
realtime mode after its 2500 ms timeout and showed its own look. The page
showed nothing wrong.
Code: `src/pewpew/health.py`, `src/pewpew/sinks/ddp.py`,
`src/pewpew/room.py` (`rebind_text`). *(Since 2026-11-05 the room map is
`src/pewpew/room/map.py`, and the `/json/info` fetch, the name lookup and
the Find boards sweep are in `src/pewpew/wled.py`.)*

### Decision

- **A board may be named by its mDNS name** (`"A": "pewpew-1.local"`) as
  well as by an IPv4 literal. The name is looked up off the render loop, by
  the board monitor, at start and again whenever the board stops
  answering; a new address is written to the audit log (`ddp-readdress`)
  before the sink sends there. The sink itself still never resolves a name.
- **The host polls each board's `/json/info`**, one request at a time
  (`pewpew.health`, checks in `BoardHealth.assess`), and also flags a board
  whose address is answered by another MAC than the one first seen.
- **The page says what is wrong and what to do.** The health panel shows
  each board's level as a word beside a coloured dot, the reasons, and one
  fix sentence; a banner names a board that has gone bad.
- **"Find boards" sweeps the host's /24** for `/json/info`, matches what it
  finds to room boards by MAC, and offers "use for A", which rewrites that
  board's one string in the room file; the existing map reload applies and
  audits it.

### Evidence

- [S1250:wled00/json.cpp#L762-L778][S1250:wled00/json.cpp#L869][S1250:wled00/json.cpp#L910]
  `/json/info` reports `live`, the realtime source `lm` ("DDP"), the
  sender's address `lip`, `uptime` and `mac`: enough to tell "takes this
  host's stream" from every failure above.
- [S1250:wled00/wled.cpp#L855-L860] WLED advertises its mDNS name with a
  `_wled._tcp` service carrying its MAC, so a `.local` name follows the
  board across DHCP changes.
- [S1250:wled00/wled.h#L451] The 2500 ms realtime timeout is why a lost
  stream shows as the board's own look within seconds.
- [S1300:homeassistant/components/wled/config_flow.py#L77-L91] Home
  Assistant identifies a WLED by MAC and updates its host when that MAC
  appears at a new address: the same follow-the-board model.
- [S1301:www/multisync.php#L1696-L1804] FPP marks a remote system
  unreachable only after consecutive failed polls: prior art for the
  two-poll confirmation.
- [S1303] WCAG 1.4.1: state shown by colour must also show as text or
  shape.

### Rejected alternatives

- **Fixed IPv4 addresses only** (the v0.2.6 rule): correct on a router
  with DHCP reservations, but a board on any other network silently
  loses the stream after a power cycle, which is the incident above.
- **Looking names up in the sink**: a name no resolver answers blocks for
  seconds, on the thread beside the render loop (`docs/backlog/v0.2.x.md`,
  room map story).
- **python-zeroconf for discovery** [S1305]: a fifth runtime dependency,
  LGPL, for what a standard-library HTTP sweep of the /24 also finds.
- **Shelling out to `dns-sd`** [S1304]: Apple calls scripted use fragile.
- **Mark the board offline and wait for the user** (LedFx) [S1302]: it
  leaves the address change to be found and fixed by hand.
