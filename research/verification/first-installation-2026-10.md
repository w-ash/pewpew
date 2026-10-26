# First installation — web research verification (2026-10-19)

Five research agents reported on 2026-10-19 for pewpew's first deployment (one
hotel room, three ESP32-S3 boards on stock WLED v16.0.1, DDP over a private
travel router). The reports shaped the "First installation" epic in
`docs/backlog/v0.2.x.md`. New sources S1250–S1299 (block RA-22); reused
S150, S158, S165, S202, S257, S303, S305, S309, S376, S418, S521, S550,
S551, S552, S554, S555, S670.

Claims below come from the reports and their cited sources. **Rechecked on
2026-10-26** against source: the WLED v16.0.1 lines cited inline (at
[S1250]'s pin), websockets' body refusal [S521], Home Assistant's WLED poll
interval [S1287], xLights' WLED per-port limit [S1279], pixelblaze-client's
flash default [S552], the state, author and dates of every WLED issue and PR
named here [S1253]–[S1257], release dates [S376][S1267][S1270][S1284], the
boot-loop rule [S1261], the S3 UDP throughput [S1251], and RFC 9119 [S1259].
Everything else is as the reports state it.

## Corrections to the reports

- The DDP data-type fix for v16 nightlies [S1254] reached the v16.0.0 and
  v16.0.1 tags as #5554 on `16_x` (merged 2026-05-01), not as #5547, which
  merged to `main` on 2026-05-13 and is not an ancestor of either tag. The
  behavior claim stands.
- PR #5267 (the S3 PR "using 600" per-output pixels) was closed **unmerged**
  on 2026-01-19 [S1256]. The reports had not checked this.
- "Largely untested except by author" describes WLED-MM PR #320 but is
  softhack007's comment in WLED #5478, not text from the PR [S1255].
- websockets 17.0.1 refuses a request body at
  `[S521:src/websockets/http11.py#L186-L190]`; the backlog cites L186–189.

## 1. WLED DDP over Wi-Fi at this scale

**Found.**
- 1,280 px per board is ~1.8 Mbit/s RGB or ~2.5 Mbit/s RGBW at 60 fps
  (inference, arithmetic), against an S3 iperf UDP RX of 30 Mbit/s over the
  air in the lab [S1251]. Bandwidth is not the constraint; 2.4 GHz airtime
  contention and jitter are (inference). The S3 is 2.4 GHz only [S1251].
- One output of 320 RGBW px takes ~12.8 ms on the wire, ~78 fps if the
  outputs run in parallel [S1252]; the S3 has 4 RMT outputs
  [S1250:wled00/const.h#L88].
- A streamed frame is shown only if more than 15 ms have passed since the
  last show [S1250:wled00/udp.cpp#L477], a ~66 fps cap; bursty arrival
  merges or drops frames (inference). Target FPS (default 42) does not gate
  DDP [S1250][NEEDS-VERIFICATION].
- DDP bytes per pixel are set per packet: 4 when data-type bits 3–5 are
  `011`, else 3 [S1250:wled00/e131.cpp#L54-L57]. An 8-bit RGBW type byte is
  0x1B [S150][NEEDS-VERIFICATION]. Streamed RGB on an RGBW output gets W
  from the output's auto-white mode [S1250:wled00/bus_manager.cpp#L275].
- Measured scale: a classic-ESP32 Dig-Octa (4×400 RGB) had to drop fps from
  ~1,400 LEDs, Wi-Fi vs Ethernet not stated [S1252]; stutter building over
  hours, cured by reboot, closed not planned [S1253] (#4320); ~4k px on 5
  ESP32s over DDP "no lag on wifi", no fps or version [S1258]; WLED docs
  advise ≤3 E1.31 universes (510 LEDs) for 40 fps [S158]. **No measurement
  of stock WLED DDP over Wi-Fi on an ESP32-S3 at this pixel count was
  found.**
- Settings: Wi-Fi sleep is off by default on ESP32
  [S1250:wled00/wled.h#L372]; modem sleep can delay RX by a DTIM cycle
  [S1251]. Realtime timeout defaults to 2,500 ms; 65000 holds the last frame
  [S418]. "Skip out-of-sequence" is off by default and assumes ≤4 packets
  per frame [S1254] (#5412); a 1,280-px RGBW frame needs 4 packets of
  1,440 B, RGB needs 3 (inference). DDP is unicast only
  [S1250:wled00/wled.cpp#L875], and Wi-Fi multicast would go at the slowest
  client's rate without ACKs [S1259]. The WLED FAQ recommends DDP [S165].
- Open bug: ~1 s lag on v16.0.0 that 0.15.3 lacks [S1253] (#5575, open).
  v16.0.1's notes carry no DDP change; related merged fixes are realtime
  gamma (#5666), color_wheel white (#5694) and audioreactive suspend in
  realtime (#5599) [S376].
- Venue: no WLED-specific post-mortem found. A maintainer puts live-mode
  stutter down to Wi-Fi and asks for "a clean wifi channel with no other
  traffic on it" [S1253] (#5596). QuinLED: Wi-Fi serves one device at a
  time, use Ethernet for realtime [S1260]. Disable WMM [S158]; channels
  1/6/11 at 20 MHz [S1260]; external antennas beat PCB ones [S165], and the
  DevKitC-1U has U.FL [S1260].
- Wired fallback: stock WLED has no W5500 support; WLED-MM PR #320 adds it,
  open since 2026-01 [S1255]. `main`'s `wled_ethernet.h` supports only RMII
  PHYs on classic ESP32 and ESP32-P4 [S001][NEEDS-VERIFICATION] (read on
  `main`, unpinned).

**Decided.** "Wi-Fi ingest test on the real rig" runs first: 1,280 px per
board at 40/50/60 fps, router on 1/6/11 at 20 MHz with WMM and client
isolation off and the laptop wired, v16.0.1 compared with v0.15.4, RMT
outputs. Its failure branch is boards with built-in Ethernet (classic ESP32
or P4), bought before check-in.

## 2. Live control interface

**Found.**
- Master with a hard cap: QLC+ Grand Master "Limit" [S1264], Pixelblaze
  "Limit Brightness" [S1268]. ETC's hardware blackout needs two keys, its
  touchscreen one fires on one touch [S1269].
- Looks: Chromatik snapshots choose what they store, carry a transition time
  and a per-snapshot auto-cycle flag, and a re-recall finishes the running
  fade [S1265]; WLED presets can leave brightness out [S554]; a typed fade
  time overrides the stored one on desks [S1269]. LedFx scenes set each
  output to activate/ignore/force black/stop
  [S1266:docs/settings/scenes.md]; WLED playlists are steps with duration,
  fade, repeat and end preset [S550].
- Show vs editor: QLC+ kiosk mode with web login limited to the Virtual
  Console [S1264]; Chromatik Performance Mode [S1265]; Open Stage Control
  `read-only` [S1270].
- Override-and-restore: LedFx's silence scene journals state, switches, and
  restores [S1266:docs/developer/silence_scene.md]. Undo and a
  changed-since-saved count: grandMA3 Oops and masters [S1269].
- Phone: 24 CSS px is the WCAG AA floor, 44 px the usual target; the bottom
  third is thumb-reachable [S1271]. Service workers need HTTPS or localhost
  [S1272], so a phone on plain HTTP gets no offline cache (inference).
- Two masters fight: WLED brightness scales incoming DDP unless "Force max
  brightness"; the current limiter still applies and is one setting for all
  outputs [S1263]. Writing WLED presets freezes the lights for seconds
  [S554]; pixelblaze-client defaults `saveToFlash` to False
  [S552:pixelblaze/pixelblaze.py#L972-L979].
- Flashes at 3–30 per second are the common photosensitive-seizure range
  [S1273].
- WLED's settings PIN guards settings pages and file editing only; the JSON
  API has no PIN check [S1250][NEEDS-VERIFICATION].
- Client isolation and auto channel selection took WLED nodes offline
  [S1258]. xSchedule is reportedly discontinued [S1274][NEEDS-VERIFICATION].

**Decided.** "On-site control page" (pattern picker, capped master, two-step
blackout, show view, phone layout, all assets local), "Saved looks with
crossfade recall" (partial-state looks on the laptop, deterministic fade,
idle cycle), and "Show pattern set" (nothing above 3 Hz; tap tempo, palette
swatches and randomize deferred).

## 3. 2D layout modeling

**Found.**
- Chromatik `.lxf` is the most complete file format: `strip` with
  `numPoints`, `spacing`, `direction`; ordered transforms; typed parameters;
  `tags`; per-component outputs; `instances` for arrays [S309]; tags drive
  views and the GUI reloads the file on save [S309][S1265]. Chromatik places the first point at the origin and steps
  by `spacing` [S309], so 64 px on 1 m is a 1/64 vs 1/63 trap (inference).
  Chromatik is left-handed with +Z into the scene (inference).
- One color per bar while the preview draws every pixel: xLights "Single
  Line as a Pixel" [S1278], LedFx grouping and span vs copy [S305], WLED
  segment grouping [S1262].
- Pixelblaze normalizes any units to 0–1 by Fill or Contain [S202]; Fill
  stretches aspect (inference).
- Floor plan: xLights background brightness [S1278] and a two-point ruler
  that sets real length [S1279:src-core/models/RulerObject.h].
- Wiring checks: xLights model chains and overlap flags [S1278][S1279];
  the controller visualizer refuses upload on errors [S1278]; xLights caps
  WLED ESP32 at 3,600 channels per port
  [S1279:resources/controllers/wled.xcontroller]; LedFx warns on overlapping
  segments [S305]. xLights allocates channels contiguously, so an insert
  mid-port shifts the rest [S1274].
- Per-output limits changed between releases: 300 px per parallel-I2S output
  in 0.15.0-b4 [S1256]; WLED docs call 512 per pin on 4 outputs "perfect
  performance" [S1262].
- WLED ledmaps: `map` with -1 gaps; a ledmap makes WLED ignore
  `2d-gaps.json`; the parser is whitespace-sensitive [S303].
- Preview: Chromatik's point cloud (point size, feather, contrast, gamma,
  LED textures) [S1277:src/main/java/heronarts/glx/ui/component/UIPointCloud.java];
  FastLED ScreenMap uses diameter 0.5 for 5 mm LEDs [S1280].
- Build day: marimapper maps from one webcam with a WLED backend [S670];
  MadMapper LED scanner [S1276]; wled-mapper lights the current LED [S1282];
  EasyLEDMap (v0.1, 2026-10) traces the data path on a photo [S1281].
- Not found: snap-to-grid in the tools surveyed, a distinct "LedMapper"
  product, a visual fixture editor in Chromatik, MoonLight's layout format.

**Decided.** "Room map file with live 2D simulation" (JSON in meters shaped
after `.lxf`, Contain normalization, wiring checks at load, fixture units by
two index tables), "Simulation view: floor plan and true-to-life pixels"
(pitch-sized dots over a two-point-calibrated plan, blink-to-identify), and
"Drag to arrange fixtures on the page" (xLights/Chromatik editing, file stays
the source of truth).

## 4. Room-event triggers

**Found.**
- OSC senders are current and maintained: TouchOSC 1.5.3, Companion v5.1.0
  with a generic-OSC module [S1284], Open Stage Control v1.31.0 [S1270], a
  Stream Deck OSC plugin [S1285]. python-osc 1.10.2 handlers can receive the
  sender address [S1283].
- Home Assistant `rest_command` is HTTP only [S1286]; ESPHome
  `http_request` runs on the main loop with a 4.5 s default timeout, and
  `udp.write` sends raw bytes [S1288]. websockets 17.0.1 refuses request
  bodies [S521:src/websockets/http11.py#L186-L190].
- MQTT needs a broker that from 2.0 binds localhost and then requires auth
  [S1289]; WLED MQTT has no TLS [S1262]. Network MIDI 2.0 was ratified
  2024-11; Microsoft's transport lacks auth [S1290].
- Sensors: LD2410 gates, 5 s presence timeout and engineering mode; LD2450
  three-target tracking [S1288]. mmWave false-triggers on fans, curtains and
  through thin walls; PIR needs ~1 min warm-up [S1291]; LD2450 ghost targets
  from furniture and metal [S1292]. MediaPipe live-stream drops frames for
  latency; latency figures not found [S1293].
- Arbitration precedents: HA automation modes [S1286]; TouchDesigner Trigger
  CHOP envelopes [S1294]; Chromatik triggers fire on change only [S1265];
  a student installation fired after 15 s of sustained activity [S1295].
- A board-local trigger fights DDP: WLED takes control back ~2.5 s after
  realtime stops [S1258]. WLED UDP sync is on by default on port 21324
  [S257].
- OSC has no authentication, and audience phones are a known attack path
  [S1295]. TouchDesigner's OSC In filters by address, not sender [S1294].

**Decided.** "Room-event triggers": a tick-stamped event queue first, with
debounce, cooldown, priority, edge-only firing and override-then-restore;
JSONL event log for L1 replay; inputs in order page button, HTTP `GET`,
then OSC; MQTT, network MIDI and camera deferred; bind to the router,
allowlist senders, require a token; sensors route to pewpew, WLED UDP sync
off.

## 5. Multi-day show reliability

**Found.**
- Biggest risks: macOS sleeping or throttling the sender, v16 brownout
  reboots on a weak 3.3 V rail, and boards silently resetting config
  (inference from the items below). No published show-day checklist found.
- Health: `/json/info` exposes `live`, `lip`, `leds.fps`, `wifi.rssi`,
  `uptime`, `freeheap` and `leds.count` [S550]. Polling the full `/json`
  stalled output every 10 s [S1253] (#3411); Home Assistant polls every 10 s
  [S1287:homeassistant/components/wled/const.py#L14].
- launchd restarts a job only on exit; `KeepAlive {SuccessfulExit=false}`,
  `ThrottleInterval` 10 s default, unset `ProcessType` throttles CPU and
  I/O; `caffeinate -i -s -w <pid>`; `pmset -c sleep 0` [S1296]. Only
  `pmset disablesleep 1` stops lid-closed sleep [S1298][NEEDS-VERIFICATION];
  it is absent from the 27.0 man page [S1296]. Background Security
  Improvements install silently from Tahoe 26.1 [S1298]. Automatic login is
  unavailable with FileVault on [S1297].
- WLED boot-loop recovery: after 5 crashes in 2 minutes it restores the
  backup config, then resets config, then rolls back firmware, one step per
  boot [S1261]. Config backup files exclude passwords
  [S1250][NEEDS-VERIFICATION].
- v16 crashes on weak 3.3 V; reported fixes are a 3V3 capacitor, TX ≤8.5 dBm
  and stable USB power, through 2026-10-12 [S1257]. Stale DDP sequence
  numbers after a sender restart: fix open in PR #5896 [S1254].
- Power: common ground across supplies, LEDs and ESP [S165]; fuse each
  supply near it [S1261]. Official power-up order not found; community says
  ground, V+, then data [S1299].

**Decided.** "Show health and restart safety" (read-only `/json/info` poller,
self-exiting watchdog under a LaunchAgent, sleep assertion, board config
backup, continuous DDP sequence numbers) and "Show checklist" (router, WLED,
macOS and power settings plus pre-doors checks, seeded from this note).
