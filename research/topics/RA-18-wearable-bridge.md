# RA-18: Wearable participation in group coordination via BLE bridging

Last researched: 2026-07-09
Status: draft
S-ID block: S1050–S1099

## Key questions

1. Connectionless BLE broadcast/observer model: do legacy advertising payload limits (31 B AD, ~26 B usable) fit pewpew's ~11-byte group-state payload? What do BLE 5 extended advertising and nRF52840 support add?
2. What does periodic scanning (observer role) cost in mA on nRF52840 — scan-duty-cycle vs power vs state-freshness tradeoffs, with Nordic-sourced numbers?
3. Bridge node pattern: ESP32-S3 (or C6) dual-role ESP-NOW-recv + BLE-adv node vs an nRF52 bridge paired with an ESP32 over UART — which is simplest/most robust? How reliable is WiFi+BLE coexistence on S3?
4. CircuitPython feasibility on nRF52840: does `_bleio` support the observer role (scan for advertisements without connecting) while driving LEDs at ~60 fps? adafruit_ble status/maintenance; GC/latency issues.
5. Latency & rate: BLE advertising intervals vs the ~10 Hz group-state rate — is ~1–2 s state freshness trivial? Is beat-phase (tens of ms) achievable, or are wearables scene-synced but not beat-phase-synced?
6. Power verdict: does periodic BLE observing preserve the µA–low-mA class that justified nRF52840 in ADR-008?
7. Rejected paths, honestly checked: ESP-NOW-only wearable with WiFi off + connectionless power save (what average current is actually achievable?), Nordic ESB, LoRa on-body.

## Findings

### Connectionless BLE broadcast fits the payload trivially

A legacy BLE advertising PDU carries up to 31 bytes of AD structures; after the 2-byte length/type overhead of one AD element that is 29 bytes, and using the standard Manufacturer Specific Data container (the only AD type intended for arbitrary custom payloads, costing a further 2-byte Company ID) leaves ~27 bytes of custom payload [S1050]. pewpew's fixed-layout group-state payload is ~11 bytes — it fits in a single legacy advertisement with 2x headroom, even alongside a Flags element. Extended advertising (BLE 5) raises the ceiling to 254 bytes per AUX PDU (~250 custom via MSD), but is an optional feature "not necessarily supported by any Bluetooth Low Energy scanner" and buys nothing for an 11-byte payload [S1050]. Conclusion: **legacy non-connectable advertising is the right container**; extended advertising is unnecessary complexity for this payload size.

Interval floor: Bluetooth 4.x required non-connectable advertising intervals ≥100 ms ("the advInterval shall not be less than 100 ms", enforced by Nordic's SoftDevice); Bluetooth 5.0 (Vol 6, Part B, 4.4.2.2.1) removed the restriction, allowing the general 20 ms floor [S1059]. Either way the bridge can re-broadcast at or faster than the mesh's ~10 Hz state rate. Every advertising event also carries a mandatory link-layer `advDelay` — a pseudo-random 0–10 ms added per event (T_advEvent = advInterval + advDelay) that cannot be disabled [S1057]; this is the spec-level floor on BLE-advertising timing jitter and matters for the beat-phase question below.

The connectionless pattern is established practice in exactly pewpew's ecosystem: Adafruit's BLE_BroadcastNet library (MIT, pinned) packs compact fixed-layout sensor state into Manufacturer Specific Data and broadcasts it with no connection — "this is not a secure connection... think of this system as 'broadcasting' in the truest sense of the word" [S1060]; the companion Learn guide runs a fleet of CircuitPython broadcasters plus a BLE→WiFi bridge node [S1061] — the mirror image of pewpew's ESP-NOW→BLE bridge.

### Observer-side power on nRF52840: duty cycle is the whole game

The nRF52840 radio draws 6.26 mA (typ) while receiving at 1 Mbps BLE with the DC/DC regulator, and 6.40 mA transmitting at 0 dBm [S1052]; Nordic support confirms continuous scanning lands at ~6.5 mA with DCDC (~10 mA without), and that "the radio does consume quite a bit of power when it is running" — the only lever is the scan window/interval duty cycle [S1051]. The average scanning current is essentially `~6.5 mA x (scan_window / scan_interval)` plus baseline. Worked points:

| scan window / interval | radio duty | avg radio current |
|---|---|---|
| continuous | 100% | ~6.5 mA [S1051] |
| 100 ms / 1 s | 10% | ~0.65 mA |
| 30 ms / 1 s | 3% | ~0.2 mA |
| 30 ms / 5 s | 0.6% | ~0.04 mA |

(Derived from the continuous figure [S1051][S1052]; the wearable's CPU is already awake rendering LEDs, so the radio delta is the relevant budget item.) A bridge advertising the group state at high rate (e.g. every 50–100 ms) lets even a 30 ms window catch a packet with high probability per scan event — see latency section.

### Bridge node: ESP32-S3 dual-role in WiFi-STA mode is the simplest supported shape

The ESP32-S3 has a single 2.4 GHz RF module time-sliced between WiFi and BLE by a priority-arbitrated coexistence layer [S1053]. The official coexistence support table is decisive for the bridge design: **WiFi STA + BLE advertising is marked stable ("Y"), but ESP-NOW RX is "supported and the performance is stable in STA mode, otherwise not supported", and SoftAP + BLE combinations are marked unstable ("C1")** [S1053]. So a dual-role bridge is officially supported *provided* the WiFi side runs in station mode (which is how ESP-NOW mesh nodes run anyway), with coexistence enabled via `CONFIG_ESP_COEX_SW_COEXIST_ENABLE` and WiFi/BT tasks pinned to separate cores per Espressif's recommendation [S1053]. Espressif also warns to keep WiFi connectionless power-save parameters at defaults under coexistence unless extensively tested [S1053]. Two design consequences:

- **The bridge should be a dedicated, non-rendering node.** Coexistence time-slicing means some ESP-NOW receptions and some advertising events will be delayed or lost around each other; a node that does nothing but ESP-NOW-RX → repack → BLE-adv has no render deadline to miss, and the mesh's ~10 Hz repeating state broadcasts make individual losses self-healing (the next packet 100 ms later carries full state). No time-sync or history is needed — the bridge is stateless except for "latest seen group state."
- **ESP32-C6 offers no advantage for this role.** The C6 has the same single time-sliced 2.4 GHz RF module (WiFi/BLE/802.15.4) and the same coexistence-matrix shape (STA + BLE-adv "Y"; ESP-NOW RX stable only in STA mode) [S1065], plus a single core where Espressif's S3 guidance recommends pinning WiFi and BT to separate cores [S1053]. Choose S3 for fleet homogeneity with the mesh nodes.

**Alternative: nRF52-based bridge + paired ESP32 over UART.** Splitting the roles across two chips (ESP32 does ESP-NOW, forwards over UART to an nRF52 that does nothing but BLE advertising) removes RF coexistence contention entirely — each protocol gets a dedicated radio. The cost is two firmware images, an inter-chip framing protocol, and a custom two-chip board or wired module pair, and the nRF side would need nRF Connect SDK or CircuitPython advertising code. Since the single-chip S3 path is *officially documented as stable* for exactly this mode combination [S1053], the two-chip bridge is the fallback if bench testing (open question) shows unacceptable ESP-NOW loss or advertising starvation under coexistence — not the starting point.

### CircuitPython on nRF52840: the observer role is fully exposed

CircuitPython's core `_bleio` API supports the observer role directly: `Adapter.start_scan(prefixes=b'...', *, buffer_size=512, extended=False, timeout=None, interval=0.1, window=0.1, minimum_rssi=-80, active=True)` returns an iterable of `ScanEntry` objects; `interval` may range 0.0025–40.96 s with `window ≤ interval`, giving Python-level control of exactly the duty-cycle lever the power math needs, and `prefixes` filters advertisements by leading bytes (e.g. an MSD company-ID prefix) before they reach Python [S1055]. Passive scanning (`active=False`) skips scan-request/scan-response traffic — correct for a broadcast listener and cheaper [S1055]. The high-level `adafruit_ble` library (MIT) wraps this as `BLERadio.start_scan()` yielding typed `Advertisement`/`ManufacturerData` objects and is actively maintained — release 10.1.3 on 2026-04-23 [S1056].

Integration constraints, honestly:

- **Iteration blocks.** Iterating scan results blocks waiting for the next entry while the scan is active [S1055], so a 60 fps render loop cannot naively `for entry in scan:`. The workable patterns are short timeout-bounded scan bursts between frames, or scanning with a window that tolerates a blocked frame; which one holds 60 fps is a prototype item, not settled by docs.
- **Heap pressure is real but manageable.** Long-running unfiltered scans have historically driven 64 KB-class allocations and `MemoryError` on nRF52840 CircuitPython (issue filed 2020, closed 2023) [S1062]; the mitigations are exactly the knobs `_bleio` exposes — hardware `prefixes` filtering so only pewpew's advertisements are buffered, bounded `buffer_size`, and short scans [S1055][S1062]. GC pauses from scan-entry allocation are a jitter source for the render loop; ulab-style preallocated buffers on the render side don't protect against allocation inside the BLE stack's Python objects.
- **Radio + render concurrency exists in the ecosystem** — Adafruit's official guides run BLE and NeoPixel animation simultaneously on nRF52840-class boards [S1066] — but at low pixel counts and no stated frame rate; nobody has published scan-while-render numbers at pewpew's ~60 fps target. [NEEDS-VERIFICATION — prototype: fire benchmark + 30 ms/1 s passive scan on a Feather nRF52840.]

### Latency and rate: scene freshness is trivial; beat-phase is not

The rate math is comfortable in one direction. The mesh publishes state at ~10 Hz; the bridge re-advertises the latest state at a 50–100 ms advertising interval (both legal: BT 5 allows 20 ms non-connectable, and even the BT 4.x floor is 100 ms [S1059]). A wearable scanning with a 30 ms window every 1 s catches, per scan window, any advertiser whose interval is ≤ the window with high probability across the three advertising channels — and worst case simply waits for the next window. **State freshness within 1–2 s is therefore achievable at sub-percent radio duty cycle**; freshness within ~100–200 ms needs scan windows/intervals in that range (a few-percent to tens-of-percent duty).

Beat-phase is the other direction. The jitter stack between a mesh node's state change and the wearable's render loop includes: ESP-NOW→bridge delivery (ms-class), the bridge's advertising interval quantization (up to one interval, 50–100 ms), the mandatory pseudo-random 0–10 ms `advDelay` per advertising event [S1057], the wearable's scan-window aliasing (zero to one full scan interval), and CircuitPython-side GC/scheduling jitter [S1062]. Without time-sync there is no way to timestamp away the transport delay: the wearable cannot distinguish "phase reference generated 5 ms ago" from "generated 900 ms ago" beyond bounding it by its own scan cadence. Even in the most aggressive configuration (continuous scanning at ~6.5 mA [S1051], bridge advertising at 20 ms), the advDelay floor plus interpreter jitter puts phase error in the tens-of-milliseconds class — and continuous scanning forfeits the power story. **Verdict: wearables are scene/palette/tempo-synced, not beat-phase-locked.** The workable pattern is to carry tempo (and a coarse phase/bar counter) in the state payload and let the wearable free-run a local beat clock, applying slow corrections — beat-*aligned* to within human-noticeable-but-forgivable error, never sample-tight. Anything requiring tight phase (sub-30 ms visual simultaneity) stays on the ESP-NOW mesh tier.

### Power verdict: duty-cycled observing preserves the ADR-008 budget

Numbers, all nRF52840 with DC/DC at 3 V: radio RX at 1 Mbps BLE draws 6.26 mA (typ) [S1052]; Nordic support puts continuous scanning at ~6.5 mA system-level (~10 mA without DCDC), with duty-cycling the scan window/interval as the only real lever [S1051]. Average scanning current ≈ 6.5 mA × (window/interval):

| scan window / interval | radio duty | avg scan current | freshness bound (bridge adv @ ≤100 ms) |
|---|---|---|---|
| continuous | 100% | ~6.5 mA [S1051] | ~instant (adv interval + 0–10 ms advDelay) |
| 100 ms / 1 s | 10% | ~0.65 mA | ≤ ~1 s |
| 30 ms / 1 s | 3% | ~0.2 mA | ≤ ~1 s (may need 2 windows) |
| 30 ms / 5 s | 0.6% | ~0.04 mA | ≤ ~5 s (idle/pocket mode) |

(Derived from [S1051][S1052].) Two framings: against ADR-008's µA-class *idle* budget, a 30 ms/5 s idle scan adds ~40 µA — the wearable stays in the µA–low-mA class that justified nRF52840. Against the *active* budget, the wearable is already spending several mA of CPU on rendering and tens-to-hundreds of mA on LEDs, so even the 0.2–0.65 mA of a 1 s-fresh scan cadence is noise. The correct policy is adaptive duty: slow scan when dark/idle, 1 s-class scan when rendering. Only continuous scanning (~6.5 mA) would materially erode the advantage, and nothing in the design requires it. Compare the rejected alternatives: this is ~2 orders of magnitude below an ESP-NOW-only wearable (~20 mA average, below) and ~3 below the SoftAP floor that ADR-008 already rejected.

### Rejected alternative paths (cited)

- **ESP32 radio on the wearable, SoftAP mode** — already rejected in ADR-008 on the ~100–130 mA no-power-save SoftAP floor; not re-litigated here.
- **ESP-NOW-only wearable (WiFi APIs off, connectionless power save)** — the honest check. ESP-NOW does have a purpose-built power-save mode: `esp_now_set_wake_window()` + `esp_wifi_connectionless_module_set_wake_interval()` duty-cycle the RX radio, station mode only (the default window "allow[s] RX all the time") [S1054]. But Espressif's own measured (shielded-box) figures for the analogous duty-cycled-radio regime on ESP32-S3 land at ~19.5–20.7 mA *average* with DFS enabled (~38–40 mA without), with ~113 mA peaks [S1058]. So the surprise is real but bounded: ESP-NOW+sleep is ~5× better than the SoftAP floor, yet still ~30–100× worse than a duty-cycled nRF52840 observer (~0.2–0.65 mA) [S1051][S1058]. It also abandons the CircuitPython-on-nRF52840 stack ADR-008 chose. Rejected for wearables; fine for mains/pack-powered mesh nodes, which is what RA-13 already assumes.
- **Nordic Enhanced ShockBurst (ESB)** — proprietary 2.4 GHz protocol whose interop is limited to nRF5/nRF52/nRF53/nRF24-series silicon, shipped as an nRF Connect SDK library demanding exclusive radio-resource access [S1063]. No ESP32 end can speak it, so it would *still* need a bridge (ESP-NOW↔ESB), and there is no CircuitPython exposure — the wearable would need custom NCS firmware, abandoning the tier's stack. Strictly dominated by BLE advertising, which nRF52840 CircuitPython speaks natively [S1055]. Rejected.
- **LoRa on-body** — EU 868 MHz ISM rules cap transmit duty cycle at ~1% (864 s airtime/day) [S1064]; a ~10 Hz continuous state broadcast is regulatorily impossible, before even considering the added radio hardware, antenna, and mismatch of LoRa's design point (long range, low rate) to a same-room sync problem. Rejected without further analysis.

### Recommended wearable-bridge disposition

1. **Bridge**: one (or more, for spatial coverage — receivers pick any copy, state is idempotent) dedicated non-rendering **ESP32-S3 node, WiFi in STA mode, coexistence enabled, cores split between WiFi and BT tasks** [S1053], that receives the mesh's ESP-NOW state broadcasts and continuously re-emits the latest ~11-byte group state as a **legacy non-connectable BLE advertisement in a Manufacturer Specific Data element** (fits with 2× headroom [S1050]) at a 50–100 ms advertising interval [S1059]. Two-chip (ESP32+nRF52 UART) bridge held as fallback only.
2. **Wearable-side stack**: unchanged from ADR-008 — CircuitPython + ulab on nRF52840 — adding a **passive, prefix-filtered, duty-cycled `_bleio` scan** (e.g. 30 ms/1 s active, 30 ms/5 s idle) costing ~0.04–0.2 mA average [S1051][S1052][S1055]. RP2350 (no-radio) wearables remain standalone — group participation is a reason to pick the nRF52840 variant, not to add a radio to RP2350.
3. **State tier**: **scene, palette, tempo: yes** (freshness ≤1–2 s at sub-percent duty, trivially); **beat-phase: no** — advDelay jitter [S1057], scan aliasing, and interpreter GC [S1062] cap it at tens-of-ms error even with continuous scanning; wearables free-run a local beat clock disciplined by the broadcast tempo, and tight-phase effects stay on the ESP-NOW mesh tier.

## Verdicts

- **Legacy non-connectable BLE advertising as the group-state carrier** — **stable.** Spec-mature (20 ms floor since BT 5 [S1059]), universally receivable by any BLE scanner [S1050], payload fits 2× over [S1050]. Build on it.
- **BLE 5 extended advertising** — **stable but unnecessary here.** 254 B AUX PDUs solve a problem pewpew doesn't have, at the cost of optional-feature scanner support [S1050]. Skip.
- **nRF52840 observer role** — **stable.** Official radio-current figures [S1052] and Nordic-confirmed scan behavior [S1051]; the duty-cycle math closes with large margin. Same "stable" as RA-09's nRF52840 verdict — this doc adds no reason to revisit it.
- **`_bleio` + adafruit_ble observer stack (CircuitPython)** — **stable, actively maintained.** Core API exposes scan interval/window/prefix filtering [S1055]; adafruit_ble MIT, release 10.1.3 on 2026-04-23 [S1056]; BroadcastNet (MIT, same-day commit activity) proves the connectionless pattern in-ecosystem [S1060]. Scan-while-render at 60 fps is the one unproven spot (prototype).
- **ESP32-S3 dual-role bridge (ESP-NOW RX + BLE adv under coexistence)** — **stable, with a bench-test caveat.** The exact mode combination is in Espressif's official support matrix as stable in STA mode [S1053]; no published loss-rate numbers, so prototype before committing fleet-wide.
- **ESP32-C6 as bridge silicon** — **stable but non-advantageous.** Same single time-sliced radio and matrix shape [S1065]; S3 wins on fleet homogeneity and dual-core task pinning [S1053].
- **ESP-NOW-with-power-save on wearables** — **waning for this role.** The mode exists and is better than its reputation (~20 mA average, not ~130 mA [S1054][S1058]) but is two orders of magnitude off the nRF52840 observer budget. Do not build wearables on it.
- **Nordic ESB / LoRa for wearable group sync** — **rejected** (nRF-only interop + no CircuitPython [S1063]; ~1% regulatory duty cycle [S1064]).

## Code-reading queue

1. **adafruit/Adafruit_CircuitPython_BLE_BroadcastNet** (`adafruit_ble_broadcastnet.py`) — the MSD packing pattern (company ID, sequence numbering, fixed-layout fields) as the direct template for pewpew's group-state advertisement format; check how it handles the 27-byte budget [S1060].
2. **adafruit/Adafruit_CircuitPython_BLE** (`advertising/__init__.py`, `BLERadio.start_scan`) — how prefix matching and Advertisement construction allocate per scan entry; what a minimal-allocation "raw ScanEntry, manual struct.unpack" fast path looks like for a 60 fps loop [S1056].
3. **adafruit/circuitpython `ports/nordic` `_bleio` implementation** (`Adapter.c`, `ScanResults.c`) — whether the SoftDevice buffers scan reports without Python involvement between windows, the blocking semantics of ScanResults iteration, and the real cost of `buffer_size` [S1055][S1062].
4. **ESP-IDF coexistence + NimBLE advertising example** (esp-idf `examples/bluetooth/nimble` + `esp_now` example) — skeleton for the bridge prototype: ESP-NOW RX callback updating a NimBLE advertisement payload in place; check whether adv-data updates at 10 Hz require stop/start of advertising [S1053][S1054].

## Open questions

- **Scan-while-render on real hardware.** No published data on nRF52840 CircuitPython holding ~60 fps ulab rendering while running a 30 ms/1 s passive prefix-filtered scan — frame-time jitter, dropped advertisements, GC pause distribution. Settle with: fire benchmark + scan on a Feather nRF52840, PPK2 on the rail to confirm the derived ~0.2 mA scan delta [S1051][S1052].
- **Bridge loss rate under coexistence.** Espressif's matrix says "stable" for STA+BLE-adv and ESP-NOW-RX-in-STA [S1053] but publishes no numbers: what fraction of 10 Hz ESP-NOW broadcasts does a bridging S3 miss while advertising at 50 ms? Settle with: two-node bench test, counters on both sides. If loss is >~20% sustained, escalate to the two-chip UART bridge.
- **Advertising-payload update cadence on the bridge.** Whether NimBLE (ESP-IDF) updates advertising data in place at 10 Hz without visible gaps in the advertising train. Settle in code-reading item 4 / bridge prototype.
- **Company ID etiquette.** Shipping a product-adjacent protocol inside Manufacturer Specific Data formally requires a Bluetooth SIG-assigned company identifier; BroadcastNet rides Adafruit's ID [S1060]. Decide: test-range ID for art use vs. rider on an existing ID vs. SIG membership. Not a blocker for prototypes.
- **Achievable beat-phase error, measured.** The tens-of-ms estimate is a composition of documented jitter bounds (advDelay 0–10 ms [S1057], scan aliasing, GC [S1062]), not a measurement. If coarse beat alignment (±50 ms class) turns out to matter for wearables, measure end-to-end phase error at continuous scan before declaring even that infeasible.
- **iOS/Android phone as a fallback bridge.** Phones can scan ESP-NOW? No — but a phone *could* relay group state to a wearable over GATT when no bridge node is present. Whether this degenerate path is worth speccing was out of scope here.
